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
