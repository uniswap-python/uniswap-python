import os
import time
import logging
import functools
from typing import List, Any, Optional, Union, Tuple, Dict

from web3 import Web3
from web3.eth import Contract
from web3.contract import ContractFunction
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
    _factory_contract_addresses_v1,
    _factory_contract_addresses_v2,
    _router_contract_addresses_v2,
    ETH_ADDRESS,
)

logger = logging.getLogger(__name__)


class Uniswap:
    """
    Wrapper around Uniswap contracts.
    """

    def __init__(
        self,
        address: Union[AddressLike, str, None],
        private_key: Optional[str],
        provider: str = None,
        web3: Web3 = None,
        version: int = 1,
        default_slippage: float = 0.01,
        factory_contract_addr: str = None,
        router_contract_addr: str = None,
    ) -> None:
        """
        :param address: The public address of the ETH wallet to use.
        :param private_key: The private key of the ETH wallet to use.
        :param provider: Can be optionally set to a Web3 provider URI. If none set, will fall back to the PROVIDER environment variable, or web3 if set.
        :param web3: Can be optionally set to a custom Web3 instance.
        :param version: Which version of the Uniswap contracts to use.
        :param default_slippage: Default slippage for a trade, as a float (0.01 is 1%). WARNING: slippage is untested.
        :param factory_contract_addr: Can be optionally set to override the address of the factory contract.
        :param router_contract_addr: Can be optionally set to override the address of the router contract (v2 only).
        """
        self.address: AddressLike = _str_to_addr(
            address or "0x0000000000000000000000000000000000000000"
        )
        self.private_key = (
            private_key
            or "0x0000000000000000000000000000000000000000000000000000000000000000"
        )

        self.version = version

        # TODO: Write tests for slippage
        self.default_slippage = default_slippage

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
            if factory_contract_addr is None:
                factory_contract_addr = _factory_contract_addresses_v1[self.network]

            self.factory_contract = _load_contract(
                self.w3,
                abi_name="uniswap-v1/factory",
                address=_str_to_addr(factory_contract_addr),
            )
        elif self.version == 2:
            if router_contract_addr is None:
                router_contract_addr = _router_contract_addresses_v2[self.network]
            self.router_address: AddressLike = _str_to_addr(router_contract_addr)

            if factory_contract_addr is None:
                factory_contract_addr = _factory_contract_addresses_v2[self.network]
            self.factory_contract = _load_contract(
                self.w3,
                abi_name="uniswap-v2/factory",
                address=_str_to_addr(factory_contract_addr),
            )
            # Documented here: https://uniswap.org/docs/v2/smart-contracts/router02/
            self.router = _load_contract(
                self.w3,
                abi_name="uniswap-v2/router02",
                address=self.router_address,
            )
        elif self.version == 3:
            # https://github.com/Uniswap/uniswap-v3-periphery/blob/main/deploys.md
            quoter_addr = _str_to_addr("0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6")
            self.router_address = _str_to_addr(
                "0xE592427A0AEce92De3Edee1F18E0157C05861564"
            )
            self.quoter = _load_contract(
                self.w3, abi_name="uniswap-v3/quoter", address=quoter_addr
            )
            self.router = _load_contract(
                self.w3, abi_name="uniswap-v3/router", address=self.router_address
            )
        else:
            raise Exception(f"Invalid version '{self.version}', only 1 or 2 supported")

        if hasattr(self, "factory_contract"):
            logger.info(f"Using factory contract: {self.factory_contract}")

    # ------ Market --------------------------------------------------------------------

    def get_price_input(
        self,
        token0: AddressLike,
        token1: AddressLike,
        qty: int,
        fee: int = None,
        route: Optional[List[AddressLike]] = None,
    ) -> int:
        """Returns the amount of the input token you get for `qty` of the output token"""
        if fee is None:
            fee = 3000
            if self.version == 3:
                logger.warning("No fee set, assuming 0.3%")

        if token0 == ETH_ADDRESS:
            return self._get_eth_token_input_price(token1, Wei(qty), fee)
        elif token1 == ETH_ADDRESS:
            return self._get_token_eth_input_price(token0, qty, fee)
        else:
            return self._get_token_token_input_price(token0, token1, qty, fee, route)

    def get_price_output(
        self,
        token0: AddressLike,
        token1: AddressLike,
        qty: int,
        fee: int = None,
        route: Optional[List[AddressLike]] = None,
    ) -> int:
        """Returns the amount of input token you need to get `qty` of the output token"""
        if fee is None:
            fee = 3000
            if self.version == 3:
                logger.warning("No fee set, assuming 0.3%")

        if is_same_address(token0, ETH_ADDRESS):
            return self._get_eth_token_output_price(token1, qty, fee)
        elif is_same_address(token1, ETH_ADDRESS):
            return self._get_token_eth_output_price(token0, Wei(qty), fee)
        else:
            return self._get_token_token_output_price(token0, token1, qty, fee, route)

    def _get_eth_token_input_price(self, token: AddressLike, qty: Wei, fee: int) -> Wei:
        """Public price for ETH to Token trades with an exact input."""
        if self.version == 1:
            ex = self._exchange_contract(token)
            price: Wei = ex.functions.getEthToTokenInputPrice(qty).call()
        elif self.version == 2:
            price = self.router.functions.getAmountsOut(
                qty, [self.get_weth_address(), token]
            ).call()[-1]
        elif self.version == 3:
            price = self._get_token_token_input_price(
                self.get_weth_address(), token, qty, fee=fee
            )  # type: ignore
        return price

    def _get_token_eth_input_price(self, token: AddressLike, qty: int, fee: int) -> int:
        """Public price for token to ETH trades with an exact input."""
        if self.version == 1:
            ex = self._exchange_contract(token)
            price: int = ex.functions.getTokenToEthInputPrice(qty).call()
        elif self.version == 2:
            price = self.router.functions.getAmountsOut(
                qty, [token, self.get_weth_address()]
            ).call()[-1]
        elif self.version == 3:
            price = self._get_token_token_input_price(
                token, self.get_weth_address(), qty, fee=fee
            )
        return price

    def _get_token_token_input_price(
        self,
        token0: AddressLike,
        token1: AddressLike,
        qty: int,
        fee: int,
        route: Optional[List[AddressLike]] = None,
    ) -> int:
        """
        Public price for token to token trades with an exact input.

        :param fee: (v3 only) The pool's fee in hundredths of a bip, i.e. 1e-6 (3000 is 0.3%)
        """
        if route is None:
            if self.version == 2:
                # If one of the tokens are WETH, delegate to appropriate call.
                # See: https://github.com/shanefontaine/uniswap-python/issues/22
                if is_same_address(token0, self.get_weth_address()):
                    return int(self._get_eth_token_input_price(token1, Wei(qty), fee))
                elif is_same_address(token1, self.get_weth_address()):
                    return int(self._get_token_eth_input_price(token0, qty, fee))

                route = [token0, self.get_weth_address(), token1]
                logger.warning(f"No route specified, assuming route: {route}")

        if self.version == 2:
            price: int = self.router.functions.getAmountsOut(qty, route).call()[-1]
        elif self.version == 3:
            if route:
                # NOTE: to support custom routes we need to support the Path data encoding: https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/Path.sol
                # result: tuple = self.quoter.functions.quoteExactInput(route, qty).call()
                raise Exception("custom route not yet supported for v3")

            # FIXME: How to calculate this properly? See https://docs.uniswap.org/reference/libraries/SqrtPriceMath
            sqrtPriceLimitX96 = 0
            price = self.quoter.functions.quoteExactInputSingle(
                token0, token1, fee, qty, sqrtPriceLimitX96
            ).call()
        else:
            raise ValueError("function not supported for this version of Uniswap")
        return price

    def _get_eth_token_output_price(
        self, token: AddressLike, qty: int, fee: int = None
    ) -> Wei:
        """Public price for ETH to Token trades with an exact output."""
        if self.version == 1:
            ex = self._exchange_contract(token)
            price: Wei = ex.functions.getEthToTokenOutputPrice(qty).call()
        elif self.version == 2:
            route = [self.get_weth_address(), token]
            price = self.router.functions.getAmountsIn(qty, route).call()[0]
        elif self.version == 3:
            if not fee:
                logger.warning("No fee set, assuming 0.3%")
                fee = 3000
            price = Wei(
                self._get_token_token_output_price(
                    self.get_weth_address(), token, qty, fee=fee
                )
            )
        return price

    def _get_token_eth_output_price(
        self, token: AddressLike, qty: Wei, fee: int = None
    ) -> int:
        """Public price for token to ETH trades with an exact output."""
        if self.version == 1:
            ex = self._exchange_contract(token)
            price: int = ex.functions.getTokenToEthOutputPrice(qty).call()
        elif self.version == 2:
            route = [token, self.get_weth_address()]
            price = self.router.functions.getAmountsIn(qty, route).call()[0]
        elif self.version == 3:
            if not fee:
                logger.warning("No fee set, assuming 0.3%")
                fee = 3000
            price = self._get_token_token_output_price(
                token, self.get_weth_address(), qty, fee=fee
            )
        return price

    def _get_token_token_output_price(
        self,
        token0: AddressLike,
        token1: AddressLike,
        qty: int,
        fee: int = None,
        route: Optional[List[AddressLike]] = None,
    ) -> int:
        """
        Public price for token to token trades with an exact output.

        :param fee: (v3 only) The pool's fee in hundredths of a bip, i.e. 1e-6 (3000 is 0.3%)
        """
        if not route:
            if self.version == 2:
                # If one of the tokens are WETH, delegate to appropriate call.
                # See: https://github.com/shanefontaine/uniswap-python/issues/22
                if is_same_address(token0, self.get_weth_address()):
                    return int(self._get_eth_token_output_price(token1, qty, fee))
                elif is_same_address(token1, self.get_weth_address()):
                    return int(self._get_token_eth_output_price(token0, Wei(qty), fee))

                route = [token0, self.get_weth_address(), token1]
                logger.warning(f"No route specified, assuming route: {route}")

        if self.version == 2:
            price: int = self.router.functions.getAmountsIn(qty, route).call()[0]
        elif self.version == 3:
            if not fee:
                logger.warning("No fee set, assuming 0.3%")
                fee = 3000
            if route:
                # NOTE: to support custom routes we need to support the Path data encoding: https://github.com/Uniswap/uniswap-v3-periphery/blob/main/contracts/libraries/Path.sol
                # result: tuple = self.quoter.functions.quoteExactOutput(route, qty).call()
                raise Exception("custom route not yet supported for v3")

            # FIXME: How to calculate this properly?
            #   - https://docs.uniswap.org/reference/libraries/SqrtPriceMath
            #   - https://github.com/Uniswap/uniswap-v3-sdk/blob/main/src/swapRouter.ts
            sqrtPriceLimitX96 = 0
            price = self.quoter.functions.quoteExactOutputSingle(
                token0, token1, fee, qty, sqrtPriceLimitX96
            ).call()
        else:
            raise ValueError("function not supported for this version of Uniswap")
        return price

    # ------ Make Trade ----------------------------------------------------------------
    @check_approval
    def make_trade(
        self,
        input_token: AddressLike,
        output_token: AddressLike,
        qty: Union[int, Wei],
        recipient: AddressLike = None,
        fee: int = None,
        slippage: float = None,
    ) -> HexBytes:
        """Make a trade by defining the qty of the input token."""
        if fee is None:
            fee = 3000
            if self.version == 3:
                logger.warning("No fee set, assuming 0.3%")

        if slippage is None:
            slippage = self.default_slippage

        if input_token == ETH_ADDRESS:
            return self._eth_to_token_swap_input(
                output_token, Wei(qty), recipient, fee, slippage
            )
        else:
            balance = self.get_token_balance(input_token)
            if balance < qty:
                raise InsufficientBalance(balance, qty)
            if output_token == ETH_ADDRESS:
                return self._token_to_eth_swap_input(
                    input_token, qty, recipient, fee, slippage
                )
            else:
                return self._token_to_token_swap_input(
                    input_token, output_token, qty, recipient, fee, slippage
                )

    @check_approval
    def make_trade_output(
        self,
        input_token: AddressLike,
        output_token: AddressLike,
        qty: Union[int, Wei],
        recipient: AddressLike = None,
        fee: int = None,
        slippage: float = None,
    ) -> HexBytes:
        """Make a trade by defining the qty of the output token."""
        if fee is None:
            fee = 3000
            if self.version == 3:
                logger.warning("No fee set, assuming 0.3%")

        if slippage is None:
            slippage = self.default_slippage

        if input_token == ETH_ADDRESS:
            balance = self.get_eth_balance()
            need = self._get_eth_token_output_price(output_token, qty)
            if balance < need:
                raise InsufficientBalance(balance, need)
            return self._eth_to_token_swap_output(
                output_token, qty, recipient, fee, slippage
            )
        elif output_token == ETH_ADDRESS:
            qty = Wei(qty)
            return self._token_to_eth_swap_output(
                input_token, qty, recipient, fee, slippage
            )
        else:
            return self._token_to_token_swap_output(
                input_token, output_token, qty, recipient, fee, slippage
            )

    def _eth_to_token_swap_input(
        self,
        output_token: AddressLike,
        qty: Wei,
        recipient: Optional[AddressLike],
        fee: int,
        slippage: float,
    ) -> HexBytes:
        """Convert ETH to tokens given an input amount."""
        eth_balance = self.get_eth_balance()
        if qty > eth_balance:
            raise InsufficientBalance(eth_balance, qty)

        if self.version == 1:
            token_funcs = self._exchange_contract(output_token).functions
            tx_params = self._get_tx_params(qty)
            func_params: List[Any] = [qty, self._deadline()]
            if not recipient:
                function = token_funcs.ethToTokenSwapInput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.ethToTokenTransferInput(*func_params)
            return self._build_and_send_tx(function, tx_params)

        elif self.version == 2:
            if recipient is None:
                recipient = self.address
            amount_out_min = int(
                (1 - slippage) * self._get_eth_token_input_price(output_token, qty, fee)
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
        elif self.version == 3:
            return self._token_to_token_swap_input(
                self.get_weth_address(), output_token, qty, recipient, fee, slippage
            )
        else:
            raise ValueError

    def _token_to_eth_swap_input(
        self,
        input_token: AddressLike,
        qty: int,
        recipient: Optional[AddressLike],
        fee: int,
        slippage: float,
    ) -> HexBytes:
        """Convert tokens to ETH given an input amount."""
        # Balance check
        input_balance = self.get_token_balance(input_token)
        if qty > input_balance:
            raise InsufficientBalance(input_balance, qty)

        if self.version == 1:
            token_funcs = self._exchange_contract(input_token).functions
            func_params: List[Any] = [qty, 1, self._deadline()]
            if not recipient:
                function = token_funcs.tokenToEthSwapInput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.tokenToEthTransferInput(*func_params)
            return self._build_and_send_tx(function)
        elif self.version == 2:
            if recipient is None:
                recipient = self.address
            amount_out_min = int(
                (1 - slippage) * self._get_token_eth_input_price(input_token, qty, fee)
            )
            return self._build_and_send_tx(
                self.router.functions.swapExactTokensForETH(
                    qty,
                    amount_out_min,
                    [input_token, self.get_weth_address()],
                    recipient,
                    self._deadline(),
                ),
            )
        elif self.version == 3:
            return self._token_to_token_swap_input(
                input_token, self.get_weth_address(), qty, recipient, fee, slippage
            )
        else:
            raise ValueError

    def _token_to_token_swap_input(
        self,
        input_token: AddressLike,
        output_token: AddressLike,
        qty: int,
        recipient: Optional[AddressLike],
        fee: int,
        slippage: float,
    ) -> HexBytes:
        """Convert tokens to tokens given an input amount."""
        if recipient is None:
            recipient = self.address
        if self.version == 1:
            token_funcs = self._exchange_contract(input_token).functions
            # TODO: This might not be correct
            min_tokens_bought, min_eth_bought = self._calculate_max_output_token(
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
        elif self.version == 2:
            min_tokens_bought = int(
                (1 - slippage)
                * self._get_token_token_input_price(
                    input_token, output_token, qty, fee=fee
                )
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
        elif self.version == 3:
            min_tokens_bought = int(
                (1 - slippage)
                * self._get_token_token_input_price(
                    input_token, output_token, qty, fee=fee
                )
            )
            sqrtPriceLimitX96 = 0
            return self._build_and_send_tx(
                self.router.functions.exactInputSingle(
                    {
                        "tokenIn": input_token,
                        "tokenOut": output_token,
                        "fee": fee,
                        "recipient": recipient,
                        "deadline": self._deadline(),
                        "amountIn": qty,
                        "amountOutMinimum": min_tokens_bought,
                        "sqrtPriceLimitX96": sqrtPriceLimitX96,
                    }
                ),
                self._get_tx_params(
                    Wei(qty) if input_token == self.get_weth_address() else Wei(0)
                ),
            )
        else:
            raise ValueError

    def _eth_to_token_swap_output(
        self,
        output_token: AddressLike,
        qty: int,
        recipient: Optional[AddressLike],
        fee: int,
        slippage: float,
    ) -> HexBytes:
        """Convert ETH to tokens given an output amount."""
        if self.version == 1:
            token_funcs = self._exchange_contract(output_token).functions
            eth_qty = self._get_eth_token_output_price(output_token, qty)
            tx_params = self._get_tx_params(eth_qty)
            func_params: List[Any] = [qty, self._deadline()]
            if not recipient:
                function = token_funcs.ethToTokenSwapOutput(*func_params)
            else:
                func_params.append(recipient)
                function = token_funcs.ethToTokenTransferOutput(*func_params)
            return self._build_and_send_tx(function, tx_params)
        elif self.version == 2:
            if recipient is None:
                recipient = self.address
            eth_qty = int(
                (1 + slippage)
                * self._get_eth_token_output_price(output_token, qty, fee)
            )  # type: ignore
            return self._build_and_send_tx(
                self.router.functions.swapETHForExactTokens(
                    qty,
                    [self.get_weth_address(), output_token],
                    recipient,
                    self._deadline(),
                ),
                self._get_tx_params(eth_qty),
            )
        elif self.version == 3:
            return self._token_to_token_swap_output(
                self.get_weth_address(), output_token, qty, recipient, fee, slippage
            )
        else:
            raise ValueError

    def _token_to_eth_swap_output(
        self,
        input_token: AddressLike,
        qty: Wei,
        recipient: Optional[AddressLike],
        fee: int,
        slippage: float,
    ) -> HexBytes:
        """Convert tokens to ETH given an output amount."""
        # Balance check
        input_balance = self.get_token_balance(input_token)
        cost = self._get_token_eth_output_price(input_token, qty, fee)
        if cost > input_balance:
            raise InsufficientBalance(input_balance, cost)

        if self.version == 1:
            # From https://uniswap.org/docs/v1/frontend-integration/trade-tokens/
            # Is all this really necessary? Can't we just use `cost` for max_tokens?
            outputAmount = qty
            inputReserve = self.get_ex_token_balance(input_token)
            outputReserve = self.get_ex_eth_balance(input_token)

            numerator = outputAmount * inputReserve * 1000
            denominator = (outputReserve - outputAmount) * 997
            inputAmount = numerator / denominator + 1

            max_tokens = int((1 + slippage) * inputAmount)

            ex = self._exchange_contract(input_token)
            func_params: List[Any] = [qty, max_tokens, self._deadline()]
            if not recipient:
                function = ex.functions.tokenToEthSwapOutput(*func_params)
            else:
                func_params.append(recipient)
                function = ex.functions.tokenToEthTransferOutput(*func_params)
            return self._build_and_send_tx(function)
        elif self.version == 2:
            max_tokens = int((1 + slippage) * cost)
            return self._build_and_send_tx(
                self.router.functions.swapTokensForExactETH(
                    qty,
                    max_tokens,
                    [input_token, self.get_weth_address()],
                    self.address,
                    self._deadline(),
                ),
            )
        elif self.version == 3:
            return self._token_to_token_swap_output(
                input_token, self.get_weth_address(), qty, recipient, fee, slippage
            )
        else:
            raise ValueError

    def _token_to_token_swap_output(
        self,
        input_token: AddressLike,
        output_token: AddressLike,
        qty: int,
        recipient: Optional[AddressLike],
        fee: int,
        slippage: float,
    ) -> HexBytes:
        """
        Convert tokens to tokens given an output amount.

        :param fee: TODO
        """
        if self.version == 1:
            token_funcs = self._exchange_contract(input_token).functions
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
        elif self.version == 2:
            if recipient is None:
                recipient = self.address
            cost = self._get_token_token_output_price(
                input_token, output_token, qty, fee=fee
            )
            amount_in_max = int((1 + slippage) * cost)
            return self._build_and_send_tx(
                self.router.functions.swapTokensForExactTokens(
                    qty,
                    amount_in_max,
                    [input_token, self.get_weth_address(), output_token],
                    recipient,
                    self._deadline(),
                ),
            )
        elif self.version == 3:
            if recipient is None:
                recipient = self.address

            cost = self._get_token_token_output_price(
                input_token, output_token, qty, fee=fee
            )
            amount_in_max = int((1 + slippage) * cost)
            sqrtPriceLimitX96 = 0

            return self._build_and_send_tx(
                self.router.functions.exactOutputSingle(
                    {
                        "tokenIn": input_token,
                        "tokenOut": output_token,
                        "fee": fee,
                        "recipient": recipient,
                        "deadline": self._deadline(),
                        "amountOut": qty,
                        "amountInMaximum": amount_in_max,
                        "sqrtPriceLimitX96": sqrtPriceLimitX96,
                    },
                ),
                self._get_tx_params(
                    Wei(amount_in_max)
                    if input_token == self.get_weth_address()
                    else Wei(0)
                ),
            )
        else:
            raise ValueError

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

    # ------ ERC20 Pool ----------------------------------------------------------------
    @supports([1])
    def get_ex_eth_balance(self, token: AddressLike) -> int:
        """Get the balance of ETH in an exchange contract."""
        ex_addr: AddressLike = self._exchange_address_from_token(token)
        return self.w3.eth.get_balance(ex_addr)

    @supports([1])
    def get_ex_token_balance(self, token: AddressLike) -> int:
        """Get the balance of a token in an exchange contract."""
        erc20 = _load_contract_erc20(self.w3, token)
        balance: int = erc20.functions.balanceOf(
            self._exchange_address_from_token(token)
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
        function = self._exchange_contract(token).functions.addLiquidity(*func_params)
        return self._build_and_send_tx(function, tx_params)

    @supports([1])
    @check_approval
    def remove_liquidity(self, token: str, max_token: int) -> HexBytes:
        """Remove liquidity from the pool."""
        func_params = [int(max_token), 1, 1, self._deadline()]
        function = self._exchange_contract(token).functions.removeLiquidity(
            *func_params
        )
        return self._build_and_send_tx(function)

    # ------ Approval Utils ------------------------------------------------------------
    def _approve(self, token: AddressLike, max_approval: Optional[int] = None) -> None:
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
        self.w3.eth.waitForTransactionReceipt(tx, timeout=6000)

        # Add extra sleep to let tx propogate correctly
        time.sleep(1)

    def _is_approved(self, token: AddressLike) -> bool:
        """Check to see if the exchange and token is approved."""
        _validate_address(token)
        if self.version == 1:
            contract_addr = self._exchange_address_from_token(token)
        elif self.version in [2, 3]:
            contract_addr = self.router_address
        amount = (
            _load_contract_erc20(self.w3, token)
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
            return self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
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

    # ------ Helpers ------------------------------------------------------------

    def get_token(self, address: AddressLike) -> ERC20Token:
        """
        Retrieves metadata from the ERC20 contract of a given token, like its name, symbol, and decimals.
        """
        # FIXME: This function should always return the same output for the same input
        #        and would therefore benefit from caching
        token_contract = _load_contract(self.w3, abi_name="erc20", address=address)
        try:
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
        except Exception as e:
            logger.warning(
                f"Exception occurred while trying to get token {_addr_to_str(address)}: {e}"
            )
            raise InvalidToken(address)
        return ERC20Token(symbol, address, name, decimals)

    @functools.lru_cache()
    @supports([2, 3])
    def get_weth_address(self) -> ChecksumAddress:
        """Retrieves the WETH address from the contracts (which may vary between chains)."""
        if self.version == 2:
            # Contract calls should always return checksummed addresses
            address: ChecksumAddress = self.router.functions.WETH().call()
        elif self.version == 3:
            address = self.router.functions.WETH9().call()
        return address

    # ------ Exchange ------------------------------------------------------------------
    @supports([1, 2])
    def get_fee_maker(self) -> float:
        """Get the maker fee."""
        return 0

    @supports([1, 2])
    def get_fee_taker(self) -> float:
        """Get the taker fee."""
        return 0.003

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

    # ---- Old v1 utils ----

    @supports([1])
    def _exchange_address_from_token(self, token_addr: AddressLike) -> AddressLike:
        ex_addr: AddressLike = self.factory_contract.functions.getExchange(
            token_addr
        ).call()
        # TODO: What happens if the token doesn't have an exchange/doesn't exist?
        #       Should probably raise an Exception (and test it)
        return ex_addr

    @supports([1])
    def _token_address_from_exchange(self, exchange_addr: AddressLike) -> Address:
        token_addr: Address = (
            self._exchange_contract(ex_addr=exchange_addr)
            .functions.tokenAddress(exchange_addr)
            .call()
        )
        return token_addr

    @functools.lru_cache()
    @supports([1])
    def _exchange_contract(
        self, token_addr: AddressLike = None, ex_addr: AddressLike = None
    ) -> Contract:
        if not ex_addr and token_addr:
            ex_addr = self._exchange_address_from_token(token_addr)
        if ex_addr is None:
            raise InvalidToken(token_addr)
        abi_name = "uniswap-v1/exchange"
        contract = _load_contract(self.w3, abi_name=abi_name, address=ex_addr)
        logger.info(f"Loaded exchange contract {contract} at {contract.address}")
        return contract

    @supports([1])
    def _get_all_tokens(self) -> List[ERC20Token]:
        """
        Retrieves all token pairs.

        Note: This is a *very* expensive operation and might therefore not work properly.
        """
        # FIXME: This is a very expensive operation, would benefit greatly from caching.
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
