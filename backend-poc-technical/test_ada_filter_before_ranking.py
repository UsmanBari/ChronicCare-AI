"""
Unit and integration tests for excluding diabetes-only guidelines before ranking for non-diabetic patients (Day 6f).

B1: Mixed store where fake ADA, IDF-DAR, and AKU diabetes chunks outrank hypertension chunks for "routine".
    Hypertension-only patient check-in receives only hypertension/general sources (who, ish, pk_htn) in both
    inline and background modes; fake LLM is called and reason != "no_chunks".
B2: Same mixed store with diabetes and dual-condition patients: ADA chunks are retrieved first (ADA-first preserved).
B3: Direct BM25Retriever.retrieve tests: exclude_source_prefixes=() preserves existing ranking;
    non-empty exclude_source_prefixes filters candidates before BM25 ranking (case-insensitive).
B4: Store with only diabetes chunks + hypertension-only patient -> template fallback "no_chunks", zero LLM calls.
B5: Non-Ramadan diabetes check-in never gets idf_dar; Ramadan check-in allows idf_dar.
B6: Byte and AST invariants: 8 protected files and 6 validator AST hashes remain unchanged.
"""

import ast
import hashlib
import inspect
import json
import os
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))

from agents.adaptive_interview_agent import InterviewState
from data_sources import app_store
import llm.gemini_client as gemini_client
import llm.groq_client as groq_client
from orchestrator.steps import step_explain, step_persist_and_respond
from rag import explainer, explain_guards
from rag.explain_guards import (
    DIABETES_ONLY_SOURCE_PREFIXES,
    guarded_explain,
    is_patient_diabetic,
)
from rag.explain_jobs import (
    execute_job_synchronous,
    get_job_queue,
    reset_job_queue,
)
from rag.retriever import BM25Retriever


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


class TestAdaFilterBeforeRanking(unittest.TestCase):
    def setUp(self) -> None:
        explain_guards.reset_explain_guards()
        reset_job_queue()
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(
            prefix="chroniccare_test_b1_", suffix=".db"
        )
        os.close(self.temp_db_fd)
        os.environ["LOCAL_DB_PATH"] = self.temp_db_path
        os.environ["DB_BACKEND"] = "sqlite"
        app_store.migrate(db_path=self.temp_db_path, backend="sqlite")

    def tearDown(self) -> None:
        reset_job_queue()
        explain_guards.reset_explain_guards()
        if hasattr(self, "temp_db_path") and os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def _create_mixed_store(self) -> MockChunkStore:
        """
        Creates a store where diabetes guidelines (ADA, IDF-DAR, AKU) match the routine query
        with higher density and higher priority than the hypertension guidelines.
        Routine query text:
        'lifestyle modification salt sodium reduction physical activity blood pressure glucose targets'
        """
        store = MockChunkStore()

        # 1. Fake ADA chunk (matches all query terms + diabetes terms, priority 10)
        store.add_chunk({
            "chunk_id": "c_ada_sec10_routine",
            "source_id": "ada_2026_sec10",
            "title": "ADA Standards of Care Sec 10",
            "section_path": "Cardiovascular risk lifestyle targets",
            "condition": "both",
            "text": (
                "lifestyle modification salt sodium reduction physical activity blood pressure "
                "glucose targets blood pressure glucose targets"
            ),
            "full_citation": "ADA Standards of Care in Diabetes-2026, Section 10",
            "doi": "10.2337/dc26-S010",
            "priority": 10,
        })

        # 2. Fake IDF-DAR chunk (matches query terms, condition 'both', priority 8)
        store.add_chunk({
            "chunk_id": "c_idf_dar_routine",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR 2021 Guidelines",
            "section_path": "Lifestyle and targets",
            "condition": "both",
            "text": (
                "lifestyle modification salt sodium reduction physical activity blood pressure "
                "glucose targets"
            ),
            "full_citation": "IDF-DAR Practical Guidelines 2021",
            "doi": "10.1016/j.diabres.2021",
            "priority": 8,
        })

        # 3. Fake AKU diabetes chunk (matches query terms, condition 'both', priority 7)
        store.add_chunk({
            "chunk_id": "c_aku_dm_routine",
            "source_id": "aku_diabetes_pk_2023",
            "title": "AKU Pakistan Diabetes Guidelines",
            "section_path": "Lifestyle modification",
            "condition": "both",
            "text": (
                "lifestyle modification salt sodium reduction physical activity blood pressure "
                "glucose targets"
            ),
            "full_citation": "AKU Guidelines for Diabetes Management in Pakistan 2023",
            "doi": "10.1234/aku.dm.2023",
            "priority": 7,
        })

        # 4. WHO Hypertension chunk (matches query, condition 'hypertension', priority 3)
        store.add_chunk({
            "chunk_id": "c_who_htn_routine",
            "source_id": "who_2021_htn",
            "title": "WHO Hypertension Guidelines",
            "section_path": "Lifestyle management",
            "condition": "hypertension",
            "text": "lifestyle modification salt sodium reduction physical activity blood pressure targets",
            "full_citation": "WHO Guideline for the Pharmacological Treatment of Hypertension in Adults 2021",
            "doi": "10.1234/who.htn.2021",
            "priority": 3,
        })

        # 5. ISH 2020 Hypertension chunk (condition 'both', priority 2)
        store.add_chunk({
            "chunk_id": "c_ish_htn_routine",
            "source_id": "ish_2020_htn",
            "title": "ISH Global Hypertension Practice Guidelines",
            "section_path": "Lifestyle lifestyle",
            "condition": "both",
            "text": "lifestyle modification salt sodium reduction physical activity blood pressure targets",
            "full_citation": "ISH 2020 Global Hypertension Guidelines",
            "doi": "10.1097/HJH.0000000000002453",
            "priority": 2,
        })

        # 6. Pakistan Hypertension Women chunk (condition 'hypertension', priority 1)
        store.add_chunk({
            "chunk_id": "c_pk_htn_women",
            "source_id": "pk_htn_women_2023",
            "title": "Pakistan Guidelines for Hypertension in Women",
            "section_path": "Lifestyle recommendations",
            "condition": "hypertension",
            "text": "salt reduction physical activity blood pressure targets lifestyle modification",
            "full_citation": "Pakistan Hypertension Guidelines 2023",
            "doi": "10.1234/pk.htn.2023",
            "priority": 1,
        })

        return store

    def _drive_routine_checkin(
        self,
        conditions_on_file: List[str],
        mode: str,
        store: MockChunkStore,
        trigger_category: str = "routine",
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Drives a routine check-in through step_explain in inline or background mode."""
        explain_guards.reset_explain_guards()
        reset_job_queue()

        prompt_calls: List[str] = []

        def fake_groq_chat(**kwargs):
            messages = kwargs.get("messages", [])
            content = messages[-1]["content"] if messages else ""
            prompt_calls.append(content)
            body = json.dumps({
                "sentences": [
                    {
                        "text": "Your routine check-in shows readings within target range. [S1]",
                        "cites": ["S1"],
                    },
                    {
                        "text": "Maintain your healthy lifestyle habits and scheduled follow-ups. [S1]",
                        "cites": ["S1"],
                    },
                ]
            })
            return body, {"total_tokens": 50, "completion_tokens": 25}

        readings = {"blood_pressure_systolic": 120.0, "blood_pressure_diastolic": 78.0}
        state = InterviewState(
            patient_id=f"pat_{mode}_{'_'.join(conditions_on_file)}",
            conditions_on_file=list(conditions_on_file),
            intakes=[{"readings": readings}],
        )
        triage_decision = {
            "final_triage_level": "routine",
            "final_requires_review": False,
            "final_max_sev": "none",
            "review_status": "open",
            "triage_dict": {"level": "routine"},
        }
        user_id = f"usr_{mode}_{'_'.join(conditions_on_file)}"
        checkin_id = f"chk_{mode}_{int(time.time() * 1000)}"

        class DummyResult:
            def to_dict(self):
                return {}

        with patch.dict(
            os.environ,
            {
                "EXPLAIN_ENABLED": "true",
                "EXPLAIN_MODE": mode,
                "EXPLAIN_LLM_CONDITIONS": "hypertension,diabetes",
                "LLM_PROVIDER": "groq",
            },
        ), patch.object(
            groq_client, "is_configured", return_value=True, spec=lambda: True
        ), patch.object(
            gemini_client, "is_configured", return_value=False, spec=lambda: False
        ), patch.object(
            groq_client, "chat_with_detailed_usage", side_effect=fake_groq_chat, spec=fake_groq_chat
        ), patch.object(
            groq_client, "chat_with_usage", side_effect=lambda **kw: (fake_groq_chat(**kw)[0], 50), spec=lambda **kw: ("", 0)
        ), patch.object(
            get_job_queue(), "start_worker_if_needed", lambda: None
        ):
            if mode == "inline":
                res = step_explain(
                    user_id=user_id,
                    state=state,
                    triage_decision=triage_decision,
                    get_patient_profile_fn=lambda uid: {"conditions": conditions_on_file, "language": "en"},
                    store=store,
                    checkin_id=checkin_id,
                )
                return res, prompt_calls
            else:
                pending_res = step_explain(
                    user_id=user_id,
                    state=state,
                    triage_decision=triage_decision,
                    get_patient_profile_fn=lambda uid: {"conditions": conditions_on_file, "language": "en"},
                    store=store,
                    checkin_id=checkin_id,
                )
                self.assertIsNotNone(pending_res)
                self.assertEqual(pending_res.get("status"), "pending")

                step_persist_and_respond(
                    checkin_id=checkin_id,
                    state=state,
                    recon_result=DummyResult(),
                    verif_result=DummyResult(),
                    triage_decision=triage_decision,
                    med_state=None,
                    protocol_state=None,
                    record_label="test",
                    explanation=pending_res,
                )

                q = get_job_queue()._get_queue()
                self.assertFalse(q.empty(), "Job should be enqueued")
                job = q.get_nowait()
                final_res = execute_job_synchronous(job)
                return final_res, prompt_calls

    # -------------------------------------------------------------------------
    # B1: Hypertension-only patient routine check-in gets only HTN/general sources
    # -------------------------------------------------------------------------
    def test_b1_hypertension_only_routine_checkin_gets_only_htn_sources(self) -> None:
        """
        For a hypertension-only patient, routine check-in excludes all diabetes-only guidelines
        (ADA, IDF-DAR, AKU) before ranking. Only hypertension/general sources (who, ish, pk_htn)
        are retrieved and sent to the LLM in both inline and background modes.
        """
        store = self._create_mixed_store()

        for mode in ("inline", "background"):
            with self.subTest(mode=mode):
                res, prompts = self._drive_routine_checkin(
                    conditions_on_file=["hypertension"],
                    mode=mode,
                    store=store,
                )
                self.assertEqual(res.get("mode"), "llm")
                self.assertEqual(res.get("status"), "ready")
                self.assertNotEqual(res.get("reason"), "no_chunks")

                # Verify LLM was called
                self.assertTrue(len(prompts) > 0, f"Expected LLM calls for mode {mode}")
                for p in prompts:
                    for prefix in DIABETES_ONLY_SOURCE_PREFIXES:
                        self.assertNotIn(prefix, p, f"Found {prefix} in LLM prompt for mode {mode}")

                # Verify sources returned in response contain only hypertension/general sources
                sources = res.get("sources", [])
                self.assertTrue(len(sources) > 0, f"Expected non-empty sources for mode {mode}")
                allowed_prefixes = ("who_2021_htn", "ish_2020_htn", "pk_htn_women_2023")
                for s in sources:
                    sid = str(s.get("source_id", "") or s.get("chunk_id", ""))
                    self.assertTrue(
                        any(sid.startswith(p) for p in allowed_prefixes),
                        f"Unexpected source {sid} for hypertension-only patient in mode {mode}",
                    )
                    for excluded in DIABETES_ONLY_SOURCE_PREFIXES:
                        self.assertFalse(
                            sid.startswith(excluded),
                            f"Excluded diabetes source {sid} found in mode {mode}",
                        )

    # -------------------------------------------------------------------------
    # B2: Diabetes and dual-condition patients retain ADA-first ranking
    # -------------------------------------------------------------------------
    def test_b2_diabetes_and_both_condition_patients_retain_ada_ranking(self) -> None:
        """
        Diabetic and dual-condition patients retain diabetes guideline access.
        ADA chunks are ranked first.
        """
        store = self._create_mixed_store()

        # 1. Diabetes-only patient
        res_dm, prompts_dm = self._drive_routine_checkin(
            conditions_on_file=["diabetes"],
            mode="inline",
            store=store,
        )
        self.assertEqual(res_dm.get("mode"), "llm")
        self.assertEqual(res_dm.get("status"), "ready")
        sources_dm = res_dm.get("sources", [])
        self.assertTrue(len(sources_dm) > 0)
        self.assertTrue(
            str(sources_dm[0].get("source_id", "")).startswith("ada_2026"),
            f"Expected ADA as top source for diabetes patient, got: {sources_dm[0]}",
        )

        # 2. Both-condition patient
        res_both, prompts_both = self._drive_routine_checkin(
            conditions_on_file=["hypertension", "diabetes"],
            mode="inline",
            store=store,
        )
        self.assertEqual(res_both.get("mode"), "llm")
        self.assertEqual(res_both.get("status"), "ready")
        sources_both = res_both.get("sources", [])
        self.assertTrue(len(sources_both) > 0)
        self.assertTrue(
            str(sources_both[0].get("source_id", "")).startswith("ada_2026"),
            f"Expected ADA as top source for both-condition patient, got: {sources_both[0]}",
        )

    # -------------------------------------------------------------------------
    # B3: BM25Retriever.retrieve exclude_source_prefixes behavior
    # -------------------------------------------------------------------------
    def test_b3_retriever_exclude_source_prefixes_filtering(self) -> None:
        """BM25Retriever.retrieve excludes specified prefixes before scoring and ranking."""
        store = self._create_mixed_store()
        retriever = BM25Retriever(store)
        query = "lifestyle modification salt sodium reduction physical activity blood pressure glucose targets"

        # Without exclusions: ADA chunk ranks first
        all_results = retriever.retrieve(query=query, top_k=3, condition="both")
        self.assertTrue(len(all_results) > 0)
        self.assertTrue(all_results[0]["source_id"].startswith("ada_2026"))

        # With DIABETES_ONLY_SOURCE_PREFIXES: only hypertension sources returned
        filtered_results = retriever.retrieve(
            query=query,
            top_k=3,
            condition="both",
            exclude_source_prefixes=DIABETES_ONLY_SOURCE_PREFIXES,
        )
        self.assertTrue(len(filtered_results) > 0)
        for r in filtered_results:
            sid = r["source_id"]
            for p in DIABETES_ONLY_SOURCE_PREFIXES:
                self.assertFalse(sid.startswith(p), f"Source {sid} matches excluded prefix {p}")

        # Case-insensitivity check
        case_results = retriever.retrieve(
            query=query,
            top_k=3,
            condition="both",
            exclude_source_prefixes=("ADA_2026", "Idf_Dar", "AKU_DIABETES"),
        )
        self.assertEqual(len(filtered_results), len(case_results))
        for r1, r2 in zip(filtered_results, case_results):
            self.assertEqual(r1["chunk_id"], r2["chunk_id"])

    # -------------------------------------------------------------------------
    # B4: Store with only diabetes chunks + HTN-only patient -> no_chunks template
    # -------------------------------------------------------------------------
    def test_b4_store_with_only_diabetes_chunks_falls_back_to_no_chunks(self) -> None:
        """If store contains only diabetes chunks, hypertension-only patient gets no_chunks template."""
        store = MockChunkStore()
        store.add_chunk({
            "chunk_id": "c_ada_1",
            "source_id": "ada_2026_sec05",
            "title": "ADA Lifestyle",
            "condition": "both",
            "text": "lifestyle modification salt reduction blood pressure targets",
            "full_citation": "ADA 2026",
            "priority": 5,
        })
        store.add_chunk({
            "chunk_id": "c_idf_1",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Lifestyle",
            "condition": "both",
            "text": "lifestyle modification salt reduction blood pressure targets",
            "full_citation": "IDF-DAR 2021",
            "priority": 5,
        })

        res, prompts = self._drive_routine_checkin(
            conditions_on_file=["hypertension"],
            mode="inline",
            store=store,
        )
        self.assertEqual(res.get("mode"), "template")
        self.assertEqual(res.get("status"), "ready")
        self.assertEqual(res.get("reason"), "no_chunks")
        self.assertEqual(len(prompts), 0, "Zero LLM calls should be made when no valid chunks exist")

    # -------------------------------------------------------------------------
    # B5: Non-Ramadan diabetes check-in never gets idf_dar
    # -------------------------------------------------------------------------
    def test_b5_non_ramadan_diabetes_checkin_never_gets_idf_dar(self) -> None:
        """Non-Ramadan diabetes check-in never retrieves or uses idf_dar chunks."""
        store = MockChunkStore()
        store.add_chunk({
            "chunk_id": "c_idf_dm",
            "source_id": "idf_dar_2021",
            "title": "IDF-DAR Fasting Management",
            "condition": "diabetes",
            "text": "blood glucose monitoring hydration during Ramadan roza iftar sehri",
            "full_citation": "IDF-DAR 2021",
            "priority": 10,
        })
        store.add_chunk({
            "chunk_id": "c_ada_dm",
            "source_id": "ada_2026_sec06",
            "title": "ADA Glycemic Targets",
            "condition": "diabetes",
            "text": "blood glucose monitoring hydration glycemic targets in type 2 diabetes",
            "full_citation": "ADA Standards of Care 2026",
            "priority": 5,
        })

        retriever = BM25Retriever(store)

        # 1. Non-Ramadan diabetes query -> IDF-DAR chunk is excluded
        res_non_ramadan = retriever.retrieve(
            query="blood glucose monitoring hydration glycemic targets",
            condition="diabetes",
            top_k=2,
        )
        self.assertTrue(len(res_non_ramadan) > 0)
        for c in res_non_ramadan:
            self.assertFalse(c["source_id"].startswith("idf_dar"))
        self.assertTrue(res_non_ramadan[0]["source_id"].startswith("ada_2026"))

        # 2. Ramadan diabetes query -> IDF-DAR chunk is included and prioritized
        res_ramadan = retriever.retrieve(
            query="roza mein blood glucose monitoring hydration iftar",
            condition="diabetes",
            top_k=2,
        )
        self.assertTrue(len(res_ramadan) > 0)
        self.assertTrue(res_ramadan[0]["source_id"].startswith("idf_dar"))

    # -------------------------------------------------------------------------
    # B6: Invariance Verification (AST Hashes & Protected Files)
    # -------------------------------------------------------------------------
    def test_b6_validator_ast_hashes_invariant(self) -> None:
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

    def test_b6_protected_files_sha256_invariant(self) -> None:
        """Verify all 8 clinical protected files remain strictly untouched."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        expected_shas = {
            os.path.join(repo_root, "backend-poc-technical", "agents", "triage_protocol.py"): (
                "5638237470fe8743743cb1574c13863bab35ffae63dfe9ab57dc99d839d3a72a"
            ),
            os.path.join(repo_root, "backend-poc-technical", "agents", "input_triage.py"): (
                "2cbcf35eea971744d9c0e5fa8ad95e9987cc8874ea0d623920e6df4eb55f87e8"
            ),
            os.path.join(repo_root, "backend-poc-technical", "agents", "answer_validation.py"): (
                "72d6fb94adab0ef5f21159265f291d8c307d10769715462e240272785a1e2e1f"
            ),
            os.path.join(repo_root, "backend-poc-technical", "agents", "verification_agent.py"): (
                "72e44368d011a79164774b61abd20717e287da94f310d691fab6fce86dcb7ada"
            ),
            os.path.join(repo_root, "backend-poc-technical", "agents", "reconciliation_agent.py"): (
                "17df17416451690cf921285bf40804b6bc6aee7c17abbdafa6189f316fbc61a1"
            ),
            os.path.join(repo_root, "backend-poc-technical", "agents", "adaptive_interview_agent.py"): (
                "9c05514a9699f07caab7d4d00ea1c7f269418ebeb9a7d734fe779f5e58c389d8"
            ),
            os.path.join(repo_root, "backend-poc-technical", "agents", "medication_confirmation.py"): (
                "31e261aebfd61dee1e56f674a7f859653c9e3596a083f7f01cb556538401c5b0"
            ),
            os.path.join(repo_root, "docs", "CLINICAL_RULES.md"): (
                "968239436f1ea286ac3a5984087bcde7e179183dd41cb6b20490171977fad7d6"
            ),
        }

        for path, exp_sha in expected_shas.items():
            self.assertTrue(os.path.exists(path), f"File missing: {path}")
            with open(path, "rb") as f:
                actual_sha = hashlib.sha256(f.read()).hexdigest().lower()
            self.assertEqual(
                actual_sha,
                exp_sha.lower(),
                f"Protected file modified: {path} ({actual_sha} != {exp_sha})",
            )


if __name__ == "__main__":
    unittest.main()
