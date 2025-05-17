r"""Tests for assorted_hooks.check_typing.check_no_return_union."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_no_return_union


def test_no_return_union_pep604() -> None:
    code = r"""
    def foo(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, filename="test.py") == 1
    assert check_no_return_union(tree, recursive=True, filename="test.py") == 1


def test_no_return_union_pep604_recursion() -> None:
    code = r"""
    def foo(x: int) -> list[None | int]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, filename="test.py") == 0
    assert check_no_return_union(tree, recursive=True, filename="test.py") == 1


def test_no_return_union_typing_recursion() -> None:
    code = r"""
    def foo(x: int) -> list[Union[None, int]]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, filename="test.py") == 0
    assert check_no_return_union(tree, recursive=True, filename="test.py") == 1


def test_no_return_union_typing() -> None:
    code = r"""
    def foo(x: int) -> Union[int, None]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, filename="test.py") == 1
    assert check_no_return_union(tree, recursive=True, filename="test.py") == 1


def test_no_return_union_overload() -> None:
    """Test exclusion of overload implementation.

    We assume that a type-checker would select one of the overloads,
    and the union in the implementation is only for consistency.
    """
    code = r"""
    class Foo:
        @overload
        def __getitem__(self, index: int) -> int: ...
        @overload
        def __getitem__(self, index: slice) -> Self: ...
        def __getitem__(self, index: int | slice) -> int | Self: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, filename="test.py") == 0
    assert check_no_return_union(tree, recursive=True, filename="test.py") == 0


def test_no_return_union_protocol() -> None:
    r"""Test exclusion of Protocol implementation."""
    code = r"""
    @runtime_checkable
    class Map[K, V](Collection[K], Protocol):  # K, +V
        @abstractmethod
        def __getitem__(self, __key: K, /) -> V: ...

        # Mixin Methods
        def keys(self) -> KeysView[K]:
            return KeysView(self)  # type: ignore[arg-type]

        def values(self) -> ValuesView[V]:
            return ValuesView(self)  # type: ignore[arg-type]

        def items(self) -> ItemsView[K, V]:
            return ItemsView(self)  # type: ignore[arg-type]

        @overload
        def get(self, key: K, /) -> Optional[V]: ...
        @overload
        def get[T](self, key: K, /, default: V | T) -> V | T: ...
        def get(self, key, /, default=None):
            try:
                return self[key]
            except KeyError:
                return default

        def __eq__(self, other: object, /) -> bool:
            if not isinstance(other, Map):
                return NotImplemented
            return dict(self.items()) == dict(other.items())

        def __contains__(self, key: object, /) -> bool:
            try:
                self[key]  # type: ignore[index]
            except KeyError:
                return False
            return True
    """
    tree = ast.parse(dedent(code))
    assert (
        check_no_return_union(
            tree, exclude_protocols=False, recursive=False, filename="test.py"
        )
        == 0
    )
    assert (
        check_no_return_union(
            tree, exclude_protocols=False, recursive=True, filename="test.py"
        )
        == 0
    )


def test_no_return_union_protocol_contrafactual() -> None:
    r"""Test exclusion of Protocol implementation."""
    code = r"""
    @runtime_checkable
    class Map[K, V](Collection[K]):  # K, +V
        @abstractmethod
        def __getitem__(self, __key: K, /) -> V: ...

        # Mixin Methods
        def keys(self) -> KeysView[K]:
            return KeysView(self)  # type: ignore[arg-type]

        def values(self) -> ValuesView[V]:
            return ValuesView(self)  # type: ignore[arg-type]

        def items(self) -> ItemsView[K, V]:
            return ItemsView(self)  # type: ignore[arg-type]

        @overload
        def get(self, key: K, /) -> Optional[V]: ...
        @overload
        def get[T](self, key: K, /, default: V | T) -> V | T: ...
        def get(self, key, /, default=None):
            try:
                return self[key]
            except KeyError:
                return default

        def __eq__(self, other: object, /) -> bool:
            if not isinstance(other, Map):
                return NotImplemented
            return dict(self.items()) == dict(other.items())

        def __contains__(self, key: object, /) -> bool:
            try:
                self[key]  # type: ignore[index]
            except KeyError:
                return False
            return True
    """
    tree = ast.parse(dedent(code))
    assert (
        check_no_return_union(
            tree, exclude_protocols=False, recursive=False, filename="test.py"
        )
        == 1
    )
    assert (
        check_no_return_union(
            tree, exclude_protocols=False, recursive=True, filename="test.py"
        )
        == 1
    )
