// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/AbstractCallback.sol";

/**
 * @title OmniPulseCallbackVault
 * @notice Destination-chain autonomous DeFi vault deployed on Unichain Sepolia (1301)
 *         and Base Sepolia (84532). Receives authenticated callbacks emitted by
 *         `OmniPulseReactiveSentinel` on the Reactive Network and executes atomic
 *         stop-loss unwinding, cross-chain hedge rebalancing, or emergency circuit-breaker pauses.
 */
contract OmniPulseCallbackVault is AbstractCallback {
    uint8 public constant ACTION_STOP_LOSS_EXIT = 1;
    uint8 public constant ACTION_CROSS_CHAIN_HEDGE = 2;
    uint8 public constant ACTION_CIRCUIT_BREAKER_PAUSE = 3;

    bool public circuitBreakerPaused;
    uint256 public volatileCollateralWei;
    uint256 public stableReserveUsdc6;
    uint256 public totalCallbacksExecuted;
    bytes32 public lastProcessedOriginTx;

    struct ExecutionAudit {
        uint256 timestamp;
        uint256 originChainId;
        uint8 actionType;
        uint256 severityBps;
        bytes32 originTxHash;
        uint256 protectedValueUsdc6;
    }

    ExecutionAudit[] public auditLog;

    event ReactiveProtectionExecuted(
        address indexed rvmId,
        uint256 indexed originChainId,
        uint8 indexed actionType,
        uint256 severityBps,
        bytes32 originTxHash,
        uint256 protectedValueUsdc6
    );

    constructor(
        address _callbackProxy,
        uint256 _initialCollateralWei,
        uint256 _initialStableUsdc6
    ) AbstractCallback(_callbackProxy) payable {
        volatileCollateralWei = _initialCollateralWei;
        stableReserveUsdc6 = _initialStableUsdc6;
    }

    /**
     * @notice Invoked exclusively by the Reactive Network Callback Proxy.
     *         The first argument `_rvmId` is overwritten by the Reactive Network with the
     *         deployer's RVM ID to prevent spoofing.
     */
    function executeReactiveAction(
        address _rvmId,
        uint256 originChainId,
        uint8 actionType,
        uint256 severityBps,
        bytes32 originTxHash
    ) external authorizedSenderOnly rvmIdOnly(_rvmId) {
        totalCallbacksExecuted += 1;
        lastProcessedOriginTx = originTxHash;
        uint256 protectedUsdc = 0;

        if (actionType == ACTION_STOP_LOSS_EXIT) {
            // Unwind 100% of volatile WETH collateral into stable USDC reserve
            uint256 unwindWei = volatileCollateralWei;
            volatileCollateralWei = 0;
            protectedUsdc = (unwindWei * 2850) / 1e12; // 18-dec wei to 6-dec USDC at $2,850/ETH
            stableReserveUsdc6 += protectedUsdc;
        } else if (actionType == ACTION_CROSS_CHAIN_HEDGE) {
            // Rebalance 40% of exposed liquidity to capture cross-chain spread and neutralize delta
            uint256 hedgeSlice = (volatileCollateralWei * 40) / 100;
            volatileCollateralWei -= hedgeSlice;
            protectedUsdc = (hedgeSlice * 2910) / 1e12;
            stableReserveUsdc6 += protectedUsdc;
        } else if (actionType == ACTION_CIRCUIT_BREAKER_PAUSE) {
            // Isolate vault immediately upon AI flash-manipulation alert
            circuitBreakerPaused = true;
            protectedUsdc = stableReserveUsdc6 + ((volatileCollateralWei * 2880) / 1e12);
        }

        auditLog.push(
            ExecutionAudit({
                timestamp: block.timestamp,
                originChainId: originChainId,
                actionType: actionType,
                severityBps: severityBps,
                originTxHash: originTxHash,
                protectedValueUsdc6: protectedUsdc
            })
        );

        emit ReactiveProtectionExecuted(
            _rvmId,
            originChainId,
            actionType,
            severityBps,
            originTxHash,
            protectedUsdc
        );
    }

    function getAuditLogLength() external view returns (uint256) {
        return auditLog.length;
    }
}
