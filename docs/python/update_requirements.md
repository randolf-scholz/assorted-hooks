# update-requirements

**NOTE:** THIS HOOK IS SET TO MANUAL BY DEFAULT. RUN VIA

```bash
pre-commit run --hook-stage manual pyproject-update-deps
```

Updates dependencies in `pyproject.toml`.

- `"package>=version"` ⟶ `"package>=currently_installed"` (`[project]` section)
- `package=">=version"` ⟶ `package=">=currently_installed"` (`[tool.poetry]` section)
- `package={version=">=version"` ⟶ `package={version=">=currently_installed"` (`[tool.poetry]` section)

## Additional Arguments
