# Hassaan Mudassar: Engineering Guide, Commits and Viva (ChronicCare AI)

**Why this file exists:** the Mid-1 evaluation says each student must independently explain their modules, source code, architecture and tests. You own the **interaction layer**: interview bank and answer validation, reconciliation and trust levels, the Local Store, and the two screens that show them. This guide gives you every step, command and AI prompt to make real commits in those files, so that you can show your own work and explain it.

**Honest scope:** your commits will carry today's date. They add tests, fixes and documentation to Iteration 1 modules. The report will describe them as "completed 13 to 14 October 2026". Usman wrote most of the engine and that is in the commit history. Do not say you wrote it. Say what you own, what you tested, what you changed.

## STEP 0: Setup (PowerShell, once)

```powershell
cd <folder where you keep projects>
git clone https://github.com/UsmanBari/chroniccare-ai
cd chroniccare-ai
git checkout dev
git pull origin dev
git config user.name "Hassaan Mudassar"
git config user.email "i230536@isb.nu.edu.pk"
cd backend-poc-technical
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_local_db.py
python -m pytest -q
```

The last command must end green. If it fails, copy the error to Usman before doing anything else. Do not change code to "make it pass".

## The rules for every task

1. One task = one branch = one pull request to `dev`. Never push to `dev` or `main` directly.
2. Start each task from fresh `dev`: `git checkout dev; git pull origin dev; git checkout -b <branch>`.
3. Run the checks before every commit: `cd backend-poc-technical; python -m pytest -q` and, if you touched the frontend, `cd ..; npm test`.
4. Commit with your own git identity (Step 0). Use the exact commit message in the task.
5. The AI agent writes a draft. You read every line, run it, and change what is wrong. If you cannot explain a line, delete it or ask the agent to explain it until you can.
6. After each task, add one row to your AI log (Step LOG at the bottom). Use real dates and what really happened. Include one row where the agent was wrong, if that happened.
7. Never write a result you did not see. If the detector misses a phrase, the miss goes in the results file.

## STEP 1: Read before you touch anything (60 to 90 minutes, no commits)

Open these files and read the docstring and the function list. Write 3 lines of notes per file in `notes_hassaan.txt` (this file is for you, do not commit it).

| File | What to learn |
|---|---|
| `backend-poc-technical/agents/answer_validation.py` | How "ek sau bees", "12080" and "7" (glucose) are read; the plausibility ranges |
| `backend-poc-technical/agents/reconciliation_agent.py` | 48-hour match window; thresholds glucose 15, HbA1c 0.5, BP 10, weight 2 |
| `backend-poc-technical/agents/verification_agent.py` | `TRUST_LEVELS`: fhir high, local medium, self-reported low |
| `backend-poc-technical/data_sources/local_store.py` and `local_adapter.py` | Stores rows only; no clinical meaning |
| `backend-poc-technical/agents/interview_bank/loader.py` | What makes the loader reject a bank file |
| `app/components/ConflictScreen.tsx` | How two values and their sources are shown |

Run once and read the output: `python -m pytest -q test_answer_validation.py test_interview_bank.py scenarios/test_reconciliation.py -v`.

## STEP 2: Tasks

### H-1: Independent Urdu and Roman Urdu danger-phrase set

**Goal:** Create a phrase set the detector was NOT tuned on, and report the real result. This answers the evaluator point about 100% recall and denominators.

**Files:** `tests/sim/danger_phrases_independent_hassaan.json`, `docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md`, `scripts/eval_phrase_set.py` (if another member already added it, reuse theirs)

**Steps**

1. Do not open `tests/sim/danger_phrases_gold.json` yet.
2. Write 30 phrases yourself: 15 that describe an emergency and 15 that negate one. Mix Urdu script and Roman Urdu. Cover: chest pain, breathing, confusion or stroke, fainting, vision loss, vomiting with high sugar, severe headache.
3. Save them in `tests/sim/danger_phrases_independent_hassaan.json` as a list of objects with the fields `text`, `expected_danger`, `category`, `language`, `author` (always `"hassaan"`).
4. Run the script in the prompt. Record TP, FN, FP, TN.
5. Write `docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md` with the table, the phrases that failed and why you think they failed. Do not edit the detector. A miss is a finding, not a failure.

**Prompt for your AI agent (copy and paste, then follow up until you understand every line):**

> Write a Python script `scripts/eval_phrase_set.py` for the repo at backend-poc-technical. It takes a JSON file path as argument. The file is a list of objects with text, expected_danger, category, language, author. For each item call screen_multilingual_danger_phrases from agents.input_triage (run from backend-poc-technical, add it to sys.path). Print TP, FN, FP, TN, sensitivity and specificity, then list every failing item with its text and category. Do not change the detector. Explain each line of the script to me after writing it.

**Check before you commit:** `python scripts/eval_phrase_set.py ../tests/sim/danger_phrases_independent_hassaan.json` prints numbers that add up to 30, and you can explain TP, FN, FP, TN in your own words.

**Commit and pull request**

```powershell
git checkout dev
git pull origin dev
git checkout -b test/h1-independent-urdu-phrases
# ... do the work, run the checks ...
git add <the files listed above>
git commit -m "test: add independent Urdu danger-phrase set and results"
git push -u origin test/h1-independent-urdu-phrases
```

Then open a pull request into `dev` on GitHub with this description: what you added, the test result you saw, and what you checked or changed after the AI draft. Send Usman the pull request link.

---
### H-2: Reconciliation boundary tests

**Goal:** Prove what happens exactly at the 48-hour window and at each threshold.

**Files:** `backend-poc-technical/test_reconciliation_boundaries.py`

**Steps**

1. Open `scenarios/fixtures.py` and copy how a bundle is built.
2. Create `backend-poc-technical/test_reconciliation_boundaries.py`.
3. Write tests for: two readings exactly 48.0 hours apart; 48 hours and 1 minute apart; a delta equal to each threshold (glucose 15, HbA1c 0.5, systolic 10, diastolic 10, weight 2) and just above it; mismatched units; different patient ids (expect `ValueError`).
4. For each test, write in a comment what the code does (matched or not, conflict or agree). If the code behaves differently from the docstring, write that in the pull request.

**Prompt for your AI agent (copy and paste, then follow up until you understand every line):**

> In the repo backend-poc-technical, read agents/reconciliation_agent.py and scenarios/fixtures.py. Write a pytest file test_reconciliation_boundaries.py with boundary tests for reconcile_bundles: exactly 48h and 48h plus one minute match window; each conflict threshold exactly equal and just above; mismatched units; different patient ids raising ValueError. Use the same bundle shape as scenarios/fixtures.py. For every test, tell me whether the current code uses > or >= at that boundary and show the line.

**Check before you commit:** `python -m pytest -q test_reconciliation_boundaries.py` is green. Then change one threshold in `reconciliation_agent.py` on your machine, see a test fail, and undo the change (do not commit it).

**Commit and pull request**

```powershell
git checkout dev
git pull origin dev
git checkout -b test/h2-reconciliation-boundaries
# ... do the work, run the checks ...
git add <the files listed above>
git commit -m "test: boundary cases for reconciliation window and thresholds"
git push -u origin test/h2-reconciliation-boundaries
```

Then open a pull request into `dev` on GitHub with this description: what you added, the test result you saw, and what you checked or changed after the AI draft. Send Usman the pull request link.

---
### H-3: Answer-validation tests for Urdu and Roman Urdu

**Goal:** Add tests for the inputs real patients type.

**Files:** `backend-poc-technical/test_answer_validation.py`

**Steps**

1. Read `test_answer_validation.py` (9 tests).
2. Add at least 8 tests for: Urdu digits in a BP answer, mixed digits, "ek sau bees" for glucose, "do sau" with and without a unit, a minimiser phrase ("bas thora sa"), a decimal comma, a glucose of 7 with no unit.
3. Any input that does not behave as you expect: keep the test, mark it with `pytest.mark.xfail(reason="...")` and describe it in the pull request. Do not hide it.

**Prompt for your AI agent (copy and paste, then follow up until you understand every line):**

> In backend-poc-technical read agents/answer_validation.py and test_answer_validation.py. Add at least 8 new pytest tests in the same style covering Urdu and Eastern Arabic digits for BP, mixed digits, Roman Urdu number words for glucose, glucose with and without unit, minimiser phrases, decimal commas. Run each input through the real function first and base the expected value on the real behaviour; if the behaviour looks wrong, mark the test xfail with a reason instead of changing the code. Tell me what each test shows.

**Check before you commit:** `python -m pytest -q test_answer_validation.py` is green (xfail counts as expected failure).

**Commit and pull request**

```powershell
git checkout dev
git pull origin dev
git checkout -b test/h3-answer-validation-urdu
# ... do the work, run the checks ...
git add <the files listed above>
git commit -m "test: Urdu and Roman Urdu answer validation cases"
git push -u origin test/h3-answer-validation-urdu
```

Then open a pull request into `dev` on GitHub with this description: what you added, the test result you saw, and what you checked or changed after the AI draft. Send Usman the pull request link.

---
### H-4: Local Store cross-patient access tests

**Goal:** Show that one patient cannot read or change another patient's rows.

**Files:** `backend-poc-technical/test_local_store_ownership.py` (and `data_sources/local_store.py` only if a bug is found)

**Steps**

1. Read the functions in `data_sources/local_store.py` (`add_local_observation`, `delete_local_observation`, `update_local_medication`, `get_local_*`).
2. Create `backend-poc-technical/test_local_store_ownership.py` using a temporary SQLite file (`tmp_path`).
3. Test: patient A adds an observation; patient B cannot get, update or delete it by id.
4. If B can, that is a real bug. Write the failing test, then fix the function in the same pull request with a small change and explain it.

**Prompt for your AI agent (copy and paste, then follow up until you understand every line):**

> In backend-poc-technical read data_sources/local_store.py. Write test_local_store_ownership.py using pytest tmp_path and the SQLite backend: patient A adds an observation and a medication; check that patient B cannot get, update or delete them by id. Run it. If any test shows B can access A's row, show me the function and propose the smallest fix, and explain why it is safe.

**Check before you commit:** Tests pass, or you have a failing test plus a fix and an explanation.

**Commit and pull request**

```powershell
git checkout dev
git pull origin dev
git checkout -b test/h4-local-store-ownership
# ... do the work, run the checks ...
git add <the files listed above>
git commit -m "test: Local Store cross-patient access"
git push -u origin test/h4-local-store-ownership
```

Then open a pull request into `dev` on GitHub with this description: what you added, the test result you saw, and what you checked or changed after the AI draft. Send Usman the pull request link.

---
### H-5: Make the system-test sheet true

**Goal:** The sheet in the repo must match what you really ran.

**Files:** `docs/SYSTEM_TEST_RESULTS_Hassaan.md`

**Steps**

1. Open `docs/SYSTEM_TEST_RESULTS_Hassaan.md`.
2. For each of your tests (ST-01 to ST-20 share), write DONE or NOT DONE, the date, and one line of what you saw. If you did not run a test, leave NOT DONE.
3. The report (Chapter 7) says ST-01 to ST-20 were run. If your rows say NOT DONE, tell Usman now so the report is corrected.

**Prompt for your AI agent (copy and paste, then follow up until you understand every line):**

> Reformat my system test results into the table style used in docs/SYSTEM_TEST_RESULTS_Hassaan.md. I will paste my notes. Do not add any result I did not give you; if a field is missing write NOT DONE.

**Check before you commit:** The sheet and the report say the same thing.

**Commit and pull request**

```powershell
git checkout dev
git pull origin dev
git checkout -b docs/h5-system-test-results
# ... do the work, run the checks ...
git add <the files listed above>
git commit -m "docs: record real system-test results"
git push -u origin docs/h5-system-test-results
```

Then open a pull request into `dev` on GitHub with this description: what you added, the test result you saw, and what you checked or changed after the AI draft. Send Usman the pull request link.

---
### H-6: Accessibility check for the remaining screens

**Goal:** The evaluator says accessibility is partly pending. Finish what you can.

**Files:** `docs/ACCESSIBILITY_CHECK.md`

**Steps**

1. Open `docs/ACCESSIBILITY_CHECK.md`. The chat, result and provider screens are NOT DONE.
2. On the live site, sign in and, for each of those three screens, do: keyboard only (Tab, Shift+Tab, Enter), browser zoom 200 %, and window width 320 px.
3. Record PASS or FAIL and one line of what you saw for each. Take a screenshot of each failure.
4. Do not fix the frontend yet. Report failures to Usman in the pull request.

**Prompt for your AI agent (copy and paste, then follow up until you understand every line):**

> Help me format accessibility results for the chat, result and provider screens into the table already in docs/ACCESSIBILITY_CHECK.md. I will give you the observations. Do not invent any result.

**Check before you commit:** The file has a real result for every cell you tested, and NOT DONE for the rest.

**Commit and pull request**

```powershell
git checkout dev
git pull origin dev
git checkout -b test/h6-accessibility-remaining
# ... do the work, run the checks ...
git add <the files listed above>
git commit -m "docs: accessibility results for chat, result and provider screens"
git push -u origin test/h6-accessibility-remaining
```

Then open a pull request into `dev` on GitHub with this description: what you added, the test result you saw, and what you checked or changed after the AI draft. Send Usman the pull request link.

---
## STEP 3: What you must be able to explain (absolutes)

- The bank is split into modules (core, diabetes, hypertension, insulin_or_sulfonylurea, fasting, access_barriers, sick_day, wellbeing, caregiver). Every question has English and Urdu text and a source id that must exist in `SOURCES.json`. The loader refuses to start on a duplicate id, a missing template, an unmapped rule trigger or an unknown source.
- A glucose answer from 2.0 to 40.0 with no unit triggers a question about the unit. Above 40 is read as mg/dL. If the unit stays unclear, the answer is stored as unknown and flagged.
- An unknown answer is never turned into "no".
- Reconciliation matches two readings one-to-one by nearest timestamp inside 48 hours, then compares the difference with a fixed threshold. It never says which source is right and never gives clinical meaning.
- Thresholds are illustrative until the doctor signs them off.
- Trust: FHIR high, local medium, self-reported low, missing side none. One side missing and the present side high: severity low, auto-resolved. Present side medium or low: severity moderate, human review. Both sides low: severity low, human review.
- The Local Store stores and returns rows and does no clinical work. The adapter makes local and FHIR rows look the same (source-blind).

## STEP 4: Viva questions and answers

1. **What is your module?** The interaction layer: how the interview asks, how answers are checked, how two records are compared, and how much each source is trusted.
2. **Why is unknown never no?** Silence could hide a danger. We store unknown, flag it, and the level cannot go down.
3. **How does reconciliation decide a conflict?** Same patient, nearest reading within 48 hours, difference above a fixed threshold. It does not decide who is right.
4. **Why are the thresholds not clinical?** They are illustrative until the doctor signs them off. The report says so.
5. **What are trust levels for?** To decide whether a human must look.
6. **How do you know the danger-phrase detector works?** On the team set: 83 of 83 danger phrases found and 0 of 56 negated phrases raised. The team wrote that set. My independent set (H-1) gave: (fill in your real TP, FN, FP, TN).
7. **What did you personally change?** Read `git log --author="Hassaan" --oneline` and answer only with those commits.
8. **What bug or gap did you find?** (Fill in from H-2, H-3, H-4.)
9. **What would you do with another week?** Add the doctor's changes to the bank, widen the Urdu phrases, test with real patient wording.
10. **What does the Local Store not do?** It never interprets, scores or reconciles.

## STEP 5: Tell Usman when each pull request is merged

Usman then updates the report: the contribution table, Chapter 8 and the AI log tables. Send him a list: task id, pull request number, one line of result.

## STEP LOG: AI log in the repo (do this after every task)

The repo file `docs/ai-usage/hassaan.md` and the table in the report (Section 8.7) must be identical. The file `ai-usage-hassaan.md` next to this guide is the current version, copied from the report. Steps:

```powershell
git checkout dev
git pull origin dev
git checkout -b docs/hassaan-ai-usage
copy <path>\ai-usage-hassaan.md docs\ai-usage\hassaan.md
# open docs\ai-usage\hassaan.md and fix any row that is not true for you
git add docs/ai-usage/hassaan.md
git commit -m "docs: Hassaan AI usage log"
git push -u origin docs/hassaan-ai-usage
```

Rules for the rows:
- Dates written as `2026-08` mean "that month, exact day not recorded". Replace with the exact date when you know it.
- **Delete any row that did not happen to you, and add any that is missing.** Tell Usman the final table so the report matches. A log that is true and short is better than a long one that is not.
- For each new task below, add a row: date, tool, what you asked (the prompt above in one sentence), what it gave, what you checked or changed, file used in.
