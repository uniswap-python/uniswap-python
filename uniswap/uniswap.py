import os
import json
import time

from web3 import Web3


class UniswapWrapper():
    def __init__(self):
        # Initialize web3
        self.provider = os.environ['PROVIDER']
        self.eth_address = os.environ['ETH_ADDRESS']
        self.password = os.environ['ETH_ADDRESS_PW']

        self.w3 = Web3(Web3.HTTPProvider(self.provider,
                                         request_kwargs={'timeout':60}))

        # Initialize address and contract
        path = './uniswap/'
        with open(os.path.abspath(path + 'contract_addresses.JSON')) as f:
            contract_addresses = json.load(f)
        with open(os.path.abspath(path + 'token_addresses.JSON')) as f:
            token_addressess = json.load(f)
        with open(os.path.abspath(path + 'uniswap_exchange.abi')) as f:
            exchange_abi = json.load(f)

        # Defined addresses and contract instance for each token
        self.address = {}
        self.contract = {}
        for token in contract_addresses:
            address = contract_addresses[token]
            self.address[token] = address
            self.contract[token] = self.w3.eth.contract(address=address,
                                                        abi=exchange_abi)

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


if __name__ == '__main__':
    us = UniswapWrapper()
    token = 'bat'
    out_token = 'eth'
    one_eth = 1*10**18
    qty = 1 * one_eth
    res = us.get_eth_token_input_price(token, qty)
    print(res)
    res = us.get_token_eth_input_price(token, qty)
    print(res)
    res = us.get_eth_token_output_price(token, qty)
    print(res)
    res = us.get_token_eth_output_price(token, qty)
    print(res)
