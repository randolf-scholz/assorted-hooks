r"""Test the check_unmaintained script."""

import tomllib
from contextlib import redirect_stdout
from io import BytesIO, StringIO

from assorted_hooks.scripts.pyproject_check_unmaintained import check_pyproject

# NOTE: need bytes for `tomllib.load`.
TEST_PYPROJECT_TOML = rb"""
[project]
version = "0.1.0"
name = "assorted-hooks"

dependencies = ["wget>=3.2"]

[project.optional-dependencies]
test = ["unittest"]
"""

EXPECTED = """\
Dependency unittest appears unmaintained (latest release=0.0 from 2010-07-14 00:51:11
Dependency wget appears unmaintained (latest release=3.2 from 2015-10-22 15:26:37
"""


def test_check_unmaintained():
    # fake input of pyproject.toml
    with BytesIO(TEST_PYPROJECT_TOML) as file:
        config = tomllib.load(file)

    # check the pyproject.toml
    with redirect_stdout(StringIO()) as stdout:
        assert check_pyproject(config) == 2

    assert stdout.getvalue() == EXPECTED
