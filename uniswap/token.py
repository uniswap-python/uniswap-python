from dataclasses import dataclass
from .types import AddressLike


@dataclass
class BaseToken:
    """Base for tokens of all kinds"""

    symbol: str
    """Symbol such as ETH, DAI, etc."""

    address: AddressLike
    """Address of the token contract."""

    def __repr__(self) -> str:
        return f"BaseToken({self.symbol}, {self.address!r})"


@dataclass
class ERC20Token(BaseToken):
    """Represents an ERC20 token"""

    name: str
    """Name of the token, as specified in the contract."""

    decimals: int
    """Decimals used to denominate the token."""

    def __repr__(self) -> str:
        return f"Token({self.symbol}, {self.address!r}, {self.decimals})"
