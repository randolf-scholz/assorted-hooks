"""Test no_mixed_args.py."""

from typing import overload


class Foo:
    """Dummy class."""

    def method(self):
        """Dummy method."""
        ...

    def __call__(self, x: int, /) -> None:
        """Dummy call."""
        ...

    @classmethod
    def from_list(cls, x: list[int], /) -> "Foo":
        """Dummy classmethod."""
        return cls()

    @classmethod
    def foo(funny_name):  # pyright: ignore reportSelfClsParameterName
        pass


class Meta(type):
    """Dummy metaclass."""

    def __call__(cls, x: int, /) -> None:
        """Dummy call."""
        ...

    def __new__(mcs, *args, **kwargs):
        """Dummy new."""
        return super().__new__(mcs, *args, **kwargs)


@overload
def foo(x, /):
    ...


@overload
def foo(x, y, /):
    ...


def foo(x, y=None, /):
    pass
