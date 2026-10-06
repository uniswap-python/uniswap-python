"""Offline arithmetic regressions on imported classes; no RPC or transactions."""

from decimal import Decimal, localcontext
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
from web3 import Web3

from uniswap import Uniswap, Uniswap4
import uniswap.uniswap as module

TOKEN0 = "0x0000000000000000000000000000000000000001"
TOKEN1 = "0x0000000000000000000000000000000000000002"


@pytest.fixture
def clients(monkeypatch):
    state = NS(q=2**96, decimals=(18, 6), low=0, high=1, fee=100)
    pool = Mock()
    pool.functions.token1.return_value.call.return_value = TOKEN1
    pool.functions.slot0.return_value.call.side_effect = lambda: (state.q,)
    pool.functions.ticks.return_value._encode_transaction_data.return_value = "0x00"
    monkeypatch.setattr(module, "_load_contract", lambda *a, **k: pool)
    erc20 = Mock()
    erc20.functions.decimals.return_value.call.return_value = 0
    monkeypatch.setattr(module, "_load_contract_erc20", lambda *a, **k: erc20)
    v3 = object.__new__(Uniswap)
    v3.version = 3
    v3.w3 = Web3()
    v3.factory_contract = Mock()
    v3.factory_contract.functions.getPool.return_value.call.return_value = TOKEN0
    v4 = object.__new__(Uniswap4)
    for client in (v3, v4):
        setattr(
            client,
            "get_token",
            lambda token: NS(
                decimals=state.decimals[
                    0 if Web3.to_checksum_address(token).lower() == TOKEN0 else 1
                ]
            ),
        )
    setattr(v4, "stateview_get_slot0", lambda *a: {"sqrtPriceX96": state.q})
    setattr(
        v3,
        "get_pool_immutables",
        lambda p: {"fee": state.fee, "token0": TOKEN0, "token1": TOKEN1},
    )
    setattr(v3, "get_pool_state", lambda p: {"sqrtPriceX96": state.q})
    setattr(v3, "find_tick_from_bitmap", lambda *a: state.high if a[-1] else state.low)
    setattr(v3, "multicall", lambda batch, types: [(0, 10**30)] * len(batch))
    return state, pool, v3, v4


@pytest.mark.parametrize(
    "target,decimals",
    [
        ("0.00000987", (18, 6)),
        ("0.00000049", (18, 6)),
        ("1.23456789", (6, 18)),
        ("1e-24", (18, 18)),
    ],
)
@pytest.mark.parametrize("version", [3, 4])
@pytest.mark.parametrize("reverse", [False, True])
def test_low_price_and_reciprocal(clients, target, decimals, version, reverse):
    state, _, v3, v4 = clients
    state.decimals = decimals
    with localcontext() as ctx:
        ctx.prec = 100
        scale = Decimal(10) ** (decimals[0] - decimals[1])
        state.q = int((Decimal(target) / scale).sqrt() * 2**96)
        expected = Decimal(state.q**2) / Decimal(2**192) * scale
        if reverse:
            expected = 1 / expected
        tokens = (TOKEN1, TOKEN0) if reverse else (TOKEN0, TOKEN1)
        method = v3.get_raw_price if version == 3 else v4.get_token_token_spot_price
        actual = method(*tokens, 100)
        assert isinstance(actual, float)
        assert actual > 0
        assert abs(Decimal.from_float(actual) / expected - 1) < Decimal("5e-16")


@pytest.mark.parametrize(
    "q", [4295128739, 1461446703485210103287273052203988822378723970341]
)
@pytest.mark.parametrize("version", [3, 4])
@pytest.mark.parametrize("reverse", [False, True])
def test_sqrt_price_boundaries(clients, q, version, reverse):
    state, _, v3, v4 = clients
    state.q, state.decimals = q, (18, 18)
    with localcontext() as ctx:
        ctx.prec = 100
        expected = Decimal(q**2) / Decimal(2**192)
        if reverse:
            expected = 1 / expected
        tokens = (TOKEN1, TOKEN0) if reverse else (TOKEN0, TOKEN1)
        method = v3.get_raw_price if version == 3 else v4.get_token_token_spot_price
        actual = method(*tokens, 100)
        assert actual > 0
        assert abs(Decimal.from_float(actual) / expected - 1) < Decimal("5e-16")


@pytest.mark.parametrize(
    "low,high,fee",
    [
        (0, 1, 100),
        (1, 2, 100),
        (-1, 0, 100),
        (0, 60, 3000),
        (-887271, -887270, 100),
        (887270, 887271, 100),
    ],
)
@pytest.mark.parametrize("position", ["below", "inside", "above"])
def test_tick_amounts(clients, low, high, fee, position):
    state, pool, v3, _ = clients
    state.low, state.high, state.fee = low, high, fee
    with localcontext() as ctx:
        ctx.prec = 100
        a = Decimal("1.0001") ** (Decimal(low) / 2)
        b = Decimal("1.0001") ** (Decimal(high) / 2)
        desired = {"below": a / 2, "inside": (a + b) / 2, "above": b * 2}[position]
        state.q = int(desired * 2**96)
        current = Decimal(state.q) / Decimal(2**96)
        clamped = max(min(current, b), a)
        expected = (
            Decimal(10**30) * (b - clamped) / (clamped * b),
            Decimal(10**30) * (clamped - a),
        )
        actual = v3.get_tvl_in_pool(pool)
        for amount, reference in zip(actual, expected):
            if reference == 0:
                assert amount == 0
            else:
                assert amount > 0
                # Existing float exponent rounding is amplified near extreme ticks;
                # whole-token flooring is retained. This is not exact TickMath parity.
                tolerance = "2e-6" if abs(low) > 887000 else "1e-9"
                assert abs(Decimal.from_float(amount) / reference - 1) < Decimal(
                    tolerance
                )
