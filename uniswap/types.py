from typing import Union
from dataclasses import dataclass
from eth_typing.evm import Address, ChecksumAddress
from typing import List, Tuple


AddressLike = Union[Address, ChecksumAddress]

@dataclass
class UniswapV4_slot0:
    sqrtPriceX96: int
    tick: int
    protocolFee: int

    def __repr__(self) -> str:
        return f"Slot0 value (sqrtPriceX96: {self.sqrtPriceX96}; tick: {self.tick}; protocolFee: {self.protocolFee!r})"

@dataclass
class UniswapV4_position_info:
    liquidity: int
    feeGrowthInside0LastX128: int
    feeGrowthInside1LastX128: int

    def __repr__(self) -> str:
        return f"Position info (liquidity: {self.liquidity}; feeGrowthInside0LastX128: {self.feeGrowthInside0LastX128}; feeGrowthInside1LastX128: {self.feeGrowthInside1LastX128!r})"

@dataclass
class UniswapV4_tick_info:
    liquidityGross : int
    liquidityNet : int
    feeGrowthOutside0X128 : int
    feeGrowthOutside1X128 : int
    
    def __repr__(self) -> str:
        return f"Tick info (liquidityGross: {self.liquidityGross}; liquidityNet: {self.liquidityNet}; feeGrowthOutside0X128: {self.feeGrowthOutside0X128}; feeGrowthOutside1X128: {self.feeGrowthOutside1X128!r})"

@dataclass
class UniswapV4_PathKey:
    # The lower currency of the pool, sorted numerically
    currency0 : Address
    # The higher currency of the pool, sorted numerically
    currency1 : Address
    # The pool swap fee, capped at 1_000_000. If the first bit is 1, the pool has a dynamic fee and must be exactly equal to 0x800000
    fee : int
    # Ticks that involve positions must be a multiple of tick spacing
    tickSpacing : int
    # The hooks of the pool
    hooks : List[Address]

    def __repr__(self) -> Tuple[Address, Address, int, int, List[Address]]:
        return (self.currency0, self.currency1, self.fee, self.tickSpacing, self.hooks)