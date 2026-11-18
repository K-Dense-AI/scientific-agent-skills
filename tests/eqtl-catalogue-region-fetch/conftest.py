"""pytest configuration."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: integration test that hits the real EBI eQTL Catalogue FTP",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    import os
    run_live = os.environ.get("RUN_LIVE_TESTS") == "1" or "live" in (config.getoption("-m") or "")
    if run_live:
        return
    skip_live = pytest.mark.skip(reason="live test (set RUN_LIVE_TESTS=1 or pytest -m live)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
