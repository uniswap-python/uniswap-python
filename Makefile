.PHONY: test typecheck lint precommit docs

test:
	poetry run pytest -v --tb=auto --maxfail=20 --cov=uniswap --cov-report html --cov-report term --cov-report xml

typecheck:
	poetry run mypy --pretty

lint:
	poetry run ruff check uniswap

format:
	poetry run ruff format uniswap

format-abis:
	npx prettier --write --parser=json uniswap/assets/*/*.abi

precommit:
	make typecheck
	make lint
	make test

docs:
	cd docs/ && make html
