// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IReactive.sol";

/**
 * @title AbstractReactive
 * @notice Base abstract contract for Reactive Network contracts on Lasna / Kopli Testnet.
 *         Distinguishes between the Reactive Network System Contract environment (`rnOnly`)
 *         and the isolated Reactive Virtual Machine execution environment (`vmOnly`).
 */
abstract contract AbstractReactive is IReactive {
    uint256 internal constant REACTIVE_IGNORE = 0xa65f96fc951c35ead38878e0f0b7a3c744a6f5ccc1476b313353ce31712313ad;
    address internal constant SERVICE_ADDR = 0x0000000000000000000000000000000000fffFfF;

    ISubscriptionService internal service;
    bool internal vm;

    constructor() {
        service = ISubscriptionService(SERVICE_ADDR);
        uint256 size;
        assembly {
            size := extcodesize(0x0000000000000000000000000000000000fffFfF)
        }
        vm = (size == 0);
    }

    modifier rnOnly() {
        require(!vm, "OmniPulse: Reactive Network only");
        _;
    }

    modifier vmOnly() {
        require(vm, "OmniPulse: RVM instance only");
        _;
    }
}
