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
