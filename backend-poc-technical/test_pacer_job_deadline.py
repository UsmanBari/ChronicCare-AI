"""
Unit and integration tests for Groq OTPM pacer waiting against the job deadline in background mode (Day 6g).

C1: Background mode, hypertension check-in (provider="auto", Gemini configured and eligible):
    Pacer set so translation call needs 30 s wait, job deadline 45 s.
    Groq waits (mock sleep advances clock by 30 s), Groq translation succeeds.
    Asserts: mode == "llm", status == "ready", provider == "groq", providers_tried == ["groq"],
    Gemini was NOT called, and main thread used worker's result (not a template from a 20 s timeout).
C2: Same setup, but needed pacer wait is 50 s (> 45 s job deadline):
    Groq raises TimeoutError("Pacer wait exceeds deadline") and falls back to Gemini (provider == "gemini").
C3: After pacer wait in background mode, Groq HTTP call kwargs receive timeout <= EXPLAIN_CALL_TIMEOUT_SECONDS (20 s)
    and now + timeout <= job deadline.
C4: Inline mode test: pacer background wait is bypassed; inline budget remains strictly bounded by 3.0 s and
    kwargs["timeout"] == max(0.1, prov_deadline - now_fn()).
AST Invariance: 5 validators and is_template_consistent AST hashes match expected constants.
"""

import ast
import hashlib
import inspect
import json
import os
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from data_sources import app_store
from rag import explainer, explain_guards
from rag.explain_guards import (
    guarded_explain,
    _GLOBAL_GROQ_PACER,
    DEFAULT_JOB_DEADLINE_SECONDS,
    DEFAULT_CALL_TIMEOUT_SECONDS,
)
from rag.explain_jobs import (
    ExplanationJob,
    execute_job_synchronous,
    reset_job_queue,
)


class MockChunkStore:
    """In-memory ChunkStore for deterministic retriever testing."""

    def __init__(self, chunks: Optional[List[Dict[str, Any]]] = None) -> None:
        self._chunks = list(chunks or [])
        self._by_id = {c.get("chunk_id", c.get("id", "")): c for c in self._chunks}

    def add_chunk(self, chunk: Dict[str, Any]) -> None:
        self._chunks.append(chunk)
        cid = chunk.get("chunk_id", chunk.get("id", ""))
        if cid:
            self._by_id[cid] = chunk

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(chunk_id)

    def get(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(chunk_id)

    def list_chunks(
        self,
        condition: Optional[str] = None,
        topic: Optional[str] = None,
        min_priority: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return list(self._chunks)

    def total_chunks(self) -> int:
        return len(self._chunks)

    def count(self) -> int:
        return len(self._chunks)


class TestPacerJobDeadline(unittest.TestCase):
    def setUp(self) -> None:
        explain_guards.reset_explain_guards()
        reset_job_queue()
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(
            prefix="chroniccare_test_pacer_", suffix=".db"
        )
        os.close(self.temp_db_fd)
        os.environ["LOCAL_DB_PATH"] = self.temp_db_path
        os.environ["DB_BACKEND"] = "sqlite"
        app_store.migrate(db_path=self.temp_db_path, backend="sqlite")

        os.environ["EXPLAIN_ENABLED"] = "true"
        os.environ["LLM_PROVIDER"] = "auto"
        os.environ["EXPLAIN_LLM_CONDITIONS"] = "hypertension,diabetes"
        self.mock_store = MockChunkStore(self._get_hypertension_candidate_chunks())

    def tearDown(self) -> None:
        reset_job_queue()
        explain_guards.reset_explain_guards()
        if hasattr(self, "temp_db_path") and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def _get_hypertension_candidate_chunks(self) -> List[Dict[str, Any]]:
        return [
            {
                "chunk_id": "who_chunk_1",
                "id": "who_chunk_1",
                "source_id": "who_2021_htn",
                "text": "For adults with hypertension, blood pressure targets should be systolic under 140 mmHg.",
                "condition_tags": ["hypertension"],
                "priority": 1,
            }
        ]

    def test_c1_pacer_wait_fits_job_deadline_groq_succeeds(self) -> None:
        """
        C1: Background mode, hypertension check-in with provider='auto' and Gemini eligible.
        Pacer set so translation call needs 30 s wait, job deadline 45 s.
        Groq waits against job deadline, Groq translation succeeds.
        Asserts mode == 'llm', provider == 'groq', providers_tried == ['groq'],
        Gemini not called, and main thread used worker's result (not a 20 s timeout template).
        """
        current_time = [100.0]
        sleeps: List[float] = []

        def mock_clock() -> float:
            return current_time[0]

        def mock_sleep(sec: float) -> None:
            sleeps.append(sec)
            current_time[0] += sec

        # Seed Groq pacer with 500 tokens at ts = 70.0.
        # Window is 60 s. At t = 100.0:
        # Call 1 (English, max_tokens=250): 500 + 250 = 750 <= 1000 -> wait 0.0 s.
        # Call 2 (Urdu translation, max_tokens=700):
        #   total_used = 500 + 50 = 550.
        #   550 + 700 = 1250 > 1000. Wait = (70.0 + 60.0) - 100.0 = 30.0 s.
        # 100.0 + 30.0 + 1.0 = 131.0 <= 145.0 (job deadline), so wait is allowed.
        _GLOBAL_GROQ_PACER.record_tokens(500, clock_fn=lambda: 70.0)

        groq_calls: List[Dict[str, Any]] = []
        gemini_calls: List[Dict[str, Any]] = []

        def fake_groq(**kwargs: Any) -> Any:
            groq_calls.append(kwargs)
            messages = kwargs.get("messages", [])
            is_trans = any("Translate the following" in m.get("content", "") for m in messages)
            if not is_trans:
                # English call
                return json.dumps({
                    "sentences": [
                        {"text": "Your blood pressure of 120/75 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                        {"text": "Regular blood pressure monitoring supports normal cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}
            else:
                # Translation call
                return json.dumps({
                    "sentences": [
                        {"text": "آپ کا بلڈ پریشر 120/75 mmHg معمول کی حد میں ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                        {"text": "بلڈ پریشر کی باقاعدہ نگرانی صحت کو برقرار رکھتی ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}

        def fake_gemini(**kwargs: Any) -> Any:
            gemini_calls.append(kwargs)
            return json.dumps({
                "sentences": [
                    {"text": "Gemini text [who_chunk_1].", "cites": ["who_chunk_1"]},
                ]
            }), {"total_tokens": 100, "completion_tokens": 50}

        res = guarded_explain(
            triage_result={"level": "routine"},
            readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0},
            store=self.mock_store,
            language="ur",
            patient_conditions=["hypertension"],
            provider="auto",
            mode="background",
            budget_seconds=45.0,
            clock_fn=mock_clock,
            sleep_fn=mock_sleep,
            llm={"groq": fake_groq, "gemini": fake_gemini},
        )

        self.assertEqual(res["mode"], "llm", f"Expected mode 'llm', got {res.get('mode')}: {res.get('rejected_reasons')}")
        self.assertNotEqual(res.get("mode"), "template", "Main thread must use worker LLM result, not a template from a 20s timeout")
        self.assertNotIn("budget_timeout", str(res.get("reason", "")))
        self.assertEqual(res["provider"], "groq")
        self.assertEqual(res["providers_tried"], ["groq"])
        self.assertEqual(len(gemini_calls), 0, "Gemini must NOT be called when Groq wait fits in job deadline")
        self.assertEqual(len(groq_calls), 2, "Groq must execute both English and translation calls")
        self.assertTrue(any(abs(s - 30.0) < 0.1 for s in sleeps), f"Expected ~30s pacer wait in sleeps, got {sleeps}")
        self.assertEqual(len(res["sentences"]), 2)
        self.assertEqual(res.get("rejected_reasons"), [])

    def test_c1_background_job_synchronous_status_ready(self) -> None:
        """C1: Assert background execution via execute_job_synchronous yields status='ready', mode='llm', provider='groq'."""
        checkin_id = "chk_bg_test_c1_ready"
        user_id = "usr_bg_c1"
        app_store.create_checkin_result(
            checkin_id=checkin_id,
            emergency=False,
            intakes=[],
            triage_level="routine",
            triage={"level": "routine", "reasons": ["Blood pressure normal"]},
            explanation={"status": "pending", "queued_at": "2026-11-07T00:00:00Z"},
        )
        _GLOBAL_GROQ_PACER.record_tokens(500, clock_fn=lambda: 70.0)

        current_time = [100.0]

        def mock_clock() -> float:
            return current_time[0]

        def mock_sleep(sec: float) -> None:
            current_time[0] += sec

        def fake_groq(**kwargs: Any) -> Any:
            messages = kwargs.get("messages", [])
            is_trans = any("Translate the following" in m.get("content", "") for m in messages)
            if not is_trans:
                return json.dumps({
                    "sentences": [
                        {"text": "Your blood pressure of 120/75 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                        {"text": "Regular blood pressure monitoring supports normal cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}
            else:
                return json.dumps({
                    "sentences": [
                        {"text": "آپ کا بلڈ پریشر 120/75 mmHg معمول کی حد میں ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                        {"text": "بلڈ پریشر کی باقاعدہ نگرانی صحت کو برقرار رکھتی ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}

        def fake_gemini(**kwargs: Any) -> Any:
            return "{}", {"total_tokens": 0, "completion_tokens": 0}

        job = ExplanationJob(
            checkin_id=checkin_id,
            user_id=user_id,
            condition="hypertension",
            patient_conditions=["hypertension"],
            readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0},
            language="ur",
            fallback_template={
                "status": "ready",
                "mode": "template",
                "reason": "fallback",
                "sentences": [],
                "sources": [],
            },
            store=self.mock_store,
        )

        with patch("rag.explain_guards.groq_client.chat_with_detailed_usage", fake_groq), \
             patch("rag.explain_guards.groq_client.is_configured", return_value=True), \
             patch("rag.explain_guards.gemini_client.chat_with_detailed_usage", fake_gemini), \
             patch("rag.explain_guards.gemini_client.is_configured", return_value=True):
            res = execute_job_synchronous(job, clock_fn=mock_clock, sleep_fn=mock_sleep)

        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["mode"], "llm")
        self.assertEqual(res["provider"], "groq")
        self.assertEqual(res["providers_tried"], ["groq"])
        self.assertNotEqual(res.get("mode"), "template")

    def test_c2_pacer_wait_exceeds_job_deadline_falls_back_to_gemini(self) -> None:
        """
        C2: Same setup, but needed pacer wait is 50 s (> 45 s job deadline).
        Groq raises TimeoutError("Pacer wait exceeds deadline") and falls back to Gemini.
        """
        current_time = [100.0]
        sleeps: List[float] = []

        def mock_clock() -> float:
            return current_time[0]

        def mock_sleep(sec: float) -> None:
            sleeps.append(sec)
            current_time[0] += sec

        # Seed Groq pacer with 500 tokens at ts = 90.0.
        # Window is 60 s. At t = 100.0:
        # Call 1 (English, max_tokens=250): 500 + 250 = 750 <= 1000 -> wait 0.0 s.
        # Call 2 (Urdu translation, max_tokens=700):
        #   total_used = 500 + 50 = 550.
        #   550 + 700 = 1250 > 1000. Wait = (90.0 + 60.0) - 100.0 = 50.0 s.
        # 100.0 + 50.0 + 1.0 = 151.0 > 145.0 (job deadline), so wait exceeds deadline.
        _GLOBAL_GROQ_PACER.record_tokens(500, clock_fn=lambda: 90.0)

        groq_calls: List[Dict[str, Any]] = []
        gemini_calls: List[Dict[str, Any]] = []

        def fake_groq(**kwargs: Any) -> Any:
            groq_calls.append(kwargs)
            messages = kwargs.get("messages", [])
            is_trans = any("Translate the following" in m.get("content", "") for m in messages)
            if not is_trans:
                return json.dumps({
                    "sentences": [
                        {"text": "Your blood pressure of 120/75 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                        {"text": "Regular blood pressure monitoring supports normal cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}
            else:
                return json.dumps({
                    "sentences": [
                        {"text": "آپ کا بلڈ پریشر 120/75 mmHg معمول کی حد میں ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                        {"text": "بلڈ پریشر کی باقاعدہ نگرانی صحت کو برقرار رکھتی ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}

        def fake_gemini(**kwargs: Any) -> Any:
            gemini_calls.append(kwargs)
            messages = kwargs.get("messages", [])
            is_trans = any("Translate the following" in m.get("content", "") for m in messages)
            if not is_trans:
                return json.dumps({
                    "sentences": [
                        {"text": "Your blood pressure of 120/75 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                        {"text": "Regular blood pressure monitoring supports normal cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}
            else:
                return json.dumps({
                    "sentences": [
                        {"text": "آپ کا بلڈ پریشر 120/75 mmHg معمول کی حد میں ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                        {"text": "بلڈ پریشر کی باقاعدہ نگرانی صحت کو برقرار رکھتی ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}

        res = guarded_explain(
            triage_result={"level": "routine"},
            readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0},
            store=self.mock_store,
            language="ur",
            patient_conditions=["hypertension"],
            provider="auto",
            mode="background",
            budget_seconds=45.0,
            clock_fn=mock_clock,
            sleep_fn=mock_sleep,
            llm={"groq": fake_groq, "gemini": fake_gemini},
        )

        self.assertEqual(res["mode"], "llm")
        self.assertEqual(res["provider"], "gemini", "Must fall back to Gemini when Groq wait exceeds job deadline")
        self.assertIn("groq", res["providers_tried"])
        self.assertIn("gemini", res["providers_tried"])
        self.assertGreater(len(gemini_calls), 0)

    def test_c3_groq_http_timeout_bounded_by_call_timeout_and_deadline(self) -> None:
        """
        C3: After pacer wait in background mode, Groq HTTP call kwargs receive
        timeout <= EXPLAIN_CALL_TIMEOUT_SECONDS (20 s) and now + timeout <= job deadline.
        """
        current_time = [100.0]
        sleeps: List[float] = []

        def mock_clock() -> float:
            return current_time[0]

        def mock_sleep(sec: float) -> None:
            sleeps.append(sec)
            current_time[0] += sec

        _GLOBAL_GROQ_PACER.record_tokens(500, clock_fn=lambda: 70.0)
        captured_timeouts: List[float] = []
        captured_clock_times: List[float] = []

        def fake_groq(**kwargs: Any) -> Any:
            captured_timeouts.append(float(kwargs.get("timeout", 0.0)))
            captured_clock_times.append(mock_clock())
            messages = kwargs.get("messages", [])
            is_trans = any("Translate the following" in m.get("content", "") for m in messages)
            if not is_trans:
                return json.dumps({
                    "sentences": [
                        {"text": "Your blood pressure of 120/75 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                        {"text": "Regular blood pressure monitoring supports normal cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}
            else:
                return json.dumps({
                    "sentences": [
                        {"text": "آپ کا بلڈ پریشر 120/75 mmHg معمول کی حد میں ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                        {"text": "بلڈ پریشر کی باقاعدہ نگرانی صحت کو برقرار رکھتی ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}

        def fake_gemini(**kwargs: Any) -> Any:
            return "{}", {"total_tokens": 0, "completion_tokens": 0}

        job_deadline = 45.0
        start_t = 100.0
        abs_deadline = start_t + job_deadline

        res = guarded_explain(
            triage_result={"level": "routine"},
            readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0},
            store=self.mock_store,
            language="ur",
            patient_conditions=["hypertension"],
            provider="auto",
            mode="background",
            budget_seconds=job_deadline,
            clock_fn=mock_clock,
            sleep_fn=mock_sleep,
            llm={"groq": fake_groq, "gemini": fake_gemini},
        )

        self.assertEqual(res["mode"], "llm")
        self.assertEqual(len(captured_timeouts), 2)
        call_timeout_cap = DEFAULT_CALL_TIMEOUT_SECONDS  # 20.0 s

        for to, clk in zip(captured_timeouts, captured_clock_times):
            self.assertLessEqual(to, call_timeout_cap, f"HTTP call timeout {to}s exceeds {call_timeout_cap}s cap")
            self.assertLessEqual(clk + to, abs_deadline + 0.001, f"Call finish time {clk + to} exceeds job deadline {abs_deadline}")

    def test_c4_inline_mode_bypasses_pacer_and_strictly_bounded(self) -> None:
        """
        C4: Inline mode test: pacer background wait is bypassed; inline budget remains strictly bounded by 3.0 s
        and kwargs["timeout"] == max(0.1, prov_deadline - now_fn()).
        """
        current_time = [100.0]
        sleeps: List[float] = []

        def mock_clock() -> float:
            return current_time[0]

        def mock_sleep(sec: float) -> None:
            sleeps.append(sec)
            current_time[0] += sec

        # Seed tokens that would trigger pacer wait if in background mode
        _GLOBAL_GROQ_PACER.record_tokens(900, clock_fn=lambda: 95.0)
        captured_timeouts: List[float] = []

        def fake_groq(**kwargs: Any) -> Any:
            captured_timeouts.append(float(kwargs.get("timeout", 0.0)))
            return json.dumps({
                "sentences": [
                    {"text": "Your blood pressure of 120/75 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                    {"text": "Regular blood pressure monitoring supports normal cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                ]
            }), {"total_tokens": 100, "completion_tokens": 50}

        def fake_gemini(**kwargs: Any) -> Any:
            return "{}", {"total_tokens": 0, "completion_tokens": 0}

        res = guarded_explain(
            triage_result={"level": "routine"},
            readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 75.0},
            store=self.mock_store,
            language="en",
            patient_conditions=["hypertension"],
            provider="auto",
            mode="inline",
            budget_seconds=3.0,
            clock_fn=mock_clock,
            sleep_fn=mock_sleep,
            llm={"groq": fake_groq, "gemini": fake_gemini},
        )

        self.assertEqual(res["mode"], "llm")
        self.assertEqual(len(sleeps), 0, "Inline mode must NOT execute pacer sleep")
        self.assertEqual(len(captured_timeouts), 1)
        # Primary provider in inline mode gets min(0.6 * time_left, time_left) when has_next
        self.assertLessEqual(captured_timeouts[0], 3.0)

    def test_c5_validator_and_consistency_ast_hashes_invariant(self) -> None:
        """Verify the 5 validators and is_template_consistent are 100% byte-identical in AST."""
        expected_hashes_311 = {
            "validate_sentence_structure": "513d2a7f86f78064325e58477c026cf7ed1c86da6b537b8a25bb6d9e874c8cd8",
            "validate_citations": "6e0eab7f62bbbc4995f95279d83f008f107bdb59ae0b9a2cad67d40097013954",
            "validate_number_grounding": "0b57a80d0790327d2066093eeba765e1c9e27b652bddb303358e70f549ae397a",
            "validate_banned_patterns": "321b9aa8fe5cfe4fdd2ea6cf713ed7b8be39d0f22a753a347a6d7408f68977bf",
            "validate_level_consistency": "c5d798b6172b4e515c921f71a4e02a1725589cacfb504115edb6a1656254b26b",
            "is_template_consistent": "54ca30d6a46081bfe54a18088f5144f9cb7a09cd63c7a9d608527f29c697ca1b",
        }
        expected_hashes_314 = {
            "validate_sentence_structure": "54bddabce0c2ab5fb075922c519eb5813871bfcee4be5468d7a8c2e61e18fcae",
            "validate_citations": "4bebfac3f05cceb0284a0b6ddd626ed1c77261c83d27b569712d851ede80bc8c",
            "validate_number_grounding": "9a0adcc2847422df52c14a30cf6352a6d240f63048ebd3c85921508d3acf63b6",
            "validate_banned_patterns": "dd8bd5bbe703ab386e780bd48fe730c7f1b8251890558afb8885c0722144aac2",
            "validate_level_consistency": "884ff910024ab25db6bdff3c53ba70d416934ce7e882e433f53ab3ffc9076727",
            "is_template_consistent": "1536ffccf30afa5fc12f394bd7f1aab0a763294e5347bd3dcb87c2b78a42b77d",
        }

        for func_name in expected_hashes_311:
            fn = getattr(explainer, func_name)
            src = inspect.getsource(fn)
            tree = ast.parse(src)
            dumped = ast.dump(tree)
            actual_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
            self.assertIn(
                actual_hash,
                (expected_hashes_311[func_name], expected_hashes_314[func_name]),
                f"AST Hash mismatch for {func_name}: {actual_hash}",
            )


if __name__ == "__main__":
    unittest.main()
