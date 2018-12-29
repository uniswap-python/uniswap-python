import os
import json
import time

from web3 import Web3


class UniswapWrapper():
    def __init__(self) -> None:
        # Initialize web3
        self.eth_address = os.environ['ETH_ADDRESS']
        self.password = os.environ['ETH_ADDRESS_PW']

        self.w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545",
                                         request_kwargs={'timeout':60}))
        self.w3.personal.unlockAccount(self.eth_address, self.password)

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
    def get_fee_maker(self) -> float:
        """Get the maker fee."""
        return 0

    def get_fee_taker(self) -> float:
        """Get the maker fee."""
        return 0.003


if __name__ == '__main__':
    us = UniswapWrapper()
    res = us.get_fee_maker()
    print(res)

