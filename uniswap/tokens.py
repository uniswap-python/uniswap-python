from typing import Dict

from web3 import Web3
from eth_typing.evm import ChecksumAddress


tokens_mainnet: Dict[str, ChecksumAddress] = {
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

tokens_arbitrum: Dict[str, ChecksumAddress] = {
    k: Web3.toChecksumAddress(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
        "DAI": "0xda10009cbd5d07dd0cecc66161fc93d7c9000da1",
        "USDC": "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8",
        "UNI": "0xfa7f8980b0f1e64a2062791cc3b0871572f1f7f0",
    }.items()
}


def get_tokens(netname: str) -> Dict[str, ChecksumAddress]:
    """
    Returns a dict with addresses for tokens for the current net.
    Used in testing.
    """
    if netname == "mainnet":
        return tokens_mainnet
    elif netname == "rinkeby":
        return tokens_rinkeby
    elif netname == "arbitrum":
        return tokens_arbitrum
    else:
        raise Exception(f"Unknown net '{netname}'")
