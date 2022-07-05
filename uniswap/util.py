import os
import json
import functools
from typing import Union, List, Tuple, Any, Dict
from dataclasses import dataclass

from web3 import Web3
from web3.exceptions import NameNotFound
from eth_abi import encode_abi

from .types import AddressLike, Address, Contract


def _str_to_addr(s: Union[AddressLike, str]) -> Address:
    """Idempotent"""
    if isinstance(s, str):
        if s.startswith("0x"):
            return Address(bytes.fromhex(s[2:]))
        else:
            raise NameNotFound(f"Couldn't convert string '{s}' to AddressLike")
    else:
        return s


def _addr_to_str(a: AddressLike) -> str:
    if isinstance(a, bytes):
        # Address or ChecksumAddress
        addr: str = Web3.toChecksumAddress("0x" + bytes(a).hex())
        return addr
    elif isinstance(a, str) and a.startswith("0x"):
        addr = Web3.toChecksumAddress(a)
        return addr

    raise NameNotFound(a)


def is_same_address(a1: Union[AddressLike, str], a2: Union[AddressLike, str]) -> bool:
    return _str_to_addr(a1) == _str_to_addr(a2)


def _validate_address(a: AddressLike) -> None:
    assert _addr_to_str(a)


def _load_abi(name: str) -> str:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/assets/"
    with open(os.path.abspath(path + f"{name}.abi")) as f:
        abi: str = json.load(f)
    return abi


@functools.lru_cache()
def _load_contract(w3: Web3, abi_name: str, address: AddressLike) -> Contract:
    address = Web3.toChecksumAddress(address)
    return w3.eth.contract(address=address, abi=_load_abi(abi_name))


def _load_contract_erc20(w3: Web3, address: AddressLike) -> Contract:
    return _load_contract(w3, "erc20", address)


@dataclass
class Pool(dict):
    token0: AddressLike
    token1: AddressLike
    fee: int


@dataclass
class Route:
    pools: List[Pool]


def _token_seq_to_route(tokens: List[AddressLike], fee: int = 3000) -> Route:
    return Route(
        pools=[
            Pool(token0, token1, fee) for token0, token1 in zip(tokens[:-1], tokens[1:])
        ]
    )


def _encode_path(
    token_in: AddressLike,
    route: List[Tuple[int, AddressLike]],
    # route: Route,
    exactOutput: bool,
) -> bytes:
    """
    Needed for multi-hop swaps in V3.

    https://github.com/Uniswap/uniswap-v3-sdk/blob/1a74d5f0a31040fec4aeb1f83bba01d7c03f4870/src/utils/encodeRouteToPath.ts
    """
    from functools import reduce

    _route = _token_seq_to_route([token_in] + [token for fee, token in route])

    def merge(acc: Dict[str, Any], pool: Pool) -> Dict[str, Any]:
        """Returns a dict with the keys: inputToken, path, types"""
        index = 0 if not acc["types"] else None
        inputToken = acc["inputToken"]
        outputToken = pool.token1 if pool.token0 == inputToken else pool.token0
        if index == 0:
            return {
                "inputToken": outputToken,
                "types": ["address", "uint24", "address"],
                "path": [inputToken, pool.fee, outputToken],
            }
        else:
            return {
                "inputToken": outputToken,
                "types": [*acc["types"], "uint24", "address"],
                "path": [*path, pool.fee, outputToken],
            }

    params = reduce(
        merge,
        _route.pools,
        {"inputToken": _addr_to_str(token_in), "path": [], "types": []},
    )
    types = params["types"]
    path = params["path"]

    if exactOutput:
        encoded: bytes = encode_abi(list(reversed(types)), list(reversed(path)))
    else:
        encoded = encode_abi(types, path)

    return encoded


def test_encode_path() -> None:
    """Take tests from: https://github.com/Uniswap/uniswap-v3-sdk/blob/1a74d5f0a31040fec4aeb1f83bba01d7c03f4870/src/utils/encodeRouteToPath.test.ts"""
    from uniswap.tokens import tokens

    # TODO: Actually assert testcases
    path = _encode_path(tokens["WETH"], [(3000, tokens["DAI"])], exactOutput=True)
    print(path)

    path = _encode_path(tokens["WETH"], [(3000, tokens["DAI"])], exactOutput=False)
    print(path)
