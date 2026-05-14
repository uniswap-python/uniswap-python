import logging
import os
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from time import sleep
from typing import Generator

import pytest
from web3 import Web3

from uniswap import Uniswap4
from uniswap.constants import ETH_ADDRESS, ZERO_HOOK
from uniswap.types import PoolKey

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
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
ETH_USDC_FEE = 500
ETH_USDC_TICK_SPACING = 10
USDC_USDT_FEE = 10
USDC_USDT_TICK_SPACING = 1


@dataclass
class AnvilInstance:
    provider: str
    eth_address: str
    eth_privkey: str


@pytest.fixture(scope="module")
def eth_usdc_poolkey() -> PoolKey:
    return PoolKey(
        currency0=ETH_ADDRESS,  # ETH
        currency1=USDC_ADDRESS,  # USDC
        fee=ETH_USDC_FEE,
        tick_spacing=ETH_USDC_TICK_SPACING,
        hooks=ZERO_HOOK,
    )


@pytest.fixture(scope="module")
def usdc_usdt_poolkey() -> PoolKey:
    return PoolKey(
        currency0=USDC_ADDRESS,  # USDC
        currency1=USDT_ADDRESS,  # USDT
        fee=USDC_USDT_FEE,
        tick_spacing=USDC_USDT_TICK_SPACING,
        hooks=ZERO_HOOK,
    )


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
    # ------ Market --------------------------------------------------------------------
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
