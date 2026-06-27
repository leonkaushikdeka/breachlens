.PHONY: install dev test cov lint format type train app api figures clean

install:
	pip install -e .

dev:
	pip install -e ".[dev,app,api]"

test:
	pytest -q

cov:
	pytest --cov=breachlens --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

type:
	mypy breachlens

train:
	python -m breachlens.cli train

app:
	streamlit run streamlit_app.py

api:
	uvicorn api.main:app --reload

figures:
	python scripts/generate_figures.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
