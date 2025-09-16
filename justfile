# Run with `just all`
all: fmt check coverage

setup:
  uv venv

install:
  uv pip install -e ".[test]"

fmt:
  ruff format

check:
  ruff check

test:
  pytest

coverage:
  coverage run -m pytest
  coverage report
