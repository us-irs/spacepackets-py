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
4. Run tests with `pytest .`
5. Run auto-formatter with `black .`
6. Run linter script `flake8 .`
7. Wait for CI/CD results. This also runs the tests on different operating systems

# Release

1. Deleting existing distribution: `rm dist/*`
2. Build the package. Requires the `build` package: `python3 -m build`
3. Upload the source and build distribution: `python3 -m twine upload dist/*`. You might require
   a PyPI upload token to do this.

# Post-Release

1. Create new release on `GitHub` based on the release branch. This also creates
   a tag.
