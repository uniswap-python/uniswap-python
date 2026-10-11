"""
Runnable examples for Uniswap v4.

These tests serve as executable documentation: each test demonstrates one
common workflow against a live mainnet fork (Anvil). They run as part of the
``UNISWAP_VERSION=4`` CI matrix job, so every snippet is verified on every
commit.

Run locally:
    PROVIDER=<mainnet_rpc_url> UNISWAP_VERSION=4 pytest tests/test_v4_examples.py -v

See docs/v4.rst for the prose version of these examples.
"""

import os
import shutil
import subprocess
from collections.abc import Generator
from dataclasses import dataclass
from time import sleep

import pytest
from web3 import Web3

from uniswap import Uniswap4
from uniswap.constants import ETH_ADDRESS, ZERO_HOOK
from uniswap.types import PoolKey
from uniswap.util import V4pools

pytestmark = pytest.mark.skipif(
    os.getenv("UNISWAP_VERSION") != "4",
    reason="Run with UNISWAP_VERSION=4",
)

# ---------------------------------------------------------------------------
# Well-known mainnet addresses used in examples
# ---------------------------------------------------------------------------

USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

# Canonical fee tiers and tick spacings
ETH_USDC_FEE = 500
ETH_USDC_TICK_SPACING = 10
USDC_USDT_FEE = 100
USDC_USDT_TICK_SPACING = 1

ONE_ETH = 10**18
ONE_USDC = 10**6
ONE_USDT = 10**6

# PoolKey for ETH/USDC 0.05%
ETH_USDC_POOL = PoolKey(
    currency0=ETH_ADDRESS,
    currency1=USDC_ADDRESS,
    fee=ETH_USDC_FEE,
    tick_spacing=ETH_USDC_TICK_SPACING,
    hooks=ZERO_HOOK,
)

# PoolKey for USDC/USDT 0.01%
USDC_USDT_POOL = PoolKey(
    currency0=USDC_ADDRESS,
    currency1=USDT_ADDRESS,
    fee=USDC_USDT_FEE,
    tick_spacing=USDC_USDT_TICK_SPACING,
    hooks=ZERO_HOOK,
)


# ---------------------------------------------------------------------------
# Fixtures — same pattern as test_uniswap4.py
# ---------------------------------------------------------------------------


@dataclass
class AnvilInstance:
    provider: str
    eth_address: str
    eth_privkey: str


@pytest.fixture(scope="module")
def anvil() -> Generator[AnvilInstance, None, None]:
    """Start an Anvil instance forked from mainnet."""
    if not shutil.which("anvil"):
        raise ValueError("anvil was not found in PATH")
    if "PROVIDER" not in os.environ:
        raise ValueError(
            "PROVIDER must be set to a mainnet RPC URL so Anvil can fork mainnet."
        )

    port = 10997  # different from test_uniswap4.py (10998) to allow parallel runs
    p = subprocess.Popen(
        f"anvil --port {port} --chain-id 1 --fork-url {os.environ['PROVIDER']}",
        shell=True,
    )
    # Anvil test account #2 (1000 ETH pre-funded)
    eth_address = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
    eth_privkey = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"
    sleep(3)
    yield AnvilInstance(f"http://127.0.0.1:{port}", eth_address, eth_privkey)
    p.kill()
    p.wait()


@pytest.fixture(scope="module")
def web3(anvil: AnvilInstance) -> Web3:
    return Web3(Web3.HTTPProvider(anvil.provider, request_kwargs={"timeout": 30}))


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


# ---------------------------------------------------------------------------
# Example 1: Get the spot price
# ---------------------------------------------------------------------------


class TestExampleSpotPrice:
    """Example: reading the current pool price from the StateView contract."""

    def test_get_eth_usdc_spot_price(self, client: Uniswap4) -> None:
        """
        get_token_token_spot_price returns the spot price of token0 in units
        of token1. The result comes from the pool's sqrtPriceX96 slot without
        executing any swap.
        """
        price = client.get_token_token_spot_price(
            token0=ETH_ADDRESS,
            token1=USDC_ADDRESS,
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
        )
        # Sanity-check: ETH is worth more than $100 and less than $1M
        assert 100 < price < 1_000_000, f"Unexpected ETH/USDC price: {price}"

    def test_spot_price_is_reciprocal(self, client: Uniswap4) -> None:
        """The USDC/ETH price should be roughly 1/ETH_USDC price."""
        eth_usdc = client.get_token_token_spot_price(
            ETH_ADDRESS, USDC_ADDRESS, ETH_USDC_FEE, ETH_USDC_TICK_SPACING
        )
        usdc_eth = client.get_token_token_spot_price(
            USDC_ADDRESS, ETH_ADDRESS, ETH_USDC_FEE, ETH_USDC_TICK_SPACING
        )
        assert abs(usdc_eth - 1.0 / eth_usdc) / (1.0 / eth_usdc) < 0.001


# ---------------------------------------------------------------------------
# Example 2: Quote a trade before executing it
# ---------------------------------------------------------------------------


class TestExampleQuote:
    """Example: use the on-chain Quoter to get an accurate trade estimate."""

    def test_quote_exact_input_single_hop(self, client: Uniswap4) -> None:
        """
        get_price_input returns the USDC received for a fixed ETH input.
        Use this before a swap to set the slippage cap (qtycap).
        """
        usdc_out = client.get_price_input(
            token0=ETH_ADDRESS,
            token1=USDC_ADDRESS,
            qty=ONE_ETH,
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
        )
        # Quote should be a positive integer (USDC in smallest unit)
        assert usdc_out > 0
        usdc_human = usdc_out / ONE_USDC
        assert 100 < usdc_human < 1_000_000, f"Unexpected USDC quote: {usdc_human}"

    def test_quote_exact_output_single_hop(self, client: Uniswap4) -> None:
        """
        get_price_output returns the ETH required to buy an exact USDC amount.
        """
        eth_needed = client.get_price_output(
            token0=ETH_ADDRESS,
            token1=USDC_ADDRESS,
            qty=1000 * ONE_USDC,  # buy 1000 USDC
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
        )
        assert eth_needed > 0
        assert eth_needed < ONE_ETH, "1000 USDC should cost less than 1 ETH"

    def test_quote_exact_input_two_hop(self, client: Uniswap4) -> None:
        """
        Multi-hop quote: ETH → USDC → USDT via two pools.
        Pass a list of PoolKey objects as ``route``.
        """
        usdt_out = client.get_price_input(
            token0=ETH_ADDRESS,
            token1=USDT_ADDRESS,
            qty=ONE_ETH // 10,  # 0.1 ETH
            route=[ETH_USDC_POOL, USDC_USDT_POOL],
        )
        assert usdt_out > 0
        usdt_human = usdt_out / ONE_USDT
        assert 10 < usdt_human < 100_000, f"Unexpected USDT quote: {usdt_human}"


# ---------------------------------------------------------------------------
# Example 3: Estimate price impact before swapping
# ---------------------------------------------------------------------------


class TestExamplePriceImpact:
    """Example: check price impact to avoid trading into thin pools."""

    def test_small_trade_has_low_impact(self, client: Uniswap4) -> None:
        """
        A small ETH trade in a deep ETH/USDC pool should have near-zero impact.
        estimate_price_impact returns a float: 0.01 = 1%.
        """
        impact = client.estimate_price_impact(
            token0=ETH_ADDRESS,
            token1=USDC_ADDRESS,
            qty=ONE_ETH // 100,  # 0.01 ETH — tiny relative to pool depth
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
        )
        # Impact should be small (< 1%) for a tiny trade in a liquid pool
        assert impact < 0.01, f"Expected low impact, got {impact:.4%}"

    def test_large_trade_has_higher_impact(self, client: Uniswap4) -> None:
        """
        A larger trade should show measurably more price impact than a tiny one.
        """
        small_impact = client.estimate_price_impact(
            ETH_ADDRESS,
            USDC_ADDRESS,
            ONE_ETH // 100,
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
        )
        large_impact = client.estimate_price_impact(
            ETH_ADDRESS,
            USDC_ADDRESS,
            100 * ONE_ETH,
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
        )
        assert large_impact > small_impact


# ---------------------------------------------------------------------------
# Example 4: Read pool state via StateView
# ---------------------------------------------------------------------------


class TestExampleStateView:
    """Example: read on-chain pool state without making a swap."""

    def test_get_slot0(self, client: Uniswap4) -> None:
        """
        stateview_get_slot0 returns the current sqrtPriceX96 and tick for a pool.
        This is the cheapest way to read the current price.
        """
        slot0 = client.stateview_get_slot0(
            ETH_ADDRESS,
            USDC_ADDRESS,
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
            hooks=ZERO_HOOK,
        )
        assert slot0["sqrtPriceX96"] > 0
        # Tick is a signed integer; ETH/USDC tick should be negative
        # (ETH address < USDC address, so token0=ETH, current price ~3400 USDC
        # corresponds to a negative tick)
        assert isinstance(slot0["tick"], int)

    def test_get_pool_liquidity(self, client: Uniswap4) -> None:
        """
        stateview_get_liquidity returns total in-range liquidity for a pool.
        A popular pool like ETH/USDC 0.05% should always have positive liquidity.
        """
        liquidity = client.stateview_get_liquidity(
            ETH_ADDRESS,
            USDC_ADDRESS,
            fee=ETH_USDC_FEE,
            tick_spacing=ETH_USDC_TICK_SPACING,
            hooks=ZERO_HOOK,
        )
        assert liquidity > 0, "ETH/USDC 0.05% pool should have liquidity"


# ---------------------------------------------------------------------------
# Example 5: Discover pools for a token pair
# ---------------------------------------------------------------------------


class TestExamplePoolDiscovery:
    """Example: filter a saved v4 pool index by token pair using V4pools."""

    def test_find_eth_usdc_pools(self, pool_service: V4pools) -> None:
        """
        Load a checked-in pool index, then filter it by token pair.

        ``fetch_poolkey_data`` is documented in ``docs/v4.rst`` but is not
        suitable for the public CI RPC: scanning historical logs requires an
        archive endpoint. The fixture is generated by that method and keeps
        this example deterministic while exercising the filtering workflow.
        """
        pool_data = os.path.join(os.path.dirname(__file__), "pool_list.test")
        pool_service.load_poolkeys_list(pool_data)

        eth_usdc_pools = pool_service.get_poolkeys_sublist(ETH_ADDRESS, USDC_ADDRESS)
        # There should be at least one ETH/USDC pool (the 0.05% one)
        assert len(eth_usdc_pools) >= 1

        # All returned keys should reference the correct tokens
        for pk in eth_usdc_pools:
            currencies = {pk.currency0.lower(), pk.currency1.lower()}
            assert ETH_ADDRESS.lower() in currencies
            assert USDC_ADDRESS.lower() in currencies
