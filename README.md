<p align="center">
  <img width="350" height="350" src="https://user-images.githubusercontent.com/9441295/107376524-d96b5880-6a9e-11eb-9eba-094c439cfb07.png">
</p>

# uniswap-python

[![GitHub Actions](https://github.com/shanefontaine/uniswap-python/workflows/Test/badge.svg)](https://github.com/shanefontaine/uniswap-python/actions)
[![codecov](https://codecov.io/gh/uniswap-python/uniswap-python/branch/master/graph/badge.svg?token=VHAZHHLFX8)](https://codecov.io/gh/uniswap-python/uniswap-python)
[![Downloads](https://pepy.tech/badge/uniswap-python)](https://pepy.tech/project/uniswap-python)
[![License](http://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/shanefontaine/uniswap-python/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/uniswap-python)](https://pypi.org/project/uniswap-python/)
[![Typechecking: Mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

[![GitHub Repo stars](https://img.shields.io/github/stars/uniswap-python/uniswap-python?style=social)](https://github.com/uniswap-python/uniswap-python/stargazers)
[![Twitter Follow](https://img.shields.io/twitter/follow/UniswapPython?label=Follow&style=social)](https://twitter.com/UniswapPython)

The unofficial Python client for [Uniswap](https://uniswap.io/).

Documentation is available at https://uniswap-python.com/

## Functionality

*  A simple to use Python wrapper for all available contract functions and variables
*  A basic CLI to get prices and token metadata
*  Simple parsing of data returned from the Uniswap contract

### Supports

 - Uniswap v3 (as of v0.5.0)
    - Including beta support for Arbitrum & Optimism deployments (as of v0.5.4)
 - Uniswap v2 (as of v0.4.0)
 - Uniswap v1 (deprecated)
 - Various forks (untested, but should work)
   - Honeyswap (xDai)
   - Pancakeswap (BSC)
   - Sushiswap (mainnet)

## Getting Started

See our [Getting started guide](https://uniswap-python.com/getting-started.html) in the documentation.

## Testing

Unit tests are under development using the pytest framework. Contributions are welcome!

Test are run on a fork of the main net using ganache-cli. You need to install it with `npm install -g ganache-cli` before running tests.

To run the full test suite, in the project directory set the `PROVIDER` env variable to a mainnet provider, and run:

```sh
poetry install
export PROVIDER= # URL of provider, e.g. https://mainnet.infura.io/v3/...
make test
# or...
poetry run pytest --capture=no  # doesn't capture output (verbose)
```

## Support our continued work!

You can support us on [Gitcoin Grants](https://gitcoin.co/grants/2631/uniswap-python).

## Authors

* [Shane Fontaine](https://twitter.com/shanecoin)
* [Erik Bjäreholt](https://twitter.com/ErikBjare)
* [@liquid-8](https://github.com/liquid-8)
* ...and [others](https://github.com/uniswap-python/uniswap-python/graphs/contributors)

*Want to help out with development? We have funding to those that do! See [#181](https://github.com/uniswap-python/uniswap-python/discussions/181)*

## Changelog

_0.5.1_

* Updated dependencies
* Fixed minor typing issues

_0.5.0_

* Basic support for Uniswap V3
* Added new methods `get_price_input` and `get_price_output`
* Made a lot of previously public methods private
* Added documentation site
* Removed ENS support (which was probably broken to begin with)

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
