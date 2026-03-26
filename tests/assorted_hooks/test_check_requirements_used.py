r"""Tests for ``check_requirements_used``."""

import ast
from textwrap import dedent

from check_requirements_used import get_requirements_from_ast


def test_get_requirements_from_ast_ignores_relative_imports() -> None:
    tree = ast.parse(
        dedent(
            """
        from . import local_module
        from ..subpackage import sibling
        from third_party.lib import thing
        import requests
        """
        )
    )

    reqs = get_requirements_from_ast(tree)

    assert {req.name for req in reqs} == {"third_party", "requests"}
