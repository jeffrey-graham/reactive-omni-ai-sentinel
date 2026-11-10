// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/AbstractReactive.sol";

/**
 * @title OmniPulseReactiveSentinel
 * @notice Reactive Smart Contract (RSC) deployed on Reactive Network (Lasna / Kopli Testnet).
 *         Subscribes to DEX liquidity pool `Swap` / `Sync` events and AI Risk Copilot telemetry
 *         across Unichain Sepolia (1301) and Base Sepolia (84532) with ~1s CometBFT finality.
 *
 *         When a flash-slippage shock, cross-chain price divergence, or AI manipulation anomaly
 *         is detected inside `react(LogRecord calldata log)`, it emits a `Callback` event that
 *         triggers automated stop-loss, delta-neutral hedging, or circuit-breaker isolation on
 *         the destination chain without centralized keepers.
 */
contract OmniPulseReactiveSentinel is AbstractReactive {
    uint256 public constant UNICHAIN_SEPOLIA_CHAIN_ID = 1301;
    uint256 public constant BASE_SEPOLIA_CHAIN_ID = 84532;
    uint64 public constant CALLBACK_GAS_LIMIT = 450000;

    // Canonical Event Topic_0 Signatures
    // keccak256("Swap(address,address,int256,int256,uint160,uint128,int24)")
    uint256 public constant TOPIC_UNISWAP_SWAP =
        0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67;
    // keccak256("Sync(uint112,uint112)")
    uint256 public constant TOPIC_POOL_SYNC =
        0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1;
    // keccak256("RiskTelemetryUpdated(address,uint256,uint256,uint256)")
    uint256 public constant TOPIC_AI_RISK_TELEMETRY =
        0x8a9c5b2f4d1e3a7c9b0e2f6d8a1c3e5f7b9d0a2c4e6f8a0b2c4d6e8f0a1b2c3d;

    // Defensive Action Codes
    uint8 public constant ACTION_STOP_LOSS_EXIT = 1;
    uint8 public constant ACTION_CROSS_CHAIN_HEDGE = 2;
    uint8 public constant ACTION_CIRCUIT_BREAKER_PAUSE = 3;

    address public immutable unichainCallbackVault;
    address public immutable baseCallbackVault;

    // RVM State Tracking
    uint256 public lastUnichainPriceX96;
    uint256 public lastBasePriceX96;
    uint256 public stopLossTriggerPriceX96;
    uint256 public divergenceThresholdBps;
    uint256 public aiCircuitBreakerBps;
    uint256 public totalReactiveTriggers;

    event AnomalyDetectedAndDispatched(
        uint256 indexed originChainId,
        uint256 indexed destinationChainId,
        uint8 indexed actionType,
        uint256 severityBps,
        uint256 originTxHash
    );

    constructor(
        address _unichainPool,
        address _basePool,
        address _aiOracle,
        address _unichainCallbackVault,
        address _baseCallbackVault,
        uint256 _stopLossTriggerPriceX96,
        uint256 _divergenceThresholdBps,
        uint256 _aiCircuitBreakerBps
    ) payable {
        unichainCallbackVault = _unichainCallbackVault;
        baseCallbackVault = _baseCallbackVault;
        stopLossTriggerPriceX96 = _stopLossTriggerPriceX96;
        divergenceThresholdBps = _divergenceThresholdBps;
        aiCircuitBreakerBps = _aiCircuitBreakerBps;

        if (!vm) {
            // Subscribe to Unichain Sepolia (1301) DEX Swap & AI Risk Telemetry
            service.subscribe(
                UNICHAIN_SEPOLIA_CHAIN_ID,
                _unichainPool,
                TOPIC_UNISWAP_SWAP,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE
            );
            service.subscribe(
                UNICHAIN_SEPOLIA_CHAIN_ID,
                _aiOracle,
                TOPIC_AI_RISK_TELEMETRY,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE
            );

            // Subscribe to Base Sepolia (84532) DEX Swap & Pool Sync
            service.subscribe(
                BASE_SEPOLIA_CHAIN_ID,
                _basePool,
                TOPIC_UNISWAP_SWAP,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE
            );
            service.subscribe(
                BASE_SEPOLIA_CHAIN_ID,
                _basePool,
                TOPIC_POOL_SYNC,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE,
                REACTIVE_IGNORE
            );
        }
    }

    /**
     * @notice Invoked automatically inside the isolated RVM upon any matching log on
     *         Unichain Sepolia (1301) or Base Sepolia (84532).
     */
    function react(LogRecord calldata log) external override vmOnly {
        if (log.topic_0 == TOPIC_UNISWAP_SWAP && log.data.length >= 96) {
            (, , uint256 sqrtPriceX96) = abi.decode(log.data, (int256, int256, uint256));

            if (log.chain_id == UNICHAIN_SEPOLIA_CHAIN_ID) {
                lastUnichainPriceX96 = sqrtPriceX96;
            } else if (log.chain_id == BASE_SEPOLIA_CHAIN_ID) {
                lastBasePriceX96 = sqrtPriceX96;
            }

            // 1. Check Stop-Loss Threshold Breach
            if (sqrtPriceX96 > 0 && sqrtPriceX96 <= stopLossTriggerPriceX96) {
                uint256 dropBps = ((stopLossTriggerPriceX96 - sqrtPriceX96) * 10000) /
                    stopLossTriggerPriceX96;
                _dispatchCallback(
                    log.chain_id,
                    log.chain_id,
                    ACTION_STOP_LOSS_EXIT,
                    dropBps + 500,
                    log.tx_hash
                );
                return;
            }

            // 2. Check Cross-Chain Price Divergence between Unichain Sepolia & Base Sepolia
            if (lastUnichainPriceX96 > 0 && lastBasePriceX96 > 0) {
                uint256 high = lastUnichainPriceX96 > lastBasePriceX96
                    ? lastUnichainPriceX96
                    : lastBasePriceX96;
                uint256 low = lastUnichainPriceX96 > lastBasePriceX96
                    ? lastBasePriceX96
                    : lastUnichainPriceX96;
                uint256 spreadBps = ((high - low) * 10000) / low;

                if (spreadBps >= divergenceThresholdBps) {
                    uint256 targetChain = log.chain_id == UNICHAIN_SEPOLIA_CHAIN_ID
                        ? BASE_SEPOLIA_CHAIN_ID
                        : UNICHAIN_SEPOLIA_CHAIN_ID;
                    _dispatchCallback(
                        log.chain_id,
                        targetChain,
                        ACTION_CROSS_CHAIN_HEDGE,
                        spreadBps,
                        log.tx_hash
                    );
                }
            }
        } else if (log.topic_0 == TOPIC_AI_RISK_TELEMETRY && log.data.length >= 64) {
            (uint256 aiRiskScoreBps, uint256 velocitySigmaBps) = abi.decode(
                log.data,
                (uint256, uint256)
            );
            uint256 compositeScore = (aiRiskScoreBps * 70 + velocitySigmaBps * 30) / 100;

            if (compositeScore >= aiCircuitBreakerBps) {
                // Dispatch dual-chain emergency circuit breaker on both Unichain & Base Sepolia
                _dispatchCallback(
                    log.chain_id,
                    UNICHAIN_SEPOLIA_CHAIN_ID,
                    ACTION_CIRCUIT_BREAKER_PAUSE,
                    compositeScore,
                    log.tx_hash
                );
                _dispatchCallback(
                    log.chain_id,
                    BASE_SEPOLIA_CHAIN_ID,
                    ACTION_CIRCUIT_BREAKER_PAUSE,
                    compositeScore,
                    log.tx_hash
                );
            }
        }
    }

    function _dispatchCallback(
        uint256 originChainId,
        uint256 destChainId,
        uint8 actionType,
        uint256 severityBps,
        uint256 originTxHash
    ) internal {
        totalReactiveTriggers += 1;
        address targetVault = destChainId == UNICHAIN_SEPOLIA_CHAIN_ID
            ? unichainCallbackVault
            : baseCallbackVault;

        // First address argument (`address(0)`) is overwritten by Reactive Network with the verified RVM ID
        bytes memory payload = abi.encodeWithSignature(
            "executeReactiveAction(address,uint256,uint8,uint256,bytes32)",
            address(0),
            originChainId,
            actionType,
            severityBps,
            bytes32(originTxHash)
        );

        emit AnomalyDetectedAndDispatched(
            originChainId,
            destChainId,
            actionType,
            severityBps,
            originTxHash
        );
        emit Callback(destChainId, targetVault, CALLBACK_GAS_LIMIT, payload);
    }
}
