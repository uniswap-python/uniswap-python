# ruff: noqa: UP035
# ruff: noqa: UP006
# ruff: noqa: UP007
# ruff: noqa: UP045
# ruff: noqa: TRY002
# ruff: noqa: B006
# ruff: noqa: BLE001
# ruff: noqa: SIM102
import logging
import os
import time
from dataclasses import astuple
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

import eth_abi.abi
from eth_abi import encode
from eth_abi.packed import encode_packed
from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.exceptions import BadFunctionCallOutput, ContractLogicError, NameNotFound
from web3.types import (
    HexBytes,
    Nonce,
    TxParams,
    Wei,
)

from .constants import (
    ETH_ADDRESS,
    Q96,
    ZERO_HOOK,
    _netid_to_name,
    _permit2_contract_addresses_v4,
    _poolmanager_contract_addresses_v4,
    _position_descriptor_contract_addresses_v4,
    _position_manager_contract_addresses_v4,
    _quoter_contract_addresses_v4,
    _reserves_lens_contract_addresses_v4,
    _router_contract_addresses_v4,
    _stateview_contract_addresses_v4,
    universal_router_commands,
    universal_router_commands_abis,
    v4_actions,
    v4_actions_abis,
)
from .exceptions import InvalidToken
from .token import ERC20Token
from .types import (
    AddressLike,
    ModifyLiquidityParams,
    PathKey,
    PermitBatch,
    PermitSingle,
    PoolKey,
    SwapParams,
)
from .util import (
    _addr_to_str,
    _load_abi,
    _load_contract,
    _str_to_addr,
    get_sqrt_ratio_at_tick,
    realised_fee_percentage,
)

logger = logging.getLogger(__name__)


class Uniswap4:
    """
    Wrapper around Uniswap v4 contracts.
    """

    w3: Web3
    address: AddressLike
    last_nonce: Nonce

    def __init__(
        self,
        address: Union[str, AddressLike],
        private_key: Optional[str] = None,
        provider: Optional[str] = None,
        web3: Optional[Web3] = None,
        max_slippage: float = 0.01,
        gas_limit: float = 250000.0,
        gas_price: float = 1.80,
        priority_fee: float = 1.0,
        post_merge: bool = True,
    ) -> None:
        """
        :param address: The public address of the ETH wallet to use.
        :param private_key: The private key of the ETH wallet to use.
        :param provider: Can be optionally set to a Web3 provider URI. If none set, will fall back to the PROVIDER environment variable, or web3 if set.
        :param web3: Can be optionally set to a custom Web3 instance.
        :param max_slippage: Maximum slippage for a trade, as a float (0.01 is 1%).
        :param gas_limit: Maximum gas amount allocated for transactions.
        :param gas_price: Cost per unit of gas, in GWei.
        :param priority_fee: Amount of ETH to pay to the block producers, in GWei. Affects tx position in the block, the bigger value, the higher position is.
        :param post_merge: True is for post-Merge transations, False for legacy ones.
        """

        self.address: AddressLike = (
            _str_to_addr(address) if isinstance(address, str) else address
        )
        self.private_key = private_key

        self.max_slippage = max_slippage

        if web3:
            self.w3 = web3
        else:
            self.provider = provider or os.environ["PROVIDER"]
            self.w3 = Web3(
                Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60})
            )

        self.last_nonce = self.w3.eth.get_transaction_count(self.address)

        # This code automatically approves you for trading on the exchange.
        # max_approval is to allow the contract to exchange on your behalf.
        # max_approval_check checks that current approval is above a reasonable
        # number
        # The program cannot check for max_approval each time because it
        # decreases with each trade.
        self.max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
        self.max_approval_check_int = int(self.max_approval_check_hex, 16)
        self.gas_limit = gas_limit
        self.gas_price = gas_price
        self.post_merge = post_merge
        self.priority_fee = priority_fee

        chain_id = int(self.w3.net.version)
        self.net_id = chain_id
        if self.net_id in _netid_to_name:
            self.net_name = _netid_to_name[self.net_id]
            if self.net_name not in _quoter_contract_addresses_v4:
                raise Exception(f"Netid {self.net_id} is not supported yet.")
        else:
            raise Exception(f"Unknown netid: {self.net_id}")

        logger.info(f"Using {self.w3} ('{self.net_name}', netid: {self.net_id})")
        quoter_address = _quoter_contract_addresses_v4[self.net_name]
        router_address = _router_contract_addresses_v4[self.net_name]
        stateview_address = _stateview_contract_addresses_v4[self.net_name]
        permit2_address = _permit2_contract_addresses_v4[self.net_name]
        position_descriptor_address = _position_descriptor_contract_addresses_v4[
            self.net_name
        ]
        pool_manager_address = _poolmanager_contract_addresses_v4[self.net_name]
        position_manager_address = _position_manager_contract_addresses_v4[
            self.net_name
        ]
        reserves_lens_address = _reserves_lens_contract_addresses_v4[self.net_name]

        """
        NOTE: Following exception handling relates to the testnets only, as production contracts are always deployed.
        Specifically, PositionDescriptor is not deployed on Sepolia and Unichain Sepolia yet, so loading it will raise an error.
        However, this is a periphery helper which is not critical for core functionality.
        """
        try:
            self.quoter_address = _str_to_addr(quoter_address)
            self.quoter = _load_contract(
                self.w3, abi_name="uniswap-v4/quoter", address=self.quoter_address
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading quoter contract: {e}")

        try:
            self.router_address = _str_to_addr(router_address)
            self.router = _load_contract(
                self.w3, abi_name="uniswap-v4/router", address=self.router_address
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading router contract: {e}")

        try:
            self.stateview_address = _str_to_addr(stateview_address)
            self.stateview = _load_contract(
                self.w3, abi_name="uniswap-v4/stateview", address=self.stateview_address
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading stateview contract: {e}")

        try:
            self.permit2_address = _str_to_addr(permit2_address)
            self.permit2 = _load_contract(
                self.w3, abi_name="uniswap-v4/permit2", address=self.permit2_address
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading permit2 contract: {e}")

        try:
            self.position_descriptor_address = _str_to_addr(position_descriptor_address)
            self.position_descriptor = _load_contract(
                self.w3,
                abi_name="uniswap-v4/pos_descriptor",
                address=self.position_descriptor_address,
            )
        except NameNotFound as e:
            logger.error(
                f"Error occurred while loading position descriptor contract: {e}"
            )

        try:
            self.pool_manager_address = _str_to_addr(pool_manager_address)
            self.pool_manager = _load_contract(
                self.w3,
                abi_name="uniswap-v4/poolmanager",
                address=self.pool_manager_address,
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading pool manager contract: {e}")

        try:
            self.position_manager_address = _str_to_addr(position_manager_address)
            self.position_manager = _load_contract(
                self.w3,
                abi_name="uniswap-v4/pos_manager",
                address=self.position_manager_address,
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading position manager contract: {e}")

        try:
            self.reserves_lens_address = _str_to_addr(reserves_lens_address)
            self.reserves_lens = _load_contract(
                self.w3,
                abi_name="uniswap-v4/reserves_lens",
                address=self.reserves_lens_address,
            )
        except NameNotFound as e:
            logger.error(f"Error occurred while loading reserves lens contract: {e}")

    # Approvals
    def approve(
        self,
        token: AddressLike,
        max_approval: Optional[int] = None,
        delay_interval: Optional[int] = 7,
        approve_position_manager: bool = False,
    ) -> HexBytes:
        """Approve the router to spend a token on the user's behalf, or set up a permit for the position manager to pull the token from the user's wallet. For ETH, the router can pull from the user's wallet directly, so no approval is necessary.

        :param token: The address of the token to approve.
        :param max_approval: Optional. The maximum amount to approve. If not set, will approve a maximum possible amount.
        :param delay_interval: Optional. Seconds to wait between two approval transactions. Defaults to 7. Values less than 1 are treated as default.
        :param approve_position_manager: Optional. Whether to approve the position manager to spend the token. Defaults to False.
        """

        # If the token is not ETH, approve the router to spend it. For ETH, the router can pull from the user's wallet directly, so no approval is necessary.
        if _addr_to_str(token) != ETH_ADDRESS:
            max_approval = self.max_approval_int if not max_approval else max_approval
            function = self.erc20_contract(token).functions.approve(
                _addr_to_str(self.permit2_address), max_approval
            )
            logger.info(f"Approving {_addr_to_str(token)} for PERMIT2...")
            tx = self._build_and_send_tx(function)
            if delay_interval is None or delay_interval < 1:
                delay_interval = 7
            time.sleep(delay_interval)
        else:
            raise ValueError("ETH needs no approval.")
        # Give an exchange/router max approval for a token.
        max_approval = 2**100 - 1
        expiration: int = 10**12
        logger.info(f"Setting permit for {_addr_to_str(token)} at router contract...")
        function = self.permit2.functions.approve(
            _str_to_addr(token), self.router_address, max_approval, expiration
        )
        tx = self._build_and_send_tx(function)

        if approve_position_manager:
            # time.sleep(delay_interval)
            # max_approval = self.max_approval_int
            # function = self.erc20_contract(token).functions.approve(
            #     _addr_to_str(self.position_manager_address), max_approval
            # )
            # logger.info(f"Approving {_addr_to_str(token)} for PositionManager...")
            # tx = self._build_and_send_tx(function)

            time.sleep(delay_interval)
            max_approval = 2**100 - 1
            expiration = 10**12
            logger.info(
                f"Setting permit for {_addr_to_str(token)} at position manager contract..."
            )
            function = self.permit2.functions.approve(
                _str_to_addr(token),
                self.position_manager_address,
                max_approval,
                expiration,
            )
            tx = self._build_and_send_tx(function)
        return tx

    def approval(self, token: AddressLike) -> int:
        """Returns the current allowance for the router to spend a token on the user's behalf. Note that this is not the allowance of the token itself, but the allowance set in the Permit2 contract for the router to spend the token."""
        # [0]=current allowance, [1]=allowance expiration [2]=current nonce
        result = int(
            self.permit2.functions.allowance(
                self.address, token, self.router.address
            ).call()[0]
        )
        return result

    # Transaction parameters customization
    # Gas limit
    def get_gas_limit(self) -> float:
        """Returns the current gas limit for transactions."""
        return self.gas_limit

    def set_gas_limit(self, gas_limit: float) -> None:
        """Sets the gas limit for transactions."""
        self.gas_limit = gas_limit

    # Gas price in GWei
    def get_gas_price(self) -> float:
        """Returns the current gas price in GWei."""
        return self.gas_price

    def set_gas_price(self, gas_price: float) -> None:
        """Sets the gas price in GWei."""
        self.gas_price = gas_price

    # Priority fee in GWei
    def get_gas_priorityfee(self) -> float:
        """Returns the current priority fee in GWei."""
        return self.priority_fee

    def set_gas_priorityfee(self, priority_fee: float) -> None:
        """Sets the priority fee in GWei."""
        self.priority_fee = priority_fee

    # Slippage
    def get_max_slippage(self) -> float:
        """Returns the current maximum slippage as a float (0.01 is 1%)."""
        return self.max_slippage

    def set_max_slippage(self, max_slippage: float) -> None:
        """Sets the maximum slippage as a float (0.01 is 1%)."""
        self.max_slippage = max_slippage

    # Nonce management
    def update_last_nonce(self) -> None:
        """Updates the last nonce to the current nonce of the wallet. This can be used to resync the nonce if transactions have been sent outside of this class or custom nonce is used."""
        self.last_nonce = self.w3.eth.get_transaction_count(self.address)

    # StateView methods
    def stateview_get_fee_growth_globals(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ) -> Dict:
        """
        Retrieves the global fee growth of a pool.
        """
        if token0.lower() > token1.lower():
            token0, token1 = token1, token0

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)
        fee_growth_globals: Dict = self.stateview.functions.getFeeGrowthGlobals(
            pool_id
        ).call()
        return_value = {
            "feeGrowthGlobal0": fee_growth_globals[0],
            "feeGrowthGlobal1": fee_growth_globals[1],
        }
        return return_value

    def stateview_get_fee_growth_inside(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        tick_lower: int,
        tick_upper: int,
    ) -> Dict:
        """
        Calculates the fee growth inside a tick range of a pool
        """
        if token0.lower() > token1.lower():
            token0, token1 = token1, token0

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)
        fee_growth_inside: Dict = self.stateview.functions.getFeeGrowthInside(
            pool_id, tick_lower, tick_upper
        ).call()
        return_value = {
            "feeGrowthInside0X128": fee_growth_inside[0],
            "feeGrowthInside1X128": fee_growth_inside[1],
        }
        return return_value

    def stateview_get_liquidity(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ) -> int:
        """Retrieves the total liquidity of a pool."""
        if token0.lower() > token1.lower():
            token0, token1 = token1, token0

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)

        liquidity: int = self.stateview.functions.getLiquidity(pool_id).call()
        return liquidity

    def stateview_get_position_info(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        owner: str,
        tick_lower: int,
        tick_upper: int,
        token_id: int,
    ) -> Dict:
        """
        Retrieves position info in a pool.

        :param token_id: TokenID of the correspoding NFT
        """
        if token0.lower() > token1.lower():
            token1, token0 = token0, token1

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)

        salt = HexBytes(token_id.to_bytes(32, byteorder="big"))
        position_info: Dict = self.stateview.functions.getPositionInfo(
            pool_id, owner, tick_lower, tick_upper, salt
        ).call()
        return_value = {
            "liquidity": position_info[0],
            "feeGrowthInside0LastX128": position_info[1],
            "feeGrowthInside1LastX128": position_info[2],
        }
        return return_value

    def stateview_get_slot0(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
    ) -> Dict:
        """
        Returns current state of the pool.
        """
        if token0.lower() > token1.lower():
            token1, token0 = token0, token1

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)

        slot: Dict = self.stateview.functions.getSlot0(pool_id).call()
        return_value = {
            "sqrtPriceX96": slot[0],
            "tick": slot[1],
            "protocolFee": slot[2],
            "lpFee": slot[3],
        }
        return return_value

    def stateview_get_tick_bitmap(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        tick: int,
    ) -> int:
        """
        Retrieves the tick bitmap of a pool at a specific tick.

        :param tick: MUST be int16
        """
        if token0.lower() > token1.lower():
            token1, token0 = token0, token1

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)

        tick_bitmap: int = self.stateview.functions.getTickBitmap(pool_id, tick).call()
        return tick_bitmap

    def stateview_get_tick_fee_growth_outside(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        tick: int,
    ) -> Dict:
        """
        Retrieves the fee growth outside a tick range of a pool
        """
        if token0.lower() > token1.lower():
            token1, token0 = token0, token1

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)
        fee_growth_outside: Dict = self.stateview.functions.getTickFeeGrowthOutside(
            pool_id, tick
        ).call()
        return_value = {
            "feeGrowthOutside0X128": fee_growth_outside[0],
            "feeGrowthOutside1X128": fee_growth_outside[1],
        }
        return return_value

    def stateview_get_tick_pool_info(
        self,
        token0: str,
        token1: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        tick: int,
    ) -> Dict:
        """
        Retrieves the tick information of a pool at a specific tick.
        """
        if token0.lower() > token1.lower():
            token1, token0 = token0, token1

        pool = PoolKey(token0, token1, fee, tick_spacing, hooks)
        pool_id = self.get_pool_id(pool)
        tick_info: Dict = self.stateview.functions.getTickInfo(pool_id, tick).call()
        return_value = {
            "liquidityGross": tick_info[0],
            "liquidityNet": tick_info[1],
            "feeGrowthOutside0X128": tick_info[2],
            "feeGrowthOutside1X128": tick_info[3],
        }
        return return_value

    # ReservesLens methods
    def reserves_lens_get_pool_tvl(
        self, pool_key: PoolKey, custom_provider: str = ""
    ) -> Dict:
        """
        Retrieves the total value locked (TVL) of a pool.
        See https://github.com/Uniswap/v4-periphery/blob/main/src/interfaces/IReservesLens.sol for more details.

        :param pool_key: The PoolKey object representing the pool.
        :param custom_provider: The custom provider address, empty string for default.
        :returns: A dictionary containing the reserves of the pool.
        """
        if custom_provider == "":
            reserves: Dict = self.reserves_lens.functions.getPoolTVL(
                _addr_to_str(self.pool_manager_address), astuple(pool_key)
            ).call()
        else:
            reserves = self.reserves_lens.functions.getPoolTVL(
                _addr_to_str(self.pool_manager_address),
                astuple(pool_key),
                custom_provider,
            ).call()
        return_value = {
            "coreAmount0": reserves[0],
            "coreAmount1": reserves[1],
            "hookReserves0": reserves[2],
            "hookReserves1": reserves[3],
            "hookEffective0": reserves[4],
            "hookEffective1": reserves[5],
            "sqrtPriceX96": reserves[6],
            "tick": reserves[7],
            "activeLiquidity": reserves[8],
            "blockNumber": reserves[9],
            "statsProvider": reserves[10],
            "hookPermissions": reserves[11],
            "hasCustomAccounting": reserves[12],
            "statsStatus": reserves[13],
        }
        return return_value

    def reserves_lens_get_pool_tvl_batch(
        self, pool_keys: List[PoolKey], custom_provider: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Retrieves the total value locked (TVL) of multiple pools in a batch.
        See https://github.com/Uniswap/v4-periphery/blob/main/src/interfaces/IReservesLens.sol for more details.

        :param pool_keys: A list of PoolKey objects representing the pools.
        :param custom_provider: The custom provider addresses for each pool. If None, will use default for all pools.
        :returns: A list of dictionaries containing the reserves of each pool.
        """
        if custom_provider is None:
            custom_provider = [""] * len(pool_keys)

            reserves_list: List = self.reserves_lens.functions.getPoolTVLBatch(
                _addr_to_str(self.pool_manager_address),
                [astuple(pool_key) for pool_key in pool_keys],
            ).call()
        else:
            reserves_list = self.reserves_lens.functions.getPoolTVLBatch(
                _addr_to_str(self.pool_manager_address),
                [astuple(pool_key) for pool_key in pool_keys],
                custom_provider,
            ).call()

        return_value = []
        for reserves in reserves_list:
            return_value.append(
                {
                    "coreAmount0": reserves[0],
                    "coreAmount1": reserves[1],
                    "hookReserves0": reserves[2],
                    "hookReserves1": reserves[3],
                    "hookEffective0": reserves[4],
                    "hookEffective1": reserves[5],
                    "sqrtPriceX96": reserves[6],
                    "tick": reserves[7],
                    "activeLiquidity": reserves[8],
                    "blockNumber": reserves[9],
                    "statsProvider": reserves[10],
                    "hookPermissions": reserves[11],
                    "hasCustomAccounting": reserves[12],
                    "statsStatus": reserves[13],
                }
            )

        return return_value

    def reserves_lens_get_tvl_paged(
        self,
        pool_key: PoolKey,
        cursor: bytes,
        custom_provider: str = "",
        max_reads: int = 0,
    ) -> Tuple[Dict, bytes, bool]:
        """
        Retrieves the total value locked (TVL) of multiple pools in a paged manner.
        See https://github.com/Uniswap/v4-periphery/blob/main/src/interfaces/IReservesLens.sol for more details.

        :param pool_key: A list of PoolKey objects representing the pools.
        :param cursor: The cursor for paged retrieval.
        :param custom_provider: The custom provider address, empty string for default.
        :param max_reads: The maximum number of reads to perform using custom provider.
        :returns: A tuple containing the reserves dictionary, the next cursor, and a boolean indicating if the paged retrieval is done.
        """
        if custom_provider == "":
            reserves_tuple, next_cursor, done = (
                self.reserves_lens.functions.getPoolTVLPaged(
                    _addr_to_str(self.pool_manager_address),
                    astuple(pool_key),
                    cursor,
                ).call()
            )
        else:
            reserves_tuple, next_cursor, done = (
                self.reserves_lens.functions.getPoolTVLPaged(
                    _addr_to_str(self.pool_manager_address),
                    astuple(pool_key),
                    custom_provider,
                    cursor,
                    max_reads,
                ).call()
            )

        reserves: Dict = {
            "coreAmount0": reserves_tuple[0],
            "coreAmount1": reserves_tuple[1],
            "hookReserves0": reserves_tuple[2],
            "hookReserves1": reserves_tuple[3],
            "hookEffective0": reserves_tuple[4],
            "hookEffective1": reserves_tuple[5],
            "sqrtPriceX96": reserves_tuple[6],
            "tick": reserves_tuple[7],
            "activeLiquidity": reserves_tuple[8],
            "blockNumber": reserves_tuple[9],
            "statsProvider": reserves_tuple[10],
            "hookPermissions": reserves_tuple[11],
            "hasCustomAccounting": reserves_tuple[12],
            "statsStatus": reserves_tuple[13],
        }

        return_value = (reserves, next_cursor, done)
        return return_value

    def reserves_lens_get_populated_ticks_in_word(
        self, pool_key: PoolKey, word_position: int
    ) -> List[Dict]:
        """
        Retrieves the populated ticks in a specific word of a pool.
        See https://github.com/Uniswap/v4-periphery/blob/main/src/interfaces/IReservesLens.sol for more details.

        :param pool_key: The PoolKey object representing the pool.
        :param word_position: The position of the word to retrieve.
        :returns: A list of dictionaries containing the populated ticks.
        """
        results: List = self.reserves_lens.functions.getPopulatedTicksInWord(
            _addr_to_str(self.pool_manager_address),
            astuple(pool_key),
            word_position,
        ).call()
        return_value: List[Dict] = []
        for result in results:
            return_value.append(
                {
                    "tick": result[0],
                    "liquidityNet": result[1],
                    "liquidityGross": result[2],
                }
            )
        return return_value

    # PositionDescriptor methods
    def position_descriptor_get_currency_ratio_priority(self, currency: str) -> int:
        """
        For certain currencies on mainnet, the smaller the currency, the higher the priority.
        And those with the higher priority values (more positive values) will be in the numerator of the price ratio

        :returns: The priority of a currency.
        """
        ratio_priority: int = int(
            self.position_descriptor.functions.currencyRatioPriority(currency).call()
        )
        return_value = ratio_priority
        return return_value

    def position_descriptor_get_flip_ratio(
        self, currency0: str, currency1: str
    ) -> bool:
        """
        :returns: True if currency0 has higher priority than currency1
        """
        flip_ratio: bool = bool(
            self.position_descriptor.functions.flipRatio(currency0, currency1).call()
        )
        return_value = flip_ratio
        return return_value

    def position_descriptor_get_native_currency_label(self) -> str:
        """
        :returns: The label for the native currency as a string
        """
        native_currency_label: str = str(
            self.position_descriptor.functions.nativeCurrencyLabel().call()
        )
        return_value = native_currency_label
        return return_value

    def position_descriptor_get_pool_manager(self) -> str:
        """
        :returns: PoolManager address as a string
        """
        pool_manager: str = str(self.position_descriptor.functions.poolManager().call())
        return_value = pool_manager
        return return_value

    def position_descriptor_get_token_uri(self, pos_manager: str, token_id: int) -> str:
        """
        Produces the URI describing a particular token ID
        Note this URI may be a data: URI with the JSON contents directly inlined

        :returns: The URI of the ERC721-compliant metadata
        """
        token_uri: str = str(
            self.position_descriptor.functions.tokenURI(pos_manager, token_id).call()
        )
        return_value = token_uri
        return return_value

    def position_descriptor_get_wrapped_native_address(self) -> str:
        """
        :returns: The wrapped native currency address as a string
        """
        wrapped_native_address: str = str(
            self.position_descriptor.functions.wrappedNative().call()
        )
        return_value = wrapped_native_address
        return return_value

    # PositionManager methods
    # Read methods
    def position_manager_get_domain_separator(
        self,
    ) -> bytes:
        """
        :returns: The domain separator for the current chain; bytes32
        """
        domain_separator: bytes = bytes(
            self.position_manager.functions.DOMAIN_SEPARATOR().call()
        )
        return_value = domain_separator
        return return_value

    def position_manager_get_weth9(
        self,
    ) -> str:
        """
        :returns: The wrapped native token address
        """
        weth9: str = str(self.position_manager.functions.WETH9().call())
        return_value = weth9
        return return_value

    def position_manager_get_balance_of(self, address: str) -> int:
        """
        :returns: The number of tokens in owner's address.
        """
        balance: int = int(self.position_manager.functions.balanceOf(address).call())
        return_value = balance
        return return_value

    def position_manager_get_approved(self, token_id: int) -> str:
        """
        :returns: The account approved for a token.
        """
        operator: str = str(
            self.position_manager.functions.getApproved(token_id).call()
        )
        return_value = operator
        return return_value

    def position_manager_get_pool_and_position_info(self, token_id: int) -> Dict:
        """
        :returns: The PoolKey class object and position info of a position
        """
        pool_key_tuple, info = self.position_manager.functions.getPoolAndPositionInfo(
            token_id
        ).call()
        pool_key: PoolKey = PoolKey(*pool_key_tuple)
        return_value = {
            "poolKey": pool_key,
            "info": info,
        }
        return return_value

    def position_manager_get_position_liquidity(self, token_id: int) -> int:
        """
        :returns: The liquidity of a position
        """
        position_liquidity: int = int(
            self.position_manager.functions.getPositionLiquidity(token_id).call()
        )
        return_value = position_liquidity
        return return_value

    def position_manager_get_is_approved_for_all(
        self, owner: str, operator: str
    ) -> bool:
        """
        :returns: True if the operator is allowed to manage all of the assets of owner
        """
        is_approved_for_all: bool = bool(
            self.position_manager.functions.isApprovedForAll(owner, operator).call()
        )
        return_value = is_approved_for_all
        return return_value

    def position_manager_get_msg_sender(
        self,
    ) -> str:
        """
        :returns: address considered executor of the actions

        The other context functions, _msgData and _msgValue, are not supported by this contract.
        In many contracts this will be the address that calls the initial entry point
        that calls `_executeActions` `msg.sender` shouldn't be used, as this will be
        the v4 pool manager contract that calls `unlockCallback`
        If using ReentrancyLock.sol, this function can return _getLocker()
        """
        msg_sender: str = str(self.position_manager.functions.msgSender().call())
        return_value = msg_sender
        return return_value

    def position_manager_get_name(
        self,
    ) -> str:
        """
        :returns: The name of the PositionManager token
        """
        name: str = str(self.position_manager.functions.name().call())
        return_value = name
        return return_value

    def position_manager_get_next_token_id(
        self,
    ) -> int:
        """
        :returns: The ID that will be used for the next minted liquidity position
        """
        next_token_id: int = int(self.position_manager.functions.nextTokenId().call())
        return_value = next_token_id
        return return_value

    def position_manager_get_nonces(self, owner: str, word: int) -> int:
        """
        :returns: Mapping of nonces consumed by each address, where a nonce is a single bit on the 256-bit bitmap
        """
        bitmap: int = int(self.position_manager.functions.nonces(owner, word).call())
        return_value = bitmap
        return return_value

    def position_manager_get_owner_of(self, token_id: int) -> str:
        """
        :returns: The owner of the position for a given token ID
        """
        owner: str = str(self.position_manager.functions.ownerOf(token_id).call())
        return_value = owner
        return return_value

    def position_manager_get_permit2(
        self,
    ) -> str:
        """
        :returns: The Permit2 contract to forward approvals
        """
        permit2: str = str(self.position_manager.functions.permit2().call())
        return_value = permit2
        return return_value

    def position_manager_get_pool_keys(self, pool_id_trunc: bytes) -> PoolKey:
        """
        :param pool_id_trunc: The truncated ID of the pool, first 25 bytes of common pool_id
        :returns: The PoolKey class object for a given token ID
        """
        pool_keys_tuple = self.position_manager.functions.poolKeys(pool_id_trunc).call()
        pool_keys: PoolKey = PoolKey(*pool_keys_tuple)
        return_value = pool_keys
        return return_value

    def position_manager_get_position_info(self, token_id: int) -> int:
        """
        :returns: The position info for a given token ID
        """
        position_info: int = int(
            self.position_manager.functions.positionInfo(token_id).call()
        )
        return_value = position_info
        return return_value

    def position_manager_get_subscriber(self, token_id: int) -> str:
        """
        :returns: The subscriber of the position for a given token ID
        """
        subscriber: str = str(
            self.position_manager.functions.subscriber(token_id).call()
        )
        return_value = subscriber
        return return_value

    def position_manager_get_is_support_interface(
        self,
        interface_id: bytes,
    ) -> bool:
        """
        :param interface_id: The interface ID to check; should be 'bytes4'
        :returns: True if specifeid interface is supported by the PositionManager contract
        """
        if len(interface_id) != 4:
            raise ValueError("interface_id should be 4 bytes long")
        is_supported: bool = bool(
            self.position_manager.functions.supportsInterface(interface_id).call()
        )
        return_value = is_supported
        return return_value

    def position_manager_get_symbol(
        self,
    ) -> str:
        """
        :returns: The symbol of the PositionManager token
        """
        symbol: str = str(self.position_manager.functions.symbol().call())
        return_value = symbol
        return return_value

    def position_manager_get_token_descriptor(
        self,
    ) -> str:
        """
        :returns: The address of the PositionDescriptor contract as a string
        """
        token_descriptor: str = str(
            self.position_manager.functions.tokenDescriptor().call()
        )
        return_value = token_descriptor
        return return_value

    def position_manager_get_position_uri(self, token_id: int) -> str:
        """
        :returns: The URI of the position manager's ERC721-compliant metadata for a given token ID
        """
        uri: str = str(self.position_manager.functions.tokenURI(token_id).call())
        return_value = uri
        return return_value

    def position_manager_get_unsubscribe_gas_limit(self) -> int:
        """
        :returns: The gas limit used when unsubscribing from a position.
        """
        unsubscribe_gas_limit: int = (
            self.position_manager.functions.unsubscribeGasLimit().call()
        )
        return_value = unsubscribe_gas_limit
        return return_value

    # Write methods
    def position_manager_approve(self, spender: str, token_id: int) -> HexBytes:
        """
        Change or reaffirm the approved address for an NFT
        Zero address removes existing approval.
        """
        function = self.position_manager.functions.approve(spender, token_id)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def position_manager_initialize_pool(
        self, pool_key: PoolKey, sqrt_price_x96: int, payable_amount: int
    ) -> HexBytes:
        """
        Initialize a Uniswap v4 Pool with the given parameters.
        """
        function = self.position_manager.functions.initializePool(
            astuple(pool_key), sqrt_price_x96
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_modify_liquidities(
        self, unlock_data: bytes, deadline: int, payable_amount: int
    ) -> HexBytes:
        """
        Unlocks Uniswap v4 PoolManager and batches actions for modifying liquidity
        """
        function = self.position_manager.functions.modifyLiquidities(
            unlock_data, deadline
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_modify_liquidities_without_unlock(
        self, actions: bytes, params: List[bytes], payable_amount: int
    ) -> HexBytes:
        """
        Batches actions for modifying liquidity without unlocking v4 PoolManager

        This must be called by a contract that has already unlocked the v4 PoolManager
        """
        function = self.position_manager.functions.modifyLiquiditiesWithoutUnlock(
            actions, params
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_multicall(
        self, data: List[bytes], payable_amount: int
    ) -> HexBytes:
        """
        Call multiple functions in the current contract in a single transaction, with the possibility of sending ETH along with the calls.
        """
        function = self.position_manager.functions.multicall(data)
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_permit(
        self,
        spender: str,
        token_id: int,
        deadline: int,
        nonce: int,
        signature: bytes,
        payable_amount: int,
    ) -> HexBytes:
        """
        Approve of a specific token ID for spending by spender via signature
        """
        function = self.position_manager.functions.permit(
            spender, token_id, deadline, nonce, signature
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_permit2_single(
        self,
        owner: str,
        permit_single: PermitSingle,
        signature: bytes,
        payable_amount: int,
    ) -> HexBytes:
        """
        Allows forwarding a single permit to permit2
        """
        function = self.position_manager.functions.permit(
            owner, astuple(permit_single), signature
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_permit2_batch(
        self,
        owner: str,
        permit_batch: PermitBatch,
        signature: bytes,
        payable_amount: int,
    ) -> HexBytes:
        """
        Allows forwarding batch permits to permit2
        """
        function = self.position_manager.functions.permit(
            owner, astuple(permit_batch), signature
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_permit_for_all(
        self,
        owner: str,
        operator: str,
        approved: bool,
        deadline: int,
        nonce: int,
        signature: bytes,
        payable_amount: int,
    ) -> HexBytes:
        """
        Set an operator with full permission to an owner's tokens via signature
        """
        function = self.position_manager.functions.permitForAll(
            owner, operator, approved, deadline, nonce, signature
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_revoke_nonce(
        self, nonce: int, payable_amount: int
    ) -> HexBytes:
        """
        Revoke a nonce by spending it, preventing it from being used again
        """
        function = self.position_manager.functions.revokeNonce(nonce)
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_safe_transfer_from(
        self, from_addr: str, to_addr: str, token_id: int, payable_amount: int
    ) -> HexBytes:
        """
        Transfer a position from one address to another
        """
        function = self.position_manager.functions.safeTransferFrom(
            from_addr, to_addr, token_id
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_safe_transfer_from_with_data(
        self,
        from_addr: str,
        to_addr: str,
        token_id: int,
        data: bytes,
        payable_amount: int,
    ) -> HexBytes:
        """
        Transfer a position from one address to another with additional data
        """
        function = self.position_manager.functions.safeTransferFrom(
            from_addr, to_addr, token_id, data
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_set_approval_for_all(
        self, operator: str, approved: bool, payable_amount: int
    ) -> HexBytes:
        """
        Enable or disable approval for a third party ("operator") to manage all of `msg.sender`'s assets
        """
        function = self.position_manager.functions.setApprovalForAll(operator, approved)
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_subscribe(
        self, token_id: int, new_subscriber: str, data: bytes, payable_amount: int
    ) -> HexBytes:
        """
        Enables the subscriber to receive notifications for a respective position
        """
        function = self.position_manager.functions.subscribe(
            token_id, new_subscriber, data
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_transfer_from(
        self, from_addr: str, to_addr: str, token_id: int, payable_amount: int
    ) -> HexBytes:
        """
        Overrides solmate transferFrom in case a notification to subscribers is needed
        """
        function = self.position_manager.functions.transferFrom(
            from_addr, to_addr, token_id
        )
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def position_manager_unsubscribe(
        self, token_id: int, payable_amount: int
    ) -> HexBytes:
        """
        Removes the subscriber from receiving notifications for a respective position
        """
        function = self.position_manager.functions.unsubscribe(token_id)
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    # PoolManager methods
    # Read methods
    def pool_manager_get_allowance(
        self, owner: str, spender: str, token_id: int
    ) -> int:
        """
        Spender allowance of an id.
        """
        allowance: int = int(
            self.pool_manager.functions.allowance(owner, spender, token_id).call()
        )
        return_value = allowance
        return return_value

    def pool_manager_get_balance_of(self, address: str, token_id: int) -> int:
        """
        The number of tokens in owner's address.
        """
        balance: int = int(
            self.pool_manager.functions.balanceOf(address, token_id).call()
        )
        return_value = balance
        return return_value

    def pool_manager_get_extsload(self, slot: bytes) -> bytes:
        """
        Called by external contracts to access granular pool state
        """
        value: bytes = self.pool_manager.functions.extsload(slot).call()
        return_value = value
        return return_value

    def pool_manager_get_extsload_sequence(
        self, start_slot: bytes, slots_count: int
    ) -> List[bytes]:
        """
        Called by external contracts to access a sequence of storage slots
        """
        value: List[bytes] = self.pool_manager.functions.extsload(
            start_slot, slots_count
        ).call()
        return_value = value
        return return_value

    def pool_manager_get_extsload_sparse(self, slots: List[bytes]) -> List[bytes]:
        """
        Called by external contracts to access a sparse set of storage slots
        """
        value: List[bytes] = self.pool_manager.functions.extsload(slots).call()
        return_value = value
        return return_value

    def pool_manager_get_exttload_sparse(self, slots: List[bytes]) -> List[bytes]:
        """
        Called by external contracts to access sparse transient pool state
        """
        value: List[bytes] = self.pool_manager.functions.exttload(slots).call()
        return_value = value
        return return_value

    def pool_manager_get_exttload(self, slot: bytes) -> bytes:
        """
        Called by external contracts to access transient storage of the contract
        """
        value: bytes = self.pool_manager.functions.exttload(slot).call()
        return_value = value
        return return_value

    def pool_manager_get_is_operator(self, owner: str, operator: str) -> bool:
        """
        Checks if a spender is approved by an owner as an operator
        """
        is_operator: bool = self.pool_manager.functions.isOperator(
            owner, operator
        ).call()
        return_value = is_operator
        return return_value

    def pool_manager_get_owner(self) -> str:
        """
        Retrieve the contract owner.
        """
        owner: str = str(self.pool_manager.functions.owner().call())
        return_value = owner
        return return_value

    def pool_manager_get_protocol_fee_controller(self) -> str:
        """
        Returns the current protocol fee controller address
        """
        protocol_fee_controller: str = str(
            self.pool_manager.functions.protocolFeeController().call()
        )
        return_value = protocol_fee_controller
        return return_value

    def pool_manager_get_protocol_fees_accrued(self, address: str) -> int:
        """
        Given a currency address, returns the protocol fees accrued in that currency.
        """
        protocol_fees_accrued: int = int(
            self.pool_manager.functions.protocolFeesAccrued(address).call()
        )
        return_value = protocol_fees_accrued
        return return_value

    def pool_manager_get_supports_interface(self, interface_id: bytes) -> bool:
        """
        Checks if a given interface ID is supported by the contract

        :param interface_id: The interface ID to check; should be `bytes4`
        :returns: True if specifeid interface is supported by the PoolManager contract
        """
        if len(interface_id) != 4:
            raise ValueError("interface_id should be 4 bytes long")
        supports_interface: bool = bool(
            self.pool_manager.functions.supportsInterface(interface_id).call()
        )
        return_value = supports_interface
        return return_value

    # Write methods
    def pool_manager_approve(
        self, spender: str, token_id: int, amount: int
    ) -> HexBytes:
        """
        Approves an amount of an id to a spender.
        """
        function = self.pool_manager.functions.approve(spender, token_id, amount)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_burn(self, from_addr: str, token_id: int, amount: int) -> HexBytes:
        """
        Called by the user to move value from ERC6909 balance.
        """
        function = self.pool_manager.functions.burn(from_addr, token_id, amount)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_clear(self, currency: str, amount: int) -> HexBytes:
        """
        !!!WARNING!!! - Any currency that is cleared, will be non-retrievable, and locked in the contract permanently.
        A call to clear will zero out a positive balance WITHOUT a corresponding transfer.
        This could be used to clear a balance that is considered dust.
        Additionally, the amount must be the exact positive balance.
        This is to enforce that the caller is aware of the amount being cleared.
        """
        function = self.pool_manager.functions.clear(currency, amount)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_collect_protocol_fees(
        self, recipient: str, currency: str, amount: int
    ) -> HexBytes:
        """
        Collects the protocol fees for a given recipient and currency, returning the amount collected
        This will revert if the contract is unlocked
        """
        function = self.pool_manager.functions.collectProtocolFees(
            recipient, currency, amount
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_donate(
        self, pool_key: PoolKey, amount0: int, amount1: int, hook_data: bytes
    ) -> HexBytes:
        """
        Donate the given currency amounts to the in-range liquidity providers of a pool
        """
        function = self.pool_manager.functions.donate(
            astuple(pool_key), amount0, amount1, hook_data
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_initialize(
        self, pool_key: PoolKey, sqrt_price_x96: int
    ) -> HexBytes:
        """
        Initialize the state for a given pool ID.
        """
        function = self.pool_manager.functions.initialize(
            astuple(pool_key), sqrt_price_x96
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_mint(self, to_addr: str, token_id: int, amount: int) -> HexBytes:
        """
        Called by the user to move value into ERC6909 balance.
        """
        function = self.pool_manager.functions.mint(to_addr, token_id, amount)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_modify_liquidity(
        self,
        pool_key: PoolKey,
        liquidity_params: ModifyLiquidityParams,
        hook_data: bytes,
    ) -> HexBytes:
        """
        Modify the liquidity for the given pool.
        """
        function = self.pool_manager.functions.modifyLiquidity(
            astuple(pool_key), astuple(liquidity_params), hook_data
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_set_operator(self, operator: str, approved: bool) -> HexBytes:
        """
        Sets or removes an operator for the caller.
        """
        function = self.pool_manager.functions.setOperator(operator, approved)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_set_protocol_fee(
        self, pool_key: PoolKey, new_protocol_fee: int
    ) -> HexBytes:
        """
        Sets the protocol fee for the given pool.
        """
        function = self.pool_manager.functions.setProtocolFee(
            astuple(pool_key), new_protocol_fee
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_set_protocol_fee_controller(self, controller: str) -> HexBytes:
        """
        Sets a new protocol fee controller.
        """
        function = self.pool_manager.functions.setProtocolFeeController(controller)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_settle(self, payable_amount: int) -> HexBytes:
        """
        Called by the user to pay what is owed.
        """
        function = self.pool_manager.functions.settle()
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def pool_manager_settle_for(self, recipient: str, payable_amount: int) -> HexBytes:
        """
        Called by the user to pay on behalf of another address.
        """
        function = self.pool_manager.functions.settleFor(recipient)
        tx = self._build_and_send_tx(
            function, self._get_tx_params(value=payable_amount)
        )
        return tx

    def pool_manager_swap(
        self, pool_key: PoolKey, params: SwapParams, hook_data: bytes
    ) -> HexBytes:
        """
        Swap against the given pool.
        """
        function = self.pool_manager.functions.swap(
            astuple(pool_key), astuple(params), hook_data
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_sync(self, currency: str) -> HexBytes:
        """
        Writes the current ERC20 balance of the specified currency to transient storage.
        This is used to checkpoint balances for the manager and derive deltas for the caller.
        This MUST be called before any ERC20 tokens are sent into the contract, see documentation for more details.
        """
        function = self.pool_manager.functions.sync(currency)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_take(self, currency: str, to_addr: str, amount: int) -> HexBytes:
        """
        Called by the user to net out some value owed to the user.
        """
        function = self.pool_manager.functions.take(currency, to_addr, amount)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_transfer(
        self, to_addr: str, token_id: int, amount: int
    ) -> HexBytes:
        """
        Transfers an amount of an id from the caller to a receiver.
        """
        function = self.pool_manager.functions.transfer(to_addr, token_id, amount)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_transfer_from(
        self, sender: str, receiver: str, token_id: int, amount: int
    ) -> HexBytes:
        """
        Transfers an amount of an id from a sender to a receiver.
        """
        function = self.pool_manager.functions.transferFrom(
            sender, receiver, token_id, amount
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_transfer_ownership(self, new_owner: str) -> HexBytes:
        """
        Transfers ownership of the contract to a new owner.
        """
        function = self.pool_manager.functions.transferOwnership(new_owner)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_unlock(self, data: bytes) -> HexBytes:
        """
        All interactions on the contract that account deltas require unlocking.
        A caller that calls `unlock` must implement `IUnlockCallback(msg.sender).unlockCallback(data)`,
        where they interact with the remaining functions on this contract.
        """
        function = self.pool_manager.functions.unlock(data)
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    def pool_manager_update_dynamic_lp_fee(
        self, pool_key: PoolKey, new_dynamic_lp_fee: int
    ) -> HexBytes:
        """
        Updates the pools lp fees for the a pool that has enabled dynamic lp fees.
        """
        function = self.pool_manager.functions.updateDynamicLPFee(
            astuple(pool_key), new_dynamic_lp_fee
        )
        tx = self._build_and_send_tx(function, self._get_tx_params())
        return tx

    # Tokens price functions
    def get_token_token_spot_price(
        self,
        token0: str,
        token1: str,
        fee: int = 500,
        tick_spacing: int = 10,
        hooks: str = ZERO_HOOK,
    ) -> float:
        """
        :param token0: The first token in the pair.
        :param token1: The second token in the pair.
        :param fee: The fee tier for the swap.
        :param tick_spacing: The tick spacing for the swap.
        :param hooks: The hooks for the swap.
        :return: The current spot price for token to token trades.
        """

        if token0.lower() < token1.lower():
            den0 = self.get_token(_str_to_addr(token0)).decimals
            den1 = self.get_token(_str_to_addr(token1)).decimals
            zero_for_one = True
        else:
            den0 = self.get_token(_str_to_addr(token1)).decimals
            den1 = self.get_token(_str_to_addr(token0)).decimals
            zero_for_one = False

        if token0.lower() > token1.lower():
            token1, token0 = token0, token1

        spot_price_x96: int = self.stateview_get_slot0(
            token0, token1, fee, tick_spacing, hooks
        )["sqrtPriceX96"]

        spot_price: float = (spot_price_x96 * spot_price_x96 * 10**den0 >> (96 * 2)) / (
            10**den1
        )
        if not zero_for_one:
            spot_price = 1 / spot_price
        return spot_price

    # Estimates slippage for the given amount of token0
    def estimate_price_impact(
        self,
        token0: str,
        token1: str,
        qty: int,
        fee: int = 500,
        tick_spacing: int = 10,
        hooks: str = ZERO_HOOK,
        hook_data: bytes = b"",
    ) -> float:
        """
        :param token0: The token to be sold.
        :param token1: The token to be bought.
        :param qty: The amount of `token0` to be sold.
        :param fee: The fee tier for the swap.
        :param tick_spacing: The tick spacing for the swap.
        :param hooks: The hooks for the swap.
        :param hook_data: The hook data for the swap.
        :return: the estimated price impact as a positive float (0.01 = 1%).

        See ``examples/v4_examples.py`` for an example which uses this.

        NOTE: Does not support multi-hop swaps, should be used for single-hop swaps only.
        """

        try:
            spot_price = self.get_token_token_spot_price(
                token0, token1, fee, tick_spacing, hooks
            )
        except (ArithmeticError, BadFunctionCallOutput):
            # ArithmeticError is raised when `token0` amount in the pool
            # equals 0.
            # BadFunctionCallOutput is raised when the pool for
            # given `(token0, token1, fee)` doesn't exist
            return 1

        if spot_price == 0:
            # Occurs when `token1` amount in the pool equals 0
            return 1
        try:
            quote_amount = self.get_quote_exact_input_single(
                token0, token1, qty, fee, tick_spacing, hooks, hook_data
            )
        except ContractLogicError:
            # ContractLogicError is raised when the pool's contract for given
            # `(token0, token1, fee)` hasn't been deployed.
            return 1
        price = (
            quote_amount / (qty / (10 ** self.get_token(_str_to_addr(token0)).decimals))
        ) / 10 ** self.get_token(_str_to_addr(token1)).decimals

        # calculate and subtract the realised fees from the price impact.  See:
        # https://github.com/uniswap-python/uniswap-python/issues/310
        price_impact_with_fees: float = (spot_price - price) / spot_price
        fee_realised_percentage: float = realised_fee_percentage(fee, qty)
        price_impact_real: float = price_impact_with_fees - fee_realised_percentage
        return price_impact_real

    # Quoter methods
    # Read methods
    def get_quote_exact_input_single(
        self,
        token0: str,
        token1: str,
        qty: int,
        fee: int,
        tick_spacing: int,
        hooks: str = ZERO_HOOK,
        hook_data: bytes = b"",
    ) -> int:
        """
        :param token0: The token to be sold.
        :param token1: The token to be bought.
        :param qty: The amount of `token0` to be sold.
        :param fee: The fee tier for the swap.
        :param tick_spacing: The tick spacing for the swap.
        :param hooks: The hooks for the swap.
        :param hook_data: The hook data for the swap.
        :return: Quote for token to token single hop trades with an exact input.
        """
        if token0.lower() < token1.lower():
            zero_for_one = True
        else:
            zero_for_one = False
            token0, token1 = token1, token0
        pool_key = (token0, token1, fee, tick_spacing, hooks)
        # [0]=The output quote [1]=estimated gas units used for the swap
        quote_amount: int = self.quoter.functions.quoteExactInputSingle(
            (pool_key, zero_for_one, qty, hook_data)
        ).call()[0]
        return quote_amount

    def get_quote_exact_input(
        self,
        token_exact: str,
        qty: int,
        route: List[PoolKey],
    ) -> int:
        """
        :param token_exact: The token for which the qty parameter is specified.
        :param qty: The amount of the token_exact to be swapped.
        :param route: The list of PoolKeys representing the path of the swap, starting with the pool containing the input token and ending with the pool containing the output token.
        :return: Quote for token to token multi-hop trades with an exact input.
        """
        encoded_route = self.encode_path_keys_input(route, token_exact)

        # [0]=The output quote [1]=estimated gas units used for the swap
        quote_amount: int = self.quoter.functions.quoteExactInput(
            (
                token_exact,
                [astuple(path_key) for path_key in encoded_route],
                qty,
            )
        ).call()[0]
        return quote_amount

    def get_quote_exact_output_single(
        self,
        token0: str,
        token1: str,
        qty: int,
        fee: int,
        tick_spacing: int,
        hooks: str = ZERO_HOOK,
        hook_data: bytes = b"",
    ) -> int:
        """
        :param token0: The token to be sold.
        :param token1: The token to be bought.
        :param qty: The amount of `token1` to be bought.
        :param fee: The fee tier for the swap.
        :param tick_spacing: The tick spacing for the swap.
        :param hooks: The hooks for the swap.
        :param hook_data: The hook data for the swap.
        :return: Quote for token to token single hop trades with an exact output.
        """
        if token0.lower() < token1.lower():
            zero_for_one = True
        else:
            zero_for_one = False
            token1, token0 = token0, token1

        pool_key = (
            token0,
            token1,
            fee,
            tick_spacing,
            hooks,
        )
        # [0]=The input quote [1]=estimated gas units used for the swap
        quote_amount: int = self.quoter.functions.quoteExactOutputSingle(
            (pool_key, zero_for_one, qty, hook_data)
        ).call()[0]
        return quote_amount

    def get_quote_exact_output(
        self,
        token_exact: str,
        qty: int,
        route: List[PoolKey],
    ) -> int:
        """
        :param token_exact: The token for which the qty parameter is specified, either the input or output token depending on the quote type.
        :param qty: The amount of the token_exact to be swapped. For an exact output quote, this is the amount of output token desired.
        :param route: The list of PoolKeys representing the path of the swap in reverse order, starting with the pool containing the output token and ending with the pool containing the input token.
        :return: Quote for token to token multi-hop trades with an exact output.
        """

        encoded_route = self.encode_path_keys_output(route, token_exact)
        quote_amount: int = self.quoter.functions.quoteExactOutput(
            (
                token_exact,
                [astuple(path_key) for path_key in encoded_route],
                qty,
            )
        ).call()[0]
        return quote_amount

    # Market price functions for selling `qty` amount of `token0` to buy `token1`
    def get_price_input(
        self,
        token0: str,
        token1: str,
        qty: int,
        fee: Optional[int] = None,
        tick_spacing: Optional[int] = None,
        hooks: Optional[str] = ZERO_HOOK,
        hook_data: Optional[bytes] = b"",
        route: Optional[List[PoolKey]] = None,
    ) -> int:
        """
        :param token0: The token to be sold.
        :param token1: The token to be bought.
        :param qty: The amount of `token0` to be sold.
        :param fee: Optional. The fee tier for the swap.

        :param tick_spacing: Optional. The tick spacing for the swap.
        :param hooks: Optional. The hooks for the swap.
        :param hook_data: Optional. The hook data for the swap.
        :param route: Optional. The route for the swap. The first element should be the pool containing `token0` and the last element should be the pool containing `token1`.
        :return: Returns the exact amount of `token1` that can be received for `qty` amount of `token0` at the current price.

        If `route` is provided, it will be used for the quote. Otherwise, `fee` and `tick_spacing` must be provided for a single hop quote.
        """
        result: int = 0
        if route is None:
            if fee is None or tick_spacing is None:
                raise ValueError(
                    "fee and tick_spacing parameters must be provided for single hop quotes"
                )
            result = self.get_quote_exact_input_single(
                token0,
                token1,
                qty,
                fee,
                tick_spacing,
                hooks,  # type: ignore[arg-type]
                hook_data,  # type: ignore[arg-type]
            )
        else:
            result = self.get_quote_exact_input(token0, qty, route)
        return result

    def get_price_output(
        self,
        token0: str,
        token1: str,
        qty: int,
        fee: Optional[int] = None,
        tick_spacing: Optional[int] = None,
        hooks: Optional[str] = ZERO_HOOK,
        hook_data: Optional[bytes] = b"",
        route: Optional[List[PoolKey]] = None,
    ) -> int:
        """
        :param token0: The token to be sold.
        :param token1: The token to be bought.
        :param qty: The amount of `token1` to be bought.
        :param fee: Optional. The fee tier for the swap.
        :param tick_spacing: Optional. The tick spacing for the swap.
        :param hooks: Optional. The hooks for the swap.
        :param hook_data: Optional. The hook data for the swap.
        :param route: Optional. The route for the swap in reverse order. The first element should be the pool containing `token1` and the last element should be the pool containing `token0`.
        :return: Returns the exact amount of `token0` required to buy `qty` amount of `token1` at the current price.

        If `route` is provided, it will be used for the quote. Otherwise, `fee` and `tick_spacing` must be provided for a single hop quote.
        """
        result: int = 0
        if route is None:
            if fee is None or tick_spacing is None or hooks is None:
                raise ValueError(
                    "fee, tick_spacing, and hooks parameters must be provided for single hop quotes"
                )
            result = self.get_quote_exact_output_single(
                token0,
                token1,
                qty,
                fee,
                tick_spacing,
                hooks,
                hook_data,  # type: ignore[arg-type]
            )
        else:
            result = self.get_quote_exact_output(token1, qty, route)
        return result

    # Swap functions
    def token_to_token_swap_exact_input(
        self,
        input_token: str,
        qty: int,
        qtycap: int,
        output_token: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        hook_data: bytes = b"",
        min_hop_price_x_36: int = 0,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        :param input_token: The token to be sold.
        :param qty: The amount of `input_token` to be sold.
        :param qtycap: The minimum amount of `output_token` that must be bought for the swap to succeed.
        :param output_token: The token to be bought.
        :param fee: The fee for the swap.
        :param tick_spacing: The tick spacing for the swap.
        :param hooks: The hooks for the swap.
        :param hook_data: The hook data for the swap.
        :param min_hop_price_x_36: Optional. The minimum price for each hop in the route, expressed as an integer.
        :param custom_nonce: Optional. The nonce to use for the transaction.

        Swaps an exact amount of `input_token` for a minimum amount of `output_token`,
        reverting if the amount of `output_token` received is less than `qtycap`.
        """
        min_tokens_bought: int = int((1 - self.max_slippage) * qtycap)

        ether_amount: int = 0
        if input_token == ETH_ADDRESS:
            ether_amount = qty

        # V4_SWAP // Encode swap commands and actions
        commands: bytes = encode_packed(
            ["uint8"],
            args=[universal_router_commands["V4_SWAP"]],
        )

        # Actions are SWAP_EXACT_IN_SINGLE, SETTLE_ALL, TAKE_ALL
        actions: bytes = encode_packed(
            ["uint8", "uint8", "uint8"],
            [
                v4_actions["SWAP_EXACT_IN_SINGLE"],
                v4_actions["SETTLE_ALL"],
                v4_actions["TAKE_ALL"],
            ],
        )

        # SETTING PARAMS
        if input_token.lower() < output_token.lower():
            zero_for_one = True
            token0, token1 = input_token, output_token
        else:
            zero_for_one = False
            token0, token1 = output_token, input_token
        exact_input_single_params: bytes = encode(
            v4_actions_abis["SWAP_EXACT_IN_SINGLE"],
            [
                (
                    (token0, token1, fee, tick_spacing, hooks),
                    zero_for_one,
                    qty,
                    min_tokens_bought,
                    min_hop_price_x_36,
                    hook_data,
                )
            ],
        )
        settle_all_params: bytes = encode(
            v4_actions_abis["SETTLE_ALL"],
            [input_token, qty],
        )
        take_all_params: bytes = encode(
            v4_actions_abis["TAKE_ALL"],
            [output_token, min_tokens_bought],
        )

        # ENCODING DATA
        params = [exact_input_single_params, settle_all_params, take_all_params]
        inputs = []
        inputs.append(
            encode(
                ["bytes", "bytes[]"],
                [actions, params],
            )
        )

        return self._build_and_send_tx(
            self.router.functions.execute(commands, inputs, self._deadline()),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )

    def token_to_token_swap_input(
        self,
        input_token: str,
        qty: int,
        qtycap: int,
        route: List[PoolKey],
        min_hop_price_x_36: List[int] = [],
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        :param input_token: The token to be sold.
        :param qty: The amount of `input_token` to be sold.
        :param qtycap: The minimum amount of `output_token` that must be bought for the swap to succeed.
        :param route: The list of PoolKeys representing the path of the swap. The first element should be the pool containing the `input_token` and the last element should be the pool containing the `output_token`.
        :param min_hop_price_x_36: Optional. A list of minimum prices for each hop in the route, expressed as a list of integers.
        :param custom_nonce: Optional. The nonce to use for the transaction.

        Swaps an exact amount of `input_token` for a minimum amount of `output_token` through a specified multi-hop route,
        reverting if the amount of `output_token` received is less than `qtycap`.
        """
        min_tokens_bought: int = int((1 - self.max_slippage) * qtycap)

        encoded_route = self.encode_path_keys_input(route, input_token)

        ether_amount: int = 0

        if input_token == ETH_ADDRESS:
            ether_amount = qty

        # V4_SWAP // Encode swap commands and actions
        commands: bytes = encode_packed(
            ["uint8"],
            args=[universal_router_commands["V4_SWAP"]],
        )

        # Actions are SWAP_EXACT_IN, SETTLE_ALL, TAKE_ALL
        actions: bytes = encode_packed(
            ["uint8", "uint8", "uint8"],
            [
                v4_actions["SWAP_EXACT_IN"],
                v4_actions["SETTLE_ALL"],
                v4_actions["TAKE_ALL"],
            ],
        )

        # SETTING PARAMS
        exact_input_params: bytes = encode(
            v4_actions_abis["SWAP_EXACT_IN"],
            [
                (
                    input_token,
                    [astuple(path_key) for path_key in encoded_route],
                    min_hop_price_x_36,
                    qty,
                    min_tokens_bought,
                )
            ],
        )
        settle_all_params: bytes = encode(
            v4_actions_abis["SETTLE_ALL"],
            [input_token, qty],
        )
        take_all_params: bytes = encode(
            v4_actions_abis["TAKE_ALL"],
            [
                _addr_to_str(encoded_route[-1].intermediate_currency),  # type: ignore[arg-type]
                min_tokens_bought,
            ],
        )

        # ENCODING DATA
        params = [exact_input_params, settle_all_params, take_all_params]
        inputs = []
        inputs.append(
            encode(
                ["bytes", "bytes[]"],
                [actions, params],
            )
        )

        return self._build_and_send_tx(
            self.router.functions.execute(commands, inputs, self._deadline()),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )

    def token_to_token_swap_exact_output(
        self,
        input_token: str,
        qty: int,
        qtycap: int,
        output_token: str,
        fee: int,
        tick_spacing: int,
        hooks: str,
        hook_data: bytes = b"",
        min_hop_price_x_36: int = 0,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        :param input_token: The token to be sold.
        :param qty: The amount of `output_token` to be bought.
        :param qtycap: The maximum amount of `input_token` that can be sold for the trade to proceed.
        :param output_token: The token to be bought.
        :param fee: The fee for the swap.
        :param tick_spacing: The tick spacing for the swap.
        :param hooks: The hooks for the swap.
        :param hook_data: The hook data for the swap.
        :param min_hop_price_x_36: Optional. The minimum price for each hop in the route, expressed as an integer.
        :param custom_nonce: Optional. The nonce for the transaction.
        """

        amount_in_max: int = int((1 + self.max_slippage) * qtycap)

        ether_amount: int = 0
        if input_token == ETH_ADDRESS:
            ether_amount = amount_in_max

        # V4_SWAP // Encode swap commands and actions
        commands: bytes = encode_packed(
            ["uint8"],
            args=[universal_router_commands["V4_SWAP"]],
        )

        # Actions are SWAP_EXACT_OUT_SINGLE, SETTLE_ALL, TAKE_ALL, TAKE
        actions: bytes = encode_packed(
            ["uint8", "uint8", "uint8", "uint8"],
            args=[
                v4_actions["SWAP_EXACT_OUT_SINGLE"],
                v4_actions["SETTLE_ALL"],
                v4_actions["TAKE_ALL"],
                v4_actions["TAKE"],
            ],
        )
        # SETTING PARAMS
        if input_token.lower() < output_token.lower():
            zero_for_one = True
            token0, token1 = input_token, output_token
        else:
            zero_for_one = False
            token0, token1 = output_token, input_token
        exact_output_single_params = encode(
            v4_actions_abis["SWAP_EXACT_OUT_SINGLE"],
            [
                (
                    (
                        token0,
                        token1,
                        fee,
                        tick_spacing,
                        hooks,
                    ),
                    zero_for_one,
                    qty,
                    amount_in_max,
                    min_hop_price_x_36,
                    hook_data,
                )
            ],
        )
        settle_all_params = encode(
            v4_actions_abis["SETTLE_ALL"],
            [input_token, amount_in_max],
        )
        take_all_params = encode(
            v4_actions_abis["TAKE_ALL"],
            [output_token, qty],
        )
        take_input_params = encode(
            v4_actions_abis["TAKE"], [input_token, _addr_to_str(self.address), 0]
        )

        # ENCODING DATA
        params = [
            exact_output_single_params,
            settle_all_params,
            take_all_params,
            take_input_params,
        ]
        inputs = []
        inputs.append(
            encode(
                ["bytes", "bytes[]"],
                [actions, params],
            )
        )

        return self._build_and_send_tx(
            self.router.functions.execute(commands, inputs, self._deadline()),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )

    def token_to_token_swap_output(
        self,
        output_token: str,
        qty: int,
        qtycap: int,
        route: List[PoolKey],
        min_hop_price_x_36: List[int] = [],
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        :param output_token: The token to be bought.
        :param qty: The amount of `output_token` to be bought.
        :param qtycap: The maximum amount of `input_token` that can be sold for the trade to proceed.
        :param route: The route for the swap in reverse order. The first element should be the pool containing `output_token` and the last element should be the pool containing `input_token`.
        :param min_hop_price_x_36: Optional. The minimum price for each hop in the route, expressed as a list of integers.
        :param custom_nonce: Optional. The nonce for the transaction.

        Swaps a maximum amount of `input_token` for an exact amount of `output_token` through a specified multi-hop route,
        reverting if the amount of `input_token` required is more than `qtycap`.
        """

        amount_in_max: int = int((1 + self.max_slippage) * qtycap)
        encoded_route = self.encode_path_keys_output(route, output_token)

        input_token: str = _addr_to_str(encoded_route[0].intermediate_currency)  # type: ignore[arg-type]

        ether_amount: int = 0
        if input_token == ETH_ADDRESS:
            ether_amount = amount_in_max

        # V4_SWAP // Encode swap commands and actions
        commands: bytes = encode_packed(
            ["uint8"],
            args=[universal_router_commands["V4_SWAP"]],
        )

        # Actions are SWAP_EXACT_OUT, SETTLE_ALL, TAKE_ALL, TAKE
        actions: bytes = encode_packed(
            ["uint8", "uint8", "uint8", "uint8"],
            args=[
                v4_actions["SWAP_EXACT_OUT"],
                v4_actions["SETTLE_ALL"],
                v4_actions["TAKE_ALL"],
                v4_actions["TAKE"],
            ],
        )
        # SETTING PARAMS
        exact_output_params: bytes = encode(
            v4_actions_abis["SWAP_EXACT_OUT"],
            [
                (
                    output_token,
                    [astuple(path_key) for path_key in encoded_route],
                    min_hop_price_x_36,
                    qty,
                    amount_in_max,
                )
            ],
        )
        settle_all_params: bytes = encode(
            v4_actions_abis["SETTLE_ALL"],
            [input_token, amount_in_max],
        )
        take_all_params: bytes = encode(
            v4_actions_abis["TAKE_ALL"],
            [output_token, qty],
        )
        take_input_params = encode(
            v4_actions_abis["TAKE"], [input_token, _addr_to_str(self.address), 0]
        )

        # ENCODING DATA
        params = [
            exact_output_params,
            settle_all_params,
            take_all_params,
            take_input_params,
        ]
        inputs = []
        inputs.append(
            encode(
                ["bytes", "bytes[]"],
                [actions, params],
            )
        )

        return self._build_and_send_tx(
            self.router.functions.execute(commands, inputs, self._deadline()),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )

    def drop_txn(
        self,
        address_to: AddressLike,
        gas_price: float,
        priority_fee: int = 10,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Replaces pending transaction with zero-value ETH transfer

        :param address_to: Zero address or any other valid address to which the zero-value transaction will be sent

        Params `gas_price` and `priority_fee` are Gas Price and Max Priority Fee respectively;
        MUST be at least 20% higher than values the original transaction has.
        """
        # This one is for legacy transactions
        transaction_dict_legacy = {
            "nonce": self.w3.eth.get_transaction_count(self.address)
            if custom_nonce is None
            else custom_nonce,
            "from": _addr_to_str(self.address),
            "to": Web3.to_checksum_address(address_to),
            "value": Web3.to_wei(0, "wei"),
            "gasPrice": Web3.to_wei(gas_price, "gwei"),
            "gas": int(self.gas_limit),
            "chainId": int(self.w3.eth.chain_id),
        }
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction_dict_legacy,
            self.private_key,
        )
        # This one is for post-Merge transactions
        transaction_dict = {
            "type": 2,
            "nonce": self.w3.eth.get_transaction_count(self.address)
            if custom_nonce is None
            else custom_nonce,
            "from": _addr_to_str(self.address),
            "to": _addr_to_str(address_to),
            "value": Web3.to_wei(0, "wei"),
            "maxFeePerGas": Web3.to_wei(int(gas_price), "gwei"),
            "maxPriorityFeePerGas": Web3.to_wei(priority_fee, "gwei"),
            "gas": int(self.gas_limit),
            "chainId": int(self.w3.eth.chain_id),
        }
        signed_txn_london = self.w3.eth.account.sign_transaction(
            transaction_dict,
            self.private_key,
        )
        if self.post_merge:
            return self.w3.eth.send_raw_transaction(signed_txn_london.rawTransaction)
        else:
            return self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    # Market functions for swapping `qty` amount of `token0` to buy `token1`
    def make_swap_input(
        self,
        input_token: str,
        output_token: str,
        qty: int,
        qtycap: int,
        swap_pool_key: Optional[PoolKey] = None,
        hook_data: Optional[bytes] = b"",
        route: Optional[List[PoolKey]] = None,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        :param input_token: The token to be sold.
        :param output_token: The token to be bought.
        :param qty: The amount of `input_token` to be sold.
        :param qtycap: The minimum amount of `output_token` that must be bought for the trade to proceed.
        :param swap_pool_key: Optional. The PoolKey for the swap, required if `route` is not provided.
        :param hook_data: Optional. The hook data for the swap. This is only used for single hop swaps and will be ignored if `route` is provided.
        :param route: Optional. The route for the swap. The first element should be the pool containing `input_token` and the last element should be the pool containing `output_token`. If `route` is provided, it will be used for the swap instead of `swap_pool_key`.
        :param custom_nonce: Optional. The nonce for the transaction.

        Make a trade by defining the qty of the input token.
         If `route` is provided, it will be used for the swap. Otherwise, `swap_pool_key` must be provided for a single hop swap."""
        result: Optional[HexBytes] = None
        if route is None:
            if swap_pool_key is None:
                raise ValueError("swap_pool_key must be provided for single hop swaps")
            result = self.token_to_token_swap_exact_input(
                input_token,
                qty,
                qtycap,
                output_token,
                swap_pool_key.fee,
                swap_pool_key.tick_spacing,
                swap_pool_key.hooks,
                hook_data,  # type: ignore[arg-type]
                min_hop_price_x_36=0,
                custom_nonce=custom_nonce,
            )
        else:
            result = self.token_to_token_swap_input(
                input_token,
                qty,
                qtycap,
                route,
                min_hop_price_x_36=[],
                custom_nonce=custom_nonce,
            )
        return result

    def make_swap_output(
        self,
        input_token: str,
        output_token: str,
        qty: int,
        qtycap: int,
        swap_pool_key: Optional[PoolKey] = None,
        hook_data: Optional[bytes] = b"",
        route: Optional[List[PoolKey]] = None,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        :param input_token: The token to be sold.
        :param output_token: The token to be bought.
        :param qty: The amount of `output_token` to be bought.
        :param qtycap: The maximum amount of `input_token` that can be sold for the trade to proceed.
        :param swap_pool_key: Optional. The PoolKey for the swap, required if `route` is not provided.
        :param hook_data: Optional. The hook data for the swap.
        :param route: Optional. The route for the swap in reverse order. The first element should be the pool containing `output_token` and the last element should be the pool containing `input_token`.

        Make a trade by defining the qty of the output token.
        If `route` is provided, it will be used for the swap. Otherwise, `swap_pool_key` must be provided for a single hop swap.
        """
        result: Optional[HexBytes] = None
        if route is None:
            if swap_pool_key is None:
                raise ValueError("swap_pool_key must be provided for single hop swaps")
            result = self.token_to_token_swap_exact_output(
                input_token,
                qty,
                qtycap,
                output_token,
                swap_pool_key.fee,
                swap_pool_key.tick_spacing,
                swap_pool_key.hooks,
                hook_data,  # type: ignore[arg-type]
                min_hop_price_x_36=0,
                custom_nonce=custom_nonce,
            )
        else:
            result = self.token_to_token_swap_output(
                output_token,
                qty,
                qtycap,
                route,
                min_hop_price_x_36=[],
                custom_nonce=custom_nonce,
            )
        return result

    # Liquidity management functions
    def get_position_info(self, token_id: int) -> Dict:
        """
                Get information about a liquidity position given its token ID.
                :return: A dictionary with the following keys:

        - currency0: The address of the first token in the pool
        - currency1: The address of the second token in the pool
        - fee: The fee tier of the pool
        - tickSpacing: The tick spacing of the pool
        - hooks: The hooks address of the pool
        - poolID: The truncated pool ID of the position, which is the first 25 bytes of the full pool ID
        - tickLower: The lower tick of the position
        - tickUpper: The upper tick of the position
        - hasSubscriber: A boolean indicating whether the position has a subscriber
        - owner: The address of the owner of the position
        """
        position_info = self.position_manager_get_pool_and_position_info(token_id)

        pool_key: PoolKey = position_info["poolKey"]
        pool_info = position_info["info"]
        pool_info_decoded = self.decode_position_info(pool_info)
        owner_of = self.position_manager_get_owner_of(token_id)
        return_value: Dict = {
            "currency0": pool_key.currency0,
            "currency1": pool_key.currency1,
            "fee": pool_key.fee,
            "tickSpacing": pool_key.tick_spacing,
            "hooks": pool_key.hooks,
            "poolID": pool_info_decoded["poolID"],
            "tickLower": pool_info_decoded["tickLower"],
            "tickUpper": pool_info_decoded["tickUpper"],
            "hasSubscriber": pool_info_decoded["hasSubscriber"],
            "owner": owner_of,
        }
        return return_value

    def get_position_value(
        self, token_id: int, token0_decimals: int, token1_decimals: int
    ) -> Dict:
        """
        Get the value of a liquidity position given its token ID.
        """
        liquidity: int = self.position_manager_get_position_liquidity(token_id)
        position_info = self.get_position_info(token_id)
        slot0 = self.stateview_get_slot0(
            position_info["currency0"],
            position_info["currency1"],
            position_info["fee"],
            position_info["tickSpacing"],
            position_info["hooks"],
        )
        # price: Decimal = Decimal(
        #     Decimal(
        #         decode_sqrt_ratioX96(
        #             slot0["sqrtPriceX96"],
        #         )
        #     )
        #     / Decimal(10 ** (token1_decimals - token0_decimals))
        # )
        sqrt_price = int(slot0["sqrtPriceX96"])
        raw_price: Decimal = (sqrt_price / Decimal(Q96)) ** 2
        decimal_factor: Decimal = 10**token1_decimals / Decimal(10**token0_decimals)
        price: Decimal = raw_price / decimal_factor
        amounts = self.get_amounts_for_liquidity_by_ticks(
            slot0["sqrtPriceX96"],
            position_info["tickLower"],
            position_info["tickUpper"],
            liquidity,
        )
        amount0: Decimal = Decimal(amounts["amount0"]) / Decimal(10**token0_decimals)
        amount1: Decimal = Decimal(amounts["amount1"]) / Decimal(10**token1_decimals)
        return_value: Dict = {
            "amount0": amounts["amount0"],
            "amount1": amounts["amount1"],
            # NOTE: unclaimed fees are not yet computed; total values equal principal only
            "unclaimed_fees0": 0,
            "unclaimed_fees1": 0,
            "total_amount0": amounts["amount0"],
            "total_amount1": amounts["amount1"],
            "value_in_token0": amount0 + amount1 / price,
            "value_in_token1": amount1 + amount0 * price,
        }
        return return_value

    def create_pool(
        self,
        pool_key: PoolKey,
        sqrt_price_x96: int,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Creates a new liquidity pool without initial liquidity with the specified parameters and a starting price.
        """
        function = self.position_manager.functions.initializePool(
            astuple(pool_key),
            sqrt_price_x96,
        )
        tx = self._build_and_send_tx(
            function,
            self._get_tx_params(custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )
        return tx

    def mint_position(
        self,
        pool_key: PoolKey,
        tick_lower: int,
        tick_upper: int,
        liquidity: int,
        amount0: int,
        amount1: int,
        recipient: Optional[str] = None,
        hook_data: Optional[bytes] = b"",
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Mints a new liquidity position with the specified parameters.

        :param pool_key: The parameters of the pool for which the position is being minted.
        :param tick_lower: The lower tick of the position.
        :param tick_upper: The upper tick of the position.
        :param liquidity: The amount of liquidity to mint.
        :param amount0: The amount of token0 to provide as liquidity.
        :param amount1: The amount of token1 to provide as liquidity.
        :param recipient: The address that will receive excessive ETH amounts. If None, it defaults to the caller's address.
        :param hook_data: Optional bytes that can be passed to the hooks during the minting.
        :return: The transaction hash of the minting transaction.
        """

        ether_amount: int = 0
        if recipient is None:
            recipient = _addr_to_str(self.address)
        # Encoding actions: MINT_POSITION, SETTLE_PAIR, SWEEP, SWEEP
        if pool_key.currency0 == ETH_ADDRESS:
            ether_amount = amount0
        actions: bytes = encode_packed(
            ["uint8", "uint8", "uint8", "uint8"],
            [
                v4_actions["MINT_POSITION"],
                v4_actions["SETTLE_PAIR"],
                v4_actions["SWEEP"],
                v4_actions["SWEEP"],
            ],
        )

        # Encoding params
        mint_position_params: bytes = encode(
            [
                "(address,address,uint24,int24,address)",
                "int24",
                "int24",
                "uint256",
                "uint128",
                "uint128",
                "address",
                "bytes",
            ],
            [
                astuple(pool_key),
                tick_lower,
                tick_upper,
                liquidity,
                amount0,
                amount1,
                recipient,
                hook_data,
            ],
        )
        settle_pair_params: bytes = encode(
            ["address", "address"],
            [pool_key.currency0, pool_key.currency1],
        )
        sweep0_params: bytes = encode(
            v4_actions_abis["SWEEP"],
            [pool_key.currency0, recipient],
        )
        sweep1_params: bytes = encode(
            v4_actions_abis["SWEEP"],
            [pool_key.currency1, recipient],
        )
        params: List[bytes] = [
            mint_position_params,
            settle_pair_params,
            sweep0_params,
            sweep1_params,
        ]

        # Encoding unlock data
        unlock_data: bytes = encode(
            ["bytes", "bytes[]"],
            [actions, params],
        )

        tx: HexBytes = self._build_and_send_tx(
            self.position_manager.functions.modifyLiquidities(
                unlock_data, self._deadline()
            ),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )
        return tx

    def increase_liquidity(
        self,
        pool_key: PoolKey,
        token_id: int,
        amount0_max: int,
        amount1_max: int,
        liquidity: int,
        recipient: Optional[str] = None,
        hook_data: Optional[bytes] = b"",
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Increases the liquidity of an existing position.

        :param pool_key: The parameters of the pool for which the position is being increased.
        :param token_id: The token ID of the position to increase liquidity for.
        :param amount0_max: The maximum amount of token0 to provide as liquidity.
        :param amount1_max: The maximum amount of token1 to provide as liquidity.
        :param liquidity: The amount of liquidity to add to the position.
        :param recipient: The address that will receive excessive ETH amounts. If None, it defaults to the caller's address.
        :param hook_data: Optional bytes that can be passed to the hooks during the liquidity increase.
        :return: The transaction hash of the liquidity increase transaction.
        """

        ether_amount: int = 0
        if recipient is None:
            recipient = _addr_to_str(self.address)
        # Encoding actions: INCREASE_LIQUIDITY, SETTLE_PAIR, SWEEP, SWEEP
        if pool_key.currency0 == ETH_ADDRESS:
            ether_amount = amount0_max

        actions = encode_packed(
            ["uint8", "uint8", "uint8", "uint8"],
            [
                v4_actions["INCREASE_LIQUIDITY"],
                v4_actions["SETTLE_PAIR"],
                v4_actions["SWEEP"],
                v4_actions["SWEEP"],
            ],
        )
        # Encoding params
        increase_liquidity_params: bytes = encode(
            ["uint256", "uint256", "uint128", "uint128", "bytes"],
            [
                token_id,
                liquidity,
                amount0_max,
                amount1_max,
                hook_data,
            ],
        )
        settle_pair_params: bytes = encode(
            ["address", "address"],
            [pool_key.currency0, pool_key.currency1],
        )
        sweep0_params: bytes = encode(
            v4_actions_abis["SWEEP"],
            [pool_key.currency0, recipient],
        )
        sweep1_params: bytes = encode(
            v4_actions_abis["SWEEP"],
            [pool_key.currency1, recipient],
        )
        params: List[bytes] = [
            increase_liquidity_params,
            settle_pair_params,
            sweep0_params,
            sweep1_params,
        ]

        # Encoding unlock data
        unlock_data: bytes = encode(
            ["bytes", "bytes[]"],
            [actions, params],
        )

        tx: HexBytes = self._build_and_send_tx(
            self.position_manager.functions.modifyLiquidities(
                unlock_data, self._deadline()
            ),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )
        return tx

    def decrease_liquidity(
        self,
        pool_key: PoolKey,
        token_id: int,
        amount0_min: int,
        amount1_min: int,
        liquidity: int,
        recipient: Optional[str] = None,
        hook_data: Optional[bytes] = b"",
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Decreases the liquidity of an existing position.

        :param pool_key: The parameters of the pool for which the position is being decreased.
        :param token_id: The token ID of the position to decrease liquidity for.
        :param amount0_min: The minimum amount of token0 to receive from the liquidity decrease.
        :param amount1_min: The minimum amount of token1 to receive from the liquidity decrease.
        :param liquidity: The amount of liquidity to remove from the position.
        :param recipient: The address that will receive the withdrawn liquidity. If None, it defaults to the caller's address.
        :param hook_data: Optional bytes that can be passed to the hooks during the liquidity decrease.
        :return: The transaction hash of the liquidity decrease transaction.
        """
        ether_amount: int = 0
        if recipient is None:
            recipient = _addr_to_str(self.address)
        # Encoding actions: DECREASE_LIQUIDITY, TAKE_PAIR
        actions = encode_packed(
            ["uint8", "uint8"],
            [
                v4_actions["DECREASE_LIQUIDITY"],
                v4_actions["TAKE_PAIR"],
            ],
        )
        # Encoding params
        decrease_liquidity_params: bytes = encode(
            ["uint256", "uint256", "uint128", "uint128", "bytes"],
            [
                token_id,
                liquidity,
                amount0_min,
                amount1_min,
                hook_data,
            ],
        )
        take_pair_params: bytes = encode(
            ["address", "address", "address"],
            [pool_key.currency0, pool_key.currency1, recipient],
        )
        params: List[bytes] = [decrease_liquidity_params, take_pair_params]

        # Encoding unlock data
        unlock_data: bytes = encode(
            ["bytes", "bytes[]"],
            [actions, params],
        )

        tx: HexBytes = self._build_and_send_tx(
            self.position_manager.functions.modifyLiquidities(
                unlock_data, self._deadline()
            ),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )
        return tx

    def collect_fees(
        self,
        pool_key: PoolKey,
        token_id: int,
        recipient: Optional[str] = None,
        hook_data: Optional[bytes] = b"",
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Collects the fees accrued by an existing position.

        :param pool_key: The parameters of the pool for which the position is collecting fees.
        :param token_id: The token ID of the position for which to collect fees.
        :param recipient: The address that will receive the collected fees. If None, it defaults to the caller's address.
        :param hook_data: Optional bytes that can be passed to the hooks during the fee collection.
        :return: The transaction hash of the fee collection transaction.
        """
        ether_amount: int = 0
        if recipient is None:
            recipient = _addr_to_str(self.address)
        # Encoding actions: DECREASE_LIQUIDITY, TAKE_PAIR
        actions = encode_packed(
            ["uint8", "uint8"],
            [
                v4_actions["DECREASE_LIQUIDITY"],
                v4_actions["TAKE_PAIR"],
            ],
        )
        # Encoding params
        decrease_liquidity_params: bytes = encode(
            ["uint256", "uint256", "uint128", "uint128", "bytes"],
            [
                token_id,
                0,
                0,
                0,
                hook_data,
            ],
        )
        take_pair_params: bytes = encode(
            ["address", "address", "address"],
            [pool_key.currency0, pool_key.currency1, recipient],
        )
        params: List[bytes] = [decrease_liquidity_params, take_pair_params]

        # Encoding unlock data
        unlock_data: bytes = encode(
            ["bytes", "bytes[]"],
            [actions, params],
        )

        tx: HexBytes = self._build_and_send_tx(
            self.position_manager.functions.modifyLiquidities(
                unlock_data, self._deadline()
            ),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )
        return tx

    def burn_position(
        self,
        pool_key: PoolKey,
        token_id: int,
        amount0_min: int,
        amount1_min: int,
        recipient: Optional[str] = None,
        hook_data: Optional[bytes] = b"",
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Burns an existing liquidity position.

        :param pool_key: The parameters of the pool for which the position is being burned.
        :param token_id: The token ID of the position to burn.
        :param amount0_min: The minimum amount of token0 to receive from burning the position.
        :param amount1_min: The minimum amount of token1 to receive from burning the position.
        :param recipient: The address that will receive the withdrawn liquidity. If None, it defaults to the caller's address.
        :param hook_data: Optional bytes that can be passed to the hooks during the position burn.
        :return: The transaction hash of the position burn transaction.
        """
        ether_amount: int = 0
        if recipient is None:
            recipient = _addr_to_str(self.address)
        # Encoding actions: BURN_POSITION, TAKE_PAIR
        actions = encode_packed(
            ["uint8", "uint8"],
            [
                v4_actions["BURN_POSITION"],
                v4_actions["TAKE_PAIR"],
            ],
        )
        # Encoding params
        burn_position_params: bytes = encode(
            ["uint256", "uint128", "uint128", "bytes"],
            [
                token_id,
                amount0_min,
                amount1_min,
                hook_data,
            ],
        )
        take_pair_params: bytes = encode(
            ["address", "address", "address"],
            [pool_key.currency0, pool_key.currency1, recipient],
        )
        params: List[bytes] = [burn_position_params, take_pair_params]

        # Encoding unlock data
        unlock_data: bytes = encode(
            ["bytes", "bytes[]"],
            [actions, params],
        )

        tx: HexBytes = self._build_and_send_tx(
            self.position_manager.functions.modifyLiquidities(
                unlock_data, self._deadline()
            ),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )
        return tx

    def universal_router_execute(
        self,
        commands: List[int],
        actions: List[List[int]],
        params: List[List[List]],
        ether_amount: int = 0,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """
        Executes a transaction with the Universal Router with the specified commands, actions, and parameters.

        :param commands: A list of command integers corresponding to the commands to execute.
        :param actions: A list of lists of action integers, where each sublist corresponds to the actions for the respective command in the `commands` list.
        :param params: A list of lists of lists of parameters, where each sublist corresponds to the parameters for the respective actions in the `actions` list. The structure of the parameters should match the expected input for each action as defined in the Universal Router documentation.
        :param ether_amount: The amount of ether to send with the transaction, if any.
        :param custom_nonce: Optional. The nonce for the transaction.

        See ``tests/test_uniswap4.py`` for an example which uses this, `test_universal_router_execute_multiaction()` specific test.

        NOTE: This function does not perform checks on the validity of the commands ``SWAP_EXACT_IN*`` and ``SWAP_EXACT_OUT*``. It is the caller's responsibility to ensure that they are correct and will not cause the transaction to revert.
        """
        # Validating input parameters
        ignore_list = [
            "SWAP_EXACT_IN_SINGLE",
            "SWAP_EXACT_IN",
            "SWAP_EXACT_OUT_SINGLE",
            "SWAP_EXACT_OUT",
        ]
        if len(commands) != len(actions) or len(actions) != len(params):
            raise ValueError("Lists' lengths are not equal.")
        for commands_item, actions_item, params_item in zip(commands, actions, params):
            command_key: str = self._get_dict_key_by_value(
                universal_router_commands, commands_item
            )
            if len(actions_item) == 0:
                if len(universal_router_commands_abis[command_key]) != sum(
                    len(sub_list) for sub_list in params_item
                ):
                    raise ValueError("ABI mismatch for " + command_key + " command.")
            else:
                for specific_action, specific_param in zip(actions_item, params_item):
                    action_key: str = self._get_dict_key_by_value(
                        v4_actions, specific_action
                    )
                    if action_key in ignore_list:
                        continue
                    if len(v4_actions_abis[action_key]) != len(specific_param):
                        raise ValueError(
                            "ABI mismatch for "
                            + action_key
                            + " command in "
                            + command_key
                            + " command."
                        )

        # Encoding data
        commands_abi = ["uint8"] * len(commands)
        encoded_commands: bytes = encode_packed(commands_abi, commands)
        encoded_inputs: List[bytes] = []
        for commands_item, actions_item, params_item in zip(commands, actions, params):
            command_key = self._get_dict_key_by_value(
                universal_router_commands, commands_item
            )
            if len(actions_item) == 0:
                encoded_params: bytes = encode(
                    universal_router_commands_abis[command_key], params_item[0]
                )
                encoded_inputs.append(encoded_params)
            else:
                encoded_actions_with_params = self.encode_actions_with_params(
                    actions_item, params_item
                )
                encoded_params = encode(
                    universal_router_commands_abis[command_key],
                    [
                        encoded_actions_with_params["actions"],
                        encoded_actions_with_params["params"],
                    ],
                )
                encoded_inputs.append(encoded_params)
        # Execute contract call
        result: HexBytes = self._build_and_send_tx(
            self.router.functions.execute(
                encoded_commands, encoded_inputs, self._deadline()
            ),
            self._get_tx_params(value=ether_amount, custom_nonce=custom_nonce),
            custom_nonce=custom_nonce,
        )

        return result

    # Helper functions
    def encode_actions_with_params(
        self, actions: List[int], params: List[List]
    ) -> Dict:
        encoded_actions_abi = ["uint8"] * len(actions)
        encoded_actions: bytes = encode_packed(encoded_actions_abi, actions)
        encoded_params: List[bytes] = []
        for actions_item, params_item in zip(actions, params):
            action_key = self._get_dict_key_by_value(v4_actions, actions_item)
            encoded_params_item: bytes = encode(
                v4_actions_abis[action_key], params_item
            )
            encoded_params.append(encoded_params_item)
        return_value: Dict = {
            "actions": encoded_actions,
            "params": encoded_params,
        }
        return return_value

    @staticmethod
    def _get_dict_key_by_value(param_dict: Dict, value: int) -> str:
        return_value = next((k for k, v in param_dict.items() if v == value), None)
        if return_value is None:
            raise IndexError("Key is not found.")
        return str(return_value)

    @staticmethod
    def get_liquidity_for_amount0(
        sqrt_ratio_a_x96: int, sqrt_ratio_b_x96: int, amount0: int
    ) -> int:
        """
        Helper function to calculate the amount of liquidity that can be provided for a given amount of `token0` and price range defined by `sqrt_  ratio_a_x96` and `sqrt_ratio_b_x96`.
        """
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        liquidity: int = (amount0 * (sqrt_ratio_a_x96 * sqrt_ratio_b_x96 // Q96)) // (
            sqrt_ratio_b_x96 - sqrt_ratio_a_x96
        )
        return liquidity

    @staticmethod
    def get_liquidity_for_amount1(
        sqrt_ratio_a_x96: int, sqrt_ratio_b_x96: int, amount1: int
    ) -> int:
        """
        Helper function to calculate the amount of liquidity that can be provided for a given amount of `token1` and price range defined by `sqrt_ratio_a_x96` and `sqrt_ratio_b_x96`.
        """
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        liquidity: int = (amount1 * Q96) // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
        return liquidity

    def get_liquidity_for_amounts(
        self,
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        sqrt_ratio_current_x96: int,
        amount0: int,
        amount1: int,
    ) -> int:
        """
        Helper function to calculate the amount of liquidity that can be provided for given amounts of `token0` and `token1` and price range defined by `sqrt_ratio_a_x96` and `sqrt_ratio_b_x96`.
        """
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        if sqrt_ratio_current_x96 <= sqrt_ratio_a_x96:
            liquidity: int = self.get_liquidity_for_amount0(
                sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount0
            )
        elif sqrt_ratio_current_x96 < sqrt_ratio_b_x96:
            liquidity0: int = self.get_liquidity_for_amount0(
                sqrt_ratio_current_x96, sqrt_ratio_b_x96, amount0
            )
            liquidity1: int = self.get_liquidity_for_amount1(
                sqrt_ratio_a_x96, sqrt_ratio_current_x96, amount1
            )
            liquidity = min(liquidity0, liquidity1)
        else:
            liquidity = self.get_liquidity_for_amount1(
                sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount1
            )
        return liquidity

    @staticmethod
    def get_amount0_for_liquidity(
        sqrt_ratio_a_x96: int, sqrt_ratio_b_x96: int, liquidity: int
    ) -> int:
        """
        Helper function to calculate the amount of `token0` that can be provided for a given amount of liquidity and price range defined by `sqrt_ratio_a_x96` and `sqrt_ratio_b_x96`.
        """
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        amount0: int = (
            (liquidity * Q96 * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96))
            // sqrt_ratio_b_x96
            // sqrt_ratio_a_x96
        )
        return amount0

    @staticmethod
    def get_amount1_for_liquidity(
        sqrt_ratio_a_x96: int, sqrt_ratio_b_x96: int, liquidity: int
    ) -> int:
        """
        Helper function to calculate the amount of `token1` that can be provided for a given amount of liquidity and price range defined by `sqrt_ratio_a_x96` and `sqrt_ratio_b_x96`.
        """
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        amount1: int = (liquidity * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)) // Q96
        return amount1

    def get_amounts_for_liquidity(
        self,
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        sqrt_ratio_current_x96: int,
        liquidity: int,
    ) -> Dict:
        """
        Helper function to calculate the amounts of `token0` and `token1` that can be provided for a given amount of liquidity and price range defined by `sqrt_ratio_a_x96` and `sqrt_ratio_b_x96`.
        """
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

        amount0: int = 0
        amount1: int = 0
        if sqrt_ratio_current_x96 <= sqrt_ratio_a_x96:
            amount0 = self.get_amount0_for_liquidity(
                sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity
            )
        elif sqrt_ratio_current_x96 < sqrt_ratio_b_x96:
            amount0 = self.get_amount0_for_liquidity(
                sqrt_ratio_current_x96, sqrt_ratio_b_x96, liquidity
            )
            amount1 = self.get_amount1_for_liquidity(
                sqrt_ratio_a_x96, sqrt_ratio_current_x96, liquidity
            )
        else:
            amount1 = self.get_amount1_for_liquidity(
                sqrt_ratio_a_x96, sqrt_ratio_b_x96, liquidity
            )
        return_value: Dict = {
            "amount0": amount0,
            "amount1": amount1,
        }
        return return_value

    def get_amounts_for_liquidity_by_ticks(
        self, ratio_current_x96: int, tick_lower: int, tick_upper: int, liquidity: int
    ) -> Dict:
        sqrt_ratio_a_x96 = get_sqrt_ratio_at_tick(tick_lower)
        sqrt_ratio_b_x96 = get_sqrt_ratio_at_tick(tick_upper)
        return_value: Dict = self.get_amounts_for_liquidity(
            sqrt_ratio_a_x96, sqrt_ratio_b_x96, ratio_current_x96, liquidity
        )
        return return_value

    def get_liquidity_for_amounts_by_ticks(
        self,
        ratio_current_x96: int,
        tick_lower: int,
        tick_upper: int,
        amount0: int,
        amount1: int,
    ) -> int:
        sqrt_ratio_a_x96 = get_sqrt_ratio_at_tick(tick_lower)
        sqrt_ratio_b_x96 = get_sqrt_ratio_at_tick(tick_upper)
        liquidity = self.get_liquidity_for_amounts(
            sqrt_ratio_a_x96, sqrt_ratio_b_x96, ratio_current_x96, amount0, amount1
        )
        return liquidity

    def get_minted_token_id(self, tx_hash: str) -> List[int]:
        """
        Helper function to extract the token ID of a newly minted position from the transaction receipt of the minting transaction.

        :return: A list of token IDs of the newly minted positions; empty list if none can be extracted. In most cases, this list will contain only one token ID, but in some cases (e.g., if multiple positions are minted in a single transaction), it may contain multiple token IDs.
        """
        transaction_receipt = self.w3.eth.get_transaction_receipt(tx_hash)  # type: ignore [arg-type]
        logs = self.position_manager.events.Transfer().process_receipt(
            transaction_receipt
        )
        return_value: List[int] = []
        for log in logs:
            try:
                if _addr_to_str(log.args["from"]) == ZERO_HOOK:
                    minted_token_id: int = log.args.id
                    return_value.append(minted_token_id)
            except (AttributeError, KeyError):
                logger.warning(
                    "Could not extract minted token ID from transaction receipt for transaction hash: %s.",
                    tx_hash,
                )
        return return_value

    @staticmethod
    def decode_position_info(position_info: int) -> Dict:
        """

                :return:
        A dictionary with the following keys:
        - `tickLower`: The lower tick of the position.
        - `tickUpper`: The upper tick of the position.
        - `poolID`: The truncated pool ID of the position, which is the first 25 bytes of the full pool ID.
        - `hasSubscriber`: A boolean indicating whether the position has a subscriber.
        """
        tick_lower_offset = 8
        tick_upper_offset = 32
        pool_id_offset = 56
        sign_bit = 0x800000

        # The hasSubscriber flag is stored in the least significant byte of the position info, so we can use a bitwise AND operation with a mask of 0xFF to extract it.
        mask = 0xFF
        has_subscriber: bool = (position_info & mask) != 0

        # The tick lower and tick upper values are stored in the next 3 bytes each, so we shift the position info to the right by the respective offsets and use a bitwise AND operation with a mask of 0xFFFFFF to extract them. We also check if the sign bit is set to determine if the tick values are negative, and if so, we subtract 0x1000000 from them to get the correct negative value.
        mask = 0xFFFFFF
        tick_lower: int = (position_info >> tick_lower_offset) & mask
        if tick_lower & sign_bit:
            tick_lower = tick_lower - 0x1000000

        tick_upper: int = (position_info >> tick_upper_offset) & mask
        if tick_upper & sign_bit:
            tick_upper = tick_upper - 0x1000000

        # The pool ID is stored in the remaining bytes, so we shift the position info to the right by the pool ID offset to get the pool ID.
        rest_part: int = position_info >> pool_id_offset
        pool_id: bytes = rest_part.to_bytes(25, byteorder="big")

        return_value: Dict = {
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "poolID": pool_id,
            "hasSubscriber": has_subscriber,
        }
        return return_value

    @staticmethod
    def encode_path_keys_input(
        path: List[PoolKey],
        currency_in: str,
        hook_data_list: Optional[List[bytes]] = None,
    ) -> List[PathKey]:
        """
        Encodes a list of PoolKeys into the format expected by the quoter for multi-hop ExactInput quotes.
        """
        encoded_path: List[PathKey] = []
        if hook_data_list is None:
            hook_data_list = [b""] * len(path)
        else:
            if len(hook_data_list) != len(path):
                raise ValueError("Length of hook_data_list must match length of path")
        for pool_key, hook_data in zip(path, hook_data_list):
            currency_out: str = (
                pool_key.currency1
                if currency_in.lower() == pool_key.currency0.lower()
                else pool_key.currency0
            )
            path_key: PathKey = PathKey(
                currency_out,
                pool_key.fee,
                pool_key.tick_spacing,
                pool_key.hooks,
                hook_data,
            )
            encoded_path.append(path_key)
            currency_in = currency_out
        return encoded_path

    @staticmethod
    def encode_path_keys_output(
        path: List[PoolKey],
        currency_out: str,
        hook_data_list: Optional[List[bytes]] = None,
    ) -> List[PathKey]:
        """
        Encodes a list of PoolKeys into the format expected by the quoter for multi-hop ExactOutput quotes.

        """
        encoded_path: List[PathKey] = []
        if hook_data_list is None:
            hook_data_list = [b""] * len(path)
        else:
            if len(hook_data_list) != len(path):
                raise ValueError("Length of hook_data_list must match length of path")
        for pool_key, hook_data in zip(reversed(path), reversed(hook_data_list)):
            currency_in: str = (
                pool_key.currency1
                if currency_out.lower() == pool_key.currency0.lower()
                else pool_key.currency0
            )
            path_key: PathKey = PathKey(
                currency_in,
                pool_key.fee,
                pool_key.tick_spacing,
                pool_key.hooks,
                hook_data,
            )
            encoded_path.insert(0, path_key)
            currency_out = currency_in
        return encoded_path

    @staticmethod
    def get_pool_id(pool: PoolKey) -> HexBytes:
        """Computes the pool ID for a given PoolKey by hashing its parameters."""
        pool_data = eth_abi.abi.encode(
            types=["address", "address", "uint24", "int24", "address"],
            args=[
                pool.currency0,
                pool.currency1,
                pool.fee,
                pool.tick_spacing,
                pool.hooks,
            ],
        )
        pool_id = Web3.keccak(pool_data)
        return pool_id

    def get_token(self, address: AddressLike, abi_name: str = "erc20") -> ERC20Token:
        """
        Retrieves metadata from the ERC20 contract of a given token, like its name, symbol, and decimals.
        """
        if address == ETH_ADDRESS or address == _str_to_addr(ETH_ADDRESS):
            return ERC20Token(
                address=address,
                name="ETH",
                symbol="ETH",
                decimals=18,
            )
        token_contract = _load_contract(self.w3, abi_name, address=address)
        try:
            _name = token_contract.functions.name().call()
            _symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
        except Exception:
            raise InvalidToken(address)
        try:
            name = _name.decode()
        except Exception:
            name = str(_name)
        try:
            symbol = _symbol.decode()
        except Exception as e:
            logger.warning(
                "Error occurred while decoding symbol for %s: %s",
                _addr_to_str(address),
                e,
            )
            symbol = str(_symbol)
        return ERC20Token(symbol, address, name, decimals)

    def get_token_balance(self, erc20: AddressLike) -> Decimal:
        """Get the balance of an ERC20 token for your address."""
        contract = _load_contract(self.w3, abi_name="erc20", address=erc20)
        decimals: int = contract.functions.decimals().call()
        balance: int = contract.functions.balanceOf(self.address).call()
        return_balance: Decimal = Decimal(balance) / Decimal(10**decimals)
        return return_balance

    def get_balance(self) -> Decimal:
        """Get the balance of ETH for your address."""
        balance: int = self.w3.eth.get_balance(self.address)
        return_balance: Decimal = Decimal(balance) / Decimal(10**18)
        return return_balance

    def load_contract_with_abi(self, abi_name: str, address: AddressLike) -> Contract:
        return self.w3.eth.contract(address=address, abi=_load_abi(abi_name))

    def erc20_contract(self, token_addr: AddressLike) -> Contract:
        return self.load_contract_with_abi(abi_name="erc20", address=token_addr)

    def _deadline(self) -> int:
        """Get a predefined deadline. 10min by default."""
        return int(time.time()) + 10 * 60

    def _get_tx_params(
        self, value: int = 0, custom_nonce: Optional[Nonce] = None
    ) -> TxParams:
        """Get generic transaction parameters."""
        if custom_nonce is not None:
            if custom_nonce < Nonce(0):
                raise ValueError("Nonce can only be a positive integer.")
        if not self.post_merge:
            return {
                "from": _addr_to_str(self.address),
                "value": Wei(value),
                "gas": int(self.gas_limit),
                "gasPrice": Web3.to_wei(self.gas_price, "gwei"),
                "nonce": Nonce(max(self.last_nonce, 0))
                if custom_nonce is None
                else custom_nonce,
            }
        else:
            return {
                "from": _addr_to_str(self.address),
                "gas": int(self.gas_limit),
                "maxPriorityFeePerGas": Web3.to_wei(self.priority_fee, "gwei"),
                "maxFeePerGas": Web3.to_wei(self.gas_price, "gwei"),
                "type": 2,
                "chainId": self.w3.eth.chain_id,
                "value": Wei(value),
                "nonce": Nonce(max(self.last_nonce, 0))
                if custom_nonce is None
                else custom_nonce,
            }

    def _build_and_send_tx(
        self,
        function: ContractFunction,
        tx_params: Optional[TxParams] = None,
        custom_nonce: Optional[Nonce] = None,
    ) -> HexBytes:
        """Build and send a transaction."""
        if not tx_params:
            tx_params = self._get_tx_params(custom_nonce=custom_nonce)
        transaction = function.build_transaction(tx_params)
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, private_key=self.private_key
        )
        try:
            return self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        finally:
            # logger.debug(f"nonce: {tx_params['nonce']}")
            if custom_nonce is None:
                self.last_nonce = Nonce(tx_params["nonce"] + 1)
