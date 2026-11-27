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

Use a checkout containing `skills/uniswap-trading/`, then install the library
from that checkout with `python3 -m pip install .`. The skill files live in the
repository; installing the Python wheel alone does not install this directory.
Until merged, use the branch linked from the D3 pull request.

Then:

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

# Connectivity + wallet overview on Sepolia
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 2 status

# Sepolia quote and dry-run: 0.001 native ETH to USDC, no approval needed
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 2 quote ETH USDC 1000000000000000
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 2 swap ETH USDC 1000000000000000

# Send only when the user authorizes this testnet transaction and funds the wallet
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 2 swap ETH USDC 1000000000000000 --broadcast

# Uniswap v4 on a supported production network (set PROVIDER accordingly)
# Single-hop; pool identified by fee + tick spacing
python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 4 \
    quote WETH USDC 10000000000000000 --fee 3000 --tick-spacing 60
```

On Sepolia use native `ETH` for this v2 demo. The `WETH` alias names the v3
deployment, which differs from the v2 router's WETH; do not substitute it.
`USDC` resolves automatically. On other chains pass token addresses when an
alias is unavailable.

## Safety rules (enforced by the CLI, exit code 2 on refusal)

1. Read-only commands (status, quote, balance) work on any chain. Broadcasting
   outside known testnets (Sepolia, Arbitrum/Base/Optimism Sepolia) is
   **double-armed**: it requires BOTH `UNISWAP_AGENT_ALLOW_MAINNET=1` in the
   environment AND `--allow-mainnet` on the specific call. Never set the
   environment arm yourself — that is the human operator's standing decision;
   the flag is your per-call confirmation.
2. Nothing is signed or sent without `--broadcast`.
3. Slippage above 5% is refused (`UNISWAP_AGENT_MAX_SLIPPAGE` to override).
4. v3 on testnets is refused deterministically (exit 2) — the library's v3
   contracts are mainnet-hardcoded; use v2 with native ETH for Sepolia.

## Sepolia demo

Run `./demo_sepolia.sh` from this directory for a quote and dry-run. With a
funded, dedicated Sepolia wallet, `DEMO_BROADCAST=1 ./demo_sepolia.sh` sends
one v2 native-ETH swap and checks its mined receipt. See [README.md](README.md)
for the tested deployment, fork replay, and public-testnet acceptance evidence.

The v3/v4 Sepolia library gaps do not block this v2 path. Protocol/network
support still depends on the library's contracts and available liquidity;
an accepted chain ID alone does not establish support.

## Interpreting output

With `--json`, results are a single JSON object on stdout. Errors go to
stderr as `{"error": ..., "kind": "safety"|"runtime"}`; exit code 2 means a
safety guard refused (do not retry with workarounds — report to the human),
1 means a runtime error (bad pool, no liquidity, RPC down — often worth one
retry or a different fee tier).

Amounts are integers in the token's base units (wei for ETH/WETH: 1 ETH =
10^18). Where token decimals are readable on-chain, outputs also carry
advisory `<field>_human` (decimal string) and `decimals_<field>` companions —
prefer those when showing humans, but treat the integer fields as the source
of truth (the human fields are omitted when a decimals lookup fails).

A broadcast result contains a submitted hash, not proof of success. Check the
receipt on the same chain before reporting completion or retrying. A receipt
timeout means pending/unknown; do not send a second swap automatically.
