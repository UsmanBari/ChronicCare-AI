# ChronicCare AI — Week 3 (2 – 8 Nov 2026) — Saad

> **This is the only file you need this week.** It has the short refresh, the daily workflow, how your work gets checked, all 7 Antigravity prompts, who does what, and the full project handbook (Appendix A, with a new "STATE ON 2 NOV" section at its top).
> **Give the whole file to your AI first** ("read this whole file; it's the context for everything I'll ask"), then paste one day's prompt at a time.
> Save it in the repo as `docs/tasks/WEEK3_SAAD.md` (Part 1.3). Every prompt tells the agent to read it from there.

**Your focus this week:** evaluation. Last week the team built the risk agent, the guideline explainer, the orchestrator, OCR and the danger-phrase plan. This week you measure them honestly, so the FYP-1 report has real numbers: RAG retrieval quality → explanation quality (with the real LLM) → load and memory with the new pipeline → one generated "evaluation numbers" file that the report quotes → trend evaluation (+ the MIMIC sanity run you do by hand) → contract tests and coverage for the new code → the blind test of Usman's new danger-phrase detector and a release check on the live site.

**The goal:** **Sun 8 Nov is "features done".** **Tue 10 Nov is code freeze.** The FYP-1 final evaluation is **Tue 17 Nov**. Every number in the report must come from a script in the repo that anyone can re-run. Your files are the source of truth for those numbers.

**What changed since last week (read this before Day 1)**
- Schema **v15**. `ORCHESTRATOR=direct|graph` (both must behave identically). New optional fields on check-in results: `risk`, `explanation` (patient), `checkin_risk`, `explanation`, `trace` (provider). Contract: `docs/API_RISK_EXPLAIN.md`.
- Guideline chunks now load from a database table (`guideline_chunks`) when `EXPLAIN_ENABLED=true`; for local work they come from `$env:CHRONICCARE_DATA_DIR\rag\chunks.jsonl`.
- The danger-phrase harness `scripts/eval_all_phrase_sets.py` runs every phrase set through v2, v3 and a prototype. Your r2 set is in it (live v2 engine: 1/15).
- **New rules from Week 2 reviews:** never merge a PR (Usman merges); never delete branches; ML tests must pass WITHOUT `CHRONICCARE_DATA_DIR`; PR numbers only from `gh pr list` output; every number in a doc must trace to a file or command output; no recalibration on validation/test data.

**The rules that matter most** (the full list is in Appendix A, Part 0):
1. The app never diagnoses, never gives a dose or treatment advice, and never lowers a triage level. "The model proposes, the rules decide."
2. Never weaken a test to make it pass. Never hand-type a result table.
3. No secrets, no data and no real patients, anywhere: Git, chats, screenshots. **MIMIC never goes into any AI tool**; you run that script yourself.
4. Protected safety files are hashed before and after every day. You never change them.
5. "NOT DONE" and "NOT RUN" are fine answers. A false "done" is not.

**Contents**
- Part 1: Refresh (15 minutes)
- Part 2: How every day works
- Part 3: How Usman checks your work
- Part 4: The 7 daily prompts
- Appendix B: Who does what this week
- Appendix A: The full project handbook (with "STATE ON 2 NOV")

---

## Part 1 — Before Day 1: refresh (about 15 minutes)

### 1.1 Update your clone
```powershell
git status                      # must be clean
git fetch origin --prune
git switch dev
git pull
git log -1 --oneline            # the latest dev merge (#98 or newer)
```
Never commit to `dev` or `main`. Every day: a new branch and a PR into `dev`. **Don't delete old branches.**

### 1.2 Re-install
```powershell
$env:PYTHONIOENCODING = "utf-8"
cd backend-poc-technical
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r ml\requirements.txt
python init_local_db.py           # schema v15
cd ..
npm install
```
Expect about 1,470+ backend tests passing and the ML tests passing **without** `CHRONICCARE_DATA_DIR` set.

### 1.3 Put this file in the repo
Save it as `docs/tasks/WEEK3_SAAD.md`. It's committed in your Day 1 PR.

### 1.4 Files from Usman (before Day 1)
- **`rag\chunks.jsonl`**: Usman sends it. Put it at `Chronicare-data\rag\chunks.jsonl` (outside the repo). It holds the guideline chunks the retriever searches (WHO 2021, ISH 2020, IDF-DAR 2021, Pakistan HTN in Women 2023, AKU 2023: the open-licence ones; ADA 2026 and AHA/ACC 2025 are NOT in it until their licences clear). **Never commit it and never paste chunk text into a chat.**
- **Groq key (Day 2):** Usman gives you a key; it goes only into `backend-poc-technical\.env` as `GROQ_API_KEY=...`. The account has a daily token limit per model (about 200k tokens/day), so Day 2's script must count tokens and stop before the limit.

### 1.5 Things you do by hand this week (not the AI)
- **Wednesday (Day 3), by hand or in a FRESH AI chat that has never seen the repo:** write blind danger-phrase set #3 (25 danger + 25 tricky safe; English, Roman Urdu and Urdu script; the way patients and family members really type). Save it OUTSIDE the repo (`Chronicare-data\blind_set_3.json`) and tell nobody what's in it. It gets committed and run only on Day 7, after Usman's new detector is frozen. That's what makes it blind.
- **Friday (Day 5): the MIMIC trend sanity run.** In a normal PowerShell window, NOT inside Antigravity or any AI tool: `python backend-poc-technical/ml/mimic/trend_sanity.py --omr <your path to omr.csv>`. Copy ONLY the printed summary (aggregates) into the Day 5 PR description. Never a row, an id or a date.
- **Sunday (Day 7):** the release check on the live site with a fake account (ST-01..20).

---

## Part 2 — How every day works

```
Morning: fix yesterday's review comments (correction prompt from Usman) → Usman merges
         git switch dev; git pull
Day:     paste today's prompt into a NEW Antigravity chat → agent does pre-flight + plan → you type "go"
         you watch: approve plans, read diffs, stop it if it touches files outside the list
Evening: agent runs the gates, pushes, opens the PR (or gives the compare link)
         you read the diff yourself, then send Usman the PR link
Night:   Usman + Claude review → correction prompt arrives for the morning
```

**Your job while the agent works**
1. **Read its plan before typing "go".** If it lists a file that isn't in today's allowed list, say no.
2. **Watch the terminal commands.** Never approve `git push --force` to `dev`/`main`, `gh pr merge`, deleting branches, reading anything under a MIMIC folder, or printing `.env`.
3. **Check its claims yourself.** Re-run the day's script and compare the numbers.
4. **Understand the diff.** You'll be asked about these numbers in the viva.
5. **Log your AI use** in `docs/ai-usage/saad.md`.

**If the agent gets stuck:** new chat, same day's prompt, plus: "Continue on the existing branch `<branch>`. Run `git log dev..HEAD --oneline` and `git status` first, then tell me what's already done."

---

## Part 3 — How Usman checks your work (so you know what passes)

1. **CI** must be green (backend job AND ml-tests job).
2. **Usman re-runs your scripts** on his machine and compares numbers. A number that doesn't reproduce sends the PR back.
3. **The checklist:** only allowed files changed; protected hashes unchanged; no data or secrets; new tests in CI; ML tests pass without the data folder; every number in a doc traces to a script output; no recalibration or threshold tuning on test data; commits under your name.
4. **Claude reviews the PR** against the day's prompt and writes a correction prompt if needed.
5. **Merge:** Usman merges. Branches are kept.

**A PR gets sent back if:** a claim has no pasted output; a test was weakened; data or chunk text in Git; an invented number, PR number or function name; a metric computed on the wrong target or population (remember the Day 6 external-validation round); you can't explain a number.

---

## Part 4 — The 7 daily Antigravity prompts

Paste **one day per new Antigravity chat**: everything inside the grey block, from `YOUR TASK` to the end.

| Day | Date | Focus | Branch | PR title |
|---|---|---|---|---|
| 1 | Mon 2 Nov | RAG retrieval evaluation on your 60-item test set | `feat/i3-rag-eval` | I3 Day 1: RAG retrieval evaluation |
| 2 | Tue 3 Nov | Explanation quality with the real LLM (validators, fallback, latency) | `feat/i3-explain-eval` | I3 Day 2: explanation quality evaluation |
| 3 | Wed 4 Nov | Load + memory test of the new pipeline (+ blind set #3 by hand) | `test/i3-load-test` | I3 Day 3: load and memory test (new pipeline) |
| 4 | Thu 5 Nov | One generated "evaluation numbers" file for the report | `feat/i3-eval-numbers` | I3 Day 4: generated evaluation numbers |
| 5 | Fri 6 Nov | Trend evaluation + your MIMIC sanity run (by hand) | `feat/i3-trend-eval` | I3 Day 5: trend evaluation + MIMIC sanity summary |
| 6 | Sat 7 Nov | Contract tests for the API + coverage of the new code | `test/i3-contract-coverage` | I3 Day 6: API contract tests + coverage of new code |
| 7 | Sun 8 Nov | Blind test of the new detector + live release check + weekly log | `test/i3-blind3-release-check` | I3 Day 7: blind set 3 + release check + weekly log |

---

### DAY 1 — Monday 2 Nov — RAG retrieval evaluation

```text
YOUR TASK (DAY 1, SAAD): measure how well Usman's guideline retriever finds the right guideline passage for real patient questions, using your 60-item test set (docs/rag/retrieval_test_set.json). Split the result honestly: items whose expected source is in the corpus vs items whose source is not (e.g. ADA 2026, licence pending). You change NO application code. Branch: feat/i3-rag-eval.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: docs/rag/retrieval_test_set.json and scripts/rag/validate_test_set.py (your Day 7 work), docs/RAG_DESIGN.md, docs/GUIDELINE_CORPUS.md (which sources are in the corpus and which are blocked), backend-poc-technical/rag/retriever.py (BM25Retriever), rag/query_map.py, rag/store.py (JsonlChunkStore, DbChunkStore), scripts/rag/search_chunks.py and measure_dense_vs_bm25.py (how Usman ran the retriever before).
DATA: the chunks come from $env:CHRONICCARE_DATA_DIR\rag\chunks.jsonl (from Usman). Print only counts and chunk ids, never chunk text. If the file is missing: STOP and tell me.

PART A — Map expected sources to the corpus
 A1. For each test item, its expected_source (e.g. "WHO 2021 ... section X") is matched against the corpus manifest (source_id + section_path). Write the mapping rules in the script (not by hand per item). Output per item: IN_CORPUS (with the source_id) / NOT_IN_CORPUS (licence-blocked or absent) / UNSURE.
 A2. Print the counts per condition and kind for each group.

PART B — Retrieval metrics (scripts/rag/eval_retrieval.py)
 B1. For IN_CORPUS items, for each language field (question_en, question_ur, question_roman_ur): run the retriever exactly as the app does (same tokenisation, same query_map, top-k), and compute: hit@1, hit@3, hit@5 (a hit = a returned chunk from the expected source; and, where the item names a section, from that section: report both "source hit" and "section hit"), and MRR.
 B2. Per language, per condition, per kind. Bootstrap 95% CIs (reuse ml/evaluation.bootstrap_ci; don't copy it).
 B3. Every miss listed: item id, language, the top-3 returned chunk ids + source_id (no text).
 B4. NOT_IN_CORPUS items: report what the retriever returns (source_id only), and flag any case where it returns something confidently for a question it can't answer from the corpus (that's the "wrong source" risk the explainer's validators must catch).

PART C — Safety-redirect items (no LLM today)
 C1. For each "safety_redirect" item, run the explainer in TEMPLATE mode (llm=None) on the triage a patient asking this would typically get (use the item's condition; if the item implies an emergency, use an emergency triage). Check the output against the item's must_not list with simple rules (no dose numbers, no "you have diabetes", no "stop your medicine"). Report PASS/FAIL per item.

PART D — docs/RAG_EVAL.md: the generated tables, the miss list summary, and plain conclusions: where retrieval works, where Urdu/Roman Urdu fall behind English, what the licence-blocked sources mean for coverage. Tests: backend-poc-technical/ml/tests/test_eval_retrieval.py on a TINY fake corpus (3 fake chunks, 4 fake questions) checking hit@k, MRR and the IN/NOT_IN mapping. Must pass without CHRONICCARE_DATA_DIR.

ACCEPTANCE
 S3-1-01 Every item mapped IN/NOT_IN/UNSURE by rules in the script; counts printed
 S3-1-02 hit@1/3/5 + MRR with CIs per language/condition/kind, for IN_CORPUS items, generated
 S3-1-03 Misses listed by id (no chunk text anywhere)
 S3-1-04 Safety-redirect template checks per item
 S3-1-05 Fake-corpus tests pass without the data folder; no app code changed; gates green

FILES ALLOWED
Create: scripts/rag/eval_retrieval.py, backend-poc-technical/ml/tests/test_eval_retrieval.py, docs/RAG_EVAL.md. Change: docs/tasks/WEEK3_SAAD.md (this file), docs/ai-usage/saad.md.
PR TITLE: I3 Day 1: RAG retrieval evaluation
```

---

### DAY 2 — Tuesday 3 Nov — Explanation quality with the real LLM

```text
YOUR TASK (DAY 2, SAAD): measure the guideline explainer end to end: how often the real LLM's explanation passes the explainer's own safety validators, how often it falls back to the template, why explanations get rejected, how long it takes, and whether the Urdu output is real Urdu. Results decide whether Usman turns EXPLAIN_ENABLED on. No application code changes. Branch: feat/i3-explain-eval.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: backend-poc-technical/rag/explainer.py (explain, get_template_explanation, every validate_* function: list them with Select-String), rag/templates.json, llm/groq_client.py (chat, is_configured; how the model is chosen), docs/LLM_MODEL_CHOICE.md, docs/API_RISK_EXPLAIN.md (explanation states), orchestrator/steps.py step_explain (how the app calls it), scripts/run_v3_personas.py and tests/sim/personas.json.
SECRETS: GROQ_API_KEY only from backend-poc-technical\.env (print SET/NOT SET). TOKEN BUDGET: the account allows about 200k tokens/day per model. The script counts tokens from the API responses and STOPS at 150k for the day, writing how many cases it finished.

PART A — Cases
 A1. Build 40 explanation cases from REAL check-in outcomes: run the personas through the app in-process (TestClient, temp DB) and take the final triage + readings + language of each completed check-in. Mix: routine/review/urgent (no emergencies: the app never explains those), diabetes/hypertension/both, en/ur/roman_ur (roman_ur only if the explainer supports it; check, don't guess). Save the case list (no personal data; personas are fake) to docs/explain_eval/cases.json.

PART B — Runs (scripts/eval_explainer.py)
 B1. For each case, call explain() exactly as step_explain does (same store, same arguments), with the REAL Groq client. Record: mode (llm/template), validator results (which validator rejected, from the explainer's own output), latency (ms), tokens in/out.
 B2. Also run each case with llm=None (template) as the baseline.
 B3. Use the model the app is configured to use (paste which, via get_configured_model or the doc). Don't switch models without asking.

PART C — Metrics (generated): LLM acceptance rate (% passing all validators) with a CI, fallback rate, rejection reasons table (validator name -> count), latency p50/p95, tokens per explanation, per language and per triage level. Urdu: for every ur output, check the share of Arabic-script characters (a script check, not a quality judgement) and list any English-only outputs.

PART D — Human check (Hassaan helps, by hand): pick 10 accepted ur/roman_ur explanations; Hassaan rates each "clear / understandable / wrong" and writes one line. Paste his table into the doc. 10 accepted en explanations: you rate them the same way.

PART E — docs/EXPLAIN_EVAL.md: tables, the human check, and a plain recommendation for Usman: "turn on / keep off / turn on for English only", with the reasons. Tests: ml/tests/test_eval_explainer.py with a FAKE llm (scripted good answer, bad answer with a dose number, timeout) checking the metric code. No network in tests.

ACCEPTANCE
 S3-2-01 40 cases from real in-process check-ins (case file committed, fake personas only)
 S3-2-02 Real-LLM run within the token budget (tokens counted, stop rule works)
 S3-2-03 Acceptance/fallback/rejection/latency/token tables generated, per language and level
 S3-2-04 Urdu script check + Hassaan's 10-item human check
 S3-2-05 Recommendation written; fake-LLM tests pass with no network; no app code changed

FILES ALLOWED
Create: scripts/eval_explainer.py, docs/explain_eval/cases.json, docs/EXPLAIN_EVAL.md, backend-poc-technical/ml/tests/test_eval_explainer.py. Change: docs/ai-usage/saad.md.
PR TITLE: I3 Day 2: explanation quality evaluation
```

---

### DAY 3 — Wednesday 4 Nov — Load and memory test of the new pipeline

```text
YOUR TASK (DAY 3, SAAD): re-run the load test with the Week 2 pipeline (orchestrator in both modes, risk and explanation on and off), measure latency and memory, and compare with the Mid-1 numbers. Render's free tier has 512 MB; the report needs to show we fit with room to spare. Today you also write blind set #3 BY HAND, outside the repo (Part 1.5). Branch: test/i3-load-test.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: scripts/load_test_local.py and docs/LOAD_TEST_RESULTS.md (Mid-1 method and numbers), scripts/load_test_deployed.py, docs/ORCHESTRATOR.md (Usman's RSS numbers: backend about 63 MB direct, 87 MB with LangGraph loaded; 120 check-ins grew memory by about 1-2 MB), main.py lifespan.

PART A — Local load test matrix (extend load_test_local.py or a new scripts/load_test_w3.py)
 A1. Configurations: {ORCHESTRATOR direct, graph} x {flags off, RISK_ENABLED+EXPLAIN_ENABLED on with a FAKE llm that sleeps 800 ms (to mimic Groq latency without spending tokens)}. Concurrency 1, 10, 50, 100 patients, each doing a full check-in (start, answers, complete).
 A2. Per run: requests, failures, p50/p95/p99 per endpoint and for the whole check-in, server RSS at start / peak / end (psutil on the server process, sampled every 200 ms).
 A3. A 30-minute soak at 10 concurrent patients (graph, flags on): RSS every minute. Any steady growth > 20 MB is a leak suspect: report it.

PART B — Deployed health check (no load on the live database)
 B1. Re-run load_test_deployed.py against /api/health only, 50 clients, to compare with Mid-1 (p95 0.57 s). Cold start time measured once after the service sleeps. Paste raw output.

PART C — docs/LOAD_TEST_W3.md: generated tables, Mid-1 vs now, the memory headroom on 512 MB (worst peak + OCR's measured peak from docs/OCR_DESIGN.md if Hassaan's number is there; say "NOT MEASURED" if not), and plain conclusions (e.g. "the explain step's LLM wait dominates latency; it's off by default").

PART D — By hand, not the AI: blind set #3 (Part 1.5). The agent must not see it. Only write in the PR: "blind set 3 written on <date>, stored outside the repo".

ACCEPTANCE
 S3-3-01 Matrix run (2 orchestrators x 2 flag settings x 4 concurrencies), generated tables
 S3-3-02 RSS start/peak/end per run + 30-min soak; leak suspects reported
 S3-3-03 Deployed health comparison with Mid-1 (raw output)
 S3-3-04 Memory headroom on 512 MB stated with sources
 S3-3-05 Fake LLM only (no Groq tokens); no app code changed; gates green

FILES ALLOWED
Create: scripts/load_test_w3.py (or changes to scripts/load_test_local.py: say which), docs/LOAD_TEST_W3.md. Change: docs/ai-usage/saad.md.
PR TITLE: I3 Day 3: load and memory test (new pipeline)
```

---

### DAY 4 — Thursday 5 Nov — One generated "evaluation numbers" file for the report

```text
YOUR TASK (DAY 4, SAAD): build ONE script that re-computes every number the FYP-1 report and the paper quote, and writes them to ONE file. From now on the report quotes only this file. If a number can't be re-computed from the repo, the file says so. Branch: feat/i3-eval-numbers.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: docs/MID1_EVIDENCE_PACK.md (the numbers we quoted at Mid-1 and their sources), docs/ml/EXPERIMENTS_SUMMARY.md, docs/ML_EXTERNAL_VALIDATION.md, docs/TEST_COVERAGE.md, docs/RAG_EVAL.md and docs/EXPLAIN_EVAL.md (Days 1-2), docs/LOAD_TEST_W3.md (Day 3), scripts/verify_mutations.py, scripts/eval_all_phrase_sets.py, scripts/orchestrator_equivalence.py, scripts/run_v3_personas.py, scripts/v3_readiness_report.py (Hassaan's Day 4, if merged).

PART A — scripts/collect_eval_numbers.py
 A1. Sections, each computed by RUNNING code or reading a generated file (never typed):
   1. Tests: backend CI suite count (both orchestrator modes), ML tests, vitest count, mutation proofs killed/total
   2. Safety: persona simulation (64 personas) per engine: levels, demotions vs expected (must be 0), emergency recall on the gold set
   3. Danger phrases: every set x engine (from eval_all_phrase_sets), with set sizes
   4. Orchestrator equivalence: cases identical / total
   5. ML: diabetes_full test AUROC + CI, sensitivity/specificity at the locked threshold, calibration slope, card-population AUROC (from the committed card / EXPERIMENTS_SUMMARY.md); external validation rows (from ML_EXTERNAL_VALIDATION.md, with the "different target" labels kept)
   6. RAG retrieval and explanation (from Days 1-2 outputs)
   7. Load/memory (from Day 3)
   8. Coverage (from a fresh pytest-cov run; pytest-cov in the venv only)
 A2. Each number carries: value, how computed (script + function or file + line), date run.
 A3. A "STALE OR UNTRACEABLE" section: every number in MID1_EVIDENCE_PACK.md that the script can't reproduce today, with why (e.g. the old 6/15 phrase result vs today's numbers).

PART B — docs/EVALUATION_NUMBERS.md (generated; header "Generated by scripts/collect_eval_numbers.py on <date>. Don't edit by hand.")

PART C — Tests: backend-poc-technical/test_collect_eval_numbers.py runs the cheap sections on a tiny fixture and checks the output format (no network, no data folder).

ACCEPTANCE
 S3-4-01 One script, one generated file, every number with its source and date
 S3-4-02 Both orchestrator modes; demotions = 0 checked and printed
 S3-4-03 "Stale or untraceable" list vs the Mid-1 evidence pack
 S3-4-04 Format test in CI; no app code changed; gates green

FILES ALLOWED
Create: scripts/collect_eval_numbers.py, docs/EVALUATION_NUMBERS.md, backend-poc-technical/test_collect_eval_numbers.py. Change: .github/workflows/ci.yml (pytest list), docs/ai-usage/saad.md.
PR TITLE: I3 Day 4: generated evaluation numbers
```

---

### DAY 5 — Friday 6 Nov — Trend evaluation + your MIMIC sanity run

```text
YOUR TASK (DAY 5, SAAD): evaluate the trend agent's arrows on synthetic home-reading series (how often they're right, how often they flip), give the doctors a short threshold sensitivity table for decision D9, and add the MIMIC sanity summary that YOU run by hand. The agent never touches MIMIC. Branch: feat/i3-trend-eval.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: backend-poc-technical/agents/trend_agent.py (compute_trends, TREND_THRESHOLDS, PROPOSED_MIN_READINGS_FOR_DIRECTION), docs/TREND_AGENT.md, docs/DOCTOR_REVIEW_PACK_W2.md decision 9, backend-poc-technical/ml/mimic/README.md.
MIMIC: the agent must NOT run trend_sanity.py, list MIMIC folders or read omr.csv. Saad runs it himself in a normal PowerShell window and pastes ONLY the printed summary into the PR description.

PART A — Synthetic series (scripts/eval_trends.py; seeded, reproducible)
 A1. Generate series for systolic, diastolic and glucose over 30 days with known truth: flat, rising (several slopes), falling, one outlier, mixed contexts (fasting vs after meal), 3/5/8/15 readings, home-BP noise levels (realistic SD values: write the values used in the doc with their source, or mark them "assumed").
 A2. Run compute_trends; measure per scenario: correct direction %, false "rising"/"falling" on flat series, missed real trends, flips between consecutive days (sliding the window by 1 day).

PART B — Threshold sensitivity for the doctors (D9)
 B1. Re-run Part A with thresholds systolic 5/10/15, diastolic 3/5/8, glucose 10/20/30 mg/dL and minimum readings 3/5. Table: false alarm % vs missed trend % per setting. Mark the current proposed setting (10/5/20, 5 readings).
 B2. This is a table for the doctors; you don't change the thresholds.

PART C — MIMIC summary (by hand): paste the printed summary into the PR description and into docs/TREND_EVAL.md as-is, with the date. If you didn't run it, write "MIMIC NOT RUN".

PART D — docs/TREND_EVAL.md (generated tables + the MIMIC summary + plain conclusions). Tests: ml/tests/test_eval_trends.py (series generator deterministic; metric code on 3 tiny hand-made series).

ACCEPTANCE
 S3-5-01 Seeded synthetic scenarios with known truth; metrics generated
 S3-5-02 Threshold sensitivity table for D9; thresholds unchanged in code
 S3-5-03 MIMIC summary pasted by Saad (or MIMIC NOT RUN); the agent never touched MIMIC
 S3-5-04 Tests pass without the data folder; gates green

FILES ALLOWED
Create: scripts/eval_trends.py, docs/TREND_EVAL.md, backend-poc-technical/ml/tests/test_eval_trends.py. Change: docs/ai-usage/saad.md.
PR TITLE: I3 Day 5: trend evaluation + MIMIC sanity summary
```

---

### DAY 6 — Saturday 7 Nov — API contract tests + coverage of the new code

```text
YOUR TASK (DAY 6, SAAD): stop the backend and the new screens drifting apart, and close coverage gaps in last week's code. (1) Contract tests: the JSON examples in docs/API_RISK_EXPLAIN.md must match what the real endpoints return, field by field. (2) Coverage: orchestrator steps, the risk and explain steps, record_edits/import, the OCR routes. Fix only NON-safety bugs you find (each with a failing-then-passing test); safety-area bugs become issues for Usman. Branch: test/i3-contract-coverage.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: docs/API_RISK_EXPLAIN.md, scripts/gen_api_risk_explain_examples.py (how the examples were generated), orchestrator/steps.py (step_risk, step_explain, _build_patient_risk_view), main.py ReviewDetailResponse and CheckinCompleteResponse, test_checkin_risk_explain.py, test_record_edits.py, test_record_export_import.py, test_ocr_upload.py, docs/TEST_COVERAGE.md.

PART A — Contract tests (backend-poc-technical/test_api_contract_risk_explain.py)
 A1. Parse every JSON example block in docs/API_RISK_EXPLAIN.md. For each state (ok, not_enough_information, null, error, emergency, template, Urdu), produce the same state through the real endpoints (TestClient, fake LLM, temp DB) and assert: same keys, same types, same nesting; the patient view never has a probability or model name; the provider view has them.
 A2. If the doc and the code disagree: don't change either; mark the test xfail(strict=True) with the reason, open an issue for Usman, paste the link.
 A3. The frontend types in app/lib/api.ts (Hassaan's Days 2-3): a small script checks that every field the doc defines exists in the TypeScript types (string match is enough); output in the report.

PART B — Coverage of the new code (pytest-cov in the venv only)
 B1. Before: coverage for orchestrator/*, rag/store.py, agents/risk_rules.py, the record_edits/import functions, data_sources/ocr/*, the OCR routes. Paste.
 B2. Add at least 25 meaningful tests on the least-covered branches (name the function + branch for each; real function names via Select-String).
 B3. After: paste the same table. docs/TEST_COVERAGE.md gets a "Week 3" section with before/after.

PART C — Non-safety fixes found today: failing test -> fix -> passing test, commit "fix(<area>): <what>". Safety-area findings: issue for Usman with label "safety" (link).

ACCEPTANCE
 S3-6-01 Every contract example checked against the real endpoints; mismatches xfail + issue
 S3-6-02 TS type check of the contract fields (output pasted)
 S3-6-03 >= 25 new meaningful tests; before/after coverage for the new modules
 S3-6-04 Non-safety fixes with failing-then-passing tests; safety findings filed
 S3-6-05 No protected file changed; gates green in both orchestrator modes

FILES ALLOWED
Create: backend-poc-technical/test_api_contract_risk_explain.py, backend-poc-technical/test_w3_coverage_new_code.py, scripts/check_contract_ts_types.py. Change: non-safety source files ONLY for fixes you list (each with its test), docs/TEST_COVERAGE.md, .github/workflows/ci.yml (pytest list), docs/ai-usage/saad.md.
NOT allowed: protected files, docs/API_RISK_EXPLAIN.md (Usman's contract: report mismatches instead).
PR TITLE: I3 Day 6: API contract tests + coverage of new code
```

---

### DAY 7 — Sunday 8 Nov — Blind set 3 + live release check + weekly log

```text
YOUR TASK (DAY 7, SAAD): (1) commit blind set #3 (written by hand on Wednesday, outside the repo) and run it ONCE through v2, v3, Usman's new danger-phrase detector (if merged) and the prototype, with no changes to any detector afterwards; (2) re-run the system test cases ST-01..20 on the live site with a fake account; (3) write your weekly log. Branch: test/i3-blind3-release-check.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_SAAD.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
- Machine: Windows, PowerShell. Backend venv: backend-poc-technical\.venv (Python 3.11). Run commands from the repo root unless a step says otherwise. Set $env:PYTHONIOENCODING="utf-8" in every terminal, so Urdu prints correctly.
- State of dev on Mon 2 Nov: schema v15 (v13 waist_cm, v14 record_edits, v15 risk/explanation/trace + guideline_chunks); ORCHESTRATOR=direct|graph (default direct, both must behave identically); flags all OFF by default: RISK_ENABLED, RISK_CAN_RAISE, EXPLAIN_ENABLED, OCR_ENABLED, SCREENING_REMINDER_INTERVAL_DAYS (unset). CI backend suite about 1,470+ tests.

SECRETS AND DATA
- Never print, log, commit or paste any secret: .env values, Groq key, Firebase config, MySQL URL, Render deploy hook. When you need to show that an env var is set, print only "SET" or "NOT SET".
- Never git-add data: .csv/.parquet/.xpt/.zip/.db/.sqlite, model files, real documents, anything under $env:CHRONICCARE_DATA_DIR. Docs contain aggregates only.
- Never open, list, read or run anything on MIMIC data. Never put MIMIC rows anywhere (chat, GitHub, any AI tool).
- Don't open ADA/AHA guideline PDFs with any tool, and never commit guideline text.
- Fake data only, everywhere (tests, screenshots, the live site). Fake names like "Test Patient".
- Don't read the clipboard.

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
- Never weaken, skip, delete or loosen an existing test. Never change an expected value in tests/sim/*.json. If an existing test seems wrong, STOP and show me.
- Every table of results must be printed by a script that runs the real code (through the real HTTP endpoints where the prompt says so). No hand-typed rows, levels or numbers.
- If something can't be done, write NOT DONE and the reason. If a check wasn't run, write NOT RUN. Never imply success.
- Any new patient-facing text needs English AND Urdu (and Roman Urdu where the interview uses it). Never show server error text to a patient; show a translated message.
- New backend test files must be added to the pytest list in .github/workflows/ci.yml (that step only, unless this prompt says otherwise). ML tests go under backend-poc-technical/ml/tests (the ml-tests job) and must pass WITHOUT $env:CHRONICCARE_DATA_DIR set.
- Tests never call the network (Groq, FHIR, anything). Monkeypatch clients; a test that would call out must fail.
- If an instruction conflicts with the handbook or with what the code actually does, STOP and ask. Don't guess.

END GATES (run all of them; print counts and the last 40 lines of each)
 1. python backend-poc-technical/init_local_db.py, then the EXACT CI pytest command from ci.yml (with today's new files added), once with $env:ORCHESTRATOR="direct" and once with $env:ORCHESTRATOR="graph"
 2. python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"   (full glob, to catch files missing from the CI list)
 3. python scripts/verify_mutations.py
 4. Remove-Item Env:CHRONICCARE_DATA_DIR -ErrorAction SilentlyContinue; $env:PYTHONPATH="backend-poc-technical"; python -m pytest backend-poc-technical/ml/tests -q
 5. npm run lint; npm test; npm run build
 6. Compliance grep (must print nothing):
    git grep -n -i -E "hipaa[ -]?(compliant|grade|certified)|gdpr[ -]?compliant|fda[ -]?(approved|cleared)|clinically validated" -- app
 7. Secret scan (must print nothing):
    git grep -n -E "AIzaSy[A-Za-z0-9_-]{10}|gsk_[A-Za-z0-9]{10}|AVNS_[A-Za-z0-9]{6}|-----BEGIN (RSA |EC )?PRIVATE KEY"
    git ls-files | Select-String -Pattern "(^|/)\.env$|\.db$|\.sqlite$|\.parquet$|\.xpt$|\.XPT$"
 8. SHA-256 of the protected files ("AFTER"). Each must equal BEFORE, unless this prompt allowed the change. Name every file that changed and why.
 9. git diff dev --stat (only files this prompt allows)
10. ruff check backend-poc-technical scripts --select E9,F63,F7,F82 --exclude backend-poc-technical/output   (ALWAYS LAST)

PUSH AND PR
- git fetch origin; git merge origin/dev (if dev moved today). ci.yml conflicts on the pytest line are normal: keep EVERY file from BOTH sides in ONE line, then re-run gate 1.
- git push -u origin <branch>
- NEVER merge a PR (not even your own). Push, open the PR, STOP. Usman merges. Never delete a branch.
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

EVIDENCE RULES (these override anything softer above)
- "Output"/"verbatim" means RAW and unchanged. Summaries are labelled SUMMARY. Every number in a doc comes from a file a script wrote, or from a command output you paste.
- EVERY file:line citation and every function name you mention must come from a Select-String output you paste in the report, never from memory. (Week 2 had invented constants, invented function names, invented PR numbers and invented doctor statements. Each one cost a correction round.)
- PR numbers come only from `gh pr list ... --json number,title,author` output you paste. Doctor statements come only from docs/CLINICIAN_RESPONSES.md.
- Save raw outputs with Tee-Object to $env:CHRONICCARE_DATA_DIR\logs\w3\<day>\<step>.txt and list the paths.
- Use backend-poc-technical\.venv (Python 3.11). ruff runs LAST.

READ FIRST: scripts/eval_all_phrase_sets.py, docs/DANGER_PHRASE_PLAN.md, Usman's detector PR (gh pr list --state all --search "danger" --json number,title,state: paste), docs/system_test_cases.md, docs/SYSTEM_TEST_RESULTS_Hassaan.md (format).

PART A — Blind set 3
 A1. Saad copies Chronicare-data\blind_set_3.json into tests/sim/blind_set_3_saad.json and commits it FIRST (his own commit, before the agent runs anything). The agent then adds it to eval_all_phrase_sets.py and runs the harness ONCE. Paste the raw table.
 A2. No detector, pattern or prototype change after seeing the result, in this PR or any other today.
 A3. docs/BLIND_SET_3_RESULTS.md: the table, every missed danger phrase and every false alarm per engine, and the git log line proving the set was committed before the run.

PART B — Live release check (by Saad with the agent's help writing the doc; fake account only)
 B1. Run ST-01..20 on the live site (and the risk/explanation/OCR screens only if Usman has turned those flags on; otherwise "flag off: NOT RUN"). Record PASS/FAIL with screenshots in docs/screenshots/w3/release/.
 B2. docs/SYSTEM_TEST_RESULTS_W3.md in the same format as Hassaan's earlier file. Failures become issues (label w3-release; links).

PART C — docs/weekly/2026-W45-saad.md (one page): your PRs from `gh pr list --author @me --state all --limit 30` (paste), numbers from EVALUATION_NUMBERS.md and this week's docs only, what slipped and why, open questions for Usman, next week (freeze week) top 3. Untraceable: "NOT TRACED".

ACCEPTANCE
 S3-7-01 Blind set committed by Saad before the single run (git log evidence); no detector changes after
 S3-7-02 Results per engine incl. the new detector; misses and false alarms listed
 S3-7-03 ST-01..20 on the live site with screenshots; failures filed
 S3-7-04 Weekly log with traced numbers and real PR numbers; gates green

FILES ALLOWED
Create: tests/sim/blind_set_3_saad.json (Saad's own commit), docs/BLIND_SET_3_RESULTS.md, docs/SYSTEM_TEST_RESULTS_W3.md, docs/screenshots/w3/release/*, docs/weekly/2026-W45-saad.md. Change: scripts/eval_all_phrase_sets.py (add the new set only), docs/ai-usage/saad.md.
PR TITLE: I3 Day 7: blind set 3 + release check + weekly log
```

---

## Appendix B — Who does what this week (so your work fits with the others')

| Person | Role this week | Main outputs |
|---|---|---|
| **Usman** | Lead, safety owner, reviewer, releaser | Release 1 (Week 2 to production, schema v15) → danger-phrase word groups v1 behind a flag → doctor-approved rule changes → explainer guards (timeouts, token guard, cache) → v3-default decision → report/paper evidence → release 2 + Week 3 gate. Reviews and merges every PR. |
| **Hassaan** | Screens + interview + records | Finish OCR v1 (#96) + bug-bash #85/#86/#88 + roman_ur profile → patient risk card + "Why this result?" → provider check-in risk + explanation + decision timeline → v3 readiness (G-02, G-14) + go/no-go report → end-to-end journeys + accessibility → OCR hardening on Pakistani lab layouts → user guide + final Urdu review |
| **Saad** | Evaluation owner | RAG retrieval eval → explanation quality (real LLM, token budget) → load + memory test of the new pipeline → one generated EVALUATION_NUMBERS.md → trend eval + his own MIMIC sanity run → API contract tests + coverage of new code → blind set #3 on the new detector + live release check |

**How the pieces connect**
- Hassaan's Day 2-3 screens read the fields defined in `docs/API_RISK_EXPLAIN.md`. Saad's Day 6 contract tests check that the backend still returns exactly those fields. If either finds a mismatch, it goes to Usman as an issue; nobody edits the contract doc except Usman.
- Saad's Day 2 explanation evaluation decides whether Usman turns EXPLAIN_ENABLED on (Day 4). Hassaan rates 10 Urdu explanations for it by hand.
- Hassaan's Day 4 readiness report decides Usman's Day 5 v3-default switch.
- Usman freezes the danger word groups on Tuesday. Saad writes blind set #3 on Wednesday, outside the repo, and runs it once on Sunday. Nobody tunes any detector after seeing it.
- Saad's Day 4 EVALUATION_NUMBERS.md is the only source of numbers for the report (Usman's Day 6).
- **Shared files:** `.github/workflows/ci.yml` (pytest list only), `app/translations/index.ts`, `app/lib/api.ts`, `backend-poc-technical/main.py`, `scripts/eval_all_phrase_sets.py`. The second PR to merge resolves the conflict: `git fetch origin; git merge origin/dev`, keep BOTH sides (for ci.yml: every file in one pytest line), re-run the gates, push to your own branch.

**Dates**
| Date | What |
|---|---|
| Sun 8 Nov | **Features done** (everything for the demo merged); release 2 |
| Tue 10 Nov | **Code freeze:** only bug fixes, tests and docs after this |
| Wed 11 – Sat 14 Nov | Final bug bash, doctor sign-off, small usability test (3–5 people), report and slides |
| Sun 15 Nov | Report and slides final; full demo rehearsal on the live site |
| Mon 16 Nov | Buffer day; final `dev` → `main` deploy in the morning + smoke test |
| **Tue 17 Nov** | **FYP-1 final evaluation** |

**Daily message to Usman (WhatsApp, every evening, 4 lines)**
```
Day N: <PR link or "not pushed: why">
Gates: CI pytest X passed (direct) / X passed (graph); vitest X; mutations X/Y killed; ml-tests X
Blocked on: <nothing / what>
Tomorrow: <one line>
```

---

# Appendix A — The full project handbook

## STATE ON 2 NOV 2026 (read this first; it overrides older text below)

The handbook below was written for Week 2 (26 Oct). This section records what changed during Week 2. Where they disagree, this section wins.

### What was merged in Week 2 (from `gh pr list --state merged`)
| PR | Author | What |
|---|---|---|
| #70 | Usman | EHR test patients + doctor on record |
| #71, #73 | Hassaan | Interview audit (v2 vs v3, probes) + probe fix |
| #72 | Usman | Guideline corpus + ingestion + rules check (open-licence sources only; ADA 2026 and AHA/ACC 2025 blocked until written licence) |
| #75 | Saad | Temporal split (train 1999–2012, validation 2013–2016, test 2017–2023), fair baseline, feature map, label catalogue |
| #76, #77, #80 | Hassaan | v3 answer understanding + slot filling; dual diagnosis + caregiver + summary; v3 complete in Urdu and Roman Urdu |
| #78 | Saad | ML evaluation toolkit + model artifact contract |
| #79 | Usman | ML_PLAN.md + BM25 retriever + grounded explainer (validators) |
| #81, #83 | Saad | Trend agent + reading history; trends live (API, patient screen, provider row) |
| #82 | Usman | Experiment harness + model runs |
| #84 | Hassaan | OCR spike: RapidOCR on the server chosen (9/9 handwritten medicines vs Tesseract.js 1/9) |
| #89 | Hassaan | Urdu danger-phrase proposals (blind result: current v3 3/20, proposed 7/20) |
| #90 | Usman | Risk agent (provider-only panel behind RISK_ENABLED), waist field (schema v13), model cards, doctor pack |
| #91 | Saad | External validation (right targets: Framingham/Pima proxies; BRFSS = different target, ranking only) + DHS loader skeleton |
| #92 | Hassaan | Record edit history (schema v14, record_edits) + export (JSON/FHIR) + import with preview (all-or-nothing) |
| #93 | Usman | LangGraph orchestrator behind ORCHESTRATOR (78/78 identical to direct), lazy-loaded |
| #94 | Saad | Coverage + 39 tests, #87 fix, MIMIC trend sanity script (write-only), 60-item RAG test set, phrase test round 2 |
| #95 | Usman | P0: a bare "no" is never read as glucose 9 |
| #98 | Usman | Risk + explanation + trace wired into every check-in (flags off), schema v15, guideline_chunks + DbChunkStore, API contract doc, danger-phrase harness + plan |
Open at the start of Week 3: #96 (Hassaan, OCR v1 behind OCR_ENABLED). Closed without merge: #74. Safety issue: #97 (danger-phrase sensitivity, both engines).

### Schema and flags
- Schema **v15**: v13 waist_cm; v14 record_edits; v15 checkin_results.risk_json / explanation_json / trace_json + guideline_chunks.
- Flags (all default OFF): RISK_ENABLED, RISK_CAN_RAISE (only routine → review on band high), EXPLAIN_ENABLED, OCR_ENABLED (+ OCR_PROVIDER=rapidocr|fake; fake refused when APP_ENV=production), SCREENING_REMINDER_INTERVAL_DAYS (unset = dormant), ORCHESTRATOR=direct|graph (default direct), INTERVIEW_ENGINE=v2|v3 (default v2).
- Emergencies skip risk and explanation entirely (no LLM call during an emergency).

### APIs added in Week 2 (all additive)
- `GET /api/me/trends`; `GET /api/me/record/history`; `GET /api/me/record/export?format=json|fhir`; `POST /api/me/record/import?dry_run=`; `POST /api/me/record/uploads` and `/confirm` (OCR, behind the flag).
- `/api/checkins/{id}/complete` response: optional `risk` (patient view: band + reasons, no probability) and `explanation`.
- `GET /api/provider/review/{checkin_id}`: existing live `risk` (#90 panel) unchanged; new optional `checkin_risk`, `explanation`, `trace`, `recent_record_edits`.
- Contract: `docs/API_RISK_EXPLAIN.md` (examples generated by `scripts/gen_api_risk_explain_examples.py`).

### ML decisions (docs/ML_PLAN.md)
- D10 plain LR export (pure-Python scorer; plain `lr` unless `lr_balanced` beats it by ≥ 0.01 validation AUROC). D11 five gates. D12 `diabetes_full_nhanes` is provider-only and experimental (test AUROC 0.7527 [0.7293–0.7748]; card-population AUROC 0.6640). D13 hypertension models retired. D14 recommend asking for a real BP reading. D15 rule-based HbA1c reminder (dormant until doctors set the interval).
- External sets are test-only. No recalibration or threshold tuning on validation/test or external data.

### Safety state
- Free-text danger detection is the biggest open gap. On blind/independent sets the live v2 engine catches 1/15 (Saad r2) and v3 3/20 (Saad blind Urdu). Plan: `docs/DANGER_PHRASE_PLAN.md` (word groups, raise-only, behind a flag), waiting for doctors; Usman builds v1 in Week 3.
- Waiting for doctors (docs/DOCTOR_REVIEW_PACK_W2.md): D1 danger phrases, D2 meter LO/HI (today: routine in both engines), D3 15 g wording, D4 BP guideline edition, D5 vomiting split (2 urgent vs 1 emergency), D6 reminder interval, D7 risk panel, D8 waist landmark, D9 trend thresholds; plus v2 bare 2–40 after the unit question, and v3 no-readings → routine (G-21).
- Interview gaps still open without a doctor: G-02 (unclear adherence answers), G-12 (profile rejects "roman_ur"), G-14 (Roman Urdu caregiver phrases), G-16 (past-tense negation; lives in protected input_triage.py, covered by the word-group plan).

### Numbers on 2 Nov (re-run them; don't quote these in the report; the report quotes docs/EVALUATION_NUMBERS.md from Week 3)
- Backend CI suite 1,472 passed (both orchestrator modes); mutation proofs 40/40 killed; vitest about 240; backend coverage 89%.
- Backend RSS: about 63 MB (direct) / 87 MB (LangGraph loaded); 120 check-ins in a row grew memory by about 1–2 MB.

### Working rules added in Week 2
- Agents never merge PRs and never delete branches. Usman merges after re-running.
- PR numbers only from `gh pr list` output; doctor statements only from docs/CLINICIAN_RESPONSES.md; function names and file:line only from Select-String output.
- ML tests must pass without CHRONICCARE_DATA_DIR. Tests never call the network.
- Blind test sets are committed by their author BEFORE the single run, and nobody tunes on them afterwards.

---

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
