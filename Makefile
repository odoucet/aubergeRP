.PHONY: run test lint

run:
	uvicorn aubergeRP.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/

lint:
	ruff check aubergeRP/ tests/
	mypy aubergeRP/
