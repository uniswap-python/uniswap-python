from dataclasses import dataclass
from typing import List, Union

from eth_typing.evm import Address, ChecksumAddress

AddressLike = Union[Address, ChecksumAddress]


# Uniswap V4 classes
@dataclass
class PoolKey:
    currency0: str
    currency1: str
    fee: int
    tick_spacing: int
    hooks: str


@dataclass
class PathKey:
    intermediate_currency: str
    fee: int
    tick_spacing: int
    hooks: str
    hook_data: bytes


@dataclass
class PermitDetails:
    token: str
    amount: int
    expiration: int
    nonce: int


@dataclass
class PermitSingle:
    details: PermitDetails
    spender: str
    sig_deadline: int


@dataclass
class PermitBatch:
    details: List[PermitDetails]
    spender: str
    sig_deadline: int


@dataclass
class ModifyLiquidityParams:
    tick_lower: int
    tick_upper: int
    liquidity_delta: int
    salt: int


@dataclass
class SwapParams:
    zero_for_one: bool
    amount_specified: int
    sqrt_price_limit_x96: int
