r"""Tests for ``update_requirements``."""

import pytest

from assorted_hooks.standalone import update_requirements


@pytest.mark.parametrize(
    ("declared_version", "installed_version", "expected_version"),
    [
        ("1.2.0", "1.3.0.dev2", "1.3.0.dev2"),
        ("1.3.0", "1.3.0.dev2", "1.3.0"),
        ("1.3.0a1", "1.3.0b1", "1.3.0b1"),
        ("1.2.0", "v1.3-dev2", "1.3.dev2"),
    ],
)
def test_update_versions_uses_pep440_precedence(
    monkeypatch: pytest.MonkeyPatch,
    declared_version: str,
    installed_version: str,
    expected_version: str,
) -> None:
    monkeypatch.setattr(
        update_requirements,
        "PKG_DICT",
        {update_requirements.canonicalize_name("example"): installed_version},
    )

    result = update_requirements.update_versions(
        f'"example>={declared_version}"',
        dependency_pattern=update_requirements.RE_PROJECT_DEP_GROUP,
    )

    assert result == f'"example>={expected_version}"'
