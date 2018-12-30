import pytest
import time

from uniswap.uniswap import UniswapWrapper


@pytest.fixture(scope='module')
def client():
    return UniswapWrapper()


@pytest.mark.usefixtures('client')
class TestUniswap(object):

    ONE_ETH = 1*10**18

    def test_get_fee_maker(self, client):
        r = client.get_fee_maker()
        assert r == 0

    def test_get_fee_taker(self, client):
        r = client.get_fee_taker()
        assert r == 0.003

    @pytest.mark.parametrize('token, qty', [
        ('bat', ONE_ETH),
        ('dai', ONE_ETH),
        ('bat', 2 * ONE_ETH),
        pytest.param('btc', ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_eth_token_input_price(self, client, token, qty):
        r = client.get_eth_token_input_price(token, qty)
        assert bool(r)

    @pytest.mark.parametrize('token, qty', [
        ('bat', ONE_ETH),
        ('dai', ONE_ETH),
        ('bat', 2 * ONE_ETH),
        pytest.param('btc', ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_token_eth_input_price(self, client, token, qty):
        r = client.get_token_eth_input_price(token, qty)
        assert bool(r)

    @pytest.mark.parametrize('token, qty', [
        ('bat', ONE_ETH),
        ('dai', ONE_ETH),
        ('bat', 2 * ONE_ETH),
        pytest.param('btc', ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_eth_token_output_price(self, client, token, qty):
        r = client.get_eth_token_output_price(token, qty)
        assert bool(r)

    @pytest.mark.parametrize('token, qty', [
        ('bat', ONE_ETH),
        ('dai', ONE_ETH),
        ('bat', 2 * ONE_ETH),
        pytest.param('btc', ONE_ETH,
                     marks=pytest.mark.xfail)
        ])
    def test_get_token_eth_output_price(self, client, token, qty):
        r = client.get_token_eth_output_price(token, qty)
        assert bool(r)
        