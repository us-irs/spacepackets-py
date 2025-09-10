# Run with `just all`
all: fmt check test

fmt:
  ruff format

check:
  ruff check

test:
  pytest
