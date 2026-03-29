"""Smoke test — verifies test infrastructure is functional."""


def test_conftest_loads() -> None:
    """Confirm conftest fixtures are importable."""
    from tests.conftest import mock_settings, test_client, test_db  # noqa: F401

    assert True
