.PHONY: help lint lint-fix format test typecheck clean build check-dist publish git-tag release version dev-install check-tools

# Variables
VERSION := $(shell grep "^version" pyproject.toml | cut -d '"' -f 2)
PROJECT_DIRS := src/
MYPY_DIRS := src/
PYTHON := python
GIT := git

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Conditional output logic for tool checks
ifeq ($(filter check-tools,$(MAKECMDGOALS)),check-tools)
    CHECK_ECHO := echo
else
    CHECK_ECHO := true
endif

# Tool detection helpers
check_tool = $(shell command -v $(1) 2>/dev/null)

help:
	@echo "$(BLUE)=========================================$(NC)"
	@echo "$(BLUE)Makefile Development Commands$(NC)"
	@echo "$(BLUE)=========================================$(NC)"
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@echo "  make dev-install  - Install package in development mode with all dependencies"
	@echo "  make check-tools  - Check and install missing development tools"
	@echo "  make format       - Format code with Black"
	@echo "  make lint         - Run Ruff linter"
	@echo "  make lint-fix     - Run Ruff linter with auto-fix"
	@echo "  make typecheck    - Run mypy type checker"
	@echo "  make test         - Run pytest with coverage"
	@echo ""
	@echo "$(GREEN)Build & Release:$(NC)"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make build        - Build distribution packages"
	@echo "  make check-dist   - Check distribution with twine"
	@echo "  make publish      - Upload to PyPI (interactive)"
	@echo "  make git-tag      - Create and push git tag"
	@echo "  make release      - Full release workflow (format, lint, test, build, publish, tag)"
	@echo ""
	@echo "$(GREEN)Info:$(NC)"
	@echo "  make version      - Show current version"
	@echo "  make help         - Show this help message"
	@echo ""
	@echo "$(YELLOW)Current version: $(VERSION)$(NC)"

version:
	@echo "$(GREEN)Current version: $(VERSION)$(NC)"

check-tools:
	@$(CHECK_ECHO) "$(BLUE)🔧 Checking development tools...$(NC)"
	@if [ -z "$(call check_tool,black)" ]; then \
		echo "$(YELLOW)⚠️  black not found - installing...$(NC)"; \
		$(PYTHON) -m pip install "black>=24.0.0"; \
	else \
		$(CHECK_ECHO) "$(GREEN)✓ black found$(NC)"; \
	fi
	@if [ -z "$(call check_tool,ruff)" ]; then \
		echo "$(YELLOW)⚠️  ruff not found - installing...$(NC)"; \
		$(PYTHON) -m pip install "ruff>=0.1.0"; \
	else \
		$(CHECK_ECHO) "$(GREEN)✓ ruff found$(NC)"; \
	fi
	@if [ -z "$(call check_tool,mypy)" ]; then \
		echo "$(YELLOW)⚠️  mypy not found - installing...$(NC)"; \
		$(PYTHON) -m pip install "mypy>=1.8.0"; \
	else \
		$(CHECK_ECHO) "$(GREEN)✓ mypy found$(NC)"; \
	fi
	@$(PYTHON) -c "import pytest_cov" 2>/dev/null || { \
		echo "$(YELLOW)⚠️  pytest-cov not found - installing testing stack...$(NC)"; \
		$(PYTHON) -m pip install "pytest>=8.0.0" "pytest-cov>=4.0.0"; \
	}
	@$(CHECK_ECHO) "$(GREEN)✓ pytest & coverage found$(NC)"
	@if [ -z "$(call check_tool,twine)" ]; then \
		echo "$(YELLOW)⚠️  twine not found - installing...$(NC)"; \
		$(PYTHON) -m pip install twine build; \
	else \
		$(CHECK_ECHO) "$(GREEN)✓ twine found$(NC)"; \
	fi
	@$(CHECK_ECHO) "$(GREEN)✅ All tools checked$(NC)"

dev-install: check-tools
	@echo "$(BLUE)📦 Installing ExifSort in development mode...$(NC)"
	$(PYTHON) -m pip install --upgrade pip
	pip install -e ".[dev,toml]"
	@echo "$(GREEN)✅ Development installation complete$(NC)"

lint: check-tools
	@echo "$(BLUE)🔍 Running Ruff linter...$(NC)"
	ruff check $(PROJECT_DIRS)
	@echo "$(GREEN)✅ Linting complete$(NC)"

lint-fix: check-tools
	@echo "$(BLUE)🔍 Running Ruff linter with auto-fix...$(NC)"
	ruff check $(PROJECT_DIRS) --fix
	@echo "$(GREEN)✅ Linting complete$(NC)"

format: check-tools
	@echo "$(BLUE)🎨 Formatting code with Black...$(NC)"
	black $(PROJECT_DIRS)
	@echo "$(GREEN)✅ Code formatted$(NC)"

typecheck: check-tools
	@echo "$(BLUE)🔎 Type checking with mypy...$(NC)"
	mypy $(MYPY_DIRS) --ignore-missing-imports
	@echo "$(GREEN)✅ Type checking complete$(NC)"

test: check-tools
	@echo "$(BLUE)🧪 Running tests with coverage...$(NC)"
	pytest tests/ -v --cov=src/exifsort --cov-report=term-missing
	@echo "$(GREEN)✅ Tests complete$(NC)"

clean:
	@echo "$(BLUE)🧹 Cleaning build artifacts...$(NC)"
	rm -rf dist/ build/
	rm -rf src/**/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Clean complete$(NC)"

build: clean check-tools
	@echo "$(BLUE)📦 Building distribution packages...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✅ Build complete$(NC)"

check-dist: check-tools
	@echo "$(BLUE)✅ Checking distribution...$(NC)"
	twine check dist/*
	@echo "$(GREEN)✅ Distribution check complete$(NC)"

publish: build check-dist
	@echo "$(BLUE)🚀  Publishing v$(VERSION)...$(NC)"
	@echo ""
	@read -p "Continue with upload to PyPI? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)📤 Uploading to PyPI...$(NC)"; \
		twine upload dist/*; \
		echo "$(GREEN)✅ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)❌ Upload cancelled$(NC)"; \
		exit 1; \
	fi

git-tag:
	@echo "$(BLUE)🏷️  Creating git tag v$(VERSION)...$(NC)"
	$(GIT) tag -a v$(VERSION) -m "Release v$(VERSION)"
	$(GIT) push origin v$(VERSION)
	@echo "$(GREEN)✅ Git tag created and pushed$(NC)"

release: check-tools format lint typecheck test clean build check-dist
	@echo "$(BLUE)🎉  Releasing v$(VERSION)...$(NC)"
	@echo ""
	@read -p "Commit and push changes? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(GIT) add .; \
		$(GIT) commit -m "Release v$(VERSION)"; \
		$(GIT) push origin main; \
		echo "$(GREEN)✅ Changes committed and pushed$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Skipping commit$(NC)"; \
	fi
	@echo ""
	@read -p "Upload to PyPI? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		twine upload dist/*; \
		echo "$(GREEN)✅ Uploaded to PyPI$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Skipping PyPI upload$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@read -p "Create and push git tag v$(VERSION)? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(GIT) tag -a v$(VERSION) -m "Release v$(VERSION)"; \
		$(GIT) push origin v$(VERSION); \
		echo "$(GREEN)✅ Git tag created and pushed$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Skipping git tag$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)🎊 Release v$(VERSION) completed!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Check PyPI: https://pypi.org/project/exifsort/"
	@echo "  2. Verify GitHub release: https://github.com/barabasz/exifsort/releases/new"
	@echo "  3. Update documentation if needed"

.DEFAULT_GOAL := help