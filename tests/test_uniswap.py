import pytest
import os
import subprocess
import shutil
from typing import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from time import sleep

from web3 import Web3

from uniswap import Uniswap, InvalidToken, InsufficientBalance


@dataclass
class GanacheInstance:
    provider: str
    eth_address: str
    eth_privkey: str


@pytest.fixture(scope="module", params=[1, 2])
def client(request, web3: Web3, ganache: GanacheInstance):
    uniswap = Uniswap(
        ganache.eth_address, ganache.eth_privkey, web3=web3, version=request.param
    )
    uniswap._buy_test_assets()
    return uniswap


@pytest.fixture(scope="module")
def web3(ganache: GanacheInstance):
    return Web3(Web3.HTTPProvider(ganache.provider, request_kwargs={"timeout": 60}))


@pytest.fixture(scope="module")
def ganache() -> Generator[GanacheInstance, None, None]:
    """Fixture that runs ganache-cli which has forked off mainnet"""
    if not shutil.which("ganache-cli"):
        raise Exception(
            "ganache-cli was not found in PATH, you can install it with `npm install -g ganache-cli`"
        )
    if "MAINNET_PROVIDER" not in os.environ:
        raise Exception(
            "MAINNET_PROVIDER was not set, you need to set it to a mainnet provider (such as Infura) so that we can fork off our testnet"
        )

    port = 10999
    p = subprocess.Popen(
        f"ganache-cli --port {port} -s test --networkId 1 --fork {os.environ['MAINNET_PROVIDER']}",
        shell=True,
    )
    # Address #1 when ganache is run with `-s test`, it starts with 100 ETH
    eth_address = "0x94e3361495bD110114ac0b6e35Ed75E77E6a6cFA"
    eth_privkey = "0x6f1313062db38875fb01ee52682cbf6a8420e92bfbc578c5d4fdc0a32c50266f"
    sleep(3)
    yield GanacheInstance(f"http://127.0.0.1:{port}", eth_address, eth_privkey)
    p.kill()
    p.wait()


@contextmanager
def does_not_raise():
    yield


# TODO: Change pytest.param(..., mark=pytest.mark.xfail) to the expectation/raises method
@pytest.mark.usefixtures("client", "web3")
class TestUniswap(object):
    ONE_WEI = 1
    ONE_ETH = 10 ** 18 * ONE_WEI

    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

    # TODO: Detect mainnet vs rinkeby and set accordingly, like _get_token_addresses in the Uniswap class
    # For Mainnet testing (with `ganache-cli --fork` as per the ganache fixture)
    eth = "0x0000000000000000000000000000000000000000"
    weth = Web3.toChecksumAddress("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
    bat = Web3.toChecksumAddress("0x0D8775F648430679A709E98d2b0Cb6250d2887EF")
    dai = Web3.toChecksumAddress("0x6b175474e89094c44da98b954eedeac495271d0f")

    # For Rinkeby
    # eth = "0x0000000000000000000000000000000000000000"
    # bat = "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B"
    # dai = "0x2448eE2641d78CC42D7AD76498917359D961A783"

    # ------ Exchange ------------------------------------------------------------------
    def test_get_fee_maker(self, client: Uniswap):
        r = client.get_fee_maker()
        assert r == 0

    def test_get_fee_taker(self, client: Uniswap):
        r = client.get_fee_taker()
        assert r == 0.003

    # ------ Market --------------------------------------------------------------------
    @pytest.mark.parametrize(
        "token, qty",
        [
            (bat, ONE_ETH),
            (dai, ONE_ETH),
            (bat, 2 * ONE_ETH),
            pytest.param("btc", ONE_ETH, marks=pytest.mark.xfail),
        ],
    )
    def test_get_eth_token_input_price(self, client, token, qty):
        r = client.get_eth_token_input_price(token, qty)
        assert r

    @pytest.mark.parametrize(
        "token, qty",
        [
            (bat, ONE_ETH),
            (dai, ONE_ETH),
            (bat, 2 * ONE_ETH),
            pytest.param("btc", ONE_ETH, marks=pytest.mark.xfail),
        ],
    )
    def test_get_token_eth_input_price(self, client, token, qty):
        r = client.get_token_eth_input_price(token, qty)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, qty",
        [
            (bat, dai, ONE_ETH),
            (dai, bat, ONE_ETH),
            (bat, dai, 2 * ONE_ETH),
            (weth, dai, ONE_ETH),
            (dai, weth, ONE_ETH),
        ],
    )
    def test_get_token_token_input_price(self, client, token0, token1, qty):
        if not client.version == 2:
            pytest.skip("Tested method only supported on Uniswap v2")
        r = client.get_token_token_input_price(token0, token1, qty)
        assert r

    @pytest.mark.parametrize(
        "token, qty",
        [
            (bat, ONE_ETH),
            (dai, ONE_ETH),
            (bat, 2 * ONE_ETH),
            pytest.param("btc", ONE_ETH, marks=pytest.mark.xfail),
        ],
    )
    def test_get_eth_token_output_price(self, client, token, qty):
        r = client.get_eth_token_output_price(token, qty)
        assert r

    @pytest.mark.parametrize(
        "token, qty",
        [
            (bat, ONE_ETH),
            (dai, ONE_ETH),
            (bat, 2 * ONE_ETH),
            pytest.param("btc", ONE_ETH, marks=pytest.mark.xfail),
        ],
    )
    def test_get_token_eth_output_price(self, client, token, qty):
        r = client.get_token_eth_output_price(token, qty)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, qty",
        [
            (bat, dai, ONE_ETH),
            (dai, bat, ONE_ETH),
            (bat, dai, 2 * ONE_ETH),
            (weth, dai, ONE_ETH),
            (dai, weth, ONE_ETH),
        ],
    )
    def test_get_token_token_output_price(self, client, token0, token1, qty):
        if not client.version == 2:
            pytest.skip("Tested method only supported on Uniswap v2")
        r = client.get_token_token_output_price(token0, token1, qty)
        assert r

    # ------ ERC20 Pool ----------------------------------------------------------------
    @pytest.mark.parametrize("token", [(bat), (dai)])
    def test_get_ex_eth_balance(
        self, client: Uniswap, token,
    ):
        if not client.version == 1:
            pytest.skip("Tested method only supported on Uniswap v1")
        r = client.get_ex_eth_balance(token)
        assert r

    @pytest.mark.parametrize("token", [(bat), (dai)])
    def test_get_ex_token_balance(
        self, client: Uniswap, token,
    ):
        if not client.version == 1:
            pytest.skip("Tested method only supported on Uniswap v1")
        r = client.get_ex_token_balance(token)
        assert r

    @pytest.mark.parametrize("token", [(bat), (dai)])
    def get_exchange_rate(
        self, client: Uniswap, token,
    ):
        r = client.get_exchange_rate(token)
        assert r

    # ------ Liquidity -----------------------------------------------------------------
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "token, max_eth",
        [
            (bat, 0.00001 * ONE_ETH),
            (dai, 0.00001 * ONE_ETH),
            pytest.param("btc", ONE_ETH, marks=pytest.mark.xfail),
        ],
    )
    def test_add_liquidity(self, client: Uniswap, web3: Web3, token, max_eth):
        r = client.add_liquidity(token, max_eth)
        tx = web3.eth.waitForTransactionReceipt(r, timeout=6000)
        assert tx.status  # type: ignore

    @pytest.mark.skip
    @pytest.mark.parametrize(
        "token, max_token, expectation",
        [
            (bat, 0.00001 * ONE_ETH, does_not_raise()),
            (dai, 0.00001 * ONE_ETH, does_not_raise()),
            ("btc", ONE_ETH, pytest.raises(InvalidToken)),
        ],
    )
    def test_remove_liquidity(
        self, client: Uniswap, web3: Web3, token, max_token, expectation
    ):
        with expectation:
            r = client.remove_liquidity(token, max_token)
            tx = web3.eth.waitForTransactionReceipt(r)
            assert tx.status  # type: ignore

    # ------ Make Trade ----------------------------------------------------------------
    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient, expectation",
        [
            # ETH -> Token
            (eth, bat, 1_000_000_000 * ONE_WEI, None, does_not_raise),
            # Token -> Token
            (bat, dai, 1_000_000_000 * ONE_WEI, None, does_not_raise),
            # Token -> ETH
            (bat, eth, 1_000_000 * ONE_WEI, None, does_not_raise),
            # (eth, bat, 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise),
            # (bat, eth, 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise),
            # (dai, bat, 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise),
            (dai, "btc", ONE_ETH, None, lambda: pytest.raises(InvalidToken)),
        ],
    )
    def test_make_trade(
        self,
        client: Uniswap,
        web3: Web3,
        input_token,
        output_token,
        qty: int,
        recipient,
        expectation,
    ):
        with expectation():
            bal_in_before = client.get_token_balance(input_token)

            r = client.make_trade(input_token, output_token, qty, recipient)
            tx = web3.eth.waitForTransactionReceipt(r)
            assert tx.status  # type: ignore

            # TODO: Checks for ETH, taking gas into account
            bal_in_after = client.get_token_balance(input_token)
            if input_token != self.eth:
                assert bal_in_before - qty == bal_in_after

    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient, expectation",
        [
            # ETH -> Token
            (eth, bat, 1_000_000_000 * ONE_WEI, None, does_not_raise),
            # Token -> Token
            (bat, dai, 1_000_000_000 * ONE_WEI, None, does_not_raise),
            # Token -> ETH
            (dai, eth, 1_000_000 * ONE_WEI, None, does_not_raise),
            # FIXME: These should probably be uncommented eventually
            # (eth, bat, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # (bat, eth, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # (dai, bat, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            (
                dai,
                eth,
                10 ** 18 * ONE_WEI,
                None,
                lambda: pytest.raises(InsufficientBalance),
            ),
            (dai, "btc", ONE_ETH, None, lambda: pytest.raises(InvalidToken)),
        ],
    )
    def test_make_trade_output(
        self,
        client: Uniswap,
        web3: Web3,
        input_token,
        output_token,
        qty: int,
        recipient,
        expectation,
    ):
        with expectation():
            balance_before = client.get_token_balance(output_token)

            r = client.make_trade_output(input_token, output_token, qty, recipient)
            tx = web3.eth.waitForTransactionReceipt(r, timeout=30)
            assert tx.status  # type: ignore

            # TODO: Checks for ETH, taking gas into account
            balance_after = client.get_token_balance(output_token)
            if output_token != self.eth:
                assert balance_before + qty == balance_after
