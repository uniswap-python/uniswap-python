# uniswap-python

[![Build Status](https://travis-ci.org/shanefontaine/uniswap-python.svg?branch=master)](https://travis-ci.org/shanefontaine/uniswap-python)
[![License](http://img.shields.io/badge/license-MIT-blue.svg)](https://raw.githubusercontent.com/shanefontaine/uniswap-python/master/LICENSE)

The unofficial Python client for the [Uniswap](https://uniswap.io/).

##### Provided under MIT License by Shane Fontaine.
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

_I am in no way affiliated with or funded by Uniswap, uniswap.io, or any subsidiaries or affiliates of any of the previously mentioned entities._

## Functionality
- A simple to use Python wrapper for both public and authenticated endpoints.
- Easy interaction with the Uniswap smart contracts
- Simple parsing of data returned from the Uniswap contract

## Under Development
- Better error handling
- Tests

## Getting Started
This README is documentation on the syntax of the python client presented in this repository. See function docstrings for full syntax details.
This API attempts to present a clean interface to Uniswap, but in order to use it to its full potential, you must familiarize yourself with the official Uniswap documentation.

- https://docs.uniswap.io/

You may manually install the project or use pip:

```python
pip install uniswap-python

# or

pip install git+git://github.com/shanefontaine/uniswap-python.git
```

### Public Client
Only some endpoints in the API are available to everyone. The public endpoints can be reached using PublicClient

```python
import uniswap
uniswap_wrapper = uniswap.UniswapWrapper()
```

### Market Methods
- get_fee_maker
```python
uniswap_wrapper.get_fee_maker()
```

- get_fee_taker
```python
uniswap_wrapper.get_fee_taker()
```

- [get_eth_token_input_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L416)
```python
# Get the public price for ETH to Token trades with an exact input.
uniswap_wrapper.get_eth_token_input_price('bat', 1*10**18)
uniswap_wrapper.get_eth_token_input_price('dai', 5*10**18)
```

- [get_token_eth_input_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L437)
```python
# Get the public price for token to ETH trades with an exact input.
uniswap_wrapper.get_token_eth_input_price('bat', 1*10**18)
uniswap_wrapper.get_token_eth_input_price('dai', 5*10**18)
```

- [get_eth_token_output_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L426)
```python
# Get the public price for ETH to Token trades with an exact output
uniswap_wrapper.get_eth_token_output_price('bat', 1*10**18)
uniswap_wrapper.get_eth_token_output_price('dai', 5*10**18)
```

- [get_token_eth_output_price](https://github.com/Uniswap/contracts-vyper/blob/master/contracts/uniswap_exchange.vy#L448)
```python
# Get the public price for token to ETH trades with an exact output.
uniswap_wrapper.get_token_eth_output_price('bat', 1*10**18)
uniswap_wrapper.get_token_eth_output_price('dai', 5*10**18)
```

## Testing
Unit tests are under development using the pytest framework. Contributions are welcome!

To run the full test suite and ignore warnings, in the project directory run:

```
python -m pytest -W ignore::DeprecationWarning
```

## Changelog
_0.1.1_
- Major README update

_0.1.0_
- Add market endpoints
- Add tests for market endpoints