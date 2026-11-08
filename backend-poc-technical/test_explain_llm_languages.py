"""
Unit and integration tests for EXPLAIN_LLM_LANGUAGES switch (Day 7a, Usman Bari).

Verifies:
- T1: EXPLAIN_LLM_LANGUAGES=en: English check-in calls fake LLM (mode llm); ur and roman_ur check-ins
      make ZERO LLM calls, get reviewed templates in their respective languages with reason 'language_template_only'.
      Tested across both inline and background paths.
- T2: Default (unset): today's behavior (ur gets LLM + translation) - proves nothing changed by default.
- T3: EXPLAIN_LLM_LANGUAGES="" or "xx" falls back strictly to "en".
- T4: Both diabetes and hypertension covered for T1.
- T5: Patient view (/complete and GET /api/checkins/{id}/explanation) never contains 'language_template_only', mode, or reason.
- Note 1: In guarded_explain, the language gate runs BEFORE cache lookup; unpermitted language never gets cached LLM answer.
- AST Invariance: 5 validators and is_template_consistent AST hashes match Python 3.11 baseline.
"""

import ast
import copy
import hashlib
import inspect
import json
import os
import sys
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from data_sources import app_store
from llm import gemini_client, groq_client
from agents.adaptive_interview_agent import InterviewState
from orchestrator.steps import _build_patient_explain_view, step_explain
from rag import explainer, explain_guards
from rag.explain_guards import (
    DEFAULT_LLM_LANGUAGES,
    compute_cache_key,
    get_explain_llm_languages,
    guarded_explain,
    is_language_allowed_for_llm,
    reset_explain_guards,
)
from rag.explain_jobs import (
    ExplanationJob,
    execute_job_synchronous,
    get_job_queue,
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


class TestExplainLllmLanguages(unittest.TestCase):
    def setUp(self) -> None:
        explain_guards.reset_explain_guards()
        reset_job_queue()
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(
            prefix="chroniccare_test_lang_", suffix=".db"
        )
        os.close(self.temp_db_fd)
        os.environ["LOCAL_DB_PATH"] = self.temp_db_path
        os.environ["DB_BACKEND"] = "sqlite"
        app_store.migrate(db_path=self.temp_db_path, backend="sqlite")

        self.mock_store = MockChunkStore()
        # WHO 2021 chunk
        self.mock_store.add_chunk({
            "chunk_id": "who_chunk_1",
            "source_id": "who_2021_htn",
            "title": "WHO Hypertension Guidelines 2021",
            "section_path": "Blood pressure targets",
            "condition": "hypertension",
            "text": "Regular blood pressure monitoring supports normal cardiovascular health. Blood pressure under 140/90 mmHg is standard target.",
            "full_citation": "WHO Guidelines for pharmacological treatment of hypertension",
            "doi": "10.1234/who.2021.htn",
            "priority": 5,
        })
        # ADA 2026 chunk
        self.mock_store.add_chunk({
            "chunk_id": "ada_chunk_1",
            "source_id": "ada_2026_sec06",
            "title": "ADA Standards of Care 2026",
            "section_path": "Glycemic targets",
            "condition": "diabetes",
            "text": "Fasting blood glucose 80-130 mg/dL is standard glycemic target for nonpregnant adults with diabetes.",
            "full_citation": "American Diabetes Association Standards of Care in Diabetes-2026",
            "doi": "10.2337/dc26-S006",
            "priority": 10,
        })

    def tearDown(self) -> None:
        explain_guards.reset_explain_guards()
        reset_job_queue()
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def _drive_checkin(
        self,
        conditions: List[str],
        language: str,
        mode: str,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Drives a check-in through step_explain with instrumented fake LLM."""
        explain_guards.reset_explain_guards()
        reset_job_queue()

        llm_calls: List[Dict[str, Any]] = []

        def fake_groq_chat(**kwargs: Any) -> Tuple[str, Dict[str, Any]]:
            llm_calls.append(kwargs)
            messages = kwargs.get("messages", [])
            is_trans = any("Translate the following" in m.get("content", "") for m in messages)
            if not is_trans:
                if "diabetes" in conditions and "hypertension" not in conditions:
                    return json.dumps({
                        "sentences": [
                            {"text": "Your fasting glucose of 110 mg/dL is within target range [ada_chunk_1].", "cites": ["ada_chunk_1"]},
                            {"text": "Regular monitoring supports diabetes management [ada_chunk_1].", "cites": ["ada_chunk_1"]},
                        ]
                    }), {"total_tokens": 100, "completion_tokens": 50}
                else:
                    return json.dumps({
                        "sentences": [
                            {"text": "Your blood pressure of 125/80 mmHg is within routine target range [who_chunk_1].", "cites": ["who_chunk_1"]},
                            {"text": "Regular blood pressure monitoring supports cardiovascular health [who_chunk_1].", "cites": ["who_chunk_1"]},
                        ]
                    }), {"total_tokens": 100, "completion_tokens": 50}
            else:
                return json.dumps({
                    "sentences": [
                        {"text": "آپ کا بلڈ پریشر 125/80 معمول کی حد میں ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                        {"text": "بلڈ پریشر کی باقاعدہ نگرانی دل کی صحت کے لیے مفید ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]},
                    ]
                }), {"total_tokens": 100, "completion_tokens": 50}

        readings = (
            {"glucose": 110.0}
            if "diabetes" in conditions and "hypertension" not in conditions
            else {"blood_pressure_systolic": 125.0, "blood_pressure_diastolic": 80.0}
        )
        state = InterviewState(
            patient_id=f"pat_{mode}_{language}_{'_'.join(conditions)}",
            conditions_on_file=list(conditions),
            intakes=[{"readings": readings}],
        )
        triage_decision = {
            "final_triage_level": "routine",
            "final_requires_review": False,
            "final_max_sev": "none",
            "review_status": "open",
            "triage_dict": {"level": "routine"},
        }
        user_id = f"usr_{mode}_{language}"
        checkin_id = f"chk_{mode}_{int(time.time() * 1000)}"

        base_env = {
            "EXPLAIN_ENABLED": "true",
            "EXPLAIN_MODE": mode,
            "EXPLAIN_LLM_CONDITIONS": "hypertension,diabetes",
            "LLM_PROVIDER": "groq",
        }
        if env_overrides:
            base_env.update(env_overrides)

        with patch.dict(os.environ, base_env):
            with patch.object(groq_client, "is_configured", new=lambda: True), \
                 patch.object(gemini_client, "is_configured", new=lambda: False), \
                 patch.object(groq_client, "chat_with_detailed_usage", new=fake_groq_chat), \
                 patch.object(groq_client, "chat_with_usage", new=lambda **kw: (fake_groq_chat(**kw)[0], 50)), \
                 patch.object(get_job_queue(), "start_worker_if_needed", lambda: None):

                if mode == "inline":
                    res = step_explain(
                        user_id=user_id,
                        state=state,
                        triage_decision=triage_decision,
                        get_patient_profile_fn=lambda uid: {"conditions": conditions, "language": language},
                        store=self.mock_store,
                        llm={"groq": fake_groq_chat},
                        checkin_id=checkin_id,
                    )
                    return res, llm_calls
                else:
                    pending_res = step_explain(
                        user_id=user_id,
                        state=state,
                        triage_decision=triage_decision,
                        get_patient_profile_fn=lambda uid: {"conditions": conditions, "language": language},
                        store=self.mock_store,
                        llm={"groq": fake_groq_chat},
                        checkin_id=checkin_id,
                    )
                    # If eligible, job params are returned -> simulate worker execution via execute_job_synchronous
                    if pending_res.get("status") == "pending" and "_job_params" in pending_res:
                        stored_expl = copy.deepcopy(pending_res)
                        jp = stored_expl.pop("_job_params")
                        # Seed stored row for worker to retrieve (without un-serializable store object)
                        app_store.create_checkin_result(
                            checkin_id=checkin_id,
                            emergency=False,
                            intakes=state.intakes,
                            reconciliation={},
                            verification={},
                            requires_review=False,
                            max_severity="none",
                            review_status="open",
                            triage_level="routine",
                            triage={"level": "routine"},
                            risk=None,
                            explanation=stored_expl,
                        )
                        job = ExplanationJob(
                            checkin_id=checkin_id,
                            user_id=jp["user_id"],
                            condition=jp["condition"],
                            readings=jp["readings"],
                            fallback_template=jp["fallback_template"],
                            language=jp["language"],
                            store=self.mock_store,
                            enqueued_at=time.time(),
                            patient_conditions=jp.get("patient_conditions"),
                        )
                        with patch.dict(os.environ, {"LLM_PROVIDER": "groq"}):
                            final_res = execute_job_synchronous(job)
                        return final_res, llm_calls
                    return pending_res, llm_calls

    def test_t1_english_only_flag_en_calls_llm_urdu_gets_template_inline(self) -> None:
        """T1: EXPLAIN_LLM_LANGUAGES=en in inline mode."""
        env = {"EXPLAIN_LLM_LANGUAGES": "en"}

        # 1. English check-in -> calls LLM, mode llm
        res_en, calls_en = self._drive_checkin(["hypertension"], "en", "inline", env)
        self.assertEqual(res_en["mode"], "llm")
        self.assertEqual(res_en["provider"], "groq")
        self.assertGreater(len(calls_en), 0)

        # 2. Urdu check-in -> 0 LLM calls, template, reason language_template_only
        res_ur, calls_ur = self._drive_checkin(["hypertension"], "ur", "inline", env)
        self.assertEqual(res_ur["mode"], "template")
        self.assertEqual(res_ur["reason"], "language_template_only")
        self.assertEqual(len(calls_ur), 0)
        # Template has Urdu sentences
        self.assertTrue(len(res_ur.get("sentences", [])) > 0)

        # 3. Roman Urdu check-in -> 0 LLM calls, template, reason language_template_only
        res_rur, calls_rur = self._drive_checkin(["hypertension"], "roman_ur", "inline", env)
        self.assertEqual(res_rur["mode"], "template")
        self.assertEqual(res_rur["reason"], "language_template_only")
        self.assertEqual(len(calls_rur), 0)
        self.assertTrue(len(res_rur.get("sentences", [])) > 0)

    def test_t1_english_only_flag_en_calls_llm_urdu_gets_template_background(self) -> None:
        """T1: EXPLAIN_LLM_LANGUAGES=en in background mode (pre-queue eligibility check)."""
        env = {"EXPLAIN_LLM_LANGUAGES": "en"}

        # 1. English check-in -> enqueued and resolved via worker to mode llm
        res_en, calls_en = self._drive_checkin(["hypertension"], "en", "background", env)
        self.assertEqual(res_en["mode"], "llm")
        self.assertEqual(res_en["status"], "ready")
        self.assertGreater(len(calls_en), 0)

        # 2. Urdu check-in -> ineligible pre-queue, status ready, mode template, reason language_template_only, 0 calls
        res_ur, calls_ur = self._drive_checkin(["hypertension"], "ur", "background", env)
        self.assertEqual(res_ur["mode"], "template")
        self.assertEqual(res_ur["reason"], "language_template_only")
        self.assertEqual(res_ur["status"], "ready")
        self.assertEqual(len(calls_ur), 0)

        # 3. Roman Urdu check-in -> ineligible pre-queue, status ready, mode template, reason language_template_only, 0 calls
        res_rur, calls_rur = self._drive_checkin(["hypertension"], "roman_ur", "background", env)
        self.assertEqual(res_rur["mode"], "template")
        self.assertEqual(res_rur["reason"], "language_template_only")
        self.assertEqual(res_rur["status"], "ready")
        self.assertEqual(len(calls_rur), 0)

    def test_t2_default_unset_preserves_today_behavior(self) -> None:
        """T2: Default unset (EXPLAIN_LLM_LANGUAGES not in env): ur check-in calls LLM + translation."""
        with patch.dict(os.environ, {}, clear=False):
            if "EXPLAIN_LLM_LANGUAGES" in os.environ:
                del os.environ["EXPLAIN_LLM_LANGUAGES"]

            self.assertEqual(get_explain_llm_languages(), {"en", "ur", "roman_ur"})
            self.assertTrue(is_language_allowed_for_llm("en"))
            self.assertTrue(is_language_allowed_for_llm("ur"))
            self.assertTrue(is_language_allowed_for_llm("roman_ur"))

            res_ur, calls_ur = self._drive_checkin(["hypertension"], "ur", "inline")
            self.assertEqual(res_ur["mode"], "llm")
            # 2 calls: generation + translation
            self.assertEqual(len(calls_ur), 2)

    def test_t3_empty_or_unknown_fallback_to_en(self) -> None:
        """T3: EXPLAIN_LLM_LANGUAGES='' or 'xx' parses strictly as {'en'}."""
        with patch.dict(os.environ, {"EXPLAIN_LLM_LANGUAGES": ""}):
            self.assertEqual(get_explain_llm_languages(), {"en"})
            self.assertTrue(is_language_allowed_for_llm("en"))
            self.assertFalse(is_language_allowed_for_llm("ur"))

        with patch.dict(os.environ, {"EXPLAIN_LLM_LANGUAGES": "xx"}):
            self.assertEqual(get_explain_llm_languages(), {"en"})
            self.assertTrue(is_language_allowed_for_llm("en"))
            self.assertFalse(is_language_allowed_for_llm("ur"))

        with patch.dict(os.environ, {"EXPLAIN_LLM_LANGUAGES": "ur,invalid"}):
            # Unknown ignored, valid kept
            self.assertEqual(get_explain_llm_languages(), {"ur"})
            self.assertTrue(is_language_allowed_for_llm("ur"))
            self.assertFalse(is_language_allowed_for_llm("en"))

    def test_t4_diabetes_and_hypertension_both_covered(self) -> None:
        """T4: Diabetes and hypertension both covered under EXPLAIN_LLM_LANGUAGES=en."""
        env = {"EXPLAIN_LLM_LANGUAGES": "en"}

        # Diabetes English -> LLM call
        res_dm_en, calls_dm_en = self._drive_checkin(["diabetes"], "en", "inline", env)
        self.assertEqual(res_dm_en["mode"], "llm")
        self.assertGreater(len(calls_dm_en), 0)

        # Diabetes Urdu -> template, 0 LLM calls
        res_dm_ur, calls_dm_ur = self._drive_checkin(["diabetes"], "ur", "inline", env)
        self.assertEqual(res_dm_ur["mode"], "template")
        self.assertEqual(res_dm_ur["reason"], "language_template_only")
        self.assertEqual(len(calls_dm_ur), 0)

        # Both conditions English -> LLM call
        res_both_en, calls_both_en = self._drive_checkin(["hypertension", "diabetes"], "en", "inline", env)
        self.assertEqual(res_both_en["mode"], "llm")
        self.assertGreater(len(calls_both_en), 0)

        # Both conditions Urdu -> template, 0 LLM calls
        res_both_ur, calls_both_ur = self._drive_checkin(["hypertension", "diabetes"], "ur", "inline", env)
        self.assertEqual(res_both_ur["mode"], "template")
        self.assertEqual(res_both_ur["reason"], "language_template_only")
        self.assertEqual(len(calls_both_ur), 0)

    def test_t5_patient_view_never_contains_mode_reason_or_language_template_only(self) -> None:
        """T5: Patient view strictly strips mode, reason, and error codes."""
        internal_expl = {
            "status": "ready",
            "mode": "template",
            "reason": "language_template_only",
            "sentences": [
                {"text": "آپ کا بلڈ پریشر معمول کے مطابق ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]}
            ],
            "sources": [
                {"id": "who_chunk_1", "title": "WHO 2021", "authors": "WHO", "year": "2021", "link": None}
            ],
            "provider": None,
            "providers_tried": [],
            "provider_timings": {},
            "tokens_used": 0,
            "rejected_reasons": ["Guard fallback: language_template_only"],
        }
        patient_view = _build_patient_explain_view(internal_expl)
        self.assertIsNotNone(patient_view)
        self.assertEqual(patient_view.get("status"), "ready")
        self.assertIn("sentences", patient_view)
        self.assertIn("sources", patient_view)

        # Critical: mode and reason MUST NOT be present
        self.assertNotIn("mode", patient_view)
        self.assertNotIn("reason", patient_view)
        self.assertNotIn("rejected_reasons", patient_view)
        self.assertNotIn("language_template_only", json.dumps(patient_view))

    def test_note_1_language_gate_runs_before_cache_and_never_reads_or_writes_cache(self) -> None:
        """
        Note 1: In guarded_explain, the language gate runs BEFORE '# 2. Check Cache with Safety Re-Validation'.
        If EXPLAIN_LLM_LANGUAGES=en, even if a cached ur LLM entry already exists for the same key,
        the ur check-in still gets the template with reason language_template_only,
        and the cache is not read (hit count does not increase) and not written.
        """
        explain_guards.reset_explain_guards()
        cache = explain_guards._GLOBAL_CACHE

        # Seed the cache with a fake Urdu LLM explanation under the exact cache key for routine BP 120/80
        bp_b = explain_guards.get_bp_band(120.0, 80.0)
        c_key = compute_cache_key(
            trigger_category="routine",
            triage_level="routine",
            glucose_band="normal",
            bp_band=bp_b,
            language="ur",
            condition="hypertension",
        )
        fake_cached_llm = {
            "mode": "llm",
            "status": "ready",
            "provider": "groq",
            "sentences": [
                {"text": "آپ کا بلڈ پریشر کیشڈ ایل ایل ایم وضاحت ہے [who_chunk_1]۔", "cites": ["who_chunk_1"]}
            ],
            "sources": [],
            "cites": ["who_chunk_1"],
        }
        cache.put(c_key, fake_cached_llm, ["who_chunk_1"])
        initial_hits = cache.hits
        initial_misses = cache.misses

        # With EXPLAIN_LLM_LANGUAGES=en, invoke guarded_explain for Urdu
        with patch.dict(os.environ, {"EXPLAIN_LLM_LANGUAGES": "en"}):
            res = guarded_explain(
                triage_result={"level": "routine"},
                readings={"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 80.0},
                store=self.mock_store,
                language="ur",
                patient_conditions=["hypertension"],
                mode="inline",
            )

        # Must get template with reason language_template_only (NOT the cached LLM answer!)
        self.assertEqual(res["mode"], "template")
        self.assertEqual(res["reason"], "language_template_only")
        self.assertNotIn("کیشڈ ایل ایل ایم وضاحت", json.dumps(res, ensure_ascii=False))

        # Cache was neither read (hits did not increase) nor written
        self.assertEqual(cache.hits, initial_hits, "Cache hit count must not increase when language is gated before cache")
        self.assertEqual(cache.misses, initial_misses, "Cache miss count must not increase when language is gated before cache")

    def test_c5_validator_and_consistency_ast_hashes_invariant(self) -> None:
        """Verify the 5 validators and is_template_consistent are 100% byte-identical in AST (Python 3.11)."""
        expected_hashes_311 = {
            "validate_sentence_structure": "513d2a7f86f78064325e58477c026cf7ed1c86da6b537b8a25bb6d9e874c8cd8",
            "validate_citations": "6e0eab7f62bbbc4995f95279d83f008f107bdb59ae0b9a2cad67d40097013954",
            "validate_number_grounding": "0b57a80d0790327d2066093eeba765e1c9e27b652bddb303358e70f549ae397a",
            "validate_banned_patterns": "321b9aa8fe5cfe4fdd2ea6cf713ed7b8be39d0f22a753a347a6d7408f68977bf",
            "validate_level_consistency": "c5d798b6172b4e515c921f71a4e02a1725589cacfb504115edb6a1656254b26b",
            "is_template_consistent": "54ca30d6a46081bfe54a18088f5144f9cb7a09cd63c7a9d608527f29c697ca1b",
        }

        for func_name, expected_hash in expected_hashes_311.items():
            fn = getattr(explainer, func_name)
            src = inspect.getsource(fn)
            tree = ast.parse(src)
            dumped = ast.dump(tree)
            actual_hash = hashlib.sha256(dumped.encode("utf-8")).hexdigest()
            self.assertEqual(
                actual_hash,
                expected_hash,
                f"AST Hash mismatch for {func_name}: {actual_hash} != {expected_hash}",
            )


if __name__ == "__main__":
    unittest.main()
