from typing import Dict

from web3 import Web3
from web3.types import ChecksumAddress


tokens: Dict[str, ChecksumAddress] = {
    k: Web3.toChecksumAddress(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "BAT": "0x0D8775F648430679A709E98d2b0Cb6250d2887EF",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    }.items()
}

tokens_rinkeby: Dict[str, ChecksumAddress] = {
    k: Web3.toChecksumAddress(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "DAI": "0x2448eE2641d78CC42D7AD76498917359D961A783",
        "BAT": "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B",
    }.items()
}
