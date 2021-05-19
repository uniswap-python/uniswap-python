from typing import Union
from web3.eth import Contract  # noqa: F401
from web3.types import Address, ChecksumAddress, ENS


# TODO: Consider dropping support for ENS altogether and instead use AnyAddress
AddressLike = Union[Address, ChecksumAddress, ENS]
