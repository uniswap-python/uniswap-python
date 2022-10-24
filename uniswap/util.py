import os
import json
import math
import functools
import lru

from typing import Any, Generator, Sequence, Union, List, Tuple, Type, Dict, cast

from web3 import Web3
from web3.exceptions import NameNotFound
from web3.contract import Contract
from web3.middleware.cache import construct_simple_cache_middleware
from web3.types import Middleware

from .constants import MIN_TICK, MAX_TICK, _tick_spacing, SIMPLE_CACHE_RPC_WHITELIST
from .types import AddressLike, Address


def _get_eth_simple_cache_middleware() -> Middleware:
    return construct_simple_cache_middleware(
        cache_class=cast(Type[Dict[Any, Any]], functools.partial(lru.LRU, 256)),
        rpc_whitelist=SIMPLE_CACHE_RPC_WHITELIST,
    )


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
    return w3.eth.contract(address=address, abi=_load_abi(abi_name))  # type: ignore


def _load_contract_erc20(w3: Web3, address: AddressLike) -> Contract:
    return _load_contract(w3, "erc20", address)


def _encode_path(token_in: AddressLike, route: List[Tuple[int, AddressLike]]) -> bytes:
    """
    Needed for multi-hop swaps in V3.

    https://github.com/Uniswap/uniswap-v3-sdk/blob/1a74d5f0a31040fec4aeb1f83bba01d7c03f4870/src/utils/encodeRouteToPath.ts
    """
    raise NotImplementedError


# Adapted from: https://github.com/Uniswap/v3-sdk/blob/main/src/utils/encodeSqrtRatioX96.ts
def encode_sqrt_ratioX96(amount_0: int, amount_1: int) -> int:
    numerator = amount_1 << 192
    denominator = amount_0
    ratioX192 = numerator // denominator
    return int(math.sqrt(ratioX192))


# Adapted from: https://github.com/tradingstrategy-ai/web3-ethereum-defi/blob/c3c68bc723d55dda0cc8252a0dadb534c4fdb2c5/eth_defi/uniswap_v3/utils.py#L77
def get_min_tick(fee: int) -> int:
    min_tick_spacing: int = _tick_spacing[fee]
    return -(MIN_TICK // -min_tick_spacing) * min_tick_spacing


def get_max_tick(fee: int) -> int:
    max_tick_spacing: int = _tick_spacing[fee]
    return (MAX_TICK // max_tick_spacing) * max_tick_spacing


def default_tick_range(fee: int) -> Tuple[int, int]:
    min_tick = get_min_tick(fee)
    max_tick = get_max_tick(fee)

    return min_tick, max_tick


def nearest_tick(tick: int, fee: int) -> int:
    min_tick, max_tick = default_tick_range(fee)
    assert (
        min_tick <= tick <= max_tick
    ), f"Provided tick is out of bounds: {(min_tick, max_tick)}"

    tick_spacing = _tick_spacing[fee]
    rounded_tick_spacing = round(tick / tick_spacing) * tick_spacing

    if rounded_tick_spacing < min_tick:
        return rounded_tick_spacing + tick_spacing
    elif rounded_tick_spacing > max_tick:
        return rounded_tick_spacing - tick_spacing
    else:
        return rounded_tick_spacing


def chunks(arr: Sequence[Any], n: int) -> Generator:
    for i in range(0, len(arr), n):
        yield arr[i : i + n]
