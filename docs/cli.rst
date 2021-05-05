Command line interface
======================

uniswap-python provides a basic command line interface named ``unipy``, to let you easier query the chain for things like the current price and token metadata.

Examples
--------

.. code:: shell

    # Get price for 1 WETH quoted in DAI
    $ unipy price 0x6b175474e89094c44da98b954eedeac495271d0f 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    3350.883387688622

    # Get price for 1 WETH quoted in DAI, skip normalization
    $ unipy price --raw 0x6b175474e89094c44da98b954eedeac495271d0f 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    3350883387688622003541

    # Get token metadata from its ERC20 contract
    $ unipy token 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
    {'name': 'Wrapped Ether', 'symbol': 'WETH', 'decimals': 18}

    # List known/hardcoded tokens, with metadata
    $ unipy tokendb --metadata
    {'name': 'Wrapped Ether', 'symbol': 'WETH', 'decimals': 18}
    {'name': 'Dai Stablecoin', 'symbol': 'DAI', 'decimals': 18}
    {'name': 'Wrapped BTC', 'symbol': 'WBTC', 'decimals': 8}
    ...


Usage
-----

.. click:: uniswap.cli:main
   :prog: unipy
   :nested: full
