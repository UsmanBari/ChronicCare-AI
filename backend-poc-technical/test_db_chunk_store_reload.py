"""
Unit tests for DbChunkStore auto-reload on empty store (PR #135, Hotfix 1, H3).

Verifies:
1. 0 -> reload -> N: When cached store has 0 chunks and >=60s elapse, it reloads and logs "DbChunkStore reloaded: N chunks".
2. No reload storm: Second call inside 60s throttle window does not reload.
3. Non-empty store never reloads: When total_chunks() > 0, store is kept regardless of elapsed time.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from rag import store as rag_store


class FakeChunkStore:
    """Mock ChunkStore that tracks calls and allows dynamic chunk count."""

    def __init__(self, chunk_count: int = 0) -> None:
        self.chunk_count = chunk_count

    def total_chunks(self) -> int:
        return self.chunk_count

    def list_chunks(self, *args, **kwargs):
        return []

    def get_chunk(self, chunk_id: str):
        return None


@pytest.fixture(autouse=True)
def reset_global_store():
    """Ensure clean global store state before and after each test."""
    rag_store._GLOBAL_DB_CHUNK_STORE = None
    rag_store._LAST_EMPTY_STORE_RELOAD_TS = 0.0
    rag_store._LAST_INIT_PARAMS = (None, None, None, None)
    yield
    rag_store._GLOBAL_DB_CHUNK_STORE = None
    rag_store._LAST_EMPTY_STORE_RELOAD_TS = 0.0
    rag_store._LAST_INIT_PARAMS = (None, None, None, None)


def test_empty_store_reloads_to_n_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    """0 -> reload -> N: when empty store is called after 60s and chunks exist, it reloads and logs."""
    # Seed an initially empty store
    rag_store._GLOBAL_DB_CHUNK_STORE = FakeChunkStore(chunk_count=0)
    rag_store._LAST_EMPTY_STORE_RELOAD_TS = 100.0

    # 70 seconds later, chunks are now populated in DB (e.g. 1175 chunks)
    with (
        patch("time.monotonic", return_value=170.0),
        patch.object(rag_store, "DbChunkStore", return_value=FakeChunkStore(chunk_count=1175)),
        caplog.at_level(logging.INFO),
    ):
        reloaded = rag_store.get_db_chunk_store()

    assert reloaded.total_chunks() == 1175
    assert "DbChunkStore reloaded: 1175 chunks" in caplog.text


def test_no_reload_storm_inside_throttle_window() -> None:
    """No reload storm: second call inside 60s does not trigger another reload."""
    initial_store = FakeChunkStore(chunk_count=0)
    rag_store._GLOBAL_DB_CHUNK_STORE = initial_store
    rag_store._LAST_EMPTY_STORE_RELOAD_TS = 100.0

    # Call inside 60s window (e.g. 20s later at t=120)
    with (
        patch("time.monotonic", return_value=120.0),
        patch.object(rag_store, "DbChunkStore") as mock_db_store,
    ):
        res = rag_store.get_db_chunk_store()
        mock_db_store.assert_not_called()

    # Returns the same instance without recreating
    assert res is initial_store


def test_non_empty_store_never_reloads() -> None:
    """A non-empty store (total_chunks() > 0) never reloads regardless of elapsed time."""
    populated_store = FakeChunkStore(chunk_count=1175)
    rag_store._GLOBAL_DB_CHUNK_STORE = populated_store
    rag_store._LAST_EMPTY_STORE_RELOAD_TS = 100.0

    # Call far in the future (t=1000, 900 seconds later)
    with (
        patch("time.monotonic", return_value=1000.0),
        patch.object(rag_store, "DbChunkStore") as mock_db_store,
    ):
        res = rag_store.get_db_chunk_store()
        mock_db_store.assert_not_called()

    assert res is populated_store
    assert res.total_chunks() == 1175
