# AINarratives Project Makefile
# Comprehensive project management for UV-based Python project

# Colors for pretty output
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
BLUE   := $(shell tput -Txterm setaf 4)
RED    := $(shell tput -Txterm setaf 1)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

TARGET_MAX_CHAR_NUM=25

# Project variables
PACKAGE_NAME = pain_narratives
SRC_DIR = src
TESTS_DIR = tests
SCRIPTS_DIR = scripts

## Show help
help:
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo '${BLUE}AINarratives Project Management${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

# Environment Setup
## Install project dependencies
install:
	@echo "${BLUE}Installing project dependencies...${RESET}"
	uv sync

## Install development dependencies
dev-install: install
	@echo "${BLUE}Installing development dependencies...${RESET}"
	uv sync --group dev

## Install analysis dependencies
analysis-install: install
	@echo "${BLUE}Installing analysis dependencies...${RESET}"
	uv sync --extra analysis

## Complete development setup
setup: dev-install
	@echo "${BLUE}Setting up development environment...${RESET}"
	@echo "${GREEN}Development environment ready!${RESET}"

# Code Quality
## Run code formatters (black + isort)
format:
	@echo "${BLUE}Formatting code with black and isort...${RESET}"
	uv run black $(SRC_DIR)/ $(TESTS_DIR)/ $(SCRIPTS_DIR)/
	uv run isort $(SRC_DIR)/ $(TESTS_DIR)/ $(SCRIPTS_DIR)/
	@echo "${GREEN}Code formatting complete!${RESET}"

## Run linting with flake8
lint:
	@echo "${BLUE}Running flake8 linting...${RESET}"
	uv run python -m flake8 $(SRC_DIR)/ $(TESTS_DIR)/ $(SCRIPTS_DIR)/

## Run type checking with mypy
typecheck:
	@echo "${BLUE}Running mypy type checking...${RESET}"
	uv run mypy $(SRC_DIR)/

## Run all code quality checks
check: format lint typecheck
	@echo "${GREEN}All code quality checks passed!${RESET}"

# Testing
## Run all tests
test:
	@echo "${BLUE}Running tests with pytest...${RESET}"
	uv run pytest $(TESTS_DIR)/ -v

## Run tests with coverage
test-cov:
	@echo "${BLUE}Running tests with coverage...${RESET}"
	uv run pytest $(TESTS_DIR)/ -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term

## Run tests in watch mode
test-watch:
	@echo "${BLUE}Running tests in watch mode...${RESET}"
	uv run pytest $(TESTS_DIR)/ -f

# Application
## Run Streamlit application
app:
	@echo "${BLUE}Starting Streamlit application...${RESET}"
	uv run streamlit run $(SCRIPTS_DIR)/run_app.py

## Run experiments
experiments:
	@echo "${BLUE}Running AINarratives experiments...${RESET}"
	uv run run-experiments --models gpt-5-mini --temperatures 0.0 --repetitions 1

## Run custom experiment script
run-script:
	@echo "${BLUE}Running custom script...${RESET}"
	uv run python $(SCRIPTS_DIR)/run_app.py

# Database
## Initialize database
db-init:
	@echo "${BLUE}Initializing database...${RESET}"
	uv run python $(SCRIPTS_DIR)/setup/init_database.py

## Run database migrations
db-migrate:
	@echo "${BLUE}Running database migrations...${RESET}"
	cd $(SRC_DIR)/$(PACKAGE_NAME)/db && uv run alembic upgrade head

## Create new migration
db-migration:
	@echo "${BLUE}Creating new database migration...${RESET}"
	@read -p "Enter migration message: " message; \
	cd $(SRC_DIR)/$(PACKAGE_NAME)/db && uv run alembic revision --autogenerate -m "$$message"

# Jupyter
## Setup Jupyter kernel for project
jupyter-setup:
	@echo "${BLUE}Setting up Jupyter kernel...${RESET}"
	uv run python -m ipykernel install --user --name "pain-narratives" --display-name "Python (AINarratives)"
	@echo "${GREEN}Jupyter kernel 'Python (AINarratives)' installed successfully!${RESET}"

## Start Jupyter notebook
notebook:
	@echo "${BLUE}Starting Jupyter notebook server...${RESET}"
	uv run jupyter notebook

## Start JupyterLab
lab:
	@echo "${BLUE}Starting JupyterLab server...${RESET}"
	uv run jupyter lab

# Publication Analysis
## Run all analysis notebooks (01-14)
run-notebooks:
	@echo "${BLUE}Running all analysis notebooks...${RESET}"
	bash $(SCRIPTS_DIR)/run_all_notebooks.sh
	@echo "${GREEN}All notebooks executed!${RESET}"

## Run notebooks with continue-on-error
run-notebooks-safe:
	@echo "${BLUE}Running all analysis notebooks (continue on error)...${RESET}"
	bash $(SCRIPTS_DIR)/run_all_notebooks.sh --continue-on-error
	@echo "${GREEN}Notebook execution complete!${RESET}"

## List analysis notebooks
list-notebooks:
	@echo "${BLUE}Analysis notebooks:${RESET}"
	bash $(SCRIPTS_DIR)/run_all_notebooks.sh --list

## Consolidate publication CSVs to Excel
consolidate-tables:
	@echo "${BLUE}Consolidating publication tables to Excel...${RESET}"
	uv run python $(SCRIPTS_DIR)/consolidate_publication_tables.py
	@echo "${GREEN}Excel workbook created!${RESET}"

## Full publication pipeline: run notebooks + consolidate
publication: run-notebooks consolidate-tables
	@echo "${GREEN}✅ Publication pipeline complete!${RESET}"
	@echo "Output: notebooks/outputs/publication/publication_tables.xlsx"

# Documentation
## Build documentation
docs:
	@echo "${BLUE}Building documentation...${RESET}"
	uv run python $(SCRIPTS_DIR)/dev/build_docs.py

## Serve documentation locally
docs-serve: docs
	@echo "${BLUE}Serving documentation locally...${RESET}"
	cd docs/_build/html && python -m http.server 8000

# Development
## Run pre-commit hooks
pre-commit:
	@echo "${BLUE}Running pre-commit hooks...${RESET}"
	uv run pre-commit run --all-files

## Install pre-commit hooks
pre-commit-install:
	@echo "${BLUE}Installing pre-commit hooks...${RESET}"
	uv run pre-commit install

## Update dependencies
update:
	@echo "${BLUE}Updating dependencies...${RESET}"
	uv sync --upgrade

## Add new dependency
add-dep:
	@echo "${BLUE}Adding new dependency...${RESET}"
	@read -p "Enter package name: " package; \
	uv add "$$package"

## Add new development dependency
add-dev-dep:
	@echo "${BLUE}Adding new development dependency...${RESET}"
	@read -p "Enter package name: " package; \
	uv add --group dev "$$package"

# Git Workflow
## Create new feature branch
new-branch:
	@echo "${BLUE}Creating new feature branch...${RESET}"
	@read -p "Enter branch name (without 'feature/' prefix): " branch; \
	git checkout -b "feature/$$branch"

## Show git status and recent commits
status:
	@echo "${BLUE}Git Status:${RESET}"
	@git status --short
	@echo ""
	@echo "${BLUE}Recent Commits:${RESET}"
	@git log --oneline -10

# Cleanup
## Clean up cache and build files
clean:
	@echo "${BLUE}Cleaning up cache and build files...${RESET}"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf dist/ 2>/dev/null || true
	rm -rf build/ 2>/dev/null || true
	@echo "${GREEN}Cleanup complete!${RESET}"

## Deep clean including virtual environment
clean-all: clean
	@echo "${BLUE}Performing deep clean...${RESET}"
	rm -rf .venv/ 2>/dev/null || true
	@echo "${GREEN}Deep clean complete!${RESET}"

# CI/CD Simulation
## Run full CI pipeline locally
ci: clean check test-cov
	@echo "${GREEN}✅ All CI checks passed!${RESET}"

## Prepare for commit (format, lint, test)
pre-commit-check: format lint typecheck test
	@echo "${GREEN}✅ Ready to commit!${RESET}"

# Project Management
## Show project information
info:
	@echo "${BLUE}AINarratives Project Information:${RESET}"
	@echo "📦 Package: $(PACKAGE_NAME)"
	@echo "🐍 Python: $(shell python --version 2>/dev/null || echo 'Not found')"
	@echo "📁 Source: $(SRC_DIR)/"
	@echo "🧪 Tests: $(TESTS_DIR)/"
	@echo "📜 Scripts: $(SCRIPTS_DIR)/"
	@echo ""
	@echo "${BLUE}Dependencies Status:${RESET}"
	@uv tree --depth 1 2>/dev/null || echo "Run 'make install' first"

## Check if everything is working
health-check: info
	@echo ""
	@echo "${BLUE}Health Check:${RESET}"
	@echo -n "✓ UV installed: "; command -v uv >/dev/null && echo "${GREEN}Yes${RESET}" || echo "${RED}No${RESET}"
	@echo -n "✓ Git repository: "; test -d .git && echo "${GREEN}Yes${RESET}" || echo "${RED}No${RESET}"
	@echo -n "✓ Virtual environment: "; test -d .venv && echo "${GREEN}Yes${RESET}" || echo "${RED}No${RESET}"
	@echo -n "✓ Dependencies installed: "; uv run python -c "import pain_narratives" 2>/dev/null && echo "${GREEN}Yes${RESET}" || echo "${RED}No${RESET}"

.PHONY: help install dev-install analysis-install setup format lint typecheck check test test-cov test-watch app experiments run-script db-init db-migrate db-migration jupyter-setup notebook lab run-notebooks run-notebooks-safe list-notebooks consolidate-tables publication docs docs-serve pre-commit pre-commit-install update add-dep add-dev-dep new-branch status clean clean-all ci pre-commit-check info health-check
