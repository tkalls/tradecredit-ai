"""Smoke test: proves the toolchain runs. Replace with real tests from Week 2."""

import app


def test_app_package_imports() -> None:
    assert app.__doc__ is not None
