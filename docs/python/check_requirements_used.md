# check-requirements-used

Analyzes all `import`-statements and makes sure all third-party dependencies are listed in `pyproject.toml`.

Can be applied to test-dependencies as well. This catches missing implicit dependencies, for example package `panads` depends on `numpy` but `numpy` should still be listed in `pyproject.toml` if it is used explicitly.

**Note:** Requirement names can differ from how they are imported. For example `pyyaml` is imported as `yaml`. For this reason, the hook requires access to the local virtual environment, as it used `importlib.metadata.distributions` to get the package names.

## Additional Arguments
