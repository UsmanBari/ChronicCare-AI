"""
Unit and integration tests for explainer fixes from the real-corpus smoke (Day 6e):
F1-F3: Translation output max_tokens (EXPLAIN_TRANSLATION_MAX_TOKENS = 700 vs English 250), pacer reservation.
F4-F5: Malformed JSON answers classified as validation_failed, do not trip circuit breaker.
F6-F7: ADA Standards of Care only for patients whose conditions include diabetes; both-condition patients retain ADA access on BP triggers.
"""

import ast
import hashlib
import inspect
import json
import os
import sys
from typing import Any, Dict, List
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))

from rag import explainer, explain_guards
from rag.explain_guards import (
    CircuitBreaker,
    TokenCapGuard,
    ExplainCache,
    TokenPacer,
    guarded_explain,
)
from rag.explainer import (
    get_explain_max_tokens,
    get_explain_translation_max_tokens,
    explain,
    get_template_explanation,
)


class MockChunkStore:
    def __init__(self, chunks: List[Dict[str, Any]] = None):
        self._chunks = list(chunks or [])
        self._by_id = {c["chunk_id"]: c for c in self._chunks}

    def add_chunk(self, chunk: Dict[str, Any]):
        self._chunks.append(chunk)
        self._by_id[chunk["chunk_id"]] = chunk

    def get_chunk(self, chunk_id: str):
        return self._by_id.get(chunk_id)

    def list_chunks(
        self,
        condition=None,
        topic=None,
        min_priority=None,
    ):
        return list(self._chunks)

    def total_chunks(self) -> int:
        return len(self._chunks)


class TestRealCorpusExplainerFixes(unittest.TestCase):
    def setUp(self):
        # Ensure fresh state for tests
        explain_guards.reset_explain_guards()

    # -------------------------------------------------------------------------
    # F1 / F3: Token Limits and Translation Call
    # -------------------------------------------------------------------------
    def test_f1_token_limits_env_and_defaults(self):
        """EXPLAIN_MAX_TOKENS defaults to 250; EXPLAIN_TRANSLATION_MAX_TOKENS defaults to 700."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_explain_max_tokens(), 250)
            self.assertEqual(get_explain_translation_max_tokens(), 700)

        with patch.dict(os.environ, {"EXPLAIN_MAX_TOKENS": "300", "EXPLAIN_TRANSLATION_MAX_TOKENS": "850"}):
            self.assertEqual(get_explain_max_tokens(), 300)
            self.assertEqual(get_explain_translation_max_tokens(), 850)

    def test_f1_f3_translation_call_receives_700_tokens_and_long_urdu_succeeds(self):
        """Translation call uses max_tokens 700 and preserves longer Urdu responses (~600 tokens)."""
        calls = []

        def mock_llm(**kwargs):
            calls.append(kwargs)
            messages = kwargs.get("messages", [])
            user_msg = messages[-1]["content"] if messages else ""
            if "Translate the following" in user_msg:
                # Mock a lengthy Urdu translation with 2 sentences
                s1 = (
                    "آپ کا بلڈ پریشر 150/95 ہے جو کہ معمول کے ہدف سے زیادہ ہے۔ "
                    "طرز زندگی میں ضروری تبدیلی اور باقاعدگی سے نگرانی تجویز کی جاتی ہے۔ [S1]"
                )
                s2 = "رہنما اصولوں کے مطابق نمک کم رکھیں اور اپنے ڈاکٹر سے جلد مشورہ کریں۔ [S1]"
                return json.dumps({
                    "sentences": [
                        {"text": s1, "cites": ["S1"]},
                        {"text": s2, "cites": ["S1"]},
                    ]
                }, ensure_ascii=False)
            else:
                # English generation (2 sentences)
                return json.dumps({
                    "sentences": [
                        {
                            "text": "Your blood pressure is 150/95 mmHg, which is above the target range. [S1]",
                            "cites": ["S1"],
                        },
                        {
                            "text": "Guideline recommendations advise monitoring and consulting your healthcare team. [S1]",
                            "cites": ["S1"],
                        },
                    ]
                })

        candidate = [{
            "chunk_id": "c1",
            "source_id": "who_ish_2020",
            "title": "WHO HTN",
            "text": "Target BP is below 140/90.",
            "full_citation": "WHO Guidelines",
            "doi": "10.1234/who",
        }]

        res = explain(
            triage_result={"level": "review", "trigger": "bp_high"},
            readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 95},
            language="ur",
            candidate_chunks=candidate,
            llm=mock_llm,
        )

        self.assertEqual(res.get("mode"), "llm")
        self.assertEqual(res.get("language"), "ur")
        self.assertEqual(len(calls), 2)
        # Call 1 (English) max_tokens: 250
        self.assertEqual(calls[0].get("max_tokens"), 250)
        # Call 2 (Translation) max_tokens: 700
        self.assertEqual(calls[1].get("max_tokens"), 700)

    # -------------------------------------------------------------------------
    # F2: Pacer Token Reservation
    # -------------------------------------------------------------------------
    def test_f2_pacer_receives_actual_max_tokens_for_each_call(self):
        """Pacer checks reserve 250 for English and 700 for translation call."""
        pacer_requests = []
        real_pacer = explain_guards._GLOBAL_GROQ_PACER

        original_get_wait = real_pacer.get_wait_seconds

        def tracking_get_wait(tokens_needed: int, otpm_limit: int, clock_fn=None):
            pacer_requests.append(tokens_needed)
            return original_get_wait(tokens_needed=tokens_needed, otpm_limit=otpm_limit, clock_fn=clock_fn)

        real_pacer.get_wait_seconds = tracking_get_wait

        try:
            def mock_llm(**kwargs):
                user_msg = kwargs.get("messages", [])[-1]["content"]
                if "Translate the following" in user_msg:
                    return json.dumps({
                        "sentences": [
                            {"text": "بلڈ پریشر 150 ہے [S1]", "cites": ["S1"]},
                            {"text": "ڈاکٹر سے رابطہ کریں [S1]", "cites": ["S1"]},
                        ]
                    })
                return json.dumps({
                    "sentences": [
                        {"text": "Your blood pressure is 150. [S1]", "cites": ["S1"]},
                        {"text": "Please follow up with your doctor. [S1]", "cites": ["S1"]},
                    ]
                })

            store = MockChunkStore()
            store.add_chunk({
                "chunk_id": "c1",
                "source_id": "who_ish_2020",
                "title": "WHO",
                "condition": "hypertension",
                "text": "Target BP",
                "full_citation": "WHO 2020",
                "doi": "10.1234/who",
                "priority": 1,
            })

            with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension"}):
                res = guarded_explain(
                    triage_result={"level": "review"},
                    readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 90},
                    language="ur",
                    store=store,
                    llm=mock_llm,
                    condition="hypertension",
                    provider="groq",
                    mode="background",
                )

            self.assertEqual(res.get("mode"), "llm")
            # Verify pacer inspected tokens_needed for both calls (250 for English, 700 for translation)
            self.assertIn(250, pacer_requests)
            self.assertIn(700, pacer_requests)
        finally:
            real_pacer.get_wait_seconds = original_get_wait

    # -------------------------------------------------------------------------
    # F4 / F5: Malformed JSON vs Circuit Breaker
    # -------------------------------------------------------------------------
    def test_f4_malformed_json_returns_validation_failed_without_tripping_breaker(self):
        """Malformed JSON answer triggers validation_failed and does NOT count as circuit breaker failure."""
        breaker = CircuitBreaker(failures_threshold=3, cooldown_seconds=60.0)

        def bad_json_llm(**kwargs):
            return "```json\n{\"sentences\": [{\"text\": \"Incomplete json string"

        store = MockChunkStore()
        store.add_chunk({
            "chunk_id": "c1",
            "source_id": "who_ish_2020",
            "title": "WHO",
            "condition": "hypertension",
            "text": "Target BP",
            "full_citation": "WHO 2020",
            "doi": "10.1234/who",
            "priority": 1,
        })

        with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension"}):
            res = guarded_explain(
                triage_result={"level": "review"},
                readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 90},
                language="en",
                store=store,
                llm=bad_json_llm,
                condition="hypertension",
                breaker=breaker,
                provider="groq",
            )

        self.assertEqual(res.get("mode"), "template")
        self.assertEqual(res.get("reason"), "validation_failed")
        # Ensure rejected_reasons contains parse_error without leaking answer text
        rej = res.get("rejected_reasons", [])
        self.assertTrue(any("parse_error" in r for r in rej), f"Expected parse_error in {rej}")
        self.assertFalse(any("Incomplete json string" in r for r in rej), "Leaked raw model answer in rejected_reasons")
        # Breaker failure count must NOT increment
        self.assertEqual(breaker._consecutive_failures, 0)
        self.assertEqual(breaker.state(), "closed")

    def test_f5_three_malformed_answers_keep_breaker_closed_fourth_still_calls_llm(self):
        """3 consecutive malformed answers keep breaker closed; 4th call still executes LLM."""
        breaker = CircuitBreaker(failures_threshold=3, cooldown_seconds=60.0)
        call_count = [0]

        def test_llm(**kwargs):
            call_count[0] += 1
            if call_count[0] <= 3:
                return "{not valid json at all"
            return json.dumps({
                "sentences": [
                    {"text": "Your blood pressure is 150. [S1]", "cites": ["S1"]},
                    {"text": "Please check with your provider. [S1]", "cites": ["S1"]},
                ]
            })

        store = MockChunkStore()
        store.add_chunk({
            "chunk_id": "c1",
            "source_id": "who_ish_2020",
            "title": "WHO",
            "condition": "hypertension",
            "text": "Target BP",
            "full_citation": "WHO 2020",
            "doi": "10.1234/who",
            "priority": 1,
        })

        with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension"}):
            # 3 malformed calls
            for _ in range(3):
                r = guarded_explain(
                    triage_result={"level": "review"},
                    readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 90},
                    language="en",
                    store=store,
                    llm=test_llm,
                    condition="hypertension",
                    breaker=breaker,
                    provider="groq",
                )
                self.assertEqual(r.get("reason"), "validation_failed")
                self.assertEqual(breaker.state(), "closed")

            # 4th call succeeds with LLM
            r4 = guarded_explain(
                triage_result={"level": "review"},
                readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 90},
                language="en",
                store=store,
                llm=test_llm,
                condition="hypertension",
                breaker=breaker,
                provider="groq",
            )
            self.assertEqual(r4.get("mode"), "llm")
            self.assertEqual(call_count[0], 4)
            self.assertEqual(breaker.state(), "closed")

    def test_f5_three_timeouts_still_open_circuit_breaker(self):
        """True outages (3 consecutive timeouts) still trip breaker to open."""
        breaker = CircuitBreaker(failures_threshold=3, cooldown_seconds=60.0)

        def timeout_llm(**kwargs):
            raise TimeoutError("Request timed out upstream")

        store = MockChunkStore()
        store.add_chunk({
            "chunk_id": "c1",
            "source_id": "who_ish_2020",
            "title": "WHO",
            "condition": "hypertension",
            "text": "Target BP",
            "full_citation": "WHO 2020",
            "doi": "10.1234/who",
            "priority": 1,
        })

        with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension"}):
            for _ in range(3):
                guarded_explain(
                    triage_result={"level": "review"},
                    readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 90},
                    language="en",
                    store=store,
                    llm=timeout_llm,
                    condition="hypertension",
                    breaker=breaker,
                    provider="groq",
                )

        self.assertEqual(breaker.state(), "open")
        self.assertEqual(breaker._consecutive_failures, 3)

    # -------------------------------------------------------------------------
    # F6 / F7: ADA Chunks Filtering by Patient Condition
    # -------------------------------------------------------------------------
    def _create_mixed_store(self) -> MockChunkStore:
        store = MockChunkStore()
        store.add_chunk({
            "chunk_id": "c_htn_who",
            "source_id": "who_ish_2020",
            "title": "WHO Hypertension",
            "condition": "hypertension",
            "text": "Hypertension management guideline for adults.",
            "full_citation": "WHO 2020",
            "doi": "10.1234/who",
            "priority": 1,
        })
        store.add_chunk({
            "chunk_id": "c_ada_sec10",
            "source_id": "ada_2026_sec10",
            "title": "ADA Standards of Care Sec 10 - Cardiovascular Disease",
            "condition": "both",
            "text": "Cardiovascular risk reduction and blood pressure targets for people with diabetes.",
            "full_citation": "ADA 2026 Sec 10",
            "doi": "10.2337/ada10",
            "priority": 1,
        })
        store.add_chunk({
            "chunk_id": "c_ada_sec05",
            "source_id": "ada_2026_sec05",
            "title": "ADA Standards of Care Sec 05 - Facilitating Positive Health Behaviors",
            "condition": "diabetes",
            "text": "Lifestyle management and nutrition in type 2 diabetes.",
            "full_citation": "ADA 2026 Sec 05",
            "doi": "10.2337/ada05",
            "priority": 1,
        })
        return store

    def test_f6_hypertension_only_patient_drops_all_ada_chunks(self):
        """Hypertension-only patient never receives, cites, or exposes ADA chunks."""
        store = self._create_mixed_store()

        def mock_llm(**kwargs):
            # Check prompt text: must NOT contain ADA text
            prompt = kwargs.get("messages", [])[-1]["content"]
            self.assertNotIn("ADA Standards of Care", prompt)
            self.assertNotIn("ada_2026", prompt)
            return json.dumps({
                "sentences": [
                    {"text": "Your blood pressure is 150 mmHg. [S1]", "cites": ["S1"]},
                    {"text": "Follow lifestyle modifications. [S1]", "cites": ["S1"]},
                ]
            })

        with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension,diabetes"}):
            res = guarded_explain(
                triage_result={"level": "review"},
                readings={"blood_pressure_systolic": 150, "blood_pressure_diastolic": 90},
                language="en",
                store=store,
                llm=mock_llm,
                condition="hypertension",
                patient_conditions=["hypertension"],
                provider="groq",
            )

        self.assertEqual(res.get("mode"), "llm")
        # Verify sources list contains NO ada_2026 chunks
        for src in res.get("sources", []):
            self.assertFalse(str(src.get("source_id", "")).startswith("ada_2026"))
            self.assertFalse(str(src.get("chunk_id", "")).startswith("ada_2026"))

    def test_f7_diabetes_patient_allows_ada_chunks(self):
        """Diabetes patient retains access to ADA chunks."""
        store = self._create_mixed_store()

        def mock_llm(**kwargs):
            return json.dumps({
                "sentences": [
                    {"text": "Your glucose reading is 210 mg/dL. [S1]", "cites": ["S1"]},
                    {"text": "Follow your dietary plan and check your levels regularly. [S1]", "cites": ["S1"]},
                ]
            })

        with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension,diabetes"}):
            res = guarded_explain(
                triage_result={"level": "review"},
                readings={"glucose": 210},
                language="en",
                store=store,
                llm=mock_llm,
                condition="diabetes",
                patient_conditions=["diabetes"],
                provider="groq",
            )

        self.assertEqual(res.get("mode"), "llm")
        source_ids = [s.get("source_id", "") for s in res.get("sources", [])]
        self.assertTrue(any(s.startswith("ada_2026") for s in source_ids), f"Expected ADA sources in {source_ids}")

    def test_f7_both_condition_patient_with_bp_trigger_allows_ada_chunks(self):
        """Both-condition patient with BP trigger still retains ADA access."""
        store = self._create_mixed_store()

        def mock_llm(**kwargs):
            return json.dumps({
                "sentences": [
                    {"text": "Your blood pressure is 165/95 mmHg. [S1]", "cites": ["S1"]},
                    {"text": "Follow up with your clinician for guidance. [S1]", "cites": ["S1"]},
                ]
            })

        with patch.dict(os.environ, {"EXPLAIN_LLM_CONDITIONS": "hypertension,diabetes"}):
            res = guarded_explain(
                triage_result={"level": "urgent"},
                readings={"blood_pressure_systolic": 165, "blood_pressure_diastolic": 95},
                language="en",
                store=store,
                llm=mock_llm,
                condition="both",
                patient_conditions=["hypertension", "diabetes"],
                provider="groq",
            )

        self.assertEqual(res.get("mode"), "llm")
        source_ids = [s.get("source_id", "") for s in res.get("sources", [])]
        self.assertTrue(any(s.startswith("ada_2026") for s in source_ids), f"Expected ADA chunks for dual condition patient: {source_ids}")

    # -------------------------------------------------------------------------
    # Doc-vs-Code Parity & Validator AST Invariance
    # -------------------------------------------------------------------------
    def test_doc_vs_code_parity_explain_guards_doc(self):
        """EXPLAIN_TRANSLATION_MAX_TOKENS and EXPLAIN_MAX_TOKENS are documented in docs/EXPLAIN_GUARDS.md."""
        doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "EXPLAIN_GUARDS.md")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("EXPLAIN_MAX_TOKENS", content)
        self.assertIn("EXPLAIN_TRANSLATION_MAX_TOKENS", content)
        self.assertIn("700", content)
        self.assertIn("250", content)

    def test_validator_and_consistency_ast_hashes_invariant(self):
        """Verify the 5 validators and is_template_consistent are 100% byte-identical in AST."""
        expected_hashes = {
            "validate_sentence_structure": "513d2a7f86f78064325e58477c026cf7ed1c86da6b537b8a25bb6d9e874c8cd8",
            "validate_citations": "6e0eab7f62bbbc4995f95279d83f008f107bdb59ae0b9a2cad67d40097013954",
            "validate_number_grounding": "0b57a80d0790327d2066093eeba765e1c9e27b652bddb303358e70f549ae397a",
            "validate_banned_patterns": "321b9aa8fe5cfe4fdd2ea6cf713ed7b8be39d0f22a753a347a6d7408f68977bf",
            "validate_level_consistency": "c5d798b6172b4e515c921f71a4e02a1725589cacfb504115edb6a1656254b26b",
            "is_template_consistent": "54ca30d6a46081bfe54a18088f5144f9cb7a09cd63c7a9d608527f29c697ca1b",
        }

        for func_name, expected_hash in expected_hashes.items():
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

        for func_name, expected_hash in expected_hashes.items():
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
