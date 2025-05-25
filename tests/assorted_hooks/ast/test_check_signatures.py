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

    def __eq__(self, other):
        """od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        """
        if isinstance(other, OrderedDict):
            return dict.__eq__(self, other) and all(map(_eq, self, other))
        return dict.__eq__(self, other)

    def __rmod__(self, template):
        return self.__class__(str(template) % self)
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

    def __eq__(self, other, /):
        """od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        """
        if isinstance(other, OrderedDict):
            return dict.__eq__(self, other) and all(map(_eq, self, other))
        return dict.__eq__(self, other)

    def __rmod__(self, template, /):
        return self.__class__(str(template) % self)
'''


def test_fix_dunder_positional_only() -> None:
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    nodes = list(yield_functions(tree))
    patched_lines = fix_dunder_positional_only(lines, nodes)
    expected_lines = expected.splitlines(keepends=True)
    assert patched_lines == expected_lines
