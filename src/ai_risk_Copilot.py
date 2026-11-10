#!/usr/bin/env python3
"""
OmniPulse AI Risk Copilot & Deterministic Reactive Loop Simulator
Reactive Omni Buildathon (DoraHacks) — Reactive Smart Contracts + AI Automation

Simulates and verifies the end-to-end 3-step Reactive Network execution pipeline:
1. Origin Chain Event Emission (`Unichain Sepolia 1301` / `Base Sepolia 84532`)
2. Reactive Network RVM `react(LogRecord calldata log)` (<1s CometBFT finality on Lasna Testnet)
3. Destination Chain Authenticated `Callback` Execution (`OmniPulseCallbackVault.executeReactiveAction`)
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass, field
from typing import Any

UNICHAIN_SEPOLIA_CHAIN_ID = 1301
BASE_SEPOLIA_CHAIN_ID = 84532
REACTIVE_LASNA_CHAIN_ID = 5318007

TOPIC_UNISWAP_SWAP = 0xC42079F94A6350D7E6235F29174924F928CC2AC818EB64FED8004E115FBCCA67
TOPIC_POOL_SYNC = 0x1C411E9A96E071241C2F21F7726B17AE89E3CAB4C78BE50E062B03A9FFFBBAD1
TOPIC_AI_RISK_TELEMETRY = 0x8A9C5B2F4D1E3A7C9B0E2F6D8A1C3E5F7B9D0A2C4E6F8A0B2C4D6E8F0A1B2C3D

ACTION_STOP_LOSS_EXIT = 1
ACTION_CROSS_CHAIN_HEDGE = 2
ACTION_CIRCUIT_BREAKER_PAUSE = 3

ACTION_NAMES: dict[int, str] = {
    1: "ACTION_STOP_LOSS_EXIT",
    2: "ACTION_CROSS_CHAIN_HEDGE",
    3: "ACTION_CIRCUIT_BREAKER_PAUSE",
}


@dataclass
class LogRecord:
    chain_id: int
    _contract: str
    topic_0: int
    topic_1: int = 0
    topic_2: int = 0
    topic_3: int = 0
    data: bytes = b""
    block_number: int = 1
    op_code: int = 3
    block_hash: int = 0
    tx_hash: int = 0
    log_index: int = 0


@dataclass
class CallbackEvent:
    chain_id: int
    _contract: str
    gas_limit: int
    payload_hex: str
    decoded_args: dict[str, Any]


@dataclass
class VaultState:
    chain_id: int
    vault_address: str
    rvm_id: str
    callback_proxy: str
    circuit_breaker_paused: bool = False
    volatile_collateral_eth: float = 100.0
    stable_reserve_usdc: float = 150_000.0
    total_callbacks_executed: int = 0
    audit_log: list[dict[str, Any]] = field(default_factory=list)


def encode_uint256(val: int) -> bytes:
    return int(val).to_bytes(32, byteorder="big", signed=False)


def encode_int256(val: int) -> bytes:
    return int(val).to_bytes(32, byteorder="big", signed=True)


def decode_uint256(word: bytes) -> int:
    return int.from_bytes(word, byteorder="big", signed=False)


def compute_function_selector(signature: str) -> str:
    """
    Computes deterministic 4-byte selector hex for `executeReactiveAction(...)`.
    """
    digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:8]
    return f"0x{digest}"


def compute_ai_risk_telemetry(
    price_drop_pct: float,
    volume_spike_sigma: float,
    cross_chain_spread_bps: float,
    mempool_sandwich_density: float,
) -> dict[str, Any]:
    """
    AI Risk Copilot logistic + non-linear interaction scorer that evaluates real-time
    on-chain DEX pool telemetry and outputs `ai_risk_score_bps` (0 - 10,000) and
    `velocity_sigma_bps` (0 - 10,000) for `OmniPulseReactiveSentinel`.
    """
    z = (
        -2.65
        + 0.24 * max(0.0, price_drop_pct)
        + 0.58 * max(0.0, volume_spike_sigma)
        + 0.012 * max(0.0, cross_chain_spread_bps)
        + 2.40 * max(0.0, min(1.0, mempool_sandwich_density))
        + 0.08 * max(0.0, price_drop_pct) * max(0.0, volume_spike_sigma)
    )
    prob = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
    ai_risk_bps = int(round(prob * 10000))
    velocity_bps = min(10000, int(round(max(0.0, volume_spike_sigma) * 1650)))
    composite_bps = (ai_risk_bps * 70 + velocity_bps * 30) // 100

    return {
        "ai_risk_score_bps": ai_risk_bps,
        "velocity_sigma_bps": velocity_bps,
        "composite_score_bps": composite_bps,
        "manipulation_probability_pct": round(prob * 100.0, 2),
        "triggers_circuit_breaker": composite_bps >= 8000,
        "abi_encoded_data": encode_uint256(ai_risk_bps) + encode_uint256(velocity_bps),
    }


class ReactiveLoopSimulator:
    """
    Deterministic simulator of `OmniPulseReactiveSentinel` on Reactive Network (Lasna 5318007)
    paired with `OmniPulseCallbackVault` deployments on Unichain Sepolia (1301) and Base Sepolia (84532).
    """

    def __init__(
        self,
        stop_loss_price_usd: float = 2650.0,
        divergence_threshold_bps: int = 120,
        ai_circuit_breaker_bps: int = 8000,
    ) -> None:
        self.rvm_id = "0x7F4e9B20cA14dE89123B4567C8901234567890Ab"
        self.callback_proxy = "0x0000000000000000000000000000000000fffFfF"
        self.stop_loss_price_x96 = int(stop_loss_price_usd * 1_000_000)
        self.divergence_threshold_bps = divergence_threshold_bps
        self.ai_circuit_breaker_bps = ai_circuit_breaker_bps

        self.last_unichain_price_x96 = int(2880.0 * 1_000_000)
        self.last_base_price_x96 = int(2880.0 * 1_000_000)
        self.total_reactive_triggers = 0

        self.vaults: dict[int, VaultState] = {
            UNICHAIN_SEPOLIA_CHAIN_ID: VaultState(
                chain_id=UNICHAIN_SEPOLIA_CHAIN_ID,
                vault_address="0xUnichainOmniPulseVault000000000000001301",
                rvm_id=self.rvm_id,
                callback_proxy=self.callback_proxy,
            ),
            BASE_SEPOLIA_CHAIN_ID: VaultState(
                chain_id=BASE_SEPOLIA_CHAIN_ID,
                vault_address="0xBaseSepoliaOmniPulseVault000000000084532",
                rvm_id=self.rvm_id,
                callback_proxy=self.callback_proxy,
            ),
        }

    def build_swap_log(
        self, chain_id: int, price_usd: float, amount0: int = -25, amount1: int = 72000, tx_hash: int = 0xABC101
    ) -> LogRecord:
        price_x96 = int(round(price_usd * 1_000_000))
        data = encode_int256(amount0) + encode_int256(amount1) + encode_uint256(price_x96)
        return LogRecord(
            chain_id=chain_id,
            _contract="0xPoolAddress000000000000000000000000000001",
            topic_0=TOPIC_UNISWAP_SWAP,
            data=data,
            block_number=4_912_010,
            tx_hash=tx_hash,
        )

    def build_ai_telemetry_log(
        self, chain_id: int, ai_risk_bps: int, velocity_bps: int, tx_hash: int = 0xDEF202
    ) -> LogRecord:
        data = encode_uint256(ai_risk_bps) + encode_uint256(velocity_bps)
        return LogRecord(
            chain_id=chain_id,
            _contract="0xAiRiskOracleAddress0000000000000000000002",
            topic_0=TOPIC_AI_RISK_TELEMETRY,
            data=data,
            block_number=4_912_015,
            tx_hash=tx_hash,
        )

    def react_and_relay(self, log: LogRecord) -> list[dict[str, Any]]:
        """
        Executes `OmniPulseReactiveSentinel.react(log)` in the RVM and automatically relays
        any emitted `Callback` events to the target destination chain vault.
        """
        callbacks: list[CallbackEvent] = []

        if log.topic_0 == TOPIC_UNISWAP_SWAP and len(log.data) >= 96:
            sqrt_price_x96 = decode_uint256(log.data[64:96])
            if log.chain_id == UNICHAIN_SEPOLIA_CHAIN_ID:
                self.last_unichain_price_x96 = sqrt_price_x96
            elif log.chain_id == BASE_SEPOLIA_CHAIN_ID:
                self.last_base_price_x96 = sqrt_price_x96

            # 1. Stop-Loss Threshold Check
            if 0 < sqrt_price_x96 <= self.stop_loss_price_x96:
                drop_bps = (
                    (self.stop_loss_price_x96 - sqrt_price_x96) * 10000
                ) // self.stop_loss_price_x96
                callbacks.append(
                    self._make_callback(
                        log.chain_id,
                        log.chain_id,
                        ACTION_STOP_LOSS_EXIT,
                        drop_bps + 500,
                        log.tx_hash,
                    )
                )
            else:
                # 2. Cross-Chain Price Divergence Check
                high = max(self.last_unichain_price_x96, self.last_base_price_x96)
                low = max(1, min(self.last_unichain_price_x96, self.last_base_price_x96))
                spread_bps = ((high - low) * 10000) // low
                if spread_bps >= self.divergence_threshold_bps:
                    target_chain = (
                        BASE_SEPOLIA_CHAIN_ID
                        if log.chain_id == UNICHAIN_SEPOLIA_CHAIN_ID
                        else UNICHAIN_SEPOLIA_CHAIN_ID
                    )
                    callbacks.append(
                        self._make_callback(
                            log.chain_id,
                            target_chain,
                            ACTION_CROSS_CHAIN_HEDGE,
                            spread_bps,
                            log.tx_hash,
                        )
                    )

        elif log.topic_0 == TOPIC_AI_RISK_TELEMETRY and len(log.data) >= 64:
            ai_risk_bps = decode_uint256(log.data[0:32])
            velocity_bps = decode_uint256(log.data[32:64])
            composite = (ai_risk_bps * 70 + velocity_bps * 30) // 100
            if composite >= self.ai_circuit_breaker_bps:
                callbacks.append(
                    self._make_callback(
                        log.chain_id,
                        UNICHAIN_SEPOLIA_CHAIN_ID,
                        ACTION_CIRCUIT_BREAKER_PAUSE,
                        composite,
                        log.tx_hash,
                    )
                )
                callbacks.append(
                    self._make_callback(
                        log.chain_id,
                        BASE_SEPOLIA_CHAIN_ID,
                        ACTION_CIRCUIT_BREAKER_PAUSE,
                        composite,
                        log.tx_hash,
                    )
                )

        # Relay emitted callbacks to destination vaults (with Reactive Network RVM ID overwrite)
        execution_receipts: list[dict[str, Any]] = []
        for cb in callbacks:
            receipt = self._deliver_callback_to_vault(cb)
            execution_receipts.append(receipt)
        return execution_receipts

    def _make_callback(
        self,
        origin_chain: int,
        dest_chain: int,
        action_type: int,
        severity_bps: int,
        origin_tx_hash: int,
    ) -> CallbackEvent:
        self.total_reactive_triggers += 1
        vault = self.vaults[dest_chain]
        selector = compute_function_selector(
            "executeReactiveAction(address,uint256,uint8,uint256,bytes32)"
        )
        # First 32-byte slot is overwritten by Reactive Network with `self.rvm_id`
        payload_hex = (
            selector
            + self.rvm_id[2:].lower().rjust(64, "0")
            + encode_uint256(origin_chain).hex()
            + encode_uint256(action_type).hex()
            + encode_uint256(severity_bps).hex()
            + encode_uint256(origin_tx_hash).hex()
        )
        return CallbackEvent(
            chain_id=dest_chain,
            _contract=vault.vault_address,
            gas_limit=450_000,
            payload_hex=payload_hex,
            decoded_args={
                "rvm_id": self.rvm_id,
                "origin_chain_id": origin_chain,
                "action_type": action_type,
                "action_name": ACTION_NAMES[action_type],
                "severity_bps": severity_bps,
                "origin_tx_hash": f"0x{origin_tx_hash:064x}",
            },
        )

    def _deliver_callback_to_vault(self, cb: CallbackEvent) -> dict[str, Any]:
        vault = self.vaults[cb.chain_id]
        args = cb.decoded_args
        if args["rvm_id"] != vault.rvm_id:
            raise PermissionError("OmniPulseCallback: invalid RVM ID payload argument")

        vault.total_callbacks_executed += 1
        act = args["action_type"]
        protected_usdc = 0.0

        if act == ACTION_STOP_LOSS_EXIT:
            unwind = vault.volatile_collateral_eth
            vault.volatile_collateral_eth = 0.0
            protected_usdc = round(unwind * 2850.0, 2)
            vault.stable_reserve_usdc += protected_usdc
        elif act == ACTION_CROSS_CHAIN_HEDGE:
            slice_eth = round(vault.volatile_collateral_eth * 0.40, 4)
            vault.volatile_collateral_eth -= slice_eth
            protected_usdc = round(slice_eth * 2910.0, 2)
            vault.stable_reserve_usdc += protected_usdc
        elif act == ACTION_CIRCUIT_BREAKER_PAUSE:
            vault.circuit_breaker_paused = True
            protected_usdc = round(
                vault.stable_reserve_usdc + vault.volatile_collateral_eth * 2880.0, 2
            )

        entry = {
            "dest_chain_id": cb.chain_id,
            "origin_chain_id": args["origin_chain_id"],
            "action_type": act,
            "action_name": args["action_name"],
            "severity_bps": args["severity_bps"],
            "origin_tx_hash": args["origin_tx_hash"],
            "protected_value_usdc": protected_usdc,
            "reactive_cometbft_latency_ms": 840,
            "callback_payload_prefix": cb.payload_hex[:42] + "...",
        }
        vault.audit_log.append(entry)
        return entry


if __name__ == "__main__":
    sim = ReactiveLoopSimulator()
    # 1. Cross-Chain Divergence Event on Unichain Sepolia (1301) -> Triggers Hedge Callback on Base Sepolia (84532)
    r1 = sim.react_and_relay(sim.build_swap_log(UNICHAIN_SEPOLIA_CHAIN_ID, price_usd=2945.0, tx_hash=0x1001))
    # 2. Stop-Loss Flash Crash on Base Sepolia (84532) -> Triggers Stop-Loss Exit on Base Sepolia (84532)
    r2 = sim.react_and_relay(sim.build_swap_log(BASE_SEPOLIA_CHAIN_ID, price_usd=2590.0, tx_hash=0x1002))
    # 3. AI Flash-Loan Manipulation Alert -> Triggers Dual-Chain Circuit Breaker on 1301 & 84532
    telem = compute_ai_risk_telemetry(price_drop_pct=9.5, volume_spike_sigma=5.4, cross_chain_spread_bps=240, mempool_sandwich_density=0.88)
    r3 = sim.react_and_relay(
        sim.build_ai_telemetry_log(
            UNICHAIN_SEPOLIA_CHAIN_ID,
            telem["ai_risk_score_bps"],
            telem["velocity_sigma_bps"],
            tx_hash=0x1003,
        )
    )
    print("=== OmniPulse Reactive Loop Simulation Complete ===")
    print(f"Total Reactive Triggers Dispatched : {sim.total_reactive_triggers}")
    print(f"Step 1 Cross-Chain Hedge Receipt   : {r1[0]['action_name']} -> Protected ${r1[0]['protected_value_usdc']:,.2f}")
    print(f"Step 2 Stop-Loss Unwind Receipt    : {r2[0]['action_name']} -> Protected ${r2[0]['protected_value_usdc']:,.2f}")
    print(f"Step 3 AI Dual-Chain Circuit Break : {len(r3)} chains isolated (Prob={telem['manipulation_probability_pct']}%)")
