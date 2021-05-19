from dataclasses import dataclass
from .types import AddressLike


@dataclass
class BaseToken:
    symbol: str
    address: AddressLike

    def __repr__(self) -> str:
        return f"BaseToken({self.symbol}, {self.address!r})"


@dataclass
class Token(BaseToken):
    name: str
    decimals: int

    def __repr__(self) -> str:
        return f"Token({self.symbol}, {self.address!r}, {self.decimals})"
