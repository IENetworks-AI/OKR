# OKR Project Makefile

.PHONY: help install test lint format clean setup-dev run-ai run-data

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements.txt
	pip install -e .
	pre-commit install

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=. --cov-report=html

lint:  ## Run linting
	flake8 .
	mypy .

format:  ## Format code
	black .
	isort .

clean:  ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

setup-dev:  ## Setup development environment
	python -m venv venv
	@echo "Activate with: source venv/bin/activate"

run-ai:  ## Run AI inference API
	uvicorn ai.src.inference.main:app --reload --host 0.0.0.0 --port 8000

run-tests:  ## Run all tests
	pytest ai/tests/ data/tests/ shared/tests/

docker-build:  ## Build Docker image
	docker build -t okr-project .

docker-run:  ## Run Docker container
	docker run -p 8000:8000 okr-project