# check-requirements-valid

- Verifies that the name of the package is valid.
- Verifies that the version in `pyproject.toml` adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/).

Checks requirements listed in the following sections of `pyproject.toml`:

- `[project.dependencies]`, `[project.optional-dependencies]`, `[dependency-groups]`
- `[tool.poetry.dependencies]`, `[tool.poetry.group.*.dependencies]`
- `[tool.pdm.dev-dependencies]`

Details: <https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions>

## Additional Arguments
