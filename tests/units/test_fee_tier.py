from typing import Any

import pytest

from uniswap.fee import FeeTier, validate_fee_tier
from uniswap.exceptions import InvalidFeeTier



@pytest.mark.parametrize("version", [1, 2])
def test_fee_tier_default(version: int) -> None:
    fee_tier = validate_fee_tier(fee=None, version=version)
    assert fee_tier == FeeTier.TIER_3000


def test_fee_tier_default_v3() -> None:
    with pytest.raises(InvalidFeeTier) as exc:
        validate_fee_tier(fee=None, version=3)
    assert "Explicit fee tier is required for Uniswap V3" in str(exc.value)


@pytest.mark.parametrize(
    ("fee", "version"),
    [
        (FeeTier.TIER_100, 1),
        (FeeTier.TIER_500, 1),
        (FeeTier.TIER_10000, 1),
        (FeeTier.TIER_100, 2),
        (FeeTier.TIER_500, 2),
        (FeeTier.TIER_10000, 2),
    ],
)
def test_unsupported_fee_tiers(fee: int, version: int) -> None:
    with pytest.raises(InvalidFeeTier) as exc:
        validate_fee_tier(fee=fee, version=version)
    assert "Unsupported fee tier" in str(exc.value)


@pytest.mark.parametrize(
    "invalid_fee",
    [
        "undefined",
        0,
        1_000_000,
        1.1,
        (1, 3),
        type,
    ],
)
def test_invalid_fee_tiers(invalid_fee: Any) -> None:
    with pytest.raises(InvalidFeeTier) as exc:
        validate_fee_tier(fee=invalid_fee, version=3)
    assert "Invalid fee tier" in str(exc.value)
