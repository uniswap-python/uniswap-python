import os
import sys

import pytest
from click.testing import CliRunner

from uniswap.cli import main


def print_result(result):
    print(result)
    print(result.stdout.strip())
    print(result.stderr.strip(), file=sys.stderr)


def test_get_price():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["price", "eth", "dai"])
    print_result(result)
    assert result.exit_code == 0

    # Will break when ETH breaks 10k
    assert 1000 < float(result.stdout) < 10_000


def test_get_price_stables():
    """Tests that decimals are handled correctly."""
    if os.getenv("UNISWAP_VERSION") == "1":
        pytest.skip("Not supported in v1")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["price", "dai", "usdc"])
    print_result(result)
    assert result.exit_code == 0

    # Will break if peg is lost
    assert 0.9 < float(result.stdout) < 1.1


def test_get_token():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["token", "weth"])
    print_result(result)
    assert result.exit_code == 0


def test_get_tokendb():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["tokendb", "--metadata"])
    print_result(result)
    assert result.exit_code == 0
