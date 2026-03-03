.PHONY: lint format typecheck test all

lint:
	ruff check bot/ commands/ tests/
format:
	ruff format bot/ commands/ tests/
typecheck:
	mypy bot/ commands/
test:
	pytest --cov=bot --cov=commands --cov-report=term-missing
all: lint typecheck test
