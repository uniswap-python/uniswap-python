import enum
import logging
from typing import final, Final, Optional

from .exceptions import InvalidFeeTier

logger: Final = logging.getLogger(__name__)


@final
@enum.unique
class FeeTier(enum.IntEnum):
    """
    Available fee tiers represented as 1e-6 percentages (i.e. 0.5% is 5000)

    V1 supports only 0.3% fee tier.
    V2 supports only 0.3% fee tier.
    V3 supports 1%, 0.3%, 0.05%, and 0.01% fee tiers.

    Reference: https://support.uniswap.org/hc/en-us/articles/20904283758349-What-are-fee-tiers
    """

    TIER_100 = 100
    TIER_500 = 500
    TIER_3000 = 3000
    TIER_10000 = 10000


def validate_fee_tier(fee: Optional[int], version: int) -> int:
    """
    Validate fee tier for a given Uniswap version.
    """
    if version == 3 and fee is None:
        raise InvalidFeeTier(
            """
            Explicit fee tier is required for Uniswap V3. Refer to the following link for more information:
            https://support.uniswap.org/hc/en-us/articles/20904283758349-What-are-fee-tiers
            """
        )
    if fee is None:
        fee = FeeTier.TIER_3000

    if version < 3 and fee != FeeTier.TIER_3000:
        raise InvalidFeeTier(
            f"Unsupported fee tier {fee} for Uniswap V{version}. Choices are: {FeeTier.TIER_3000}"
        )
    try:
        return FeeTier(fee).value
    except ValueError as exc:
        raise InvalidFeeTier(
            f"Invalid fee tier {fee} for Uniswap V{version}. Choices are: {FeeTier._value2member_map_.keys()}"
        ) from exc
