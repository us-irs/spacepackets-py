Checklist for new releases
========

The steps shown here are for Ubuntu/MacOS.

# Pre-Release

1. Make sure the docs build with Sphinx, using `make html` inside the
   `docs` directory with `sphinx` and `sphinx_rtd_theme` installed. Also test the examples with
   `make doctest`.
2. Bump version inside the `pyproject.toml` file.
3. Update `CHANGELOG.md`: Convert `unreleased` section into version section
   with date and new `unreleased`section.
4. Run tests with `pytest`
5. Run auto-formatter with `ruff format`
6. Run linter with `ruff check`
7. Wait for CI/CD results. This also runs the tests on different operating systems

# Release

1. Build the package using `uv build`
2. Upload to package to PyPi using `uv publish`. You might also need to authenticate, for example
   by passing `--token <your token>` to the command.

# Post-Release

1. Create new release on `GitHub` based on the release branch. This also creates
   a tag.
