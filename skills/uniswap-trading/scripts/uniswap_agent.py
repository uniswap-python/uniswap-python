#!/usr/bin/env python3
"""Agent-facing CLI wrapper around uniswap-python.

Designed to be invoked by AI agents (Claude Code skills, gptme tools, MCP
servers) as a plain subprocess. Every command supports ``--json`` for
machine-readable output.

Safety model (testnet-first):
- Read-only commands (status, quote, balance) work on any chain.
- Broadcasting is only allowed on well-known testnets unless
  ``UNISWAP_AGENT_ALLOW_MAINNET=1`` is set.
- All state-changing commands are dry-run by default; pass ``--broadcast``
  to actually sign and send. A private key is only required to broadcast.
- Slippage is capped at 5% unless ``UNISWAP_AGENT_MAX_SLIPPAGE`` raises it.

Environment:
    PROVIDER                     JSON-RPC endpoint (uniswap-python convention)
    UNISWAP_AGENT_ADDRESS        Wallet address; required by balance
    UNISWAP_AGENT_PRIVATE_KEY    Private key; only needed with --broadcast
    UNISWAP_AGENT_ALLOW_MAINNET  Set to 1 to allow non-testnet chains
    UNISWAP_AGENT_MAX_SLIPPAGE   Override the 0.05 slippage ceiling (float)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional

ETH = "0x0000000000000000000000000000000000000000"

# Chains the wrapper will BROADCAST on without explicit mainnet opt-in.
# Read-only operations are allowed on any chain.
TESTNET_CHAIN_IDS = {
    11155111: "sepolia",
    421614: "arbitrum-sepolia",
    84532: "base-sepolia",
    11155420: "optimism-sepolia",
}

# Convenience symbols per chain, so agents can say WETH instead of an address.
TOKEN_ALIASES: dict[int, dict[str, str]] = {
    11155111: {
        "ETH": ETH,
        "WETH": "0xfFf9976782d46CC05630D1f6eBAb18b2324d6B14",
        "USDC": "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238",
    },
    1: {
        "ETH": ETH,
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    },
}

DEFAULT_MAX_SLIPPAGE = 0.05


class SafetyError(Exception):
    """A guard refused the operation. Message is agent-readable."""


def check_broadcast_chain_allowed(chain_id: int, allow_mainnet: bool) -> None:
    """Gate for state-changing (broadcast) operations only."""
    if chain_id in TESTNET_CHAIN_IDS:
        return
    if not allow_mainnet:
        raise SafetyError(
            f"refusing to broadcast on chain id {chain_id} (not a known testnet). "
            "Set UNISWAP_AGENT_ALLOW_MAINNET=1 to trade on it deliberately."
        )


def check_slippage(slippage: float, ceiling: float) -> None:
    if not 0 < slippage <= ceiling:
        raise SafetyError(
            f"slippage {slippage} outside (0, {ceiling}]; "
            "raise UNISWAP_AGENT_MAX_SLIPPAGE only if you understand the risk."
        )


def check_broadcast_allowed(broadcast: bool, private_key: Optional[str]) -> None:
    if broadcast and not private_key:
        raise SafetyError(
            "--broadcast requires UNISWAP_AGENT_PRIVATE_KEY; "
            "without it only dry-run is available."
        )


def require_wallet_address(address: Optional[str]) -> str:
    if not address:
        raise SafetyError(
            "balance requires UNISWAP_AGENT_ADDRESS to identify the wallet"
        )
    if len(address) != 42 or not address.startswith("0x"):
        raise SafetyError("UNISWAP_AGENT_ADDRESS must be a non-zero EVM address")
    try:
        value = int(address[2:], 16)
    except ValueError as error:
        raise SafetyError(
            "UNISWAP_AGENT_ADDRESS must be a non-zero EVM address"
        ) from error
    if value == 0:
        raise SafetyError("UNISWAP_AGENT_ADDRESS must be a non-zero EVM address")
    return address


def resolve_token(symbol_or_addr: str, chain_id: int) -> str:
    if symbol_or_addr.startswith("0x"):
        return symbol_or_addr
    alias = TOKEN_ALIASES.get(chain_id, {}).get(symbol_or_addr.upper())
    if alias is None:
        raise SafetyError(
            f"unknown token symbol {symbol_or_addr!r} on chain {chain_id}; "
            "pass a 0x address instead."
        )
    return alias


@dataclass
class Config:
    provider: str
    address: Optional[str]
    private_key: Optional[str]
    allow_mainnet: bool
    max_slippage: float

    @classmethod
    def from_env(cls) -> "Config":
        provider = os.environ.get("PROVIDER") or os.environ.get("UNISWAP_AGENT_RPC")
        if not provider:
            raise SafetyError("PROVIDER (JSON-RPC endpoint) is not set.")
        return cls(
            provider=provider,
            address=os.environ.get("UNISWAP_AGENT_ADDRESS"),
            private_key=os.environ.get("UNISWAP_AGENT_PRIVATE_KEY"),
            allow_mainnet=os.environ.get("UNISWAP_AGENT_ALLOW_MAINNET") == "1",
            max_slippage=float(
                os.environ.get("UNISWAP_AGENT_MAX_SLIPPAGE", DEFAULT_MAX_SLIPPAGE)
            ),
        )


def _connect(cfg: Config, version: int) -> Any:
    """Instantiate the right uniswap-python client for the chain/version."""
    os.environ["PROVIDER"] = cfg.provider
    if version == 4:
        from uniswap import Uniswap4

        return Uniswap4(
            address=cfg.address or ETH,
            private_key=cfg.private_key,
            provider=cfg.provider,
        )
    from uniswap import Uniswap

    return Uniswap(
        address=cfg.address,
        private_key=cfg.private_key,
        provider=cfg.provider,
        version=version,
    )


def _chain_id(client: Any) -> int:
    return int(client.w3.eth.chain_id)


def cmd_status(cfg: Config, args: argparse.Namespace) -> dict[str, Any]:
    client = _connect(cfg, args.version)
    chain_id = _chain_id(client)
    out: dict[str, Any] = {
        "chain_id": chain_id,
        "network": TESTNET_CHAIN_IDS.get(chain_id, "non-testnet"),
        "version": args.version,
        "address": cfg.address,
        "can_broadcast": bool(cfg.private_key),
    }
    if cfg.address:
        out["eth_balance_wei"] = int(client.w3.eth.get_balance(cfg.address))
    return out


def cmd_quote(cfg: Config, args: argparse.Namespace) -> dict[str, Any]:
    client = _connect(cfg, args.version)
    chain_id = _chain_id(client)
    token_in = resolve_token(args.token_in, chain_id)
    token_out = resolve_token(args.token_out, chain_id)
    if args.version == 4:
        amount_out = client.get_price_input(
            token_in,
            token_out,
            args.qty,
            fee=args.fee,
            tick_spacing=args.tick_spacing,
        )
    else:
        amount_out = client.get_price_input(token_in, token_out, args.qty, fee=args.fee)
    return {
        "chain_id": chain_id,
        "version": args.version,
        "token_in": token_in,
        "token_out": token_out,
        "qty_in": args.qty,
        "amount_out": int(amount_out),
    }


def cmd_swap(cfg: Config, args: argparse.Namespace) -> dict[str, Any]:
    check_broadcast_allowed(args.broadcast, cfg.private_key)
    check_slippage(args.slippage, cfg.max_slippage)
    client = _connect(cfg, args.version)
    chain_id = _chain_id(client)
    if args.broadcast:
        check_broadcast_chain_allowed(chain_id, cfg.allow_mainnet)
    token_in = resolve_token(args.token_in, chain_id)
    token_out = resolve_token(args.token_out, chain_id)

    if args.version == 4:
        quoted = int(
            client.get_price_input(
                token_in,
                token_out,
                args.qty,
                fee=args.fee,
                tick_spacing=args.tick_spacing,
            )
        )
    else:
        quoted = int(
            client.get_price_input(token_in, token_out, args.qty, fee=args.fee)
        )
    min_out = int(quoted * (1 - args.slippage))

    plan = {
        "chain_id": chain_id,
        "version": args.version,
        "token_in": token_in,
        "token_out": token_out,
        "qty_in": args.qty,
        "quoted_out": quoted,
        "min_out": min_out,
        "slippage": args.slippage,
        "broadcast": args.broadcast,
    }
    if not args.broadcast:
        plan["note"] = "dry-run: pass --broadcast to sign and send"
        return plan

    if args.version == 4:
        # Single-hop v4 swap; fee + tick_spacing identify the pool.
        from uniswap.types import PoolKey

        c0, c1 = sorted([token_in, token_out], key=str.lower)
        pool_key = PoolKey(
            currency0=c0,
            currency1=c1,
            fee=args.fee,
            tick_spacing=args.tick_spacing,
            hooks=ETH,
        )
        tx_hash = client.make_swap_input(
            token_in, token_out, args.qty, min_out, swap_pool_key=pool_key
        )
    else:
        tx_hash = client.make_trade(
            token_in, token_out, args.qty, fee=args.fee, slippage=args.slippage
        )
    plan["tx_hash"] = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)
    return plan


def cmd_balance(cfg: Config, args: argparse.Namespace) -> dict[str, Any]:
    address = require_wallet_address(cfg.address)
    cfg.address = address
    client = _connect(cfg, args.version if args.version != 4 else 3)
    chain_id = _chain_id(client)
    token = resolve_token(args.token, chain_id)
    if token == ETH:
        balance = int(client.w3.eth.get_balance(address))
    else:
        balance = int(client.get_token_balance(token))
    return {"chain_id": chain_id, "token": token, "balance": balance}


def cmd_approve(cfg: Config, args: argparse.Namespace) -> dict[str, Any]:
    check_broadcast_allowed(args.broadcast, cfg.private_key)
    client = _connect(cfg, args.version)
    chain_id = _chain_id(client)
    if args.broadcast:
        check_broadcast_chain_allowed(chain_id, cfg.allow_mainnet)
    token = resolve_token(args.token, chain_id)
    if not args.broadcast:
        return {
            "token": token,
            "note": "dry-run: pass --broadcast to send the approval tx",
        }
    client.approve(token)
    return {"token": token, "approved": True}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uniswap-agent", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--version",
        type=int,
        default=3,
        choices=[2, 3, 4],
        help="Uniswap protocol version (default: 3)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="chain, wallet, and connectivity info")

    p_quote = sub.add_parser("quote", help="quote amount out for an exact input")
    p_quote.add_argument("token_in")
    p_quote.add_argument("token_out")
    p_quote.add_argument("qty", type=int, help="input amount in wei/base units")
    p_quote.add_argument("--fee", type=int, default=3000)
    p_quote.add_argument("--tick-spacing", type=int, default=60, help="v4 only")

    p_swap = sub.add_parser("swap", help="swap exact input (dry-run by default)")
    p_swap.add_argument("token_in")
    p_swap.add_argument("token_out")
    p_swap.add_argument("qty", type=int, help="input amount in wei/base units")
    p_swap.add_argument("--fee", type=int, default=3000)
    p_swap.add_argument("--tick-spacing", type=int, default=60, help="v4 only")
    p_swap.add_argument("--slippage", type=float, default=0.01)
    p_swap.add_argument("--broadcast", action="store_true", help="sign and send")

    p_bal = sub.add_parser("balance", help="wallet balance of a token")
    p_bal.add_argument("token")

    p_appr = sub.add_parser("approve", help="approve the router for a token")
    p_appr.add_argument("token")
    p_appr.add_argument("--broadcast", action="store_true", help="sign and send")

    return parser


COMMANDS = {
    "status": cmd_status,
    "quote": cmd_quote,
    "swap": cmd_swap,
    "balance": cmd_balance,
    "approve": cmd_approve,
}


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = Config.from_env()
        result = COMMANDS[args.command](cfg, args)
    except SafetyError as e:
        payload = {"error": str(e), "kind": "safety"}
        print(json.dumps(payload) if args.json else f"refused: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001 — agents need the message, not a trace
        payload = {"error": f"{type(e).__name__}: {e}", "kind": "runtime"}
        print(json.dumps(payload) if args.json else f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
