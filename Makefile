PYTHON		= $(shell uv run which python 2>/dev/null || which python)
TEST_TIMEOUT ?= "0.5"
TEST_SESSION_TIMEOUT ?= "5.0"
TEST_OPTS := -ra --timeout=$(TEST_TIMEOUT) --session-timeout=$(TEST_SESSION_TIMEOUT)

help:
	@echo "Please use \`make <target>' where <target> is one of:"
	@echo "  help                          to show this message"
	@echo "  all                           to run check-requirements, lint, and test-coverage"
	@echo "  clean                         to remove pyc/cache files"
	@echo "  lint                          to run all linters"
	@echo "  lint-ruff                     to run ultrafast ruff linter"
	@echo "  check-requirements            to check all python dependencies"
	@echo "  lock-requirements             to lock all python dependencies"
	@echo "  update-requirements           to update all python dependencies"
	@echo "  test                          to run unit tests"
	@echo "  test-coverage                 to run unit tests and measure test coverage"

all: check-requirements lint test-coverage

clean:
	rm -rf .venv .pytest_cache quipucordsctl.egg-info dist build
	rm -rf $(shell find . | grep -E '(.*\.pyc)|(\.coverage(\..+)*)$$|__pycache__')

check-requirements:
	uv lock --check

lock-requirements:
	uv lock

update-requirements:
	uv lock --upgrade
	$(MAKE) lock-requirements

test:
	uv run pytest $(TEST_OPTS)

test-case:
	echo $(pattern)
	$(MAKE) test -e TEST_OPTS="${TEST_OPTS} $(pattern)"

test-coverage:
	$(MAKE) test TEST_OPTS="${TEST_OPTS} --cov=src/quipucordsctl --cov-report=xml"
	uv run coverage report --show-missing

lint: lint-ruff

lint-ruff:
	uv run ruff check .
	uv run ruff format --check .
