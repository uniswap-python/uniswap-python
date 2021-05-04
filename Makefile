.PHONY: test typecheck lint precommit docs

test:
	poetry run pytest -v --cov=uniswap --cov-report html

typecheck:
	poetry run mypy --pretty

lint:
	poetry run flake8

precommit:
	make typecheck
	make lint
	make test

docs:
	cd docs/ && make html
