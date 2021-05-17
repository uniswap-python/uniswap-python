import json
import sys

from click.testing import CliRunner

from uniswap.cli import main


def print_result(result):
    print(result.stdout)
    print(result.stderr, file=sys.stderr)


def test_get_price():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["price", "weth", "dai"])
    print_result(result)
    assert result.exit_code == 0

    # Will break when ETH breaks 10k
    assert 1000 < float(result.stdout) < 10_000

    result = runner.invoke(main, ["price", "wbtc", "dai"])
    assert result.exit_code == 0

    # Will break when BTC breaks 100k
    assert 10_000 < float(result.stdout) < 100_000


def test_get_token():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["token", "weth"])
    print_result(result)
    assert result.exit_code == 0

    out = json.loads(result.stdout.replace("'", '"'))
    assert out["symbol"] == "WETH"
    assert out["decimals"] == 18


def test_get_tokendb():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["tokendb", "--metadata"])
    print_result(result)
    assert result.exit_code == 0
