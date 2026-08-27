---
name: uniswap-trading
description: Quote prices and execute Uniswap v2/v3/v4 swaps via uniswap-python. Use when asked to check on-chain token prices, get swap quotes, or trade tokens on Uniswap. Testnet-first — mainnet requires explicit opt-in. Do NOT use for CEX trading, fiat, or chains without Uniswap deployments.
---

# Uniswap Trading

Trade on Uniswap through [uniswap-python](https://github.com/uniswap-python/uniswap-python)
using a single CLI: `scripts/uniswap_agent.py`. All commands are safe to
explore — state-changing operations are **dry-run unless `--broadcast`** is
passed, and non-testnet chains are refused unless explicitly allowed.

## Setup

Requires `uniswap-python >= 0.8.0` (`pip install uniswap-python`) and:

```bash
export PROVIDER=https://ethereum-sepolia-rpc.publicnode.com  # any JSON-RPC endpoint
export UNISWAP_AGENT_ADDRESS=0xYourWallet                    # for balances/swaps
export UNISWAP_AGENT_PRIVATE_KEY=0x...                       # ONLY for --broadcast
```

Never echo `UNISWAP_AGENT_PRIVATE_KEY` or write it to disk. Read-only
commands (status, quote) work with just `PROVIDER`.

## Commands

```bash
SKILL_DIR=$(dirname "$0")  # or the directory containing this SKILL.md

# Connectivity + wallet overview
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json status

# Quote: how much USDC for 0.01 WETH? (amounts in wei/base units)
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json quote WETH USDC 10000000000000000

# Dry-run swap (prints plan: quote, min-out after slippage; sends nothing)
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json swap WETH USDC 10000000000000000

# Real swap on testnet (requires key; approve the router first for ERC-20 input)
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json approve WETH --broadcast
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json swap WETH USDC 10000000000000000 --broadcast

# Uniswap v4 (single-hop; pool identified by fee + tick spacing)
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 4 \
    quote WETH USDC 10000000000000000 --fee 3000 --tick-spacing 60
```

On Sepolia the symbols `ETH`, `WETH`, `USDC` resolve automatically; on other
chains pass 0x token addresses.

## Safety rules (enforced by the CLI, exit code 2 on refusal)

1. Read-only commands (status, quote, balance) work on any chain. Broadcasting
   is limited to known testnets (Sepolia, Arbitrum/Base/Optimism Sepolia)
   unless `UNISWAP_AGENT_ALLOW_MAINNET=1` is set. Never set that variable
   yourself — ask the human operator.
2. Nothing is signed or sent without `--broadcast`.
3. Slippage above 5% is refused (`UNISWAP_AGENT_MAX_SLIPPAGE` to override).

## Current network coverage (uniswap-python 0.8.0)

Quotes work today on the ~18 production networks configured in the library
(mainnet, base, arbitrum, optimism, polygon, ...). Sepolia broadcasting is
pending library-side enablement: the v3 client hardcodes mainnet contract
addresses, and the v4 address maps don't include Sepolia yet. Until then, use
mainnet for read-only quoting and expect `status` (but not `quote`/`swap`) to
work on Sepolia.

## Interpreting output

With `--json`, results are a single JSON object on stdout. Errors go to
stderr as `{"error": ..., "kind": "safety"|"runtime"}`; exit code 2 means a
safety guard refused (do not retry with workarounds — report to the human),
1 means a runtime error (bad pool, no liquidity, RPC down — often worth one
retry or a different fee tier).

Amounts are integers in the token's base units (wei for ETH/WETH: 1 ETH =
10^18). Convert before showing humans.
