import os
import pytest

@pytest.fixture(autouse=True)
def manage_require_inclusion(request, monkeypatch):
    """
    Sets REQUIRE_INCLUSION=0 for every test unless marked with @pytest.mark.inclusion,
    where it defaults to REQUIRE_INCLUSION=1.
    """
    marker = request.node.get_closest_marker("inclusion")
    if marker is not None:
        monkeypatch.setenv("REQUIRE_INCLUSION", "1")
    else:
        monkeypatch.setenv("REQUIRE_INCLUSION", "0")
