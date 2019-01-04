import pytest
import time
import os

from web3 import Web3

from uniswap.uniswap import UniswapWrapper


@pytest.fixture(scope="module")
def client():
    address = os.environ["ETH_ADDRESS"]
    priv_key = os.environ["ETH_PRIV_KEY"]
    # For testing, use Rinkeby
    provider = os.environ["TESTNET_PROVIDER"]
    return UniswapWrapper(address, priv_key, provider)
    # return UniswapWrapper(address, priv_key)

@pytest.fixture(scope="module")
def web3_provider():
    provider = os.environ["TESTNET_PROVIDER"]
    w3 = Web3(Web3.HTTPProvider(provider, request_kwargs={"timeout": 60}))
    return w3


@pytest.mark.usefixtures("client", "web3_provider")
class TestUniswap(object):

    ONE_ETH = 1*10**18


    # ------ Exchange ------------------------------------------------------------------
    def test_get_fee_maker(self, client):
        r = client.get_fee_maker()
        assert r == 0

    def test_get_fee_taker(self, client):
        r = client.get_fee_taker()
        assert r == 0.003

    # ------ Market --------------------------------------------------------------------
    @pytest.mark.parametrize("token, qty", [
        ("bat", ONE_ETH),
        ("dai", ONE_ETH),
        ("bat", 2 * ONE_ETH),
        pytest.param("btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_eth_token_input_price(self, client, token, qty):
        r = client.get_eth_token_input_price(token, qty)
        assert bool(r)

    @pytest.mark.parametrize("token, qty", [
        ("bat", ONE_ETH),
        ("dai", ONE_ETH),
        ("bat", 2 * ONE_ETH),
        pytest.param("btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_token_eth_input_price(self, client, token, qty):
        r = client.get_token_eth_input_price(token, qty)
        assert bool(r)

    @pytest.mark.parametrize("token, qty", [
        ("bat", ONE_ETH),
        ("dai", ONE_ETH),
        ("bat", 2 * ONE_ETH),
        pytest.param("btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_eth_token_output_price(self, client, token, qty):
        r = client.get_eth_token_output_price(token, qty)
        assert bool(r)

    @pytest.mark.parametrize("token, qty", [
        ("bat", ONE_ETH),
        ("dai", ONE_ETH),
        ("bat", 2 * ONE_ETH),
        pytest.param("btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_token_eth_output_price(self, client, token, qty):
        r = client.get_token_eth_output_price(token, qty)
        assert bool(r)

    # ------ ERC20 Pool ----------------------------------------------------------------
    @pytest.mark.parametrize("token", [
        ("bat"),
        ("dai")
        ])
    def test_get_eth_balance(self, client, token,):
        r = client.get_eth_balance(token)
        assert bool(r)

    @pytest.mark.parametrize("token", [
        ("bat"),
        ("dai")
        ])
    def test_get_token_balance(self, client, token,):
        r = client.get_token_balance(token)
        assert bool(r)

    @pytest.mark.parametrize("token", [
        ("bat"),
        ("dai")
        ])
    def get_exchange_rate(self, client, token,):
        r = client.get_exchange_rate(token)
        assert bool(r)

    # ------ Liquidity -----------------------------------------------------------------
    @pytest.mark.skip
    @pytest.mark.parametrize("token, max_eth", [
        ("bat", 0.0005 * ONE_ETH),
        ("dai", 0.0005 * ONE_ETH),
        pytest.param("btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_add_liquidity(self, client, web3_provider, token, max_eth):
        r = client.add_liquidity(token, max_eth)
        tx = web3_provider.eth.waitForTransactionReceipt(r, timeout=6000)
        assert tx.status

    @pytest.mark.skip
    @pytest.mark.parametrize("token, max_token", [
        ("bat", 0.0005 * ONE_ETH),
        ("dai", 0.0005 * ONE_ETH),
        pytest.param("btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_remove_liquidity(self, client, web3_provider, token, max_token):
        r = client.remove_liquidity(token, max_token)
        tx = web3_provider.eth.waitForTransactionReceipt(r)
        assert tx.status

    # ------ Trading -------------------------------------------------------------------
    @pytest.mark.parametrize("input_token, output_token, qty", [
        ("eth", "bat", 0.00000005 * ONE_ETH),
        ("bat", "eth", 0.00000005 * ONE_ETH),
        ("dai", "bat", 0.00000001 * ONE_ETH),
        pytest.param("dai", "btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_make_trade(self, client, web3_provider, input_token, output_token, qty):
        r = client.make_trade(input_token, output_token, qty)
        tx = web3_provider.eth.waitForTransactionReceipt(r)
        assert tx.status

    @pytest.mark.parametrize("input_token, output_token, qty", [
        ("eth", "bat", 0.00000005 * ONE_ETH),
        ("bat", "eth", 0.00000005 * ONE_ETH),
        ("dai", "bat", 0.00000001 * ONE_ETH),
        pytest.param("dai", "btc", ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_make_trade_output(self, client, web3_provider, input_token, output_token, qty):
        r = client.make_trade_output(input_token, output_token, qty)
        tx = web3_provider.eth.waitForTransactionReceipt(r)
        assert tx.status