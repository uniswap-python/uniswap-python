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
from web3.types import Wei

from uniswap import Uniswap
from uniswap.constants import ETH_ADDRESS
from uniswap.fee import FeeTier
from uniswap.exceptions import InsufficientBalance, InvalidFeeTier
from uniswap.tokens import get_tokens
from uniswap.util import (
    _str_to_addr,
    default_tick_range,
    _addr_to_str,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENV_UNISWAP_VERSION = os.getenv("UNISWAP_VERSION", None)
if ENV_UNISWAP_VERSION:
    UNISWAP_VERSIONS = [int(ENV_UNISWAP_VERSION)]
else:
    UNISWAP_VERSIONS = [1, 2, 3]

RECEIPT_TIMEOUT = 5


ONE_ETH = 10**18
ONE_DAI = 10**18
ONE_USDC = 10**6

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


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


@pytest.fixture(scope="function")
def tokens(client: Uniswap):
    return get_tokens(client.netname)


@pytest.fixture(scope="module")
def test_assets(client: Uniswap):
    """
    Buy some DAI and USDC to test with.
    """
    tokens = get_tokens(client.netname)


    for token_name, amount in [
        ("DAI", 10_000 * ONE_DAI),
        ("USDC", 10_000 * ONE_USDC),
    ]:
        token_addr = tokens[token_name]
        price = client.get_price_output(_str_to_addr(ETH_ADDRESS), token_addr, amount, fee=FeeTier.TIER_3000)
        logger.info(f"Cost of {amount} {token_name}: {price}")
        logger.info("Buying...")

        txid = client.make_trade_output(tokens["ETH"], token_addr, amount, fee=FeeTier.TIER_3000)
        tx = client.w3.eth.wait_for_transaction_receipt(txid, timeout=RECEIPT_TIMEOUT)
        assert tx["status"] == 1, f"Transaction failed: {tx}"


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
    defaultGasPrice = 100_000_000_000  # 100 gwei
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



ONE_ETH = 10**18
ONE_USDC = 10**6

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
        "token0, token1, qty",
        [
            ("ETH", "UNI", ONE_ETH),
            ("UNI", "ETH", ONE_ETH),
            ("ETH", "DAI", ONE_ETH),
            ("DAI", "ETH", ONE_ETH),
            ("ETH", "UNI", 2 * ONE_ETH),
            ("UNI", "ETH", 2 * ONE_ETH),
            ("WETH", "DAI", ONE_ETH),
            ("DAI", "WETH", ONE_ETH),
            ("DAI", "USDC", ONE_ETH),
        ],
    )
    def test_get_price_input(self, client: Uniswap, tokens, token0, token1, qty):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version == 1 and ETH_ADDRESS not in [token0, token1]:
            pytest.skip("Not supported in this version of Uniswap")
        r = client.get_price_input(token0, token1, qty, fee=FeeTier.TIER_3000)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, qty",
        [
            ("ETH", "UNI", ONE_ETH),
            ("UNI", "ETH", ONE_ETH // 100),
            ("ETH", "DAI", ONE_ETH),
            ("DAI", "ETH", ONE_ETH),
            ("ETH", "UNI", 2 * ONE_ETH),
            ("WETH", "DAI", ONE_ETH),
            ("DAI", "WETH", ONE_ETH),
            ("DAI", "USDC", ONE_USDC),
        ],
    )
    def test_get_price_output(self, client: Uniswap, tokens, token0, token1, qty):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version == 1 and ETH_ADDRESS not in [token0, token1]:
            pytest.skip("Not supported in this version of Uniswap")
        r = client.get_price_output(token0, token1, qty, fee=FeeTier.TIER_3000)
        assert r

    @pytest.mark.parametrize("token0, token1, fee", [("DAI", "USDC", FeeTier.TIER_3000)])
    def test_get_raw_price(self, client: Uniswap, tokens, token0, token1, fee):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version == 1:
            pytest.skip("Only supported on Uniswap v2 and v3")
        r = client.get_raw_price(token0, token1, fee=fee)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, kwargs",
        [
            ("WETH", "DAI", {"fee": FeeTier.TIER_3000}),
        ],
    )
    def test_get_pool_instance(self, client, tokens, token0, token1, kwargs):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")
        r = client.get_pool_instance(token0, token1, **kwargs)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, kwargs",
        [
            ("WETH", "DAI", {"fee": FeeTier.TIER_3000}),
        ],
    )
    def test_get_pool_immutables(self, client, tokens, token0, token1, kwargs):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")
        pool = client.get_pool_instance(token0, token1, **kwargs)
        r = client.get_pool_immutables(pool)
        print(r)
        assert r

    @pytest.mark.parametrize(
        "token0, token1, kwargs",
        [
            ("WETH", "DAI", {"fee": FeeTier.TIER_3000}),
        ],
    )
    def test_get_pool_state(self, client, tokens, token0, token1, kwargs):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")
        pool = client.get_pool_instance(token0, token1, **kwargs)
        r = client.get_pool_state(pool)
        print(r)
        assert r

    @pytest.mark.parametrize(
        "amount0, amount1, token0, token1, kwargs",
        [
            (1, 10, "WETH", "DAI", {"fee": FeeTier.TIER_3000}),
        ],
    )
    def test_mint_position(
        self, client, tokens, amount0, amount1, token0, token1, kwargs
    ):
        token0, token1 = tokens[token0], tokens[token1]
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")
        pool = client.get_pool_instance(token0, token1, **kwargs)
        r = client.mint_position(pool, amount0, amount1)
        print(r)
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
    @pytest.mark.parametrize(
        "token0, token1, amount0, amount1, qty, fee",
        [
            ("DAI", "USDC", ONE_ETH, ONE_USDC, ONE_ETH, FeeTier.TIER_3000),
        ],
    )
    def test_v3_deploy_pool_with_liquidity(
        self, client: Uniswap, tokens, token0, token1, amount0, amount1, qty, fee
    ):
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")

        try:
            pool = client.create_pool_instance(tokens[token0], tokens[token1], fee)
        except Exception:
            pool = client.get_pool_instance(tokens[token0], tokens[token1], fee)

        print(pool.address)
        # Ensuring client has sufficient balance of both tokens
        eth_to_dai = client.make_trade(
            tokens["ETH"], tokens[token0], qty, client.address, fee=fee,
        )
        eth_to_dai_tx = client.w3.eth.wait_for_transaction_receipt(
            eth_to_dai, timeout=RECEIPT_TIMEOUT
        )
        assert eth_to_dai_tx["status"]
        dai_to_usdc = client.make_trade(
            tokens[token0], tokens[token1], qty * 10, client.address, fee=fee,
        )
        dai_to_usdc_tx = client.w3.eth.wait_for_transaction_receipt(
            dai_to_usdc, timeout=RECEIPT_TIMEOUT
        )
        assert dai_to_usdc_tx["status"]

        balance_0 = client.get_token_balance(tokens[token0])
        balance_1 = client.get_token_balance(tokens[token1])

        assert balance_0 > amount0, f"Have: {balance_0} need {amount0}"
        assert balance_1 > amount1, f"Have: {balance_1} need {amount1}"

        min_tick, max_tick = default_tick_range(fee)
        r = client.mint_liquidity(
            pool,
            amount0,
            amount1,
            tick_lower=min_tick,
            tick_upper=max_tick,
            deadline=2**64,
        )
        assert r["status"]

        position_balance = client.nonFungiblePositionManager.functions.balanceOf(
            _addr_to_str(client.address)
        ).call()
        assert position_balance > 0

        position_array = client.get_liquidity_positions()
        assert len(position_array) > 0

    @pytest.mark.parametrize(
        "deadline",
        [(2**64)],
    )
    def test_close_position(self, client: Uniswap, deadline):
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")
        position_array = client.get_liquidity_positions()
        tokenId = position_array[0]
        r = client.close_position(tokenId, deadline=deadline)
        assert r["status"]

    @pytest.mark.parametrize("token0, token1", [("DAI", "USDC")])
    def test_get_tvl_in_pool_on_chain(self, client: Uniswap, tokens, token0, token1):
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")

        pool = client.get_pool_instance(tokens[token0], tokens[token1], fee=FeeTier.TIER_3000)
        tvl_0, tvl_1 = client.get_tvl_in_pool(pool)
        assert tvl_0 > 0
        assert tvl_1 > 0

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
            ("USDC", "ETH", ONE_USDC, None, does_not_raise),
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

            txid = client.make_trade(input_token, output_token, qty, recipient, fee=FeeTier.TIER_3000)
            tx = web3.eth.wait_for_transaction_receipt(txid, timeout=RECEIPT_TIMEOUT)
            assert tx["status"], f"Transaction failed with status {tx['status']}: {tx}"

            # TODO: Checks for ETH, taking gas into account
            bal_in_after = client.get_token_balance(input_token)
            if input_token != tokens["ETH"]:
                assert bal_in_before - qty == bal_in_after

    @pytest.mark.parametrize(
        "input_token, output_token, qty, recipient, expectation",
        [
            # ETH -> Token
            ("ETH", "DAI", ONE_ETH, None, does_not_raise),
            # Token -> Token
            ("DAI", "USDC", ONE_USDC, None, does_not_raise),
            # Token -> ETH
            ("DAI", "ETH", ONE_ETH // 10, None, does_not_raise),
            # FIXME: These should probably be uncommented eventually
            # ("ETH", "UNI", int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # ("UNI", "ETH", int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            # ("DAI", "UNI", int(0.000001 * ONE_ETH), ZERO_ADDRESS),
            ("DAI", "DAI", ONE_USDC, None, lambda: pytest.raises(ValueError)),
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

            r = client.make_trade_output(input_token, output_token, qty, recipient, fee=FeeTier.TIER_3000)
            tx = web3.eth.wait_for_transaction_receipt(r, timeout=RECEIPT_TIMEOUT)
            assert tx["status"]

            # # TODO: Checks for ETH, taking gas into account
            balance_after = client.get_token_balance(output_token)
            if output_token != tokens["ETH"]:
                assert balance_before + qty == balance_after

    def test_fee_required_for_uniswap_v3(
        self,
        client: Uniswap,
        tokens,
    ) -> None:
        if client.version != 3:
            pytest.skip("Not supported in this version of Uniswap")
        with pytest.raises(InvalidFeeTier):
            client.get_price_input(tokens["ETH"], tokens["UNI"], ONE_ETH, fee=None)
        with pytest.raises(InvalidFeeTier):
            client.get_price_output(tokens["ETH"], tokens["UNI"], ONE_ETH, fee=None)
        with pytest.raises(InvalidFeeTier):
            client._get_eth_token_output_price(tokens["UNI"], ONE_ETH, fee=None)
        with pytest.raises(InvalidFeeTier):
            client._get_token_eth_output_price(tokens["UNI"], Wei(ONE_ETH), fee=None)
        with pytest.raises(InvalidFeeTier):
            client._get_token_token_output_price(
                tokens["UNI"], tokens["ETH"], ONE_ETH, fee=None
            )
        with pytest.raises(InvalidFeeTier):
            client.make_trade(tokens["ETH"], tokens["UNI"], ONE_ETH, fee=None)
        with pytest.raises(InvalidFeeTier):
            client.make_trade_output(tokens["ETH"], tokens["UNI"], ONE_ETH, fee=None)
        # NOTE: (rudiemeant@gmail.com): Since in 0.7.1 we're breaking the
        # backwards-compatibility with 0.7.0, we should check
        # that clients now get an error when trying to call methods
        # without explicitly specifying a fee tier.
        with pytest.raises(InvalidFeeTier):
            client.get_pool_instance(tokens["ETH"], tokens["UNI"], fee=None)  # type: ignore[arg-type]
        with pytest.raises(InvalidFeeTier):
            client.create_pool_instance(tokens["ETH"], tokens["UNI"], fee=None)  # type: ignore[arg-type]
        with pytest.raises(InvalidFeeTier):
            client.get_raw_price(tokens["ETH"], tokens["UNI"], fee=None)