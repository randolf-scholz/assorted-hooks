r"""Tests for rewriting absolute imports within the current package."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from assorted_hooks.ast.rewrite_absolute_imports import check_file, get_package_parts


def test_get_package_parts() -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tempdir:
        src = Path(tempdir) / "src"
        pkg = src / "assorted_hooks" / "ast"
        pkg.mkdir(parents=True)
        (src / "assorted_hooks" / "__init__.py").write_text("", encoding="utf8")
        (pkg / "__init__.py").write_text("", encoding="utf8")
        file = pkg / "module.py"
        file.write_text("", encoding="utf8")

        assert get_package_parts(file) == ("assorted_hooks", "ast")


def test_check_file_rewrites_same_package_imports(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tempdir:
        src = Path(tempdir) / "src"
        pkg = src / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf8")

        file = pkg / "module_a.py"
        file.write_text(
            dedent(
                """
                from lib.sublib.pkg.module_b import foo
                from lib.sublib.pkg.subpkg.module_c import bar
                from lib.sublib.other.module_d import baz
                """
            ).lstrip(),
            encoding="utf8",
        )

        assert check_file(file) == 2
        assert (
            file.read_text(encoding="utf8")
            == dedent(
                """
            from lib.sublib.pkg.module_b import foo
            from lib.sublib.pkg.subpkg.module_c import bar
            from lib.sublib.other.module_d import baz
            """
            ).lstrip()
        )
        captured = capsys.readouterr()
        assert "module_a.py:1:" in captured.out
        assert "module_a.py:2:" in captured.out

        assert check_file(file, fix=True) == 2
        assert (
            file.read_text(encoding="utf8")
            == dedent(
                """
            from .module_b import foo
            from .subpkg.module_c import bar
            from lib.sublib.other.module_d import baz
            """
            ).lstrip()
        )


def test_check_file_does_not_rewrite_parent_package_imports(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tempdir:
        src = Path(tempdir) / "src"
        pkg = src / "pkg" / "subpkg"
        pkg.mkdir(parents=True)
        (src / "pkg" / "__init__.py").write_text("", encoding="utf8")
        (pkg / "__init__.py").write_text("", encoding="utf8")

        file = pkg / "module_a.py"
        original = dedent(
            """
            from lib.sublib.pkg.module_b import foo
            from lib.sublib.pkg.subpkg.module_c import bar
            """
        ).lstrip()
        file.write_text(original, encoding="utf8")

        assert check_file(file) == 1
        assert file.read_text(encoding="utf8") == original
        captured = capsys.readouterr()
        assert "module_a.py:2:" in captured.out

        assert check_file(file, fix=True) == 1
        assert (
            file.read_text(encoding="utf8")
            == dedent(
                """
            from lib.sublib.pkg.module_b import foo
            from .module_c import bar
            """
            ).lstrip()
        )


def test_check_file_rewrites_package_root_import(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tempdir:
        src = Path(tempdir) / "src"
        pkg = src / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf8")

        file = pkg / "module_a.py"
        file.write_text("from lib.sublib.pkg import module_b\n", encoding="utf8")

        assert check_file(file) == 1
        assert (
            file.read_text(encoding="utf8") == "from lib.sublib.pkg import module_b\n"
        )
        captured = capsys.readouterr()
        assert "module_a.py:1:" in captured.out

        assert check_file(file, fix=True) == 1
        assert file.read_text(encoding="utf8") == "from . import module_b\n"


def test_check_init_file_rewrites_package_import(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tempdir:
        src = Path(tempdir) / "src"
        pkg = src / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(
            "from lib.sublib.pkg import module_a, module_b\n", encoding="utf8"
        )

        file = pkg / "__init__.py"

        assert check_file(file) == 1
        assert file.read_text(encoding="utf8") == (
            "from lib.sublib.pkg import module_a, module_b\n"
        )
        captured = capsys.readouterr()
        assert "__init__.py:1:" in captured.out

        assert check_file(file, fix=True) == 1
        assert file.read_text(encoding="utf8") == "from . import module_a, module_b\n"
