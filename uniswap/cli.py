import logging

import click
from dotenv import load_dotenv
from web3 import Web3

from .uniswap import Uniswap, AddressLike


logger = logging.getLogger(__name__)


def _coerce_to_checksum(addr: str) -> str:
    if Web3.isChecksumAddress(addr):
        return addr
    else:
        # logger.warning("Address wasn't in checksum format, coercing")
        return Web3.toChecksumAddress(addr)  # type: ignore


@click.group()
@click.option("-v", "--verbose", is_flag=True)
def main(verbose: bool) -> None:
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    load_dotenv()


@main.command()
@click.argument("token_in", type=_coerce_to_checksum)
@click.argument("token_out", type=_coerce_to_checksum)
@click.option(
    "--quantity", default=10 ** 18, help="quantity of output tokens to get price of"
)
def pricefeed(token_in: AddressLike, token_out: AddressLike, quantity: int) -> None:
    uni = Uniswap(None, None, version=2)
    price = uni.get_token_token_output_price(token_in, token_out, qty=quantity)
    print(price / 10 ** 18)


@main.command()
@click.argument("token", type=_coerce_to_checksum)
def token(token: AddressLike) -> None:
    uni = Uniswap(None, None, version=2)
    t1 = uni.get_token(token)
    print(t1)
