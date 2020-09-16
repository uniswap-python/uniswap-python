import os
import json
import time
import logging
import functools
from typing import List, Any, Optional, Callable, Union, Tuple, Dict

from web3 import Web3
from web3.eth import Contract
from web3.contract import ContractFunction
from web3.types import (
    TxParams,
    Wei,
    Address,
    ChecksumAddress,
    ENS,
    Nonce,
    HexBytes,
)

ETH_ADDRESS = "0x0000000000000000000000000000000000000000"

logger = logging.getLogger(__name__)


AddressLike = Union[Address, ChecksumAddress, ENS]


class InvalidToken(Exception):
    def __init__(self, address: Any) -> None:
        Exception.__init__(self, f"Invalid token address: {address}")


class InsufficientBalance(Exception):
    def __init__(self, had: int, needed: int) -> None:
        Exception.__init__(self, f"Insufficient balance. Had {had}, needed {needed}")


def _load_abi(name: str) -> str:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/assets/"
    with open(os.path.abspath(path + f"{name}.abi")) as f:
        abi: str = json.load(f)
    return abi


def check_approval(method: Callable) -> Callable:
    """Decorator to check if user is approved for a token. It approves them if they
        need to be approved."""

    @functools.wraps(method)
    def approved(self: Any, *args: Any, **kwargs: Any) -> Any:
        # Check to see if the first token is actually ETH
        token = args[0] if args[0] != ETH_ADDRESS else None
        token_two = None

        # Check second token, if needed
        if method.__name__ == "make_trade" or method.__name__ == "make_trade_output":
            token_two = args[1] if args[1] != ETH_ADDRESS else None

        # Approve both tokens, if needed
        if token:
            is_approved = self._is_approved(token)
            if not is_approved:
                self.approve(token)
        if token_two:
            is_approved = self._is_approved(token_two)
            if not is_approved:
                self.approve(token_two)
        return method(self, *args, **kwargs)

    return approved


def supports(versions: List[int]) -> Callable:
    def g(f: Callable) -> Callable:
        @functools.wraps(f)
        def check_version(self: "Uniswap", *args: List, **kwargs: Dict) -> Any:
            if self.version not in versions:
                raise Exception(
                    "Function does not support version of Uniswap passed to constructor"
                )
            return f(self, *args, **kwargs)

        return check_version

    return g


def _str_to_addr(s: str) -> AddressLike:
    if s.startswith("0x"):
        return Address(bytes.fromhex(s[2:]))
    elif s.endswith(".ens"):
        return ENS(s)
    else:
        raise Exception("Could't convert string {s} to AddressLike")


def _addr_to_str(a: AddressLike) -> str:
    if isinstance(a, bytes):
        # Address or ChecksumAddress
        addr: str = Web3.toChecksumAddress("0x" + bytes(a).hex())
        return addr
    elif isinstance(a, str):
        if a.endswith(".ens"):
            # Address is ENS
            raise Exception("ENS not supported for this operation")
        elif a.startswith("0x"):
            addr = Web3.toChecksumAddress(a)
            return addr
        else:
            raise InvalidToken(a)


def _validate_address(a: AddressLike) -> None:
    assert _addr_to_str(a)


_netid_to_name = {1: "mainnet", 4: "rinkeby"}


class Uniswap:
    def __init__(
        self,
        address: Union[str, AddressLike],
        private_key: str,
        provider: str = None,
        web3: Web3 = None,
        version: int = 1,
        max_slippage: float = 0.1,
    ) -> None:
        self.address: AddressLike = _str_to_addr(address) if isinstance(
            address, str
        ) else address
        self.private_key = private_key
        self.version = version

        # TODO: Write tests for slippage
        self.max_slippage = max_slippage

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

        self.last_nonce: Nonce = self.w3.eth.getTransactionCount(self.address)

        # This code automatically approves you for trading on the exchange.
        # max_approval is to allow the contract to exchange on your behalf.
        # max_approval_check checks that current approval is above a reasonable number
        # The program cannot check for max_approval each time because it decreases
        # with each trade.
        self.max_approval_hex = f"0x{64 * 'f'}"
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_approval_check_hex = f"0x{15 * '0'}{49 * 'f'}"
        self.max_approval_check_int = int(self.max_approval_check_hex, 16)

        if self.version == 1:
            factory_contract_addresses = {
                "mainnet": "0xc0a47dFe034B400B47bDaD5FecDa2621de6c4d95",
                "ropsten": "0x9c83dCE8CA20E9aAF9D3efc003b2ea62aBC08351",
                "rinkeby": "0xf5D915570BC477f9B8D6C0E980aA81757A3AaC36",
                "kovan": "0xD3E51Ef092B2845f10401a0159B2B96e8B6c3D30",
                "görli": "0x6Ce570d02D73d4c384b46135E87f8C592A8c86dA",
            }

            self.factory_contract = self._load_contract(
                abi_name="uniswap-v1/factory",
                address=_str_to_addr(factory_contract_addresses[self.network]),
            )
        elif self.version == 2:
            # For v2 the address is the same on mainnet, Ropsten, Rinkeby, Görli, and Kovan
            # https://uniswap.org/docs/v2/smart-contracts/factory
            factory_contract_address_v2 = _str_to_addr(
                "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
            )
            self.factory_contract = self._load_contract(
                abi_name="uniswap-v2/factory", address=factory_contract_address_v2,
            )
            self.router_address: AddressLike = _str_to_addr(
                "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
            )
            """Documented here: https://uniswap.org/docs/v2/smart-contracts/router02/"""
            self.router = self._load_contract(
                abi_name="uniswap-v2/router02", address=self.router_address,
            )
        else:
            raise Exception("Invalid version, only 1 or 2 supported")

        logger.info(f"Using factory contract: {self.factory_contract}")

    @supports([1])
    def get_all_tokens(self) -> List[dict]:
        # FIXME: This is a very expensive operation, would benefit greatly from caching
        tokenCount = self.factory_contract.functions.tokenCount().call()
        tokens = []
        for i in range(tokenCount):
            address = self.factory_contract.functions.getTokenWithId(i).call()
            if address == "0x0000000000000000000000000000000000000000":
                # Token is ETH
                continue
            token = self.get_token(address)
            tokens.append(token)
        return tokens

    @supports([1])
    def get_token(self, address: AddressLike) -> dict:
        # FIXME: This function should always return the same output for the same input
        #        and would therefore benefit from caching
        token_contract = self._load_contract(abi_name="erc20", address=address)
        try:
            symbol = token_contract.functions.symbol().call()
            name = token_contract.functions.name().call()
        except Exception as e:
            logger.warning(
                f"Exception occurred while trying to get token {_addr_to_str(address)}: {e}"
            )
            raise InvalidToken(address)
        return {"name": name, "symbol": symbol}

    @supports([1])
    def exchange_address_from_token(self, token_addr: AddressLike) -> AddressLike:
        ex_addr: AddressLike = self.factory_contract.functions.getExchange(
            token_addr
        ).call()
        # TODO: What happens if the token doesn't have an exchange/doesn't exist? Should probably raise an Exception (and test it)
        return ex_addr

    @supports([1])
    def token_address_from_exchange(self, exchange_addr: AddressLike) -> Address:
        token_addr: Address = (
            self.exchange_contract(ex_addr=exchange_addr)
            .functions.tokenAddress(exchange_addr)
            .call()
        )
        return token_addr

    @functools.lru_cache()
    @supports([1])
    def exchange_contract(
        self, token_addr: AddressLike = None, ex_addr: AddressLike = None
    ) -> Contract:
        if not ex_addr and token_addr:
            ex_addr = self.exchange_address_from_token(token_addr)
        if ex_addr is None:
            raise InvalidToken(token_addr)
        abi_name = "uniswap-v1/exchange"
        contract = self._load_contract(abi_name=abi_name, address=ex_addr)
        logger.info(f"Loaded exchange contract {contract} at {contract.address}")
        return contract

    @functools.lru_cache()
    def erc20_contract(self, token_addr: AddressLike) -> Contract:
        return self._load_contract(abi_name="erc20", address=token_addr)

    @supports([2])
    def get_weth_address(self) -> Address:
        address: Address = self.router.functions.WETH().call()
        return address

    def _load_contract(self, abi_name: str, address: AddressLike) -> Contract:
        return self.w3.eth.contract(address=address, abi=_load_abi(abi_name))

    # ------ Exchange ------------------------------------------------------------------
    @supports([1, 2])
    def get_fee_maker(self) -> float:
        """Get the maker fee."""
        return 0

    @supports([1, 2])
    def get_fee_taker(self) -> float:
        """Get the taker fee."""
        return 0.003

    # ------ Market --------------------------------------------------------------------
    @supports([1, 2])
    def get_eth_token_input_price(self, token: AddressLike, qty: Wei) -> Wei:
        """Public price for ETH to Token trades with an exact input."""
        if self.version == 1:
            ex = self.exchange_contract(token)
            price: Wei = ex.functions.getEthToTokenInputPrice(qty).call()
        elif self.version == 2:
            price = self.router.functions.getAmountsOut(
                qty, [self.get_weth_address(), token]
            ).call()[-1]
        return price

    @supports([1, 2])
    def get_token_eth_input_price(self, token: AddressLike, qty: int) -> int:
        """Public price for token to ETH trades with an exact input."""
        if self.version == 1:
            ex = self.exchange_contract(token)
            price: int = ex.functions.getTokenToEthInputPrice(qty).call()
        else:
            price = self.router.functions.getAmountsOut(
                qty, [token, self.get_weth_address()]
            ).call()[-1]
        return price

    @supports([2])
    def get_token_token_input_price(
        self, token0: AddressLike, token1: AddressLike, qty: int
    ) -> int:
        """Public price for token to token trades with an exact input."""
        price: int = self.router.functions.getAmountsOut(
            qty, [token0, self.get_weth_address(), token1]
        ).call()[-1]
        return price

    @supports([1, 2])
    def get_eth_token_output_price(self, token: AddressLike, qty: int) -> Wei:
        """Public price for ETH to Token trades with an exact output."""
        if self.version == 1:
            ex = self.exchange_contract(token)
            price: Wei = ex.functions.getEthToTokenOutputPrice(qty).call()
        else:
            price = self.router.functions.getAmountsIn(
                qty, [self.get_weth_address(), token]
            ).call()[0]
        return price

    @supports([1, 2])
    def get_token_eth_output_price(self, token: AddressLike, qty: Wei) -> int:
        """Public price for token to ETH trades with an exact output."""
        if self.version == 1:
            ex = self.exchange_contract(token)
            price: int = ex.functions.getTokenToEthOutputPrice(qty).call()
        else:
            price = self.router.functions.getAmountsIn(
                qty, [token, self.get_weth_address()]
            ).call()[0]
        return price

    @supports([2])
    def get_token_token_output_price(
        self, token0: AddressLike, token1: AddressLike, qty: int
    ) -> int:
        """Public price for token to token trades with an exact output."""
        price: int = self.router.functions.getAmountsIn(
            qty, [token0, self.get_weth_address(), token1]
        ).call()[0]
        return price

    # ------ Wallet balance ------------------------------------------------------------
    def get_eth_balance(self) -> Wei:
        """Get the balance of ETH in a wallet."""
        return self.w3.eth.getBalance(self.address)

    def get_token_balance(self, token: AddressLike) -> int:
        """Get the balance of a token in a wallet."""
        _validate_address(token)
        if _addr_to_str(token) == ETH_ADDRESS:
            return self.get_eth_balance()
        erc20 = self.erc20_contract(token)
        balance: int = erc20.functions.balanceOf(self.address).call()
        return balance

    # ------ ERC20 Pool ----------------------------------------------------------------
    @supports([1])
    def get_ex_eth_balance(self, token: AddressLike) -> int:
        """Get the balance of ETH in an exchange contract."""
        ex_addr: AddressLike = self.exchange_address_from_token(token)
        return self.w3.eth.getBalance(ex_addr)

    @supports([1])
    def get_ex_token_balance(self, token: AddressLike) -> int:
        """Get the balance of a token in an exchange contract."""
        erc20 = self.erc20_contract(token)
        balance: int = erc20.functions.balanceOf(
            self.exchange_address_from_token(token)
        ).call()
        return balance

    # TODO: ADD TOTAL SUPPLY
    @supports([1])
    def get_exchange_rate(self, token: AddressLike) -> float:
        """Get the current ETH/token exchange rate of the token."""
        eth_reserve = self.get_ex_eth_balance(token)
        token_reserve = self.get_ex_token_balance(token)
        return float(token_reserve / eth_reserve)

    # ------ Liquidity -----------------------------------------------------------------
    @supports([1])
    @check_approval
    def add_liquidity(
        self, token: AddressLike, max_eth: Wei, min_liquidity: int = 1
    ) -> HexBytes:
        """Add liquidity to the pool."""
        tx_params = self._get_tx_params(max_eth)
        # Add 1 to avoid rounding errors, per
        # https://hackmd.io/hthz9hXKQmSyXfMbPsut1g#Add-Liquidity-Calculations
        max_token = int(max_eth * self.get_exchange_rate(token)) + 10
        func_params = [min_liquidity, max_token, self._deadline()]
        function = self.exchange_contract(token).functions.addLiquidity(*func_params)
        return self._build_and_send_tx(function, tx_params)

    @supports([1])
    @check_approval
    def remove_liquidity(self, token: str, max_token: int) -> HexBytes:
        """Remove liquidity from the pool."""
        func_params = [int(max_token), 1, 1, self._deadline()]
        function = self.exchange_contract(token).functions.removeLiquidity(*func_params)
        return self._build_and_send_tx(function)

    # ------ Make Trade ----------------------------------------------------------------
    @check_approval
    def make_trade(
        self,
        input_token: AddressLike,
        output_token: AddressLike,
        qty: Union[int, Wei],
        recipient: AddressLike = None,
    ) -> HexBytes:
        """Make a trade by defining the qty of the input token."""
        if input_token == ETH_ADDRESS:
            return self._eth_to_token_swap_input(output_token, Wei(qty), recipient)
        else:
            balance = self.get_token_balance(input_token)
            if balance < qty:
                raise InsufficientBalance(balance, qty)
            if output_token == ETH_ADDRESS:
                return self._token_to_eth_swap_input(input_token, qty, recipient)
            else:
                return self._token_to_token_swap_input(
                    input_token, qty, output_token, recipient
                )

    @check_approval
    def make_trade_output(
        self,
        input_token: AddressLike,
        output_token: AddressLike,
        qty: Union[int, Wei],
        recipient: AddressLike = None,
    ) -> HexBytes:
        """Make a trade by defining the qty of the output token."""
        if input_token == ETH_ADDRESS:
            balance = self.get_eth_balance()
            need = self.get_eth_token_output_price(output_token, qty)
            if balance < need:
                raise InsufficientBalance(balance, need)
            return self._eth_to_token_swap_output(output_token, qty, recipient)
        else:
            if output_token == ETH_ADDRESS:
                qty = Wei(qty)
                return self._token_to_eth_swap_output(input_token, qty, recipient)
            else:
                return self._token_to_token_swap_output(
                    input_token, qty, output_token, recipient
                )

    def _eth_to_token_swap_input(
        self, output_token: AddressLike, qty: Wei, recipient: Optional[AddressLike]
    ) -> HexBytes:
        """Convert ETH to tokens given an input amount."""
        eth_balance = self.get_eth_balance()
        if qty > eth_balance:
            raise InsufficientBalance(eth_balance, qty)

        if self.version == 1:
            token_funcs = self.exchange_contract(output_token).functions
            tx_params = self._get_tx_params(qty)
            func_params: List[Any] = [qty, self._deadline()]
            if not recipient:
                function = token_funcs.ethToTokenSwapInput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.ethToTokenTransferInput(*func_params)
            return self._build_and_send_tx(function, tx_params)
        else:
            if recipient is None:
                recipient = self.address
            amount_out_min = int(
                (1 - self.max_slippage)
                * self.get_eth_token_input_price(output_token, qty)
            )
            return self._build_and_send_tx(
                self.router.functions.swapExactETHForTokens(
                    amount_out_min,
                    [self.get_weth_address(), output_token],
                    recipient,
                    self._deadline(),
                ),
                self._get_tx_params(qty),
            )

    def _token_to_eth_swap_input(
        self, input_token: AddressLike, qty: int, recipient: Optional[AddressLike]
    ) -> HexBytes:
        """Convert tokens to ETH given an input amount."""
        # Balance check
        input_balance = self.get_token_balance(input_token)
        cost = self.get_token_eth_input_price(input_token, qty)
        if cost > input_balance:
            raise InsufficientBalance(input_balance, cost)

        if self.version == 1:
            token_funcs = self.exchange_contract(input_token).functions
            func_params: List[Any] = [qty, 1, self._deadline()]
            if not recipient:
                function = token_funcs.tokenToEthSwapInput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.tokenToEthTransferInput(*func_params)
            return self._build_and_send_tx(function)
        else:
            if recipient is None:
                recipient = self.address
            return self._build_and_send_tx(
                self.router.functions.swapExactTokensForETH(
                    qty,
                    int((1 - self.max_slippage) * cost),
                    [input_token, self.get_weth_address()],
                    recipient,
                    self._deadline(),
                ),
            )

    def _token_to_token_swap_input(
        self,
        input_token: AddressLike,
        qty: int,
        output_token: AddressLike,
        recipient: Optional[AddressLike],
    ) -> HexBytes:
        """Convert tokens to tokens given an input amount."""
        if self.version == 1:
            token_funcs = self.exchange_contract(input_token).functions
            # TODO: This might not be correct
            min_tokens_bought, min_eth_bought = self._calculate_max_input_token(
                input_token, qty, output_token
            )
            func_params = [
                qty,
                min_tokens_bought,
                min_eth_bought,
                self._deadline(),
                output_token,
            ]
            if not recipient:
                function = token_funcs.tokenToTokenSwapInput(*func_params)
            else:
                func_params.insert(len(func_params) - 1, recipient)
                function = token_funcs.tokenToTokenTransferInput(*func_params)
            return self._build_and_send_tx(function)
        else:
            if recipient is None:
                recipient = self.address
            min_tokens_bought = int(
                (1 - self.max_slippage)
                * self.get_token_token_input_price(input_token, output_token, qty)
            )
            return self._build_and_send_tx(
                self.router.functions.swapExactTokensForTokens(
                    qty,
                    min_tokens_bought,
                    [input_token, self.get_weth_address(), output_token],
                    recipient,
                    self._deadline(),
                ),
            )

    def _eth_to_token_swap_output(
        self, output_token: AddressLike, qty: int, recipient: Optional[AddressLike]
    ) -> HexBytes:
        """Convert ETH to tokens given an output amount."""
        if self.version == 1:
            token_funcs = self.exchange_contract(output_token).functions
            eth_qty = self.get_eth_token_output_price(output_token, qty)
            tx_params = self._get_tx_params(eth_qty)
            func_params: List[Any] = [qty, self._deadline()]
            if not recipient:
                function = token_funcs.ethToTokenSwapOutput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.ethToTokenTransferOutput(*func_params)
            return self._build_and_send_tx(function, tx_params)
        else:
            if recipient is None:
                recipient = self.address
            eth_qty = self.get_eth_token_output_price(output_token, qty)
            return self._build_and_send_tx(
                self.router.functions.swapETHForExactTokens(
                    qty,
                    [self.get_weth_address(), output_token],
                    recipient,
                    self._deadline(),
                ),
                self._get_tx_params(eth_qty),
            )

    def _token_to_eth_swap_output(
        self, input_token: AddressLike, qty: Wei, recipient: Optional[AddressLike]
    ) -> HexBytes:
        """Convert tokens to ETH given an output amount."""
        # Balance check
        input_balance = self.get_token_balance(input_token)
        cost = self.get_token_eth_output_price(input_token, qty)
        if cost > input_balance:
            raise InsufficientBalance(input_balance, cost)

        if self.version == 1:
            token_funcs = self.exchange_contract(input_token).functions

            # From https://uniswap.org/docs/v1/frontend-integration/trade-tokens/
            # Is all this really necessary? Can't we just use `cost` for max_tokens?
            outputAmount = qty
            inputReserve = self.get_ex_token_balance(input_token)
            outputReserve = self.get_ex_eth_balance(input_token)

            numerator = outputAmount * inputReserve * 1000
            denominator = (outputReserve - outputAmount) * 997
            inputAmount = numerator / denominator + 1

            max_tokens = int((1 + self.max_slippage) * inputAmount)

            func_params: List[Any] = [qty, max_tokens, self._deadline()]
            if not recipient:
                function = token_funcs.tokenToEthSwapOutput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.tokenToEthTransferOutput(*func_params)
            return self._build_and_send_tx(function)
        else:
            max_tokens = int((1 + self.max_slippage) * cost)
            return self._build_and_send_tx(
                self.router.functions.swapTokensForExactETH(
                    qty,
                    max_tokens,
                    [input_token, self.get_weth_address()],
                    self.address,
                    self._deadline(),
                ),
            )

    def _token_to_token_swap_output(
        self,
        input_token: AddressLike,
        qty: int,
        output_token: AddressLike,
        recipient: Optional[AddressLike],
    ) -> HexBytes:
        """Convert tokens to tokens given an output amount."""
        if self.version == 1:
            token_funcs = self.exchange_contract(input_token).functions
            max_tokens_sold, max_eth_sold = self._calculate_max_input_token(
                input_token, qty, output_token
            )
            tx_params = self._get_tx_params()
            func_params = [
                qty,
                max_tokens_sold,
                max_eth_sold,
                self._deadline(),
                output_token,
            ]
            if not recipient:
                function = token_funcs.tokenToTokenSwapOutput(*func_params)
            else:
                func_params.insert(len(func_params) - 1, recipient)
                function = token_funcs.tokenToTokenTransferOutput(*func_params)
            return self._build_and_send_tx(function, tx_params)
        else:
            cost = self.get_token_token_output_price(input_token, output_token, qty)
            amount_in_max = int((1 + self.max_slippage) * cost)
            return self._build_and_send_tx(
                self.router.functions.swapTokensForExactTokens(
                    qty,
                    amount_in_max,
                    [input_token, self.get_weth_address(), output_token],
                    self.address,
                    self._deadline(),
                ),
            )

    # ------ Approval Utils ------------------------------------------------------------
    def approve(self, token: AddressLike, max_approval: Optional[int] = None) -> None:
        """Give an exchange/router max approval of a token."""
        max_approval = self.max_approval_int if not max_approval else max_approval
        contract_addr = (
            self.exchange_address_from_token(token)
            if self.version == 1
            else self.router_address
        )
        function = self.erc20_contract(token).functions.approve(
            contract_addr, max_approval
        )
        logger.info(f"Approving {_addr_to_str(token)}...")
        tx = self._build_and_send_tx(function)
        self.w3.eth.waitForTransactionReceipt(tx, timeout=6000)

        # Add extra sleep to let tx propogate correctly
        time.sleep(1)

    def _is_approved(self, token: AddressLike) -> bool:
        """Check to see if the exchange and token is approved."""
        _validate_address(token)
        if self.version == 1:
            contract_addr = self.exchange_address_from_token(token)
        else:
            contract_addr = self.router_address
        amount = (
            self.erc20_contract(token)
            .functions.allowance(self.address, contract_addr)
            .call()
        )
        if amount >= self.max_approval_check_int:
            return True
        else:
            return False

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
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, private_key=self.private_key
        )
        # TODO: This needs to get more complicated if we want to support replacing a transaction
        # FIXME: This does not play nice if transactions are sent from other places using the same wallet.
        try:
            return self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        finally:
            logger.debug(f"nonce: {tx_params['nonce']}")
            self.last_nonce = Nonce(tx_params["nonce"] + 1)

    def _get_tx_params(self, value: Wei = Wei(0), gas: Wei = Wei(250000)) -> TxParams:
        """Get generic transaction parameters."""
        return {
            "from": _addr_to_str(self.address),
            "value": value,
            "gas": gas,
            "nonce": max(
                self.last_nonce, self.w3.eth.getTransactionCount(self.address)
            ),
        }

    # ------ Price Calculation Utils ---------------------------------------------------
    def _calculate_max_input_token(
        self, input_token: AddressLike, qty: int, output_token: AddressLike
    ) -> Tuple[int, int]:
        """
        For buy orders (exact output), the cost (input) is calculated.
        Calculate the max input and max eth sold for a token to token output swap.
        Equation from:
         - https://hackmd.io/hthz9hXKQmSyXfMbPsut1g
         - https://uniswap.org/docs/v1/frontend-integration/trade-tokens/
        """
        # Buy TokenB with ETH
        output_amount_b = qty
        input_reserve_b = self.get_ex_eth_balance(output_token)
        output_reserve_b = self.get_ex_token_balance(output_token)

        # Cost
        numerator_b = output_amount_b * input_reserve_b * 1000
        denominator_b = (output_reserve_b - output_amount_b) * 997
        input_amount_b = numerator_b / denominator_b + 1

        # Buy ETH with TokenA
        output_amount_a = input_amount_b
        input_reserve_a = self.get_ex_token_balance(input_token)
        output_reserve_a = self.get_ex_eth_balance(input_token)

        # Cost
        numerator_a = output_amount_a * input_reserve_a * 1000
        denominator_a = (output_reserve_a - output_amount_a) * 997
        input_amount_a = numerator_a / denominator_a - 1

        return int(input_amount_a), int(1.2 * input_amount_b)

    def _calculate_max_output_token(
        self, output_token: AddressLike, qty: int, input_token: AddressLike
    ) -> Tuple[int, int]:
        """
        For sell orders (exact input), the amount bought (output) is calculated.
        Similar to _calculate_max_input_token, but for an exact input swap.
        """
        # TokenA (ERC20) to ETH conversion
        inputAmountA = qty
        inputReserveA = self.get_ex_token_balance(input_token)
        outputReserveA = self.get_ex_eth_balance(input_token)

        # Cost
        numeratorA = inputAmountA * outputReserveA * 997
        denominatorA = inputReserveA * 1000 + inputAmountA * 997
        outputAmountA = numeratorA / denominatorA

        # ETH to TokenB conversion
        inputAmountB = outputAmountA
        inputReserveB = self.get_ex_token_balance(output_token)
        outputReserveB = self.get_ex_eth_balance(output_token)

        # Cost
        numeratorB = inputAmountB * outputReserveB * 997
        denominatorB = inputReserveB * 1000 + inputAmountB * 997
        outputAmountB = numeratorB / denominatorB

        return int(outputAmountB), int(1.2 * outputAmountA)

    # ------ Test utilities ------------------------------------------------------------

    def _buy_test_assets(self) -> None:
        """
        Buys some BAT and DAI.
        Used in testing.
        """
        ONE_ETH = 1 * 10 ** 18
        TEST_AMT = int(0.1 * ONE_ETH)
        tokens = self._get_token_addresses()

        for token_name in ["BAT", "DAI"]:
            token_addr = tokens[token_name.lower()]
            price = self.get_eth_token_output_price(_str_to_addr(token_addr), TEST_AMT)
            logger.info(f"Cost of {TEST_AMT} {token_name}: {price}")
            logger.info("Buying...")
            tx = self.make_trade_output(
                tokens["eth"], tokens[token_name.lower()], TEST_AMT
            )
            self.w3.eth.waitForTransactionReceipt(tx)

    def _get_token_addresses(self) -> Dict[str, str]:
        """
        Returns a dict with addresses for tokens for the current net.
        Used in testing.
        """
        netid = int(self.w3.net.version)
        netname = _netid_to_name[netid]
        if netname == "mainnet":
            return {
                "eth": "0x0000000000000000000000000000000000000000",
                "bat": Web3.toChecksumAddress(
                    "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
                ),
                "dai": Web3.toChecksumAddress(
                    "0x6b175474e89094c44da98b954eedeac495271d0f"
                ),
            }
        elif netname == "rinkeby":
            return {
                "eth": "0x0000000000000000000000000000000000000000",
                "bat": "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B",
                "dai": "0x2448eE2641d78CC42D7AD76498917359D961A783",
            }
        else:
            raise Exception(f"Unknown net '{netname}'")
