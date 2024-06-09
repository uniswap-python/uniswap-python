import os
import time
import logging
import functools
import dataclasses
from typing import List, Any, Optional, Union, Tuple, Dict

from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractFunction
from web3.exceptions import BadFunctionCallOutput, ContractLogicError
from web3.types import (
    TxParams,
    Wei,
    Address,
    ChecksumAddress,
    Nonce,
    HexBytes,
)
from .types import AddressLike, UniswapV4_slot0, UniswapV4_position_info, UniswapV4_tick_info, UniswapV4_path_key
from .token import ERC20Token
from .exceptions import InvalidToken, InsufficientBalance
from .util import (
    _str_to_addr,
    _addr_to_str,
    _validate_address,
    _load_contract,
    _load_contract_erc20,
    is_same_address,
)
from .decorators import supports, check_approval
from .constants import (
    _netid_to_name,
    _poolmanager_contract_addresses,
    _quoter_contract_addresses,
    ETH_ADDRESS,
    NOHOOK_ADDRESS,
)

logger = logging.getLogger(__name__)


class Uniswap4Core:
    """
    Wrapper around Uniswap v4 contracts.
    """

    def __init__(
        self,
        address: Union[AddressLike, str, None],
        private_key: Optional[str],
        provider: Optional[str] = None,
        web3: Optional[Web3] = None,
        default_slippage: float = 0.01,
        poolmanager_contract_addr: Optional[str] = None,
        quoter_contract_addr: Optional[str] = None,
    ) -> None:
        """
        :param address: The public address of the ETH wallet to use.
        :param private_key: The private key of the ETH wallet to use.
        :param provider: Can be optionally set to a Web3 provider URI. If none set, will fall back to the PROVIDER environment variable, or web3 if set.
        :param web3: Can be optionally set to a custom Web3 instance.
        :param poolmanager_contract_addr: Can be optionally set to override the address of the PoolManager contract.
        """
        self.address: AddressLike = _str_to_addr(
            address or "0x0000000000000000000000000000000000000000"
        )
        self.private_key = (
            private_key
            or "0x0000000000000000000000000000000000000000000000000000000000000000"
        )

        if web3:
            self.w3 = web3
        else:
            # Initialize web3. Extra provider for testing.
            self.provider = provider or os.environ["PROVIDER"]
            self.w3 = Web3(
                Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60})
            )

        netid = int(self.w3.net.version)
        if netid in _netid_to_name:
            self.network = _netid_to_name[netid]
        else:
            raise Exception(f"Unknown netid: {netid}")
        logger.info(f"Using {self.w3} ('{self.network}')")

        self.last_nonce: Nonce = self.w3.eth.get_transaction_count(self.address)

        max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(max_approval_hex, 16)
        max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
        self.max_approval_check_int = int(max_approval_check_hex, 16)

        if poolmanager_contract_addr is None:
            poolmanager_contract_addr = _poolmanager_contract_addresses[self.network]
        self.poolmanager_contract_addr: AddressLike = _str_to_addr(poolmanager_contract_addr)

        if quoter_contract_addr is None:
            quoter_contract_addr = _quoter_contract_addresses[self.network]
        self.quoter_contract_addr: AddressLike = _str_to_addr(quoter_contract_addr)

        self.router = _load_contract(
            self.w3,
            abi_name="uniswap-v4/poolmanager",
            address=self.poolmanager_contract_addr,
        )

        self.quoter = _load_contract(
            self.w3,
            abi_name="uniswap-v4/quoter",
            address=self.quoter_contract_addr,
        )

        if hasattr(self, "poolmanager_contract"):
            logger.info(f"Using pool manager contract: {self.router}")

    # ------ Contract calls ------------------------------------------------------------

    # ------ Quoter methods --------------------------------------------------------------------

    def get_quote_exact_input_single(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        qty: int,
        fee: int,
        tick_spacing: int,
        hook_data: bytes,
        sqrt_price_limit_x96: int = 0,
        zero_for_one: bool = True,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> Any:
        """
        :if `zero_to_one` is true: given `qty` amount of the input `token0`, returns the maximum output amount of output `token1`.
        :if `zero_to_one` is false: returns the minimum amount of `token0` required to buy `qty` amount of `token1`.
        """

        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0,
            "currency1": currency1,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        quote_params = {
            "poolKey": pool_key,
            "zeroForOne": zero_for_one,
            "recipient": self.address,
            "exactAmount": qty,
            "sqrtPriceLimitX96": sqrt_price_limit_x96,
            "hookData" : hook_data,
        }

        values = self.quoter.functions.quoteExactInputSingle(quote_params)
        #[0]returns deltaAmounts: Delta amounts resulted from the swap
        #[1]returns sqrtPriceX96After: The sqrt price of the pool after the swap
        #[2]returns initializedTicksLoaded: The number of initialized ticks that the swap loaded
        return values

    def get_quote_exact_output_single(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        qty: int,
        fee: int,
        tick_spacing: int,
        hook_data: bytes,
        sqrt_price_limit_x96: int = 0,
        zero_for_one: bool = True,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> Any:
        """
        :if `zero_to_one` is true: given `qty` amount of the input `token0`, returns the maximum output amount of output `token1`.
        :if `zero_to_one` is false: returns the minimum amount of `token0` required to buy `qty` amount of `token1`.
        """

        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0,
            "currency1": currency1,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        quote_params = {
            "poolKey": pool_key,
            "zeroForOne": zero_for_one,
            "recipient": self.address,
            "exactAmount": qty,
            "sqrtPriceLimitX96": sqrt_price_limit_x96,
            "hookData" : hook_data,
        }

        values = self.quoter.functions.quoteExactOutputSingle(quote_params)
        #[0]returns deltaAmounts: Delta amounts resulted from the swap
        #[1]returns sqrtPriceX96After: The sqrt price of the pool after the swap
        #[2]returns initializedTicksLoaded: The number of initialized ticks that the swap loaded
        return values
    
    def get_quote_exact_input(
        self,
        currency: AddressLike,  # input token
        qty: int,
        path : List[UniswapV4_path_key],
    ) -> Any:
        """
        :path  is a swap route
        """

        quote_path = [dataclasses.astuple(item) for item in path]
        quote_params = {
            "exactCurrency": currency,
            "path": quote_path,
            "recipient": self.address,
            "exactAmount": qty,
        }

        values = self.quoter.functions.quoteExactInput(quote_params)
        #[0] returns deltaAmounts: Delta amounts along the path resulted from the swap
        #[1] returns sqrtPriceX96AfterList: List of the sqrt price after the swap for each pool in the path
        #[2] returns initializedTicksLoadedList: List of the initialized ticks that the swap loaded for each pool in the path
        return values

    def get_quote_exact_output(
        self,
        currency: AddressLike,  # input token
        qty: int,
        path : List[UniswapV4_path_key],
    ) -> Any:
        """
        :path  is a swap route
        """

        quote_path = [dataclasses.astuple(item) for item in path]
        quote_params = {
            "exactCurrency": currency,
            "path": quote_path,
            "recipient": self.address,
            "exactAmount": qty,
        }

        values = self.quoter.functions.quoteExactOutput(quote_params)
        #[0] returns deltaAmounts: Delta amounts along the path resulted from the swap
        #[1] returns sqrtPriceX96AfterList: List of the sqrt price after the swap for each pool in the path
        #[2] returns initializedTicksLoadedList: List of the initialized ticks that the swap loaded for each pool in the path
        return values

    # ------ Pool manager READ methods -------------------------------------------------------------------- 
    def get_slot0(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        fee: int,
        tick_spacing: int,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> UniswapV4_slot0:
        """
        :Get the current value in slot0 of the given pool
        """

        pool_id = self.get_pool_id(currency0, currency1, fee, tick_spacing, hooks)
        slot0 = UniswapV4_slot0(*self.router.functions.getSlot0(pool_id).call())
        return slot0

    def get_liquidity(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        fee: int,
        tick_spacing: int,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> int:
        """
        :Get the current value of liquidity of the given pool
        """
        pool_id = self.get_pool_id(currency0, currency1, fee, tick_spacing, hooks)
        liquidity = int(self.router.functions.getLiquidity(pool_id).call())
        return liquidity

    def get_liquidity_for_position(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        fee: int,
        tick_spacing: int,
        owner: AddressLike,
        tick_lower: int,
        tick_upper: int,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> int:
        """
        :Get the current value of liquidity for the specified pool and position
        """
        pool_id = self.get_pool_id(currency0, currency1, fee, tick_spacing, hooks)
        liquidity = int(self.router.functions.getLiquidity(pool_id,owner,tick_lower,tick_upper).call())
        return liquidity

    def get_position(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        fee: int,
        tick_spacing: int,
        owner: AddressLike,  # output token
        tick_lower: int,
        tick_upper: int,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> UniswapV4_position_info:
        """
        :Get the current value of liquidity for the specified pool and position
        """
        pool_id = self.get_pool_id(currency0, currency1, fee, tick_spacing, hooks)
        liquidity = UniswapV4_position_info(*self.router.functions.getPosition(pool_id,owner,tick_lower,tick_upper).call())
        return liquidity

    def get_pool_tick_info(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        fee: int,
        tick_spacing: int,
        tick: int,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> UniswapV4_tick_info:
        """
        :Get the current value of liquidity for the specified pool and position
        """
        pool_id = self.get_pool_id(currency0, currency1, fee, tick_spacing, hooks)
        tick_info = UniswapV4_tick_info(*self.router.functions.getPoolTickInfo(pool_id,tick).call())
        return tick_info

    def get_pool_bitmap_info(
        self,
        currency0: AddressLike,  # input token
        currency1: AddressLike,  # output token
        fee: int,
        tick_spacing: int,
        word: int,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
    ) -> int:
        """
        :Get the current value of liquidity for the specified pool and position
        """
        pool_id = self.get_pool_id(currency0, currency1, fee, tick_spacing, hooks)
        bitmap_info = int(self.router.functions.getPoolBitmapInfo(pool_id, word).call())
        return bitmap_info

    def currency_delta(
        self,
        locker: AddressLike,  # input token
        currency0: AddressLike,  # output token
    ) -> int:
        """
        :Get the current value of liquidity for the specified pool and position
        """
        currency_delta = int(self.router.functions.currencyDelta(locker, currency0).call())
        return currency_delta

    def reserves_of(
        self,
        currency0: AddressLike,  # input token
    ) -> int:
        """
        :Get the current value in slot0 of the given pool
        """

        reserves = int(self.router.functions.reservesOf().call())
        return reserves

    # ------ Pool manager WRITE methods ----------------------------------------------------------------
    def swap(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty: int,
        fee: int,
        tick_spacing: int,
        hook_data : bytes,
        sqrt_price_limit_x96: int = 0,
        zero_for_one: bool = True,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Swap against the given pool
        :
        :`currency0`:The lower currency of the pool, sorted numerically
        :`currency1`:The higher currency of the pool, sorted numerically
        :`fee`: The pool swap fee, capped at 1_000_000. The upper 4 bits determine if the hook sets any fees.
        :`tickSpacing`: Ticks that involve positions must be a multiple of tick spacing
        :`hooks`: The hooks of the pool
        :if `zero_for_one` is true: make a trade by defining the qty of the input token.
        :if `zero_for_one` is false: make a trade by defining the qty of the output token.
        """
        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0.address,
            "currency1": currency1.address,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        swap_params = {
            "zeroForOne": zero_for_one,
            "amountSpecified": qty,
            "sqrtPriceLimitX96": sqrt_price_limit_x96,
        }

        return self._build_and_send_tx(
            self.router.functions.swap(
                {
                    "key": pool_key,
                    "params": swap_params,
                }
            ),
            self._get_tx_params(gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def initialize(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty: int,
        fee: int,
        tick_spacing: int,
        sqrt_price_limit_x96: int,
        hook_data : bytes,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Initialize the state for a given pool key
        :
        :`currency0`:The lower currency of the pool, sorted numerically
        :`currency1`:The higher currency of the pool, sorted numerically
        :`fee`: The pool swap fee, capped at 1_000_000. The upper 4 bits determine if the hook sets any fees.
        :`tickSpacing`: Ticks that involve positions must be a multiple of tick spacing
        :`hooks`: The hooks of the pool
        """
        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0.address,
            "currency1": currency1.address,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        return self._build_and_send_tx(
            self.router.functions.initialize(
                {
                    "key": pool_key,
                    "sqrtPriceX96": sqrt_price_limit_x96,
                    "hookData": hook_data,
                }
            ),
            self._get_tx_params(gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def donate(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty1: int,
        qty2: int,
        fee: int,
        tick_spacing: int,
        sqrt_price_limit_x96: int,
        hook_data : bytes,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Donate the given currency amounts to the pool with the given pool key
        :
        :`currency0`:The lower currency of the pool, sorted numerically
        :`currency1`:The higher currency of the pool, sorted numerically
        :`fee`: The pool swap fee, capped at 1_000_000. The upper 4 bits determine if the hook sets any fees.
        :`tickSpacing`: Ticks that involve positions must be a multiple of tick spacing
        :`hooks`: The hooks of the pool
        """
        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0.address,
            "currency1": currency1.address,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        return self._build_and_send_tx(
            self.router.functions.donate(
                {
                    "key": pool_key,
                    "amount0": qty1,
                    "amount1": qty2,
                    "hookData": hook_data,
                }
            ),
            self._get_tx_params(gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def modify_liquidity(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty: int,
        fee: int,
        tick_spacing: int,
        tick_upper: int,
        tick_lower: int,
        salt : int,
        hook_data : bytes,
        hooks: Union[AddressLike, str, None] = NOHOOK_ADDRESS,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Modify the liquidity for the given pool
        :Poke by calling with a zero liquidityDelta
        :
        :`currency0`:The lower currency of the pool, sorted numerically
        :`currency1`:The higher currency of the pool, sorted numerically
        :`fee`: The pool swap fee, capped at 1_000_000. The upper 4 bits determine if the hook sets any fees.
        :`tickSpacing`: Ticks that involve positions must be a multiple of tick spacing
        :`hooks`: The hooks of the pool
        """
        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0.address,
            "currency1": currency1.address,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        modify_liquidity_params = {
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "liquidityDelta": qty,
            "salt": salt,
        }

        return self._build_and_send_tx(
            self.router.functions.modifyLiquidity(
                {
                    "key": pool_key,
                    "params": modify_position_params,
                    "hookData": hook_data,
                }
            ),
            self._get_tx_params(value=Wei(qty), gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def settle(
        self,
        currency0: Union[AddressLike, str, None],
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Called by the user to pay what is owed
        """

        return self._build_and_send_tx(
            self.router.functions.settle(
                {
                    "currency ": currency0,
                }
            ),
            self._get_tx_params(value=Wei(qty), gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def take(
        self,
        currency0: Union[AddressLike, str, None],
        to: Union[AddressLike, str, None],
        qty: int,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Called by the user to net out some value owed to the user
        :Can also be used as a mechanism for _free_ flash loans
        """

        return self._build_and_send_tx(
            self.router.functions.take(
                {
                    "currency ": currency0,
                    "to ": to,
                    "amount ": qty,
                }
            ),
            self._get_tx_params(gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def mint(
        self,
        currency0: Union[AddressLike, str, None],
        id: int,
        qty: int,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Called by the user to net out some value owed to the user
        :Can also be used as a mechanism for _free_ flash loans
        """

        return self._build_and_send_tx(
            self.router.functions.mint(
                {
                    "currency ": currency0,
                    "id ": id,
                    "amount ": qty,
                }
            ),
            self._get_tx_params(gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    def burn(
        self,
        currency0: Union[AddressLike, str, None],
        id: int,
        qty: int,
        gas: Optional[Wei] = None,
        max_fee: Optional[Wei] = None,
        priority_fee: Optional[Wei] = None,
    ) -> HexBytes:
        """
        :Called by the user to net out some value owed to the user
        :Can also be used as a mechanism for _free_ flash loans
        """

        return self._build_and_send_tx(
            self.router.functions.burn(
                {
                    "currency ": currency0,
                    "id ": id,
                    "amount ": qty,
                }
            ),
            self._get_tx_params(gas = gas, max_fee = max_fee, priority_fee = priority_fee),
        )

    # ------ Wallet balance ------------------------------------------------------------
    def get_eth_balance(self) -> Wei:
        """Get the balance of ETH for your address."""
        return self.w3.eth.get_balance(self.address)

    def get_token_balance(self, token: AddressLike) -> int:
        """Get the balance of a token for your address."""
        _validate_address(token)
        if _addr_to_str(token) == ETH_ADDRESS:
            return self.get_eth_balance()
        erc20 = _load_contract_erc20(self.w3, token)
        balance: int = erc20.functions.balanceOf(self.address).call()
        return balance

    # ------ Approval Utils ------------------------------------------------------------
    def approve(self, token: AddressLike, max_approval: Optional[int] = None) -> None:
        """Give an exchange/router max approval of a token."""
        max_approval = self.max_approval_int if not max_approval else max_approval
        contract_addr = _addr_to_str(self.poolmanager_contract_addr)
        function = _load_contract_erc20(self.w3, token).functions.approve(
            contract_addr, max_approval
        )
        logger.warning(f"Approving {_addr_to_str(token)}...")
        tx = self._build_and_send_tx(function)
        self.w3.eth.wait_for_transaction_receipt(tx, timeout=6000)

        # Add extra sleep to let tx propogate correctly
        time.sleep(1)

    # ------ Tx Utils ------------------------------------------------------------------
    def _deadline(self) -> int:
        """Get a predefined deadline. 10min by default."""
        return int(time.time()) + 10 * 60

    def _build_and_send_tx(
        self, function: ContractFunction, tx_params: Optional[TxParams] = None
    ) -> HexBytes:
        """Build and send a transaction."""
        if not tx_params:
            tx_params = self._get_tx_params()
        transaction = function.build_transaction(tx_params)
        # Uniswap3 uses 20% margin for transactions
        transaction["gas"] = Wei(int(self.w3.eth.estimate_gas(transaction) * 1.2))
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, private_key=self.private_key
        )
        # TODO: This needs to get more complicated if we want to support replacing a transaction
        # FIXME: This does not play nice if transactions are sent from other places using the same wallet.
        try:
            return self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        finally:
            logger.debug(f"nonce: {tx_params['nonce']}")
            self.last_nonce = Nonce(tx_params["nonce"] + 1)

    def _get_tx_params(self, value: Wei = Wei(0), gas: Optional[Wei] = None, max_fee: Optional[Wei] = None, priority_fee: Optional[Wei] = None) -> TxParams:
        """Get generic transaction parameters."""
        params: TxParams = {
            "from": _addr_to_str(self.address),
            "value": value,
            "nonce": max(
                self.last_nonce, self.w3.eth.get_transaction_count(self.address)
            ),
        }

        if gas:
            params["gas"] = gas
        if max_fee:
            params["maxFeePerGas"] = max_fee
        if priority_fee:
            params["maxPriorityFeePerGas"] = priority_fee

        return params

    # ------ Helpers ------------------------------------------------------------

    def get_token(self, address: AddressLike, abi_name: str = "erc20") -> ERC20Token:
        """
        Retrieves metadata from the ERC20 contract of a given token, like its name, symbol, and decimals.
        """
        # FIXME: This function should always return the same output for the same input
        #        and would therefore benefit from caching
        if address == ETH_ADDRESS:
            return ERC20Token("ETH", address, "Ether", 18)
        token_contract = _load_contract(self.w3, abi_name, address=address)
        try:
            _name = token_contract.functions.name().call()
            _symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
        except Exception as e:
            logger.warning(
                f"Exception occurred while trying to get token {_addr_to_str(address)}: {e}"
            )
            raise InvalidToken(address)
        try:
            name = _name.decode()
        except:
            name = _name
        try:
            symbol = _symbol.decode()
        except:
            symbol = _symbol
        return ERC20Token(symbol, address, name, decimals)

    def get_pool_id(self, currency0: Union[AddressLike, str, None], currency1: Union[AddressLike, str, None], fee : int, tickSpacing : int, hooks : Union[AddressLike, str, None] = NOHOOK_ADDRESS) -> bytes:
        if int(currency0, 16) > int(currency1, 16):
            currency0 , currency1 = currency1 , currency0
        pool_id = bytes(self.w3.solidity_keccak(["address", "address", "int24", "int24", "address"], [(currency0, currency1, fee, tickSpacing, hooks)]))
        return pool_id


    