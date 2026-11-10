// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AbstractCallback
 * @notice Base contract for destination-chain contracts (Unichain Sepolia 1301 & Base Sepolia 84532)
 *         receiving authenticated cross-chain callbacks from the Reactive Network Callback Proxy.
 */
abstract contract AbstractCallback {
    address internal rvm_id;
    address internal callback_sender;

    constructor(address _callback_sender) {
        rvm_id = msg.sender;
        callback_sender = _callback_sender;
    }

    modifier authorizedSenderOnly() {
        require(
            callback_sender == address(0) || msg.sender == callback_sender,
            "OmniPulseCallback: unauthorized callback proxy"
        );
        _;
    }

    modifier rvmIdOnly(address _rvm_id) {
        require(
            rvm_id == address(0) || rvm_id == _rvm_id,
            "OmniPulseCallback: invalid RVM ID payload argument"
        );
        _;
    }
}
