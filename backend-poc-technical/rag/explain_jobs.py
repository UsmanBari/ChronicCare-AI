"""
Background Clinical Explanation Job Runner for ChronicCare AI.

Enforces:
1. In-process daemon worker processing queued explanation jobs.
2. Bounded in-memory FIFO queue (Queue(maxsize=EXPLAIN_QUEUE_MAX), default 50).
3. Lazy worker thread creation on first enqueued job.
4. Independent execution: checkin completion returns immediately with triage level and
   pending status; explanation is generated asynchronously without blocking patient responses.
5. Pacer & 429 retries live inside guarded_explain; worker calls guarded_explain(mode="background").
6. Decided level read directly from stored checkin_results in the database (never from in-memory param).
7. Testable interface supporting synchronous execution with injected clock and sleep callables.
"""

from __future__ import annotations

import copy
import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExplanationJob:
    checkin_id: str
    user_id: str
    condition: str
    readings: Dict[str, Any]
    language: str
    fallback_template: Dict[str, Any]
    store: Optional[Any] = None
    enqueued_at: float = 0.0


class ExplanationJobQueue:
    """Thread-safe bounded job queue for background clinical explanations."""

    def __init__(self, maxsize: Optional[int] = None):
        self._maxsize = maxsize
        self._queue: Optional[queue.Queue] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._running = False

    def _get_queue(self) -> queue.Queue:
        with self._lock:
            if self._queue is None:
                from rag.explain_guards import get_queue_max
                sz = self._maxsize if self._maxsize is not None else get_queue_max()
                self._queue = queue.Queue(maxsize=sz)
            return self._queue

    def qsize(self) -> int:
        if self._queue is None:
            return 0
        return self._queue.qsize()

    def start_worker_if_needed(self) -> None:
        """Lazily creates and starts the background worker thread on first job."""
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._running = True
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="ExplainBackgroundWorker",
                    daemon=True,
                )
                self._worker_thread.start()

    def stop_worker(self, timeout: float = 2.0) -> None:
        """Stops the worker thread (primarily for test teardown)."""
        with self._lock:
            self._running = False
        t = self._worker_thread
        if t and t.is_alive():
            t.join(timeout=timeout)
        with self._lock:
            self._worker_thread = None

    def enqueue_job(
        self,
        checkin_id: str,
        user_id: str,
        condition: str,
        readings: Dict[str, Any],
        language: str,
        fallback_template: Dict[str, Any],
        store: Optional[Any] = None,
        start_worker: bool = True,
    ) -> bool:
        """
        Enqueues an explanation job. Returns True if successfully enqueued,
        or False if queue is full. Starts daemon worker lazily.
        """
        q = self._get_queue()
        job = ExplanationJob(
            checkin_id=checkin_id,
            user_id=user_id,
            condition=condition,
            readings=copy.deepcopy(readings),
            language=language,
            fallback_template=copy.deepcopy(fallback_template),
            store=store,
            enqueued_at=time.monotonic(),
        )
        try:
            q.put_nowait(job)
        except queue.Full:
            logger.warning("Explain background queue full (capacity %d); dropping to template", q.maxsize)
            return False

        if start_worker:
            self.start_worker_if_needed()
        return True

    def _worker_loop(self) -> None:
        while self._running:
            try:
                q = self._get_queue()
                job: ExplanationJob = q.get(timeout=0.5)
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning("Queue error in worker loop: %s", type(e).__name__)
                continue

            try:
                self.process_job(job)
            except Exception as e:
                logger.warning("Unexpected error processing explain job %s: %s", job.checkin_id, type(e).__name__)
            finally:
                q.task_done()

    def process_job(
        self,
        job: ExplanationJob,
        clock_fn: Optional[Callable[[], float]] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Processes a single job:
        1. Reads decided level from the stored checkin_results row in database.
        2. Executes guarded_explain(mode="background").
        3. Updates checkin_results.explanation_json with the final result.
        """
        import data_sources.app_store as app_store
        from rag.explain_guards import get_job_deadline_seconds, guarded_explain

        now_fn = clock_fn or time.monotonic
        nap_fn = sleep_fn or time.sleep

        # Step 1: Read decided level from stored database row (waiting if still writing)
        stored_row = None
        for _ in range(25):
            stored_row = app_store.get_checkin_result(job.checkin_id)
            if stored_row and (stored_row.get("triage_level") or stored_row.get("triage")):
                break
            nap_fn(0.04)

        if not stored_row:
            logger.warning("Checkin result row not found for job %s; falling back to template", job.checkin_id)
            fallback = copy.deepcopy(job.fallback_template)
            fallback["status"] = "ready"
            fallback["mode"] = "template"
            fallback["reason"] = "job_lost"
            fallback["provider"] = None
            fallback["providers_tried"] = []
            fallback["provider_timings"] = {}
            fallback["tokens_used"] = 0
            app_store.update_checkin_explanation(job.checkin_id, fallback)
            return fallback

        decided_level = str(
            stored_row.get("triage_level")
            or (stored_row.get("triage") or {}).get("level", "routine")
        ).lower().strip()

        triage_dict = copy.deepcopy(stored_row.get("triage") or {})
        triage_dict["level"] = decided_level

        # Step 2: Execute guarded_explain in background mode
        deadline_sec = get_job_deadline_seconds()
        try:
            result = guarded_explain(
                triage_result=triage_dict,
                readings=job.readings,
                language=job.language,
                store=job.store,
                condition=job.condition,
                budget_seconds=deadline_sec,
                mode="background",
                clock_fn=clock_fn,
                sleep_fn=sleep_fn,
            )
            result["status"] = "ready"
        except Exception as e:
            logger.warning("guarded_explain raised in background worker: %s", type(e).__name__)
            result = copy.deepcopy(job.fallback_template)
            result["status"] = "ready"
            result["mode"] = "template"
            result["reason"] = "error"
            result["provider"] = None
            result["providers_tried"] = []
            result["provider_timings"] = {}
            result["tokens_used"] = 0

        # Step 3: Update database row
        app_store.update_checkin_explanation(job.checkin_id, result)
        return result


# Module-level singleton
_GLOBAL_JOB_QUEUE = ExplanationJobQueue()


def get_queue_length() -> int:
    return _GLOBAL_JOB_QUEUE.qsize()


def get_explain_queue():
    return _GLOBAL_JOB_QUEUE._get_queue()


def get_job_queue():
    return _GLOBAL_JOB_QUEUE


def enqueue_job(
    checkin_id: str,
    user_id: str,
    condition: str,
    readings: Dict[str, Any],
    language: str,
    fallback_template: Dict[str, Any],
    store: Optional[Any] = None,
) -> bool:
    return _GLOBAL_JOB_QUEUE.enqueue_job(
        checkin_id=checkin_id,
        user_id=user_id,
        condition=condition,
        readings=readings,
        language=language,
        fallback_template=fallback_template,
        store=store,
    )


def execute_job_synchronous(
    job: ExplanationJob,
    clock_fn: Optional[Callable[[], float]] = None,
    sleep_fn: Optional[Callable[[float], None]] = None,
) -> Dict[str, Any]:
    """Helper for testing: runs a job synchronously without background threads."""
    return _GLOBAL_JOB_QUEUE.process_job(job, clock_fn=clock_fn, sleep_fn=sleep_fn)


run_job_synchronous = execute_job_synchronous


def reset_job_queue() -> None:
    """Helper for hermetic test suites."""
    global _GLOBAL_JOB_QUEUE
    _GLOBAL_JOB_QUEUE.stop_worker()
    _GLOBAL_JOB_QUEUE = ExplanationJobQueue()
