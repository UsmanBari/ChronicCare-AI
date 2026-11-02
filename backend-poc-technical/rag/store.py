"""
ChunkStore protocol and JSONL implementation for ChronicCare AI RAG.
Provides clean abstraction for chunk retrieval across development and production.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChunkStore(Protocol):
    """Protocol defining the chunk storage interface."""

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Retrieve a single chunk by chunk_id, or None if not found."""
        ...

    def list_chunks(
        self,
        condition: str | None = None,
        topic: str | None = None,
        min_priority: int | None = None,
    ) -> list[dict[str, Any]]:
        """List chunks optionally filtered by condition, topic, and minimum priority."""
        ...

    def total_chunks(self) -> int:
        """Return the total number of chunks stored."""
        ...


class JsonlChunkStore:
    """
    In-memory chunk store populated from a JSONL file.
    Used for local development, test suites, and hermetic CI evaluations.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"JSONL chunk store file does not exist: {self.path}")

        self._by_id: dict[str, dict[str, Any]] = {}
        self._chunks: list[dict[str, Any]] = []

        with open(self.path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON at line {line_num} in {self.path}: {exc}") from exc

                cid = str(data.get("chunk_id", "")).strip()
                if not cid:
                    continue
                self._by_id[cid] = data
                self._chunks.append(data)

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self._by_id.get(chunk_id)

    def list_chunks(
        self,
        condition: str | None = None,
        topic: str | None = None,
        min_priority: int | None = None,
    ) -> list[dict[str, Any]]:
        results = self._chunks

        if condition is not None:
            c_norm = condition.lower().strip()
            # If chunk condition matches target or is general/both
            results = [
                c for c in results
                if c.get("condition", "").lower() in (c_norm, "both", "general", "")
            ]

        if topic is not None:
            t_norm = topic.lower().strip()
            results = [
                c for c in results
                if t_norm in [str(t).lower().strip() for t in c.get("topics", [])]
            ]

        if min_priority is not None:
            results = [
                c for c in results
                if int(c.get("priority", 0)) >= min_priority
            ]

        return results

    def total_chunks(self) -> int:
        return len(self._chunks)

    def all_chunks(self) -> list[dict[str, Any]]:
        return list(self._chunks)


class DbChunkStore:
    """
    In-memory chunk store populated from the database guideline_chunks table.
    Loaded once at startup when EXPLAIN_ENABLED=true.
    Implements the ChunkStore protocol with identical filtering to JsonlChunkStore.
    """

    def __init__(
        self,
        backend: str | None = None,
        db_path: str | None = None,
        mysql_url: str | None = None,
        ssl_ca: str | None = None,
    ) -> None:
        self._by_id: dict[str, dict[str, Any]] = {}
        self._chunks: list[dict[str, Any]] = []
        self._load(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca)

    def _load(
        self,
        backend: str | None = None,
        db_path: str | None = None,
        mysql_url: str | None = None,
        ssl_ca: str | None = None,
    ) -> None:
        from data_sources.app_store import get_db_cursor
        with get_db_cursor(backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca) as (cursor, be, ph):
            cursor.execute(
                """
                SELECT chunk_id, source_id, title, edition, priority, section_path,
                       page_start, page_end, grade, condition, topics_json, text, loaded_at
                FROM guideline_chunks
                """
            )
            rows = cursor.fetchall()
            for row in rows:
                d = dict(row)
                topics_raw = d.pop("topics_json", None)
                if topics_raw:
                    try:
                        d["topics"] = json.loads(topics_raw)
                    except Exception:
                        d["topics"] = []
                else:
                    d["topics"] = []
                cid = str(d.get("chunk_id", "")).strip()
                if not cid:
                    continue
                self._by_id[cid] = d
                self._chunks.append(d)

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self._by_id.get(chunk_id)

    def list_chunks(
        self,
        condition: str | None = None,
        topic: str | None = None,
        min_priority: int | None = None,
    ) -> list[dict[str, Any]]:
        results = self._chunks

        if condition is not None:
            c_norm = condition.lower().strip()
            results = [
                c for c in results
                if c.get("condition", "").lower() in (c_norm, "both", "general", "")
            ]

        if topic is not None:
            t_norm = topic.lower().strip()
            results = [
                c for c in results
                if t_norm in [str(t).lower().strip() for t in c.get("topics", [])]
            ]

        if min_priority is not None:
            results = [
                c for c in results
                if int(c.get("priority", 0)) >= min_priority
            ]

        return results

    def total_chunks(self) -> int:
        return len(self._chunks)

    def all_chunks(self) -> list[dict[str, Any]]:
        return list(self._chunks)


_GLOBAL_DB_CHUNK_STORE: DbChunkStore | None = None


def get_db_chunk_store(
    backend: str | None = None,
    db_path: str | None = None,
    mysql_url: str | None = None,
    ssl_ca: str | None = None,
    force_reload: bool = False,
) -> DbChunkStore:
    """Retrieve or initialize the global DbChunkStore singleton."""
    global _GLOBAL_DB_CHUNK_STORE
    if _GLOBAL_DB_CHUNK_STORE is None or force_reload:
        _GLOBAL_DB_CHUNK_STORE = DbChunkStore(
            backend=backend, db_path=db_path, mysql_url=mysql_url, ssl_ca=ssl_ca
        )
    return _GLOBAL_DB_CHUNK_STORE
