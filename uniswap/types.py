from typing import Union
from web3.eth import Contract  # noqa: F401
from web3.types import Address, ChecksumAddress


AddressLike = Union[Address, ChecksumAddress]
