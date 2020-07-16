import os
import json
import time
import logging
import functools
from typing import List, Any, Dict, Optional, Callable

from web3 import Web3
from web3.eth import Contract

ETH_ADDRESS = "0x0000000000000000000000000000000000000000"

logger = logging.getLogger(__name__)


def _load_abi(name: str) -> str:
    path = f"{os.path.dirname(os.path.abspath(__file__))}/assets/"
    with open(os.path.abspath(path + f"{name}.abi")) as f:
        abi = json.load(f)
    return abi


def check_approval(method: Callable[..., Any]):
    """Decorator to check if user is approved for a token. It approves them if they
        need to be approved."""

    def approved(self, *args):
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
                self.approve_exchange(token)
        if token_two:
            is_approved = self._is_approved(token_two)
            if not is_approved:
                self.approve_exchange(token_two)
        return method(self, *args)

    return approved


class UniswapWrapper:
    def __init__(
        self,
        address: str,
        private_key: str,
        provider: str = None,
        web3: Web3 = None,
        version: int = 1,
    ) -> None:
        self.address = address
        self.private_key = private_key
        self.version = version

        if web3:
            self.w3 = web3
        else:
            # Initialize web3. Extra provider for testing.
            self.provider = provider or os.environ["PROVIDER"]
            self.w3 = Web3(
                Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60})  # type: ignore
            )

        netid = int(self.w3.net.version)
        if netid == 1:
            self.network = "mainnet"
        elif netid == 4:
            self.network = "rinkeby"
        else:
            raise Exception(f"Unknown netid: {netid}")
        logger.info(f"Using {self.w3} ('{self.network}')")

        self.last_nonce = self.w3.eth.getTransactionCount(self.address)

        # This code automatically approves you for trading on the exchange.
        # max_approval is to allow the contract to exchange on your behalf.
        # max_approval_check checks that current approval is above a reasonable number
        # The program cannot check for max_approval each time because it decreases
        # with each trade.
        self.max_approval_hex = "0x" + "f" * 64
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_approval_check_hex = "0x" + "0" * 15 + "f" * 49
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
                abi_name="factory_contract",
                address=factory_contract_addresses[self.network],
            )
        elif self.version == 2:
            # For v2 the address is the same on mainnet, Ropsten, Rinkeby, Görli, and Kovan
            # https://uniswap.org/docs/v2/smart-contracts/factory
            factory_contract_address_v2 = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
            self.factory_contract = self._load_contract(
                abi_name="UniswapV2Factory", address=factory_contract_address_v2,
            )
        else:
            raise Exception("Invalid version, only 1 or 2 supported")

        logger.info(f"Using factory contract: {self.factory_contract}")

    def get_all_tokens(self) -> List[dict]:
        # FIXME: This is a very expensive operation, would benefit greatly from caching
        tokenCount = self.factory_contract.functions.tokenCount().call()
        tokens = []
        for i in range(tokenCount):
            address = self.factory_contract.functions.getTokenWithId(i).call()
            print(address)
            if address == "0x0000000000000000000000000000000000000000":
                # Token is ETH
                continue
            try:
                token = self.get_token(address)
            except Exception:
                # continue
                raise
            tokens.append(token)
        print(tokens)
        return tokens

    def get_token(self, address: str) -> dict:
        # FIXME: This function should always return the same output for the same input
        #        and would therefore benefit from caching
        token_contract = self._load_contract(abi_name="erc20", address=address)
        try:
            symbol = token_contract.functions.symbol().call()
            name = token_contract.functions.name().call()
        except Exception as e:
            logger.warning(
                f"Exception occurred while trying to get token {address}: {e}"
            )
            raise
        return {"name": name, "symbol": symbol}

    def get_new_exchanges(self):
        new_exchange_event = self.factory_contract.events.NewExchange
        print(new_exchange_event)
        raise NotImplementedError

    def exchange_address_from_token(self, token_addr: str) -> str:
        return self.factory_contract.functions.getExchange(token_addr).call()

    def token_address_from_exchange(self, exchange_addr: str):
        return (
            self.exchange_contract(ex_addr=exchange_addr)
            .functions.tokenAddress(exchange_addr)
            .call()
        )

    @functools.lru_cache()
    def exchange_contract(self, token_addr: str = None, ex_addr: str = None):
        if not ex_addr and token_addr:
            ex_addr = self.exchange_address_from_token(token_addr)
        if ex_addr is None:
            # TODO: Give proper exception
            raise Exception("Couldn't get exchange for {token_addr}")
        contract = self._load_contract(abi_name="uniswap_exchange", address=ex_addr)
        logger.info(f"Loaded exchange contract {contract} at {contract.address}")
        return contract

    @functools.lru_cache()
    def erc20_contract(self, token_addr: str) -> Contract:
        return self._load_contract(abi_name="erc20", address=token_addr)

    def _load_contract(self, abi_name: str, address: str) -> Contract:
        return self.w3.eth.contract(address=address, abi=_load_abi(abi_name))  # type: ignore

    # ------ Exchange ------------------------------------------------------------------
    def get_fee_maker(self) -> float:
        """Get the maker fee."""
        return 0

    def get_fee_taker(self) -> float:
        """Get the taker fee."""
        return 0.003

    # ------ Market --------------------------------------------------------------------
    def get_eth_token_input_price(self, token: str, qty: int):
        """Public price for ETH to Token trades with an exact input."""
        return (
            self.exchange_contract(token).functions.getEthToTokenInputPrice(qty).call()
        )

    def get_token_eth_input_price(self, token: str, qty: int):
        """Public price for token to ETH trades with an exact input."""
        return (
            self.exchange_contract(token).functions.getTokenToEthInputPrice(qty).call()
        )

    def get_eth_token_output_price(self, token: str, qty: int):
        """Public price for ETH to Token trades with an exact output."""
        return (
            self.exchange_contract(token).functions.getEthToTokenOutputPrice(qty).call()
        )

    def get_token_eth_output_price(self, token: str, qty: int):
        """Public price for token to ETH trades with an exact output."""
        return (
            self.exchange_contract(token).functions.getTokenToEthOutputPrice(qty).call()
        )

    # ------ ERC20 Pool ----------------------------------------------------------------
    def get_eth_balance(self, token):
        """Get the balance of ETH in an exchange contract."""
        return self.w3.eth.getBalance(self.exchange_address_from_token(token))

    def get_token_balance(self, token):
        """Get the balance of a token in an exchange contract."""
        return (
            self.erc20_contract(token)
            .functions.balanceOf(self.exchange_address_from_token(token))
            .call()
        )

    # TODO: ADD TOTAL SUPPLY
    def get_exchange_rate(self, token):
        """Get the current ETH/token exchange rate of the token."""
        eth_reserve = self.get_eth_balance(token)
        token_reserve = self.get_token_balance(token)
        return token_reserve / eth_reserve

    # ------ Liquidity -----------------------------------------------------------------
    @check_approval
    def add_liquidity(self, token, max_eth, min_liquidity=1):
        """Add liquidity to the pool."""
        tx_params = self._get_tx_params(int(max_eth))
        # Add 1 to avoid rounding errors, per
        # https://hackmd.io/hthz9hXKQmSyXfMbPsut1g#Add-Liquidity-Calculations
        max_token = int(max_eth * self.get_exchange_rate(token)) + 10
        func_params = [min_liquidity, max_token, self._deadline()]
        function = self.exchange_contract(token).functions.addLiquidity(*func_params)
        return self._build_and_send_tx(function, tx_params)

    @check_approval
    def remove_liquidity(self, token, max_token):
        """Remove liquidity from the pool."""
        tx_params = self._get_tx_params()
        func_params = [int(max_token), 1, 1, self._deadline()]
        function = self.exchange_contract(token).functions.removeLiquidity(*func_params)
        return self._build_and_send_tx(function, tx_params)

    # ------ Make Trade ----------------------------------------------------------------
    @check_approval
    def make_trade(self, input_token, output_token, qty, recipient=None):
        """Make a trade by defining the qty of the input token."""
        qty = int(qty)
        if input_token == ETH_ADDRESS:
            return self._eth_to_token_swap_input(output_token, qty, recipient)
        else:
            if output_token == ETH_ADDRESS:
                return self._token_to_eth_swap_input(input_token, qty, recipient)
            else:
                return self._token_to_token_swap_input(
                    input_token, qty, output_token, recipient
                )

    @check_approval
    def make_trade_output(self, input_token, output_token, qty, recipient=None):
        """Make a trade by defining the qty of the output token."""
        qty = int(qty)
        if input_token == ETH_ADDRESS:
            return self._eth_to_token_swap_output(output_token, qty, recipient)
        else:
            if output_token == ETH_ADDRESS:
                return self._token_to_eth_swap_output(input_token, qty, recipient)
            else:
                return self._token_to_token_swap_output(
                    input_token, qty, output_token, recipient
                )

    def _eth_to_token_swap_input(self, output_token, qty, recipient):
        """Convert ETH to tokens given an input amount."""
        token_funcs = self.exchange_contract(output_token).functions
        tx_params = self._get_tx_params(qty)
        func_params = [qty, self._deadline()]
        if not recipient:
            function = token_funcs.ethToTokenSwapInput(*func_params)
        else:
            func_params.append(recipient)
            function = token_funcs.ethToTokenTransferInput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _token_to_eth_swap_input(self, input_token, qty, recipient):
        """Convert tokens to ETH given an input amount."""
        token_funcs = self.exchange_contract(input_token).functions
        tx_params = self._get_tx_params()
        func_params = [qty, 1, self._deadline()]
        if not recipient:
            function = token_funcs.tokenToEthSwapInput(*func_params)
        else:
            func_params.append(recipient)
            function = token_funcs.tokenToEthTransferInput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _token_to_token_swap_input(self, input_token, qty, output_token, recipient):
        """Convert tokens to tokens given an input amount."""
        token_funcs = self.exchange_contract(input_token).functions
        tx_params = self._get_tx_params()
        func_params = [qty, 1, 1, self._deadline(), output_token]
        if not recipient:
            function = token_funcs.tokenToTokenSwapInput(*func_params)
        else:
            func_params.insert(len(func_params) - 1, recipient)
            function = token_funcs.tokenToTokenTransferInput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _eth_to_token_swap_output(self, output_token, qty, recipient):
        """Convert ETH to tokens given an output amount."""
        token_funcs = self.exchange_contract(output_token).functions
        eth_qty = self.get_eth_token_output_price(output_token, qty)
        tx_params = self._get_tx_params(eth_qty)
        func_params = [qty, self._deadline()]
        if not recipient:
            function = token_funcs.ethToTokenSwapOutput(*func_params)
        else:
            func_params.append(recipient)
            function = token_funcs.ethToTokenTransferOutput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _token_to_eth_swap_output(self, input_token, qty, recipient):
        """Convert tokens to ETH given an output amount."""
        token_funcs = self.exchange_contract(input_token).functions
        max_token = self.get_token_eth_output_price(input_token, qty)
        tx_params = self._get_tx_params()
        func_params = [qty, max_token, self._deadline()]
        if not recipient:
            function = token_funcs.tokenToEthSwapOutput(*func_params)
        else:
            func_params.append(recipient)
            function = token_funcs.tokenToEthTransferOutput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _token_to_token_swap_output(self, input_token, qty, output_token, recipient):
        """Convert tokens to tokens given an output amount."""
        token_funcs = self.exchange_contract(input_token).functions
        max_input_token, max_eth_sold = self._calculate_max_input_token(
            input_token, qty, output_token
        )
        tx_params = self._get_tx_params()
        func_params = [
            qty,
            max_input_token,
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

    # ------ Approval Utils ------------------------------------------------------------
    def approve_exchange(self, token, max_approval=None):
        """Give an exchange max approval of a token."""
        max_approval = self.max_approval_int if not max_approval else max_approval
        tx_params = self._get_tx_params()
        exchange_addr = self.exchange_address_from_token(token)
        function = self.erc20_contract(token).functions.approve(
            exchange_addr, max_approval
        )
        tx = self._build_and_send_tx(function, tx_params)
        self.w3.eth.waitForTransactionReceipt(tx, timeout=6000)
        # Add extra sleep to let tx propogate correctly
        time.sleep(1)

    def _is_approved(self, token):
        """Check to see if the exchange and token is approved."""
        exchange_addr = self.exchange_address_from_token(token)
        amount = (
            self.erc20_contract(token)
            .functions.allowance(self.address, exchange_addr)
            .call()
        )
        if amount >= self.max_approval_check_int:
            return True
        else:
            return False

    # ------ Tx Utils ------------------------------------------------------------------
    def _deadline(self):
        """Get a predefined deadline."""
        return int(time.time()) + 1000

    def _build_and_send_tx(self, function, tx_params):
        """Build and send a transaction."""
        transaction = function.buildTransaction(tx_params)
        signed_txn = self.w3.eth.account.signTransaction(
            transaction, private_key=self.private_key
        )
        # TODO: This needs to get more complicated if we want to support replacing a transaction
        # FIXME: This does not play nice if transactions are sent from other places using the same wallet.
        try:
            return self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        finally:
            logger.debug(f"nonce: {tx_params['nonce']}")
            self.last_nonce = tx_params["nonce"] + 1

    def _get_tx_params(self, value=0, gas=150000) -> Dict[str, Any]:
        """Get generic transaction parameters."""
        return {
            "from": self.address,
            "value": value,
            "gas": gas,
            "nonce": max(
                self.last_nonce, self.w3.eth.getTransactionCount(self.address)
            ),
        }

    # ------ Price Calculation Utils ---------------------------------------------------
    def _calculate_max_input_token(self, input_token, qty, output_token):
        """Calculate the max input and max eth sold for a token to token output swap.
            Equation from: https://hackmd.io/hthz9hXKQmSyXfMbPsut1g"""
        output_amount_b = qty
        input_reserve_b = self.get_eth_balance(output_token)
        output_reserve_b = self.get_token_balance(output_token)

        numerator_b = output_amount_b * input_reserve_b * 1000
        denominator_b = (output_reserve_b - output_amount_b) * 997
        input_about_b = numerator_b / denominator_b + 1

        output_amount_a = input_about_b
        input_reserve_a = self.get_token_balance(input_token)
        output_reserve_a = self.get_eth_balance(input_token)
        numerator_a = output_amount_a * input_reserve_a * 1000
        denominator_a = (output_reserve_a - output_amount_a) * 997
        input_amount_a = numerator_a / denominator_a - 1

        return int(input_amount_a), int(1.2 * input_about_b)


def main():
    address = os.environ["ETH_ADDRESS"]
    priv_key = os.environ["ETH_PRIV_KEY"]
    provider = os.environ["TESTNET_PROVIDER"]
    w3 = Web3(Web3.HTTPProvider(provider, request_kwargs={"timeout": 60}))

    # us = UniswapWrapper(address, priv_key)
    us = UniswapWrapper(address, priv_key, provider)
    ONE_ETH = 1 * 10 ** 18
    ZERO_ADDRESS = "0xD6aE8250b8348C94847280928c79fb3b63cA453e"
    qty = 0.00000005 * ONE_ETH
    eth_main = "0x0000000000000000000000000000000000000000"
    bat_main = "0x0D8775F648430679A709E98d2b0Cb6250d2887EF"
    dai_main = "0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359"

    eth_test = "0x0000000000000000000000000000000000000000"
    bat_test = "0xDA5B056Cfb861282B4b59d29c9B395bcC238D29B"
    dai_test = "0x2448eE2641d78CC42D7AD76498917359D961A783"

    print(us.make_trade_output(bat_test, eth_test, 0.00001 * ONE_ETH, ZERO_ADDRESS))
    # print(us.make_trade_output(input_token, output_token, qty, ZERO_ADDRESS))


if __name__ == "__main__":
    main()
