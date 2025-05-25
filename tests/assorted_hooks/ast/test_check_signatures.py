r"""Test the fix_dunder_positional_only function."""

import ast

from assorted_hooks.ast.ast_utils import yield_functions
from assorted_hooks.ast.check_signatures import fix_dunder_positional_only

text = r'''
class Foo:
    def __eq__(self, other: object) -> bool:
        r"""Docstring."""

    def __ne__(
        self,
        other: object,
    ) -> bool:
        r"""Docstring."""

    def __le__(self, other: object) -> bool: ...

    def __lt__(
        self,
        other: object,
    ) -> bool: ...

    @overload
    def __add__(
        self,
        other: "Foo",
    ) -> "Foo": ...
    @overload
    def __add__(
        self,
        other: int,
    ) -> "Foo": ...
    def __add__(
        self,
        other: object,
    ) -> "Foo":
        r"""ADDITION."""
'''


expected = r'''
class Foo:
    def __eq__(self, other: object, /) -> bool:
        r"""Docstring."""

    def __ne__(
        self, other: object, /,
    ) -> bool:
        r"""Docstring."""

    def __le__(self, other: object, /) -> bool: ...

    def __lt__(
        self, other: object, /,
    ) -> bool: ...

    @overload
    def __add__(
        self, other: 'Foo', /,
    ) -> "Foo": ...
    @overload
    def __add__(
        self, other: int, /,
    ) -> "Foo": ...
    def __add__(
        self, other: object, /,
    ) -> "Foo":
        r"""ADDITION."""
'''


def test_fix_dunder_positional_only() -> None:
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    nodes = list(yield_functions(tree))
    patched_lines = fix_dunder_positional_only(lines, nodes)
    expected_lines = expected.splitlines(keepends=True)
    for line, expected_line in zip(patched_lines, expected_lines, strict=True):
        assert line == expected_line, f"Expected: {expected_line!r}, but got: {line!r}"
