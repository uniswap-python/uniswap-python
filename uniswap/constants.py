from typing import cast

from web3.types import RPCEndpoint

# look at web3/middleware/cache.py for reference
# RPC methods that will be cached inside _get_eth_simple_cache_middleware
SIMPLE_CACHE_RPC_WHITELIST = cast(
    set[RPCEndpoint],
    {
        "eth_chainId",
    },
)

ETH_ADDRESS = "0x0000000000000000000000000000000000000000"
WETH9_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
ZERO_HOOK = "0x0000000000000000000000000000000000000000"

Q96 = 2**96


# see: https://chainid.network/chains/
_netid_to_name = {
    1: "mainnet",
    3: "ropsten",
    4: "rinkeby",
    5: "görli",
    10: "optimism",
    42: "kovan",
    56: "bnb",
    97: "bnb_testnet",
    100: "xdai",
    130: "unichain",
    137: "polygon",
    143: "monad",
    196: "xlayer",
    250: "fantom",
    480: "worldchain",
    999: "hyperevm",
    1868: "soneium",
    4217: "tempo",
    4326: "megaeth",
    4663: "robinhood",
    5042: "arc",
    8453: "base",
    42161: "arbitrum",
    42220: "celo",
    43114: "avalanche",
    57073: "ink",
    99901: "elysium",
    421611: "arbitrum_testnet",
    7777777: "zora",
    1666600000: "harmony_mainnet",
    1666700000: "harmony_testnet",
    11155111: "sepolia",
}

_factory_contract_addresses_v1 = {
    "mainnet": "0xc0a47dFe034B400B47bDaD5FecDa2621de6c4d95",
    "ropsten": "0x9c83dCE8CA20E9aAF9D3efc003b2ea62aBC08351",
    "rinkeby": "0xf5D915570BC477f9B8D6C0E980aA81757A3AaC36",
    "kovan": "0xD3E51Ef092B2845f10401a0159B2B96e8B6c3D30",
    "görli": "0x6Ce570d02D73d4c384b46135E87f8C592A8c86dA",
}


# For v2 the address is the same on mainnet, Ropsten, Rinkeby, Görli, and Kovan
# https://uniswap.org/docs/v2/smart-contracts/factory
_factory_contract_addresses_v2 = {
    "mainnet": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "ropsten": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "rinkeby": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "görli": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    "xdai": "0xA818b4F111Ccac7AA31D0BCc0806d64F2E0737D7",
    "bnb": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
    "bnb_testnet": "0x6725F303b657a9451d8BA641348b6761A6CC7a17",
    # SushiSwap on Harmony
    "harmony_mainnet": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
    "harmony_testnet": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",
    "sepolia": "0x7E0987E5b3a30e3f2828572Bb659A548460a3003",
}

_router_contract_addresses_v2 = {
    "mainnet": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "ropsten": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "rinkeby": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "görli": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    "sepolia": "0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008",
    "xdai": "0x1C232F01118CB8B424793ae03F870aa7D0ac7f77",
    "bnb": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
    "bnb_testnet": "0xD99D1c33F9fC3444f8101754aBC46c52416550D1",
    # SushiSwap on Harmony
    "harmony_mainnet": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
    "harmony_testnet": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
}

MAX_UINT_128 = (2**128) - 1

# Source: https://github.com/Uniswap/v3-core/blob/v1.0.0/contracts/libraries/TickMath.sol#L8-L11
MIN_TICK = -887272
MAX_TICK = -MIN_TICK

# Source: https://github.com/Uniswap/v3-core/blob/v1.0.0/contracts/UniswapV3Factory.sol#L26-L31
_tick_spacing = {100: 1, 500: 10, 3_000: 60, 10_000: 200}

# Derived from (MIN_TICK//tick_spacing) >> 8 and (MAX_TICK//tick_spacing) >> 8
_tick_bitmap_range = {
    100: (-3466, 3465),
    500: (-347, 346),
    3_000: (-58, 57),
    10_000: (-18, 17),
}
# Source:
# https://developers.uniswap.org/docs/protocols/v4/deployments
_router_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0x23617e59A5925b2A4Bf75d73ff6711cD0b29De85",
    "unichain": "0xD1b797D92d87B688193A2B976eFc8D577D204343",
    "optimism": "0xC09255D86DB563cBc11C2fCf4a0C512e160111B4",
    "base": "0xd6145b2D3F379919E8CdEda7B97e37c4b2Ca9c40",
    "arbitrum": "0x2d01411773c8C24805306E89A41F7855C3c4Fe65",
    "polygon": "xDc264714F68d84CF29BC605589405E78bDBE7C9f",
    "zora": "0xF025e0Fe9E331A0eF05c2ad3C4E9C64b625cda6f",
    "worldchain": "0xF025e0Fe9E331A0eF05c2ad3C4E9C64b625cda6f",
    "ink": "0x661E93cca42AfacB172121EF892830cA3b70F08d",
    "soneium": "0x661E93cca42AfacB172121EF892830cA3b70F08d",
    "avalanche": "0x661E93cca42AfacB172121EF892830cA3b70F08d",
    "bnb": "0xDc264714F68d84CF29BC605589405E78bDBE7C9f",
    "celo": "0xe2023F3FA515cF070e07fD9d51c1d236e07843f4",
    "monad": "0xa6CE4F10d83dBdDAc17E68e1837ca9cE6a1b596e",
    "megaeth": "0xAedd1CF4C14e833140A61E9C0d2b73a64795c823",
    "xlayer": "0x1cd182C94fcF42277B80DBB9060F88024809E61E",
    "tempo": "0x182a927119D56008d921126764bF884221b10f59",
    "robinhood": "0x204FAca1764B154221e35c0d20aBb3c525710498",
    "arc": "0x8702463e73f74d0b6765aBceb314Ef07aCb92650",
    "hyperevm": "0xeD270A1Bcdc63cf1356D695e7f40961d4819d6bF",
    "elysium": "0xA13f7611115752DEB2B13813BDDE16A5073e4b45",
}

_quoter_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0x99bd42B2B22e531f283b7F8a86dFf631EB16A9D1",
    "unichain": "0xF885781cB68A0BE66AA2AC7eDa5Fe72Bde7dA907",
    "optimism": "0xd673F731EDFe5AaF1bDa7FD43D13Bbb5150B87Ca",
    "base": "0xE1A6C5803e3c44368b171BD680c7D32dfc92CA47",
    "arbitrum": "0x8928074CA1b241D8Ec02815881c1Af11E8bC5219",
    "polygon": "0x31AB0Dea31FC0ad5A54F03cD59C896eCD067447B",
    "zora": "0x2a7AaD35a2EbD95c1dC5AE323E866a737Bf79523",
    "worldchain": "0xAD02601f1bE313C952AD198c0Cbc3F87f9eE8E63",
    "ink": "0x8928074CA1b241D8Ec02815881c1Af11E8bC5219",
    "soneium": "0x8928074CA1b241D8Ec02815881c1Af11E8bC5219",
    "avalanche": "0xf27e532878B622d6b916F524E8711880107D4eF0",
    "bnb": "0x95C086d7fE28AdD842ee220fef225a777474d781",
    "celo": "0x28566da1093609182dff2cb2a91cfd72e61d66cd",
    "monad": "0xa222dd357a9076d1091ed6aa2e16c9742dd26891",
    "megaeth": "0x94bdc671f0c35f44a1daa53143fd1f868d1623b9",
    "xlayer": "0x8928074ca1b241d8ec02815881c1af11e8bc5219",
    "tempo": "0x20e6487c371a2086f841ef453f85378223df4f4e",
    "robinhood": "0x8dc178efb8111bb0973dd9d722ebeff267c98f94",
    "arc": "0x8Dc178eFB8111BB0973Dd9d722ebeFF267c98F94",
    "hyperevm": "0x108Bfe38532C98f8Cd8D7Ab49c9dDAa3675a1c5e",
    "elysium": "0x379F556c5a748BD7Cc9baF0F7A344094Ac1814f5",
}

_stateview_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0x7ffe42c4a5deea5b0fec41c94c136cf115597227",
    "unichain": "0x86e8631a016f9068c3f085faf484ee3f5fdee8f2",
    "optimism": "0xc18a3169788f4f75a170290584eca6395c75ecdb",
    "base": "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71",
    "arbitrum": "0x76fd297e2d437cd7f76d50f01afe6160f86e9990",
    "polygon": "0x5ea1bd7974c8a611cbab0bdcafcb1d9cc9b3ba5a",
    "zora": "0x385785af07d63b50d0a0ea57c4ff89d06adf7328",
    "worldchain": "0x51d394718bc09297262e368c1a481217fdeb71eb",
    "ink": "0x76fd297e2d437cd7f76d50f01afe6160f86e9990",
    "soneium": "0x76fd297e2d437cd7f76d50f01afe6160f86e9990",
    "avalanche": "0xc3c9e198c735a4b97e3e683f391ccbdd60b69286",
    "bnb": "0xd13dd3d6e93f276fafc9db9e6bb47c1180aee0c4",
    "celo": "0xbc21f8720babf4b20d195ee5c6e99c52b76f2bfb",
    "monad": "0x77395f3b2e73ae90843717371294fa97cc419d64",
    "megaeth": "0x726f84e1dfb8d375a365e0808282f40d52d3e4e8",
    "xlayer": "0x76fd297e2d437cd7f76d50f01afe6160f86e9990",
    "tempo": "0x21b954fba3f5ddebe77ef2d47a3100c066908b2a",
    "robinhood": "0xf3334192d15450cdd385c8b70e03f9a6bd9e673b",
    "arc": "0xF3334192D15450CdD385c8B70e03f9A6bD9E673b",
    "hyperevm": "0x1656326235cb9E34Cb58CaDe53AE30789AB32A1A",
    "elysium": "0x27eD73aE0652fdCf71d6793412A7525f32bE9dfE",
}

_permit2_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "unichain": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "optimism": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "base": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "arbitrum": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "polygon": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "zora": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "worldchain": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "ink": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "soneium": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "avalanche": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "bnb": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "celo": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "monad": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "megaeth": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "xlayer": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "tempo": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "robinhood": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "arc": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "hyperevm": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
    "elysium": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
}

_poolmanager_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0x000000000004444c5dc75cB358380D2e3dE08A90",
    "unichain": "0x1f98400000000000000000000000000000000004",
    "optimism": "0x9a13f98cb987694c9f086b1f5eb990eea8264ec3",
    "base": "0x498581ff718922c3f8e6a244956af099b2652b2b",
    "arbitrum": "0x360e68faccca8ca495c1b759fd9eee466db9fb32",
    "polygon": "0x67366782805870060151383f4bbff9dab53e5cd6",
    "zora": "0x0575338e4c17006ae181b47900a84404247ca30f",
    "worldchain": "0xb1860d529182ac3bc1f51fa2abd56662b7d13f33",
    "ink": "0x360e68faccca8ca495c1b759fd9eee466db9fb32",
    "soneium": "0x360e68faccca8ca495c1b759fd9eee466db9fb32",
    "avalanche": "0x06380c0e0912312b5150364b9dc4542ba0dbbc85",
    "bnb": "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df",
    "celo": "0x288dc841A52FCA2707c6947B3A777c5E56cd87BC",
    "monad": "0x188d586ddcf52439676ca21a244753fa19f9ea8e",
    "megaeth": "0xacb7e78fa05d562e0a5d3089ec896d57d057d38e",
    "xlayer": "0x360e68faccca8ca495c1b759fd9eee466db9fb32",
    "tempo": "0x33620f62c5b9b2086dd6b62f4a297a9f30347029",
    "robinhood": "0x8366a39cc670b4001a1121b8f6a443a643e40951",
    "arc": "0x8366a39CC670B4001A1121B8F6A443A643e40951",
    "hyperevm": "0x12D4Fd9C5DeDd00ab8a0bCe2CF0167bbf94b6B1F",
    "elysium": "0xE2e105d3F7209A9DA11f83cCf3E7398a753823F1",
}

_position_descriptor_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0xd1428ba554f4c8450b763a0b2040a4935c63f06c",
    "unichain": "0x9fb28449a191cd8c03a1b7abfb0f5996ecf7f722",
    "optimism": "0xedd81496169c46df161b8513a52ffecaaaa66743",
    "base": "0x25d093633990dc94bedeed76c8f3cdaa75f3e7d5",
    "arbitrum": "0xe2023f3fa515cf070e07fd9d51c1d236e07843f4",
    "polygon": "0x0892771f0c1b78ad6013d6e5536007e1c16e6794",
    "zora": "0x7d64630bbb4993b5578dbd65e400961c9e68d55a",
    "worldchain": "0x7da419153bd420b689f312363756d76836aeace4",
    "ink": "0x42e3ccd9b7f67b5b2ee0c12074b84ccf2a8e7f36",
    "soneium": "0x42e3ccd9b7f67b5b2ee0c12074b84ccf2a8e7f36",
    "avalanche": "0x2b1aed9445b05ac1a3b203eccc1e25dd9351f0a9",
    "bnb": "0xf0432f360703ec3d33931a8356a75a77d8d380e1",
    "celo": "0x5727E22b25fEEe05E8dFa83C752B86F19D102D8A",
    "monad": "0x5770d2914355a6d0a39a70aeea9bcce55df4201b",
    "megaeth": "0xa9fdbb9d3dce2e1cfb91c4af1b8cf4ed62c0041a",
    "xlayer": "0x9e9fbbef0e1bd752e83de5acff3d0c936a9e5a4b",
    "tempo": "0xc73ed2cba8c347593d1d9120aa0be8ff88c6ff77",
    "robinhood": "0x9639443158e8c5efa35bd45287bf2effd3d8dc06",
    "arc": "0x516b8a945700D6bBfDeDaa6dcFc4586bA60B8707",
    "hyperevm": "0xfF0b85caDaC458D5aAcc22755e5107bfE31ED402",
    "elysium": "0x9f92C5297EB3b39E6804b5e03899bC66B6b77348",
}

_position_manager_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e",
    "unichain": "0x4529a01c7a0410167c5740c487a8de60232617bf",
    "optimism": "0x3c3ea4b57a46241e54610e5f022e5c45859a1017",
    "base": "0x7c5f5a4bbd8fd63184577525326123b519429bdc",
    "arbitrum": "0xd88f38f930b7952f2db2432cb002e7abbf3dd869",
    "polygon": "0x1ec2ebf4f37e7363fdfe3551602425af0b3ceef9",
    "zora": "0xf66c7b99e2040f0d9b326b3b7c152e9663543d63",
    "worldchain": "0xc585e0f504613b5fbf874f21af14c65260fb41fa",
    "ink": "0x1b35d13a2e2528f192637f14b05f0dc0e7deb566",
    "soneium": "0x1b35d13a2e2528f192637f14b05f0dc0e7deb566",
    "avalanche": "0xb74b1f14d2754acfcbbe1a221023a5cf50ab8acd",
    "bnb": "0x7a4a5c919ae2541aed11041a1aeee68f1287f95b",
    "celo": "0xf7965f3981e4d5bc383bfbcb61501763e9068ca9",
    "monad": "0x5b7ec4a94ff9bedb700fb82ab09d5846972f4016",
    "megaeth": "0x9ae0921e981aaa7308f176f8d4f9129b9247c89d",
    "xlayer": "0xcf1eafc6928dc385a342e7c6491d371d2871458b",
    "tempo": "0x3fc79444f8eacc1894775493ff3fa41f1e35ce11",
    "robinhood": "0x58daec3116aae6d93017baaea7749052e8a04fa7",
    "arc": "0x6049c9a0e26405C0985f9E3685C87d0aE917f82B",
    "hyperevm": "0x0d7Ab5B3db668128Aff6F70C4eBC71D7d4DA9bf9",
    "elysium": "0x1d1C51b9d07fD27d36412A2b66CC23D19Eb3E518",
}

_reserves_lens_contract_addresses_v4 = {
    # Production addresses
    "mainnet": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "unichain": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "optimism": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "base": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "arbitrum": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "polygon": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "zora": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "worldchain": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "ink": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "soneium": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "avalanche": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "bnb": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "celo": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "monad": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "megaeth": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "xlayer": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "tempo": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "robinhood": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "arc": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "hyperevm": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
    "elysium": "0x0000001b173C3bbF3984D417d8614E3eed34865B",
}


# Source: https://github.com/Uniswap/universal-router/blob/main/contracts/libraries/Commands.sol
universal_router_commands = {
    "V3_SWAP_EXACT_IN": 0x00,
    "V3_SWAP_EXACT_OUT": 0x01,
    "PERMIT2_TRANSFER_FROM": 0x02,
    "PERMIT2_PERMIT_BATCH": 0x03,
    "SWEEP": 0x04,
    "TRANSFER": 0x05,
    "PAY_PORTION": 0x06,
    "PAY_PORTION_FULL_PRECISION": 0x07,  # Deprecated
    "V2_SWAP_EXACT_IN": 0x08,
    "V2_SWAP_EXACT_OUT": 0x09,
    "PERMIT2_PERMIT": 0x0A,
    "WRAP_ETH": 0x0B,
    "UNWRAP_WETH": 0x0C,
    "PERMIT2_TRANSFER_FROM_BATCH": 0x0D,
    "BALANCE_CHECK_ERC20": 0x0E,
    "V4_SWAP": 0x10,
    "V3_POSITION_MANAGER_PERMIT": 0x11,
    "V3_POSITION_MANAGER_CALL": 0x12,
    "V4_INITIALIZE_POOL": 0x13,
    "V4_POSITION_MANAGER_CALL": 0x14,
    "EXECUTE_SUB_PLAN": 0x21,
}
# Source: https://github.com/Uniswap/universal-router/blob/d3123d99493aa6524bc5de44423c3961177758cb/test/integration-tests/shared/planner.ts
universal_router_commands_abis = {
    "V3_SWAP_EXACT_IN": [
        "address",
        "uint256",
        "uint256",
        "bytes",
        "bool",
        "uint256[]",
    ],
    "V3_SWAP_EXACT_OUT": [
        "address",
        "uint256",
        "uint256",
        "bytes",
        "bool",
        "uint256[]",
    ],
    "PERMIT2_TRANSFER_FROM": [
        "address",
        "address",
        "uint160",
    ],
    "PERMIT2_PERMIT_BATCH": [
        "((address,uint160,uint48,uint48)[],address,uint256)[]",
        "bytes",
    ],
    "SWEEP": [
        "address",
        "address",
        "uint256",
    ],
    "TRANSFER": [
        "address",
        "address",
        "uint256",
    ],
    "PAY_PORTION": [
        "address",
        "address",
        "uint256",
    ],
    "PAY_PORTION_FULL_PRECISION": [
        "address",
        "address",
        "uint256",
    ],
    "V2_SWAP_EXACT_IN": [
        "address",
        "uint256",
        "uint256",
        "address[]",
        "bool",
        "uint256[]",
    ],
    "V2_SWAP_EXACT_OUT": [
        "address",
        "uint256",
        "uint256",
        "address[]",
        "bool",
        "uint256[]",
    ],
    "PERMIT2_PERMIT": [
        "((address,uint160,uint48,uint48),address,uint256)",
        "bytes",
    ],
    "WRAP_ETH": [
        "address",
        "uint256",
    ],
    "UNWRAP_WETH": [
        "address",
        "uint256",
    ],
    "PERMIT2_TRANSFER_FROM_BATCH": [
        "(address,address,uint160,address)[]",
    ],
    "BALANCE_CHECK_ERC20": [
        "address",
        "address",
        "uint256",
    ],
    "V4_SWAP": [
        "bytes",
        "bytes[]",
    ],
    "V3_POSITION_MANAGER_PERMIT": [
        "bytes",
    ],
    "V3_POSITION_MANAGER_CALL": [
        "bytes",
    ],
    "V4_INITIALIZE_POOL": [
        "(address,address,uint24,int24,address)",
        "uint160",
    ],
    "V4_POSITION_MANAGER_CALL": [
        "bytes",
    ],
    "EXECUTE_SUB_PLAN": [
        "bytes",
        "bytes[]",
    ],
}

# Source: https://github.com/Uniswap/v4-periphery/blob/main/src/libraries/Actions.sol
# NOTE: `INCREASE_LIQUIDITY_FROM_DELTAS` and `MINT_POSITION_FROM_DELTAS` are deprecated and should not be used, see comments in the source file.
# NOTE: `DONATE` is not supported in the position manager or router.
v4_actions = {
    "INCREASE_LIQUIDITY": 0x00,
    "DECREASE_LIQUIDITY": 0x01,
    "MINT_POSITION": 0x02,
    "BURN_POSITION": 0x03,
    "INCREASE_LIQUIDITY_FROM_DELTAS": 0x04,
    "MINT_POSITION_FROM_DELTAS": 0x05,
    "SWAP_EXACT_IN_SINGLE": 0x06,
    "SWAP_EXACT_IN": 0x07,
    "SWAP_EXACT_OUT_SINGLE": 0x08,
    "SWAP_EXACT_OUT": 0x09,
    "DONATE": 0x0A,
    "SETTLE": 0x0B,
    "SETTLE_ALL": 0x0C,
    "SETTLE_PAIR": 0x0D,
    "TAKE": 0x0E,
    "TAKE_ALL": 0x0F,
    "TAKE_PORTION": 0x10,
    "TAKE_PAIR": 0x11,
    "CLOSE_CURRENCY": 0x12,
    "CLEAR_OR_TAKE": 0x13,
    "SWEEP": 0x14,
    "WRAP": 0x15,
    "UNWRAP": 0x16,
    "MINT_6909": 0x17,
    "BURN_6909": 0x18,
}

# Source: https://github.com/Uniswap/universal-router/blob/d3123d99493aa6524bc5de44423c3961177758cb/test/integration-tests/shared/v4Planner.ts
v4_actions_abis = {
    "INCREASE_LIQUIDITY": [
        "uint256",
        "uint256",
        "uint128",
        "uint128",
        "bytes",
    ],
    "DECREASE_LIQUIDITY": [
        "uint256",
        "uint256",
        "uint128",
        "uint128",
        "bytes",
    ],
    "MINT_POSITION": [
        "(address,address,uint24,int24,address)",
        "int24",
        "int24",
        "uint256",
        "uint128",
        "uint128",
        "address",
        "bytes",
    ],
    "BURN_POSITION": [
        "uint256",
        "uint128",
        "uint128",
        "bytes",
    ],
    "INCREASE_LIQUIDITY_FROM_DELTAS": [
        "uint256",
        "uint128",
        "uint128",
        "bytes",
    ],
    "MINT_POSITION_FROM_DELTAS": [
        "(address,address,uint24,int24,address)",
        "int24",
        "int24",
        "uint128",
        "uint128",
        "address",
        "bytes",
    ],
    "SWAP_EXACT_IN_SINGLE": [
        "((address,address,uint24,int24,address),bool,uint128,uint128,uint256,bytes)",
    ],
    "SWAP_EXACT_IN": [
        "(address,(address,uint24,int24,address,bytes)[],int256[],uint128,uint128)",
    ],
    "SWAP_EXACT_OUT_SINGLE": [
        "((address,address,uint24,int24,address),bool,uint128,uint128,uint256,bytes)",
    ],
    "SWAP_EXACT_OUT": [
        "(address,(address,uint24,int24,address,bytes)[],int256[],uint128,uint128)",
    ],
    "SETTLE": [
        "address",
        "uint256",
        "bool",
    ],
    "SETTLE_ALL": [
        "address",
        "uint256",
    ],
    "SETTLE_PAIR": [
        "address",
        "address",
    ],
    "TAKE": [
        "address",
        "address",
        "uint256",
    ],
    "TAKE_ALL": [
        "address",
        "uint256",
    ],
    "TAKE_PORTION": [
        "address",
        "address",
        "uint256",
    ],
    "TAKE_PAIR": [
        "address",
        "address",
        "address",
    ],
    "CLOSE_CURRENCY": [
        "address",
    ],
    "CLEAR_OR_TAKE": [
        "address",
        "uint256",
    ],
    "SWEEP": [
        "address",
        "address",
    ],
    "WRAP": [
        "uint256",
    ],
    "UNWRAP": [
        "uint256",
    ],
    "MINT_6909": [
        "address",
        "uint256",
        "uint256",
    ],
    "BURN_6909": [
        "address",
        "uint256",
        "uint256",
    ],
}
