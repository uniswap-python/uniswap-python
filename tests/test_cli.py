import json

from click.testing import CliRunner

from uniswap.cli import main


def test_hello_world():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "pricefeed",
            "0x6b175474e89094c44da98b954eedeac495271d0f",
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        ],
    )
    assert result.exit_code == 0

    # Will break when ETH breaks 10k
    assert 1000 < float(result.output) < 10_000


def test_get_token():
    runner = CliRunner()
    result = runner.invoke(
        main, ["token", "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"],
    )
    assert result.exit_code == 0
    out = json.loads(result.output.replace("'", '"'))
    assert out["symbol"] == "WETH"
    assert out["decimals"] == 18
