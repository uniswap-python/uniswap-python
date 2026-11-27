# uniswap-trading agent skill

An AI-agent integration for uniswap-python: [SKILL.md](SKILL.md) plus a
subprocess CLI, `scripts/uniswap_agent.py --json`. Agents can quote, inspect
balances, and prepare swaps. Transactions require an explicit `--broadcast`;
production-chain broadcasts additionally require both mainnet opt-ins.

## Install

Use a repository checkout containing this directory and install the library
from its root with `python3 -m pip install .` in a virtual environment. The
Python wheel does not install the skill files.

- **Claude Code:** symlink or copy this directory into
  `~/.claude/skills/uniswap-trading` or a project's `.claude/skills/`.
- **gptme:** add this directory to the configured lessons/skills path.
- **Other agents:** invoke the CLI as a subprocess. Stdout contains a JSON
  object; errors go to stderr. Exit codes: 0 success, 1 runtime error,
  2 safety refusal.

## Sepolia demo

From this directory, with the virtual environment active:

```bash
./demo_sepolia.sh
```

This checks chain ID 11155111, quotes 0.001 native ETH to USDC through v2,
and prints a dry-run swap plan. It needs no wallet or private key.

To send the same swap, provision a **dedicated Sepolia-only wallet** with
0.001 testnet ETH plus gas. Set `UNISWAP_AGENT_ADDRESS` and its matching
`UNISWAP_AGENT_PRIVATE_KEY` securely in the environment, then explicitly run:

```bash
DEMO_BROADCAST=1 ./demo_sepolia.sh
```

The script prints balances before and after, the transaction hash, and the
mined receipt's status, block number, and gas used. A reverted transaction
exits nonzero. If waiting for the receipt times out, inspect the printed hash
on the same RPC before retrying; do not blindly send another swap.
`SEPOLIA_RPC` overrides the default public endpoint.

### Why v2 works without the v3/v4 library changes

The existing library configures this Sepolia v2 deployment:

| Contract | Address |
|---|---|
| Router | `0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008` |
| Factory | `0x7E0987E5b3a30e3f2828572Bb659A548460a3003` |
| Router's WETH | `0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9` |
| USDC | `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` |
| WETH/USDC pair | `0x6c1bBfD6330CA6c3f27C29b3a3330dB2B6B0980a` |

These are the **library-configured contracts**, not the separate v2 deployment
currently listed in the [Uniswap deployment documentation](https://developers.uniswap.org/docs/protocols/v2/deployments).
Their router/factory/WETH linkage and positive quote were checked directly on
Sepolia on 2026-11-27. This demo uses only testnet assets.

Use native `ETH` input: the library resolves WETH from the router and needs
no approval transaction. The skill's `WETH` alias points to the separate v3
WETH deployment; substituting that alias changes the route. The previous demo
used v3 on Sepolia, which the wrapper deliberately refuses. v3's address/ABI
work and v4's deployment/pool work remain separate from this v2 demonstration.

### Fork replay and acceptance boundary

Run a local Sepolia fork bound to loopback:

```bash
anvil --fork-url https://ethereum-sepolia-rpc.publicnode.com \
  --chain-id 11155111 --host 127.0.0.1 --port 18574
```

Use one of that fork's funded development accounts in the environment, then:

```bash
SEPOLIA_RPC=http://127.0.0.1:18574 DEMO_BROADCAST=1 ./demo_sepolia.sh
```

Never use a public Anvil development key for a funded public-chain wallet.
A local fork shares Sepolia's chain ID, so chain ID alone does **not** establish
that a transaction was published on Sepolia.

Replay on 2026-11-27, library master `16614e1cad120ac8836d6c549f33685cc48491fe`:

- Unmodified wrapper trading path, v2 native ETH input: 1,000,000,000,000,000 wei.
- Receipt status 1, gas used 113,656, local block 12,219,864.
- USDC base-unit balance: 65,200,247 → 110,303,356; received 45,103,109.
- **Local fork hash only:**
  `0x8f5169e7e540933f7943400edd399d84cb43a329b70a12e64ce9e4f1ba333358`.

The public Sepolia transaction is still outstanding. To close D3, record the
public-network transaction hash, successful receipt and token transfer, exact
source revision, and command used. The fork hash above is implementation
verification, **not** that acceptance receipt.

## Tests and prior dogfood

```bash
python3 -m pytest skills/uniswap-trading/tests/ -q
```

The 41 offline tests cover safety gates, CLI results, exact amount formatting,
and the real v4 calldata minimum. The
repository's default pytest discovery includes these tests. The demo additionally
needs the live or forked contract state described above.

Prior dogfood (2026-08-27): Gordon installed the skill and verified mainnet
v3/v4 and Polygon v3 quoting. His corrections are included: human-readable
amounts, deterministic v3-testnet refusal, and double-armed mainnet broadcast.
This establishes trial use; production trading adoption is not claimed.
