#!/usr/bin/env bash
# Demo for the uniswap-trading agent skill.
#
# Part 1 (works today): read-only quoting against mainnet — no key needed.
# Part 2 (Sepolia broadcast): blocked on library-side Sepolia enablement
#   (v3 hardcodes mainnet contracts; v4 address maps lack Sepolia). Once
#   uniswap-python configures Sepolia, run with:
#   UNISWAP_AGENT_ADDRESS=0x... UNISWAP_AGENT_PRIVATE_KEY=0x... DEMO_BROADCAST=1
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="python3 $SKILL_DIR/scripts/uniswap_agent.py --json"

MAINNET_RPC="${MAINNET_RPC:-https://ethereum-rpc.publicnode.com}"
SEPOLIA_RPC="${SEPOLIA_RPC:-https://ethereum-sepolia-rpc.publicnode.com}"

# 0.001 WETH in wei
QTY=1000000000000000

echo "== [mainnet, read-only] status =="
PROVIDER=$MAINNET_RPC $AGENT status

echo "== [mainnet, read-only] v3 quote: 0.001 WETH -> USDC =="
PROVIDER=$MAINNET_RPC $AGENT quote WETH USDC "$QTY"

echo "== [mainnet, read-only] v4 quote: 0.001 ETH -> USDC =="
PROVIDER=$MAINNET_RPC $AGENT --version 4 quote ETH USDC "$QTY" --fee 500 --tick-spacing 10

echo "== [mainnet] dry-run swap plan (nothing is sent) =="
PROVIDER=$MAINNET_RPC $AGENT swap WETH USDC "$QTY"

echo "== [sepolia] status =="
PROVIDER=$SEPOLIA_RPC $AGENT status

if [ "${DEMO_BROADCAST:-0}" = "1" ]; then
    echo "== [sepolia] approve WETH (broadcast) =="
    PROVIDER=$SEPOLIA_RPC $AGENT approve WETH --broadcast
    echo "== [sepolia] swap 0.001 WETH -> USDC (broadcast) =="
    PROVIDER=$SEPOLIA_RPC $AGENT swap WETH USDC "$QTY" --broadcast
else
    echo "(Sepolia swap skipped: needs DEMO_BROADCAST=1, a funded key, and"
    echo " library-side Sepolia contract enablement — see README status list)"
fi
