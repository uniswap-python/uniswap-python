Command line interface
======================

uniswap-python provides a basic command line interface named ``unipy``, to let you easier query the chain for things like the current price and token metadata.

Example usage
-------------

**Note:** uniswap-python contains a small database of token contract addresses for convenience. You can always provide a contract address in place of a shorthand, and need to do so for all tokens not in the bundled database, or if you're not on mainnet.

.. code:: shell

    # Get price for 1 WETH quoted in DAI
    $ unipy price WETH DAI
    3350.883387688622

    # Get price for 1 WETH quoted in DAI, skip decimal normalization
    $ unipy price --raw WETH DAI
    3350883387688622003541

    # Get price for 1 WETH quoted in USDT
    $ unipy price WETH 0xdac17f958d2ee523a2206206994597c13d831ec7
    3348.128969

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
