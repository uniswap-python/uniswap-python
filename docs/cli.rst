Command line interface
======================

uniswap-python provides a basic command line interface to let you easier query the chain for things like current price.

.. code:: shell

    # Get price for 1 WETH quoted in DAI
    $ unipy pricefeed 0x6b175474e89094c44da98b954eedeac495271d0f 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    3298.8656126202463

    # Get token metadata from its ERC20 contract
    $ unipy token 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    {'name': 'Wrapped Ether', 'symbol': 'WETH', 'decimals': 18}

