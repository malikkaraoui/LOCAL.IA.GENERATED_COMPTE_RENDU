.PHONY: help install install-dev test lint format clean run

help: ## Affiche l'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe les dépendances de production
	pip install -r requirements.txt

install-dev: ## Installe les dépendances de développement
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Lance les tests avec coverage
	pytest -v --cov=core --cov=rapport_orchestrator --cov-report=html --cov-report=term

test-fast: ## Lance les tests sans coverage
	pytest -v

lint: ## Vérifie le code avec ruff
	ruff check .
	ruff format --check .

format: ## Formate le code avec ruff et black
	ruff check --fix .
	ruff format .
	black .

type-check: ## Vérifie les types avec mypy
	mypy core/ rapport_orchestrator.py

clean: ## Nettoie les fichiers temporaires
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf .ruff_cache

run: ## Lance l'application Streamlit
	streamlit run app.py

run-debug: ## Lance l'application en mode debug
	streamlit run app.py --logger.level=debug

pre-commit: ## Lance les pre-commit hooks manuellement
	pre-commit run --all-files

update-version: ## Met à jour le fichier VERSION
	python tools/versioning/update_version.py

all: clean install-dev lint test ## Lance toutes les vérifications
