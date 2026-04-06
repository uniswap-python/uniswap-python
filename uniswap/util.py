import functools
import json
import math
import os
from typing import (
    Any,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from xml.etree import ElementTree as ET

import lru
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import NameNotFound
from web3.middleware.cache import construct_simple_cache_middleware
from web3.types import Middleware

from .constants import (
    MAX_TICK,
    MIN_TICK,
    SIMPLE_CACHE_RPC_WHITELIST,
    _netid_to_name,
    _poolmanager_contract_addresses_v4,
    _tick_spacing,
)
from .types import Address, AddressLike, PoolKey


def _get_eth_simple_cache_middleware() -> Middleware:
    return construct_simple_cache_middleware(
        cache=functools.partial(lru.LRU, 256),  # type: ignore
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
        addr: str = Web3.to_checksum_address("0x" + bytes(a).hex())
        return addr
    elif isinstance(a, str) and a.startswith("0x"):
        addr = Web3.to_checksum_address(a)
        return addr

    raise NameNotFound(a)


def is_same_address(a1: Union[AddressLike, str], a2: Union[AddressLike, str]) -> bool:
    return bool(_str_to_addr(a1) == _str_to_addr(a2))


def _validate_address(a: AddressLike) -> None:
    assert _addr_to_str(a)


def _load_abi(name: str) -> str:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/assets/"
    with open(os.path.abspath(path + f"{name}.abi")) as f:
        abi: str = json.load(f)
    return abi


@functools.lru_cache()
def _load_contract(w3: Web3, abi_name: str, address: AddressLike) -> Contract:
    address = Web3.to_checksum_address(address)
    return w3.eth.contract(address=address, abi=_load_abi(abi_name))


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


def decode_sqrt_ratioX96(sqrtPriceX96: int) -> float:
    Q96 = 2**96
    ratio = sqrtPriceX96 / Q96
    price = ratio**2
    return price


def get_tick_at_sqrt(sqrtPriceX96: int) -> int:
    sqrtPriceX96 = int(sqrtPriceX96)

    # Define constants
    Q96 = 2**96

    # Calculate the price from the sqrt ratio
    ratio = sqrtPriceX96 / Q96
    price = ratio**2

    # Calculate the natural logarithm of the price
    logPrice = math.log(price)

    # Calculate the log base 1.0001 of the price
    logBase = math.log(1.0001)
    tick = logPrice / logBase

    # Round tick to nearest integer
    tick = int(round(tick))

    # Ensure the tick is within the valid range
    assert tick >= MIN_TICK and tick <= MAX_TICK

    return tick


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
    assert min_tick <= tick <= max_tick, (
        f"Provided tick is out of bounds: {(min_tick, max_tick)}"
    )

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


def fee_to_fraction(fee: int) -> float:
    return fee / 1000000


def realised_fee_percentage(fee: int, amount_in: int) -> float:
    """
    Calculate realised fee expressed as a percentage of the amount_in.
    The realised fee is rounded up as fractional units cannot be used -
        this correlates to how the fees are rounded by Uniswap.
    """

    fee_percentage = fee_to_fraction(fee)
    fee_realised = math.ceil(amount_in * fee_percentage)
    return fee_realised / amount_in


class V4pools:
    """Uniswap V4 pools handler"""

    poolkeys_list: List[PoolKey]

    def __init__(
        self,
        web3: Web3,
    ):
        self.poolkeys_list: List[PoolKey] = list()
        self.web3 = web3
        self.last_block = 0

    def get_last_block(
        self,
    ) -> int:
        return self.last_block

    def set_last_block(self, value: int) -> None:
        self.last_block = value

    def fetch_poolkey_data(
        self,
        first_block: int,
        chunk_size: int = 500,
        clear_list: bool = True,
        last_block: Optional[int] = None,
    ) -> None:
        """
        :param first_block: Starting block for scanning process
        :param chunk_size Defines amount of blocks per single log request
        :param clear_list When True, clears pool list before log scanning, when False - new entries will be added to the end of the list.
        :param last_block Optional parameter defining the last block for scanning process. If None, current block number will be used.
        """
        # Scans PoolManager contract' Initialize() event logs in order to get
        # list of all pools.  See documentation for suggested starting blocks.
        # chunk_size default value 500 should be suitable for public RPCs;
        # can be increased on private/local RPCs for better performance.

        chain_id = int(self.web3.net.version)
        net_name = _netid_to_name[chain_id]
        pool_manager_contract_address = _poolmanager_contract_addresses_v4[net_name]
        pool_manager_contract = _load_contract(
            self.web3,
            "uniswap-v4/poolmanager",
            _str_to_addr(pool_manager_contract_address),
        )
        first_block_number: int = first_block
        if last_block is None:
            last_block_number: int = int(self.web3.eth.get_block_number())
        else:
            last_block_number = min(
                max(first_block, last_block), int(self.web3.eth.get_block_number())
            )

        chunks_amount = int((last_block_number - first_block_number) // chunk_size)
        start_block = first_block_number
        end_block = 0

        print(
            f"Logs processing started, start block = {start_block}; end block = {last_block_number}."
        )
        if clear_list:
            self.poolkeys_list.clear()

        for i in range(0, chunks_amount + 1):
            if start_block + chunk_size <= last_block_number:
                end_block = start_block + chunk_size
            else:
                end_block = last_block_number
            print(
                f"Processing chunk {i}/{chunks_amount}; (start block = {start_block}; end block = {end_block})",
                end="\r",
                flush=True,
            )
            try:
                logs = pool_manager_contract.events.Initialize().get_logs(
                    fromBlock=start_block, toBlock=end_block
                )
            except Exception as e:
                # Exception occurs when chunk size value is too big so RPC endpoint rejects
                # requests OR RPC endpoint is down.
                print(
                    "Couldn't retrieve logs; check chunk size and RPC availability. Aborted.              "
                )
                print(f"Error details: {e}")
                return
            for log_item in logs:
                try:
                    txn = self.web3.eth.get_transaction_receipt(
                        log_item.transactionHash
                    )
                except Exception as e:
                    # Exception occurs when RPC endpoint is down.
                    print(
                        "Couldn't retrieve transaction receipt; check RPC availability."
                    )
                    print(f"Error details: {e}")
                    continue

                if (
                    txn["to"].lower() != pool_manager_contract_address.lower()
                    or int(txn["status"]) == 0
                ):
                    continue
                try:
                    pool_currency0 = str(log_item.args.currency0)
                    pool_currency1 = str(log_item.args.currency1)
                    pool_fee = int(str(log_item.args.fee))
                    pool_tick_spacing = int(str(log_item.args.tickSpacing))
                    pool_hooks = str(log_item.args.hooks)
                    pool: PoolKey = PoolKey(
                        pool_currency0,
                        pool_currency1,
                        pool_fee,
                        pool_tick_spacing,
                        pool_hooks,
                    )
                    if pool not in self.poolkeys_list:
                        self.poolkeys_list.append(pool)
                except Exception:
                    continue
            self.set_last_block(end_block)
            if end_block == last_block_number:
                break
            start_block = start_block + chunk_size

        print(
            "---------------------------------------------------------------------------------------------"
        )
        print(f"Logs processing completed. Last block processed {last_block_number}")
        self.set_last_block(last_block_number)
        return

    def save_poolkeys_list(self, poolkey_data_filename: str) -> None:
        """Saves poolKey list to specified file (XML format)"""
        pool_data = ET.Element("PoolData")

        for pool_item in self.poolkeys_list:
            pool = ET.SubElement(pool_data, "Pool")

            currency0 = ET.SubElement(pool, "Currency0")
            currency0.text = str(pool_item.currency0)

            currency1 = ET.SubElement(pool, "Currency1")
            currency1.text = str(pool_item.currency1)

            fee = ET.SubElement(pool, "Fee")
            fee.text = str(pool_item.fee)

            tick_spacing = ET.SubElement(pool, "TickSpacing")
            tick_spacing.text = str(pool_item.tick_spacing)

            hooks = ET.SubElement(pool, "Hooks")
            hooks.text = str(pool_item.hooks)

        ET.ElementTree(pool_data).write(poolkey_data_filename)
        return

    def load_poolkeys_list(self, poolkey_data_filename: str) -> None:
        """Loads poolKey list from specified file (XML format)"""
        if os.path.isfile(poolkey_data_filename):
            try:
                tree = ET.parse(poolkey_data_filename)
            except ET.ParseError:
                raise ValueError(
                    "Parse error, file seems to be corrupted ("
                    + poolkey_data_filename
                    + ")"
                )
            self.poolkeys_list.clear()
            root = tree.getroot()
            for item in root:
                pool_currency0 = str(item[0].text)
                pool_currency1 = str(item[1].text)
                pool_fee = int(str(item[2].text))
                pool_tick_spacing = int(str(item[3].text))
                pool_hooks = str(item[4].text)
                pool: PoolKey = PoolKey(
                    pool_currency0,
                    pool_currency1,
                    pool_fee,
                    pool_tick_spacing,
                    pool_hooks,
                )
                self.poolkeys_list.append(pool)
        else:
            raise ValueError("Couldn't locate file " + poolkey_data_filename)

    def get_poolkeys_sublist(self, currency0: str, currency1: str) -> List[PoolKey]:
        """Returns all pools for the (currency0, currency1) pair"""
        if currency0 < currency1:
            c0, c1 = currency0, currency1
        else:
            c0, c1 = currency1, currency0
        result_list = [
            x for x in self.poolkeys_list if c0 == x.currency0 and c1 == x.currency1
        ]
        return result_list
