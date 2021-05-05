import json

from click.testing import CliRunner

from uniswap.cli import main


def test_get_price():
    runner = CliRunner()
    result = runner.invoke(main, ["price", "dai", "weth"])
    assert result.exit_code == 0

    # Will break when ETH breaks 10k
    assert 1000 < float(result.output) < 10_000

    result = runner.invoke(main, ["price", "dai", "wbtc"])
    assert result.exit_code == 0

    # Will break when BTC breaks 100k
    assert 10_000 < float(result.output) < 100_000


def test_get_token():
    runner = CliRunner()
    result = runner.invoke(main, ["token", "weth"])
    assert result.exit_code == 0
    out = json.loads(result.output.replace("'", '"'))
    assert out["symbol"] == "WETH"
    assert out["decimals"] == 18


def test_get_tokendb():
    runner = CliRunner()
    result = runner.invoke(main, ["tokendb", "--metadata"])
    assert result.exit_code == 0
