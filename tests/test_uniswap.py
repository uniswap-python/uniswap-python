import pytest
import time
import os

from web3 import Web3
from web3.types import Wei

from uniswap import Uniswap


@pytest.fixture(scope="module")
def client(web3: Web3):
    address = os.environ["ETH_ADDRESS"]
    priv_key = os.environ["ETH_PRIV_KEY"]

    return Uniswap(address, priv_key, web3=web3)


@pytest.fixture(scope="module")
def web3():
    if "TESTNET_PROVIDER" in os.environ:
        provider = os.environ["TESTNET_PROVIDER"]
        return Web3(Web3.HTTPProvider(provider, request_kwargs={"timeout": 60}))
    else:
        # pylint: disable=import-outside-toplevel
        from web3.auto.infura.rinkeby import w3

        return w3


@pytest.mark.usefixtures("client", "web3")
class TestUniswap(object):

    ONE_WEI = 1
    ONE_ETH = 10 ** 18 * ONE_WEI
    ZERO_ADDRESS = "0xD6aE8250b8348C94847280928c79fb3b63cA453e"
    eth = "0x0000000000000000000000000000000000000000"
    bat = "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B"
    dai = "0x2448eE2641d78CC42D7AD76498917359D961A783"

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
        assert bool(r)

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
        assert bool(r)

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
        assert bool(r)

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
        assert bool(r)

    # ------ ERC20 Pool ----------------------------------------------------------------
    @pytest.mark.parametrize("token", [(bat), (dai)])
    def test_get_eth_balance(
        self, client: Uniswap, token,
    ):
        r = client.get_eth_balance(token)
        assert bool(r)

    @pytest.mark.parametrize("token", [(bat), (dai)])
    def test_get_token_balance(
        self, client: Uniswap, token,
    ):
        r = client.get_token_balance(token)
        assert bool(r)

    @pytest.mark.parametrize("token", [(bat), (dai)])
    def get_exchange_rate(
        self, client: Uniswap, token,
    ):
        r = client.get_exchange_rate(token)
        assert bool(r)

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
        "token, max_token",
        [
            (bat, 0.00001 * ONE_ETH),
            (dai, 0.00001 * ONE_ETH),
            pytest.param("btc", ONE_ETH, marks=pytest.mark.xfail),
        ],
    )
    def test_remove_liquidity(self, client: Uniswap, web3: Web3, token, max_token):
        r = client.remove_liquidity(token, max_token)
        tx = web3.eth.waitForTransactionReceipt(r)
        assert tx.status  # type: ignore

    # ------ Make Trade ----------------------------------------------------------------
    @pytest.mark.skip
    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient",
        [
            (eth, bat, 0.00001 * ONE_ETH, None),
            (bat, eth, 0.00001 * ONE_ETH, None),
            (dai, bat, 0.00001 * ONE_ETH, None),
            (eth, bat, 0.00001 * ONE_ETH, ZERO_ADDRESS),
            (bat, eth, 0.00001 * ONE_ETH, ZERO_ADDRESS),
            (dai, bat, 0.00001 * ONE_ETH, ZERO_ADDRESS),
            pytest.param(dai, "btc", ONE_ETH, None, marks=pytest.mark.xfail),
        ],
    )
    def test_make_trade(
        self, client: Uniswap, web3: Web3, input_token, output_token, qty, recipient
    ):
        r = client.make_trade(input_token, output_token, qty, recipient)
        tx = web3.eth.waitForTransactionReceipt(r)
        time.sleep(5)
        tx = web3.eth.getTransactionReceipt(r)
        assert tx.status  # type: ignore

    # @pytest.mark.skip
    # NOTE: This test requires ETH, BAT, and DAI in testnet wallet
    #       It can be obtained by running the main function in uniswap.py
    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient",
        [
            # ETH -> Token
            (eth, bat, 100 * ONE_WEI, None),
            # Token -> Token
            (bat, dai, 100 * ONE_WEI, None),
            # Token -> ETH
            (dai, eth, 100 * ONE_WEI, None),
            # (eth, bat, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # (bat, eth, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # (dai, bat, int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            pytest.param(dai, "btc", ONE_ETH, None, marks=pytest.mark.xfail),
        ],
    )
    def test_make_trade_output(
        self,
        client: Uniswap,
        web3: Web3,
        input_token,
        output_token,
        qty: Wei,
        recipient,
    ):
        r = client.make_trade_output(input_token, output_token, qty, recipient)
        tx = web3.eth.waitForTransactionReceipt(r, timeout=30)
        assert tx.status  # type: ignore
