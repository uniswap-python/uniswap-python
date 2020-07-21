.PHONY: test buy-testassets typecheck lint precommit

test:
	poetry run pytest --cov=uniswap

buy-testassets:
	poetry run python3 -m uniswap.uniswap

typecheck:
	poetry run mypy

lint:
	poetry run flake8

precommit:
	make typecheck
	make lint
	make test
