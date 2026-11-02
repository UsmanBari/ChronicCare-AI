# ChronicCare AI — Week 3 (2 – 8 Nov 2026) — Hassaan

> **This is the only file you need this week.** It has the short refresh, the daily workflow, how your work gets checked, all 7 Antigravity prompts, who does what, and the full project handbook (Appendix A, with a new "STATE ON 2 NOV" section at its top).
> **Give the whole file to your AI first** ("read this whole file; it's the context for everything I'll ask"), then paste one day's prompt at a time.
> Save it in the repo as `docs/tasks/WEEK3_HASSAAN.md` (Part 1.3). Every prompt tells the agent to read it from there.

**Your focus this week:** turn last week's backend work into screens a patient and a doctor can actually use, and close the interview gaps that don't need a doctor. In order: finish OCR v1 (#96) and the bug-bash issues → the patient risk card and "Why this result?" box → the provider risk/explanation/decision-trace view → v3 interview readiness (close the non-doctor gaps, measure v2 vs v3) → end-to-end and accessibility checks → OCR hardening on realistic Pakistani lab formats → a user guide, final Urdu review and your weekly log.

**The goal:** **Sun 8 Nov is "features done".** **Tue 10 Nov is code freeze** (only bug fixes, tests and docs after that). The FYP-1 final evaluation is **Tue 17 Nov**. Everything that should be in the demo must be merged by Sunday night. A screen that works in English and Urdu with honest tests beats three half-screens.

**What changed since last week (read this before Day 1)**
- Schema is **v15** now (v13 waist, v14 your record_edits, v15 Usman's risk/explanation/trace + guideline_chunks). You add **no** migration this week. If you think you need one, stop and ask Usman.
- `ORCHESTRATOR=direct|graph` exists (Usman's LangGraph orchestrator, #93). Both must behave identically; the end gates run the backend suite in both modes.
- The check-in completion now returns optional `risk` and `explanation` (patient view), and the review detail returns `checkin_risk`, `explanation`, `trace` (provider view). The contract you build on is **`docs/API_RISK_EXPLAIN.md`**. The old live `risk` field on the review detail (#90, the provider risk panel) stays exactly as it is.
- A bare "no" is no longer read as glucose 9 (#95).
- **New rules from Week 2 reviews:** never merge a PR (Usman merges); never delete branches; PR numbers only from `gh pr list` output; every number in a doc must trace to a file or command output. Weekly logs with invented numbers were sent back last week.

**The rules that matter most** (the full list is in Appendix A, Part 0):
1. The app never diagnoses, never gives a dose or treatment advice, and never lowers a triage level. "The model proposes, the rules decide."
2. Never weaken a test to make it pass. Never hand-type a result table.
3. No secrets, no data and no real patients, anywhere: Git, chats, screenshots.
4. Protected safety files are hashed before and after every day. They change only when the prompt says so (this week: never, for you).
5. Every patient-facing string has English **and** Urdu. Numbers and units go in `<bdi>` in RTL.
6. "NOT DONE" and "NOT RUN" are fine answers. A false "done" is not.

**Contents**
- Part 1: Refresh (10 minutes)
- Part 2: How every day works
- Part 3: How Usman checks your work
- Part 4: The 7 daily prompts
- Appendix B: Who does what this week
- Appendix A: The full project handbook (with "STATE ON 2 NOV")

---

## Part 1 — Before Day 1: refresh (about 10 minutes)

### 1.1 Finish last week first
Your Day 7 PR **#96 (OCR v1)** still has Correction 2 open (merge dev, the Render build-command fix, the memory measurement, two doc facts). **Day 1 starts by finishing it.** Usman merges #96 before you start Day 2.

### 1.2 Update your clone
```powershell
git status                      # must be clean
git fetch origin --prune
git switch dev
git pull
git log -1 --oneline            # the latest dev merge (#98 or newer)
```
Never commit to `dev` or `main`. Every day: a new branch and a PR into `dev`. **Don't delete old branches** (Usman's rule).

### 1.3 Put this file in the repo
Save this file as `docs/tasks/WEEK3_HASSAAN.md`. It's committed in your Day 1 PR.

### 1.4 Re-install (requirements changed: langgraph, pillow)
```powershell
$env:PYTHONIOENCODING = "utf-8"
cd backend-poc-technical
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python init_local_db.py           # schema v15
cd ..
npm install
```
Backend suite (repo root, venv active), expect about 1,470+ passed:
```powershell
python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"
```
OCR (only for Day 6): use the separate venv and the recipe from your Correction 2 (`requirements-ocr.txt` + the headless OpenCV fix). Never install OCR packages into the backend venv's `requirements.txt`.

### 1.5 Things you do by hand this week (not the AI)
- **Tuesday evening:** read every Urdu string the agent added for the risk card and explanation box and fix the wording. You're the native-speaker reviewer; the PR says "Urdu reviewed by: Hassaan".
- **Thursday:** run 10 real check-ins yourself on v3 in Urdu and Roman Urdu (local, fake account) and write down anything that sounds wrong or confusing. Paste your notes into the Day 4 PR.
- **Friday:** 5 fake printed lab reports in common Pakistani layouts (a big-chain lab style, a hospital lab style, a small clinic printout). Make them in Word/Docs with the name "Test Patient", print or screenshot them, and photograph 2 with your phone. Type the true values into the ground-truth file. **No real reports, ever.**
- **Sunday:** the final read-through of every new Urdu string in the app (Day 7 lists them).

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
2. **Watch the terminal commands.** Never approve `git push --force` to `dev`/`main`, `gh pr merge`, deleting branches, deleting files outside the task, or `.github/` edits beyond the pytest list.
3. **Check its claims yourself.** Run the tests in your own terminal, at least once a day.
4. **Understand the diff** (`git diff dev`). You'll be asked about this code in the viva.
5. **Log your AI use** in `docs/ai-usage/hassaan.md` (the agent appends a line; you check it's true).

**If the agent gets stuck or the session dies:** new chat, same day's prompt, plus at the top: "Continue on the existing branch `<branch>`. Run `git log dev..HEAD --oneline` and `git status` first, then tell me what's already done before doing anything else."

**If yesterday's PR isn't merged yet:** branch today's work from yesterday's branch (the pre-flight handles this) and say so in the PR.

---

## Part 3 — How Usman checks your work (so you know what passes)

1. **CI** must be green on every PR.
2. **Usman checks out your branch** and re-runs the gates himself on Python 3.11 (in a clean venv, like CI):
   ```powershell
   git fetch origin
   git switch <your-branch>
   git log dev..HEAD --format="%an %ae %s"
   git diff dev --stat
   ```
3. **The checklist:** only allowed files changed; protected hashes unchanged; no data or secrets; new tests in CI; every number reproduces; Urdu for every new string; commits under your name; the backend suite passes in BOTH orchestrator modes.
4. **Claude reviews the PR** line by line against the day's prompt, re-runs what it can, and writes a correction prompt if anything is wrong. You paste it into the same chat; the agent fixes it on the same branch.
5. **Merge:** Usman merges into `dev`. Branches are kept.

**A PR gets sent back if:** a claim has no pasted output; a test was weakened; a protected file changed; English-only patient text; files outside the list changed; data in Git; an invented number, PR number, function name or doctor statement; you can't explain the change.

---

## Part 4 — The 7 daily Antigravity prompts

Paste **one day per new Antigravity chat**: everything inside the grey block, from `YOUR TASK` to the end.

| Day | Date | Focus | Branch | PR title |
|---|---|---|---|---|
| 1 | Mon 2 Nov | Finish #96, then bug-bash issues #85 #86 #88 + interview gap G-12 | `fix/i3-bugbash-h` | I3 Day 1: bug-bash fixes (#85 #86 #88) + roman_ur profile language |
| 2 | Tue 3 Nov | Patient risk card + "Why this result?" explanation box | `feat/i3-patient-risk-explain-ui` | I3 Day 2: patient risk card + explanation box (flags off) |
| 3 | Wed 4 Nov | Provider view: check-in risk, explanation, decision trace | `feat/i3-provider-trace-ui` | I3 Day 3: provider check-in risk + explanation + decision trace |
| 4 | Thu 5 Nov | v3 readiness: close non-doctor gaps (G-02, G-14 Roman Urdu), v2 vs v3 report | `feat/i3-v3-readiness` | I3 Day 4: v3 readiness (gaps G-02, G-14) + go/no-go report |
| 5 | Fri 6 Nov | End-to-end journeys + accessibility on the new screens | `test/i3-e2e-a11y` | I3 Day 5: end-to-end journeys + accessibility |
| 6 | Sat 7 Nov | OCR memory fix (must fit Render) + hardening on Pakistani lab layouts | `feat/i3-ocr-hardening` | I3 Day 6: OCR memory fix + hardening (Pakistani lab layouts) |
| 7 | Sun 8 Nov | Features done: user guide, final Urdu review, screenshots, weekly log | `docs/i3-user-guide-final` | I3 Day 7: user guide + final Urdu review + weekly log |

---

### DAY 1 — Monday 2 Nov — Finish #96, then bug-bash fixes + roman_ur profile language

```text
YOUR TASK (DAY 1, HASSAAN): (0) finish PR #96 (OCR v1) with the open Correction 2, on its own branch, and STOP for Usman; then (1) fix three non-safety bug-bash issues (#85, #86, #88) each with a failing-then-passing regression test, and (2) close interview gap G-12 (the profile API rejects "roman_ur"). Branch for (1)-(2): fix/i3-bugbash-h, from dev AFTER Usman merges #96 (if #96 isn't merged by the time you start (1), branch from feat/i2-5-ocr-v1 and say so).

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

PART 0 — Finish PR #96 (branch feat/i2-5-ocr-v1)
 Do Correction 2 exactly as Usman sent it (it is in your chat history; if not, ask Usman for HASSAAN_DAY7_CORRECTION2.txt): merge dev (keep every file in the ci.yml pytest line), fix the Render build command with the tested recipe in a CLEAN Python 3.11 venv (pin numpy too), measure backend RSS (flag off / first OCR call / peak), fix the diastolic range in OCR_DESIGN.md (30-160) and delete "All 7 milestones..." from your weekly log. Gates, push, STOP. Show Usman the report. Start Part A only after he says "go".

READ FIRST (Part A): the three GitHub issues (gh issue view 85; gh issue view 86; gh issue view 88; paste their text), docs/INTERVIEW_AUDIT.md row G-12, data_sources/app_store.py (ALLOWED_LANGUAGES and every place it's used), main.py (the profile model and PUT /api/me/profile), app/translations/index.ts, and the components each issue names.

PART A — Bug-bash fixes (one commit per issue: "fix(<area>): <what> (closes #NN)")
 For EACH issue:
  1. write a FAILING regression test that reproduces it (vitest for UI, pytest for API); run it and paste the failure
  2. fix it with the smallest change
  3. run the test again and paste the pass
 A1. #85 "Observation input card does not update unit label when profile preferred unit is mmol/L": the label and the placeholder follow the profile's glucose unit; the value sent to the API is converted exactly as the existing unit logic does (reuse it; the 18.0 factor lives in one place only, find it with Select-String). Test both units, en + ur.
 A2. #86 "Microphone permission rejection in Urdu displays raw English NotAllowedError": map NotAllowedError, NotFoundError, NotReadableError and "unknown" to translated messages (en + ur) with a next step ("allow the microphone in browser settings" / "type your answer instead"). Never show the raw error name. Test each mapping in Urdu.
 A3. #88 "EHR Sandbox disconnection leaves stale high-trust provenance badges until hard refresh": after disconnect, the record view refetches and badges show the new source/trust straight away. Test: connected record shows the EHR badge; disconnect; the badge disappears without a reload.

PART B — Interview gap G-12 (roman_ur profile language)
 B1. ALLOWED_LANGUAGES gains "roman_ur" (data_sources/app_store.py is not protected). Check every reader of the language value (Select-String "language" in main.py, steps.py, interview_v3_runner.py, rag/explainer.py) and list what each does with "roman_ur". Anything that would break (e.g. a lookup that only knows en/ur): fall back to "en" for that feature and say so; never crash.
 B2. The profile screen offers Roman Urdu as a third choice (en + ur labels).
 B3. Tests: PUT /api/me/profile with "roman_ur" -> 200 and stored; an invalid language -> 422 (unchanged); a v3 check-in with a roman_ur profile asks its first question in Roman Urdu; the explanation step (with EXPLAIN_ENABLED=true and a fake LLM) gets a language it supports or falls back to English (test it, don't guess).
 B4. docs/INTERVIEW_AUDIT.md: mark G-12 FIXED with the commit and the test name.

ACCEPTANCE
 H3-1-00 #96 Correction 2 done and pushed (separate branch), Usman told
 H3-1-01 #85, #86, #88: each failing test shown, then fixed, then passing; closing commits
 H3-1-02 "roman_ur" accepted by the profile API; every language reader checked and listed; no crash path
 H3-1-03 Urdu for every new string; no raw error text shown to patients
 H3-1-04 Protected hashes identical; all gates green in both ORCHESTRATOR modes

FILES ALLOWED
Part A/B: the components each issue needs (list them in your plan; Usman approves), app/translations/index.ts, app/lib/api.ts (only if needed), backend-poc-technical/data_sources/app_store.py (ALLOWED_LANGUAGES only), backend-poc-technical/main.py (profile model only, if needed), new tests (tests/*.test.tsx, backend-poc-technical/test_profile_roman_ur.py), docs/INTERVIEW_AUDIT.md, docs/tasks/WEEK3_HASSAAN.md (this file), docs/ai-usage/hassaan.md, .github/workflows/ci.yml (pytest list)
PR TITLE: I3 Day 1: bug-bash fixes (#85 #86 #88) + roman_ur profile language
```

---

### DAY 2 — Tuesday 3 Nov — Patient risk card + "Why this result?" explanation box

```text
YOUR TASK (DAY 2, HASSAAN): when the flags are on, a patient sees two new things after a check-in: a small risk card (advisory band + reasons, never a probability) and a "Why this result?" box (2-4 plain sentences with sources). With the flags off, the screens look exactly as today. You build on the contract in docs/API_RISK_EXPLAIN.md; you change NO backend code. Branch: feat/i3-patient-risk-explain-ui.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

READ FIRST: docs/API_RISK_EXPLAIN.md (all of it: every state and the wording rules), docs/RISK_PANEL.md (the provider panel's wording, so the patient card is consistent but simpler), the check-in result screens (find which component renders the /complete response: Select-String "complete" in app/lib/api.ts and app/components/*.tsx; likely RiskResultScreen.tsx, RoutedToReviewScreen.tsx, ConfirmationScreen.tsx, EmergencyScreen.tsx), app/components/RiskBadge.tsx, app/lib/api.ts (the complete-response type), app/translations/index.ts, tests/no-fake-values.test.tsx and tests/honest-labels.test.ts (the rules you must not break).

PART A — Types
 A1. app/lib/api.ts: add the optional `risk` and `explanation` fields to the complete-response type, EXACTLY as docs/API_RISK_EXPLAIN.md defines them (copy field names from the doc's JSON examples; paste the Select-String lines you copied from). All optional; old responses (no fields) must still type-check.

PART B — The patient risk card (component app/components/PatientRiskCard.tsx)
 B1. Shown only when the response has risk with status "ok" AND the check-in is NOT an emergency. States from the contract: ok (band + up to 3 reasons), not_enough_information (one line: what's missing, e.g. "add your waist size in your profile"), null (render nothing), error (render nothing; no error shown to the patient).
 B2. Wording rules (from the contract): the header says it's advisory and not a diagnosis; never a percentage or number; one line "Ask your doctor whether you need a sugar test (HbA1c)" only if the contract's text says so (copy, don't invent). en + ur, RTL, `<bdi>` around any value.
 B3. Badge: text + icon, never colour alone (same accessible pattern as RiskBadge.tsx).

PART C — The "Why this result?" box (component app/components/ExplanationBox.tsx)
 C1. Shown when explanation exists and isn't error. Collapsed by default with a button "Why this result?" (en + ur); expands to the sentences and a sources line formatted like "ADA 2026, Section 6" exactly as the contract shows. Template-mode explanations show the same way (no "AI" wording either way).
 C2. Emergency: never shown (the emergency screen stays exactly as today).
 C3. Keyboard: the button toggles with Enter/Space, aria-expanded set, focus stays on the button.

PART D — Wire into the result screens
 D1. Insert the two components into the result screen(s) for routine/review/urgent outcomes, below the existing result, without moving anything else. Emergency screen untouched.
 D2. Demo mode: if the app has a demo/presenter mode, it may show a FIXED example from docs/API_RISK_EXPLAIN.md, labelled "Example"; live mode never shows a fixed example.

PART E — Tests (vitest; new file tests/patient-risk-explain.test.tsx)
 - flags off (no fields): result screens render exactly as before (snapshot of the key text, or assert the new components are absent)
 - each risk state: ok, not_enough_information, null, error
 - no number or "%" anywhere in the patient card (assert with a regex on the rendered text)
 - explanation collapsed by default; expands; sources rendered; template mode renders
 - emergency response with risk/explanation present -> neither component renders
 - Urdu: dir="rtl", values in <bdi>, Nastaliq font class as the app uses
 - live mode never shows the fixed example

PART F — Screenshots: docs/screenshots/w3/patient_risk_en.png, patient_risk_ur.png, explanation_en.png, explanation_ur.png (local, flags on, fake patient). Plus one with flags off showing the screen unchanged.

ACCEPTANCE
 H3-2-01 Types match the contract (Select-String evidence); old responses still type-check
 H3-2-02 Risk card: every contract state handled; no probability or number shown (test)
 H3-2-03 Explanation box: collapsed/expand, sources, template mode, keyboard (tests)
 H3-2-04 Emergency screen unchanged; flags off = no visible change (tests + screenshot)
 H3-2-05 en + ur screenshots; "Urdu reviewed by: Hassaan" in the PR after your evening review
 H3-2-06 No backend change; protected hashes identical; all gates green

FILES ALLOWED
Create: app/components/PatientRiskCard.tsx, app/components/ExplanationBox.tsx, tests/patient-risk-explain.test.tsx, docs/screenshots/w3/*. Change: app/lib/api.ts (types), the result screen component(s) you list in your plan, app/translations/index.ts, docs/ai-usage/hassaan.md.
NOT allowed: any backend file.
PR TITLE: I3 Day 2: patient risk card + explanation box (flags off)
```

---

### DAY 3 — Wednesday 4 Nov — Provider view: check-in risk, explanation, decision trace

```text
YOUR TASK (DAY 3, HASSAAN): on the provider's review detail, a clinician sees (1) the risk as it was AT THE CHECK-IN (checkin_risk: band, model name/version, raised yes/no, caveats; NO percentage, per docs/RISK_PANEL.md section 3), next to the existing live risk panel; (2) the explanation the patient saw, with its mode and any rejected reasons; (3) a compact decision timeline (the trace: node, time, summary). Flags off = nothing new appears. No backend change. Branch: feat/i3-provider-trace-ui.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

READ FIRST: docs/API_RISK_EXPLAIN.md (provider sections), docs/RISK_PANEL.md, docs/ORCHESTRATOR.md (node names and what each summary means), app/components/provider/PatientDetailScreen.tsx and ReconciliationAlertDetail.tsx (wherever the review detail renders; the existing risk panel and your recent-record-edits block), app/lib/api.ts (ReviewDetailResponse), tests/provider-risk-panel.test.tsx (don't break it).

PART A — Types: ReviewDetailResponse gains optional checkin_risk, explanation, trace exactly as the contract defines (Select-String evidence). The existing `risk` field is untouched.

PART B — "Risk at check-in" block
 B1. Only when checkin_risk exists. Shows the band (Low/Moderate/High badge, same as the live panel), model name + version, NO percentage or decimal anywhere (docs/RISK_PANEL.md section 3: "No Raw Percentages"; paste the Select-String line), "Raised this check-in to review: yes/no", caveats as text chips (home_bp_not_exam_bp, not_validated_pakistan: translate each to a plain sentence, en + ur).
 B2. Labelled clearly as "at the time of this check-in" vs the existing live panel "today". If both exist and differ, show both; never merge them.
 B3. status not_enough_information / error -> a one-line note, no numbers.

PART C — "What the patient was told" block: the explanation sentences + sources + mode (llm / template) + rejected_reasons (as a small list, provider only). Hidden when null.

PART D — "Decision timeline" block
 D1. A vertical list of trace steps: node name in plain words (map each node from ORCHESTRATOR.md to a label, e.g. "decide_triage" -> "Rules decided the level"), duration in ms, and the summary text (counts and levels only; it never contains readings or names, by design; don't add any).
 D2. Collapsed to the first 3 steps with "Show all steps".
 D3. If a step's summary contains an emergency short-cut, show it with an icon + text "Emergency path: reconciliation skipped".

PART E — Tests (vitest; tests/provider-trace.test.tsx)
 - all three blocks absent when the fields are missing (flags off)
 - checkin_risk vs live risk shown separately with their labels
 - no percentage or probability number rendered anywhere, provider or patient (regex on the rendered text)
 - raised yes/no, caveats translated, en + ur
 - timeline: node labels mapped, collapse/expand, emergency step labelled
 - the existing provider-risk-panel tests still pass unchanged

PART F — Screenshots: docs/screenshots/w3/provider_checkin_risk_en.png, provider_trace_en.png, provider_trace_ur.png.

ACCEPTANCE
 H3-3-01 Types per contract; existing `risk` untouched
 H3-3-02 Three blocks render every state; absent when flags off (tests)
 H3-3-03 Live vs check-in risk never merged; labels clear
 H3-3-04 Timeline readable, collapsible, emergency step labelled
 H3-3-05 en + ur; screenshots; no backend change; gates green

FILES ALLOWED
Create: tests/provider-trace.test.tsx, app/components/provider/DecisionTimeline.tsx (or similar; name it in your plan), docs/screenshots/w3/*. Change: app/components/provider/PatientDetailScreen.tsx and/or ReconciliationAlertDetail.tsx, app/lib/api.ts (types), app/translations/index.ts, docs/ai-usage/hassaan.md.
PR TITLE: I3 Day 3: provider check-in risk + explanation + decision trace
```

---

### DAY 4 — Thursday 5 Nov — v3 readiness: close the non-doctor gaps + go/no-go report

```text
YOUR TASK (DAY 4, HASSAAN): give Usman the evidence to decide whether the v3 interview becomes the default on Friday. Close the two open interview gaps that don't need a doctor (G-02 unclear adherence answers; G-14 Roman Urdu caregiver phrases), then produce a measured v2-vs-v3 readiness report against the checklist in docs/INTERVIEW_AUDIT.md section 6. You do NOT switch the default. Branch: feat/i3-v3-readiness.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

READ FIRST: docs/INTERVIEW_AUDIT.md (sections 3 and 6), agents/interview_v3_runner.py, agents/interview_planner.py, agents/answer_understanding.py (parse_yes_no and the yes/no lists), scripts/run_v3_personas.py, scripts/engine_equivalence.py, scripts/eval_all_phrase_sets.py, test_sim_personas.py, test_engine_equivalence.py, docs/INTERVIEW_V3_FLOW_RULES.md.
NOTE: caregiver detection currently lives partly in input_triage.py (PROTECTED). You may NOT change it. If G-14 can't be done without touching it, do it in answer_understanding.py / interview_v3_runner.py (not protected), or write NOT DONE with the reason.

PART A — G-02: unclear adherence answers
 A1. Answers like "maybe", "shayad", "pata nahi", "kal tha", "kabhi kabhi", "not sure", "یاد نہیں" to an adherence question must NOT count as adherent. They get ONE clarification question (en/ur/roman_ur, from messages.json; add the strings), and if still unclear, the adherence slot is recorded as "unclear" and the check-in goes to review (needs_review), never silently "adherent".
 A2. Tests (backend-poc-technical/test_v3_adherence_unclear.py): each phrase above -> clarification asked; a clear "haan"/"yes" after it -> adherent; still unclear -> "unclear" + review; a clear "no" -> missed-dose reason asked (unchanged behaviour).
 A3. Check whether v2 has the same gap. v2 lives in adaptive_interview_agent.py (PROTECTED): don't change it; describe the v2 behaviour with a probe and list it under OPEN QUESTIONS.

PART B — G-14: Roman Urdu / Urdu caregiver phrases
 B1. "ammi ki taraf se", "abbu ke liye", "main apni walida ke liye jawab de raha hoon", "میں اپنی امی کی طرف سے", and 5 more you write yourself -> answered_by="caregiver", confidence Medium, exactly like the English path.
 B2. Tests for each phrase + 5 look-alikes that must NOT trigger (e.g. "ammi ne kaha tha dawai lo" is not a caregiver statement).

PART C — The readiness report (script + doc)
 C1. scripts/v3_readiness_report.py runs, for BOTH engines: all personas (run_v3_personas), the engine-equivalence scenarios, every phrase set in tests/sim (via eval_all_phrase_sets), and a "no English leak" scan of every v3 patient-facing string in ur and roman_ur. It prints one table per checklist item: item | v2 | v3 | PASS/FAIL | evidence.
 C2. docs/V3_READINESS.md: the generated tables, then a plain go/no-go per checklist item. Items that need a doctor (15g wording G-06, LO/HI G-18, no-readings G-21) are marked "WAITING FOR DOCTOR" with the doctor-pack decision number. Any v3 triage DEMOTION vs v2 on any persona is an automatic NO-GO for that item; list each case.
 C3. Your Thursday by-hand notes (10 real check-ins in Urdu/Roman Urdu) pasted as a section "Native speaker check", with what you fixed in messages.json and what you couldn't.

ACCEPTANCE
 H3-4-01 G-02 fixed in v3 with tests; v2 behaviour described (not changed)
 H3-4-02 G-14 Roman Urdu/Urdu caregiver phrases + look-alikes tested, no protected file changed
 H3-4-03 Readiness tables generated by the script, both engines, every checklist item
 H3-4-04 Demotions listed case by case; doctor items marked WAITING
 H3-4-05 Native-speaker notes included; gates green in both modes

FILES ALLOWED
Change: backend-poc-technical/agents/interview_v3_runner.py, agents/interview_planner.py, agents/answer_understanding.py, agents/interview_bank/messages.json, docs/INTERVIEW_AUDIT.md, docs/ai-usage/hassaan.md, .github/workflows/ci.yml (pytest list). Create: backend-poc-technical/test_v3_adherence_unclear.py, backend-poc-technical/test_v3_caregiver_roman_ur.py, scripts/v3_readiness_report.py, docs/V3_READINESS.md.
NOT allowed: any protected file (including input_triage.py and adaptive_interview_agent.py), main.py.
PR TITLE: I3 Day 4: v3 readiness (gaps G-02, G-14) + go/no-go report
```

---

### DAY 5 — Friday 6 Nov — End-to-end journeys + accessibility

```text
YOUR TASK (DAY 5, HASSAAN): prove the main user journeys work end to end in a real browser, and that the screens built this week and last week are accessible. You add browser tests that run locally (not in CI unless they're fast and need no network) and an accessibility report. You fix only small, non-safety UI problems you find; anything bigger becomes an issue. Branch: test/i3-e2e-a11y.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

READ FIRST: docs/ACCESSIBILITY_CHECK.md (last round's method), docs/system_test_cases.md (ST-01..20), the Playwright note in the environment (if `npx playwright --version` works use it; otherwise install @playwright/test as a DEV dependency only, and say how big it is), app/page.tsx and the demo/presenter mode (how to reach screens without real Firebase sign-in).

PART A — Five journeys (Playwright, tests-e2e/ folder, run with `npx playwright test`; backend on 127.0.0.1:8000 with a fresh local DB and fake data; no real Firebase: use the app's existing demo/test path, or a test-only token mechanism that ALREADY exists; never add an auth bypass to production code)
 J1. New patient: consent -> profile (en, then switch to ur) -> first check-in with normal readings -> routine result
 J2. Check-in with a high BP reading -> urgent result screen; the emergency number text is present
 J3. Record: add a medicine, change its dose, open History, export JSON
 J4. (flags on: RISK_ENABLED, EXPLAIN_ENABLED with a fake/template explainer) patient sees the risk card + "Why this result?"; provider opens the review and sees check-in risk + timeline
 J5. (OCR_ENABLED with OCR_PROVIDER=fake) upload -> confirm 2, fix 1, remove 1 -> saved with the OCR badge
 Each journey: screenshots at the key steps into docs/screenshots/w3/e2e/, en and ur for J1 and J4. If a journey can't run, NOT RUN with the exact reason.

PART B — Accessibility (axe-core via @axe-core/playwright as a DEV dependency, or the browser extension with screenshots)
 B1. Scan: result screens (incl. the new risk card + explanation box), provider review detail (new blocks), HealthRecordScreen (history panel, import preview, OCR confirm), profile, trends. Report violations by impact.
 B2. Keyboard-only pass on the same screens: tab order, visible focus, Esc closes panels, no focus traps. Screen-reader labels on icon buttons.
 B3. Mobile width 360 px: no horizontal scroll, buttons at least 44 px.
 B4. docs/ACCESSIBILITY_CHECK_W3.md: a table screen | check | PASS/FAIL | evidence (screenshot or axe output). Fix the serious/critical ones that are small (labels, contrast tokens, focus); list the rest as GitHub issues with the label w3-a11y (paste the links).

ACCEPTANCE
 H3-5-01 Five journeys scripted; each PASS with screenshots or NOT RUN with the reason
 H3-5-02 No auth bypass added to production code
 H3-5-03 axe results + keyboard + 360 px checks per screen, in a table
 H3-5-04 Small serious/critical issues fixed with tests; the rest filed as issues (links)
 H3-5-05 Dev dependencies only; CI unchanged unless the e2e run is fast and offline (say which)

FILES ALLOWED
Create: tests-e2e/**, playwright.config.ts, docs/ACCESSIBILITY_CHECK_W3.md, docs/screenshots/w3/e2e/*. Change: package.json + package-lock.json (DEV dependencies only), small a11y fixes in app/components/** that you list in the plan, app/translations/index.ts, docs/ai-usage/hassaan.md.
PR TITLE: I3 Day 5: end-to-end journeys + accessibility
```

---

### DAY 6 — Saturday 7 Nov — OCR memory fix + hardening on realistic Pakistani lab layouts

```text
YOUR TASK (DAY 6, HASSAAN): first make OCR fit in Render's 512 MB (Part 0), then make OCR v1 read the kinds of printed lab reports patients in Pakistan actually have. Using your 5 fake reports (made by hand on Friday, "Test Patient", no real data), measure the current extractor, fix what it misses, and report before/after numbers. OCR stays behind OCR_ENABLED=false. Branch: feat/i3-ocr-hardening.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

READ FIRST: backend-poc-technical/data_sources/ocr/extract_fields.py and its tests, docs/OCR_DESIGN.md (incl. your Correction 2 recipe), docs/ocr/compare_results.md, ocr_spike/run_compare.py (the scoring), the ground-truth format in ocr_spike/samples/.

PART 0 — Memory first (OCR can't be switched on until this passes)
 Measured on 2 Nov in a clean Python 3.11 Linux venv with your requirements-ocr.txt recipe: your doc says 70 MB idle -> 227 MB after the first OCR call -> 436 MB peak (76 MB headroom). Usman's re-run (TestClient, same photo, 3 uploads) got about 469 MB resident after the first call and a sampled peak near 600 MB. Either way, Render's 512 MB free tier would be at or over its limit, especially with LangGraph loaded or two uploads at once.
 0.1 Write scripts/measure_ocr_memory.py: a fresh process, import main, then N=5 uploads of rx_photo_01.jpg through TestClient; RSS sampled every 50 ms; print idle / after first call / steady after 5 / peak. Run it 3 times, paste all raw outputs.
 0.2 Try, one at a time, and re-measure after each (keep only what helps, and say what each change did):
     a) ONNX Runtime session options inside the provider: 1 intra-op thread, 1 inter-op thread, memory arena and memory pattern OFF (check what rapidocr_onnxruntime 1.4.4 lets you pass: read its source in the venv and paste the relevant lines; don't guess parameter names)
     b) downscale to max 1280 px on the long side before OCR (then re-check the handwriting medicine recall on the 4 photos: it must stay 9/9, or report the drop)
     c) run the OCR call in a short-lived subprocess (multiprocessing with spawn, one task, then the worker exits), so the backend's own memory returns to idle after each upload; measure the extra latency
 0.3 Target: peak <= 300 MB and idle back near 70-90 MB after an upload. Write the before/after table in docs/OCR_DESIGN.md 6.3 and a plain recommendation for Usman: "safe to enable on Render free tier: yes/no". If no option gets there, say so; OCR then stays off in production for FYP-1.
 0.4 Tests (fake provider): the subprocess path returns the same result shape; a crashing worker -> 502 ocr_provider_error; a hanging worker -> timeout -> 502 (inject a short timeout).

PART A — New samples
 A1. Add your 5 fake reports (3 screenshots/prints + 2 phone photos, max 1600 px, EXIF stripped) under ocr_spike/samples/pk_labs/ with ground truth (full_text + fields) typed by YOU. Confirm in the PR that they're fake and made by you.
 A2. Typical things to cover: "HbA1c 7.8 %" vs "Glycosylated Hb", "FBS"/"RBS"/"Fasting Blood Sugar" in mg/dL and mmol/L, "B.P 140/90", reference ranges printed next to values (must NOT be read as the value), units on the next line, tables with columns Test | Result | Unit | Reference.

PART B — Measure, fix, re-measure (RapidOCR in the separate OCR venv; fake provider for unit tests)
 B1. Before: run the scoring on pk_labs with the current extractor: field recall/precision per field kind, plus every miss with the OCR snippet near it (generated by the script).
 B2. Fix extract_fields.py for the misses (never guess a value; a reference range must never become the value). One test per new case in the extractor tests.
 B3. After: same scoring; paste both tables. Also re-run the OLD samples: no regression allowed (paste).
 B4. If a field can't be read reliably, the confirm screen must show it as "Low" confidence (test).

PART C — Docs: docs/ocr/pk_labs_results.md (generated tables, sample count, plain statement that 5 fake reports is a small sample).

ACCEPTANCE
 H3-6-01 5 fake Pakistani-layout samples with hand-typed ground truth
 H3-6-02 Before/after tables generated; misses listed with snippets
 H3-6-03 Reference ranges never read as values (tests); no regression on old samples
 H3-6-00 Memory table (3 runs, each option) + yes/no recommendation for Render
 H3-6-04 OCR_ENABLED default false unchanged; gates green

FILES ALLOWED
Create: backend-poc-technical/ocr_spike/samples/pk_labs/**, docs/ocr/pk_labs_results.md, scripts/measure_ocr_memory.py. Change: backend-poc-technical/data_sources/ocr/rapidocr_provider.py, backend-poc-technical/main.py (OCR upload route only, for the subprocess path), backend-poc-technical/test_ocr_upload.py, backend-poc-technical/data_sources/ocr/extract_fields.py, its tests, backend-poc-technical/ocr_spike/run_compare.py (scoring only), docs/OCR_DESIGN.md, docs/ai-usage/hassaan.md.
PR TITLE: I3 Day 6: OCR memory fix + hardening (Pakistani lab layouts)
```

---

### DAY 7 — Sunday 8 Nov — Features done: user guide, final Urdu review, screenshots, weekly log

```text
YOUR TASK (DAY 7, HASSAAN): it's "features done" day. Finish any open review fixes from Days 1-6 first (on their own branches). Then write a short user guide for patients and providers with real screenshots, do the final native-speaker review of every Urdu string added in Weeks 2-3, and write your weekly log. No new features today. Branch: docs/i3-user-guide-final.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK3_HASSAAN.md. Read Part 0 of it and the "STATE ON 2 NOV" section at its top before doing anything. Where the old handbook text and "STATE ON 2 NOV" disagree, "STATE ON 2 NOV" wins.
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

READ FIRST: this week's merged PRs (gh pr list --author @me --state all --limit 30 --json number,title,state,mergedAt: paste it), app/translations/index.ts, agents/interview_bank/messages.json, docs/URDU_REVIEW_LIST.md, scripts/find_untranslated.py.

PART A — docs/USER_GUIDE.md (en; with an Urdu summary section)
 A1. Patient: sign up, consent, profile (units, waist, language), a check-in (what each result means; what "review" means; the emergency screen), the risk card and "Why this result?" (advisory, not a diagnosis), records (add/edit, history, export/import), OCR upload (when enabled). One screenshot per step from docs/screenshots (real, fake data).
 A2. Provider: review queue, review detail (live risk vs check-in risk, explanation, timeline, recent record edits), actions.
 A3. A "What the app does NOT do" box (no diagnosis, no doses, never lowers a level, not validated in Pakistan yet).

PART B — Final Urdu review
 B1. scripts/find_untranslated.py (run it; paste output) + a list of every Urdu/Roman Urdu string added since 26 Oct (git log -p since that date on translations/index.ts and messages.json, generated by a script).
 B2. You read them all and fix the wording. docs/URDU_REVIEW_LIST.md gets a "Week 3 review" section: string key | old | new | why. Mark "Urdu reviewed by: Hassaan (native speaker)".

PART C — docs/weekly/2026-W45-hassaan.md (one page)
 Done (your PRs from the pasted gh output only), numbers (tests added this week, e2e journeys passing, a11y issues fixed/filed, OCR before/after recall), what slipped and why, items waiting on a doctor, next week (freeze week) top 3. Anything you can't trace: "NOT TRACED".

ACCEPTANCE
 H3-7-01 User guide with real screenshots, patient + provider, Urdu summary
 H3-7-02 Untranslated scan clean (or each remaining item explained); review table filled
 H3-7-03 Weekly log with only traced numbers and real PR numbers
 H3-7-04 No feature code changed; gates green

FILES ALLOWED
Create: docs/USER_GUIDE.md, docs/weekly/2026-W45-hassaan.md, a script to list new strings (scripts/list_new_strings.py). Change: app/translations/index.ts and agents/interview_bank/messages.json (wording only, no key changes), docs/URDU_REVIEW_LIST.md, docs/ai-usage/hassaan.md.
PR TITLE: I3 Day 7: user guide + final Urdu review + weekly log
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
- `scripts/mysql_preflight.py` is NOT read-only: it runs the migration and creates/drops a temp table. Never run it against production before a deploy (older text below says to; that's wrong). Before a deploy use the read-only check (`scripts/prod_schema_readonly.py`, added in Week 3); run preflight once after.
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
