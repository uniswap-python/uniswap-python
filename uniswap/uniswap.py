import os
import json
import time

from web3 import Web3


class UniswapWrapper:
    def __init__(self, address, private_key):
        # Initialize web3
        self.provider = os.environ["PROVIDER"]
        self.w3 = Web3(Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60}))
        self.address = address
        self.private_key = private_key

        # Initialize address and contract
        path = "./uniswap/"
        with open(os.path.abspath(path + "contract_addresses.JSON")) as f:
            contract_addresses = json.load(f)
        with open(os.path.abspath(path + "token_addresses.JSON")) as f:
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

    # ------ Exchange ---------------------------------------------------------
    def get_fee_maker(self):
        """Get the maker fee."""
        return 0

    def get_fee_taker(self):
        """Get the maker fee."""
        return 0.003

    # ------ Market -----------------------------------------------------------
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

    # ------ ERC20 Pool -------------------------------------------------------
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

    # ------ Liquidity --------------------------------------------------------
    def add_liquidity(self, token, max_eth, min_liquidity=1, deadline=None):
        """Add liquidity to the pool."""
        deadline = int(time.time()) + 1000 if not deadline else deadline
        tx_params = self._get_tx_params(max_eth)
        max_token = int(max_eth * self.get_exchange_rate(token))
        func_params = [min_liquidity, max_token, deadline]
        function = self.contract[token].functions.addLiquidity(*func_params)
        self._build_and_send_tx(function, tx_params)

    def remove_liquidity(self, token, max_token, deadline=None):
        """Remove liquidity from the pool."""
        deadline = int(time.time()) + 1000 if not deadline else deadline
        tx_params = self._get_tx_params()
        func_params = [max_token, 1, 1, deadline]
        function = self.contract[token].functions.removeLiquidity(*func_params)
        self._build_and_send_tx(function, tx_params)

    # ------ Tx Utils-------------------------------------------------------------------
    def _build_and_send_tx(self, function, tx_params):

        """Build and send a transaction."""
        transaction = function.buildTransaction(tx_params)
        signed_txn = self.w3.eth.account.signTransaction(
            transaction, private_key=self.private_key
        )
        self.w3.eth.sendRawTransaction(signed_txn.rawTransaction)

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
    us = UniswapWrapper(address, priv_key)
    one_eth = 1 * 10 ** 18
    qty = 0.000001 * one_eth
    token = "bat"
    out_token = "eth"

    print(us.remove_liquidity(token, int(qty)))
