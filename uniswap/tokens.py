from typing import Dict

from eth_typing.evm import ChecksumAddress
from web3 import Web3

tokens_mainnet: Dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
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
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "DAI": "0x2448eE2641d78CC42D7AD76498917359D961A783",
        "BAT": "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B",
    }.items()
}

tokens_arbitrum: Dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
        "DAI": "0xda10009cbd5d07dd0cecc66161fc93d7c9000da1",
        "USDC": "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8",
        "UNI": "0xfa7f8980b0f1e64a2062791cc3b0871572f1f7f0",
    }.items()
}

tokens_zksync: Dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ZK" :"0x5A7d6b2F92C77FAD6CCaBd7EE0624E64907Eaf3E",
        "USDC":"0x3355df6d4c9c3035724fd0e3914de96a5a83aaf4",
        "ETH":"0x0000000000000000000000000000000000000000",
        "WETH":"0x5aea5775959fbc2557cc8789bc1bf90a239d9a91",
    }.items()
}

tokens_worldchain: Dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "WLD":"0x2cFc85d8E48F8EAB294be644d9E25C3030863003",
        "USDC":"0x79A02482A880bCE3F13e09Da970dC34db4CD24d1",
        "ETH":"0x0000000000000000000000000000000000000000",
        "WETH":"0x4200000000000000000000000000000000000006",
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
    elif netname == "zksync":
        return tokens_zksync
    elif netname == "worldchain":
        return tokens_worldchain
    else:
        raise Exception(f"Unknown net '{netname}'")
