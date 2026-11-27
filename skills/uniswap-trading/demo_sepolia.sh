#!/usr/bin/env bash
# Quote and dry-run on Sepolia by default. DEMO_BROADCAST=1 sends one swap.
# Requires a dedicated Sepolia wallet with ETH for 0.001 ETH input plus gas.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT=(python3 "$SKILL_DIR/scripts/uniswap_agent.py" --json --version 2)
export PROVIDER="${SEPOLIA_RPC:-https://ethereum-sepolia-rpc.publicnode.com}"
QTY=1000000000000000

# Refuse another chain even if it is accepted by the general-purpose wrapper.
status=$("${AGENT[@]}" status)
python3 - "$status" <<'PYTHON'
import json
import sys

status = json.loads(sys.argv[1])
if status["chain_id"] != 11155111:
    sys.exit("This demo requires Sepolia (chain 11155111)")
print(json.dumps(status, indent=2))
PYTHON

# Native ETH uses the router's WETH address, with no ERC-20 approval needed.
echo "== Sepolia v2: quote and dry-run 0.001 ETH -> USDC =="
"${AGENT[@]}" quote ETH USDC "$QTY"
"${AGENT[@]}" swap ETH USDC "$QTY"

if [ "${DEMO_BROADCAST:-0}" != "1" ]; then
    echo "Dry-run complete. Set DEMO_BROADCAST=1 with a funded Sepolia wallet to send."
    exit 0
fi

: "${UNISWAP_AGENT_ADDRESS:?Set the dedicated Sepolia wallet address}"
: "${UNISWAP_AGENT_PRIVATE_KEY:?Set its private key securely in the environment}"
echo "== USDC balance before =="
"${AGENT[@]}" balance USDC
swap=$("${AGENT[@]}" swap ETH USDC "$QTY" --broadcast)
printf '%s\n' "$swap"

# A submitted hash alone is not a successful transaction. Never resend on timeout:
# inspect this hash on the same endpoint first.
python3 - "$swap" <<'PYTHON'
import json
import os
import sys
from web3 import Web3

swap = json.loads(sys.argv[1])
w3 = Web3(Web3.HTTPProvider(os.environ["PROVIDER"], request_kwargs={"timeout": 30}))
receipt = w3.eth.wait_for_transaction_receipt(swap["tx_hash"], timeout=180)
print(json.dumps({
    "chain_id": w3.eth.chain_id,
    "tx_hash": Web3.to_hex(receipt["transactionHash"]),
    "block_number": receipt["blockNumber"],
    "status": receipt["status"],
    "gas_used": receipt["gasUsed"],
}, indent=2))
if receipt["status"] != 1:
    sys.exit("Swap reverted; do not count this as a successful demo")
PYTHON

echo "== USDC balance after =="
"${AGENT[@]}" balance USDC
