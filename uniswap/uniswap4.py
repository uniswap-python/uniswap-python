import os
import time
import logging
import functools
from typing import List, Any, Optional, Union, Tuple, Dict

from web3 import Web3
from web3.eth import Contract
from web3.contract import ContractFunction
from web3.exceptions import BadFunctionCallOutput, ContractLogicError
from web3.types import (
    TxParams,
    Wei,
    Address,
    ChecksumAddress,
    Nonce,
    HexBytes,
)

from .types import AddressLike
from .token import ERC20Token
from .tokens import tokens, tokens_rinkeby
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
    ETH_ADDRESS,
)

logger = logging.getLogger(__name__)


class Uniswap4:
    """
    Wrapper around Uniswap v4 contracts.
    """

    def __init__(
        self,
        address: Union[AddressLike, str, None],
        private_key: Optional[str],
        provider: str = None,
        web3: Web3 = None,
        default_slippage: float = 0.01,
        poolmanager_contract_addr: str = None,
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

        if poolmanager_contract_addr is None:
            poolmanager_contract_addr = _poolmanager_contract_addresses[self.network]

        self.poolmanager_contract = _load_contract(
            self.w3,
            abi_name="uniswap-v4/poolmanager",
            address=_str_to_addr(poolmanager_contract_addr),
        )

        if hasattr(self, "poolmanager_contract"):
            logger.info(f"Using factory contract: {self.poolmanager_contract}")

    # ------ Market --------------------------------------------------------------------

    def get_price(
        self,
        token0: AddressLike,  # input token
        token1: AddressLike,  # output token
        qty: int,
        fee: int,
        route: Optional[List[AddressLike]] = None,
        zero_to_one: bool = true,
    ) -> int:
        """
        :if `zero_to_one` is true: given `qty` amount of the input `token0`, returns the maximum output amount of output `token1`.
        :if `zero_to_one` is false: returns the minimum amount of `token0` required to buy `qty` amount of `token1`.
        """

        # WIP

        return 0

    # ------ Make Trade ----------------------------------------------------------------
    def make_trade(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty: Union[int, Wei],
        fee: int,
        tick_spacing: int,
        sqrt_price_limit_x96: int = 0,
        zero_for_one: bool = true,
        hooks: AddressLike = ETH,
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
            self._get_tx_params(value=qty),
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

    # ------ Liquidity -----------------------------------------------------------------
    def initialize(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty: Union[int, Wei],
        fee: int,
        tick_spacing: int,
        hooks: AddressLike,
        sqrt_price_limit_x96: int,
    ) -> HexBytes:
        """
        :Initialize the state for a given pool ID
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
                }
            ),
            self._get_tx_params(value=qty),
        )

    def modify_position(
        self,
        currency0: ERC20Token,
        currency1: ERC20Token,
        qty: Union[int, Wei],
        fee: int,
        tick_spacing: int,
        tick_upper: int,
        tick_lower: int,
        hooks: AddressLike,
    ) -> HexBytes:
        if currency0 == currency1:
            raise ValueError

        pool_key = {
            "currency0": currency0.address,
            "currency1": currency1.address,
            "fee": fee,
            "tickSpacing": tick_spacing,
            "hooks": hooks,
        }

        modify_position_params = {
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "liquidityDelta": qty,
        }

        return self._build_and_send_tx(
            self.router.functions.modifyPosition(
                {
                    "key": pool_key,
                    "params": modify_position_params,
                }
            ),
            self._get_tx_params(value=qty),
        )

    # ------ Approval Utils ------------------------------------------------------------
    def approve(self, token: AddressLike, max_approval: Optional[int] = None) -> None:
        """Give an exchange/router max approval of a token."""
        max_approval = self.max_approval_int if not max_approval else max_approval
        contract_addr = (
            self._exchange_address_from_token(token)
            if self.version == 1
            else self.router_address
        )
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
        """Get a predefined deadline. 10min by default (same as the Uniswap SDK)."""
        return int(time.time()) + 10 * 60

    def _build_and_send_tx(
        self, function: ContractFunction, tx_params: Optional[TxParams] = None
    ) -> HexBytes:
        """Build and send a transaction."""
        if not tx_params:
            tx_params = self._get_tx_params()
        transaction = function.buildTransaction(tx_params)
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

    def _get_tx_params(self, value: Wei = Wei(0)) -> TxParams:
        """Get generic transaction parameters."""
        return {
            "from": _addr_to_str(self.address),
            "value": value,
            "nonce": max(
                self.last_nonce, self.w3.eth.get_transaction_count(self.address)
            ),
        }

    # ------ Helpers ------------------------------------------------------------

    def get_token(self, address: AddressLike, abi_name: str = "erc20") -> ERC20Token:
        """
        Retrieves metadata from the ERC20 contract of a given token, like its name, symbol, and decimals.
        """
        # FIXME: This function should always return the same output for the same input
        #        and would therefore benefit from caching
        if address == ETH_ADDRESS:
            return ERC20Token("ETH", ETH_ADDRESS, "Ether", 18)
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

    # ------ Test utilities ------------------------------------------------------------

    def _get_token_addresses(self) -> Dict[str, ChecksumAddress]:
        """
        Returns a dict with addresses for tokens for the current net.
        Used in testing.
        """
        netid = int(self.w3.net.version)
        netname = _netid_to_name[netid]
        if netname == "mainnet":
            return tokens
        elif netname == "rinkeby":
            return tokens_rinkeby
        else:
            raise Exception(f"Unknown net '{netname}'")
