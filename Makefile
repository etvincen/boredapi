.PHONY: install dev test lint format clean

install:
	poetry install --no-root

dev:
	./scripts/dev.sh

test:
	./scripts/test.sh

lint:
	poetry run ruff src tests
	poetry run mypy src tests

format:
	poetry run black src tests
	poetry run isort src tests

clean:
	rm -rf dist/
	rm -rf .coverage
	rm -rf .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
