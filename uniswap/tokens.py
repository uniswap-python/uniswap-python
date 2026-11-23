from eth_typing.evm import ChecksumAddress
from web3 import Web3

tokens_mainnet: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "BAT": "0x0D8775F648430679A709E98d2b0Cb6250d2887EF",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    }.items()
}

tokens_rinkeby: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "DAI": "0x2448eE2641d78CC42D7AD76498917359D961A783",
        "BAT": "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B",
    }.items()
}

tokens_arbitrum: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "DAI": "0xda10009cbd5d07dd0cecc66161fc93d7c9000da1",
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "UNI": "0xfa7f8980b0f1e64a2062791cc3b0871572f1f7f0",
    }.items()
}

tokens_unichain: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x078D782b760474a361dDA0AF3839290b0EF57AD6",
        "USDT": "0x9151434b16b9763660705744891fA906F660EcC5",
    }.items()
}

tokens_optimism: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
    }.items()
}

tokens_base: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    }.items()
}

tokens_polygon: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    }.items()
}

tokens_ink: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x2D270e6886d130D724215A266106e6832161EAEd",
        "USDT": "0xAd09Cd20e513E4d8cB78036F77Ab9AfdE8555929",  # used kHYPE instead, no proper stables pool
    }.items()
}

tokens_soneium: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0xbA9986D2381edf1DA03B0B9c1f8b00dc4AacC369",
        "USDT": "0x3A337a6adA9d885b6Ad95ec48F9b75f197b5AE35",
    }.items()
}

tokens_avalanche: dict[str, ChecksumAddress] = {
    k: Web3.to_checksum_address(v)
    for k, v in {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
    }.items()
}

# tokens decimals
decimals_mainnet: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_arbitrum: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_unichain: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_optimism: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_base: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_polygon: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_ink: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 18,  # kHYPE decimals
    }.items()
}

decimals_soneium: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

decimals_avalanche: dict[str, int] = {
    k: v
    for k, v in {
        "ETH": 18,
        "WETH": 18,
        "USDC": 6,
        "USDT": 6,
    }.items()
}

# pools data
pool_data_mainnet: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (500, 10),
        "USDC_USDT": (10, 1),
    }.items()
}

pool_data_arbitrum: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (500, 10),
        "USDC_USDT": (8, 1),
    }.items()
}

pool_data_unichain: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (500, 10),
        "USDC_USDT": (100, 1),
    }.items()
}

pool_data_optimism: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (20000, 400),
        "USDC_USDT": (25, 1),
    }.items()
}

pool_data_base: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (3000, 60),
        "USDC_USDT": (7, 1),
    }.items()
}

pool_data_polygon: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (3000, 60),
        "USDC_USDT": (8, 1),
    }.items()
}

pool_data_ink: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (3000, 60),
        "USDC_USDT": (2500, 25),
    }.items()
}

pool_data_soneium: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (3000, 60),
        "USDC_USDT": (50, 1),
    }.items()
}

pool_data_avalanche: dict[str, tuple[int, int]] = {
    k: (v, z)
    for k, (v, z) in {
        "ETH_USDC": (500, 10),
        "USDC_USDT": (32, 1),
    }.items()
}


def get_tokens(netname: str) -> dict[str, ChecksumAddress]:
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
    elif netname == "unichain":
        return tokens_unichain
    elif netname == "optimism":
        return tokens_optimism
    elif netname == "base":
        return tokens_base
    elif netname == "polygon":
        return tokens_polygon
    elif netname == "ink":
        return tokens_ink
    elif netname == "soneium":
        return tokens_soneium
    elif netname == "avalanche":
        return tokens_avalanche
    else:
        raise ValueError(f"Unknown net '{netname}'")


def get_decimals(netname: str) -> dict[str, int]:
    """
    Returns a dict with decimals for tokens for the current net.
    Used in testing.
    """
    if netname == "mainnet":
        return decimals_mainnet
    elif netname == "arbitrum":
        return decimals_arbitrum
    elif netname == "unichain":
        return decimals_unichain
    elif netname == "optimism":
        return decimals_optimism
    elif netname == "base":
        return decimals_base
    elif netname == "polygon":
        return decimals_polygon
    elif netname == "ink":
        return decimals_ink
    elif netname == "soneium":
        return decimals_soneium
    elif netname == "avalanche":
        return decimals_avalanche
    else:
        raise ValueError(f"Unknown net '{netname}'")


def get_pool_data(netname: str) -> dict[str, tuple[int, int]]:
    """
    Returns a dict with pool data for tokens for the current net.
    Used in testing.
    """
    if netname == "mainnet":
        return pool_data_mainnet
    elif netname == "arbitrum":
        return pool_data_arbitrum
    elif netname == "unichain":
        return pool_data_unichain
    elif netname == "optimism":
        return pool_data_optimism
    elif netname == "base":
        return pool_data_base
    elif netname == "polygon":
        return pool_data_polygon
    elif netname == "ink":
        return pool_data_ink
    elif netname == "soneium":
        return pool_data_soneium
    elif netname == "avalanche":
        return pool_data_avalanche
    else:
        raise ValueError(f"Unknown net '{netname}'")
