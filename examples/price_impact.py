from typing import List

from web3 import Web3

from uniswap import Uniswap
from uniswap.types import AddressLike

eth = Web3.toChecksumAddress("0x0000000000000000000000000000000000000000")
weth = Web3.toChecksumAddress("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
usdt = Web3.toChecksumAddress("0xdac17f958d2ee523a2206206994597c13d831ec7")
vxv = Web3.toChecksumAddress("0x7d29a64504629172a429e64183d6673b9dacbfce")


def _perc(f: float) -> str:
    return f"{round(f * 100, 3)}%"


def usdt_to_vxv_v2():
    """
    Checks impact for a pool with very little liquidity.

    This particular route caused a $14k loss for one user: https://github.com/uniswap-python/uniswap-python/discussions/198
    """
    uniswap = Uniswap(address=None, private_key=None, version=2)

    route: List[AddressLike] = [usdt, weth, vxv]

    # Compare the results with the output of:
    # https://app.uniswap.org/#/swap?use=v2&inputCurrency=0xdac17f958d2ee523a2206206994597c13d831ec7&outputCurrency=0x7d29a64504629172a429e64183d6673b9dacbfce
    qty = 10 * 10**8

    # price = uniswap.get_price_input(usdt, vxv, qty, route=route) / 10 ** 18
    # print(price)

    impact = uniswap.estimate_price_impact(usdt, vxv, qty, route=route)
    # NOTE: Not sure why this differs from the quote in the UI?
    #       Getting -27% in the UI for 10 USDT, but this returns >95%
    #       The slippage for v3 (in example below) returns correct results.
    print(f"Impact for buying VXV on v2 with {qty / 10**8} USDT:  {_perc(impact)}")

    qty = 13900 * 10**8
    impact = uniswap.estimate_price_impact(usdt, vxv, qty, route=route)
    print(f"Impact for buying VXV on v2 with {qty / 10**8} USDT:  {_perc(impact)}")


def eth_to_vxv_v3():
    """Checks price impact for a pool with liquidity."""
    uniswap = Uniswap(address=None, private_key=None, version=3)

    # Compare the results with the output of:
    # https://app.uniswap.org/#/swap?use=v3&inputCurrency=ETH&outputCurrency=0x7d29a64504629172a429e64183d6673b9dacbfce
    qty = 1 * 10**18
    impact = uniswap.estimate_price_impact(eth, vxv, qty, fee=10000)
    print(f"Impact for buying VXV on v3 with {qty / 10**18} ETH:  {_perc(impact)}")

    qty = 100 * 10**18
    impact = uniswap.estimate_price_impact(eth, vxv, qty, fee=10000)
    print(f"Impact for buying VXV on v3 with {qty / 10**18} ETH:  {_perc(impact)}")


if __name__ == "__main__":
    usdt_to_vxv_v2()
    eth_to_vxv_v3()
