# update-requirements

**NOTE:** THIS HOOK IS SET TO MANUAL BY DEFAULT. RUN VIA

```bash
pre-commit run --hook-stage manual pyproject-update-deps
```

Updates dependencies in `pyproject.toml`.

Versions are compared and normalized according to [PEP 440](https://peps.python.org/pep-0440/).

- `"package>=version"` ⟶ `"package>=currently_installed"` (`[project]` section)
- `package=">=version"` ⟶ `package=">=currently_installed"` (`[tool.poetry]` section)
- `package={version=">=version"` ⟶ `package={version=">=currently_installed"` (`[tool.poetry]` section)

## Additional Arguments
