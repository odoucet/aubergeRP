.PHONY: run test lint

run:
	python -m uvicorn aubergeRP.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest tests/

lint:
	python -m ruff check aubergeRP/ tests/
	python -m mypy aubergeRP/
