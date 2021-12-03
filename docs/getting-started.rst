Getting started
===============

This library attempts to present a clean interface to Uniswap, but in order to use it to its full potential, you must familiarize yourself with the official Uniswap documentation:

- V1: https://uniswap.org/docs/v1/
- V2: https://uniswap.org/docs/v2/
- V3: https://docs.uniswap.org/

.. contents:: Table of contents
    :local:
    :depth: 3

Installation
------------

You can install the latest release from PyPI, or install the latest commit directly from git:

.. code:: sh

    # Install the latest release from PyPI:

    pip install uniswap-python

    # or install from git:
    
    pip install git+git://github.com/uniswap-python/uniswap-python.git

    # or clone and install with poetry:

    git clone https://github.com/uniswap-python/uniswap-python.git
    cd uniswap-python
    poetry install


Initializing the Uniswap class
------------------------------

If you want to trade you need to provide your address and private key. If not, you can set them to ``None``.

In addition, the :class:`~uniswap.Uniswap` class takes several optional parameters, as documented in the `API Reference`.

.. code:: python

    from uniswap import Uniswap

    address = "YOUR ADDRESS"          # or None if you're not going to make transactions
    private_key = "YOUR PRIVATE KEY"  # or None if you're not going to make transactions
    version = 2                       # specify which version of Uniswap to use
    provider = "WEB3 PROVIDER URL"    # can also be set through the environment variable `PROVIDER`
    uniswap = Uniswap(address=address, private_key=private_key, version=version, provider=provider)

    # Some token addresses we'll be using later in this guide
    eth = "0x0000000000000000000000000000000000000000"
    bat = "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
    dai = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    

Environment Variables
`````````````````````

The program expects an environment variables to be set in order to run the program. You can use an Infura node, since the transactions are being signed locally and broadcast as a raw transaction. The environment variable is:

.. code:: sh

    PROVIDER  # HTTP Provider for web3

Gas pricing
```````````

To modify the gas pricing strategy you need to pass a custom `Web3` instance to the :class:`~uniswap.Uniswap` constructor. You can find details for how to configure Web3 gas strategies in their `documentation <https://web3py.readthedocs.io/en/stable/gas_price.html>`_.


Quoting prices
--------------

.. note::

    These methods assume a certain route for the swap to take, which may not be the optimal route. See :issue:`93` for details.

There are two functions to retrieve the price for a given pair, one for specifying how much you get given a certain amount of the input token, and another for specifying how much you need to pay to receive a certain amount of the output token.

:func:`~uniswap.Uniswap.get_price_input`
````````````````````````````````````````

Returns the amount of output tokens you get for a given amount of input tokens.

.. code:: python

    # Returns the amount of DAI you get for 1 ETH (10^18 wei)
    uniswap.get_price_input(eth, dai, 10**18)

:func:`~uniswap.Uniswap.get_price_output`
`````````````````````````````````````````

Returns the amount of input token you need for the given amount of output tokens.

.. code:: python

    # Returns the amount of ETH you need to pay (in wei) to get 1000 DAI
    uniswap.get_price_output(eth, dai, 1_000 * 10**18)


.. note:: 

    These methods return the price as an integer in the smallest unit of the token. You need to ensure that you know how many decimals the token you're trying to trade uses to get prices in the common decimal format. See :issue:`12` for details.

    Decimals for common tokens:

    - ETH, DAI, and BAT uses 18 decimals (as you can see in code below)
    - WBTC uses 8 decimals
    - USDC and USDT uses 6 decimals

    You can look up the number of decimals used by a particular token by looking up the contract on Etherscan.

Making trades
-------------

.. note::

    The same route assumptions and need for handling decimals apply here as those mentioned in the previous section.

.. warning::

    Always check the expected price before executing a trade. It's important that you're using a pool with adequate liquidity, or else you may suffer significant losses! (see :issue:`198` and :issue:`208`)

    Use the Uniswap version with the most liquidity for your route, and if using v3, make sure you set the ``fee`` parameter to use the best pool.

:func:`~uniswap.Uniswap.make_trade`
```````````````````````````````````

.. code:: python

    # Make a trade by specifying the quantity of the input token you wish to sell
    uniswap.make_trade(eth, bat, 1*10**18)  # sell 1 ETH for BAT
    uniswap.make_trade(bat, eth, 1*10**18)  # sell 1 BAT for ETH
    uniswap.make_trade(bat, dai, 1*10**18)  # sell 1 BAT for DAI
    uniswap.make_trade(eth, bat, 1*10**18, "0x123...")  # sell 1 ETH for BAT, and send the BAT to the provided address
    uniswap.make_trade(dai, usdc, 1*10**18, fee=500)    # sell 1 DAI for USDC using the 0.05% fee pool (v3 only)

:func:`~uniswap.Uniswap.make_trade_output`
``````````````````````````````````````````

.. code:: python

    # Make a trade by specifying the quantity of the output token you wish to buy
    uniswap.make_trade_output(eth, bat, 1*10**18)  # buy ETH for 1 BAT
    uniswap.make_trade_output(bat, eth, 1*10**18)  # buy BAT for 1 ETH
    uniswap.make_trade_output(bat, dai, 1*10**18, "0x123...")  # buy BAT for 1 DAI, and send the BAT to the provided address
    uniswap.make_trade_output(dai, usdc, 1*10**8, fee=500)     # buy USDC for 1 DAI using the 0.05% fee pool (v3 only)


Pool Methods (v1 only)
---------------------------

.. code:: python

    # Get the balance of ETH in an exchange contract.
    uniswap.get_ex_eth_balance(bat)

    # Get the balance of a token in an exchange contract.
    uniswap.get_ex_token_balance(bat)

    # Get the exchange rate of token/ETH
    uniswap.get_exchange_rate(bat)


Liquidity Methods (v1 only)
---------------------------

.. code:: python

    # Add liquidity to the pool.
    uniswap.add_liquidity(bat, 1*10**18)

    # Remove liquidity from the pool.
    uniswap.remove_liquidity(bat, 1*10**18)

