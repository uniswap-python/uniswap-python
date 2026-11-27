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
    def test_sepolia_allowed_without_arms(self):
        agent.check_broadcast_chain_allowed(11155111, False, False)

    def test_mainnet_refused_by_default(self):
        with pytest.raises(agent.SafetyError, match="not a known testnet"):
            agent.check_broadcast_chain_allowed(1, False, False)

    def test_mainnet_env_alone_refused(self):
        with pytest.raises(agent.SafetyError, match="--allow-mainnet"):
            agent.check_broadcast_chain_allowed(1, True, False)

    def test_mainnet_flag_alone_refused(self):
        with pytest.raises(agent.SafetyError, match="UNISWAP_AGENT_ALLOW_MAINNET"):
            agent.check_broadcast_chain_allowed(1, False, True)

    def test_mainnet_allowed_with_both_arms(self):
        agent.check_broadcast_chain_allowed(1, True, True)

    def test_unknown_chain_refused(self):
        with pytest.raises(agent.SafetyError):
            agent.check_broadcast_chain_allowed(56, True, False)


class TestVersionGate:
    def test_v3_on_sepolia_refused_deterministically(self):
        with pytest.raises(agent.SafetyError, match="mainnet-hardcoded"):
            agent.check_version_supported(3, 11155111)

    def test_v3_on_mainnet_ok(self):
        agent.check_version_supported(3, 1)

    def test_v3_on_polygon_ok(self):
        agent.check_version_supported(3, 137)

    def test_v4_on_sepolia_ok(self):
        agent.check_version_supported(4, 11155111)


class TestHumanize:
    class _FailingW3:
        class eth:  # noqa: N801 — mimics web3 attribute shape
            @staticmethod
            def contract(*a, **k):
                raise RuntimeError("no network in tests")

    def test_eth_gets_18_decimals_offline(self):
        out = {"qty_in": 1500000000000000000}
        agent._humanize(out, self._FailingW3(), {"qty_in": agent.ETH})
        assert out["decimals_qty_in"] == 18
        assert out["qty_in_human"] == "1.5"

    def test_unknown_decimals_skips_silently(self):
        out = {"amount_out": 123}
        token = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
        agent._humanize(out, self._FailingW3(), {"amount_out": token})
        assert "amount_out_human" not in out
        assert out["amount_out"] == 123


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


class TestTransactionResults:
    @staticmethod
    def config():
        return agent.Config("http://unused", agent.ETH, "test-key", False, 0.05)

    @pytest.mark.parametrize("quote", [10000, 10**30 + 123])
    def test_v4_encoded_minimum_matches_reported_limit(self, monkeypatch, quote):
        from types import SimpleNamespace
        from eth_abi import decode
        from hexbytes import HexBytes
        from uniswap import Uniswap4
        from uniswap.constants import v4_actions_abis

        client = object.__new__(Uniswap4)
        client.max_slippage = 0.01
        client.w3 = SimpleNamespace(eth=SimpleNamespace(chain_id=11155111))
        client.get_price_input = lambda *a, **k: quote
        client._get_tx_params = lambda **k: {}
        client.router = SimpleNamespace(
            functions=SimpleNamespace(
                execute=lambda commands, inputs, deadline: inputs[0]
            )
        )
        encoded = []

        def capture(payload, *a, **k):
            encoded.append(payload)
            return HexBytes("0x" + "11" * 32)

        client._build_and_send_tx = capture
        monkeypatch.setattr(agent, "_connect", lambda *a: client)
        args = agent.build_parser().parse_args(
            ["--version", "4", "swap", "ETH", "USDC", "1000", "--broadcast"]
        )
        result = agent.cmd_swap(self.config(), args)
        _, params = decode(["bytes", "bytes[]"], encoded[0])
        swap = decode(v4_actions_abis["SWAP_EXACT_IN_SINGLE"], params[0])[0]
        assert swap[3] == result["min_out"] == quote * 99 // 100

    @pytest.mark.parametrize("version", [2, 3])
    @pytest.mark.parametrize("status", [0, 1])
    def test_approval_receipt_status(self, monkeypatch, version, status):
        from types import SimpleNamespace
        from hexbytes import HexBytes

        tx_hash = HexBytes("0x" + "22" * 32)
        client = SimpleNamespace(
            w3=SimpleNamespace(eth=SimpleNamespace(chain_id=1)),
            approve=lambda token: {"status": status, "transactionHash": tx_hash},
        )
        monkeypatch.setattr(agent, "_connect", lambda *a: client)
        cfg = self.config()
        cfg.allow_mainnet = True
        args = agent.build_parser().parse_args(
            [
                "--version",
                str(version),
                "approve",
                "USDC",
                "--broadcast",
                "--allow-mainnet",
            ]
        )
        if status == 0:
            with pytest.raises(RuntimeError, match="reverted"):
                agent.cmd_approve(cfg, args)
        else:
            result = agent.cmd_approve(cfg, args)
            assert result["approved"] is True
            assert result["tx_hash"] == "0x" + "22" * 32
            assert result["status"] == "confirmed"

    def test_v4_approval_hash_is_submission_not_success(self, monkeypatch):
        from types import SimpleNamespace
        from hexbytes import HexBytes

        client = SimpleNamespace(
            w3=SimpleNamespace(eth=SimpleNamespace(chain_id=11155111)),
            approve=lambda token: HexBytes("0x" + "33" * 32),
        )
        monkeypatch.setattr(agent, "_connect", lambda *a: client)
        args = agent.build_parser().parse_args(
            ["--version", "4", "approve", "USDC", "--broadcast"]
        )
        result = agent.cmd_approve(self.config(), args)
        assert result["status"] == "submitted"
        assert result["tx_hash"] == "0x" + "33" * 32
        assert not result.get("approved")

    def test_v3_sepolia_approval_refused_without_sending(self, monkeypatch):
        from types import SimpleNamespace

        def forbidden(token):
            pytest.fail("unsupported approval must not be sent")

        client = SimpleNamespace(
            w3=SimpleNamespace(eth=SimpleNamespace(chain_id=11155111)),
            approve=forbidden,
        )
        monkeypatch.setattr(agent, "_connect", lambda *a: client)
        args = agent.build_parser().parse_args(["approve", "USDC", "--broadcast"])
        with pytest.raises(agent.SafetyError, match="mainnet-hardcoded"):
            agent.cmd_approve(self.config(), args)

    def test_v2_minimum_is_labelled_as_quote_estimate(self, monkeypatch):
        from types import SimpleNamespace

        client = SimpleNamespace(
            w3=SimpleNamespace(eth=SimpleNamespace(chain_id=11155111)),
            get_price_input=lambda *a, **k: 10000,
        )
        monkeypatch.setattr(agent, "_connect", lambda *a: client)
        args = agent.build_parser().parse_args(
            ["--version", "2", "swap", "ETH", "USDC", "1000"]
        )
        result = agent.cmd_swap(self.config(), args)
        assert "min_out" not in result
        assert result["estimated_min_out"] == 9900


@pytest.mark.parametrize(
    "amount,decimals,expected",
    [
        (1, 18, "0.000000000000000001"),
        (9007199254740993000001, 6, "9007199254740993.000001"),
        (42, 0, "42"),
        (1000000, 6, "1"),
    ],
)
def test_human_amount_preserves_base_units(monkeypatch, amount, decimals, expected):
    monkeypatch.setattr(agent, "_token_decimals", lambda *a: decimals)
    out = {"amount": amount}
    agent._humanize(out, None, {"amount": agent.ETH})
    assert out["amount_human"] == expected
