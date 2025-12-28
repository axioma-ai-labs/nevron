DIRS_PYTHON := src tests

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo
	@echo "Targets:"
	@echo "  help            This help (default target)"
	@echo "  deps            Install all dependencies"
	@echo "  format          Format source code"
	@echo "  lint            Run lint checks"
	@echo "  run             Run the agent"
	@echo "  test            Run tests"
	@echo "  test-ci         Run tests in CI"
	@echo "  docs            Generate docs"
	@echo
	@echo "Dashboard:"
	@echo "  api             Run the FastAPI backend (port 8000)"
	@echo "  dashboard       Run the Svelte dashboard (port 5173)"
	@echo "  dashboard-build Build the dashboard for production"
	@echo "  dashboard-deps  Install dashboard dependencies"
	@echo "  dev             Run both API and dashboard (requires tmux)"
	@echo
	@echo "Docker:"
	@echo "  docker-up       Start all services with Docker Compose"
	@echo "  docker-down     Stop all Docker services"
	@echo "  docker-build    Build Docker images"
	@echo "  docker-logs     View Docker container logs"

.PHONY: deps
deps:
	poetry install --with dev

.PHONY: format
format:	\
	format-ruff \
	format-isort

.PHONY: format-ruff
format-ruff:
	poetry run ruff format --line-length 100 $(DIRS_PYTHON)

.PHONY: format-isort
format-isort:
	poetry run isort --profile=black --line-length 100 $(DIRS_PYTHON)

.PHONY: lint
lint: \
	lint-ruff \
	lint-isort \
	lint-mypy

.PHONY: lint-ruff
lint-ruff:
	poetry run ruff check --line-length 100 $(DIRS_PYTHON)

.PHONY: lint-isort
lint-isort:
	poetry run isort --profile=black --line-length 100 --check-only --diff $(DIRS_PYTHON)

.PHONY: lint-mypy
lint-mypy:
	poetry run mypy --check-untyped-defs $(DIRS_PYTHON)

.PHONY: run
run:
	poetry run python -m src.main

.PHONY: test
test:
	poetry run pytest \
		--cov-report term-missing \
		--cov-report lcov \
		--cov=src \
		tests/

.PHONY: test-ci
test-ci:
	poetry run pytest \
		--cov-report term-missing \
		--cov-report lcov \
		--cov=src \
		tests/

.PHONY: docs
docs:
	poetry run mkdocs serve

# =============================================================================
# Dashboard Commands
# =============================================================================

.PHONY: api
api:
	poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: dashboard-deps
dashboard-deps:
	cd dashboard && npm install

.PHONY: dashboard
dashboard:
	cd dashboard && npm run dev

.PHONY: dashboard-build
dashboard-build:
	cd dashboard && npm run build

.PHONY: dev
dev:
	@echo "Starting API and Dashboard in parallel..."
	@echo "API will be available at http://localhost:8000"
	@echo "Dashboard will be available at http://localhost:5173"
	@echo "Press Ctrl+C to stop both services"
	@trap 'kill 0' INT; \
		poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 & \
		cd dashboard && npm run dev & \
		wait

# =============================================================================
# Docker Commands
# =============================================================================

.PHONY: docker-build
docker-build:
	docker-compose build

.PHONY: docker-up
docker-up:
	docker-compose up -d

.PHONY: docker-down
docker-down:
	docker-compose down

.PHONY: docker-logs
docker-logs:
	docker-compose logs -f

# .PHONY: jupyternotebook
# jupyternotebook:
# 	pipenv run \
# 		jupyter notebook

# .PHONY: jupyterlab
# jupyterlab:
# 	cp src/bench/results_analysis.ipynb tmp.ipynb && \
# 	PYTHON=. pipenv run \
# 		jupyter lab \
# 			--ip=0.0.0.0 --allow-root --NotebookApp.custom_display_url=http://127.0.0.1:8888 \
# 			tmp.ipynb
