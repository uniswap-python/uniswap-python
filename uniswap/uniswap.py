import os
import json
import time

from web3 import Web3


class UniswapWrapper:
    def __init__(self, address, private_key, provider=None):
        # Initialize web3. Extra provider for testing.
        if not provider:
            self.provider = os.environ["PROVIDER"]
        else:
            self.provider = provider

        self.w3 = Web3(Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60}))
        self.address = address
        self.private_key = private_key

        # This code automatically approves you for trading on the exchange.
        # max_approval is to allow the contract to exchange on your behalf.
        # max_approval_check checks that current approval is above a reasonable number
        # The program cannot check for max_approval each time because it decreases
        # with each trade.
        self.max_approval_hex = "0x" + "f" * 64
        self.max_approval_int = int(self.max_approval_hex, 16)
        self.max_approval_check_hex = "0x" + "0" * 15 + "f" * 49
        self.max_approval_check_int = int(self.max_approval_check_hex, 16)

        # Initialize address and contract
        path = "./uniswap/assets/"
        # Mainnet vs. testnet addressess
        if not provider:
            with open(os.path.abspath(path + "contract_addresses.JSON")) as f:
                contract_addresses = json.load(f)
            with open(os.path.abspath(path + "token_addresses.JSON")) as f:
                self.token_address = json.load(f)
        else:
            with open(os.path.abspath(path + "contract_addresses_testnet.JSON")) as f:
                contract_addresses = json.load(f)
            with open(os.path.abspath(path + "token_addresses_testnet.JSON")) as f:
                self.token_address = json.load(f)

        with open(os.path.abspath(path + "uniswap_exchange.abi")) as f:
            exchange_abi = json.load(f)
        with open(os.path.abspath(path + "erc20.abi")) as f:
            erc20_abi = json.load(f)

        # Defined addresses and contract instance for each token
        self.token_exchange_address = {}
        self.erc20_contract = {}
        self.contract = {}
        for token in contract_addresses:
            address = contract_addresses[token]
            self.token_exchange_address[token] = address
            self.erc20_contract[token] = self.w3.eth.contract(
                address=self.token_address[token], abi=erc20_abi
            )
            self.contract[token] = self.w3.eth.contract(
                address=address, abi=exchange_abi
            )

    # ------ Decorators ----------------------------------------------------------------
    def check_approval(method):
        """Decorator to check if user is approved for a token. It approves them if they
            need to be approved."""
        def approved(self, *args):
            # Check to see if the first token is actually ETH
            token = args[0] if args[0] != 'eth' else None
            token_two = None

            # Check second token, if needed
            if method.__name__ == 'make_trade':
                token_two = args[1] if args[1] != 'eth' else None

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

    # ------ Exchange ------------------------------------------------------------------
    def get_fee_maker(self):
        """Get the maker fee."""
        return 0

    def get_fee_taker(self):
        """Get the maker fee."""
        return 0.003

    # ------ Market --------------------------------------------------------------------
    def get_eth_token_input_price(self, token, qty):
        """Public price for ETH to Token trades with an exact input."""
        return self.contract[token].call().getEthToTokenInputPrice(qty)

    def get_token_eth_input_price(self, token, qty):
        """Public price for token to ETH trades with an exact input."""
        return self.contract[token].call().getTokenToEthInputPrice(qty)

    def get_eth_token_output_price(self, token, qty):
        """Public price for ETH to Token trades with an exact output."""
        return self.contract[token].call().getEthToTokenOutputPrice(qty)

    def get_token_eth_output_price(self, token, qty):
        """Public price for token to ETH trades with an exact output."""
        return self.contract[token].call().getTokenToEthOutputPrice(qty)

    # ------ ERC20 Pool ----------------------------------------------------------------
    def get_eth_balance(self, token):
        """Get the balance of ETH in an exchange contract."""
        return self.w3.eth.getBalance(self.token_exchange_address[token])

    def get_token_balance(self, token):
        """Get the balance of a token in an exchange contract."""
        return (
            self.erc20_contract[token]
            .call()
            .balanceOf(self.token_exchange_address[token])
        )

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
        max_token = int(max_eth * self.get_exchange_rate(token))
        func_params = [min_liquidity, max_token, self._deadline()]
        function = self.contract[token].functions.addLiquidity(*func_params)
        return self._build_and_send_tx(function, tx_params)

    @check_approval
    def remove_liquidity(self, token, max_token):
        """Remove liquidity from the pool."""
        tx_params = self._get_tx_params()
        func_params = [int(max_token), 1, 1, self._deadline()]
        function = self.contract[token].functions.removeLiquidity(*func_params)
        return self._build_and_send_tx(function, tx_params)

    # ------ Trading -------------------------------------------------------------------
    @check_approval
    def make_trade(self, input_token, output_token, qty):
        """Make a trade by defining the qty of the input token."""
        qty = int(qty)
        if input_token == 'eth':
            return self._eth_to_token_swap_input(output_token, qty, self._deadline())
        else:
            if output_token == 'eth':
                return self._token_to_eth_swap_input(input_token, qty, self._deadline())
            else:
                return self._token_to_token_swap_input(input_token, qty, self._deadline(), output_token)

    @check_approval
    def make_trade_output(self, input_token, output_token, qty):
        """Make a trade by defining the qty of the output token."""
        qty = int(qty)
        if input_token == 'eth':
            return self._eth_to_token_swap_input(output_token, qty, self._deadline())
        else:
            if output_token == 'eth':
                return self._token_to_eth_swap_input(input_token, qty, self._deadline())
            else:
        return self._token_to_token_swap_input(input_token, qty, output_token)
    def _eth_to_token_swap_input(self, output_token, qty):
        token_funcs = self.contract[output_token].functions
        tx_params = self._get_tx_params(qty)
        func_params = [qty, self._deadline()]
        function = token_funcs.ethToTokenSwapInput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _token_to_eth_swap_input(self, input_token, qty):
        token_funcs = self.contract[input_token].functions
        tx_params = self._get_tx_params()
        func_params = [qty, 1, self._deadline()]
        function = token_funcs.tokenToEthSwapInput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    def _token_to_token_swap_input(self, input_token, qty, output_token):
        token_funcs = self.contract[input_token].functions
        tx_params = self._get_tx_params()
        func_params = [qty, 1, 1, self._deadline(), self.token_address[output_token]]
        function = token_funcs.tokenToTokenSwapInput(*func_params)
        return self._build_and_send_tx(function, tx_params)

    # ------ Approval Utils ------------------------------------------------------------
    def approve_exchange(self, token, max_approval=None):
        """Give an exchange max approval of a token."""
        max_approval = self.max_approval_int if not max_approval else max_approval
        tx_params = self._get_tx_params()
        exchange_addr = self.token_exchange_address[token]
        function = self.erc20_contract[token].functions.approve(exchange_addr, max_approval)
        tx = self._build_and_send_tx(function, tx_params)
        self.w3.eth.waitForTransactionReceipt(tx, timeout=6000)
        # Add extra sleep to let tx propogate correctly
        time.sleep(1)

    def _is_approved(self, token):
        """Check to see if the exchange and token is approved."""
        exchange_addr = self.token_exchange_address[token]
        amount = (
            self.erc20_contract[token].call().allowance(self.address, exchange_addr)
        )
        if amount >= self.max_approval_check_int:
            return True
        else:
            return False

    # ------ Tx Utils-------------------------------------------------------------------
    def _build_and_send_tx(self, function, tx_params):
        """Build and send a transaction."""
        transaction = function.buildTransaction(tx_params)
        signed_txn = self.w3.eth.account.signTransaction(
            transaction, private_key=self.private_key
        )
        return self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

    def _get_tx_params(self, value=0, gas=100000):
        """Get generic transaction parameters."""
        return {
            "from": self.address,
            "value": value,
            "gas": gas,
            "nonce": self.w3.eth.getTransactionCount(self.address),
        }

if __name__ == "__main__":
    address = os.environ["ETH_ADDRESS"]
    priv_key = os.environ["ETH_PRIV_KEY"]
    # provider = os.environ["TESTNET_PROVIDER"]
    us = UniswapWrapper(address, priv_key)
    # us = UniswapWrapper(address, priv_key, provider)
    one_eth = 1 * 10 ** 18
    qty = 0.000001 * one_eth
    input_token = "bat"
    output_token = "dai"

    print(us.make_trade_output(input_token, output_token, qty))
