import pytest
import os
from typing import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from web3 import Web3
from web3.types import Wei

from uniswap import Uniswap, InvalidToken, InsufficientBalance


@dataclass
class GanacheInstance:
    provider: str
    eth_address: str
    eth_privkey: str


@pytest.fixture(scope="module")
def client(web3: Web3, ganache: GanacheInstance):
    uniswap = Uniswap(ganache.eth_address, ganache.eth_privkey, web3=web3)
    uniswap._buy_test_assets()
    return uniswap


@pytest.fixture(scope="module")
def web3(ganache: GanacheInstance):
    return Web3(Web3.HTTPProvider(ganache.provider, request_kwargs={"timeout": 60}))


@pytest.fixture(scope="module")
def ganache() -> Generator[GanacheInstance, None, None]:
    """Fixture that runs ganache which has forked off mainnet"""
    import subprocess
    from time import sleep

    assert "MAINNET_PROVIDER" in os.environ

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

    # Why this zero address?
    ZERO_ADDRESS = "0xD6aE8250b8348C94847280928c79fb3b63cA453e"

    eth = "0x0000000000000000000000000000000000000000"

    # TODO: Detect mainnet vs rinkeby and set accordingly
    # For Mainnet testing (with `ganache-cli --fork` as per the ganache fixture)
    bat = Web3.toChecksumAddress("0x0D8775F648430679A709E98d2b0Cb6250d2887EF")
    dai = Web3.toChecksumAddress("0x6b175474e89094c44da98b954eedeac495271d0f")

    # For Rinkeby
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

    # ------ ERC20 Pool ----------------------------------------------------------------
    @pytest.mark.parametrize("token", [(bat), (dai)])
    def test_get_ex_eth_balance(
        self, client: Uniswap, token,
    ):
        r = client.get_ex_eth_balance(token)
        assert r

    @pytest.mark.parametrize("token", [(bat), (dai)])
    def test_get_ex_token_balance(
        self, client: Uniswap, token,
    ):
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
            (eth, bat, 1_000_000_000 * ONE_WEI, None, does_not_raise()),
            # Token -> Token
            (dai, bat, 1_000_000_000 * ONE_WEI, None, does_not_raise()),
            # Token -> ETH
            (bat, eth, 1_000_000 * ONE_WEI, None, does_not_raise()),
            # (eth, bat, 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise()),
            # (bat, eth, 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise()),
            # (dai, bat, 0.00001 * ONE_ETH, ZERO_ADDRESS, does_not_raise()),
            (dai, "btc", ONE_ETH, None, pytest.raises(InvalidToken)),
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
        with expectation:
            # bal_in_before = client.get_token_balance(input_token)

            r = client.make_trade(input_token, output_token, qty, recipient)
            tx = web3.eth.waitForTransactionReceipt(r)
            assert tx.status  # type: ignore

            # bal_in_after = client.get_token_balance(input_token)
            # assert bal_in_before - qty == bal_in_after

    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient, expectation",
        [
            # ETH -> Token
            (eth, bat, 1_000_000_000 * ONE_WEI, None, does_not_raise()),
            # Token -> Token
            (bat, dai, 1_000_000_000 * ONE_WEI, None, does_not_raise()),
            # Token -> ETH
            (dai, eth, 1_000_000 * ONE_WEI, None, does_not_raise()),
            # FIXME: These should probably be uncommented eventually
            # (eth, bat, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # (bat, eth, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # (dai, bat, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            (dai, eth, 10 ** 18 * ONE_WEI, None, pytest.raises(InsufficientBalance)),
            (dai, "btc", ONE_ETH, None, pytest.raises(InvalidToken)),
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
        with expectation:
            # balance_before = client.get_token_balance(output_token)

            r = client.make_trade_output(input_token, output_token, qty, recipient)
            tx = web3.eth.waitForTransactionReceipt(r, timeout=30)
            assert tx.status  # type: ignore

            # balance_after = client.get_token_balance(output_token)
            # assert balance_before == balance_after + qty
