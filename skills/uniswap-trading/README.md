# uniswap-trading agent skill

An AI-agent integration for uniswap-python: a [SKILL.md](SKILL.md) following
the [Anthropic skill format](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/skills)
plus a subprocess-friendly CLI (`scripts/uniswap_agent.py`) that any agent
framework can call.

## Install into an agent

- **Claude Code**: symlink or copy this directory to `~/.claude/skills/uniswap-trading`
  (or `.claude/skills/uniswap-trading` in a project). The skill loads on demand.
- **gptme**: add this directory to a configured lessons/skills path; the
  `description` frontmatter drives matching.
- **Anything else** (LangChain, OpenAI tools, MCP): wrap
  `scripts/uniswap_agent.py --json <command>` as a subprocess tool. The CLI is
  the integration surface — stdout is one JSON object, exit codes are stable
  (0 ok, 1 runtime error, 2 safety refusal).

## Demo

`./demo_sepolia.sh` runs read-only mainnet quotes (v3 + v4, verified working
against public RPCs) plus Sepolia status, and — once the library gains Sepolia
support — a real Sepolia swap with `DEMO_BROADCAST=1` and a funded key.

## Tests

```bash
python3 -m pytest skills/uniswap-trading/tests/ -q
```

No network needed — tests cover the safety gates and argument surface.

## Status

Skeleton (grant deliverable D3 groundwork). Verified working: v3 + v4
mainnet quotes over public RPCs, dry-run swap plans, all safety gates.
Cross-agent dogfood (Gordon, 2026-08-27): install clean, mainnet v3/v4 +
Polygon v3 quoting verified; his four corrections are folded in — human
amounts in JSON, deterministic v3-testnet refusal, branch-install setup
docs, double-armed mainnet broadcast (`UNISWAP_AGENT_ALLOW_MAINNET=1` +
`--allow-mainnet`).
TODO before production:

- [ ] **Sepolia enablement in the library** (blocks the D3 testnet tx demo):
      v3 hardcodes the mainnet quoter/router in `uniswap.py`; the v4 maps in
      `constants.py` have no `"sepolia"` entries. Official Sepolia v4
      deployments (PoolManager `0xE03A1074c86CFeDd5C142C4F04F1a1536e203543`,
      UniversalRouter `0x3A9D48AB9751398BbFa63ad67599Bb04e4BdF98b`, V4Quoter
      `0x61b3f2011a92d183c7dbadbda940a7555ccf9227`, StateView
      `0xe1dd9c3fa50edb962e442f60dfbc432e24537e4c`, PositionManager
      `0x429ba70129df741B2Ca2a85BC3A2a3328e5c09b4`, Permit2
      `0x000000000022D473030F116dDEE9F6B43aC78BA3`) cover 6 of the 8
      contracts `Uniswap4.__init__` requires — `position_descriptor` and
      `reserves_lens` still need deployments/addresses.
- [ ] v4 route/multi-hop support in `swap` (currently single-hop PoolKey)
- [ ] Wire tests into repo CI
- [ ] MCP server wrapper (optional distribution surface)
- [ ] Publish demo transcript + testnet tx hash in docs
