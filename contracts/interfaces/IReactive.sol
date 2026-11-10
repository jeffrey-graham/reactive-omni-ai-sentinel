// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IReactive
 * @notice Canonical Reactive Network interface for event-driven Reactive Smart Contracts (RSCs)
 *         operating on Lasna / Kopli Testnet & Reactive Mainnet (~1s CometBFT finality).
 */
interface IReactive {
    struct LogRecord {
        uint256 chain_id;
        address _contract;
        uint256 topic_0;
        uint256 topic_1;
        uint256 topic_2;
        uint256 topic_3;
        bytes data;
        uint256 block_number;
        uint256 op_code;
        uint256 block_hash;
        uint256 tx_hash;
        uint256 log_index;
    }

    event Callback(
        uint256 indexed chain_id,
        address indexed _contract,
        uint64 indexed gas_limit,
        bytes payload
    );

    /**
     * @notice Entry point invoked by the Reactive Virtual Machine (RVM) whenever a subscribed
     *         origin-chain log matches the registered topic/contract filter.
     * @param log The origin-chain event log record captured by Reactive Network validators.
     */
    function react(LogRecord calldata log) external;
}

interface ISubscriptionService {
    function subscribe(
        uint256 chain_id,
        address _contract,
        uint256 topic_0,
        uint256 topic_1,
        uint256 topic_2,
        uint256 topic_3
    ) external;

    function unsubscribe(
        uint256 chain_id,
        address _contract,
        uint256 topic_0,
        uint256 topic_1,
        uint256 topic_2,
        uint256 topic_3
    ) external;
}
