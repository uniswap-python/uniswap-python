Examples
========

This examples page is a work-in-progress. See the README for the old examples.

Initializing the Uniswap class
------------------------------

.. code:: python

    from uniswap import Uniswap
    address = "YOUR ADDRESS"          # or "0x0000000000000000000000000000000000000000", if you're not making transactions
    private_key = "YOUR PRIVATE KEY"  # or None, if you're not going to make transactions
    uniswap = Uniswap(address, private_key, version=2)  # pass version=2 to use Uniswap v2
    eth = "0x0000000000000000000000000000000000000000"
    bat = "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
    dai = "0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359"



Getting prices
--------------

TODO


Making trades
-------------

TODO
