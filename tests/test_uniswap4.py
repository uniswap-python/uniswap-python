import logging
import os
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import astuple, dataclass
from time import sleep
from typing import Generator, List, Optional

import pytest
from web3 import Web3
from web3.types import Nonce

from uniswap import Uniswap4
from uniswap.constants import (
    ETH_ADDRESS,
    ZERO_HOOK,
    universal_router_commands,
    v4_actions,
)
from uniswap.types import AddressLike, PoolKey
from uniswap.util import V4pools, _addr_to_str, _str_to_addr

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
        gas_limit=500_000,
    )


@pytest.fixture(scope="module")
def pool_service(web3: Web3) -> V4pools:
    return V4pools(web3)


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
    test_token_id: int = 0
    test_mint_tx_hash: str = ""
    test_tick: int = 0

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
        tx = client.approve(
            _str_to_addr(token),
            max_approval,
            delay_interval=delay_interval,
            approve_position_manager=True,
        )
        assert tx
        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )
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
            address: AddressLike = client.address
        else:
            address = _str_to_addr(address_to)
        client.update_last_nonce()
        if custom_nonce == 0:
            nonce: Optional[Nonce] = client.last_nonce
        else:
            nonce = None

        tx = client.drop_txn(
            address,
            gas_price,
            priority_fee=priority_fee,
            custom_nonce=nonce,
        )
        assert tx
        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )
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
            (
                USDT_ADDRESS,
                ETH_ADDRESS,
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
    # Input swaps
    @pytest.mark.parametrize(
        "token0, token1, qty, fee, tick_spacing, hooks, hook_data, custom_nonce",
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
                USDT_ADDRESS,
                ONE_USDC,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
                b"",
                None,
            ),
        ],
    )
    def test_token_to_token_swap_exact_input(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        fee: int,
        tick_spacing: int,
        hooks: str,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        qtycap = client.get_quote_exact_input_single(
            token0, token1, qty, fee, tick_spacing, hooks, hook_data
        )
        tx = client.token_to_token_swap_exact_input(
            token0,
            qty,
            qtycap,
            token1,
            fee,
            tick_spacing,
            hooks,
            hook_data,
            0,  # min_hop_price_x_36
            custom_nonce,
        )
        assert tx
        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "token0, qty, route, custom_nonce",
        [
            (
                ETH_ADDRESS,
                ONE_ETH,
                [
                    eth_usdc_poolkey,
                ],
                None,
            ),
            (
                USDC_ADDRESS,
                1000 * ONE_USDC,
                [
                    eth_usdc_poolkey,
                ],
                None,
            ),
            (
                ETH_ADDRESS,
                ONE_ETH,
                [
                    eth_usdc_poolkey,
                    usdc_usdt_poolkey,
                ],
                None,
            ),
            (
                USDT_ADDRESS,
                1000 * ONE_USDT,
                [
                    usdc_usdt_poolkey,
                    eth_usdc_poolkey,
                ],
                None,
            ),
        ],
    )
    def test_token_to_token_swap_input(
        self,
        client: Uniswap4,
        token0: str,
        qty: int,
        route: List[PoolKey],
        custom_nonce: Optional[Nonce],
    ):
        qtycap = client.get_quote_exact_input(token0, qty, route)

        tx = client.token_to_token_swap_input(
            token0, qty, qtycap, route, min_hop_price_x_36=[], custom_nonce=custom_nonce
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "token0, token1, qty, pool_key, hook_data, route, custom_nonce",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                10 * ONE_ETH,
                eth_usdc_poolkey,
                b"",
                None,
                None,
            ),
            (
                USDC_ADDRESS,
                ETH_ADDRESS,
                1000 * ONE_USDC,
                eth_usdc_poolkey,
                b"",
                None,
                None,
            ),
            (
                ETH_ADDRESS,
                USDT_ADDRESS,
                10 * ONE_ETH,
                None,
                None,
                [eth_usdc_poolkey, usdc_usdt_poolkey],
                None,
            ),
            (
                USDT_ADDRESS,
                ETH_ADDRESS,
                1000 * ONE_USDT,
                None,
                None,
                [usdc_usdt_poolkey, eth_usdc_poolkey],
                None,
            ),
        ],
    )
    def test_make_swap_input(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        pool_key: Optional[PoolKey],
        hook_data: Optional[bytes],
        route: Optional[List[PoolKey]],
        custom_nonce: Optional[Nonce],
    ):
        qtycap = client.get_price_input(
            token0,
            token1,
            qty,
            None if pool_key is None else pool_key.fee,
            None if pool_key is None else pool_key.tick_spacing,
            None if pool_key is None else pool_key.hooks,
            hook_data,
            route,
        )
        tx = client.make_swap_input(
            token0, token1, qty, qtycap, pool_key, hook_data, route, custom_nonce
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    # Output swaps
    @pytest.mark.parametrize(
        "token0, token1, qty, fee, tick_spacing, hooks, hook_data, custom_nonce",
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
                USDT_ADDRESS,
                ONE_USDC,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
                b"",
                None,
            ),
        ],
    )
    def test_token_to_token_swap_exact_output(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        fee: int,
        tick_spacing: int,
        hooks: str,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        qtycap = client.get_quote_exact_output_single(
            token0, token1, qty, fee, tick_spacing, hooks, hook_data
        )
        tx = client.token_to_token_swap_exact_output(
            token0,
            qty,
            qtycap,
            token1,
            fee,
            tick_spacing,
            hooks,
            hook_data,
            0,  # min_hop_price_x_36
            custom_nonce,
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "token0, qty, route, custom_nonce",
        [
            (
                USDC_ADDRESS,
                1000 * ONE_USDC,
                [
                    eth_usdc_poolkey,
                ],
                None,
            ),
            (
                USDT_ADDRESS,
                1000 * ONE_USDT,
                [
                    usdc_usdt_poolkey,
                ],
                None,
            ),
            (
                USDT_ADDRESS,
                1000 * ONE_USDT,
                [
                    eth_usdc_poolkey,
                    usdc_usdt_poolkey,
                ],
                None,
            ),
            (
                ETH_ADDRESS,
                ONE_ETH,
                [
                    usdc_usdt_poolkey,
                    eth_usdc_poolkey,
                ],
                None,
            ),
        ],
    )
    def test_token_to_token_swap_output(
        self,
        client: Uniswap4,
        token0: str,
        qty: int,
        route: List[PoolKey],
        custom_nonce: Optional[Nonce],
    ):
        qtycap = client.get_quote_exact_output(token0, qty, route)
        tx = client.token_to_token_swap_output(
            token0, qty, qtycap, route, min_hop_price_x_36=[], custom_nonce=custom_nonce
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "token0, token1, qty, pool_key, hook_data, route, custom_nonce",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                1000 * ONE_USDC,
                eth_usdc_poolkey,
                b"",
                None,
                None,
            ),
            (
                USDC_ADDRESS,
                ETH_ADDRESS,
                ONE_ETH,
                eth_usdc_poolkey,
                b"",
                None,
                None,
            ),
            (
                ETH_ADDRESS,
                USDT_ADDRESS,
                1000 * ONE_USDT,
                None,
                None,
                [
                    eth_usdc_poolkey,
                    usdc_usdt_poolkey,
                ],
                None,
            ),
            (
                USDT_ADDRESS,
                ETH_ADDRESS,
                ONE_ETH,
                None,
                None,
                [
                    usdc_usdt_poolkey,
                    eth_usdc_poolkey,
                ],
                None,
            ),
        ],
    )
    def test_make_swap_output(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        qty: int,
        pool_key: Optional[PoolKey],
        hook_data: Optional[bytes],
        route: Optional[List[PoolKey]],
        custom_nonce: Optional[Nonce],
    ):
        qtycap = client.get_price_output(
            token0,
            token1,
            qty,
            None if pool_key is None else pool_key.fee,
            None if pool_key is None else pool_key.tick_spacing,
            None if pool_key is None else pool_key.hooks,
            hook_data,
            route,
        )
        tx = client.make_swap_output(
            token0, token1, qty, qtycap, pool_key, hook_data, route, custom_nonce
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    # ------ Liquidity --------------------------------------------------------------------

    @pytest.mark.parametrize(
        "pool_key, custom_nonce",
        [
            (eth_usdc_poolkey, None),
        ],
    )
    def test_create_pool(
        self,
        client: Uniswap4,
        pool_key: PoolKey,
        custom_nonce: Optional[Nonce],
    ):
        sqrt_price_x96 = 1 << 96  # 1:1 price
        test_pool_key = PoolKey(
            currency0=pool_key.currency0,
            currency1=pool_key.currency1,
            fee=pool_key.fee + 100,
            tick_spacing=pool_key.tick_spacing + 500,
            hooks=pool_key.hooks,
        )
        tx = client.create_pool(test_pool_key, sqrt_price_x96, custom_nonce)
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "pool_key, tick_lower, tick_upper, liquidity, amount0, amount1, hook_data, custom_nonce",
        [
            (
                eth_usdc_poolkey,
                -600,
                600,
                ONE_ETH,
                ONE_ETH,
                2500 * ONE_USDC,
                b"",
                None,
            ),
        ],
    )
    def test_mint_position(
        self,
        client: Uniswap4,
        pool_key: PoolKey,
        tick_lower: int,
        tick_upper: int,
        liquidity: int,
        amount0: int,
        amount1: int,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        recipient = _addr_to_str(client.address)
        tx = client.mint_position(
            pool_key,
            tick_lower,
            tick_upper,
            liquidity,
            amount0,
            amount1,
            recipient,
            hook_data,
            custom_nonce,
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )
        test_token_id_result = client.get_minted_token_id(
            tx_receipt["transactionHash"].hex()
        )
        assert len(test_token_id_result) > 0
        TestUniswap4.test_token_id = test_token_id_result[0]
        TestUniswap4.test_mint_tx_hash = tx_receipt["transactionHash"].hex()

    def test_get_minted_token_id(
        self,
        client: Uniswap4,
    ):
        result = client.get_minted_token_id(TestUniswap4.test_mint_tx_hash)
        assert result

    def test_get_position_info(
        self,
        client: Uniswap4,
    ):
        result = client.get_position_info(TestUniswap4.test_token_id)
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
        "token0_decimals, token1_decimals",
        [(ETH_DECIMALS, USDC_DECIMALS)],
    )
    def test_get_position_value(
        self,
        client: Uniswap4,
        token0_decimals: int,
        token1_decimals: int,
    ):
        result = client.get_position_value(
            TestUniswap4.test_token_id, token0_decimals, token1_decimals
        )
        assert result

    @pytest.mark.parametrize(
        "pool_key, liquidity, amount0, amount1, hook_data, custom_nonce",
        [
            (
                eth_usdc_poolkey,
                int(0.05 * ONE_ETH),
                int(0.5 * ONE_ETH),
                1250 * ONE_USDC,
                b"",
                None,
            ),
        ],
    )
    def test_increase_liquidity(
        self,
        client: Uniswap4,
        pool_key: PoolKey,
        liquidity: int,
        amount0: int,
        amount1: int,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        recipient = _addr_to_str(client.address)
        tx = client.increase_liquidity(
            pool_key,
            TestUniswap4.test_token_id,
            amount0,
            amount1,
            liquidity,
            recipient,
            hook_data,
            custom_nonce,
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "pool_key, hook_data, custom_nonce",
        [
            (eth_usdc_poolkey, b"", None),
        ],
    )
    def test_collect_fees(
        self,
        client: Uniswap4,
        pool_key: PoolKey,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        recipient = _addr_to_str(client.address)
        tx = client.collect_fees(
            pool_key, TestUniswap4.test_token_id, recipient, hook_data, custom_nonce
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    @pytest.mark.parametrize(
        "pool_key, liquidity, amount0, amount1, hook_data, custom_nonce",
        [
            (
                eth_usdc_poolkey,
                int(0.05 * ONE_ETH),
                0,
                0,
                b"",
                None,
            ),
        ],
    )
    def test_decrease_liquidity(
        self,
        client: Uniswap4,
        pool_key: PoolKey,
        liquidity: int,
        amount0: int,
        amount1: int,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        recipient = _addr_to_str(client.address)
        tx = client.decrease_liquidity(
            pool_key,
            TestUniswap4.test_token_id,
            amount0,
            amount1,
            liquidity,
            recipient,
            hook_data,
            custom_nonce,
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    # ------ V4Pools tests ----------------------------------------------------------------
    @pytest.mark.skip(
        reason="Test node issues with fetching poolkey data, skipping for now"
    )
    def test_fetch_poolkey_data(
        self,
        pool_service: V4pools,
        first_block: int,
    ):
        result: int = pool_service.fetch_poolkey_data(
            first_block, chunk_size=500, clear_list=False, last_block=first_block + 1001
        )
        assert result == 0

    @pytest.mark.parametrize(
        "test_data_file_path",
        [
            "pool_list.test",
        ],
    )
    def test_load_poolkeys_list(
        self,
        pool_service: V4pools,
        test_data_file_path: str,
    ):
        test_data_file_full_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), test_data_file_path
        )
        pool_service.load_poolkeys_list(test_data_file_full_path)
        assert len(pool_service.poolkeys_list) > 0

    @pytest.mark.parametrize(
        "test_data_file_path",
        [
            "pool_list_dump.test",
        ],
    )
    def test_save_poolkeys_list(
        self,
        pool_service: V4pools,
        test_data_file_path: str,
        tmp_path,
    ):
        test_data_file_full_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "pool_list.test"
        )
        pool_service.load_poolkeys_list(test_data_file_full_path)
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        test_data_dump_full_path = temp_dir / test_data_file_path
        pool_service.save_poolkeys_list(test_data_dump_full_path)
        assert len(test_data_dump_full_path.read_text()) > 0

    @pytest.mark.parametrize(
        "currecy0, currency1",
        [
            (ETH_ADDRESS, USDC_ADDRESS),
            (USDC_ADDRESS, USDT_ADDRESS),
        ],
    )
    def test_get_poolkeys_sublist(
        self,
        pool_service: V4pools,
        currecy0: str,
        currency1: str,
    ):
        test_data_file_full_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "pool_list.test"
        )
        pool_service.load_poolkeys_list(test_data_file_full_path)

        result = pool_service.get_poolkeys_sublist(currecy0, currency1)
        assert len(result) > 0

    # ------ StateView tests --------------------------------------------------------------
    # Read methods
    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
            (
                USDC_ADDRESS,
                USDT_ADDRESS,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_liquidity(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_liquidity(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
        )
        assert result

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_slot0(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_slot0(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
        )
        assert result
        TestUniswap4.test_tick = int(result["tick"])

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
            (
                USDC_ADDRESS,
                USDT_ADDRESS,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_fee_growth_globals(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_fee_growth_globals(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
        )
        assert result

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
            (
                USDC_ADDRESS,
                USDT_ADDRESS,
                USDC_USDT_FEE,
                USDC_USDT_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_fee_growth_inside(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_fee_growth_inside(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
            TestUniswap4.test_tick - tick_spacing * 50,
            TestUniswap4.test_tick + tick_spacing * 50,
        )
        assert result

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_position_info(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_position_info(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
            _addr_to_str(client.address),
            -600,
            600,
            TestUniswap4.test_token_id,
        )
        assert result

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_tick_bitmap(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_tick_bitmap(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
            -30000,
        )
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_tick_fee_growth_outside(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_tick_fee_growth_outside(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
            TestUniswap4.test_tick,
        )
        assert result

    @pytest.mark.parametrize(
        "token0, token1, fee, tick_spacing, hooks",
        [
            (
                ETH_ADDRESS,
                USDC_ADDRESS,
                ETH_USDC_FEE,
                ETH_USDC_TICK_SPACING,
                ZERO_HOOK,
            ),
        ],
    )
    def test_stateview_get_tick_pool_info(
        self,
        client: Uniswap4,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ):
        result = client.stateview_get_tick_pool_info(
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
            TestUniswap4.test_tick,
        )
        assert result

    # ------ PositionDescriptor tests -----------------------------------------------------
    # Read methods
    @pytest.mark.parametrize(
        "token0",
        [
            (USDC_ADDRESS),
            (USDT_ADDRESS),
        ],
    )
    def test_position_descriptor_get_currency_ratio_priority(
        self, client: Uniswap4, token0: str
    ):
        result = client.position_descriptor_get_currency_ratio_priority(token0)
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "token0, token1",
        [
            (USDC_ADDRESS, ETH_ADDRESS),
            (USDT_ADDRESS, ETH_ADDRESS),
        ],
    )
    def test_position_descriptor_get_flip_ratio(
        self, client: Uniswap4, token0: str, token1: str
    ):
        result = client.position_descriptor_get_flip_ratio(token0, token1)
        assert isinstance(result, bool)

    def test_position_descriptor_get_native_currency_label(self, client: Uniswap4):
        result = client.position_descriptor_get_native_currency_label()
        assert result

    def test_position_descriptor_get_pool_manager(self, client: Uniswap4):
        result = client.position_descriptor_get_pool_manager()
        assert result

    def test_position_descriptor_get_token_uri(self, client: Uniswap4):
        result = client.position_descriptor_get_token_uri(
            _addr_to_str(client.position_manager_address), TestUniswap4.test_token_id
        )
        assert result

    def test_position_descriptor_get_wrapped_native_address(self, client: Uniswap4):
        result = client.position_descriptor_get_wrapped_native_address()
        assert result

    # ------ PositionManager tests --------------------------------------------------------
    # Read methods

    # Write methods

    # ------ PoolManager tests ------------------------------------------------------------
    # Read methods

    # Write methods

    # Burn test position.
    @pytest.mark.parametrize(
        "pool_key, hook_data, custom_nonce",
        [
            (eth_usdc_poolkey, b"", None),
        ],
    )
    def test_burn_position(
        self,
        client: Uniswap4,
        pool_key: PoolKey,
        hook_data: bytes,
        custom_nonce: Optional[Nonce],
    ):
        recipient = _addr_to_str(client.address)
        # Removing liquidity before burning position, otherwise burn will revert since position is not empty
        tx = client.decrease_liquidity(
            pool_key,
            TestUniswap4.test_token_id,
            0,
            0,
            client.stateview_get_position_info(
                pool_key.currency0,
                pool_key.currency1,
                pool_key.fee,
                pool_key.tick_spacing,
                pool_key.hooks,
                recipient,
                -600,
                600,
                TestUniswap4.test_token_id,
            )["liquidity"],
            recipient,
            hook_data,
            custom_nonce,
        )
        assert tx
        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

        # Now burn the position
        tx = client.burn_position(
            pool_key,
            TestUniswap4.test_token_id,
            0,
            0,
            recipient,
            hook_data,
            custom_nonce,
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    # ------ UniversalRouter tests --------------------------------------------------------
    def test_universal_router_execute_simple_command(
        self,
        client: Uniswap4,
    ):
        commands: List = [
            universal_router_commands["WRAP_ETH"],
        ]
        actions: List = [
            [],
        ]
        params: List = [
            [
                [
                    _addr_to_str(client.address),
                    1 * ONE_ETH,
                ],
            ],
        ]
        tx = client.universal_router_execute(
            commands, actions, params, ether_amount=1 * ONE_ETH
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    def test_universal_router_execute_composite_command(
        self,
        client: Uniswap4,
    ):
        if eth_usdc_poolkey.currency0.lower() < eth_usdc_poolkey.currency1.lower():
            zero_for_one: bool = True
        else:
            zero_for_one = False
        qty: int = 1 * ONE_ETH
        qtycap: int = client.get_quote_exact_input_single(
            eth_usdc_poolkey.currency0,
            eth_usdc_poolkey.currency1,
            qty,
            eth_usdc_poolkey.fee,
            eth_usdc_poolkey.tick_spacing,
            eth_usdc_poolkey.hooks,
            b"",
        )
        qtycap = int((1 - client.max_slippage) * qtycap)

        commands: List = [
            universal_router_commands["V4_SWAP"],
        ]
        actions: List = [
            [
                v4_actions["SWAP_EXACT_IN_SINGLE"],
                v4_actions["SETTLE_ALL"],
                v4_actions["TAKE_ALL"],
            ],
        ]

        params: List = [
            [
                [
                    (
                        astuple(eth_usdc_poolkey),
                        zero_for_one,
                        qty,
                        qtycap,
                        0,  # min_hop_price_x_36
                        b"",
                    )
                ],
                [
                    eth_usdc_poolkey.currency0,
                    qty,
                ],
                [
                    eth_usdc_poolkey.currency1,
                    qtycap,
                ],
            ],
        ]
        tx = client.universal_router_execute(
            commands, actions, params, ether_amount=qty
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )

    def test_universal_router_execute_multiaction(
        self,
        client: Uniswap4,
    ):
        if eth_usdc_poolkey.currency0.lower() < eth_usdc_poolkey.currency1.lower():
            zero_for_one: bool = True
        else:
            zero_for_one = False
        qty: int = 1 * ONE_ETH
        qtycap: int = client.get_quote_exact_input_single(
            eth_usdc_poolkey.currency0,
            eth_usdc_poolkey.currency1,
            qty,
            eth_usdc_poolkey.fee,
            eth_usdc_poolkey.tick_spacing,
            eth_usdc_poolkey.hooks,
            b"",
        )
        qtycap = int((1 - client.max_slippage) * qtycap)
        ether_value = ONE_ETH

        # Executes a WRAP_ETH followed by a V4_SWAP in the same transaction
        commands: List = [
            universal_router_commands["WRAP_ETH"],
            universal_router_commands["V4_SWAP"],
        ]

        # List of actions for each command, in this case we have 0 action for the WRAP_ETH command and 3 actions for the V4_SWAP command (swap, settle and take)
        # As WRAP_ETH command does not require any action, we pass an empty list for it
        actions: List = [
            [],
            [
                v4_actions["SWAP_EXACT_IN_SINGLE"],
                v4_actions["SETTLE_ALL"],
                v4_actions["TAKE_ALL"],
            ],
        ]

        # List of parameters for each action, the first element of the list corresponds to the parameters for the WRAP_ETH command (recipient and amount),
        # and the second element corresponds to the parameters for each of the 3 actions of the V4_SWAP command
        params: List = [
            [
                [
                    _addr_to_str(client.address),
                    ether_value,
                ],
            ],
            [
                [
                    (
                        astuple(eth_usdc_poolkey),
                        zero_for_one,
                        qty,
                        qtycap,
                        0,  # min_hop_price_x_36
                        b"",
                    )
                ],
                [
                    eth_usdc_poolkey.currency0,
                    qty,
                ],
                [
                    eth_usdc_poolkey.currency1,
                    qtycap,
                ],
            ],
        ]
        # Both commands use ether as input token, so we set the ether_amount to the sum of the ether required for each commands
        tx = client.universal_router_execute(
            commands, actions, params, ether_amount=(ether_value + qty)
        )
        assert tx

        tx_receipt = client.w3.eth.wait_for_transaction_receipt(
            tx, timeout=RECEIPT_TIMEOUT
        )
        assert tx_receipt["status"], (
            f"Transaction failed with status {tx_receipt['status']}; tx_receipt: {tx_receipt}"
        )
