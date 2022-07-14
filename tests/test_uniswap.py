import pytest
import os
import subprocess
import shutil
import logging
from typing import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from time import sleep

from web3 import Web3
from web3.exceptions import NameNotFound

from uniswap import Uniswap
from uniswap.constants import ETH_ADDRESS
from uniswap.exceptions import InsufficientBalance
from uniswap.util import _str_to_addr
from uniswap.tokens import get_tokens


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENV_UNISWAP_VERSION = os.getenv("UNISWAP_VERSION", None)
if ENV_UNISWAP_VERSION:
    UNISWAP_VERSIONS = [int(ENV_UNISWAP_VERSION)]
else:
    UNISWAP_VERSIONS = [1, 2, 3]

RECEIPT_TIMEOUT = 5


@dataclass
class GanacheInstance:
    provider: str
    eth_address: str
    eth_privkey: str


@pytest.fixture(scope="module", params=UNISWAP_VERSIONS)
def client(request, web3: Web3, ganache: GanacheInstance):
    return Uniswap(
        ganache.eth_address,
        ganache.eth_privkey,
        web3=web3,
        version=request.param,
        use_estimate_gas=False,  # see note in _build_and_send_tx
    )


@pytest.fixture(scope="function", params=UNISWAP_VERSIONS)
def tokens(client: Uniswap):
    return get_tokens(client.netname)


@pytest.fixture(scope="module")
def test_assets(client: Uniswap):
    """
    Buy some DAI and USDC to test with.
    """
    tokens = get_tokens(client.netname)

    for token_name, amount in [("DAI", 100 * 10 ** 18), ("USDC", 100 * 10 ** 6)]:
        token_addr = tokens[token_name]
        price = client.get_price_output(_str_to_addr(ETH_ADDRESS), token_addr, amount)
        logger.info(f"Cost of {amount} {token_name}: {price}")
        logger.info("Buying...")

        tx = client.make_trade_output(tokens["ETH"], token_addr, amount)
        client.w3.eth.wait_for_transaction_receipt(tx, timeout=RECEIPT_TIMEOUT)


@pytest.fixture(scope="module")
def web3(ganache: GanacheInstance):
    w3 = Web3(Web3.HTTPProvider(ganache.provider, request_kwargs={"timeout": 30}))
    if 1 != int(w3.net.version):
        logger.warning("PROVIDER was not a mainnet provider, which the tests require")
    return w3


@pytest.fixture(scope="module")
def ganache() -> Generator[GanacheInstance, None, None]:
    """Fixture that runs ganache which has forked off mainnet"""
    if not shutil.which("ganache"):
        raise Exception(
            "ganache was not found in PATH, you can install it with `npm install -g ganache`"
        )
    if "PROVIDER" not in os.environ:
        raise Exception(
            "PROVIDER was not set, you need to set it to a mainnet provider (such as Infura) so that we can fork off our testnet"
        )

    port = 10999
    defaultGasPrice = 1000_000_000_000  # 1000 gwei
    p = subprocess.Popen(
        f"""ganache
        --port {port}
        --wallet.seed test
        --chain.networkId 1
        --chain.chainId 1
        --fork.url {os.environ['PROVIDER']}
        --miner.defaultGasPrice {defaultGasPrice}
        --miner.instamine "strict"
        """.replace(
            "\n", " "
        ),
        shell=True,
    )
    # Address #1 when ganache is run with `--wallet.seed test`, it starts with 1000 ETH
    eth_address = "0x94e3361495bD110114ac0b6e35Ed75E77E6a6cFA"
    eth_privkey = "0x6f1313062db38875fb01ee52682cbf6a8420e92bfbc578c5d4fdc0a32c50266f"
    sleep(3)
    yield GanacheInstance(f"http://127.0.0.1:{port}", eth_address, eth_privkey)
    p.kill()
    p.wait()


@contextmanager
def does_not_raise():
    yield


ONE_ETH = 10 ** 18
ONE_USDC = 10 ** 6

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


# TODO: Change pytest.param(..., mark=pytest.mark.xfail) to the expectation/raises method
@pytest.mark.usefixtures("client", "web3")
class TestUniswap(object):

    # ------ Exchange ------------------------------------------------------------------
    def test_get_fee_maker(self, client: Uniswap):
        if client.version not in [1, 2]:
            pytest.skip("Tested method not supported in this Uniswap version")
        r = client.get_fee_maker()
        assert r == 0

    def test_get_fee_taker(self, client: Uniswap):
        if client.version not in [1, 2]:
            pytest.skip("Tested method not supported in this Uniswap version")
        r = client.get_fee_taker()
        assert r == 0.003

    # ------ Market --------------------------------------------------------------------
    @pytest.mark.parametrize(
        "token0, token1, qty, kwargs",
        [
            ("ETH", "UNI", ONE_ETH, {}),
            ("UNI", "ETH", ONE_ETH, {}),
            ("ETH", "DAI", ONE_ETH, {}),
            ("DAI", "ETH", ONE_ETH, {}),
            ("ETH", "UNI", 2 * ONE_ETH, {}),
            ("UNI", "ETH", 2 * ONE_ETH, {}),
            ("WETH", "DAI", ONE_ETH, {}),
            ("DAI", "WETH", ONE_ETH, {}),
            ("DAI", "USDC", ONE_ETH, {"fee": 500}),
        ],
    )
    def test_get_price_input(self, client, tokens, token0, token1, qty, kwargs):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version == 1 and ETH_ADDRESS not in [token0, token1]:
            pytest.skip("Not supported in this version of Uniswap")
        r = client.get_price_input(token0, token1, qty, **kwargs)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, qty, kwargs",
        [
            ("ETH", "UNI", ONE_ETH, {}),
            ("UNI", "ETH", ONE_ETH // 100, {}),
            ("ETH", "DAI", ONE_ETH, {}),
            ("DAI", "ETH", ONE_ETH, {}),
            ("ETH", "UNI", 2 * ONE_ETH, {}),
            ("WETH", "DAI", ONE_ETH, {}),
            ("DAI", "WETH", ONE_ETH, {}),
            ("DAI", "USDC", ONE_USDC, {"fee": 500}),
        ],
    )
    def test_get_price_output(self, client, tokens, token0, token1, qty, kwargs):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version == 1 and ETH_ADDRESS not in [token0, token1]:
            pytest.skip("Not supported in this version of Uniswap")
        r = client.get_price_output(token0, token1, qty, **kwargs)
        assert r

    # ------ ERC20 Pool ----------------------------------------------------------------
    @pytest.mark.parametrize("token", [("UNI"), ("DAI")])
    def test_get_ex_eth_balance(
        self,
        client: Uniswap,
        tokens,
        token,
    ):
        if not client.version == 1:
            pytest.skip("Only supported on Uniswap v1")
        r = client.get_ex_eth_balance(tokens[token])
        assert r

    @pytest.mark.parametrize("token", [("UNI"), ("DAI")])
    def test_get_ex_token_balance(
        self,
        client: Uniswap,
        tokens,
        token,
    ):
        if not client.version == 1:
            pytest.skip("Only supported on Uniswap v1")
        r = client.get_ex_token_balance(tokens[token])
        assert r

    @pytest.mark.parametrize("token", [("UNI"), ("DAI")])
    def test_get_exchange_rate(
        self,
        client: Uniswap,
        tokens,
        token,
    ):
        if not client.version == 1:
            pytest.skip("Only supported on Uniswap v1")
        r = client.get_exchange_rate(tokens[token])
        assert r

    # ------ Liquidity -----------------------------------------------------------------
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "token, max_eth",
        [
            ("UNI", 0.00001 * ONE_ETH),
            ("DAI", 0.00001 * ONE_ETH),
        ],
    )
    def test_add_liquidity(self, client: Uniswap, tokens, web3: Web3, token, max_eth):
        token = tokens[token]
        r = client.add_liquidity(token, max_eth)
        tx = web3.eth.wait_for_transaction_receipt(r, timeout=RECEIPT_TIMEOUT)
        assert tx["status"]

    @pytest.mark.skip
    @pytest.mark.parametrize(
        "token, max_token, expectation",
        [
            ("UNI", 0.00001 * ONE_ETH, does_not_raise()),
            ("DAI", 0.00001 * ONE_ETH, does_not_raise()),
        ],
    )
    def test_remove_liquidity(
        self, client: Uniswap, web3: Web3, tokens, token, max_token, expectation
    ):
        token = tokens[token]
        with expectation:
            r = client.remove_liquidity(tokens[token], max_token)
            tx = web3.eth.wait_for_transaction_receipt(r)
            assert tx["status"]

    # ------ Make Trade ----------------------------------------------------------------
    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient, expectation",
        [
            # ETH -> Token
            ("ETH", "DAI", ONE_ETH, None, does_not_raise),
            # Token -> Token
            ("DAI", "USDC", ONE_ETH, None, does_not_raise),
            # Token -> ETH
            ("USDC", "ETH", 100 * ONE_USDC, None, does_not_raise),
            # ("ETH", "UNI", 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise),
            # ("UNI", "ETH", 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise),
            # ("DAI", "UNI", 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise),
        ],
    )
    def test_make_trade(
        self,
        client: Uniswap,
        web3: Web3,
        tokens,
        test_assets,
        input_token,
        output_token,
        qty: int,
        recipient,
        expectation,
    ):
        input_token, output_token = tokens[input_token], tokens[output_token]
        if client.version == 1 and ETH_ADDRESS not in [input_token, output_token]:
            pytest.skip(
                "Not supported in this version of Uniswap, or at least no liquidity"
            )
        with expectation():
            bal_in_before = client.get_token_balance(input_token)

            txid = client.make_trade(input_token, output_token, qty, recipient)
            tx = web3.eth.wait_for_transaction_receipt(txid, timeout=RECEIPT_TIMEOUT)
            assert tx["status"]

            # TODO: Checks for ETH, taking gas into account
            bal_in_after = client.get_token_balance(input_token)
            if input_token != tokens["ETH"]:
                assert bal_in_before - qty == bal_in_after

    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient, expectation",
        [
            # ETH -> Token
            ("ETH", "DAI", 10 ** 18, None, does_not_raise),
            # Token -> Token
            ("DAI", "USDC", ONE_USDC, None, does_not_raise),
            # Token -> ETH
            ("DAI", "ETH", 10 ** 16, None, does_not_raise),
            # FIXME: These should probably be uncommented eventually
            # ("ETH", "UNI", int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # ("UNI", "ETH", int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # ("DAI", "UNI", int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            (
                "DAI",
                "ETH",
                10 * 10 ** 18,
                None,
                lambda: pytest.raises(InsufficientBalance),
            ),
        ],
    )
    def test_make_trade_output(
        self,
        client: Uniswap,
        web3: Web3,
        tokens,
        test_assets,
        input_token,
        output_token,
        qty: int,
        recipient,
        expectation,
    ):
        input_token, output_token = tokens[input_token], tokens[output_token]
        if client.version == 1 and ETH_ADDRESS not in [input_token, output_token]:
            pytest.skip(
                "Not supported in this version of Uniswap, or at least no liquidity"
            )
        with expectation():
            balance_before = client.get_token_balance(output_token)

            r = client.make_trade_output(input_token, output_token, qty, recipient)
            tx = web3.eth.wait_for_transaction_receipt(r, timeout=RECEIPT_TIMEOUT)
            assert tx["status"]

            # TODO: Checks for ETH, taking gas into account
            balance_after = client.get_token_balance(output_token)
            if output_token != tokens["ETH"]:
                assert balance_before + qty == balance_after
