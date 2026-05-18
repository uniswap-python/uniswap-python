import logging
import os
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from time import sleep
from typing import Generator, List, Optional

import pytest
from web3 import Web3
from web3.types import Nonce

from uniswap import Uniswap4
from uniswap.constants import ETH_ADDRESS, ZERO_HOOK
from uniswap.types import AddressLike, PoolKey
from uniswap.util import _str_to_addr

pytestmark = pytest.mark.skipif(
    os.getenv("UNISWAP_VERSION") != "4",
    reason="This test file is for Uniswap v4. For Uniswap v1, v2, and v3 tests, see test_uniswap.py",
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

RECEIPT_TIMEOUT = 5

ONE_ETH = 10**18
ONE_USDT = 10**6
ONE_USDC = 10**6
ETH_DECIMALS = 18
USDT_DECIMALS = 6
USDC_DECIMALS = 6
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
ETH_USDC_FEE = 500
ETH_USDC_TICK_SPACING = 10
USDC_USDT_FEE = 10
USDC_USDT_TICK_SPACING = 1

TOKEN_ID = 1

eth_usdc_poolkey: PoolKey = PoolKey(
    currency0=ETH_ADDRESS,  # ETH
    currency1=USDC_ADDRESS,  # USDC
    fee=ETH_USDC_FEE,
    tick_spacing=ETH_USDC_TICK_SPACING,
    hooks=ZERO_HOOK,
)


usdc_usdt_poolkey: PoolKey = PoolKey(
    currency0=USDC_ADDRESS,  # USDC
    currency1=USDT_ADDRESS,  # USDT
    fee=USDC_USDT_FEE,
    tick_spacing=USDC_USDT_TICK_SPACING,
    hooks=ZERO_HOOK,
)


@dataclass
class AnvilInstance:
    provider: str
    eth_address: str
    eth_privkey: str


@pytest.fixture(scope="module")
def client(web3: Web3, anvil: AnvilInstance) -> Uniswap4:
    return Uniswap4(
        anvil.eth_address,
        anvil.eth_privkey,
        web3=web3,
    )


@pytest.fixture(scope="module")
def web3(anvil: AnvilInstance) -> Web3:
    w3 = Web3(Web3.HTTPProvider(anvil.provider, request_kwargs={"timeout": 30}))
    if 1 != int(w3.net.version):
        logger.warning("PROVIDER was not a mainnet provider, which the tests require")
    return w3


@pytest.fixture(scope="module")
def anvil() -> Generator[AnvilInstance, None, None]:
    """Fixture that runs anvil which has forked off mainnet"""
    if not shutil.which("anvil"):
        raise Exception("anvil was not found in PATH")
    if "PROVIDER" not in os.environ:
        raise Exception(
            "PROVIDER was not set, you need to set it to a mainnet provider (such as Infura) so that we can fork off our testnet"
        )

    port = 10998
    defaultGasPrice = 100_000_000_000  # 100 gwei
    p = subprocess.Popen(
        f"""anvil
        --port {port}
        --chain-id 1
        --fork-url {os.environ["PROVIDER"]}
        --gas-price {defaultGasPrice}
        """.replace("\n", " "),
        shell=True,
    )
    # Address #1 when anvil is run with `--wallet.seed test`, it starts with 1000 ETH
    eth_address = "0xa0Ee7A142d267C1f36714E4a8F75612F20a79720"
    eth_privkey = "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6"
    sleep(3)
    yield AnvilInstance(f"http://127.0.0.1:{port}", eth_address, eth_privkey)
    p.kill()
    p.wait()


@contextmanager
def does_not_raise():
    yield


@pytest.mark.usefixtures("client", "web3")
class TestUniswap4(object):
    # ------ Approve/tx replacement-----------------------------------------------------
    @pytest.mark.parametrize(
        "token, max_approval, delay_interval",
        [
            (USDC_ADDRESS, None, 7),
            (USDT_ADDRESS, 1_000_000 * ONE_USDT, 1),
        ],
    )
    def test_approve(
        self,
        client: Uniswap4,
        token: str,
        max_approval: Optional[int],
        delay_interval: int,
    ):
        # Approve the token
        tx_receipt = client.approve(
            _str_to_addr(token), max_approval, delay_interval=delay_interval
        )
        assert tx_receipt
        print(tx_receipt.hex())
        tx = client.w3.eth.wait_for_transaction_receipt(
            tx_receipt, timeout=RECEIPT_TIMEOUT
        )
        print(str(tx))
        assert tx["status"], f"Transaction failed with status {tx['status']}; tx: {tx}"
        # Check that the approval was successful by calling allowance
        allowance = client.approval(_str_to_addr(token))
        assert allowance

    @pytest.mark.parametrize(
        "address_to, gas_price, priority_fee, custom_nonce",
        [
            ("self", 20, 10, None),
            (ETH_ADDRESS, 20, 10, 0),
        ],
    )
    def test_drop_txn(
        self,
        client: Uniswap4,
        address_to: str,
        gas_price: float,
        priority_fee: int,
        custom_nonce: Optional[int],
    ):
        if not client.w3.is_address(address_to):
            address: AddressLike = client.w3.to_checksum_address(
                client.address  # ETH_ADDRESS
            )  # client.address
        else:
            address = client.w3.to_checksum_address(address_to)
        client.update_last_nonce()
        if custom_nonce == 0:
            nonce: Optional[Nonce] = client.last_nonce
        else:
            nonce = None

        tx_receipt = client.drop_txn(
            address,
            gas_price,
            priority_fee=priority_fee,
            custom_nonce=nonce,
        )
        assert tx_receipt
        print(tx_receipt.hex())
        tx = client.w3.eth.wait_for_transaction_receipt(
            tx_receipt, timeout=RECEIPT_TIMEOUT
        )
        print(str(tx))
        assert tx["status"], f"Transaction failed with status {tx['status']}; tx: {tx}"
        client.update_last_nonce()

    # ------ Market/price impact--------------------------------------------------------
    # Input quotes
    @pytest.mark.parametrize(
        "token0, token1, qty, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ONE_ETH,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
            (
                USDC_ADDRESS,
                USDT_ADDRESS,
                ONE_USDC,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_get_quote_exact_input_single(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.get_quote_exact_input_single(
            token0, token1, qty, fee, tick_spacing, hooks
        )
        assert result

    @pytest.mark.parametrize(
        "token0, qty, route",
        [
            (
                ETH_ADDRESS,
                ONE_ETH,
                [
                    eth_usdc_poolkey,
                ],
            ),
            (
                USDC_ADDRESS,
                1000 * ONE_USDC,
                [
                    eth_usdc_poolkey,
                ],
            ),
            (
                ETH_ADDRESS,
                ONE_ETH,
                [
                    eth_usdc_poolkey,
                    usdc_usdt_poolkey,
                ],
            ),
            (
                USDT_ADDRESS,
                1000 * ONE_USDT,
                [
                    usdc_usdt_poolkey,
                    eth_usdc_poolkey,
                ],
            ),
        ],
    )
    def test_get_quote_exact_input(
        self,
        client: Uniswap4,
        token0: str,
        qty: int,
        route: List[PoolKey],
    ):
        result = client.get_quote_exact_input(token0, qty, route)
        assert result

    @pytest.mark.parametrize(
        "token0, token1, qty, fee, tick_spacing, hooks, hook_data, route",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ONE_ETH,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
                b"",
                None,
            ),
            (
                USDC_ADDRESS,
                ETH_ADDRESS,
                1000 * ONE_USDC,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
                b"",
                None,
            ),
            (
                ETH_ADDRESS,
                USDT_ADDRESS,
                ONE_ETH,
                None,
                None,
                None,
                None,
                [eth_usdc_poolkey, usdc_usdt_poolkey],
            ),
            (
                USDT_ADDRESS,
                ETH_ADDRESS,
                1000 * ONE_USDT,
                None,
                None,
                None,
                None,
                [usdc_usdt_poolkey, eth_usdc_poolkey],
            ),
        ],
    )
    def test_get_price_input(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        fee: Optional[int],
        tick_spacing: Optional[int],
        hooks: Optional[str],
        hook_data: Optional[bytes],
        route: Optional[List[PoolKey]],
    ):
        result = client.get_price_input(
            token0, token1, qty, fee, tick_spacing, hooks, hook_data, route
        )
        assert result

    # Output quotes
    @pytest.mark.parametrize(
        "token0, token1, qty, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                1000 * ONE_USDC,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
            (
                USDC_ADDRESS,
                USDT_ADDRESS,
                ONE_USDC,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_get_quote_exact_output_single(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.get_quote_exact_output_single(
            token0, token1, qty, fee, tick_spacing, hooks
        )
        assert result

    @pytest.mark.parametrize(
        "token0, qty, route",
        [
            (
                USDC_ADDRESS,
                1000 * ONE_USDC,
                [
                    eth_usdc_poolkey,
                ],
            ),
            (
                USDT_ADDRESS,
                1000 * ONE_USDT,
                [
                    usdc_usdt_poolkey,
                ],
            ),
            (
                USDT_ADDRESS,
                1000 * ONE_USDT,
                [
                    eth_usdc_poolkey,
                    usdc_usdt_poolkey,
                ],
            ),
            (
                ETH_ADDRESS,
                ONE_ETH,
                [
                    usdc_usdt_poolkey,
                    eth_usdc_poolkey,
                ],
            ),
        ],
    )
    def test_get_quote_exact_output(
        self, client: Uniswap4, token0: str, qty: int, route: List[PoolKey]
    ):
        result = client.get_quote_exact_output(token0, qty, route)
        assert result

    @pytest.mark.parametrize(
        "token0, token1, qty, fee, tick_spacing, hooks, hook_data, route",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                1000 * ONE_USDC,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
                b"",
                None,
            ),
            (
                USDC_ADDRESS,
                ETH_ADDRESS,
                ONE_ETH,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
                b"",
                None,
            ),
            (
                ETH_ADDRESS,
                USDT_ADDRESS,
                ONE_ETH,
                None,
                None,
                None,
                None,
                [
                    usdc_usdt_poolkey,
                    eth_usdc_poolkey,
                ],
            ),
            (
                USDT_ADDRESS,
                ETH_ADDRESS,
                1000 * ONE_USDT,
                None,
                None,
                None,
                None,
                [
                    eth_usdc_poolkey,
                    usdc_usdt_poolkey,
                ],
            ),
        ],
    )
    def test_get_price_output(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        fee: Optional[int],
        tick_spacing: Optional[int],
        hooks: Optional[str],
        hook_data: Optional[bytes],
        route: Optional[List[PoolKey]],
    ):
        result = client.get_price_output(
            token0, token1, qty, fee, tick_spacing, hooks, hook_data, route
        )
        assert result

    # Price impact/spot price
    @pytest.mark.parametrize(
        "token0, token1, test_volume",
        [
            (ETH_ADDRESS, USDC_ADDRESS, ONE_ETH),
            (ETH_ADDRESS, USDC_ADDRESS, 10 * ONE_ETH),
            (ETH_ADDRESS, USDC_ADDRESS, 100 * ONE_ETH),
            (ETH_ADDRESS, USDC_ADDRESS, 1000 * ONE_ETH),
        ],
    )
    def test_estimate_price_impact(
        self, client: Uniswap4, token0: str, token1: str, test_volume: int
    ):
        result = client.estimate_price_impact(token0, token1, test_volume)
        assert result

    @pytest.mark.parametrize(
        "token0, token1",
        [
            (ETH_ADDRESS, USDC_ADDRESS),
            (USDC_ADDRESS, ETH_ADDRESS),
        ],
    )
    def test_get_token_token_spot_price(
        self, client: Uniswap4, token0: str, token1: str
    ):
        result = client.get_token_token_spot_price(token0, token1)
        assert result

    # ------ Swaps----------------------------------------------------------------------
    def test_swap_exact_input_single(self):
        pass

    def test_swap_exact_input(self):
        pass

    def test_make_swap_input(self):
        pass

    def test_swap_exact_output_single(self):
        pass

    def test_swap_exact_output(self):
        pass

    def test_make_swap_output(self):
        pass

    # ------ Liquidity --------------------------------------------------------------------
    @pytest.mark.parametrize("token_id", [(TOKEN_ID)])
    def test_get_position_info(self, client: Uniswap4, token_id: int):
        result = client.get_position_info(token_id)
        test_pool_id_result: int = int.from_bytes(result["poolID"], byteorder="big")
        truncated_pool_id_str = hex(test_pool_id_result).lower()
        pool_id_str = (
            client.get_pool_id(
                PoolKey(
                    result["currency0"],
                    result["currency1"],
                    result["fee"],
                    result["tickSpacing"],
                    result["hooks"],
                )
            )
            .hex()
            .lower()
        )
        assert truncated_pool_id_str == pool_id_str[: len(truncated_pool_id_str)]

    @pytest.mark.parametrize(
        "token_id, token0_decimals, token1_decimals",
        [(TOKEN_ID, ETH_DECIMALS, USDC_DECIMALS)],
    )
    def test_get_position_value(
        self,
        client: Uniswap4,
        token_id: int,
        token0_decimals: int,
        token1_decimals: int,
    ):
        result = client.get_position_value(token_id, token0_decimals, token1_decimals)
        assert result

    @pytest.mark.parametrize(
        "transaction_hash",
        [("0xb30d3dde98f715e5880da9f8833f99823623229e193e04661cb7ce193e4028f8")],
    )
    def test_get_minted_token_id(self, client: Uniswap4, transaction_hash: str):
        result = client.get_minted_token_id(transaction_hash)
        assert result

    def test_create_pool(self):
        pass

    def test_mint_position(self):
        pass

    def test_increase_liquidity(self):
        pass

    def test_decrease_liquidity(self):
        pass

    def test_collect_fees(self):
        pass

    def test_burn_position(self):
        pass

    # ------ V4Pools tests ----------------------------------------------------------------
    # ------ StateView tests --------------------------------------------------------------
    # ------ PositionDescriptor tests -----------------------------------------------------
    # ------ PositionManager tests --------------------------------------------------------
    # ------ PoolManager tests ------------------------------------------------------------
    # ------ UniversalRouter tests --------------------------------------------------------
