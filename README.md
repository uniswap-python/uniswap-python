<p align="center">
  <img width="350" height="290" src="https://user-images.githubusercontent.com/9441295/107376524-d96b5880-6a9e-11eb-9eba-094c439cfb07.png">
</p>

# uniswap-python

[![GitHub Actions](https://github.com/shanefontaine/uniswap-python/workflows/test/badge.svg)](https://github.com/shanefontaine/uniswap-python/actions)
[![Downloads](https://pepy.tech/badge/uniswap-python)](https://pepy.tech/project/uniswap-python)
[![License](http://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/shanefontaine/uniswap-python/master/LICENSE)
[![Typechecking: Mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

The unofficial Python client for [Uniswap](https://uniswap.io/).

_The authors are in no way affiliated with or funded by Uniswap, uniswap.io, or any subsidiaries or affiliates of any of the previously mentioned entities._

### This package supports Uniswap V2 as of version 0.4.0.

## Functionality
*  A simple to use Python wrapper for all available contract functions and variables
*  Simple parsing of data returned from the Uniswap contract

## Under Development
*  Better error handling

## Getting Started
This README is documentation on the syntax of the python client presented in this repository. See function docstrings for full syntax details.
This API attempts to present a clean interface to Uniswap, but in order to use it to its full potential, you must familiarize yourself with the official Uniswap documentation.

*  https://docs.uniswap.io/

You may manually install the project or use pip:

```python
pip install uniswap-python

# or

pip install git+git://github.com/shanefontaine/uniswap-python.git
```

### Environment Variables
The program expects an environment variables to be set in order to run the program. You can use an Infura node, since the transactions are being signed locally and broadcast as a raw transaction. The environment variable is:

```
PROVIDER  # HTTP Provider for web3
```

### Gas pricing

To modify the gas pricing strategy you need to pass a custom `Web3` instance to the `Uniswap` constructor. You can find details for how to configure Web3 gas strategies in their [documentation](https://web3py.readthedocs.io/en/stable/gas_price.html).

### Examples and API

**Note:** These examples are in the process of being moved to the [docs](https://shanefontaine.github.io/uniswap-python/).

The `Uniswap` class takes several optional parameters, read the code to see which ones are available.

```python
from uniswap import Uniswap
address = "YOUR ADDRESS"          # or "0x0000000000000000000000000000000000000000", if you're not making transactions
private_key = "YOUR PRIVATE KEY"  # or None, if you're not going to make transactions
uniswap_wrapper = Uniswap(address, private_key, version=2)  # pass version=2 to use Uniswap v2
eth = "0x0000000000000000000000000000000000000000"
bat = "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
dai = "0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359"
```

#### Price Methods

> **Note:** These methods assume a certain route for the swap to take, which may not be the optimal route. See https://github.com/shanefontaine/uniswap-python/issues/69 for details.

These methods return the price as an integer in the smallest unit of the token. You need to ensure that you know how many decimals the token you're trying to trade uses to get prices in the common decimal format. See https://github.com/shanefontaine/uniswap-python/issues/12 for details.

Decimals for common tokens:

 - ETH, DAI, and BAT uses 18 decimals (as you can see in code below)
 - WBTC uses 8 decimals
 - USDC and USDT uses 6 decimals

You can look up the number of decimals used by a particular token by looking up the contract on Etherscan. As an example, here is the one for WBTC: https://etherscan.io/token/0x2260fac5e5542a773aa44fbcfedf7c193bc2c599

*  [get_eth_token_input_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L416)
```python
# Get the public price for ETH to Token trades with an exact input.
uniswap_wrapper.get_eth_token_input_price(bat, 1*10**18)
uniswap_wrapper.get_eth_token_input_price(dai, 5*10**18)
```

*  [get_token_eth_input_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L437)
```python
# Get the public price for token to ETH trades with an exact input.
uniswap_wrapper.get_token_eth_input_price(bat, 1*10**18)
uniswap_wrapper.get_token_eth_input_price(dai, 5*10**18)
```

*  [get_eth_token_output_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L426)
```python
# Get the public price for ETH to Token trades with an exact output
uniswap_wrapper.get_eth_token_output_price(bat, 1*10**18)
uniswap_wrapper.get_eth_token_output_price(dai, 5*10**18)
```

*  [get_token_eth_output_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L448)
```python
# Get the public price for token to ETH trades with an exact output.
uniswap_wrapper.get_token_eth_output_price(bat, 1*10**18)
uniswap_wrapper.get_token_eth_output_price(dai, 5*10**18)
```

#### Trading

> **Note:** The same route assumptions and need for handling decimals apply here as those mentioned in the previous section.

* make_trade
  * eth_to_token_input
    * [ethToTokenSwapInput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L127)
    * [ethToTokenTransferInput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L162)
  * token_to_eth_input
    * [tokenToEthSwapInput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L202)
    * [tokenToEthTransferInput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L232)
  * token_to_token_input
    * [tokenToTokenSwapInput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L271)
    * [tokenToTokenTransferInput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L307)

```python
# Make a trade based on the input parameters
uniswap_wrapper.make_trade(eth, bat, 1*10**18) # calls _eth_to_token_input
uniswap_wrapper.make_trade(bat, eth, 1*10**18) # calls _token_to_eth_input
uniswap_wrapper.make_trade(bat, dai, 1*10**18) # calls _token_to_token_input
uniswap_wrapper.make_trade(eth, bat, 1*10**18, "0x123...") # calls _eth_to_token_input
```

* make_trade_output
  * eth_to_token_swap_output
    * [ethToTokenSwapOutput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L167)
    * [ethToTokenTransferOutput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L197)
  * token_to_eth_swap_output
    * [tokenToEthSwapOutput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L237)
    * [tokenToEthTransferOutput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L266)
  * token_to_token_swap_output
    * [tokenToTokenSwapOutput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L312)
    * [tokenToTokenTransferOutput](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L349))

```python
# Make a trade where the output qty is known based on the input parameters
uniswap_wrapper.make_trade_output(eth, bat, 1*10**18) # calls _eth_to_token_swap_output
uniswap_wrapper.make_trade_output(bat, eth, 1*10**18) # calls _token_to_eth_swap_output
uniswap_wrapper.make_trade_output(bat, dai, 1*10**18, "0x123...") # calls _token_to_token_swap_output
```

#### Fee Methods
*  [get_fee_maker](https://docs.uniswap.io/)
```python
uniswap_wrapper.get_fee_maker()
```

*  [get_fee_taker](https://docs.uniswap.io/)
```python
uniswap_wrapper.get_fee_taker()
```


#### ERC20 Pool Methods (v1 only)
*  [get_ex_eth_balance](https://docs.uniswap.io/smart-contract-integration/vyper)
```python
# Get the balance of ETH in an exchange contract.
uniswap_wrapper.get_ex_eth_balance(bat)
```

*  [get_ex_token_balance](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L469)
```python
# Get the balance of a token in an exchange contract.
uniswap_wrapper.get_ex_token_balance(bat)
```

*  [get_exchange_rate](https://github.com/Uniswap/uniswap-frontend/blob/master/src/pages/Pool/AddLiquidity.js#L351)
```python
# Get the exchange rate of token/ETH
uniswap_wrapper.get_exchange_rate(bat)
```

#### Liquidity Methods (v1 only)

*  [add_liquidity](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L48)
```python
# Add liquidity to the pool.
uniswap_wrapper.add_liquidity(bat, 1*10**18)
```

*  [remove_liquidity](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L83)
```python
# Remove liquidity from the pool.
uniswap_wrapper.remove_liquidity(bat, 1*10**18)
```

## Testing
Unit tests are under development using the pytest framework. Contributions are welcome!

Test are run on a fork of the main net using ganache-cli. You need to install it with `npm install -g ganache-cli` before running tests.

To run the full test suite, in the project directory run:

```
make test
```

## Authors
* [Shane Fontaine](https://twitter.com/shanecoin)
* [Erik Bjäreholt](https://twitter.com/ErikBjare)

## Ownership Disclosure

*  I own some BAT and DAI tokens that are seen in the examples above. These tokens are used only for example purposes and are not meant to be an endorsement. I am not affiliated with BAT, Brave, Basic Attention Token, Brave Browser, DAI, Maker, MakerDAO, or any subsidiaries.

## Changelog

_0.4.6_
* Bug fix: Update bleach package from 3.1.4 to 3.3.0

_0.4.5_
* Bug fix: Use .eth instead of .ens

_0.4.4_

* General: Add new logo for Uniswap V2
* Bug fix: Invalid balance check (#25)
* Bug fix: Fixed error when passing WETH as token

_0.4.3_

* Allow kwargs in `approved` decorator.

_0.4.2_

* Add note about Uniswap V2 support

_0.4.1_

* Update changelog for PyPi and clean up

_0.4.0_

_A huge thank you [Erik Bjäreholt](https://github.com/ErikBjare) for adding Uniswap V2 support, as well as all changes in this version!_

* Added support for Uniswap v2
* Handle arbitrary tokens (by address) using the factory contract
* Switched from setup.py to pyproject.toml/poetry
* Switched from Travis to GitHub Actions
* For CI to work in your repo, you need to set the secret MAINNET_PROVIDER. I use Infura.
* Running tests on a local fork of mainnet using ganache-cli (started as a fixture)
* Fixed tests for make_trade and make_trade_output
* Added type annotations to the entire codebase and check them with mypy in CI
* Formatted entire codebase with black
* Moved stuff around such that the basic import becomes from uniswap import Uniswap (instead of from uniswap.uniswap import UniswapWrapper)
* Fixed misc bugs

_0.3.3_
*  Provide token inputs as addresses instead of names

_0.3.2_
*  Add ability to transfer tokens after a trade
*  Add tests for this new functionality

_0.3.1_
*  Add tests for all types of trades

_0.3.0_
*  Add ability to make all types of trades
*  Add example to README

_0.2.1_
*  Add liquidity tests

_0.2.0_
*  Add liquidity and ERC20 pool methods

_0.1.1_
*  Major README update

_0.1.0_
*  Add market endpoints
*  Add tests for market endpoints
