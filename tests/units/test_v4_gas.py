"""Offline gas-limit regressions for the V4 clients; no RPC or transactions."""

import asyncio
from unittest.mock import AsyncMock, Mock, PropertyMock

import pytest
from web3.types import Nonce

from uniswap import AsyncUniswap4, Uniswap4
from uniswap.util import _str_to_addr

ADDRESS = "0x0000000000000000000000000000000000000001"
# A modifyLiquidities call creating storage after the Glamsterdam gas repricing
# measured 324,645-443,172 gas; the old fixed default was 250,000.
ESTIMATE = 443_172


def _sync_client(gas_limit):
    client = object.__new__(Uniswap4)
    client.address = _str_to_addr(ADDRESS)
    client.private_key = "0x" + "11" * 32
    client.gas_limit = gas_limit
    client.gas_price = 1.8
    client.priority_fee = 1.0
    client.post_merge = True
    client.last_nonce = Nonce(7)
    client.w3 = Mock()
    client.w3.eth.chain_id = 1
    return client


def _function(estimate=ESTIMATE, is_async=False):
    function = Mock()
    if is_async:
        function.estimate_gas = AsyncMock(return_value=estimate)
        function.build_transaction = AsyncMock(side_effect=dict)
    else:
        function.estimate_gas.return_value = estimate
        function.build_transaction.side_effect = dict
    return function


@pytest.mark.parametrize("post_merge", [True, False])
def test_sync_estimates_gas_by_default(post_merge):
    client = _sync_client(gas_limit=None)
    client.post_merge = post_merge
    function = _function()

    client._build_and_send_tx(function)

    estimate_args = function.estimate_gas.call_args.args[0]
    assert "gas" not in estimate_args and "nonce" not in estimate_args
    built = function.build_transaction.call_args.args[0]
    assert built["gas"] == int(ESTIMATE * 1.2)
    assert built["nonce"] == 7
    assert client.last_nonce == 8


def test_sync_fixed_gas_limit_overrides_estimate():
    client = _sync_client(gas_limit=500_000)
    function = _function()

    client._build_and_send_tx(function)

    function.estimate_gas.assert_not_called()
    assert function.build_transaction.call_args.args[0]["gas"] == 500_000


def test_sync_set_gas_limit_none_restores_estimation():
    client = _sync_client(gas_limit=500_000)
    client.set_gas_limit(None)
    function = _function()

    client._build_and_send_tx(function)

    assert client.get_gas_limit() is None
    assert function.build_transaction.call_args.args[0]["gas"] == int(ESTIMATE * 1.2)


def test_sync_drop_txn_estimates_transfer_gas():
    client = _sync_client(gas_limit=None)
    client.w3.eth.estimate_gas.return_value = 21_000
    client.w3.eth.get_transaction_count.return_value = 7

    client.drop_txn(ADDRESS, gas_price=10)

    signed = [c.args[0] for c in client.w3.eth.account.sign_transaction.call_args_list]
    assert [tx["gas"] for tx in signed] == [21_000, 21_000]


def _async_client(gas_limit):
    client = object.__new__(AsyncUniswap4)
    client.address = _str_to_addr(ADDRESS)
    client.private_key = "0x" + "11" * 32
    client.gas_limit = gas_limit
    client.gas_price = 1.8
    client.priority_fee = 1.0
    client.post_merge = True
    client.last_nonce = Nonce(7)
    client._nonce_lock = asyncio.Lock()
    client.w3 = Mock()
    # Each access returns a fresh awaitable, like AsyncWeb3's chain_id property.
    type(client.w3.eth).chain_id = PropertyMock(
        side_effect=lambda: asyncio.sleep(0, result=1)
    )
    client.w3.eth.send_raw_transaction = AsyncMock(return_value=b"")
    return client


def test_async_estimates_gas_by_default():
    client = _async_client(gas_limit=None)
    function = _function(is_async=True)

    asyncio.run(client._build_and_send_tx(function))

    assert "nonce" not in function.estimate_gas.call_args.args[0]
    built = function.build_transaction.call_args.args[0]
    assert built["gas"] == int(ESTIMATE * 1.2)
    assert client.last_nonce == 8


def test_async_fixed_gas_limit_overrides_estimate():
    client = _async_client(gas_limit=500_000)
    function = _function(is_async=True)

    asyncio.run(client._build_and_send_tx(function))

    function.estimate_gas.assert_not_called()
    assert function.build_transaction.call_args.args[0]["gas"] == 500_000


def test_sync_failed_estimate_keeps_nonce():
    client = _sync_client(gas_limit=None)
    failing = _function()
    failing.estimate_gas.side_effect = ValueError("execution reverted")

    with pytest.raises(ValueError):
        client._build_and_send_tx(failing)
    client._build_and_send_tx(function := _function())

    assert function.build_transaction.call_args.args[0]["nonce"] == 7
    assert client.last_nonce == 8


def test_async_failed_estimate_keeps_nonce():
    client = _async_client(gas_limit=None)
    failing = _function(is_async=True)
    failing.estimate_gas.side_effect = ValueError("execution reverted")

    with pytest.raises(ValueError):
        asyncio.run(client._build_and_send_tx(failing))
    asyncio.run(client._build_and_send_tx(function := _function(is_async=True)))

    assert function.build_transaction.call_args.args[0]["nonce"] == 7
    assert client.last_nonce == 8
