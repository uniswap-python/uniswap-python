import logging
import os

import click
from dotenv import load_dotenv
from web3 import Web3
from typing import Optional

from .uniswap import Uniswap, AddressLike, _str_to_addr
from .token import BaseToken
from .tokens import get_tokens
from .constants import ETH_ADDRESS


logger = logging.getLogger(__name__)

# Global used in _coerce_to_checksum to look up tokens
_uni: Optional[Uniswap] = None


def _coerce_to_checksum(addr: str) -> str:
    assert _uni
    tokens = get_tokens(_uni.netname)
    if not addr.startswith("0x"):
        if addr.upper() in tokens:
            return tokens[addr.upper()]
        else:
            raise ValueError(
                "token was not an address, and a shorthand was not found in the token db"
            )
    if Web3.isChecksumAddress(addr):
        return addr
    else:
        return Web3.toChecksumAddress(addr)


@click.group()
@click.option("-v", "--verbose", is_flag=True)
@click.option(
    "--version",
    type=click.Choice(["1", "2", "3"]),
    default=os.getenv("UNISWAP_VERSION", "3"),
)
@click.pass_context
def main(ctx: click.Context, verbose: bool, version: str) -> None:
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    load_dotenv()

    ctx.ensure_object(dict)
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["UNISWAP"] = Uniswap(None, None, version=int(version))
    global _uni
    _uni = ctx.obj["UNISWAP"]


@main.command()
@click.argument("token_in", type=_coerce_to_checksum)
@click.argument("token_out", type=_coerce_to_checksum)
@click.option(
    "--raw",
    is_flag=True,
    help="Don't normalize the quoted price to the output token's decimals",
)
@click.option(
    "--quantity",
    help="Quantity of output tokens to get price of. Falls back to one full unit of the input token by default (10**18 for WETH, for example).",
)
@click.pass_context
def price(
    ctx: click.Context,
    token_in: AddressLike,
    token_out: AddressLike,
    raw: bool,
    quantity: int = None,
) -> None:
    """Returns the price of ``quantity`` tokens of ``token_in`` quoted in ``token_out``."""
    uni: Uniswap = ctx.obj["UNISWAP"]
    if quantity is None:
        if token_in == ETH_ADDRESS:
            decimals = 18
        else:
            decimals = uni.get_token(token_in).decimals
        quantity = 10**decimals
    price = uni.get_price_input(token_in, token_out, qty=quantity)
    if raw:
        click.echo(price)
    else:
        if token_in == ETH_ADDRESS:
            decimals = 18
        else:
            decimals = uni.get_token(token_out).decimals
        click.echo(price / 10**decimals)


@main.command()
@click.argument("token", type=_coerce_to_checksum)
@click.pass_context
def token(ctx: click.Context, token: AddressLike) -> None:
    """Show metadata for token"""
    uni: Uniswap = ctx.obj["UNISWAP"]
    t1 = uni.get_token(token)
    click.echo(t1)


@main.command()
@click.option("--metadata", is_flag=True, help="Also get metadata for tokens")
@click.pass_context
def tokendb(ctx: click.Context, metadata: bool) -> None:
    """List known token addresses"""
    uni: Uniswap = ctx.obj["UNISWAP"]
    for symbol, addr in get_tokens(uni.netname).items():
        if metadata and addr != "0x0000000000000000000000000000000000000000":
            data = uni.get_token(_str_to_addr(addr))
            assert data.symbol.lower() == symbol.lower()
            click.echo(data)
        else:
            click.echo(BaseToken(symbol, addr))
