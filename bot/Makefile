formatting:
	@echo "Running Ruff..." && ruff check . --fix
	@echo "Running Ruff format..." && ruff format .

lint:
	@echo "Running Ruff checks..." && ruff check .

test:
	@echo "Running all tests..." && pytest

test-fast:
	@echo "Running tests (fail fast)..." && pytest -x --tb=short -q

test-cov:
	@echo "Running tests with coverage report (HTML)..." && pytest --cov=. --cov-report=html:htmlcov && echo "Report generated: htmlcov/index.html"

test-module:
	@echo "Running tests for module: $(MODULE)" && pytest tests/$(MODULE)/

ci:
	@echo "Running CI tests..." && pytest --tb=short -q --cov=. --cov-fail-under=75