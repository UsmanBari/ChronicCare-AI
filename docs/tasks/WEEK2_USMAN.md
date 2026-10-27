# ChronicCare AI — Week 2 (26 Oct – 1 Nov 2026) — Usman

> **Your file for the week:** your setup, your daily rhythm as lead and reviewer, who reviews your work, your 7 Antigravity prompts, who does what, and the full handbook (Appendix A).
> Give the whole file to your AI first, then paste one day's prompt at a time. Save it as `docs/tasks/WEEK2_USMAN.md`.

**Your focus this week:** you own the ML (`ML_PLAN.md`, the harness, the models, the risk agent), the guideline RAG and explanations, the LangGraph orchestrator and the EHR test patients, and you review every PR from Saad and Hassaan.

**The goal:** the FYP-1 final evaluation is on **Tue 17 Nov**, and by then the project should be about 65–70% of the full FYP. Nothing has been cut for the earlier date: features are done by **8 Nov** and the code freeze is **10 Nov**. This week you build the engine of every Iteration 2 feature. Week 3 is risk/explanation screens (Hassaan), the RAG retrieval half (Saad), evaluation on Saad's test set, and doctor sign-off.

**The rules that matter most** (the full list is in Appendix A, Part 0):
1. "The model proposes, the rules decide." The risk agent and the explainer never change a triage level, except the one doctor-approved rule behind `RISK_CAN_RAISE`, and even that only raises.
2. Every new feature ships behind a flag that's off on Render until the doctors sign off.
3. No guideline text, data or secrets in Git. No MIMIC anywhere near an AI tool.
4. Your PRs pass the same gates and reviews as everyone else's.
5. "NOT DONE" and "NOT RUN" are fine answers. A false "done" is not.

**Contents**
- Part 1: Your setup
- Part 2: Your day (lead + builder)
- Part 3: Who reviews your PRs
- Part 4: The 7 daily prompts
- Part 5: Added for Week 3: the Jev answer-understanding test
- Appendix B: Who does what this week
- Appendix A: The full project handbook

---

## Part 1 — Your setup (once, before Monday)

1. **Repo:** `git switch dev; git pull`. Your clone is the reference: run the full gates once and note the counts (about 744 backend tests passing). Every PR is compared against them.
2. **Branch protection:** check `dev` needs a PR + 1 approval + green CI, and nobody can push straight to `dev` or `main`, you included.
3. **Data folder:** the same `Chronicare-data\` layout you sent Saad, plus three new folders:
   - `guidelines\` for the PDFs (Day 2)
   - `rag\` for chunks and the smoke questions (Days 2–3)
   - `synthea\` for the generated patients (Day 1)
   
   Set `$env:CHRONICCARE_DATA_DIR` in every terminal.
4. **Java 17+** for Synthea (`java -version`).
5. **Groq key:** rotate it (the old one was exposed). The new key goes only in `backend-poc-technical\.env` and in Render's environment, never in a chat or a screenshot.
6. **Flags you add this week** (all default `false` / `direct`, in `.env.example` and on Render): `RISK_ENABLED`, `RISK_CAN_RAISE`, `EXPLAIN_ENABLED`, `ORCHESTRATOR`. They stay off on Render until the doctors sign off.
7. Save this file as `docs/tasks/WEEK2_USMAN.md` and commit it in your Day 1 PR.

---

## Part 2 — Your day (lead + builder)

```
08:00–09:00  Review (every day, before your own prompt)
             - open each new PR from Saad and Hassaan
             - give Claude the PR link + "review against Day N of WEEK2_<NAME>.md": it checks out the branch,
               re-runs the gates, checks the diff against FILES ALLOWED and the acceptance IDs, and writes the
               correction prompt
             - send the correction prompt to them; merge what's green and correct
09:00–20:00  Your own day: paste today's prompt into a new Antigravity chat → plan → "go" → watch it
20:00–21:00  Read the 4-line messages from Saad and Hassaan; push your PR; send yours for review
```

**Merge order matters this week:**
| Day | Merge first thing | Because |
|---|---|---|
| Wed | Saad Day 2 | Your `ML_PLAN.md` is built from it |
| Thu | Saad Day 3 + approve `ML_INTERFACES.md` | Your harness calls his toolkit |
| Sun | Hassaan Day 6 (schema v13) | Your Day 7 adds v14 on top |

**Your review checklist for every PR** (the same one in their files, Part 3):
- only allowed files changed
- protected-file hashes unchanged (unless allowed)
- no data or secrets
- new tests are in the CI list
- every number in the PR reproduces
- Urdu present for every new string
- commits under their own name
- they can explain the change. Ask them one question about it on WhatsApp.

---

## Part 3 — Who reviews your PRs

Your work goes through the same gates and the same review, so nobody can say the lead's code skipped checks.

| Your PR | Reviewer | What they check |
|---|---|---|
| Day 1 EHR patients | Hassaan + Saad | Each connects to 4 of the patients and confirms the record |
| Days 3–5 ML | Saad | `ML_PLAN.md`, the harness vs his toolkit, the model cards vs the reports |
| Day 6 LangGraph | Hassaan | Runs the equivalence script himself |
| Every PR | Claude | Same review as theirs: the gates, the diff vs FILES ALLOWED, acceptance IDs |

Self-merging is allowed only after one teammate approves and CI is green.

---

## Part 4 — The 7 daily Antigravity prompts

Paste **one day per new Antigravity chat**: everything inside the grey block, from `YOUR TASK` to the end. Every day starts with **1 hour of PR review** (Part 2) before you paste the prompt.

| Day | Date | Focus | Branch | PR title |
|---|---|---|---|---|
| 1 | Mon 26 Oct | EHR test patients (8–12 sandbox + Synthea fill), doctor on record, EHR allergies | `feat/i2-0-ehr-test-patients` | I2-0 Day 1: EHR test patients + doctor on record |
| 2 | Tue 27 Oct | Guideline corpus manifest, ingestion + chunker, rules-vs-guidelines check | `feat/i2-2-corpus-ingest` | I2-2 Day 2: guideline corpus, ingestion, rules check |
| 3 | Wed 28 Oct | `ML_PLAN.md` decisions + RAG retriever + grounded explainer (EN/UR) + open-weight model choice | `feat/i2-2-retriever-explainer` | I2-2 Day 3: ML plan + retriever + grounded explainer |
| 4 | Thu 29 Oct | Experiment harness on Saad's toolkit + all model runs | `feat/i2-1-harness-experiments` | I2-1 Day 4: experiment harness + model runs |
| 5 | Fri 30 Oct | Model choice, model cards, export, `risk_agent` (pure inference), can-only-raise rule; bug bash | `feat/i2-1-risk-agent` | I2-1 Day 5: model cards + risk agent |
| 6 | Sat 31 Oct | LangGraph orchestrator around the complete-check-in pipeline, proven identical | `feat/i2-3-langgraph` | I2-3 Day 6: LangGraph orchestrator (equivalence-proven) |
| 7 | Sun 1 Nov | Risk + explanation + trace wired into check-ins behind flags (schema v14), API contract for Hassaan, weekly log, Week 2 gate | `feat/i2-1-2-3-wire` | I2 Day 7: risk + explanation + trace wired (flags off) |

**Who waits on whom this week (why the days are in this order)**
- **Day 3** needs Saad's Day 2 (feature map + label catalogue) merged. Review it first thing Wednesday.
- **Day 4** needs Saad's Day 3 (`evaluation.py`, `artifacts.py`, `ML_INTERFACES.md`) merged. Review and approve `ML_INTERFACES.md` first thing Thursday.
- **Day 7** needs Hassaan's Day 6 (schema v13) merged first, because your migration is v14. Review it first thing Sunday.
- **Saad's Day 6** validates whatever models you have saved by Saturday, so save your artifacts on Day 5.

**Things you do by hand, not the AI**
| When | Task |
|---|---|
| Before Mon | **Rotate the Groq key** that was exposed earlier: create a new one, put it in Render's environment and your local `.env`, delete the old one. Never paste it in any chat. |
| Before Mon | Send Saad the dataset folder (without `mimiciv\`), both team files, and your BigQuery queries. |
| Mon | Download Synthea and generate ~30 adults (Day 1 Part F tells you the command). |
| Mon–Tue | Download the guideline PDFs into `Chronicare-data\guidelines\` (list in Day 2). Email the AKU Pakistan-guideline author for the full document. |
| Tue evening | Send `docs/RULES_VS_GUIDELINES_2026.md` to the three doctors for written sign-off, with the vomiting item. |
| Wed morning | Make the decisions in `docs/ML_PLAN.md` (the agent drafts, you decide). |
| Wed | Write 15 test questions for the RAG smoke test (Day 3 Part D). |
| Thu morning | Approve or change Saad's `docs/ML_INTERFACES.md`. |
| Fri | 1-hour bug bash with the team on the live site. |
| Any day | Ask sir: contribution 4 in the paper, and the 65% shares. |

---

### DAY 1 — Monday 26 Oct — EHR test patients + doctor on record

```text
YOUR TASK (DAY 1, USMAN): connected mode gets 8–12 well-chosen test patients with diabetes and/or hypertension, active medicines, readings and a doctor. Gaps are filled with Synthea patients in the simulated hospital. The app also starts reading the doctor on record and EHR allergies. Branch: feat/i2-0-ehr-test-patients.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: data_sources/fhir_client.py, fhir_sim.py, fhir_adapter.py (additive functions only; existing behaviour unchanged), app_store.py and main.py (ONLY the suggested-patient lists and one additive optional field on the record response), app/components/ConnectionScreen.tsx and HealthRecordScreen.tsx, app/lib/api.ts, app/translations/index.ts. No triage, interview, reconciliation or verification code.

READ FIRST: docs/EHR_SANDBOX.md (all of it); data_sources/fhir_client.py, fhir_sim.py, fhir_adapter.py, medication_scope.py; scripts/probe_fhir.py; app_store.py around PUBLIC_SANDBOX_SUGGESTED_PATIENT_IDS and get_enabled_ehr_systems; main.py around SAMPLE_PATIENTS_LIST, SUGGESTED_PATIENT_IDS and GET /api/ehr/systems; app/components/ConnectionScreen.tsx; tests test_fhir_sim.py, test_ehr_connected.py, test_fhir_client.py.

PART A — Finder script: scripts/find_ehr_test_patients.py
A1. Uses the existing fhir_client.fhir_get (don't write a new HTTP client), against https://r4.smarthealthit.org.
A2. Search Condition?code=http://snomed.info/sct|44054006 (type 2 diabetes) and |59621000 (essential hypertension). Collect the patient ids and page through Bundle.link "next" up to a cap (--max-patients, default 300).
A3. For each candidate: age ≥ 18 and not deceased; active MedicationRequest count (and how many pass medication_scope); latest dates of HbA1c (4548-4), glucose (2339-0) and BP (85354-9 / 55284-4); Patient.generalPractitioner or the latest Encounter.participant Practitioner; AllergyIntolerance count.
A4. Throttle (≥ 0.3 s between calls), retry once on a timeout, cache raw answers under $CHRONICCARE_DATA_DIR/ehr_probe/ so re-runs don't hit the server again.
A5. Print a table sorted by "usefulness score" (has diabetes/HTN, in-scope active meds, readings, practitioner). This is public synthetic data, so printing it is allowed.

PART B — Choose and document: docs/EHR_TEST_PATIENTS.md
B1. Pick 8–12 patients covering: T2D only, HTN only, both; on insulin or a sulfonylurea; on 2+ BP medicines; older adult (75+); one with allergies; one with a practitioner, one without. Explain in one line per patient why it's in.
B2. A table: id, age, sex, conditions, in-scope meds, latest reading dates, practitioner (yes/no), what it tests.
B3. A "Gaps" section: what no sandbox patient covers (e.g. recent readings, since the sandbox data stops in 2020–2021). Part F fills these.

PART C — One list, not two
main.py (SUGGESTED_PATIENT_IDS, SAMPLE_PATIENTS_LIST) and app_store.py (PUBLIC_SANDBOX_SUGGESTED_PATIENT_IDS and the sim list) duplicate the same data. Move it to ONE module, data_sources/ehr_test_patients.py, with id, label, description, ehr_system_id and "simulated": bool. Both places import from it. /api/ehr/systems keeps returning the same JSON shape (a test compares the response before and after for the existing systems).

PART D — Doctor on record
D1. fhir_client: get_fhir_practitioner_for_patient(patient_id): Patient.generalPractitioner → Practitioner; else the latest Encounter's participant → Practitioner; else None. Same caching, the same SSRF guard, and the sim:// scheme works.
D2. fhir_sim: give every sim patient a Practitioner (made-up names, clearly fictional) and generalPractitioner references, except sim-newpatient (tests the "none" path).
D3. The record response gets an ADDITIVE optional field doctor_on_record: {"name", "identifier" (if any), "source": "ehr_general_practitioner" | "ehr_encounter", "as_of"}, or null. Connected mode only.
D4. HealthRecordScreen shows "Doctor on record: <name> (from your hospital record)". It is never worded as if the doctor reviewed this app's results. en + ur.

PART E — EHR allergies
E1. fhir_client.get_fhir_allergies(patient_id) + fhir_adapter normalisation (code text, criticality, verificationStatus; entered-in-error excluded).
E2. In connected mode, the record's allergies list includes them with origin "ehr" and trust high, read-only exactly like EHR medicines. Isolated mode is unchanged.

PART F — Synthea gap fill
F1. Usman runs Synthea by hand (Java 17+). Download synthea-with-dependencies.jar from https://github.com/synthetichealth/synthea/releases, then:
      java -jar synthea-with-dependencies.jar -p 30 -a 35-80 --exporter.fhir.export=true
    into a folder under $CHRONICCARE_DATA_DIR/synthea/. The agent checks the folder exists and prints the file count only.
F2. scripts/synthea_to_fhirsim.py: pick 3–5 bundles that fill the Part B gaps; keep only Patient, Condition, active MedicationRequest, Observations of glucose/HbA1c/BP from the last 30 days of the record, Practitioner, AllergyIntolerance. Re-base all timestamps relative to "now" the way fhir_sim does (T − hours/days), so readings are always recent. Strip names and replace them with clearly fictional ones; ids prefixed "sim-syn-".
F3. Write them as fixtures: backend-poc-technical/data_sources/fhir_sim_fixtures/sim-syn-*.json (synthetic, Apache-2.0, OK to commit; keep each file under 50 KB). fhir_sim loads them at import. Labels say "Simulated (Synthea)".

PART G — Tests (add to CI): backend-poc-technical/test_ehr_test_patients.py
- the single list module is the only source (grep-style test: the ids appear in no other .py file)
- /api/ehr/systems is unchanged for the existing systems
- every fixture loads; timestamps are within the last 30 days for any "now"; every Observation normalises through fhir_adapter
- a practitioner is found for every sim patient except sim-newpatient (None)
- allergies normalise; entered-in-error is excluded
- an end-to-end connected check-in through TestClient on EACH new sim-syn patient completes without error (any level)
- the existing tests (test_fhir_sim.py, test_ehr_connected.py, persona tests) still pass untouched
Vitest: the doctor-on-record line in en + ur, hidden when null.

ACCEPTANCE
 U1-01 Finder script run; the table pasted
 U1-02 EHR_TEST_PATIENTS.md with 8–12 patients + gaps
 U1-03 One patient list; /api/ehr/systems unchanged (test)
 U1-04 Doctor on record (FHIR + sim) end to end; screenshot en + ur
 U1-05 EHR allergies read-only in connected mode
 U1-06 3–5 Synthea fixtures, recent, < 50 KB each; e2e check-in per patient
 U1-07 Protected hashes identical; all gates green

FILES ALLOWED
Create: scripts/find_ehr_test_patients.py, scripts/synthea_to_fhirsim.py, backend-poc-technical/data_sources/ehr_test_patients.py, backend-poc-technical/data_sources/fhir_sim_fixtures/*.json, backend-poc-technical/test_ehr_test_patients.py, docs/EHR_TEST_PATIENTS.md, tests/doctor-on-record.test.tsx
Change: backend-poc-technical/data_sources/{fhir_client.py, fhir_sim.py, fhir_adapter.py, app_store.py}, backend-poc-technical/main.py (lists + one additive field), app/components/{ConnectionScreen.tsx, HealthRecordScreen.tsx}, app/lib/api.ts, app/translations/index.ts, docs/EHR_SANDBOX.md, docs/DATA_DICTIONARY.md, .github/workflows/ci.yml (pytest list)

PR TITLE: I2-0 Day 1: EHR test patients + doctor on record
REVIEWERS: Hassaan and Saad each check 4 patients by connecting to them on the deployed preview or locally.
```

---

### DAY 2 — Tuesday 27 Oct — Guideline corpus, ingestion, rules check

```text
YOUR TASK (DAY 2, USMAN): turn the guideline PDFs into clean, cited chunks the RAG can search, and check every number in our clinical rules against the 2026 ADA and 2025 AHA/ACC guidelines. No guideline text ever goes into Git. Branch: feat/i2-2-corpus-ingest.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: new files only (backend-poc-technical/rag/, scripts/rag/, docs/). docs/CLINICAL_RULES.md and agents/triage_protocol.py are READ-ONLY: you report differences, you never fix them.

COPYRIGHT RULE: guideline PDFs, extracted text and chunks live ONLY under $CHRONICCARE_DATA_DIR/guidelines and $CHRONICCARE_DATA_DIR/rag. Tests use hand-written FAKE guideline text ("FAKE GUIDELINE: ..."), never real passages. Quotes in docs are ≤ 25 words with a citation.

READ FIRST: handbook B9 (RAG design) and D5 (the corpus table); docs/CLINICAL_RULES.md; agents/triage_protocol.py constants and thresholds; docs/SOURCES_REVIEW.md.

THE PDFs (Usman downloads them by hand into $CHRONICCARE_DATA_DIR/guidelines/; check which exist, print names + sizes only):
  ada2026_sec02_diagnosis.pdf, ada2026_sec05_lifestyle.pdf, ada2026_sec06_glycemic_goals_hypoglycemia.pdf, ada2026_sec10_cvd_risk.pdf, ada2026_sec11_ckd.pdf, ada2026_sec13_older_adults.pdf  (diabetesjournals.org/care/issue/49/Supplement_1)
  aha_acc_2025_hbp_guideline.pdf (+ the executive summary if separate)
  who_2021_htn_pharmacological.pdf
  ish_2020_global_htn.pdf
  idf_dar_ramadan_2021.pdf
  pk_htn_women_2023.pdf
  aku_diabetes_pakistan_2023.pdf (the published article; the full guideline if the author replies)
Missing files → that source is NOT RUN, listed in the report.

PART A — Manifest: scripts/rag/build_manifest.py → docs/GUIDELINE_CORPUS.md
Per file: source_id, title, edition, publisher, URL, download date (file mtime), SHA-256, page count, priority (1 = our rules, 2 = ADA/AHA, 3 = WHO/ISH, 4 = Pakistan/IDF-DAR), and "terms of use: TO FILL BY USMAN". Re-running it updates the hashes. The doc says the files are not in Git and where they live.

PART B — Chunker: backend-poc-technical/rag/chunking.py (pure stdlib, so CI can test it)
B1. clean_page_text(text): drop running headers/footers (lines repeated on > 50% of pages), page numbers, hyphenation at line ends, reference lists (from "References" to the end of a section).
B2. split_sections(pages): detect headings (numbered "6.1", "Section 6", ALL-CAPS lines, "Recommendations"); keep a heading path ("6 Glycemic Goals > Hypoglycemia").
B3. Recommendations as their own chunks: ADA ("6.5 ... A") and AHA ("COR/LOE") boxes, with "grade" in metadata.
B4. chunk_section(): 200–400 words, 40-word overlap, never across sections, never splits a sentence or a table row.
B5. Metadata per chunk: chunk_id (sha1 of source_id + section + first 50 chars), source_id, title, edition, priority, section_path, page_start, page_end, grade (or null), condition ("diabetes" | "hypertension" | "both"), topics (keyword rules → slugs like hypoglycemia, bp_targets, bp_measurement, glucose_targets, ramadan_fasting, sick_day, older_adults, ckd, lifestyle, diagnosis_thresholds, emergency_signs).
B6. Every function is unit-tested on FAKE text.

PART C — Ingestion: scripts/rag/ingest.py (runs on Usman's machine only)
C1. scripts/rag/requirements.txt: pypdf (pinned). NOT added to the backend requirements.
C2. PDF → pages → chunking.py → $CHRONICCARE_DATA_DIR/rag/chunks.jsonl (+ chunks_meta.json with counts and the manifest hashes). Deterministic: the same PDFs give the same chunk_ids.
C3. Print per source: pages, sections, chunks, recommendation chunks, mean words per chunk, and 3 random chunk headings (headings only).
C4. Quality check: print the 10 shortest and 10 longest chunks' section paths + word counts. Fix the cleaner if junk (tables of contents, author lists) shows up, and say what you fixed.

PART D — Rules vs guidelines: docs/RULES_VS_GUIDELINES_2026.md
D1. List EVERY numeric threshold in docs/CLINICAL_RULES.md and the triage_protocol.py constants (e.g. BP ≥ 180/120 emergency, the BP-rise rule, glucose ≥ 300 / < 70 / < 54, baseline windows).
D2. For each: our value | ADA 2026 / AHA-ACC 2025 value (if any) | the chunk_id + section + page it came from | ≤ 25-word quote | MATCH / DIFFERENT / NOT IN GUIDELINE (an engineering choice) | proposed action.
D3. Search the chunks with a small script (keyword + section path). No LLM for this: it must be checkable.
D4. Mark the BP stages: the 2025 AHA/ACC guideline's stage definitions vs what CLINICAL_RULES.md cites (it currently cites the 2017 guideline). This is a DIFFERENT item for the doctors.
D5. The doc ends with "SENT TO DOCTORS: <date> — awaiting written sign-off" (Usman fills the date). No rule changes in code.

PART E — Tests (add to CI): backend-poc-technical/test_rag_chunking.py (FAKE text only)
- header/footer removal; hyphen join; references dropped
- the heading path is right on a fake 3-level document
- recommendation boxes become their own chunks with a grade
- chunk sizes within bounds; overlap present; no chunk crosses a section
- chunk_id is stable across runs
- condition and topic tagging on fake sentences

ACCEPTANCE
 U2-01 Manifest generated; terms of use marked TO FILL
 U2-02 Ingestion run: the counts table pasted; junk check done
 U2-03 Chunker unit-tested on fake text; in CI
 U2-04 RULES_VS_GUIDELINES_2026.md complete, every row cited; nothing changed in rules or code
 U2-05 No guideline text in git (git grep for 3 distinctive phrases from the PDFs returns nothing)
 U2-06 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/rag/{__init__.py, chunking.py}, scripts/rag/{build_manifest.py, ingest.py, requirements.txt, search_chunks.py}, backend-poc-technical/test_rag_chunking.py, docs/GUIDELINE_CORPUS.md, docs/RULES_VS_GUIDELINES_2026.md
Change: .gitignore (only if a rag/ data path is missing), .github/workflows/ci.yml (pytest list)

PR TITLE: I2-2 Day 2: guideline corpus, ingestion, rules check
```

---

### DAY 3 — Wednesday 28 Oct — ML plan + RAG retriever + grounded explainer

```text
YOUR TASK (DAY 3, USMAN): (1) draft docs/ML_PLAN.md from Saad's Day 2 work so Usman can make the decisions; (2) build the retriever and the explanation writer. The explainer explains the level the rules already decided, cites the guideline for every sentence, checks every number, and falls back to a safe template when anything is off. It can never change a level. Branch: feat/i2-2-retriever-explainer.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: new files under backend-poc-technical/rag/ and docs/; llm/groq_client.py is used, not changed. Not wired into check-ins yet (that's Day 7).

READ FIRST: docs/ML_FEATURE_MAP.md, docs/ML_LABEL_CATALOGUE.md, docs/DATA_CHECKS.md, docs/ML_BASELINE_TEMPORAL.md (Saad, Day 2); handbook B8, B9, B3 steps 10–12; backend-poc-technical/rag/chunking.py (Day 2); llm/groq_client.py (chat(), is_configured(), timeouts); main.py: what the stored "triage" dict looks like after a completed check-in (find where create_checkin_result is called with triage=...; list its keys from the code); docs/CLINICAL_RULES.md.

PART A — docs/ML_PLAN.md (the agent drafts, USMAN decides)
A1. One section per DECISION, each with: the options (from Saad's docs, with numbers), a recommendation with a one-line reason, and a line "USMAN DECISION: ____" left blank. Decisions:
    D1 Who sees which risk. Our users already HAVE diabetes and/or hypertension, so a model of "has diabetes" is useless for a diabetic. Recommended: the risk card shows the risk of the condition the patient does NOT have (hypertension-only → diabetes risk; diabetes-only → hypertension risk; both → no risk card in FYP-1).
    D2 The labels (per disease, from the catalogue). D3 Training population (all adults vs adults without the other condition). D4 Basic and full feature sets (only features the app collects or can start collecting, from the feature map). D5 Missing inputs (basic-model fallback vs "not enough information"; never silent imputation in the app). D6 Models to try. D7 Threshold policy (sensitivity ≥ 0.80 on validation). D8 Risk bands (low / moderate / high cut points). D9 The can-only-raise rule (high band may raise routine → review, never lowers; off until the doctors sign off). D10 Production format (exported logistic regression in pure Python unless a tree model beats it by ≥ 0.02 validation AUROC with OK calibration). D11 Success criteria for FYP-1.
A2. STOP after Part A and wait for Usman to fill the decisions and type "decisions done". Then continue with Part B. The PR includes the filled ML_PLAN.md.

PART B — Chunk store + retriever: backend-poc-technical/rag/store.py, retriever.py (pure stdlib)
B1. ChunkStore protocol with JsonlChunkStore(path) (dev/tests). A DB-backed store comes on Day 7.
B2. BM25 (k1 = 1.5, b = 0.75), implemented in Python (no rank_bm25 dependency), tokenised with lower-casing, unit normalisation (mg/dl → mgdl, mmhg) and number tokens kept.
B3. Filters: condition, topics, min priority. Ties go to the higher-priority source.
B4. Query building from a TRIAGE RESULT, not free text: a deterministic map from trigger category / reasons → topic slugs + query words (e.g. glucose_low → hypoglycemia; bp_severe → bp_targets + emergency_signs). It's a table in the code, tested.
B5. Dense retrieval decision: install fastembed with BAAI/bge-small-en-v1.5 in a scratch venv, embed the chunks, measure (a) peak RSS of the backend process with the model loaded and (b) retrieval quality vs BM25 on Usman's 15 smoke questions (Part D). Render free tier = 512 MB. Write the numbers in docs/RAG_DESIGN.md and the decision: BM25 only, or hybrid. The handbook's B9 says sentence-transformers + ChromaDB. If you go another way, say so and why (memory, ~3k chunks don't need a vector DB).

PART C — Explainer: backend-poc-technical/rag/explainer.py
C1. explain(triage_result: dict, readings: dict, language: "en"|"ur"|"roman_ur", store, llm=groq_client) -> dict:
    {"sentences": [{"text", "cites": [chunk_id]}], "sources": [{"chunk_id", "title", "edition", "section_path", "page_start"}], "language", "mode": "llm"|"template", "rejected_reasons": [...], "version"}
C2. It takes a deep COPY of its inputs and returns a new dict. A test asserts the input triage dict is byte-identical after the call.
C3. LLM call: the system prompt says: you explain a level ALREADY decided by clinician-approved rules; 2–3 sentences, ≤ 35 words each; plain words for a patient; every sentence ends with [S1]-style citations to the given passages; no new numbers; no medicine names with doses; no telling the patient to start, stop or change a medicine; no diagnosis; never say the situation is fine if the level is review or higher. Output JSON only. Temperature 0. Timeout 8 s.
C4. VALIDATORS (all must pass, else template):
    V1 valid JSON, 2–3 sentences, length limits
    V2 every sentence cites ≥ 1 passage that was actually retrieved
    V3 every number in the text (after unit normalisation) appears in the patient's readings, the triage result's thresholds, or the cited passage text
    V4 banned patterns (en + roman_ur + ur): dose units next to a medicine word; start/stop/increase/decrease/skip + medicine; "you have diabetes/hypertension" style diagnosis; "nothing to worry", "you are fine", "no need to see" when the level ≥ review
    V5 the level word used (if any) matches the decided level
C5. Urdu / Roman Urdu: translate the VALIDATED English with the LLM, then run V1, V3 and V4 again on the translation (numbers must be identical). Failure → the template in that language.
C6. Templates: backend-poc-technical/rag/templates.json, one per trigger category × language, with {placeholders} filled only from the triage result. Citations come from the top retrieved chunk's metadata. Every template is marked "needs_doctor_review": true.
C7. No API key, a timeout, an LLM error → template, mode "template", with the reason logged (no PHI in the log).

PART D — Smoke evaluation (local only): scripts/rag/smoke_eval.py
Usman writes 15 questions with the expected source + section in $CHRONICCARE_DATA_DIR/rag/smoke_questions.json (not committed). The script prints recall@4 and MRR for BM25 (and dense, if Part B5 tried it), plus 3 example explanations for 3 fake triage results. Saad's 60-question set (his Day 7) replaces this next week.

PART F — Open-weight model choice for the explainer (so the report can say which open model writes the explanations, and why)
F1. scripts/llm/list_models.py: list the models the configured Groq key can use (the SDK's models list call; print ids only). For each, find on Groq's model docs page (URL in the output) whether it's open-weight and its licence. Keep only open-weight chat models.
F2. scripts/llm/compare_explainer_models.py: run explain() on 12 FAKE triage results (all trigger categories + routine, en + ur + roman_ur) with 2–4 of those models (set via the model parameter, not by editing .env). Per model: validator pass rate (V1–V5 separately), template fallbacks, Urdu translation pass rate, p50/p95 latency, tokens used. No real patient data, only the fake results.
F3. docs/LLM_MODEL_CHOICE.md: the table, the chosen model (Usman decides), its licence and where its model card lives, and one paragraph: "The explanation layer uses an open-weight model served by Groq; the safety decision uses no model." Plus a "Future work (FYP-2)" paragraph: fine-tuning a small open medical model (e.g. MedGemma or a small Qwen) for Roman Urdu answer understanding, compared against the rule parser, a general LLM and Jev.
F4. Usman sets GROQ_MODEL locally and on Render to the chosen id. The PR body names it.

PART E — Tests (add to CI): test_rag_retriever.py and test_rag_explainer.py, using FAKE chunks + a FAKE llm object
- BM25 ranks the obviously relevant fake chunk first; filters work; ties go to priority
- the trigger → topic map covers every trigger category in triage_protocol.py (import the categories; fail if one is missing)
- each validator rejects its bad case: an uncited sentence, a citation to a non-retrieved chunk, a new number "take 500 mg", "stop your metformin", "you have diabetes", "you are fine" at level urgent, the wrong level word
- a good fake LLM answer passes and keeps its citations
- the Urdu translation with a changed number → Urdu template
- no key / timeout / exception → template; never raises
- the input triage dict is unchanged (deep compare)
- mutation proof in scripts/verify_mutations.py: disable V3 (numbers) → a test must KILL it

ACCEPTANCE
 U3-01 ML_PLAN.md drafted; Usman's decisions filled in; committed
 U3-02 Retriever + store; the BM25 vs dense numbers in RAG_DESIGN.md with a decision
 U3-03 Explainer with V1–V5; templates en/ur/roman_ur; never changes the level (test)
 U3-04 Smoke eval output pasted (recall@4, MRR, 3 example explanations)
 U3-05 Tests in CI; mutation killed
 U3-06 No guideline text in git; protected hashes identical; all gates green
 U3-07 Open-weight model comparison table pasted; GROQ_MODEL chosen and documented with its licence

FILES ALLOWED
Create: scripts/llm/{list_models.py, compare_explainer_models.py}, docs/LLM_MODEL_CHOICE.md, docs/ML_PLAN.md, docs/RAG_DESIGN.md, backend-poc-technical/rag/{store.py, retriever.py, explainer.py, templates.json, query_map.py}, scripts/rag/smoke_eval.py, backend-poc-technical/test_rag_retriever.py, backend-poc-technical/test_rag_explainer.py
Change: scripts/verify_mutations.py (append), .github/workflows/ci.yml (pytest list)

PR TITLE: I2-2 Day 3: ML plan + retriever + grounded explainer
REVIEWER: Saad (ML_PLAN.md + retriever)
```

---

### DAY 4 — Thursday 29 Oct — Experiment harness + model runs

```text
YOUR TASK (DAY 4, USMAN): one command runs any risk-model experiment from a JSON config, using Saad's evaluation toolkit, and saves models in the agreed artifact format. Then run every experiment ML_PLAN.md asks for. Branch: feat/i2-1-harness-experiments.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: backend-poc-technical/ml/experiments/ (new), configs, docs/ml/. Saad's files (evaluation.py, artifacts.py, labels.py, splits.py, common.py) are USED, not changed. If one has a bug, write a failing test, open an issue for Saad, and work around it in your code with a comment linking the issue.

READ FIRST: docs/ML_PLAN.md (the decisions are the spec), docs/ML_INTERFACES.md (approved this morning), backend-poc-technical/ml/{evaluation.py, artifacts.py, labels.py, splits.py, common.py}, docs/ML_FEATURE_MAP.md, docs/ML_LABEL_CATALOGUE.md.

PART A — backend-poc-technical/ml/experiments/run.py (+ README with the exact command that works from the repo root)
A1. The config schema (unknown keys are errors): name, dataset ("nhanes_core" | "brfss_core"), split, label, population (a filter from ML_PLAN D3, e.g. "adults_without_diabetes"), features, models, hyperparameter grid per model (≤ 6 combinations), threshold_policy, missing ("drop" | "impute_median_train"), seed, notes.
A2. Order: evaluation.check_leakage BEFORE loading → load + population filter → split → preprocessing fitted on train_core ONLY → fit each model and grid point → pick by validation AUROC → threshold with evaluation.choose_threshold on VALIDATION → test ONCE for the chosen model (all models on test only in a clearly labelled appendix) → metrics, CIs, calibration, subgroups (evaluation.py) → SHAP top 10 (LinearExplainer / TreeExplainer; permutation importance fallback, said in the report) → artifacts.save_model_artifact → report.md via evaluation.write_eval_report.
A3. BRFSS: use survey_weight ONLY for weighted prevalence in the report, not as sample_weight (say so). Its split: train 2015–2019, validation 2021, test 2023 (BRFSS has no seqn; split by year).
A4. Outputs under backend-poc-technical/ml/outputs/ (git-ignored); report text copied to docs/ml/experiments/<name>.md.

PART B — Configs from ML_PLAN.md (at least these 6)
 diabetes_basic_nhanes, diabetes_full_nhanes (no glycaemic inputs), htn_basic_nhanes, htn_full_nhanes (no BP inputs), diabetes_basic_brfss, htn_basic_brfss
 Models: lr, lr_balanced, rf, hgb (as ML_PLAN D6 says)
 Run all. Paste each headline table.

PART C — docs/ml/EXPERIMENTS_SUMMARY.md
One row per config: n train/val/test, test prevalence, best model, test AUROC [95% CI], sensitivity/specificity at the policy threshold, Brier, calibration slope, the worst subgroup sensitivity, and "beats S-6 baseline?" (0.7507 AUROC / 3.55% sensitivity). Then 5–8 honest sentences: what works, what doesn't, does the full model add enough over basic to justify asking for more inputs, any subgroup that's unsafe.

PART D — Tests (ml-tests job): backend-poc-technical/ml/tests/test_harness.py, on synthetic data
- the leakage guard fires before any data loads
- unknown config key → error
- preprocessing sees train rows only; threshold and model selection never see test (spy on Saad's functions and compare index sets)
- same seed → identical metrics.json
- the artifact folder validates with artifacts.validate_model_card
- the population filter applies before the split

ACCEPTANCE
 U4-01 6 configs run; headline tables pasted
 U4-02 EXPERIMENTS_SUMMARY.md honest, with the baseline comparison
 U4-03 Artifacts saved for every best model (paths shown; not committed)
 U4-04 Harness tests pass; no test peeking (test)
 U4-05 No data or outputs in git; protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/ml/experiments/{__init__.py, run.py, README.md, configs/*.json}, backend-poc-technical/ml/tests/test_harness.py, docs/ml/experiments/*.md, docs/ml/EXPERIMENTS_SUMMARY.md
Change: backend-poc-technical/ml/requirements.txt (pinned additions only)

PR TITLE: I2-1 Day 4: experiment harness + model runs
REVIEWER: Saad
```

---

### DAY 5 — Friday 30 Oct — Model choice, model cards, risk agent + bug bash

```text
YOUR TASK (DAY 5, USMAN): choose the production models, document them honestly, export them, and build the risk agent that runs them inside the backend with no scikit-learn. It is advisory: by default it never touches a triage level. Branch: feat/i2-1-risk-agent.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: new files under backend-poc-technical/agents/ (risk_agent.py, risk_rules.py), backend-poc-technical/models/ (exported JSON), backend-poc-technical/ml/export/, docs/. No changes to existing agents or main.py (wiring is Day 7).

READ FIRST: docs/ML_PLAN.md (D1, D5, D8, D9, D10), docs/ml/EXPERIMENTS_SUMMARY.md and the per-config reports, docs/ML_INTERFACES.md, agents/triage_protocol.py (_raise_level and the level order: read-only).

PART A — Model choice + model cards
A1. Per disease, basic and full: apply ML_PLAN D10 and record the choice in docs/ML_MODEL_CARDS.md. One card per production model: intended use (advisory, cross-condition per D1), out of scope (diagnosis, children, pregnancy, non-adults), data and population, label, features with units, test metrics with CIs, calibration, subgroup table, external validation ("Saad, Day 6: pending" until his PR lands), limitations (US data, not South Asian; self-report labels; weights not used in training; top-coding), version, training commit, owner.
A2. Mark plainly whether each model beats the S-6 baseline.

PART B — Export: backend-poc-technical/ml/export/export_lr.py
B1. From a saved artifact (a logistic regression pipeline with StandardScaler and maybe a median imputer) → backend-poc-technical/models/<model_name>.json: {name, version, label, features: [{name, unit, mean, scale, median}], coefficients, intercept, threshold, bands, training_commit, sklearn_version, created_at}. Coefficients aren't data; these small files are committed.
B2. Golden check: export 1,000 synthetic rows' predict_proba from sklearn into backend-poc-technical/models/<model_name>.golden.json (inputs + expected probabilities).
B3. If ML_PLAN chose a tree model for any disease: STOP and report the size and memory cost of shipping scikit-learn to Render (pip install in a clean venv, measure the import RSS). Usman decides; don't add sklearn to the backend requirements.

PART C — backend-poc-technical/agents/risk_agent.py (pure stdlib)
C1. load_models(dir) once at import; assess(profile: dict, latest_readings: dict, conditions: list) -> dict | None:
    - applicability per ML_PLAN D1 (which disease's risk, or None)
    - choose full if all its features are present, else basic, else {"status": "not_enough_information", "missing": [...]}
    - unit conversions from the app's stored units (cm/kg/mg/dL/mmHg; check how profile values are stored, file:line)
    - probability = sigmoid(intercept + Σ coef × (x − mean)/scale)
    - band per ML_PLAN D8
    - top 3 reasons = the largest positive contributions coef × (x − mean)/scale, in plain words en/ur/roman_ur from a label map ("your waist size", "your age"), never numbers the patient didn't give
    - output: {"status": "ok", "disease", "model_name", "model_version", "probability", "band", "reasons": [...], "advisory": true}
C2. It never raises. Bad input → {"status": "error", "reason"} and a log line without values.
C3. backend-poc-technical/agents/risk_rules.py: apply_risk_to_level(level, risk) -> (level, raised: bool). ONLY routine → review when band == "high" AND the env flag RISK_CAN_RAISE == "true" (default false); it never returns a lower level (it uses the same level order as triage_protocol, imported, not copied).

PART D — Tests (add to CI): test_risk_agent.py, test_risk_rules.py
- the golden file: risk_agent probabilities match sklearn's within 1e-9 for every row
- applicability: HTN-only → diabetes risk; T2D-only → HTN risk; both → None
- basic fallback; not_enough_information lists the missing features
- reasons are the top positive contributions (hand-checked case)
- unit conversion (feet/inches and pounds from the Oct 16 unit toggles, if the profile stores them)
- never raises on garbage input
- apply_risk_to_level: flag off → unchanged; flag on → only routine → review; never lowers, for every level × band (parametrised)
- mutation proofs in scripts/verify_mutations.py: (1) allow apply_risk_to_level to lower a level → KILLED; (2) ignore the flag → KILLED

PART E — Bug bash (1 hour, with the team, live site, fake accounts). File issues with the "week2-bash" label.

ACCEPTANCE
 U5-01 ML_MODEL_CARDS.md complete and honest
 U5-02 Exported JSON + golden files; the golden test passes
 U5-03 risk_agent pure stdlib; applicability per D1; reasons in en/ur/roman_ur
 U5-04 apply_risk_to_level can't lower (test + mutation); flag default off
 U5-05 Bug-bash issues filed
 U5-06 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/agents/{risk_agent.py, risk_rules.py}, backend-poc-technical/models/*.json, backend-poc-technical/ml/export/{__init__.py, export_lr.py}, backend-poc-technical/test_risk_agent.py, backend-poc-technical/test_risk_rules.py, docs/ML_MODEL_CARDS.md
Change: scripts/verify_mutations.py (append), .github/workflows/ci.yml (pytest list), .env.example (RISK_ENABLED=false, RISK_CAN_RAISE=false)

PR TITLE: I2-1 Day 5: model cards + risk agent
REVIEWER: Saad
```

---

### DAY 6 — Saturday 31 Oct — LangGraph orchestrator, proven identical

```text
YOUR TASK (DAY 6, USMAN): run the complete-check-in pipeline as a LangGraph graph over one shared state, behind a flag, with PROOF that every output is identical to today's code on all personas and scenarios. Each node also writes a step to a trace (the future "How this was decided" view). Branch: feat/i2-3-langgraph.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: main.py (ONLY to move the inline logic of complete_checkin_endpoint into functions, and to call the graph when the flag is on), a new backend-poc-technical/orchestrator/ package, requirements.txt (langgraph, pinned). The safety agents' code is NOT changed: the graph calls them exactly as main.py does today.

READ FIRST: main.py complete_checkin_endpoint (from @app.post("/api/checkins/{checkin_id}/complete") to its end, IN FULL) and every helper it calls; agents/reconciliation_agent.py and verification_agent.py signatures; scripts/run_v3_personas.py, scripts/engine_equivalence.py, test_engine_equivalence.py, test_sim_personas.py, scenarios/; handbook B2/B3.

PART A — Refactor first, with NO behaviour change (its own commit)
A1. Extract the endpoint's inline steps into pure-ish functions in backend-poc-technical/orchestrator/steps.py: load_and_guard, handle_emergency_v3, build_bundles, reconcile, verify, merge_triage, persist_result, build_response (names may differ; each a clear unit).
A2. The endpoint calls them in the same order. The full gates must pass with ZERO test changes before Part B starts. Paste the counts.

PART B — The graph: backend-poc-technical/orchestrator/graph.py
B1. CheckinState (TypedDict): checkin, user, mode, bundles, recon_result, verif_result, triage, result, emergency, trace: list, errors: list.
B2. Nodes wrap the Part A functions, one each; conditional edges: emergency → persist (skip reconcile/verify, exactly as today); connected vs isolated paths as today.
B3. Every node appends a trace step: {"node", "started_at", "ms", "summary"} where summary holds counts and levels only (e.g. "3 observations compared, 1 conflict"), never values or names.
B4. Flag: ORCHESTRATOR = "direct" (default) | "graph". The endpoint picks the path at request time.
B5. The graph is compiled once at import. No checkpointer, no network, no LLM.

PART C — Equivalence proof
C1. scripts/orchestrator_equivalence.py runs EVERY persona from run_v3_personas.py, the 7 POC scenarios, and the engine-equivalence cases through both paths (TestClient, temp DB, ORCHESTRATOR toggled) and compares the complete-response JSON field by field (ignoring timestamps and ids), plus the stored checkin_results rows.
C2. Prints a table: case | direct level | graph level | identical (yes/no). Expect 100% identical. ANY difference = a bug in your refactor: fix it, never the test.
C3. backend-poc-technical/test_orchestrator_equivalence.py runs a representative subset in CI (all trigger categories, emergency, connected + isolated).

PART D — Memory and speed on Render's free tier
D1. Measure the backend process RSS after startup with and without importing langgraph (psutil in a scratch venv or /proc on WSL). Paste both numbers.
D2. Measure p50/p95 of the complete endpoint for 50 runs per path locally. Paste.
D3. If RSS rises by > 80 MB, say so and propose options (lazy import, or a small hand-written state machine with the same interface). Usman decides.

ACCEPTANCE
 U6-01 Refactor commit with zero test changes; all gates green before the graph
 U6-02 Graph behind ORCHESTRATOR flag; default direct
 U6-03 Equivalence table: every case identical (pasted); CI subset added
 U6-04 Trace steps with counts/levels only (test: no reading values or names in the trace)
 U6-05 RSS + latency numbers pasted
 U6-06 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/orchestrator/{__init__.py, steps.py, graph.py, state.py}, scripts/orchestrator_equivalence.py, backend-poc-technical/test_orchestrator_equivalence.py, docs/ORCHESTRATOR.md (graph picture as Mermaid + the node list + the flag)
Change: backend-poc-technical/main.py (endpoint body → step calls + flag), backend-poc-technical/requirements.txt (langgraph pinned), .env.example (ORCHESTRATOR=direct), .github/workflows/ci.yml (pytest list)

PR TITLE: I2-3 Day 6: LangGraph orchestrator (equivalence-proven)
REVIEWER: Hassaan (runs the equivalence script himself)
```

---

### DAY 7 — Sunday 1 Nov — Wire risk + explanation + trace (flags off), weekly log, Week 2 gate

```text
YOUR TASK (DAY 7, USMAN): the risk card, the guideline explanation and the decision trace are produced for every completed check-in when their flags are on, stored, and returned to the patient and the clinician through additive API fields. With the flags off, nothing changes. Hassaan gets a written API contract to build the screens on in Week 3. Branch: feat/i2-1-2-3-wire (from dev AFTER Hassaan's schema v13 PR is merged).

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: app_store.py (schema v14: three nullable JSON columns + migration), orchestrator/ (two new nodes), main.py (additive response fields; the direct path calls the same two steps), rag/store.py (DB-backed chunk store), scripts/rag/load_chunks.py, scripts/mysql_preflight.py (expected version 14). No safety agent code.

READ FIRST: Day 3–6 code (rag/, agents/risk_agent.py, agents/risk_rules.py, orchestrator/); app_store.py migrations and the v13 migration Hassaan just added (copy its style); create_checkin_result and get_checkin_result; CheckinCompleteResponse and ReviewDetailResponse in main.py.

PART A — Schema v14
A1. checkin_results gets risk_json, explanation_json, trace_json (nullable TEXT / MySQL TEXT). Plus a table guideline_chunks (chunk_id PK, source_id, title, edition, priority, section_path, page_start, page_end, grade, condition, topics_json, text, loaded_at).
A2. An idempotent migration v13 → v14 for both backends; test_schema_v13_to_v14.py modelled on Hassaan's v12 → v13 test; mysql_preflight expects 14.

PART B — Chunks into the database (no guideline text in Git, but available on Render)
B1. scripts/rag/load_chunks.py reads $CHRONICCARE_DATA_DIR/rag/chunks.jsonl and upserts into guideline_chunks using the app's own DB config (DATABASE_URL / MYSQL_URL from the environment, never printed). It prints counts only.
B2. rag/store.py gets DbChunkStore. At startup, if EXPLAIN_ENABLED is true, the chunks are loaded into memory once (count logged). JsonlChunkStore stays for dev/tests.
B3. Usman runs load_chunks.py against Aiven MySQL by hand after the PR merges. The PR body says so.

PART C — Two new steps, in BOTH paths (direct and graph)
C1. risk step: if RISK_ENABLED, call risk_agent.assess on the patient's profile + this check-in's readings. If RISK_CAN_RAISE is also true, apply_risk_to_level and record "raised": true/false in the risk JSON; else the level is untouched.
C2. explain step: if EXPLAIN_ENABLED, call explainer.explain on a COPY of the final triage, in the patient's language.
C3. Both run AFTER the final triage is decided, in try/except. A failure stores {"status": "error"} and NEVER fails the check-in or changes emergency, requires_review, max_severity, triage_level or triage.
C4. The trace (graph path) gets the two steps. The direct path builds the same trace shape (so the clinician view doesn't depend on the flag).
C5. persist: risk_json, explanation_json, trace_json saved with the result. Idempotent re-complete returns the stored values (no second LLM call).

PART D — API (additive, optional fields)
D1. CheckinCompleteResponse: risk, explanation (patient-facing: band + reasons; sentences + sources; NO probability for the patient).
D2. ReviewDetailResponse: risk (with probability, model name/version, raised), explanation (with mode and rejected_reasons), trace.
D3. docs/API_RISK_EXPLAIN.md: the contract for Hassaan. Exact JSON examples for every state: ok, not_enough_information, not applicable (null), error, template-mode explanation, Urdu. Plus the wording rules: "advisory, not a diagnosis"; never show the probability to patients; show sources as "ADA 2026, Section 6".
D4. docs/AUTH.md and docs/DATA_DICTIONARY.md updated.

PART E — Tests (add to CI): test_checkin_risk_explain.py
- flags off: the complete response and the stored row are IDENTICAL to before (run the orchestrator-equivalence subset with flags off)
- flags on: every safety field is identical to flags-off for every case in the subset (risk/explanation can't move a level unless RISK_CAN_RAISE)
- RISK_CAN_RAISE on: only routine → review, only on band high
- explainer raising / LLM down → check-in still completes; explanation null or template
- idempotent complete: the LLM is called once (spy)
- a patient sees no probability; a provider does
- the trace has no reading values or names
Mutation proof: make the explain step write into triage → KILLED.

PART F — Weekly log + Week 2 gate
F1. docs/weekly/2026-W44-usman.md: done (PR links), numbers (patients added, chunks, experiments, AUROCs, equivalence 100%?), what slipped, decisions made, doctor sign-off status, next week's top 3.
F2. docs/weekly/2026-W44-gate.md: the Week 2 gate checklist with PASS/FAIL per item, from all three people's PRs: EHR patients live; ML_PLAN.md agreed; OCR tool chosen; trend agent merged; the interview audit done; data checks done. Each item links its PR.

ACCEPTANCE
 U7-01 Schema v14 migration tested; preflight expects 14
 U7-02 Chunk loader + DbChunkStore; no guideline text in git
 U7-03 Flags off → identical (test); flags on → safety fields identical (test)
 U7-04 Can-raise only routine → review under its flag (test)
 U7-05 API contract doc for Hassaan with every state
 U7-06 Weekly log + Week 2 gate doc
 U7-07 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/test_schema_v13_to_v14.py, backend-poc-technical/test_checkin_risk_explain.py, scripts/rag/load_chunks.py, docs/API_RISK_EXPLAIN.md, docs/weekly/2026-W44-usman.md, docs/weekly/2026-W44-gate.md
Change: backend-poc-technical/data_sources/app_store.py, backend-poc-technical/main.py (additive fields + step calls), backend-poc-technical/orchestrator/*, backend-poc-technical/rag/store.py, scripts/mysql_preflight.py, scripts/verify_mutations.py (append), .env.example (EXPLAIN_ENABLED=false), docs/AUTH.md, docs/DATA_DICTIONARY.md, .github/workflows/ci.yml (pytest list)

PR TITLE: I2 Day 7: risk + explanation + trace wired (flags off)
PR BODY MUST INCLUDE: "PRODUCTION DB MIGRATION: run scripts/mysql_preflight.py before and after deploying; expected schema 14. Then run scripts/rag/load_chunks.py once. All three flags stay false on Render until the doctors sign off."
```

---

## Part 5 — Added for Week 3 (2–8 Nov): the Jev answer-understanding test

**Why:** Jev (TypeSafe AI) is a closed "decision model". It picks one answer from a fixed list and returns a calibrated probability, fast and cheap. That suits "the model proposes, the rules decide": it can only *propose* how to read an unclear patient answer, and the patient confirms. It never touches triage or red flags.

**Before Week 3 (you, by hand):**
- Make an account at console.typesafe.ai (or use it through OpenRouter). Put about $10 of credit on it and save the key as `JEV_API_KEY` in your `.env` only. Hassaan runs with his own key or a key you share outside chat.
- **Privacy gap found while checking:** the consent text (`consentBody` in `app/translations/index.ts`) doesn't say that answers are sent to outside AI services. Groq already processes voice and text today. Decide the new sentence (en + ur) and clear it with the doctors/supervisor. Until it's live, Jev and any new AI service run on **fake data only**.

**Owner:** Hassaan (he owns answer understanding). Usman reviews. This prompt goes into Hassaan's Week 3 file as Day 1.

```text
YOUR TASK (WEEK 3 DAY 1, HASSAAN): measure, on the same answer set, how well three methods understand patient answers: (1) the rule parser from Week 2 (agents/answer_understanding.py), (2) the Groq open-weight LLM the app already uses, (3) Jev. Then wire the best non-rule method as a FALLBACK that runs only when the rules return "unclear", behind a flag, and only proposes an interpretation the patient must confirm. Branch: feat/i2-4-answer-fallback.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_USMAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC-IV data.
- Fake data only, everywhere (tests, screenshots, the live site).

PROTECTED FILES (hash them before and after; change them ONLY if this prompt explicitly allows it)
  backend-poc-technical/agents/triage_protocol.py
  backend-poc-technical/agents/input_triage.py
  backend-poc-technical/agents/answer_validation.py
  backend-poc-technical/agents/verification_agent.py
  backend-poc-technical/agents/reconciliation_agent.py
  backend-poc-technical/agents/adaptive_interview_agent.py
  backend-poc-technical/agents/medication_confirmation.py
  docs/CLINICAL_RULES.md
Hash command:
  Get-FileHash -Algorithm SHA256 <each file> | Format-Table Hash, Path -AutoSize
(Windows line endings can change a hash between machines. Compare before and after on THIS machine only.)

PRE-FLIGHT (do this first, print the outputs)
 1. git status (must be clean). If not clean, STOP and tell me what is uncommitted.
 2. git switch dev; git pull; git log -1 --oneline
 3. Create today's branch from dev, as named in this prompt. If yesterday's PR isn't merged yet, branch from yesterday's branch instead and say so in the report.
 4. Print the SHA-256 of every protected file ("BEFORE").
 5. Baseline gates, so we know what was already failing before you started:
    - python backend-poc-technical/init_local_db.py
    - the EXACT pytest command from .github/workflows/ci.yml (step "Run Backend Pytest Suite (Hermetic)"). Copy it from the file; don't retype it from memory.
    - npm test
    Print the pass/fail counts.
 6. Read every file you plan to change, IN FULL, before editing it.
 7. Show me a numbered plan: each file you will create or change, and why. Then WAIT for me to type "go".

WHILE WORKING
- Small, meaningful commits under my git identity, with messages like "feat(scope): what".
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it).
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise).
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added)
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (pip install ruff in the venv if missing)
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. If WSL with Ubuntu is installed: run gate 1 again inside WSL with Python 3.11. Otherwise write "WSL NOT RUN".

PUSH AND PR
- git push -u origin <branch>
- If "gh auth status" shows logged in: gh pr create --base dev --head <branch> --title "<title from this prompt>" --body-file <your report saved as a temp .md file, NOT committed>
- Otherwise print https://github.com/UsmanBari/ChronicCare-AI/compare/dev...<branch>?expand=1 and write "PR NOT CREATED".

FINAL REPORT (in this chat, in this order)
 1. Summary (5 lines max)
 2. Files changed (git diff dev --stat)
 3. What you built, part by part
 4. Evidence: every command you ran, with its real output (trim the middle of long outputs, never the end)
 5. Acceptance table: ID | check | PASS / FAIL / NOT RUN | where the evidence is
 6. Protected-file hashes, BEFORE vs AFTER
 7. Three lists:
    "CORRECTIONS TO MY EARLIER REPORT" (anything you said earlier in this chat that turned out wrong)
    "OPEN QUESTIONS FOR USMAN / DOCTOR"
    "NOT DONE, DIFFERENT, OR UNSURE"
 8. Three viva questions an examiner could ask about today's work, with short answers in simple words
=================================================================================

PERMISSION FOR TODAY: new files under backend-poc-technical/llm/ and agents/; agents/interview_v3_runner.py (only the call site where a slot answer is "unclear"); app/translations/index.ts (the consent sentence Usman approved + the confirmation question); test_consent_lines.py ONLY to update the expected consent text to Usman's approved wording (say so in the report). No triage, input_triage, red-flag or verification code. The danger-phrase screen still runs FIRST on every answer, unchanged.

READ FIRST: agents/answer_understanding.py and its tests; interview_v3_runner.next_turn; docs/INTERVIEW_V3_FLOW_RULES.md; scripts/probe_interview.py + probe_scenarios.json; llm/groq_client.py; docs/LLM_MODEL_CHOICE.md; Jev's current API docs (console.typesafe.ai docs, or its OpenRouter model page): request format, the choice/yes-no output, the probability field, limits, data retention. Write what you found in docs/ANSWER_FALLBACK_DESIGN.md before coding.

PART A — The answer set: tests/sim/answer_understanding_set.json
200+ items {question_slot, question_text, answer_text, language: en|ur|roman_ur, gold: yes|no|unclear|<number>|<option>}: from the probe scenarios, the 52 personas' answers, plus hand-written hard cases (negations "nahi to nahi", hedges "thora sa", typos, mixed script, sarcasm, answers to a different question). Hassaan labels gold by hand. At least 60 Urdu-script and 60 Roman Urdu items.

PART B — Comparison: scripts/compare_answer_understanding.py
For each method: accuracy overall and per language; accuracy on items the rules call "unclear"; how often a method turns a gold "unclear" into a confident wrong answer (the dangerous error); calibration of Jev's probability (reliability by 5 bins); p50/p95 latency; cost per 1,000 answers. Only the question text and the answer text are sent: no names, ids or other answers. Prints one table; writes docs/ANSWER_FALLBACK_RESULTS.md.

PART C — The fallback (behind ANSWER_FALLBACK = none (default) | groq | jev)
C1. Order: danger screen (unchanged) → rule parser → ONLY if "unclear" → the fallback provider.
C2. The fallback returns {value, probability}. If probability ≥ the threshold chosen from Part B (set so that confident-wrong ≤ 2% on the set) → the app asks "Did you mean: <value>?" (en/ur/roman_ur) and fills the slot ONLY after the patient says yes. Below the threshold → it re-asks the question as today.
C3. A timeout (1.5 s), an error or no key → behave exactly as ANSWER_FALLBACK=none.
C4. The slot evidence records method = "rules" | "fallback_confirmed", so a clinician can see it.

PART D — Tests (add to CI)
- flag none → the interview is identical to today (run the v3 persona subset)
- the fallback is never called when the rules are confident, or when the danger screen fires (spy)
- a slot is never filled from the fallback without the patient's "yes"
- timeout/error → same as none
- only question + answer text leave the app (inspect the outgoing payload in a fake provider)
- the consent text test matches the approved wording in en + ur
Mutation proof: fill the slot without confirmation → KILLED.

ACCEPTANCE
 W3H1-01 200+ labelled answers; Hassaan labelled them by hand
 W3H1-02 The comparison table for 3 methods pasted (incl. confident-wrong rate and Jev calibration)
 W3H1-03 Fallback behind the flag; confirmation required (test + mutation)
 W3H1-04 Flag off → identical interview (test)
 W3H1-05 Consent wording updated as approved; fake data only until it's live
 W3H1-06 Protected hashes identical; all gates green

PR TITLE: I2-4 W3 Day 1: answer understanding — rules vs open LLM vs Jev + confirmed fallback
```

**Kept for FYP-2 (goes in the paper's future work):** fine-tune a small open medical model (e.g. MedGemma or a small Qwen) on that same answer set and add it as a fourth row in the comparison.

---

## Appendix B — Who does what this week (so your work fits with the others')

| Person | Role this week | Main outputs |
|---|---|---|
| **Usman** | Lead, **ML owner**, reviewer | ML: `docs/ML_PLAN.md`, the experiment harness, training, model choice, SHAP, the risk card in the app. Also: safety-rule changes, the guideline corpus, reviews and merges every PR, decides whether v3 goes to production |
| **Hassaan** | Interview + records | Interview audit → v3 answer understanding → dual-diagnosis flow → full Urdu / Roman Urdu → OCR spike → record edit history → OCR v1 behind a flag |
| **Saad** | Helping on ML + owning trends | Data scripts + data checks → time-based split + feature map / label catalogue drafts → evaluation toolkit + model-file contract for Usman's harness → trend agent → trends live on the site → external validation of Usman's models → coverage + fixes |

**How the pieces connect**
- Saad's **feature map** (Day 2) is a draft that tells Usman which inputs the app can really collect. Hassaan's interview work (Days 2–4) is where any new input would be asked. If Saad's map says a feature is "not collected", don't add a question for it yourselves; Usman decides.
- Saad's **trend agent** (Days 4–5) reads readings from completed check-ins. Hassaan's **edit history** (Day 6) changes record values, not check-in readings. The two must not touch each other's files.
- Both of you join the **Friday bug bash** (1 hour, live site, fake accounts). Issues are labelled `week2-bash`. Saad fixes non-safety ones on Day 7; safety-area ones go to Usman.
- **Never edit the same file on the same day without telling the other person.** The shared ones this week are `.github/workflows/ci.yml` (the pytest list only), `app/translations/index.ts`, `app/lib/api.ts` and `backend-poc-technical/main.py`. If both PRs change one, the second to merge rebases: `git fetch origin; git rebase origin/dev`, fix the conflicts, re-run the gates, `git push --force-with-lease` **on your own branch only**.

**Dates**
| Date | What |
|---|---|
| Sun 1 Nov | End of Week 2: all 7 PRs open, weekly logs written |
| Sun 8 Nov | **Features done:** risk models in the app (behind a flag), trends live, v3 decision made, OCR + edit history merged, explanations v1 |
| Tue 10 Nov | **Code freeze:** only bug fixes, tests and docs after this |
| Wed 11 – Sat 14 Nov | Final bug bash, doctor sign-off, small usability test (3–5 people), report and slides |
| Sun 15 Nov | Report and slides final; full demo rehearsal on the live site |
| Mon 16 Nov | Buffer day; final `dev` → `main` deploy in the morning + smoke test |
| **Tue 17 Nov** | **FYP-1 final evaluation** |

**Daily message to Usman (WhatsApp, every evening, 4 lines)**
```
Day N: <PR link or "not pushed: why">
Gates: CI pytest X passed / Y failed; vitest X/Y; mutations X/Y killed
Blocked on: <nothing / what>
Tomorrow: <one line>
```

---

# Appendix A — The full project handbook

> The prompts call this "the handbook". Its sections (Part 0, A1…F) are referenced by name, e.g. "handbook B9".

## ChronicCare AI — Complete Project Handbook (for AI assistants and team members)

> **Who this is for.** You are an AI coding assistant (or a teammate) working on **ChronicCare AI**, a final-year project at FAST-NUCES Islamabad. This file is the full background: what the project is and why it exists, what the finished system will be, exactly what is built today, how we will get from here to the end, and how to work in the codebase without breaking anything.
>
> **As of:** 24 October 2026. Repository `github.com/UsmanBari/ChronicCare-AI`, commit `6e28b0a` (`main` = `dev`, last merged 16 Oct 2026).
>
> **How to use it.** Read Part 0 fully. Then read the parts your task touches. Your actual task arrives separately (a task prompt, or the Iteration 2 file). When this file and the code disagree, **the code wins** — say so in your reply instead of guessing. When anything here is marked *planned*, it does **not** exist in the code yet.

---

### Contents

- **Part 0** — Rules for you (read first)
- **Part A** — What the project is and why it exists
- **Part B** — The finished system (target design for the end of FYP-2)
- **Part C** — What exists today, in detail
- **Part D** — How we get there (roadmap, Iteration 2, evaluation, data, guidelines, risks)
- **Part E** — Engineering handbook (setup, tests, CI, git, conventions, how-to recipes)
- **Part F** — Reference (docs index, glossary, viva quick answers)

---

## Part 0 — Rules for you (read first)

1. **No claim without evidence.** Never say "verified", "all tests pass", "works", or quote a number unless you ran the command and can paste its real output. Earlier AI agents on this project reported results that were not true; every claim is now checked by hand against the output.
2. **Never lower a triage level.** The core safety rule is *the model proposes, the rules decide*. Anything new (ML, RAG, trend, LLM, OCR) may **raise** a level or **explain** it, never set it, never lower it.
3. **Do not touch the clinical safety code unless the task explicitly says so:** `agents/triage_protocol.py`, `agents/input_triage.py`, `agents/answer_validation.py`, the red-flag parts of `agents/adaptive_interview_agent.py`, the emergency path in `main.py`, `agents/verification_agent.py`, and `docs/CLINICAL_RULES.md`. A change there needs a test, a mutation proof, an update to `CLINICAL_RULES.md`, and doctor review before it goes live.
4. **Unknown is never "no".** A missing, skipped or unclear answer is stored as `unknown`, and an unknown warning-sign answer raises the level.
5. **No real patient data anywhere.** Fake data only, in code, tests, screenshots and the live site. Never paste raw rows of MIMIC-IV, DHS or any credentialed dataset into any AI tool (including you); share only counts, column names, shapes and error messages.
6. **Never commit secrets or data:** `.env`, `.env.local`, Groq key, Firebase config values, MySQL URL, Render deploy hook, the `dataset/` folder, guideline PDFs.
7. **English and Urdu stay in sync.** Every new patient-facing string goes into `app/translations/index.ts` in both languages. Urdu is right-to-left.
8. **No fake values in the UI.** Never show a made-up risk score, SHAP value or reading. The test `tests/no-fake-values.test.tsx` and `tests/honest-labels.test.ts` exist for this.
9. **No compliance or effectiveness claims** ("HIPAA compliant", "FDA approved/cleared", "GDPR compliant", "clinically validated"). CI fails the build if it finds them in `app/`.
10. **New backend test files must be added to the CI list** in `.github/workflows/ci.yml` (pytest runs an explicit file list; an unlisted file never runs in CI).
11. **Small, explainable changes.** The student who merges your code must explain every line in a viva. Prefer readable code over clever code, keep changes inside the files the task names, and explain what you changed and why.
12. **Work on a feature branch** and open a pull request into `dev`. Never commit to `main` or `dev` directly.
13. **When unsure, stop and ask** rather than inventing clinical content, thresholds or medical wording.

---

## Part A — What the project is and why it exists

### A1. The project in one paragraph

ChronicCare AI is a bilingual (English/Urdu) web platform for adults living with **type 2 diabetes and/or hypertension**, designed for the Pakistani setting. Between doctor visits, the patient does a short **daily check-in** by text or voice. An **adaptive interview** asks condition-specific follow-up questions the way a chronic-care nurse would; every answer is screened for **danger signs**; dangerous readings start **confirmation protocols**; the patient's report is **compared with their health record** (reconciliation) and **checked** (verification); and the case gets one of four levels — **emergency, urgent, review, routine**. Anything that needs a human lands in a **clinician review queue**. It works **connected** to a hospital record over HL7 FHIR R4, or **isolated** with its own local store when no record exists (the common case in Pakistan). It is **decision support, not a medical device**: it never diagnoses, never suggests treatment or doses, never changes a medicine, and never ends a possible emergency with reassurance.

**Design motto: the model proposes, the rules decide.**

### A2. The problem

- **Visits are episodic.** Patients with chronic disease see a doctor every few months. Between visits they forget medicines, ignore early symptoms and don't know when a reading is dangerous. A bad week of blood pressure, or the missed dose behind a symptom, is simply lost; at the next visit the doctor starts from zero.
- **Adherence is poor.** The WHO reports that only about **50%** of people with chronic disease follow their treatment correctly.
- **Pakistan-specific barriers.** A 2025 cross-sectional study of **600** diabetes patients across Pakistan found **65%** were aware of digital health technology but only **58%** had used any; **60%** said they could not afford it; only **36.1%** had health insurance. The devices people actually own are basic glucometers and insulin pens, not connected devices. Other barriers: data cost, weak internet, cultural resistance.
- **Scale in Pakistan.** The IDF Diabetes Atlas (11th edition, 2025) reports about **30.8%** of Pakistani adults with diabetes, roughly **36 million** people.
- **No shared record.** Most clinics have no central EHR, so a tool that only works with a hospital record would miss most patients.
- **Language.** Many patients are more comfortable in Urdu or Roman Urdu than English.
- **Records disagree.** Where a record exists, what the patient says often differs from what is on file (a stopped medicine, a new reading), and nothing flags the difference.

**Key question the project answers:** can a standards-aligned system, built from open technologies and synthetic/public data, ask the right follow-up questions, catch danger signs without ever treating a missing answer as safe, compare self-report with a record while being honest about which source is more trustworthy, and hand a clear, explainable case to a clinician — all without diagnosing?

### A3. Who it is for

| Stakeholder | Who | What they need |
|---|---|---|
| Primary | Adult patients with type 2 diabetes and/or hypertension (and caregivers answering for them) | A quick, low-cost daily check-in in their language, with no special device; clear guidance when something is dangerous |
| Secondary | Doctors and clinic staff | One queue showing who needs attention first, with reasons in plain words and the source of every number |
| Tertiary | Clinics and the wider health system | Structured between-visit data, fewer missed deteriorations, a path that works with or without an EHR |

**System roles:** `patient` (default), `provider`, `admin`.

**Inclusion:** adults (18+), not pregnant, with type 2 diabetes and/or hypertension. **Out of scope:** children, pregnancy (different BP limits), people who cannot answer for themselves (a caregiver can answer, and this is recorded), any emergency use instead of calling emergency services, kidney disease / heart failure targets.

### A4. What it is NOT

- Not a diagnostic tool, not a treatment or dosing advisor, not a medical device, not certified or "clinically validated".
- Not a replacement for emergency services: the emergency screen tells the patient to call their local emergency number (1122 in Pakistan).
- Not a wearable/device platform: everything works from conversational self-report.
- Not an LLM chatbot: no LLM decides anything. The Groq chat assist in the code is **off in production**.

### A5. Market and research gap

| System | Chronic monitoring | ML risk scoring | Explainable output | FHIR | Works without a device |
|---|---|---|---|---|---|
| Glooko (closest competitor; 3M+ users, 30+ countries) | Yes | Partial | No | Yes | No (needs one of 200+ meters/CGMs/pumps) |
| mySugr | Yes | No | No | No | Yes |
| MyChart (Epic) | No | No | No | Yes | Yes |
| Sehat Kahani (Pakistan, video consults) | No | No | No | No | Yes |
| Marham (Pakistan, doctor booking/consults) | No | No | No | No | Yes |
| **ChronicCare AI** | Yes | Yes (planned) | Yes (planned) | Yes | Yes |

The proposal reviewed 15 systems. **The gap:** no system combines (a) FHIR retrieval that treats the EHR as the authority instead of copying it, (b) an EHR-independent local store for places with no record, (c) a clinically structured interview with immediate red-flag screening, (d) condition-specific, explainable risk models with explicit confidence, (e) trend analysis across check-ins, and (f) a dedicated **Verification** step that checks every other component's output before a human sees it. The Verification step is the most distinct engineering contribution; the combination is what is new.

### A6. Objectives (from the proposal) and status today

| # | Objective | Status on 24 Oct 2026 |
|---|---|---|
| 1 | Multi-agent, dual-mode reconciliation pipeline with a clinically structured adaptive interview; never Red from one unqualified symptom; conflicts flagged, never silently overwritten | **Delivered** in deterministic form (interview v2.3, protocols, reconciliation) |
| 2 | Two explainable risk classifiers (diabetes, hypertension) with SHAP | **Iteration 2** — only a weak baseline exists |
| 3 | A Verification step that checks all output against explicit ground truth | **Delivered** for reconciliation (trust + severity); grounding checks for model/RAG output are **Iteration 2** |
| 4 | Plain-language explanations in English and Urdu | Bilingual UI and danger phrases done; generated explanations (RAG) **Iteration 2** |
| 5 | Multi-tier validation: scenarios, single-LLM baseline, volunteer pilot | Scenarios, personas, mutation proofs, smoke tests done; baselines and pilot **FYP-2** |

### A7. Contributions (what we claim as new)

1. **Dual-mode design with one pipeline:** the same reasoning code runs on a FHIR record or a local store, with the mode decided by data availability, never by nationality or region.
2. **Trust-aware, source-blind reconciliation:** conflicts are flagged with each source's trust level, never resolved by picking a winner.
3. **A Verification step** that rates every comparison (and later every model and RAG output) and forces human review when severity is moderate or high.
4. **Falsifiable safety evidence:** mutation proofs (23 deliberate rule breaks, all caught) plus an independent phrase test by teammates who never saw the detector's list. (This framing of contribution 4 still needs confirming with Dr. Basharat.)
5. **A monotonic, fail-closed triage** where unknown answers raise the level and nothing downstream can lower it.

### A8. Complex Computing Problem (CCP) — the one-line framing

**Trust-aware, verified reasoning over conflicting, incomplete and differently sourced clinical data, under real deployment constraints.**

| CCP attribute | Evidence in the project |
|---|---|
| Depth of knowledge | Clinical protocols (ACC/AHA, ADA), FHIR R4 + LOINC/SNOMED mapping, unit safety, concurrency, cloud deployment, bilingual NLP rules |
| Conflicting requirements | Fast emergency escalation vs not alarming on one number; self-report vs EHR; privacy vs clinician usefulness; free-tier hosting vs safety-critical behaviour |
| Depth of analysis | No component's output is trusted directly; verification applies trust and severity; mutation proofs show each safety rule is guarded |
| Unfamiliar issues | Negation ("no chest pain"), unit ambiguity (a bare 45), missing readings, contradictory answers — none has a textbook recipe |
| Standards | FHIR R4, SMART on FHIR, ACC/AHA and ADA thresholds, HIPAA-inspired privacy, JWT/RS256 |
| Stakeholders | Patient, provider, admin, supervisors, clinician reviewers — needs differ and compete |
| Consequences | A wrong level or a silently overwritten conflict is a patient-safety risk, so the design fails closed |
| Interdependence | Interview, triage, medication check, reconciliation, verification, storage and UI share one session state and one data interface |

**Stream B** (real-world problem, research-informed, independently evaluated). **SDG 3**, targets 3.4 (premature NCD mortality) and 3.8 (access to essential care).

### A9. Constraints

- **Cost:** free tiers only (Firebase Spark, Render free, Aiven free MySQL, Netlify, Groq free). Free tiers sleep, so the backend has a **13–60 s cold start**.
- **Data:** no real patient data. Synthetic FHIR (SMART sandbox, Synthea, FhirSim) and public datasets only.
- **Clinical content:** commercial triage protocols (Schmitt-Thompson) cannot be copied; our questions are written in our own words from public guidelines and reviewed by doctors.
- **Time:** two semesters (FYP-1, FYP-2); three people who also have courses and internships.
- **Regulation:** awareness only (Pakistan PECA 2016, US FDA non-device CDS guidance). No compliance is claimed.

### A10. Research questions (from the paper)

- **RQ1** — Can two classifiers predict diabetes and hypertension risk with useful precision/recall and calibration, and do their SHAP reasons match clinical knowledge?
- **RQ2** — Does the Verification step itself reduce unsupported or inconsistent output? (Ablation: full pipeline vs pipeline without Verification.)
- **RQ3** — Does the interview + triage detect emergencies with high sensitivity and a low rate of inappropriate escalation, compared with a rule-only baseline, an ML-only baseline and a single-LLM baseline?
- **RQ4** — Are the High/Medium/Low confidence labels calibrated (accuracy falls from High to Low)?

---

## Part B — The finished system (target design for the end of FYP-2)

> Everything in Part B is the **design**. Part C says what is actually built. Items marked *(planned)* do not exist in code yet.

### B1. Architecture at a glance

```
                       ┌──────────────────────── INTERFACES ─────────────────────────┐
                       │ Patient app (primary)   Provider dashboard   Admin dashboard │
                       │ English + Urdu, text + voice                                 │
                       └───────────────▲──────────────────────────────▲───────────────┘
                                       │ HTTPS + Firebase ID token    │
                       ┌───────────────┴──────────────────────────────┴───────────────┐
                       │ FastAPI gateway: token check, role guard, CORS, validation    │
                       └───────────────▲──────────────────────────────────────────────┘
                                       │
   ┌───────────────────────────────────┴──────────────────────────────────────────────┐
   │ ORCHESTRATOR (LangGraph, planned): one shared state per check-in, conditional     │
   │ routing, scoped inputs per step, loop-backs                                       │
   │                                                                                   │
   │  Stage 1 red-flag screen ──(danger)──► EMERGENCY: save + alert, skip the rest     │
   │        │ (safe)                                                                   │
   │        ▼                                                                          │
   │  Adaptive interview ─► confirmation protocols ─► medication confirmation          │
   │        ▼                                                                          │
   │  Record retrieval (FHIR or Local Store) ─► Reconciliation ─► Verification         │
   │        ▼                                                                          │
   │  Trend agent (planned) ─► Risk models + SHAP (planned) ─► Guideline RAG (planned) │
   │        ▼                                                                          │
   │  Verification grounding checks (planned) ─► Explanation EN/UR (planned)           │
   │        ▼                                                                          │
   │  Final triage (monotonic merge) ─► SOAP note (planned) ─► review queue            │
   │        ▼                                                                          │
   │  Appointment + notification + escalation timeout (planned, FYP-2)                 │
   └───────────────────────────────────▲──────────────────────────────────────────────┘
                                       │ one DataSource interface
   ┌───────────────────────────────────┴──────────────────────────────────────────────┐
   │ DATA: FHIR adapter (SMART sandbox / FhirSim) │ Local Store │ App DB (MySQL/SQLite) │
   │ External: Firebase Auth, Groq Whisper, (planned) vector store, OCR, FCM           │
   └──────────────────────────────────────────────────────────────────────────────────┘
```

### B2. Components (agents and services)

The proposal names 10 reasoning agents, 7 deterministic services and 3 interfaces. Supervisor feedback: the ML classifiers are framed as **tools used inside the deterministic services**, not independent reasoning agents.

| Component | Job | State | Owner |
|---|---|---|---|
| Stage 1 red-flag screen | Danger phrases + BP crisis on every answer; emergency bypass | **Built** | Usman |
| Adaptive interview | Condition-specific questions, missing-data checkpoint, dual diagnosis | **Built** (v2.3 live, v3 flagged); upgrades Iteration 2 | Hassaan builds, Usman specs |
| Confirmation protocols | 5 protocols that confirm a dangerous reading through questions | **Built** | Usman |
| Medication confirmation | Asks about each active medicine | **Built** | Usman |
| Record retrieval | FHIR read (connected) or Local Store (isolated) behind one interface | **Built** | Usman |
| Reconciliation | Source-blind comparison of report vs record | **Built** | Usman |
| Verification | Trust levels, severity, human-review decision; later grounding checks on model/RAG output against 3 ground truths: the patient record, the benchmark table, the retrieved guideline | **Built** (reconciliation part); grounding **Iteration 2** | Usman |
| Trend agent | Direction of each reading over recent check-ins, "not enough history" rule | Iteration 2 | Saad |
| Diabetes risk model + SHAP | Advisory risk + top reasons | Iteration 2 | Usman (Saad helps) |
| Hypertension risk model + SHAP | Advisory risk + top reasons | Iteration 2 | Usman (Saad helps) |
| Guideline RAG | Retrieve guideline passages for the case | Iteration 2 | Usman |
| Explanation layer | Plain-language "why this result" in English and Urdu with citations | Iteration 2 | Usman |
| LangGraph orchestrator | Runs the steps as a graph over one shared state | Iteration 2 | Usman |
| Final triage | Monotonic merge of all levels into one result | **Built** (deterministic merge) | Usman |
| SOAP note | Structured clinical note for the provider | FYP-2 | — |
| OCR pipeline | Read prescriptions and lab reports into the Local Store | Iteration 2 | Hassaan (Saad tests) |
| Appointment service | Book/skip by level and specialty, synthetic provider directory | FYP-2 (UI mock exists) | — |
| Notification service | Daily reminder, escalation alerts (FCM) | FYP-2 | — |
| Escalation timeout | Unacknowledged Red re-notified at 2 h, flagged to a second provider/admin at 24 h | FYP-2 | — |
| Audit logging | Append-only, zero-PHI | **Built** | Usman |
| Auth | Firebase sign-in, server-side verification, DB roles | **Built** | Usman |

### B3. A check-in in the finished system (step by step)

1. **Start.** Patient opens the app (reminder in FYP-2), taps check-in. Server checks sign-in, both consents, inclusion, profile; creates a session.
2. **Intake.** Patient types or speaks (Whisper STT). Every answer first goes through the **Stage 1 red-flag screen** (danger phrases in EN / Urdu / Roman Urdu, negation-aware; BP ≥ 180/120). Danger → the emergency result is saved in the same request, the provider queue gets it at the top, the patient sees "call your local emergency number now", and the rest of the pipeline is skipped.
3. **Interview.** Condition-specific questions; dual diagnosis asks both; a missing reading gets one clarifying question, then a **Low confidence** tag; unclear answers asked once, then `unknown`.
4. **Protocols.** A dangerous or changed reading starts its confirmation protocol (re-measure, warning symptoms, substances, circumstances). Only the answers decide the level.
5. **Medicines.** Each active medicine (connected mode: up to 8 diabetes/BP drugs) is confirmed: stopped / same / different dose / unclear.
6. **Record + reconciliation.** The record (FHIR or Local Store) and today's answers are normalised to one shape and compared; conflicts and missing sides are flagged, nothing is overwritten.
7. **Verification.** Each comparison gets a trust level per source and a severity; moderate or high forces human review.
8. **Trend** *(planned)*: direction of glucose, BP and adherence over recent check-ins, or "not enough history" (fewer than 3).
9. **Risk models** *(planned)*: advisory diabetes and hypertension risk with SHAP reasons and a confidence label. Can only raise the level.
10. **Guideline RAG + explanation** *(planned)*: retrieve the relevant guideline passages; write 2–3 plain sentences in English or Urdu, each citing its source.
11. **Verification grounding** *(planned)*: every number and claim in the explanation is checked against the record, the benchmark table and the retrieved passage; on mismatch the explanation is dropped, never the safety result.
12. **Final triage.** All levels merge monotonically (highest wins). Patient sees the level text, what was compared, the risk card and the explanation.
13. **Clinician.** Review queue ordered emergency → urgent → review; detail view with both sources, trust, reasons, model card, trace, SOAP note *(FYP-2)*; actions acknowledge / resolve / escalate with a note.
14. **Follow-up** *(FYP-2)*: appointment offered by level and specialty; escalation timeout for unacknowledged Red cases.

### B4. The two modes — and why there are two

- **Connected mode:** the patient links one record in a registered EHR system. The record is read over FHIR R4 at every check-in and **never copied**; the EHR stays the authority. Local record edits are refused (`409 record_managed_by_ehr`).
- **Isolated mode:** no EHR. The patient keeps their own record (medicines, allergies, conditions, baseline readings; soon OCR uploads), every value tagged with its source.
- **Mode is decided by the server from data availability** (is there an active EHR link?), never by the client, nationality or region. Disconnecting returns the patient to isolated mode.
- **Why two modes (the hardest panel question):** a single connected-only design excludes most Pakistani patients (no central EHR); a single local-only design ignores the better data when a hospital record exists and would duplicate it and let it go stale. Two modes behind **one DataSource interface** mean one reasoning pipeline, and the trust levels tell the clinician how much to rely on each value. Answer with data availability and trust, not "EHR API convenience".

### B5. Trust and confidence

| Source | Trust |
|---|---|
| FHIR record, or clinician-entered | High |
| Patient upload / OCR (confirmed by the patient) | Medium |
| Patient self-report in the check-in | Low |

- Two low-trust sources agreeing still needs review.
- A missing side backed by a high-trust present side is low severity; by medium/low trust it is moderate and needs review.
- Every result carries a **confidence label** (High / Medium / Low) based on data completeness and source trust, separate from any model probability.

### B6. Levels: proposal vs built

The proposal used Green / Yellow / Red. The built system uses four levels, which map as follows:

| Built level | Proposal colour | Shown to patient | Who is told |
|---|---|---|---|
| emergency | Red (Stage 1 bypass) | "Call your local emergency number now. Your care team is being alerted." | Provider immediately, saved by the request that decides it |
| urgent | Red | "Please contact your clinician today. If you feel worse, call your local emergency number." | Top of the queue after emergencies |
| review | Yellow | "A clinician will review this. Please measure again later today and at the same time tomorrow." | Normal review queue |
| routine | Green | (nothing) | Nobody |

### B7. Orchestration with LangGraph (planned design)

- **One shared state object** per check-in (answers, readings, record bundle, reconciliation, verification, trend, risk, retrieved passages, explanation, level, trace).
- **Conditional routing:** the red-flag screen is a gate (danger → straight to the emergency path); the diabetes model runs only if diabetes is on record, the hypertension model only if hypertension is.
- **Scoped inputs:** each node gets only what it needs (the RAG node gets the condition, risk and trend, not the raw transcript).
- **Loop-backs:** verification can send a failed explanation back once, then drops it.
- **Trace:** every node's input summary and output is recorded and shown to the clinician as "How this was decided".
- **Hard requirement:** wrapping the existing pipeline in LangGraph must not change any output. Proof = the 52 personas and 7 POC scenarios give identical results before and after (an equivalence test like `test_engine_equivalence.py`).

### B8. Risk models (planned design, Iteration 2)

- **Two levels per disease.** *Basic* model: age, sex, BMI, waist, smoking, family history (works for every patient on day 1). *Full* model: adds blood pressure and lab values when the patient has them.
- **Leakage rule:** a model never takes the measurement that defines its own label (no HbA1c input to a model whose label is HbA1c ≥ 6.5%).
- **Data:** NHANES 1999–2023 is the main training set (measured labels); BRFSS for the basic models; Framingham, cardio 70k and the Kaggle BRFSS 2015 for benchmarks; DHS India/Bangladesh/Nepal for South Asian external validation when approved. MIMIC-IV is used for trend testing, not risk training.
- **Split:** by time where possible (NHANES train 1999–2016, test 2017–2023), never random rows of the same person.
- **Metrics:** AUROC, sensitivity and specificity at a threshold chosen for sensitivity ≥ 80%, precision/recall/F1, calibration (reliability diagram, Brier score), 95% bootstrap confidence intervals. Compare against Saad's baseline (AUROC 0.75, sensitivity 3.55%).
- **SHAP:** top 3 reasons per prediction in plain words; sanity-check that the top features match clinical knowledge.
- **In the app:** a risk card (low / moderate / high, top reasons, "advisory, not a diagnosis"), and in the clinician view the probability, model version and whether it raised the level.
- **Safety:** the model output can raise a level (for example routine → review) and never lower one.

### B9. Guideline RAG (planned design, Iteration 2)

- **Corpus, in priority order:** (1) our doctor-signed rules (`CLINICAL_RULES.md`); (2) ADA Standards of Care in Diabetes 2026 and the 2025 AHA/ACC High Blood Pressure Guideline; (3) WHO 2021 hypertension treatment guideline and ISH 2020 global guidelines; (4) IDF-DAR Diabetes and Ramadan 2021, the 2023 Pakistan hypertension guideline (women), the AKU adaptation of ADA for Pakistan. The IDF Atlas is context for the report only.
- **Storage:** PDFs in `dataset/guidelines/` (not in Git); a manifest `docs/GUIDELINE_CORPUS.md` with title, edition, URL, download date, file hash, terms of use.
- **Retrieval:** chunk by section, embed (sentence-transformers / BGE), store in ChromaDB, retrieve with condition and topic filters.
- **Output:** 2–3 sentences in English or Urdu; every sentence cites source, section and edition; no advice beyond the level text; no new numbers that are not in the retrieved text or the record.
- **Grounding check:** Verification compares every number and claim with the retrieved text and the record; mismatch → explanation dropped.
- **Evaluation:** a retrieval test set (question → expected passage), and faithfulness / answer relevance (RAGAS-style) on reviewed reference explanations.

### B10. Interfaces at the end

- **Patient app (primary):** onboarding (sign-up, two consents, inclusion, profile, EHR connect or own record), daily check-in (text/voice, EN/UR), result (level text, what was compared, risk card, explanation), record (with provenance badges, OCR uploads, edit history), trends, appointments.
- **Provider dashboard:** review queue, patient detail (both sources, trust, reasons, model card, trace, trend charts, SOAP note), actions with notes, appointment scheduling.
- **Admin dashboard:** users and roles, append-only audit log, configuration status, (planned) guideline document management.

---

## Part C — What exists today, in detail

### C1. Live system

| Part | Where | Notes |
|---|---|---|
| Frontend | https://chronicare-ai.netlify.app | Static Next.js export, auto-deploys from `main` |
| Backend | https://chroniccare-backend-w568.onrender.com — health at `/api/health` | Render free tier, **cold start 13–60 s** |
| Database | Aiven managed MySQL (prod, TLS + CA cert); SQLite locally and in CI | Schema version **12** |
| Sign-in | Firebase Authentication, project `chroniccare-2b146` | Server verifies tokens |
| Voice | Groq Whisper (`whisper-large-v3-turbo`) | Needs `GROQ_API_KEY` on Render; otherwise mic says "not configured" |
| FHIR | `demo-hospital` (in-process FhirSim, `sim://demo`) and `public-sandbox` (SMART Health IT `https://r4.smarthealthit.org`) | Public sandbox data is from 2020–2021 and has returned HTTP 502 at times |

Smoke test (5 checks, last result 5/5): backend health, protected route closed (401), sign-in configured, CORS allows the frontend, frontend served.

### C2. Tech stack (exact versions in the repo)

**Frontend** (`package.json`): Next.js ^14.2.15 (App Router, `output: 'export'` → static `out/`, images unoptimized), React ^18.3.1, TypeScript ^5.6.3, Tailwind ^3.4.14, Recharts ^3.10.1, framer-motion ^11, lucide-react, Firebase JS SDK ^12.19.0. Tests: Vitest ^1.6.1, Testing Library, jsdom. Lint: `next lint` (ESLint 8). Node 18 in CI, Node 20 on Netlify.

**Backend** (`backend-poc-technical/requirements.txt`): Python 3.11, FastAPI 0.142.2, Uvicorn 0.54.0, Pydantic v2, PyMySQL 1.2.3, PyJWT[crypto] 2.15.1 + cryptography 50.0.2, groq 1.7.0, httpx 0.28.1, requests 2.34.2, python-dotenv 1.2.4, pytest 9.1.1. **No ORM**: hand-written SQL in `app_store.py` and `local_store.py` (the README's mention of SQLAlchemy is wrong). Ruff (correctness rules) in CI.

**ML** (separate `backend-poc-technical/ml/requirements.txt`): pandas, scikit-learn, shap. Not installed with the backend.

**Not in the code yet:** LangGraph, ChromaDB, sentence-transformers, any OCR library, Coqui TTS, FCM.

### C3. Repository map (real paths; the README tree is partly stale)

```
ChronicCare-AI/
├── app/                                    Next.js frontend
│   ├── page.tsx                            Screen router: renders the screen named in AppContext.screen
│   ├── layout.tsx, not-found.tsx, globals.css
│   ├── context/AppContext.tsx              Global state: user, profile, language, screen, isLiveMode, liveCheckinResult …
│   ├── lib/api.ts                          Typed client for all endpoints; ApiError; 409 handling
│   ├── lib/firebase.ts                     Firebase init and sign-in
│   ├── lib/roles.ts                        Role guards per portal
│   ├── lib/connection.ts                   ConnectionMode "fhir" | "offline"; managed-record checks
│   ├── lib/conditions.ts                   Diabetes / hypertension helpers
│   ├── lib/presentation.ts                 Formatting, age, unit conversions
│   ├── lib/useVoiceRecorder.ts             Microphone recording for voice check-ins
│   ├── translations/index.ts               English + Urdu strings
│   └── components/
│       ├── PortalLandingScreen, LoginScreen, ConsentScreen, InclusionScreen, HealthProfileScreen,
│       │   ConnectionScreen, HomeScreen, CheckInEntryScreen, AdaptiveInterviewScreen, ProcessingScreen,
│       │   RiskResultScreen, ConflictScreen, RoutedToReviewScreen, EmergencyScreen, ConfirmationScreen,
│       │   HealthRecordScreen, TrendScreen, PatientAppointmentsScreen
│       ├── Header, DemoFooter, ErrorBoundary, EvaluatorTourModal, FhirSourceBadge, Preloader,
│       │   RiskBadge, UnifiedSettingsModal
│       ├── provider/ ProviderLoginScreen, ProviderDashboardScreen, ReviewQueueScreen,
│       │   PatientDetailScreen, ReconciliationAlertDetail, AppointmentSchedulingScreen
│       └── admin/ AdminLoginScreen, AdminDashboardScreen
├── tests/                                  Vitest suites (auth-session, blocked-action, demo-readiness,
│                                           ehr-connection-parity, honest-labels, hypertension-parity,
│                                           medication-flow, medication-result, new-user-journey,
│                                           no-fake-values, onboarding-conditions, pregnancy-eligibility,
│                                           presentation, profile-units, richer-enrolment, scroll-behavior,
│                                           ux-logout-eye, voice-checkin-entry, voice-input)
├── backend-poc-technical/
│   ├── main.py                             FastAPI app: 36 endpoints, Pydantic models, check-in pipeline (~4,100 lines)
│   ├── init_local_db.py                    Create/migrate local SQLite
│   ├── .env.example                        Env template
│   ├── conftest.py, pytest.ini             Test config
│   ├── agents/
│   │   ├── adaptive_interview_agent.py     Interview v2.3 + red-flag patterns, negation, units (~990 lines)
│   │   ├── interview_planner.py            v3 planner (budget 8, up to 12 when concerning)
│   │   ├── interview_v3_runner.py          v3 turn runner (INTERVIEW_ENGINE=v3)
│   │   ├── interview_findings.py           v3 structured findings
│   │   ├── interview_bank/                 v3 bank: core, diabetes, hypertension, insulin_or_sulfonylurea,
│   │   │                                   fasting, sick_day, access_barriers, caregiver, wellbeing
│   │   │                                   (37 questions) + probes.json (16 symptom probe sets) +
│   │   │                                   responses.json (odd input: chitchat, abuse, gibberish…) +
│   │   │                                   SOURCES.json + loader.py
│   │   ├── input_triage.py                 v3 Stage 1 red-flag screen (EN, Urdu script, Roman Urdu)
│   │   ├── answer_validation.py            Number/unit parsing, ranges, mmol/L handling
│   │   ├── triage_protocol.py              5 protocols, levels, baseline, stroke extras (~730 lines)
│   │   ├── medication_confirmation.py      Per-medicine confirmation
│   │   ├── reconciliation_agent.py         Source-blind comparison
│   │   └── verification_agent.py           Trust, severity, review flag
│   ├── data_sources/
│   │   ├── data_source.py                  Abstract interface
│   │   ├── fhir_client.py                  FHIR REST client (30 s in-memory cache)
│   │   ├── fhir_adapter.py                 FHIR → internal bundle
│   │   ├── fhir_sim.py                     In-process FHIR simulator
│   │   ├── medication_scope.py             Connected-mode medicine filter (max 8)
│   │   ├── local_adapter.py, local_store.py  Isolated-mode store
│   │   ├── app_store.py                    App DB: users, profiles, check-ins, results, reviews, audit (~2,000 lines)
│   │   ├── db_config.py                    sqlite / mysql switch
│   │   ├── validation.py, models.py
│   ├── auth/firebase_verify.py             RS256 token verification
│   ├── llm/groq_client.py                  Groq client (STT used; chat assist off in prod)
│   ├── ml/                                 Baseline: load_data.py, train_baseline.py, explain.py, README.md, requirements.txt
│   ├── scenarios/                          7 POC scenarios: fixtures.py, run_all_scenarios.py, test_reconciliation.py,
│   │                                       test_verification.py, test_source_blind*.py, fixtures_recorded/
│   ├── test_*.py                           52 backend test files (+ 7 in agents/ and scenarios/)
│   ├── POC_RESULTS.md                      "Proves / does not prove" for the POC
│   └── verify_m1.py … verify_m4.py         Old POC milestone checks
├── scripts/                                smoke_test.py, load_test_local.py, load_test_deployed.py,
│                                           verify_mutations.py, run_v3_personas.py, mysql_preflight.py,
│                                           probe_fhir.py, generate_clinician_pack.py, eval_phrase_set.py,
│                                           rule_truth_table.py, glucose_truth_table.py, …
├── docs/                                   See Part F1
├── .github/workflows/ci.yml, cd.yml
├── netlify.toml, next.config.mjs, tailwind.config.ts, tsconfig.json, postcss.config.mjs
└── README.md, DEMO_SCRIPT.md
```

### C4. Backend API (36 endpoints in `main.py`)

| Group | Method + path | Role |
|---|---|---|
| System | `GET /api/health`, `GET /api/llm/health` | public |
| Auth | `POST /api/auth/session` (verify token, register or log in, audit) | any valid token |
| | `GET /api/me` | signed in |
| Profile | `GET /api/me/profile`, `PUT /api/me/profile` | patient |
| Consent | `POST /api/me/consent` (data processing), `POST /api/me/consent/provider-notification` | patient |
| Record | `GET /api/me/record`; `PUT /api/me/record/conditions-basis`; `POST /api/me/record/medications`, `PATCH`/`DELETE /api/me/record/medications/{med_id}`; `POST /api/me/record/allergies`, `DELETE …/{allergy_id}`; `POST /api/me/record/observations`, `DELETE …/{obs_id}` | patient (refused in connected mode) |
| EHR | `GET /api/ehr/systems` (public registry); `POST /api/ehr/test`; `POST /api/ehr/connect`; `GET`/`DELETE /api/ehr/connection` | patient |
| Check-in | `POST /api/checkins/start`; `POST /api/checkins/{id}/answer`; `POST /api/checkins/{id}/complete`; `GET /api/checkins`; `GET /api/checkins/{id}` | patient |
| Provider | `GET /api/provider/review-queue?status=open|acknowledged|resolved|escalated`; `GET /api/provider/review/{id}`; `POST /api/provider/review/{id}/action` (`acknowledge`, `resolve`, `escalate` + note) | provider |
| Admin | `GET /api/admin/config-status`; `POST /api/admin/users/{id}/role`; `GET /api/admin/audit` | admin |
| Tools | `POST /api/reconcile`; `POST /api/verify`; `POST /api/voice/transcribe` | per guard |

**Check-in lifecycle**
1. `start` → creates the check-in (status, `version`, `step`), reads the record bundle, returns the first question (`question`, `step`, `version`, `mode`, `is_cold_start`, optional `why_text`, `options`). Requires both consents and inclusion (`REQUIRE_INCLUSION=true`).
2. `answer` (repeated, sends `step` + `version`) → red-flag screen and BP crisis check on every answer. Emergency → status `emergency`, `checkin_results` row (emergency, `max_severity=high`, `review_status=open`, `trigger_category`, `trigger_text` ≤ 500 chars, `trigger_reading`), audit row `emergency_escalated` with only the category; response `{complete: true, emergency: true, escalation_recorded: true}`. A dangerous reading → protocol questions. Then medication confirmation. Wrong `step` → `409 stale_step`; concurrent write → `409 concurrent_update`.
3. `complete` → reconciliation + verification, triage merge, store result (`emergency`, `intakes`, `reconciliation`, `verification`, `requires_review`, `max_severity`, `triage`, `triage_level`), `review_status` open or resolved. Idempotent: calling again returns the stored result.
4. Frontend: emergency → `EmergencyScreen` (local numbers, 1122); `requires_review` → `ConflictScreen` → `RoutedToReviewScreen`; else `RiskResultScreen`.

### C5. Clinical logic (source of truth: `docs/CLINICAL_RULES.md`)

**Protocols** — only the highest-priority one runs per check-in; ordinary readings start nothing:

| Priority | Protocol | Starts when | Questions (in order) | How it decides |
|---|---|---|---|---|
| 1 | `bp_severe` | systolic ≥ 180 or diastolic ≥ 120 | re-measure after 5 min rest; crisis symptoms (chest pain/pressure, breathing, back pain, numbness/weakness, vision, speech, severe headache, confusion); substances (cold/flu medicine, NSAIDs, steroids, stimulants, nicotine, missed BP medicine); circumstances (pain, upset, activity) | symptoms yes → emergency; else review; symptoms unknown, re-measure missing/"cannot"/unclear, or still in crisis → urgent; improved but ≥ 140/90 → review "improved after rest but still high"; normal after rest → review; substances/circumstances recorded as factors |
| 2 | `glucose_high` | glucose ≥ 250 mg/dL | DKA signs (nausea/vomiting, stomach pain, fast/deep breathing, fruity breath, very drowsy); thirst and urination; context (large meal, missed insulin/medicine, illness) | DKA signs yes → emergency; unknown → urgent; glucose ≥ 300 → urgent; else review |
| 3 | `glucose_low` | glucose < 70 mg/dL | neuro (confused, drowsy, trouble speaking/staying awake) → if yes, orientation (time, place, person); can swallow safely; autonomic symptoms; context | neuro yes + not oriented/unclear → emergency; neuro yes + oriented → review; cannot swallow → emergency; unknown → urgent; glucose < 54 → urgent; else review |
| 4 | `bp_low` | systolic < 90 or diastolic < 60 | dizzy/faint/weak/tired; medicine change, vomiting, diarrhoea, low intake; falls (age ≥ 65) | review; symptoms yes or unknown → urgent; fall today (≥ 65) → urgent |
| 5 | `bp_change` | systolic ≥ 20 above the patient's baseline (not crisis) | symptoms; substances; adherence (last 2 days); circumstances; standing dizziness (age ≥ 65) | review; rise ≥ 40 → urgent; symptoms yes/unknown → urgent; standing dizziness (≥ 65) → urgent; non-adherence recorded as a factor |

- **Baseline:** median of the patient's own readings from completed, non-emergency check-ins and entered baselines in the last **14 days**, latest **7**, needs at least **3**.
- **Stroke extras** (dizziness, blurred vision, headache): with one-sided weakness or facial droop → emergency; alone at age ≥ 65 with a heart/brain history (heart attack, stroke, TIA, IHD) or ≥ 2 of hypertension/diabetes/IHD → urgent ("Please go for an urgent CT scan today."); alone otherwise → review.
- **Danger phrases** (end the interview at any answer):

| Category | Examples | Level |
|---|---|---|
| chest_pain | chest pain/tightness/pressure, crushing chest pain, pain to left arm or jaw; "bayein bazu me dard"; سینے میں درد | emergency |
| breathing | can't breathe, struggling to breathe, gasping; سانس نہیں آ رہی | emergency |
| confusion | slurred speech, don't know where I am, disoriented; "main kahan hoon" (the bare word "confused" was removed: it triggers an orientation question instead) | emergency |
| loss_of_consciousness | fainted, passed out, blacked out; بے ہوش | emergency |
| one_sided_weakness | one side weak, can't move one side, face drooping | emergency |
| severe_headache | worst headache, thunderclap headache | emergency |
| vision_loss | sudden vision loss, can't see at all | emergency |
| unable_to_keep_fluids | can't keep anything down, vomiting nonstop; "musalsal ultiyan"; مسلسل الٹیاں | **urgent** (moved from emergency by doctor review) |

   Text is split into clauses (at punctuation, but, however, although, though, and, while). A negation (no, not, never, without, don't, didn't, haven't, isn't …) within **3 words** before a phrase cancels it; past events ("last year", "years ago") route to review. Urdu negation is handled.
- **Readings:** glucose 20–600 mg/dL; systolic 60–260, diastolic 30–160, systolic > diastolic. Several plausible numbers, negative numbers or out-of-range values count as missing → one clarifying question → Low confidence. **Units:** an explicit mmol/L (English, Roman Urdu, Urdu forms) is converted ×18.0 (6.5 mmol/L → 117 mg/dL); in v3 a bare value from 2 to 40 with no unit asks the unit once, and if still unclear the level is at least review with low-sugar safety text. Eastern Arabic and Urdu digits are normalised. A meter's "HI"/"LO" is not understood (known limitation).
- **Medication confirmation:** each active medicine (max 20; connected mode filtered first to max 8 diabetes/BP drugs, active, deduplicated, newest first). Answer read as stopped / same dose / different dose (only with a dose word or unit) / unclear (asked once, then unknown, left out of the comparison). Missed doses are not "stopped". Record says active but patient says stopped → high severity for the clinician.
- **Known gap for the doctors:** "yes" to v2.3 context questions (`hypo_events_past_week`, `sick_day_flags`, `associated_symptoms`, `foot_problems`) does not raise the level when readings are normal; only exact danger phrases escalate. Doctors must decide whether these go to review.

### C6. Adaptive interview engines

**v2.3 (live, `INTERVIEW_ENGINE=v2`)** — a fixed tree with keyword branches.
- Diabetes: greeting → glucose reading (+ v2.3 `glucose_context`: fasting / before meal / after meal / bedtime) → missing-data checkpoint (only if no usable reading) → hyperglycaemia symptoms → hypoglycaemia symptoms (only if on insulin or a sulfonylurea) → adherence → lifestyle.
- Hypertension: greeting → BP reading → missing-data checkpoint → associated symptoms → adherence → lifestyle (+ v2.3 additions such as `bp_technique`, `otc_meds_bp`, `missed_doses_reason`).
- Dual diagnosis: greeting once, diabetes branch, then hypertension branch (10–12 questions).
- v2.3 additions only add information or raise a level; they never lower one. Spec: `docs/INTERVIEW_V2_3_DESIGN.md`.

**v3 (behind the flag, `INTERVIEW_ENGINE=v3`)** — a planner over a question bank.
1. Safety screen first (`input_triage.py`, deterministic).
2. Read the answer into fields (rules first: numbers, units, Urdu digits; optional LLM only with an exact evidence quote, otherwise `unknown`).
3. Validate (range, unit, plausibility, contradiction with the record).
4. Planner picks the next question by priority: safety → contradicted fields → patterns from the last 7 check-ins → barriers (cost, no device, fasting) → wellbeing. Budget **8**, up to **12** if something is concerning.
5. Fixed template wording (LLM rephrasing allowed only if a checker confirms no added numbers, advice, diagnosis or reassurance).
6. Every question offers "I don't know", "Skip", "Someone else is answering", and a one-line "why am I asked this".
- Bank: 37 questions in 9 modules + 16 symptom probe sets + fixed responses for 13 kinds of odd input (chitchat, romance, abuse, gibberish/emoji/empty, dose-advice requests, fear about prognosis, questions about the bot, reports about someone else, prompt injection, non-answers, repeated answers, wrong language, self-harm wording).
- **Persona simulation** (`docs/INTERVIEW_V3_SIM_REPORT.md`): 52 synthetic personas (caregiver, confused units, contradiction with record, cost barrier, crisis BP, DKA sick day, elderly complex, fasting, hidden danger, mixed language, negated danger, no device, pregnancy exit, prompt injection, low mood …): average 7.71 questions per check-in, 2 emergency exits and 1 pregnancy exit, works 100% with the LLM off.
- **Equivalence:** `test_engine_equivalence.py` checks v2 and v3 agree where they must.
- Spec: `docs/INTERVIEW_V3_RESEARCH_AND_DESIGN.md`. Question texts: `docs/INTERVIEW_QUESTION_BANK.md`.

**Known interview gaps (Iteration 2):** dual-diagnosis question order, more follow-ups, better handling of unclear answers, more Urdu; Saad's independent phrase test found only **6 of 15** danger phrases (the developer set scores 83/83 danger and 56/56 safe), so the phrase list must widen.

### C7. Data layer

**Mode** is derived on the server (active EHR link → connected, else isolated); clients never send it. One account links one external record; one external ID links one account (409 on collision). FHIR base URLs come only from the `ehr_systems` registry (SSRF prevention). External IDs are masked to the last 4 characters in the audit log.

**Connected mode**
- `fhir_client.py` reads `Patient`, `Condition`, `Observation`, `MedicationRequest` (30 s in-memory cache); `fhir_adapter.py` normalises. LOINC used: 4548-4 HbA1c, 2339-0 glucose, 8480-6 systolic, 8462-4 diastolic, 55284-4 BP panel; glucose conversion 18.016 in the EHR doc. `Practitioner`, `Encounter` and `AllergyIntolerance` are **not read yet** (needed to show the patient's doctor).
- Systems: `demo-hospital` (FhirSim, deterministic archetypes with relative timestamps) and `public-sandbox` (SMART Health IT R4).
- Known sandbox patients (from `docs/EHR_SANDBOX.md`): `768be7ac-743f-4c24-aa0f-fed5a3a38b6a` (POC patient: 50 observations incl. glucose and HbA1c, 42 medication requests, 6 conditions), `d48ac962-78c6-46cf-ba33-a24771bfa0e4`, `b85d7e00-3690-4e2a-87a0-f3d2dfc908b3`, `4551370c-c3eb-4164-a2ff-b528f73a4e0f`. Their data is from 2020–2021, so nothing falls within the 48-hour comparison window — that is why FhirSim exists.
- Local record edits in connected mode → `409 record_managed_by_ehr`.

**Isolated mode** — `local_store.py`: `patients`, `observations` (id, patient_id, type, value, unit, timestamp, source, origin), `medications` (id, patient_id, medication_name, status, dosage, timestamp, source, origin). Patients manage medicines, allergies, conditions basis and baseline readings via `/api/me/record/*`, tagged self-reported. **Not built:** OCR, edit history, import/export.

**App database** — `app_store.py`, schema **v12**: `schema_version`, `users`, `audit_log`, `patient_profiles`, `ehr_systems`, `ehr_connections`, `checkins`, `checkin_results`, `review_actions`, `allergies`. Both SQLite and MySQL DDL live in the file; migrations are idempotent and tested (`test_schema_v10_to_v11.py`, `test_schema_v11_to_v12.py`). Fields: `docs/DATA_DICTIONARY.md`.

### C8. Reconciliation and verification

**Reconciliation** (`reconciliation_agent.py`, `reconcile_bundles(bundle_a, bundle_b)`): normalise both bundles; match observations one-to-one by nearest timestamp within **48 hours**; check unit compatibility; a difference above the threshold is a `conflict`; an absent side is `missing_in_a` / `missing_in_b`; too little data is `insufficient_data`; medicines compared by status and dosage. It never picks a winner.

**Verification** (`verification_agent.py`):

| Reconciliation status | Rule | Severity | Human review |
|---|---|---|---|
| agree | at least one side not low trust | none | no |
| agree | both sides low trust | low | yes ("agreement only between low-trust sources") |
| conflict (observation) | difference ≤ 2× threshold | moderate | yes |
| conflict (observation) | difference > 2× threshold | high | yes |
| conflict (medication) | active vs stopped | high | yes |
| conflict (medication) | other status or dose | moderate | yes |
| missing one side | present side high trust | low | no (auto-resolved) |
| missing one side | present side medium/low trust | moderate | yes |
| insufficient data | — | per table in code | per table in code |

Any moderate or high severity forces review. Neither step makes a clinical decision. **The 7 POC scenarios** (1, 2, 3A, 3B, 4A, 4B, adversarial C1) all pass and are byte-identical across runs (`scenarios/`, `POC_RESULTS.md`).

### C9. Auth, consent and onboarding

- Firebase sign-in on the client; the backend verifies the ID token itself (RS256, key id, audience = `FIREBASE_PROJECT_ID`, issuer `https://securetoken.google.com/<project>`, expiry), caching Google's public keys.
- Roles live only in the `users` table: `patient` (default), `provider`, `admin`; enforced with `require_role(...)`; admin cannot change their own role. `DEMO_ROLE_MAP` (`email:role,email:role`) gives roles to demo accounts on first sign-in.
- Portals check the role: a patient signing in to the provider portal is signed out with "Access denied".
- **Two consents:** data processing, and clinician notification. Revoking stops new check-ins (403) but keeps earlier escalations and audit rows.
- **Inclusion:** adult (18–120 valid date of birth) and not pregnant, confirmed before the first check-in.
- **Profile:** conditions (diabetes and/or hypertension, chosen independently), height (cm or ft+in), weight (kg or lb), background (for BMI and risk factors).

### C10. Provider and admin

- **Review queue:** ordered by level (emergency first), filter by status `open | acknowledged | resolved | escalated`; detail shows both sources side by side, trust, severity, reasons, factors, trigger text/reading for emergencies; actions acknowledge / resolve / escalate with a note, each written to `review_actions` and the audit log.
- **Admin:** user list and role change, audit log (latest first), configuration status (which env settings are present, never their values).

### C11. Frontend notes

- `page.tsx` renders `AppContext.screen`. **Live mode** (`isLiveMode`) uses the real backend; an older **demo mode** from the proposal POC still exists (Presenter scenarios, "demo simulation" badge). In demo mode `RiskResultScreen` hardcodes a "low" `RiskBadge` — real model output must replace it in Iteration 2. In live mode the result screen shows real reconciliation, verification, medication checks and the confidence label.
- `FhirSourceBadge` shows only in connected mode; record items show provenance (EHR, Patient Reported, Derived).
- Charts: `TrendScreen` (Recharts) shows recent systolic/diastolic, pulse and glucose; it does **not** label a direction (rising/stable/falling) yet. The only pattern logic today is `detect_historical_trends()` in `agents/interview_planner.py` (v3), which spots patterns such as recurrent lows to choose questions. The real trend agent is Iteration 2 work.
- Voice: `useVoiceRecorder.ts` → `POST /api/voice/transcribe` (Groq Whisper); falls back gracefully when not configured.
- Frontend env vars (baked in at build): `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_AUTH_MODE` (`firebase` in production), `NEXT_PUBLIC_FIREBASE_API_KEY`, `_AUTH_DOMAIN`, `_PROJECT_ID`, `_STORAGE_BUCKET`, `_MESSAGING_SENDER_ID`, `_APP_ID`, optional `NEXT_PUBLIC_DEMO_PATIENT_EMAIL`, `_PROVIDER_EMAIL`, `_ADMIN_EMAIL`.

### C12. Evidence and numbers (Mid-1)

| Evidence | Result |
|---|---|
| Backend tests | 744 total, 715 in the CI list, 0 failures (re-run 16 Oct) |
| Frontend tests | 196 in 19 files |
| Mutation proofs | 23 of 23 deliberate rule breaks caught (`scripts/verify_mutations.py`) |
| Persona simulation | 52 personas, avg 7.71 questions |
| POC scenarios | 7 of 7 pass, byte-identical |
| Phrase test | developer set 83/83 danger, 56/56 safe; Saad's independent set 6/15 danger found, 14/15 safe |
| System tests | TC-01 to TC-35 and ST-01 to ST-20 on the live site (`docs/system_test_cases.md`) |
| Local load test | 1–100 simultaneous patients, 0 failures; whole check-in median 3.7 s at 50, 8.5 s at 100; slowest step p95 2.2 s at 100 |
| Deployed load | health endpoint p95 0.57 s at 50 clients |
| Smoke test | 5/5 on the live stack |
| Repository | 275 commits, PRs #1–#69 |

### C13. Doctor review

- **Dr. Shaiza Jabbar** (Medical Officer, Hearts International Hospital) and **Capt. Dr. Talha Yasin** (Army doctor) reviewed on 13 Oct 2026; changes applied: crushing/left-arm/jaw chest pain = emergency; nonstop vomiting = urgent; "confused" → orientation question; stroke-extras rule; "very old" = 65+; new symptoms and low sugar last week → review (not yet coded for every case).
- **Dr. Anam Zafar** signed a checklist on 14 Oct 2026; she marked vomiting as **emergency** (2 urgent vs 1 emergency — still open), added difficulty speaking and palpitations (palpitations not implemented).
- **Still open:** one joint written decision on vomiting; sick-day and foot-problem escalation; written sign-off from all three; whether all are happy to be named in the paper.

### C14. ML today

`backend-poc-technical/ml/` (Saad, branch `feat/s6-ml-baseline`, merged): logistic regression on age, sex and BMI predicting self-reported diabetes (`DIQ010`) from NHANES 2021–2023; 6,014 adults (845 with diabetes), 80/20 stratified split; **AUROC 0.7507, sensitivity 3.55%, specificity 99.23%** at threshold 0.5 — it misses almost every positive case. SHAP explanation for one patient (`explain.py`). **Not wired into the app.** Raw data stays in `ml/data/` (git-ignored).

### C15. Known gaps and inconsistencies (be honest about these)

- **No LangGraph orchestrator in the code**, although the paper and architecture diagram show one; the pipeline is plain Python called from `main.py`.
- **No guideline RAG**, embeddings or vector store.
- **No OCR, edit history or import/export** in isolated mode.
- **ML not wired in**; the demo-mode result screen hardcodes "low".
- **FHIR client does not read Practitioner/Encounter/AllergyIntolerance** (no doctor on the record).
- **README is partly stale:** its tree names files that don't exist (`agents/reconciliation.py` → `reconciliation_agent.py`; `agents/verification.py` → `verification_agent.py`; `agents/interview_question_bank.py` → `interview_bank/`; `auth/firebase_auth.py` → `firebase_verify.py`; `ml/baseline_model.py`, `ml/shap_explainer.py` → `train_baseline.py`, `explain.py`; several component names), and it mentions SQLAlchemy, which is not used.
- **`CLINICAL_RULES.md`** cites the ACC/AHA **2017** guideline (2025 AHA/ACC and ADA 2026 are current) and its section 7 still says "no clinician has reviewed any value", contradicting the review header.
- Commit history is mostly Usman's; teammates must commit their own work from now on.
- No commits since 16 Oct 2026.

---

## Part D — How we get there

### D1. Iterations and the overall plan

| Phase | When | Scope | Project done (estimate) |
|---|---|---|---|
| Proposal + POC | Jul – 11 Sep 2026 | Proposal (v1→v6), backend POC (7 scenarios), frontend POC, defense: approved with minor modifications | — |
| Iteration 1 (Mid-1) | to ~16 Oct 2026 | Deterministic safety core, auth, consent, EHR connect, server-side check-ins, review queue, CI/CD, deployment | ~36% |
| **Iteration 2 (FYP-1 Final)** | **19 Oct – 17 Nov 2026** | Risk models + SHAP, guideline RAG + explanations, LangGraph orchestrator, verification grounding, interview upgrade, Local Store + OCR, trend agent, EHR test patients, new screens, validation | **~65%** |
| Iterations 3–4 (FYP-2) | Spring 2027 | SOAP note, appointments, notifications, escalation timeout, full evaluation (baselines, ablation, calibration), ~20-volunteer pilot in isolated mode, final report | 100% |

Methodology: Agile/Scrum with weekly sprints, a written weekly log, and the supervisor seeing something running every week.

### D2. Iteration 2 in short (the detailed task file comes separately)

| ID | Workstream | Builds | Reviews |
|---|---|---|---|
| I2-0 | EHR test patients (8–12 sandbox patients with diabetes/HTN, a doctor, medicines, readings; Synthea fallback) | Usman | Hassaan, Saad |
| I2-1 | Risk models + SHAP | Usman (Saad: data checks, splits, baselines, evaluation) | Saad |
| I2-2 | Guideline RAG + explanations EN/UR | Usman | Saad (retrieval test set) |
| I2-3 | LangGraph orchestrator around the existing pipeline | Usman | Hassaan |
| I2-4 | Interview upgrade | Hassaan | Usman, doctor |
| I2-5 | Local Store: OCR, edit history, import/export | Hassaan | Saad tests, Usman reviews |
| I2-6 | Trend agent | Saad | Usman |
| I2-7 | New screens (risk, trend, explanation, doctor on record) | Hassaan | Usman |
| I2-8 | Bug hunt + validation (weekly bug bash, new phrase test, usability ~5 people, doctors' sign-off) | Saad + Hassaan, Usman (doctors) | All |
| I2-9 | FYP-1 Final report + demo | All | Usman |

**Gates:** Week 2 gate 1 Nov (setup done, EHR patients live, ML plan agreed, OCR tool chosen); features done 8 Nov (interview upgrade, trends, OCR + edit history merged; risk models in the app behind a flag; explanations v1); code freeze Tue 10 Nov; report + slides final 15 Nov; **FYP-1 Final Tue 17 Nov**.

**Nothing is cut for the earlier date.** The full scope stays in FYP-1; the daily workload goes up instead.

**Every workstream must end in something visible on the live site:** risk card with reasons; "Why this result?" with citations; a "How this was decided" trace for clinicians; OCR confirm-or-fix screen; trend arrows; the doctor's name on the record.

### D3. Evaluation plan (FYP-1 partly, FYP-2 fully)

| Question | Method | Metric |
|---|---|---|
| RQ1 classifiers | Held-out and external test sets (time split, BRFSS/Framingham/DHS) | AUROC, sensitivity/specificity at chosen threshold, precision/recall/F1, calibration (Brier, reliability), 95% bootstrap CI; SHAP sanity check |
| RQ2 verification | Ablation: full pipeline vs without verification, same inputs; injected-inconsistency test set | Catch rate, over-flagging rate, unsupported-recommendation rate |
| RQ3 triage | 30–50 written scenarios with clinician-adjudicated labels; baselines: rule-only, ML-only, single-LLM, no-verification | Emergency sensitivity, inappropriate-escalation rate; McNemar for paired comparisons |
| RQ4 confidence | Bin results by High/Medium/Low | Accuracy should fall from High to Low |
| RAG | Retrieval test set; reviewed reference explanations | Retrieval hit rate; faithfulness, answer relevance |
| Usability | ~5 volunteers (Iteration 2), ~20 volunteers in isolated mode (FYP-2 pilot) | ≥ 80% complete a check-in unaided after the first session; ≥ 80% say the explanation is understandable (placeholder targets, to agree with supervisors) |
| Safety | Mutation proofs, independent phrase tests, personas | All mutations caught; phrase recall on unseen sets |

### D4. Data

| Dataset | Rows | Labels | Use | State |
|---|---|---|---|---|
| NHANES 1999–2023 (11 cycles; `nhanes_core.csv` + `nhanes_full.parquet`) | 113,249 people; 67,357 adults; 59,412 with HbA1c; 60,000 with BP; 29,218 with fasting glucose | Measured | Main training set | Collected |
| BRFSS 2015/2017/2019/2021/2023 (`brfss_core.parquet`) | 2,181,756 (diabetes ~13%, high BP ~40%) | Self-reported | Basic models, pretraining | Collected |
| BRFSS 2015 Kaggle (Diabetes Health Indicators) | 253,680 (+ 70,692 balanced) | Self-reported | Benchmark vs papers | Collected |
| Cardiovascular 70k (Kaggle; `;`-separated; junk BP values to clean) | 70,000 | Measured BP | Extra hypertension training | Collected |
| Framingham (Kaggle) | 4,238 | Measured | Hypertension benchmark | Collected |
| Pima | 768 | Measured | Paper benchmark only | Collected |
| MIMIC-IV 3.1 (8 hosp tables via BigQuery: patients, admissions, diagnoses_icd, d_icd_diagnoses, omr, d_labitems, HbA1c/glucose labs, diabetes/BP prescriptions) | 364,627 patients; 7.75M outpatient vitals; 4.2M lab rows | Hospital records | Trend testing | Collected — **credentialed under Saad's PhysioNet account** |
| DHS: India NFHS-5, Bangladesh 2017–18, Nepal, Pakistan (+ others in the region) | large | Measured BP + glucose (not Pakistan) | South Asian external validation | Pending approval |
| Synthea | generated | Synthetic FHIR | Test patients only | Available |

**Data rules:** the whole `dataset/` folder stays out of Git; MIMIC and DHS stay on the approved person's machine; no raw rows into any AI or cloud tool (PhysioNet's data-use agreement forbids it); never report accuracy on Synthea; the paper and report say MIMIC-III and must be changed to MIMIC-IV.

### D5. Guideline sources

| Priority | Source | Edition | Link |
|---|---|---|---|
| 1 | Our doctor-signed rules | Oct 2026 | `docs/CLINICAL_RULES.md` |
| 2 | ADA Standards of Care in Diabetes—2026 | Diabetes Care 49 (Suppl 1), Jan 2026 | https://diabetesjournals.org/care/issue/49/Supplement_1 |
| 2 | 2025 AHA/ACC High Blood Pressure Guideline (stage 1 130–139/80–89, stage 2 ≥ 140/90, stage 2 starts two drugs, PREVENT risk) | Aug 2025 | https://professional.heart.org/en/science-news/2025-high-blood-pressure-guideline |
| 3 | WHO Guideline for the pharmacological treatment of hypertension in adults | 2021 | https://www.who.int/publications-detail-redirect/9789240033986 |
| 3 | ISH Global Hypertension Practice Guidelines | 2020 | https://pubmed.ncbi.nlm.nih.gov/32370572/ |
| 4 | IDF-DAR Diabetes and Ramadan Practical Guidelines | 2021 | https://idf.org/about-diabetes/resources/diabetes-and-ramadan-practical-guidelines-2021/ |
| 4 | Pakistan Hypertension Clinical Practice Guidelines: Management of Hypertension in Women | Pakistan Heart Journal 56 (Suppl 1), 2023 | https://pakheartjournal.com/index.php/pk/article/view/2455 |
| 4 | Adult diabetes guidelines adapted for Pakistan (Aga Khan University; screening from age 30) | Frontiers in Endocrinology, 2023 | https://pmc.ncbi.nlm.nih.gov/articles/PMC9849674 |
| Context | IDF Diabetes Atlas, 11th edition (Pakistan 30.8%, ~36 million) | 2025 | https://idf.org/about-diabetes/resources/idf-diabetes-atlas-11th-edition-2025/ |

### D6. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Usman is the bottleneck (ML, RAG, LangGraph, reviews) | Reviews on fixed days; Saad takes more model evaluation; LangGraph cut to a thinner version first |
| Models stay weak | Choose the threshold for sensitivity, report honestly, keep models advisory |
| Teammates merge AI code they can't explain | Evidence-pasted PRs; each person demos their own PR at the weekly meeting |
| DHS approval slow | Report BRFSS/Framingham external validation; DHS moves to FYP-2 |
| OCR poor on Urdu/handwriting | Printed English lab reports first; patient confirms every field |
| Doctors slow to sign off | Keep the 13 Oct rules live; nothing new reaches patients without review |
| Sandbox patients lack a doctor/medicines | Synthea patients in FhirSim, labelled simulated |
| RAG text drifts from source | Grounding check drops the explanation |
| Cold start spoils a demo | Wake the API first |

---

## Part E — Engineering handbook

### E1. Local setup (Windows PowerShell)

**Backend**
```powershell
cd backend-poc-technical
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env            # defaults = local SQLite
python init_local_db.py
uvicorn main:app --reload --port 8000
# open http://127.0.0.1:8000/api/health  → {"status": "healthy", ...}
# open http://127.0.0.1:8000/docs        → interactive API docs
```

**Frontend** (repo root, second terminal)
```powershell
npm install
# optional .env.local:  NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm run dev                       # http://localhost:3000
```

If `pip` is not recognised, use `python -m pip`. If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

### E2. Backend environment variables

| Variable | Local default | Purpose |
|---|---|---|
| `APP_ENV` | empty | `production` turns on strict guards (MySQL, CORS, Firebase required) |
| `CORS_ALLOWED_ORIGINS` | localhost | Comma-separated exact origins, no wildcards, no trailing slash |
| `DB_BACKEND` | `sqlite` | `mysql` in production |
| `LOCAL_DB_PATH` | `local_store.db` | SQLite file |
| `MYSQL_URL`, `MYSQL_SSL_CA` | empty | Aiven connection + CA cert |
| `FIREBASE_PROJECT_ID` | mock | Token audience |
| `DEMO_ROLE_MAP` | empty | `email:role,email:role` |
| `FHIR_BASE_URL`, `FHIR_PATIENT_ID` | empty | Optional overrides |
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_STT_MODEL` | empty / `whisper-large-v3-turbo` | Voice (secret key only on Render) |
| `REQUIRE_INCLUSION` | true | Inclusion before first check-in |
| `INTERVIEW_ENGINE` | `v2` | `v2` or `v3`; production stays `v2` |

### E3. Tests, CI and CD

```powershell
# backend (repo root)
python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"
python -m pytest backend-poc-technical/test_triage_protocol.py -q      # one file
# frontend
npm test
npm run lint
npm run build
# safety and evidence scripts
python scripts/verify_mutations.py
python scripts/run_v3_personas.py
python scripts/smoke_test.py --backend https://chroniccare-backend-w568.onrender.com --frontend https://chronicare-ai.netlify.app --wait 300
```

**CI** (`ci.yml`, on push/PR to `dev` and `main`): Python 3.11 → Ruff (`E9,F63,F7,F82`) → init SQLite → pytest on an **explicit file list** → Node 18 → `npm ci` → lint → Vitest → grep for forbidden compliance claims in `app/` → `npm run build`. Plus an informational live-FHIR job.

**CD** (`cd.yml`): after CI succeeds on `main` (or manual run) → Render deploy hook (secret `RENDER_DEPLOY_HOOK_URL`) → smoke test against `BACKEND_URL` / `FRONTEND_URL` variables. Netlify deploys `main` itself.

### E4. Git workflow

- `main` (protected, deployed) ← `dev` (integration) ← your branch.
- Branch names: `feat/i2-<n>-<name>`, `fix/<name>`, `test/<name>`, `docs/<name>`.
- Commit under **your own name and email**, small and meaningful (`feat(ocr): read HbA1c from lab report`), at least three a week.
- Pull request into `dev`, with this description:
  ```
  ## What and why
  ## Files changed
  ## Evidence (pasted, not described)
  - test command + full output
  - screenshots (fake data)
  - any numbers claimed, with the command that produced them
  ## Safety check
  - [ ] no triage level can go down because of this change
  - [ ] new strings in English and Urdu
  - [ ] new test files added to ci.yml
  ## AI use
  - logged in docs/ai-usage/<name>.md
  ```
- CI green before review; Usman reviews, runs it, checks claims, merges. `dev` → `main` weekly after a green run.

### E5. Coding conventions

**Python**
- Clinical logic is deterministic and pure where possible; no network calls inside rule functions.
- Every clinical number is a named UPPER_CASE constant with a comment, and listed in `CLINICAL_RULES.md` section 8 (`test_clinical_rules_doc.py` checks the doc against the code).
- Never compare levels by string order; use `LEVEL_RANK` / `_raise_level()`.
- Return `unknown` (or `None`) for unclear input; never default to "no" or "normal".
- Audit log entries hold categories and IDs only, never free text or readings.
- Type hints, small functions, docstrings that say what the function decides.
- SQL must work on both SQLite and MySQL (use the placeholder helper `{ph}` pattern used in `app_store.py`).

**TypeScript / React**
- All patient text through `t.<key>` in both languages.
- Show only values the backend returned; if missing, show "not available", never a made-up number.
- Use `api.ts` for every request; handle `ApiError` and 409 the way existing screens do.
- Keep accessibility: labels on inputs, keyboard focus, readable at 200% zoom and 320 px width.

### E6. How-to recipes

**Add an interview question (v3 bank)**
1. Add it to the right module in `agents/interview_bank/*.json` with its source key from `SOURCES.json` and status "proposed".
2. English and Urdu wording; "I don't know" and "Skip" handling.
3. Decide if it only records information or can raise a level (it may never lower one).
4. Run `python scripts/run_v3_personas.py` and the interview tests; update `docs/INTERVIEW_QUESTION_BANK.md`.
5. Mark it for doctor review before it goes live.

**Add a danger phrase**
1. Add it to the right category (v2 patterns in `adaptive_interview_agent.py`, v3 in `input_triage.py`), in English, Roman Urdu and Urdu script where possible.
2. Add positive and negated tests ("I have X" escalates, "I don't have X" does not, "X last year" → review).
3. Re-run the phrase evaluation (`scripts/eval_phrase_set.py`) and the mutation proofs.
4. Update `CLINICAL_RULES.md` section 5 and ask for doctor review.

**Change a threshold or protocol**
1. Only with doctor agreement in writing. Change the named constant, not inline numbers.
2. Update `CLINICAL_RULES.md` (rules and section 8), add a boundary test (just below, at, just above), add or update a mutation proof, re-run personas.

**Add an endpoint**
1. Pydantic request/response models in `main.py`, `require_role(...)` on the route, audit entry if it changes data.
2. Add it to `app/lib/api.ts` with types.
3. Tests in a `test_*.py` file that is in the CI list; update `docs/AUTH.md` route matrix.

**Change the database**
1. Bump `LATEST_SCHEMA_VERSION` in `app_store.py` (or the local store), write an idempotent migration for SQLite and MySQL.
2. Add `test_schema_v12_to_v13.py`-style tests; update `docs/DATA_DICTIONARY.md`.
3. Run `scripts/mysql_preflight.py` before deploying.

**Add a screen**
1. Component in `app/components/`, add its name to the `screen` union in `AppContext.tsx`, render it in `page.tsx`.
2. Strings in both languages; a Vitest test; no fake values.

**Add an ML model to the app (Iteration 2)**
1. Training code and notebooks in `backend-poc-technical/ml/`, data never committed; save the model file with a version.
2. A pure `predict(features) -> {risk, probability, top_reasons, version}` function; the API returns it; the triage merge may only raise.
3. Tests: model loads, handles missing features (returns "not enough data", not a guess), never lowers a level (mutation proof).

### E7. Definition of done

Merged into `dev` · CI green · works on the live site after the weekly `main` merge · tests added (and in the CI list) · docs updated · English and Urdu · evidence pasted in the PR · AI use logged · you can explain every line.

### E8. Working with AI on this project

- Give your AI this file first, then the task prompt.
- Ask it to show the exact files it will change before changing them.
- Make it run the tests and paste the output; don't accept "should work".
- Never paste secrets, real patient data or credentialed data into it.
- Log what you used it for in `docs/ai-usage/<your-name>.md` (date, task, what it produced, what you checked or changed).

---

## Part F — Reference

### F1. Docs index (`docs/`)

| File | What it holds |
|---|---|
| `CLINICAL_RULES.md` | Rule register: levels, protocols, questions, danger phrases, every constant. Source of truth |
| `SAFETY.md` | Emergency lifecycle and guarantees |
| `AUTH.md` | Token flow, roles, route matrix |
| `DATA_DICTIONARY.md` | Every table and field (app DB + local store) |
| `DATA_OWNERSHIP.md` | EHR link rules, mode derivation, privacy, sync boundaries |
| `DEPLOY.md` | Render, Netlify, Aiven, Firebase, GitHub secrets and variables |
| `EHR_SANDBOX.md` | FHIR systems, probe results, test patients, LOINC, conversions |
| `DATASETS.md`, `SOURCES_REVIEW.md` | Candidate datasets, source checks |
| `INTERVIEW_QUESTION_BANK.md` | All question texts (EN/UR) |
| `INTERVIEW_V2_3_DESIGN.md` | v2.3 question additions and rationale |
| `INTERVIEW_V3_RESEARCH_AND_DESIGN.md` | v3 design and sources |
| `INTERVIEW_V3_SIM_REPORT.md` | 52-persona results |
| `CLINICIAN_REVIEW_PACK.md`, `CLINICIAN_RESPONSES.md`, `PERSONA_EXPECTATIONS_FOR_CLINICIAN.md` | What the doctors saw and said |
| `INDEPENDENT_PHRASE_RESULTS_saad.md`, `INTERVIEW_BANK_REVIEW_hassaan.md`, `SYSTEM_TEST_RESULTS_Hassaan.md` | Teammates' independent tests |
| `system_test_cases.md` | TC-01–35, ST-01–20 |
| `LOAD_TEST_RESULTS.md`, `ACCESSIBILITY_CHECK.md`, `LOCAL_SETUP_VERIFIED.md`, `MID1_EVIDENCE_PACK.md` | Mid-1 evidence |
| `ai-usage/hassaan.md`, `ai-usage/saad.md` | AI-usage logs |

Also: `backend-poc-technical/POC_RESULTS.md`, `backend-poc-technical/ml/README.md`, `DEMO_SCRIPT.md`.

### F2. Glossary

| Term | Meaning |
|---|---|
| Check-in | One session of readings + symptoms |
| Intake | Structured interview result for one condition |
| Protocol | Question set started by a dangerous or changed reading |
| Danger phrase / red flag | Words meaning a warning sign |
| Stage 1 / Stage 2 | Immediate red-flag screen / final triage after the full pipeline |
| Reconciliation | Comparing report vs record without choosing a winner |
| Verification | Trust + severity rating and the human-review decision; later grounding checks |
| Trust level | High (FHIR/clinician), Medium (upload/OCR), Low (self-report) |
| Confidence label | High/Medium/Low on a result, from completeness and trust |
| Connected / isolated | With an EHR over FHIR / with the local store |
| Provenance / origin | Where a value came from |
| FhirSim | Built-in fake FHIR server |
| Mutation proof | Deliberately breaking a safety rule to prove a test catches it |
| Persona | Scripted synthetic patient for end-to-end interview tests |
| Baseline (patient) | Median of the patient's own recent readings |
| SHAP | Per-prediction feature contributions |
| RAG | Retrieval-augmented generation: answer from retrieved guideline text |
| Grounding check | Verifying generated text against its sources |
| Cold start | The sleeping free-tier backend taking 13–60 s to wake |

### F3. Viva quick answers

- **Is it a chatbot?** No. The interview is deterministic; no LLM decides anything; an LLM may only rephrase or extract with an exact quote, and it's off in production.
- **Why two modes?** Data availability: most Pakistani patients have no EHR, and when one exists it should be the authority, not a stale copy. One pipeline, one interface, trust levels per source.
- **How do you measure accuracy?** Safety rules: mutation proofs, independent phrase tests, 52 personas, clinician-adjudicated scenarios. Models: AUROC, sensitivity at a chosen threshold, calibration, external validation. Explanations: faithfulness and relevance.
- **What's the benefit (faida) if it doesn't diagnose?** It closes the gap between visits: catches danger signs early, flags record mismatches (like a stopped medicine), and gives the doctor a documented trend instead of starting from zero — with no device needed.
- **Why would patients use it?** Low effort (text or voice, Urdu), no hardware cost; adoption risk is real and the pilot is the honest test.
- **What if the model is wrong?** It's advisory and can only raise a level; the rules and the clinician decide.
- **What if the patient doesn't answer?** Unknown is never "no"; unknown warning answers raise the level, and missing readings get a Low confidence tag.
- **What stops a wrong emergency on one number?** One number only starts confirmation questions; the answers decide.
