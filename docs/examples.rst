Examples
========

This page shows common usage patterns for Uniswap v2 and v3. For v4 examples,
see the dedicated :doc:`v4` guide.

The code snippets here mirror the `test suite
<https://github.com/uniswap-python/uniswap-python/tree/master/tests>`_, which
runs every example against a live mainnet fork using
`Anvil <https://book.getfoundry.sh/anvil/>`_.

.. contents:: Table of contents
    :local:
    :depth: 2

Uniswap v2
----------

Initialization
``````````````

.. code:: python

    from uniswap import Uniswap

    ETH = "0x0000000000000000000000000000000000000000"
    USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    DAI  = "0x6B175474E89094C44Da98b954EedeAC495271d0F"

    uni = Uniswap(
        address="0xYOUR_ADDRESS",
        private_key="0xYOUR_PRIVATE_KEY",  # or None for read-only
        version=2,
        provider="https://mainnet.infura.io/v3/YOUR_PROJECT_ID",
    )

Getting prices
``````````````

.. code:: python

    ONE_ETH = 10**18

    # How much USDC do I get for 1 ETH?
    usdc_out = uni.get_price_input(ETH, USDC, ONE_ETH)
    print(f"1 ETH → {usdc_out / 10**6:.2f} USDC")

    # How much ETH do I need to buy exactly 1000 USDC?
    eth_needed = uni.get_price_output(ETH, USDC, 1000 * 10**6)
    print(f"ETH needed for 1000 USDC: {eth_needed / ONE_ETH:.4f}")

Making swaps
````````````

.. code:: python

    # Sell 0.1 ETH, receive USDC (exact input)
    tx = uni.make_trade(ETH, USDC, ONE_ETH // 10)

    # Buy exactly 100 USDC, pay in ETH (exact output)
    tx = uni.make_trade_output(ETH, USDC, 100 * 10**6)

    # Sell ETH → DAI with a custom recipient
    tx = uni.make_trade(ETH, DAI, ONE_ETH // 10, recipient="0xSOME_OTHER_ADDRESS")

Multi-hop swaps
```````````````

For pairs without a direct v2 pool, route through an intermediate token:

.. code:: python

    WBTC = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"

    # ETH → WBTC (routed automatically through WETH by the v2 router)
    wbtc_out = uni.get_price_input(ETH, WBTC, ONE_ETH // 10)
    tx = uni.make_trade(ETH, WBTC, ONE_ETH // 10)

Uniswap v3
----------

v3 adds concentrated liquidity pools at multiple fee tiers. Always specify
``fee`` to select the pool — the right tier depends on the pair's volatility.

Initialization
``````````````

.. code:: python

    from uniswap import Uniswap

    ETH = "0x0000000000000000000000000000000000000000"
    USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    WBTC = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
    DAI  = "0x6B175474E89094C44Da98b954EedeAC495271d0F"

    uni = Uniswap(
        address="0xYOUR_ADDRESS",
        private_key="0xYOUR_PRIVATE_KEY",
        version=3,
        provider="https://mainnet.infura.io/v3/YOUR_PROJECT_ID",
    )

Fee tiers
`````````

Common v3 fee tiers:

- ``500`` — 0.05% (stablecoin pairs, e.g. USDC/USDT)
- ``3000`` — 0.30% (most pairs, e.g. ETH/USDC)
- ``10000`` — 1.00% (exotic/volatile pairs)

Getting prices
``````````````

.. code:: python

    ONE_ETH = 10**18

    # Quote using the 0.30% ETH/USDC pool
    usdc_out = uni.get_price_input(ETH, USDC, ONE_ETH, fee=3000)
    print(f"1 ETH → {usdc_out / 10**6:.2f} USDC (0.30% pool)")

    # Compare with the 0.05% pool (better rate for large trades)
    usdc_out_low = uni.get_price_input(ETH, USDC, ONE_ETH, fee=500)
    print(f"1 ETH → {usdc_out_low / 10**6:.2f} USDC (0.05% pool)")

    # Exact output quote
    eth_needed = uni.get_price_output(ETH, USDC, 1000 * 10**6, fee=500)

Making swaps
````````````

.. code:: python

    # Sell 0.1 ETH for USDC via the 0.05% pool
    tx = uni.make_trade(ETH, USDC, ONE_ETH // 10, fee=500)

    # Buy exactly 100 USDC, paying in ETH
    tx = uni.make_trade_output(ETH, USDC, 100 * 10**6, fee=500)

Multi-hop swaps
```````````````

The v3 client does not expose a multi-hop path parameter in ``make_trade``.
For pairs without a direct pool, execute two single-hop trades in sequence.
Wait for the first transaction and use the wallet's confirmed balance increase,
not its quote, as the second hop's input:

.. code:: python

    DAI = "0x6B175474E89094C44Da98b954EedeAC495271d0F"

    # ETH → USDC (first hop, 0.05% pool)
    usdc_before = uni.get_token_balance(USDC)
    tx1 = uni.make_trade(ETH, USDC, ONE_ETH // 10, fee=500)
    uni.w3.eth.wait_for_transaction_receipt(tx1)
    usdc_received = uni.get_token_balance(USDC) - usdc_before

    # USDC → DAI (second hop, 0.01% stable pool)
    tx2 = uni.make_trade(USDC, DAI, usdc_received, fee=100)

Liquidity management (v3)
`````````````````````````

.. code:: python

    from uniswap.util import default_tick_range

    ETH = "0x0000000000000000000000000000000000000000"
    USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    ONE_ETH = 10**18

    # Get the pool contract instance
    pool = uni.get_pool_instance(ETH, USDC, fee=500)

    # Sensible full-range tick bounds for this fee tier
    tick_lower, tick_upper = default_tick_range(fee=500)

    # Mint a liquidity position (returns TxReceipt)
    receipt = uni.mint_liquidity(
        pool,
        amount0=ONE_ETH // 10,
        amount1=340 * 10**6,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        deadline=2**64,
    )
    assert receipt["status"]

    # Get your token IDs (ERC-721 NFTs representing positions)
    positions = uni.get_liquidity_positions()
    token_id = positions[0]

    # Close the position (collects fees + withdraws liquidity in one call)
    receipt = uni.close_position(token_id, deadline=2**64)
