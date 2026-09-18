PYTHON		= $(shell uv run which python 2>/dev/null || which python)
TEST_TIMEOUT ?= "0.5"
TEST_SESSION_TIMEOUT ?= "5.0"
TEST_OPTS := -ra --timeout=$(TEST_TIMEOUT) --session-timeout=$(TEST_SESSION_TIMEOUT)

# Man page generation variables
PKG_VERSION = $(shell uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
BUILD_DATE = $(shell date '+%B %d, %Y')
QUIPUCORDSCTL_VAR_CURRENT_YEAR = $(shell date '+%Y')
QUIPUCORDSCTL_VAR_PROGRAM_NAME = quipucordsctl
QUIPUCORDSCTL_VAR_PROJECT = Quipucords
OLD_MAN_PAGE_BUILD_DATE := $(shell grep -e "^\.TH" docs/_build/quipucordsctl.1 2>/dev/null | cut -d '"' -f 6)
SED = sed

.PHONY: help
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
	@echo "  manpage                       to regenerate all man page files"
	@echo "  manpage-test                  to verify man pages haven't changed (CI)"
	@echo "  bump-version                  to bump the project version (VERSION=x.y.z or SEGMENT=major|minor|patch)"

.PHONY: all
all: check-requirements lint test-coverage

.PHONY: clean
clean:
	rm -rf .venv .pytest_cache quipucordsctl.egg-info dist build
	rm -rf $(shell find . | grep -E '(.*\.pyc)|(\.coverage(\..+)*)$$|__pycache__')

.PHONY: check-requirements
check-requirements:
	uv lock --check

.PHONY: lock-requirements
lock-requirements:
	uv lock

.PHONY: update-requirements
update-requirements:
	uv lock --upgrade
	$(MAKE) lock-requirements

.PHONY: bump-version
bump-version:
ifdef VERSION
ifdef SEGMENT
	$(error Specify either VERSION or SEGMENT, not both)
endif
	uv version $(VERSION)
else ifdef SEGMENT
ifneq ($(filter $(SEGMENT),major minor patch),$(SEGMENT))
	$(error SEGMENT must be 'major', 'minor', or 'patch', got '$(SEGMENT)')
endif
	uv version --bump $(SEGMENT)
else
	$(error Specify either SEGMENT=<major|minor|patch> or VERSION=<x.y.z>)
endif
	$(SED) -i "/global version_ctl/s/.*/%global version_ctl $$(uv run python scripts/get-version.py)/" quipucordsctl.spec
	$(SED) -i "s/^%global \(\(server\|ui\)_image .*\):[0-9\.]\+/%global \1:$$(uv run python scripts/get-version.py --major-minor)/" quipucordsctl.spec

.PHONY: test
test:
	uv run pytest $(TEST_OPTS)

.PHONY: test-case
test-case:
	echo $(pattern)
	$(MAKE) test -e TEST_OPTS="${TEST_OPTS} $(pattern)"

.PHONY: test-coverage
test-coverage:
	$(MAKE) test TEST_OPTS="${TEST_OPTS} --cov=src/quipucordsctl --cov-report=xml"
	uv run coverage report --show-missing

.PHONY: lint
lint: lint-ruff

.PHONY: lint-ruff
lint-ruff:
	uv run ruff check .
	uv run ruff format --check .

# Man page generation targets

# Write a man page (roff format) with placeholders for names, version, and dates
.PHONY: update-man-template-roff
update-man-template-roff:
	@SPHINX_BUILD=$$(uv run which sphinx-build 2>/dev/null); \
	if [ -z "$$SPHINX_BUILD" ]; then \
		echo "Error: sphinx-build not found. Install with: uv sync --group build"; \
		exit 1; \
	fi; \
	$$SPHINX_BUILD -b man -q \
	  -D project='QUIPUCORDSCTL_VAR_PROGRAM_NAME' \
	  -D release='PKG_VERSION' \
	  -D today='BUILD_DATE' \
	  docs/source docs/_build

# Generate an upstream "quipucordsctl" man page in human-readable RST
.PHONY: generate-man-quipucordsctl-rst
generate-man-quipucordsctl-rst:
	@$(SED) \
	  -e "s/QUIPUCORDSCTL_VAR_PROGRAM_NAME/${QUIPUCORDSCTL_VAR_PROGRAM_NAME}/g" \
	  -e "s/QUIPUCORDSCTL_VAR_PROJECT/${QUIPUCORDSCTL_VAR_PROJECT}/g" \
	  -e "s/QUIPUCORDSCTL_VAR_CURRENT_YEAR/${QUIPUCORDSCTL_VAR_CURRENT_YEAR}/g" \
	  docs/source/man-template.rst

.PHONY: update-man-quipucordsctl-rst
update-man-quipucordsctl-rst:
	$(MAKE) --no-print-directory generate-man-quipucordsctl-rst > docs/_build/man-quipucordsctl.rst

# Generate an upstream "quipucordsctl" man page in man-parsable roff format
.PHONY: generate-man-quipucordsctl-roff
generate-man-quipucordsctl-roff:
	@$(SED) \
	  -e "s/QUIPUCORDSCTL_VAR_PROGRAM_NAME/${QUIPUCORDSCTL_VAR_PROGRAM_NAME}/g" \
	  -e "s/QUIPUCORDSCTL_VAR_PROJECT/${QUIPUCORDSCTL_VAR_PROJECT}/g" \
	  -e "s/QUIPUCORDSCTL_VAR_CURRENT_YEAR/${QUIPUCORDSCTL_VAR_CURRENT_YEAR}/g" \
	  -e "s/PKG_VERSION/${PKG_VERSION}/g" \
	  -e "s/BUILD_DATE/${BUILD_DATE}/g" \
	  docs/_build/QUIPUCORDSCTL_VAR_PROGRAM_NAME.1

.PHONY: update-man-quipucordsctl-roff
update-man-quipucordsctl-roff:
	$(MAKE) --no-print-directory generate-man-quipucordsctl-roff > docs/_build/quipucordsctl.1

# Common man page generation steps
.PHONY: generate-manpage-files
generate-manpage-files:
	$(MAKE) update-man-template-roff
	$(MAKE) update-man-quipucordsctl-rst
	$(MAKE) update-man-quipucordsctl-roff

# Regenerate and update all man page files
.PHONY: manpage
manpage:
	$(MAKE) generate-manpage-files

.PHONY: manpage-test
manpage-test:
	@if [ -z "${OLD_MAN_PAGE_BUILD_DATE}" ]; then \
		echo "Error: Cannot extract existing build date from docs/_build/quipucordsctl.1"; \
		echo "The file may be missing or malformed. Run 'make manpage' first."; \
		exit 1; \
	fi
	$(MAKE) generate-manpage-files BUILD_DATE="${OLD_MAN_PAGE_BUILD_DATE}"
	git diff --exit-code docs
	git diff --staged --exit-code docs
