"""Offline tests for the agent CLI's safety gates and argument surface."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent / "scripts" / "uniswap_agent.py"
_spec = importlib.util.spec_from_file_location("uniswap_agent", _SCRIPT)
agent = importlib.util.module_from_spec(_spec)
sys.modules["uniswap_agent"] = agent
_spec.loader.exec_module(agent)


class TestBroadcastChainGate:
    def test_sepolia_allowed(self):
        agent.check_broadcast_chain_allowed(11155111, allow_mainnet=False)

    def test_mainnet_refused_by_default(self):
        with pytest.raises(agent.SafetyError, match="not a known testnet"):
            agent.check_broadcast_chain_allowed(1, allow_mainnet=False)

    def test_mainnet_allowed_with_optin(self):
        agent.check_broadcast_chain_allowed(1, allow_mainnet=True)

    def test_unknown_chain_refused(self):
        with pytest.raises(agent.SafetyError):
            agent.check_broadcast_chain_allowed(56, allow_mainnet=False)


class TestSlippageGate:
    def test_default_ok(self):
        agent.check_slippage(0.01, agent.DEFAULT_MAX_SLIPPAGE)

    def test_above_ceiling_refused(self):
        with pytest.raises(agent.SafetyError, match="slippage"):
            agent.check_slippage(0.10, agent.DEFAULT_MAX_SLIPPAGE)

    def test_zero_refused(self):
        with pytest.raises(agent.SafetyError):
            agent.check_slippage(0.0, agent.DEFAULT_MAX_SLIPPAGE)

    def test_raised_ceiling(self):
        agent.check_slippage(0.10, 0.15)


class TestBroadcastGate:
    def test_dry_run_needs_no_key(self):
        agent.check_broadcast_allowed(False, None)

    def test_broadcast_without_key_refused(self):
        with pytest.raises(agent.SafetyError, match="broadcast"):
            agent.check_broadcast_allowed(True, None)

    def test_broadcast_with_key_ok(self):
        agent.check_broadcast_allowed(True, "0xdeadbeef")


class TestTokenResolution:
    def test_address_passthrough(self):
        addr = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
        assert agent.resolve_token(addr, 11155111) == addr

    def test_sepolia_symbols(self):
        assert agent.resolve_token("weth", 11155111).startswith("0x")
        assert agent.resolve_token("USDC", 11155111).startswith("0x")
        assert agent.resolve_token("ETH", 11155111) == agent.ETH

    def test_unknown_symbol_refused(self):
        with pytest.raises(agent.SafetyError, match="unknown token symbol"):
            agent.resolve_token("DOGE", 11155111)


class TestCLI:
    @pytest.mark.parametrize(
        "address",
        [
            None,
            "not-an-address",
            "0x0000000000000000000000000000000000000000",
        ],
    )
    def test_balance_rejects_invalid_address_before_connecting(
        self, monkeypatch, address
    ):
        monkeypatch.setenv("PROVIDER", "http://localhost:1")
        if address is None:
            monkeypatch.delenv("UNISWAP_AGENT_ADDRESS", raising=False)
        else:
            monkeypatch.setenv("UNISWAP_AGENT_ADDRESS", address)
        assert agent.main(["balance", "ETH"]) == 2

    def test_parser_covers_all_commands(self):
        parser = agent.build_parser()
        for command in agent.COMMANDS:
            args = parser.parse_args(
                [command] + (["ETH"] if command in ("balance", "approve") else [])
                if command != "quote" and command != "swap"
                else [command, "WETH", "USDC", "1000"]
            )
            assert args.command == command

    def test_missing_provider_is_safety_error(self, monkeypatch):
        monkeypatch.delenv("PROVIDER", raising=False)
        monkeypatch.delenv("UNISWAP_AGENT_RPC", raising=False)
        assert agent.main(["--json", "status"]) == 2

    def test_broadcast_without_key_exits_2(self, monkeypatch):
        monkeypatch.setenv("PROVIDER", "http://localhost:1")
        monkeypatch.delenv("UNISWAP_AGENT_PRIVATE_KEY", raising=False)
        assert agent.main(["swap", "WETH", "USDC", "1000", "--broadcast"]) == 2
