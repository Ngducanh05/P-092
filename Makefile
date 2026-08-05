.PHONY: run test lint format typecheck check clean

run:
	python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest tests -v

lint:
	python -m ruff check src tests scripts alembic

format:
	python -m ruff format src tests scripts alembic

typecheck:
	mypy src/

scan:
	python scripts/scan_secrets.py

check: lint scan test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
