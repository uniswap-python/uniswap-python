"""Offline checks for the tick helpers; no RPC or transactions."""

import pytest

from uniswap.constants import MAX_TICK, MIN_TICK
from uniswap.util import get_sqrt_ratio_at_tick, get_tick_at_sqrt


# (sqrtPriceX96, tick) pairs as returned by slot0() of mainnet v3 pools at block 26512111
@pytest.mark.parametrize(
    "sqrt_price_x96,tick",
    [
        (1947237970984315364528431785343873, 202201),  # USDC/WETH 0.05%
        (1947195717021086193266098206201374, 202201),  # USDC/WETH 0.3%
        (79232054176599129078773, -276324),  # DAI/USDC 0.01%
        (3225138538977047301064859, -202193),  # WETH/USDT 0.05%
        (79266096416521611302971912177, 9),  # USDC/USDT 0.01%
        (47602837567296889508681069119209768, 266134),  # WBTC/WETH 0.05%
    ],
)
def test_get_tick_at_sqrt_matches_slot0(sqrt_price_x96: int, tick: int) -> None:
    assert get_tick_at_sqrt(sqrt_price_x96) == tick


@pytest.mark.parametrize(
    "tick", [MIN_TICK, -276324, -887, -1, 0, 1, 9, 202201, MAX_TICK - 1]
)
def test_get_tick_at_sqrt_floors_within_tick(tick: int) -> None:
    lower = get_sqrt_ratio_at_tick(tick)
    upper = get_sqrt_ratio_at_tick(tick + 1)
    assert get_tick_at_sqrt(lower) == tick
    assert get_tick_at_sqrt((lower + upper) // 2) == tick
    assert get_tick_at_sqrt(upper - 1) == tick
