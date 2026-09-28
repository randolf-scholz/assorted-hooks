"""Tests for the __all__ checker."""

import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from assorted_hooks.ast.check_dunder_all import check_file, main


@pytest.fixture
def module_file() -> Iterator[Path]:
    """Create a module with exports that trigger both new warnings."""
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tempdir:
        path = Path(tempdir) / "module.py"
        path.write_text(
            '__all__ = ["public", "_private", "not-an-identifier"]\n\nvalue = None\n',
            encoding="utf8",
        )
        yield path


def test_check_file_warns_for_private_exports(
    module_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_file(module_file, warn_not_identifier=False) == 1

    captured = capsys.readouterr()
    assert "__all__ contains private export" in captured.out
    assert "_private" in captured.out


def test_check_file_can_ignore_private_exports(
    module_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        check_file(
            module_file,
            warn_not_identifier=False,
            warn_private_export=False,
        )
        == 0
    )

    assert capsys.readouterr().out == ""


def test_check_file_warns_for_non_identifiers(
    module_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_file(module_file, warn_private_export=False) == 1

    captured = capsys.readouterr()
    assert "__all__ contains non-identifier" in captured.out
    assert "not-an-identifier" in captured.out


def test_check_file_can_ignore_non_identifiers(
    module_file: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        check_file(
            module_file,
            warn_not_identifier=False,
            warn_private_export=False,
        )
        == 0
    )

    assert capsys.readouterr().out == ""


def test_main_can_disable_new_warnings(
    module_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check-dunder-all",
            "--no-warn-not-identifier",
            "--no-warn-private-export",
            str(module_file),
        ],
    )

    main()

    assert capsys.readouterr().out == ""
