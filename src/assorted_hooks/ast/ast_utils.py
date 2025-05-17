r"""AST based utilities for the assorted_hooks package."""

__all__ = [
    # Types
    "Func",
    "FunctionKind",
    # Classes
    "AttributeVisitor",
    "OverloadCTX",
    "FunctionCTX",
    "OverloadVisitor",
    # Functions
    "get_full_name",
    "get_full_name_and_parent",
    "get_imported_symbols",
    "has_union",
    "replace_node",
    # checks
    "is_abc",
    "is_abstractmethod",
    "is_concrete_class",
    "is_decorated_with",
    "is_dunder_all",
    "is_dunder_main",
    "is_function_def",
    "is_future_import",
    "is_literal_list",
    "is_overload",
    "is_protocol",
    "is_pure_attribute",
    "is_staticmethod",
    "is_typeddict",
    "is_typing_union",
    "is_union",
    # Iterators
    "yield_aliases",
    "yield_classes",
    "yield_concrete_classes",
    "yield_dunder_all",
    "yield_methods",
    "yield_non_method_functions",
    "yield_functions",
    "yield_overloads_and_context",
    "yield_functions_and_context",
    "yield_imported_attributes",
    "yield_namespace_and_funcs",
    "yield_overloads",
    "yield_pure_attributes",
]

import ast
from ast import (
    AST,
    AnnAssign,
    Assign,
    AsyncFunctionDef,
    Attribute,
    AugAssign,
    BinOp,
    BitOr,
    Call,
    ClassDef,
    Compare,
    Constant,
    Eq,
    FunctionDef,
    If,
    Import,
    ImportFrom,
    List,
    MatchValue,
    Module,
    Name,
    Subscript,
)
from collections.abc import Iterator
from dataclasses import KW_ONLY, dataclass, field
from enum import StrEnum
from typing import TypeAlias, TypeGuard

Func: TypeAlias = FunctionDef | AsyncFunctionDef  # noqa: UP040
r"""Type alias for function-defs."""


def get_full_name(node: AST, /) -> str:
    r"""Get the full name of an attribute.

    Example:
        Given node `c` in `a.b.c`, then returns `"a.b.c"`.
    """
    match node:
        case Call(func=Attribute() | Name() as func):
            return get_full_name(func)
        case Attribute(value=Attribute() | Name() as value, attr=attr):
            string = get_full_name(value)
            return f"{string}.{attr}"
        case Name(id=node_id):
            return node_id
        case _:
            raise TypeError(f"Expected Call, Attribute or Name, got {type(node)=!r}")


def get_full_name_and_parent(node: Attribute | Name, /) -> tuple[Name, str]:
    r"""Get the full name as well as parent node.

    Example:
        Given node is `c` in `a.b.c`, then returns `(a, "a.b.c")`
    """
    match node:
        case Attribute(value=Attribute() | Name() as value, attr=attr):
            parent, string = get_full_name_and_parent(value)
            return parent, f"{string}.{attr}"
        case Name(id=node_id):
            return node, node_id
        case _:
            raise TypeError(f"Expected Attribute or Name, got {type(node)=!r}")


def get_imported_symbols(tree: AST, /) -> dict[str, str]:
    r"""Get all imported symbols as a dictionary alias -> fullname.

    For example, `import pandas as pd` would yield `{"pd": "pandas"}`.
    """
    imported_symbols = {}

    for node in ast.walk(tree):
        match node:
            case Import(names=names):
                for alias in names:
                    imported_symbols[alias.asname or alias.name] = alias.name
            case ImportFrom(module=module, names=names) if module is not None:
                for alias in names:
                    full_name = f"{module}.{alias.name}"
                    imported_symbols[alias.asname or alias.name] = full_name

    return imported_symbols


def has_union(tree: AST, /) -> bool:
    r"""True if the return node is a union."""
    return any(is_union(node) for node in ast.walk(tree))


def is_decorated_with(node: Func, name: str, /) -> bool:
    r"""Checks if the function is decorated with a certain decorator."""
    return name in (get_full_name(d) for d in node.decorator_list)


def is_dunder_main(node: AST, /) -> TypeGuard[If]:
    r"""Check whether node is `if __name__ == "__main__":` check."""
    match node:
        case If(
            test=Compare(
                left=Name(id="__name__"),
                ops=[Eq()],
                comparators=[Constant(value="__main__")],
            )
        ):
            return True
        case _:
            return False


def is_dunder_all(node: AST, /) -> TypeGuard[Assign | AnnAssign | AugAssign]:
    r"""Check whether a node is __all__."""
    match node:
        case Assign(targets=[Name(id="__all__")]):
            return True
        case Assign(targets=targets) if "__all__" in (
            getattr(t, "id", None) for t in targets
        ):
            raise ValueError("Multiple targets in __all__ assignment.")
        case AnnAssign(target=Name(id="__all__")):
            return True
        case _:
            return False


def is_future_import(node: AST, /) -> TypeGuard[Import | ImportFrom]:
    r"""Check whether a node is a future import."""
    match node:
        case ImportFrom(module=module):
            return module == "__future__"
        case Import(names=names):
            return any(imp.name == "__future__" for imp in names)
        case _:
            return False


def is_literal_list(node: AST, /) -> TypeGuard[List]:
    r"""Check whether node is a literal list of strings."""
    match node:
        case List(elts=items):
            return all(
                isinstance(e, Constant) and isinstance(e.value, str) for e in items
            )
        case _:
            return False


def is_function_def(node: AST, /) -> TypeGuard[Func]:
    r"""True if the return node is a function definition."""
    return isinstance(node, Func)


def is_overload(node: AST, /) -> bool:
    r"""True if the return node is a function definition."""
    match node:
        case FunctionDef(decorator_list=decos) | AsyncFunctionDef(decorator_list=decos):
            return any(
                isinstance(deco, Name) and deco.id == "overload" for deco in decos
            )
        case _:
            return False


def is_staticmethod(node: Func, /) -> bool:
    r"""Checks if the func is a staticmethod."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "staticmethod" in [d.id for d in decorators]


def is_typing_union(node: AST, /) -> TypeGuard[Subscript]:
    r"""True if the return node is a union."""
    match node:
        case Subscript(value=Name(id="Union")):
            return True
        case _:
            return False


def is_union(node: AST, /) -> TypeGuard[Subscript | BinOp]:
    r"""True if the return node is a union."""
    match node:
        case Subscript(value=Name(id="Union")):
            return True
        case BinOp(op=BitOr()):
            return True
        case _:
            return False


def is_pure_attribute(node: AST, /) -> TypeGuard[Attribute]:
    r"""Check whether a node is a pure attribute."""
    match node:
        case Attribute(value=value):
            return isinstance(value, Name) or is_pure_attribute(value)
        case _:
            return False


def is_abstractmethod(node: AST, /) -> TypeGuard[FunctionDef]:
    r"""Check whether a node is an abstract method."""
    return isinstance(node, FunctionDef) and any(
        isinstance(deco, Name) and deco.id == "abstractmethod"
        for deco in node.decorator_list
    )


def is_concrete_class(node: AST, /) -> TypeGuard[ClassDef]:
    match node:
        case ClassDef(bases=bases, keywords=keywords, body=body):
            return not (
                any(map(is_protocol, bases))
                or any(map(is_typeddict, bases))
                or any(map(is_abc, bases))
                or any(keyword.arg == "metaclass" for keyword in keywords)
                or any(map(is_abstractmethod, body))
            )

    return False


def yield_pure_attributes(tree: AST, /) -> Iterator[Attribute]:
    r"""Get all nodes that consist only of attributes."""
    yield from AttributeVisitor(tree)


def yield_overloads(tree: AST, /) -> Iterator[Func]:
    r"""Get all function definitions that are decorated with `@overload`."""
    for node in ast.walk(tree):
        match node:
            case FunctionDef(decorator_list=[Name(id="overload"), *_]):
                yield node
            case AsyncFunctionDef(decorator_list=[Name(id="overload"), *_]):
                yield node


def yield_functions(tree: AST, /) -> Iterator[Func]:
    r"""Get all function-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, Func):
            yield node


def yield_classes(tree: AST, /) -> Iterator[ClassDef]:
    r"""Get all class-definitions from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ClassDef):
            yield node


def yield_methods(tree: AST, /) -> Iterator[Func]:
    r"""Get all functions that are defined directly inside class bodies."""
    for cls in yield_classes(tree):
        for node in cls.body:
            if isinstance(node, Func):
                yield node


def yield_non_method_functions(tree: AST, /) -> Iterator[Func]:
    r"""Get all functions that are nod defined inside class body."""
    class_context: set[AST] = set()

    for node in ast.walk(tree):
        match node:
            case ClassDef(body=body):
                class_context.update(body)
            # FIXME: https://github.com/python/cpython/issues/106246
            case FunctionDef() | AsyncFunctionDef():
                if node not in class_context:
                    yield node


def yield_namespace_and_funcs(
    tree: AST, /, *, namespace: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], Func]]:
    r"""Yields both namespace and function node."""
    for node in ast.iter_child_nodes(tree):
        match node:
            case FunctionDef(name=name) as func:
                yield namespace, func
                yield from yield_namespace_and_funcs(func, namespace=(*namespace, name))
            case AsyncFunctionDef(name=name) as func:
                yield namespace, func
                yield from yield_namespace_and_funcs(func, namespace=(*namespace, name))
            case ClassDef(name=name) as cls:
                yield from yield_namespace_and_funcs(cls, namespace=(*namespace, name))


def yield_dunder_all(tree: Module, /) -> Iterator[Assign | AnnAssign | AugAssign]:
    r"""Get the __all__ node from the tree."""
    # NOTE: we are only interested in the module body.
    for node in tree.body:
        if is_dunder_all(node):
            yield node


def yield_imported_attributes(tree: AST, /) -> Iterator[tuple[Attribute, Name, str]]:
    r"""Finds attributes that can be replaced by directly imported symbols."""
    imported_symbols = get_imported_symbols(tree)

    for node in yield_pure_attributes(tree):
        if node.attr in imported_symbols:
            parent, string = get_full_name_and_parent(node)

            head, tail = string.split(".", maxsplit=1)
            if head != parent.id:
                raise ValueError(f"{head=!r} != {parent.id=!r}")

            # e.g. DataFrame -> pandas.DataFrame
            matched_symbol = imported_symbols[node.attr]
            is_match = matched_symbol == string

            # need to check if parent is imported as well to catch pd.DataFrame
            if parent.id in imported_symbols:
                parent_alias = imported_symbols[parent.id]  # e.g. pd -> pandas
                is_match |= matched_symbol == f"{parent_alias}.{tail}"

            if is_match:
                yield node, parent, string


def yield_aliases(tree: AST, /) -> Iterator[ast.alias]:
    r"""Yield alias nodes from AST."""
    for node in ast.walk(tree):
        match node:
            case Attribute(attr=attr, value=Name(id=name), lineno=lineno):
                yield ast.alias(name=f"{name}.{attr}", lineno=lineno)
            case Import(names=names):
                yield from names
            case ImportFrom(module=module, names=names):
                yield from (
                    ast.alias(name=f"{module}.{alias.name}", lineno=alias.lineno)
                    for alias in names
                )


def yield_concrete_classes(tree: AST, /) -> Iterator[ClassDef]:
    r"""Yield concrete classes."""
    for node in ast.walk(tree):
        if is_concrete_class(node):
            yield node


def is_protocol(node: AST, /) -> bool:
    r"""Check if the node is a protocol."""
    match node:
        case ClassDef(bases=bases):
            return any(map(is_protocol, bases))
        case Name(id="Protocol"):
            return True
        case Attribute(attr="Protocol"):
            return True
        case _:
            return False


def is_abc(node: AST, /) -> bool:
    match node:
        case ClassDef(bases=bases):
            return any(map(is_abc, bases))
        case Name(id="ABC" | "ABCMeta"):
            return True
        case Attribute(attr="ABC" | "ABCMeta"):
            return True
        case _:
            return False


def is_typeddict(node: AST, /) -> bool:
    match node:
        case ClassDef(bases=bases):
            return any(map(is_typeddict, bases))
        case Name(id="TypedDict"):
            return True
        case Attribute(attr="TypedDict"):
            return True
        case _:
            return False


@dataclass
class AttributeVisitor(ast.NodeVisitor):
    r"""Get all attributes from the tree.

    Excludes MatchValue(value=Attribute()) nodes.
    """

    tree: AST

    def __iter__(self) -> Iterator[Attribute]:
        r"""Iterate over the tree."""
        yield from self.generic_visit(self.tree)

    def generic_visit(self, node: AST) -> Iterator[Attribute]:
        r"""Generic visit method."""
        match node:
            case MatchValue(value=Attribute()):
                # skip
                pass
            case Attribute() as attr:
                if is_pure_attribute(attr):
                    yield attr
            case _:
                for child in ast.iter_child_nodes(node):
                    yield from self.visit(child)


class FunctionKind(StrEnum):
    r"""Function kind enum."""

    FUNCTION = "function"
    METHOD = "method"

    @staticmethod
    def from_context(node: AST | None, /) -> "FunctionKind":
        r"""Get the function kind from the context."""
        match node:
            case ClassDef():
                return FunctionKind.METHOD
            case _:
                return FunctionKind.FUNCTION


def yield_functions_and_context(
    tree: AST, /, *, context: Func | ClassDef | None = None
) -> Iterator["FunctionCTX"]:
    r"""Functional alternative to `FunctionContextVisitor`."""
    for node in (nodes := list(ast.iter_child_nodes(tree))):
        match node:
            case FunctionDef() | AsyncFunctionDef() as fn:
                yield FunctionCTX(fn, context=context)
                # recurse into function body
                yield from yield_functions_and_context(fn, context=fn)
            case ClassDef() as cls:
                # recurse into class body
                yield from yield_functions_and_context(cls, context=cls)
            case _:
                nodes.extend(ast.iter_child_nodes(node))


@dataclass(slots=True)
class FunctionCTX:
    r"""Function node with context."""

    node: Func
    context: Func | ClassDef | Module | None = None

    @property
    def kind(self) -> FunctionKind:
        r"""Get the function kind."""
        return FunctionKind.from_context(self.context)

    yield_from_ast = staticmethod(yield_functions_and_context)


def yield_overloads_and_context(
    tree: AST, /, *, context: Func | ClassDef | None = None
) -> Iterator["OverloadCTX"]:
    r"""Functional alternative to `FunctionContextVisitor`."""
    nodes = list(ast.iter_child_nodes(tree))
    fn_dict: dict[str, OverloadCTX] = {}

    for node in nodes:
        match node:
            case FunctionDef(name=name) | AsyncFunctionDef(name=name) as fn:
                if name not in fn_dict:
                    fn_dict[name] = OverloadCTX(name, context=context)
                if is_overload(fn):
                    fn_dict[name].overloads.append(fn)
                else:
                    # if implementation is found, pop immediately.
                    fn_dict[name].implementation = fn
                    yield fn_dict.pop(name)
                # recurse into function body
                yield from yield_overloads_and_context(fn, context=fn)
            case ClassDef() as cls:
                # recurse into class body
                yield from yield_overloads_and_context(cls, context=cls)
            case _:
                nodes.extend(ast.iter_child_nodes(node))

    # yield all discovered functions
    yield from fn_dict.values()


@dataclass(slots=True)
class OverloadCTX:
    r"""Context for overloaded functions."""

    name: str
    r"""Function name."""

    _: KW_ONLY

    context: Func | ClassDef | Module | None
    r"""Function context."""
    implementation: Func | None = None
    r"""Implementation of the function."""
    overloads: list[Func] = field(default_factory=list)
    r"""List of associated overloads."""

    @property
    def kind(self) -> FunctionKind:
        r"""Get the function kind."""
        return FunctionKind.from_context(self.context)

    yield_from_ast = staticmethod(yield_overloads_and_context)


class OverloadVisitor(ast.NodeVisitor):
    r"""Get all function-defs and corresponding overloads from the tree.

    Each def is paired with a list of associated overloads.
    """

    tree: AST
    r"""Parent node of the current node."""
    context: Module | ClassDef | FunctionDef | AsyncFunctionDef | None
    r"""Context of the current node."""
    funcs: list[Func]
    r"""List of functions."""

    def __init__(self, tree: AST, /, context: Func | ClassDef | None = None) -> None:
        super().__init__()
        self.tree = tree
        self.context = context
        self.fn_dict: dict[str, OverloadCTX] = {}

    def __iter__(self) -> Iterator[OverloadCTX]:
        r"""Iterate over the tree."""
        return iter(self.generic_visit(self.tree))

    def _add_fn(self, func: Func) -> Iterator[OverloadCTX]:
        name = func.name
        # check if the function is already defined
        if name not in self.fn_dict:
            self.fn_dict[name] = OverloadCTX(name, context=self.context)
        if is_overload(func):
            self.fn_dict[name].overloads.append(func)
        else:
            # as soon as we find a non-overload, we clear the function from the dict
            # since subsequent overloads will be on a "new" function
            self.fn_dict[name].implementation = func
            yield self.fn_dict.pop(name)

    def generic_visit(self, node: AST) -> Iterator[OverloadCTX]:
        r"""Generic visit method."""
        for child in ast.iter_child_nodes(node):
            yield from self.visit(child)
        # yield all discovered functions
        yield from self.fn_dict.values()

    def visit_FunctionDef(self, node: FunctionDef) -> Iterator[OverloadCTX]:  # noqa: N802
        r"""Visit a function definition."""
        yield from self._add_fn(node)
        yield from OverloadVisitor(node, context=node)

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Iterator[OverloadCTX]:  # noqa: N802
        r"""Visit an async function definition."""
        yield from self._add_fn(node)
        yield from OverloadVisitor(node, context=node)

    def visit_ClassDef(self, node: ClassDef) -> Iterator[OverloadCTX]:  # noqa: N802
        r"""Visit a class definition."""
        yield from OverloadVisitor(node, context=node)


def replace_node(
    lines: list[str], old_node: ast.stmt, new_node: ast.stmt, /
) -> list[str]:
    r"""Replace a node in the AST with a new node."""
    if old_node.end_lineno is None:
        raise ValueError("Node has no end line number.")
    if old_node.end_col_offset is None:
        raise ValueError("Node has no end column offset.")

    row = old_node.lineno - 1
    col = old_node.col_offset
    end_row = old_node.end_lineno - 1
    end_col = old_node.end_col_offset

    lines[row : end_row + 1] = [
        f"{lines[row][:col]}{ast.unparse(new_node)}{lines[end_row][end_col:]}"
    ]
    return lines
