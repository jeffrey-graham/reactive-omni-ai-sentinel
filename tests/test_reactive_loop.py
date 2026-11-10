#!/usr/bin/env python3
"""
Unit & Integration Test Suite for OmniPulse Reactive Sentinel & AI Risk Copilot.
Run with: python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.ai_risk_copilot import (
    ACTION_CIRCUIT_BREAKER_PAUSE,
    ACTION_CROSS_CHAIN_HEDGE,
    ACTION_STOP_LOSS_EXIT,
    BASE_SEPOLIA_CHAIN_ID,
    UNICHAIN_SEPOLIA_CHAIN_ID,
    ReactiveLoopSimulator,
    compute_ai_risk_telemetry,
)


class TestOmniPulseReactiveLoop(unittest.TestCase):
    def test_cross_chain_divergence_triggers_hedge_callback(self) -> None:
        sim = ReactiveLoopSimulator(
            stop_loss_price_usd=2650.0,
            divergence_threshold_bps=120,
            ai_circuit_breaker_bps=8000,
        )
        # Baseline is $2,880 on both chains. A jump to $2,945 on Unichain Sepolia (1301)
        # creates a 225 bps cross-chain spread (>= 120 bps threshold) -> triggers hedge on Base Sepolia (84532)
        log = sim.build_swap_log(UNICHAIN_SEPOLIA_CHAIN_ID, price_usd=2945.0, tx_hash=0xAA01)
        receipts = sim.react_and_relay(log)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["origin_chain_id"], UNICHAIN_SEPOLIA_CHAIN_ID)
        self.assertEqual(receipts[0]["dest_chain_id"], BASE_SEPOLIA_CHAIN_ID)
        self.assertEqual(receipts[0]["action_type"], ACTION_CROSS_CHAIN_HEDGE)
        self.assertGreater(receipts[0]["protected_value_usdc"], 100_000.0)

    def test_stop_loss_breach_triggers_autonomous_collateral_unwind(self) -> None:
        sim = ReactiveLoopSimulator(stop_loss_price_usd=2650.0)
        log = sim.build_swap_log(BASE_SEPOLIA_CHAIN_ID, price_usd=2580.0, tx_hash=0xBB02)
        receipts = sim.react_and_relay(log)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["action_type"], ACTION_STOP_LOSS_EXIT)
        self.assertEqual(sim.vaults[BASE_SEPOLIA_CHAIN_ID].volatile_collateral_eth, 0.0)
        self.assertGreater(sim.vaults[BASE_SEPOLIA_CHAIN_ID].stable_reserve_usdc, 400_000.0)

    def test_ai_risk_copilot_triggers_dual_chain_circuit_breaker(self) -> None:
        sim = ReactiveLoopSimulator(ai_circuit_breaker_bps=8000)
        telem = compute_ai_risk_telemetry(
            price_drop_pct=11.0,
            volume_spike_sigma=5.8,
            cross_chain_spread_bps=290,
            mempool_sandwich_density=0.92,
        )
        self.assertTrue(telem["triggers_circuit_breaker"])
        self.assertGreaterEqual(telem["composite_score_bps"], 8000)

        log = sim.build_ai_telemetry_log(
            UNICHAIN_SEPOLIA_CHAIN_ID,
            telem["ai_risk_score_bps"],
            telem["velocity_sigma_bps"],
            tx_hash=0xCC03,
        )
        receipts = sim.react_and_relay(log)
        self.assertEqual(len(receipts), 2)
        self.assertTrue(sim.vaults[UNICHAIN_SEPOLIA_CHAIN_ID].circuit_breaker_paused)
        self.assertTrue(sim.vaults[BASE_SEPOLIA_CHAIN_ID].circuit_breaker_paused)

    def test_solidity_contracts_exist_and_implement_reactive_interfaces(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sentinel_sol = (root / "contracts" / "OmniPulseReactiveSentinel.sol").read_text(encoding="utf-8")
        vault_sol = (root / "contracts" / "OmniPulseCallbackVault.sol").read_text(encoding="utf-8")
        self.assertIn("function react(LogRecord calldata log) external override vmOnly", sentinel_sol)
        self.assertIn("service.subscribe(", sentinel_sol)
        self.assertIn("emit Callback(", sentinel_sol)
        self.assertIn("authorizedSenderOnly rvmIdOnly(_rvmId)", vault_sol)


if __name__ == "__main__":
    unittest.main()
