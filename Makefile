.PHONY: help install run test fuzz lint format audit a11y ci migrate backup restore docker-up docker-down clean

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install python dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

run: ## Run the FastAPI application locally
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

test: ## Run the test suite with coverage (Schemathesis fuzz hariç — `make fuzz`)
	SKIP_SCHEMATHESIS=1 pytest tests/ --cov=app --cov-report=term-missing

fuzz: ## Schemathesis property-based API fuzz (read + write); CI'da ayrı job
	pytest tests/test_schemathesis_fuzz.py -v --no-cov

lint: ## Run ruff linter
	ruff check .

format: ## Run ruff formatter
	ruff format .

audit: ## Security audit suite (ruff + bandit + pip-audit) — CI security.yml parity
	@echo "▶ ruff (lint + format check)" && ruff check . && ruff format --check .
	@echo "\n▶ bandit (Python source security, medium+)" && \
		python -m bandit -r app/ -f screen --severity-level medium --confidence-level medium
	@echo "\n▶ pip-audit (dependency CVE)" && \
		python -m pip_audit --requirement requirements.txt --strict

a11y: ## Run axe-core a11y scan against running dashboard (frontend npm script)
	cd frontend && npm run a11y:axe

ci: lint test audit ## Local CI parity (lint + test + audit)

migrate: ## Run database migrations
	alembic upgrade head

backup: ## Veritabanını yedekle (SQLite/PostgreSQL; ./backups/ altına)
	@./scripts/backup.sh

restore: ## Veritabanını geri yükle (BACKUP=path/to/file kullan)
	@if [ -z "$(BACKUP)" ]; then \
		echo "Kullanım: make restore BACKUP=./backups/sfdap_YYYYMMDD.db"; \
		ls -lh ./backups/sfdap_* 2>/dev/null | tail -5 || echo "(yedek yok)"; \
		exit 1; \
	fi
	@./scripts/restore.sh "$(BACKUP)"

docker-up: ## Start the application using Docker
	docker-compose up -d

docker-down: ## Stop the Docker application
	docker-compose down

clean: ## Remove python cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .coverage
