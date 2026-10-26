# ChronicCare AI — Week 2 (26 Oct – 1 Nov 2026) — Hassaan

> **This is the only file you need this week.** It has the one-time setup, the daily workflow, how your work gets checked, all 7 Antigravity prompts, who does what, and the full project handbook (Appendix A).
> **Give the whole file to your AI first** ("read this whole file; it's the context for everything I'll ask"), then paste one day's prompt at a time.
> Save it in the repo as `docs/tasks/WEEK2_HASSAAN.md` (Part 1.5). Every prompt tells the agent to read it from there.

**Your focus this week:** the adaptive interview (v3 answer understanding, the dual-diagnosis flow, full Urdu and Roman Urdu) and patient records (OCR and edit history).

**The goal:** the FYP-1 final evaluation is on **Tue 17 Nov**, and by then the project should be about 65–70% of the full FYP. Nothing has been cut for the earlier date: the same scope now fits in 3 weeks instead of 5, with features finished by 8 Nov and a code freeze on 10 Nov. So each day carries more, and there's no slack. Every day's work must be real, tested, reviewed and merged. A day that's 80% done with honest evidence beats one that claims 100% with no proof.

**The rules that matter most** (the full list is in Appendix A, Part 0):
1. The app never diagnoses, never gives a dose or treatment advice, and never lowers a triage level. "The model proposes, the rules decide."
2. Never weaken a test to make it pass. Never hand-type a result table.
3. No secrets, no data and no real patients, anywhere: Git, chats, screenshots.
4. Protected safety files are hashed before and after every day. They change only when the prompt says so.
5. Every patient-facing string has English **and** Urdu.
6. "NOT DONE" and "NOT RUN" are fine answers. A false "done" is not.

**Contents**
- Part 1: Refresh your setup (you already have the repo)
- Part 2: How every day works
- Part 3: How Usman checks your work
- Part 4: The 7 daily prompts
- Appendix B: Who does what this week
- Appendix A: The full project handbook

---

## Part 1 — Before Day 1: refresh your existing setup (about 20 minutes)

You already have the repo cloned and you've merged PRs before (Mid-1: PRs #49–#63). Nothing gets re-installed from scratch. The repo has moved on since your last PRs (13 Oct): the 5 clinician-approved rule changes (#64), the load tests (#65), the system test results (#67), Dr Anam Zafar's 14 Oct review notes, the height/weight unit toggles and the README rewrite (16 Oct). So bring everything up to date and prove it still runs.

### 1.1 Check your git identity is the one you used before
```powershell
git config --global user.name
git config --global user.email
```
The email must be the one on your earlier commits, so GitHub keeps counting them as yours: `i230536@isb.nu.edu.pk`. Your earlier commits used two different names (`hassaan07mudassar` and `Muhammad Hassaan Mudassar`). Pick one and keep it this week:
```powershell
git config --global user.name "<the name you choose>"
```
Also check line endings: `git config --global core.autocrlf true`.

### 1.2 Clean up and update your clone
In your existing clone folder:
```powershell
git status                      # must be clean. If not, commit or stash your old work first.
git fetch origin --prune
git switch dev
git pull
git log -1 --oneline            # should show the latest dev commit (16 Oct or newer)
git branch --merged dev         # your old Mid-1 branches. Delete them locally:
git branch -d <old-branch>      # one by one, never with -D
```
**Never commit to `dev` or `main` directly.** Every day's work goes on a new branch and a PR into `dev`.

### 1.3 Tools: only what's new
| Tool | Check | If missing |
|---|---|---|
| Python **3.11** | `py -3.11 --version` | CI uses 3.11. If your venv was made with another version, delete `backend-poc-technical\.venv` and recreate it (1.5). |
| Node 20 (18 OK) | `node -v` | |
| **GitHub CLI** (new: lets the agent open PRs) | `gh --version` then `gh auth status` | Install it from https://cli.github.com, then run `gh auth login` |
| **Antigravity** | open it | |
| WSL + Ubuntu (optional) | `wsl -l -v` | Skip it. The prompts write "WSL NOT RUN". |

### 1.4 Put this file in the repo
Save this file as `docs/tasks/WEEK2_HASSAAN.md` in your clone. Every day's prompt tells the agent to read it from there. It gets committed in your Day 1 PR.

### 1.5 Re-install dependencies (the requirements changed since 13 Oct)
**Backend** (terminal 1, from the repo root):
```powershell
$env:PYTHONIOENCODING = "utf-8"
cd backend-poc-technical
.venv\Scripts\Activate.ps1        # or create it first: py -3.11 -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
# .env: keep your existing one. Compare it with .env.example and add any NEW keys (never paste values anywhere).
python init_local_db.py           # schema is now v12
uvicorn main:app --reload --port 8000
```
Then check http://127.0.0.1:8000/api/health (it should show `healthy`).

**Backend tests** (terminal 2, at the repo root, with the venv active):
```powershell
python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test"
```
Expect about 744 passed and 0 failed. At Mid-1 it was around 694, and the clinician-rule PRs added more. Screenshot the result for Usman.

**Frontend** (terminal 3, at the repo root):
```powershell
npm install          # package-lock changed since 13 Oct
npm test
npm run dev          # http://localhost:3000
```

If PowerShell refuses to run `Activate.ps1`, run this once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. If `pip` isn't recognised, use `python -m pip`.


### 1.6 Hassaan-only notes
- **No dataset downloads.** Your work uses only the repo and fake data.
- **For Day 5 (OCR)** the agent may need extra packages for the spike only. They go into the venv with `python -m pip install ...` and **never** into `backend-poc-technical/requirements.txt` until Day 7 says so. Tesseract on Windows is a separate installer (https://github.com/UB-Mannheim/tesseract/wiki). Tick "Urdu" under additional languages if you want to try it.
- **Groq key (Days 5 and 7, optional).** If you test the Groq vision option, put the key in `backend-poc-technical\.env` only. It is never pasted into a chat, a commit or a screenshot. Ask Usman for a key; don't use one from an old message.
- **Urdu fonts.** The site uses Noto Nastaliq Urdu (see `app/globals.css`). If Urdu looks like boxes in your terminal, that's the terminal, not the app; check in the browser.

---

## Part 2 — How every day works

```
Morning: fix yesterday's review comments (correction prompt from Usman) → merge
         git switch dev; git pull
Day:     paste today's prompt into a NEW Antigravity chat → agent does pre-flight + plan → you type "go"
         you watch: approve plans, read diffs, stop it if it touches files outside the list
Evening: agent runs the gates, pushes, opens the PR (or gives the compare link)
         you read the diff yourself, then send Usman the PR link
Night:   Usman + Claude review → correction prompt arrives for the morning
```

**Your job while the agent works**
1. **Read its plan before typing "go".** If it lists a file that isn't in today's allowed list, say no.
2. **Watch the terminal commands.** Never approve `git push --force`, pushes to `dev` or `main`, deleting files outside the task, or edits to `.github/` beyond what the prompt allows.
3. **Check its claims yourself.** Run the tests in your own terminal, at least once a day.
4. **Understand the diff.** Run `git diff dev`. You'll be asked about this code in the viva, and "the AI wrote it" isn't an answer.
5. **Log your AI use** in `docs/ai-usage/<your-name>.md`. The prompts tell the agent to append a line, but you check it's true.

**If the agent gets stuck or the session dies**
- Start a new chat, paste the same day's prompt, and add at the top: "Continue on the existing branch `<branch>`. Run `git log dev..HEAD --oneline` and `git status` first, then tell me what's already done before doing anything else."

**If yesterday's PR isn't merged yet**
- Branch today's work from yesterday's branch. The prompt's pre-flight handles this. Mention it in the PR.

---

## Part 3 — How Usman checks your work (so you know what passes)

1. **CI** runs on every PR. It must be green.
2. **Usman checks out your branch** and runs:
   ```powershell
   git fetch origin
   git switch <your-branch>
   git log dev..HEAD --format="%an %ae %s"
   git diff dev --stat
   ```
   Then he runs the tests and the commands your PR says you ran.
3. **The checklist:**
   - only allowed files changed
   - protected-file hashes unchanged (unless allowed)
   - no data or secrets
   - new tests listed in CI
   - every number in the PR reproduces
   - Urdu present for every new string
   - commits under your name
4. **Claude reviews the PR** from the public repo. It clones your branch, re-runs what it can, checks the diff line by line against the day's prompt, and writes a **correction prompt** if anything is wrong. You paste that into the same Antigravity chat; the agent fixes it on the same branch and the PR updates.
5. **Merge:** squash or merge into `dev`, then delete the branch. Once a week `dev` goes to `main`, which deploys the live site.

**A PR gets sent back if:**
- a claim has no pasted output
- a test was weakened
- a protected file changed without permission
- there's English-only patient text
- files outside the list were changed
- there's data in Git
- you can't explain the change

---

## Part 4 — The 7 daily Antigravity prompts

Paste **one day per new Antigravity chat**: everything inside the grey block, from `YOUR TASK` to the end. Don't edit the prompts. If something is unclear, ask Usman.

| Day | Date | Focus | Branch | PR title |
|---|---|---|---|---|
| 1 | Mon 26 Oct | Refresh check + interview audit (v2 vs v3, 40+ real probes) | `docs/i2-4-interview-audit` | I2-4 Day 1: interview audit (v2 vs v3, 40+ probes) |
| 2 | Tue 27 Oct | v3 answer understanding + fix the dead fasting/sick-day branches | `feat/i2-4-v3-answer-understanding` | I2-4 Day 2: v3 answer understanding + slot filling |
| 3 | Wed 28 Oct | v3 dual-diagnosis flow, de-duplication, caregiver, summary | `feat/i2-4-v3-dual-diagnosis` | I2-4 Day 3: v3 dual-diagnosis flow + caregiver + summary |
| 4 | Thu 29 Oct | v3 fully in Urdu and Roman Urdu + blind Urdu phrase test | `feat/i2-4-v3-urdu-complete` | I2-4 Day 4: v3 complete in Urdu and Roman Urdu |
| 5 | Fri 30 Oct | OCR spike (3 options) + OCR and edit-history designs + bug bash | `feat/i2-5-ocr-spike` | I2-5 Day 5: OCR spike + OCR and edit-history designs |
| 6 | Sat 31 Oct | Record edit history (schema v13, API, UI) + record export (JSON/FHIR) and import with preview | `feat/i2-5-edit-history` | I2-5 Day 6: record edit history (schema v13) + record export/import |
| 7 | Sun 1 Nov | Build OCR v1 behind a flag + weekly log | `feat/i2-5-ocr-v1` | I2-5 Day 7: OCR v1 behind a flag |

**Things you do by hand, not the AI:**
- **Monday evening:** write 30 Urdu-script phrases yourself, 15 danger and 15 safe or negated, into `tests/sim/danger_phrases_independent_hassaan_ur.json`. Use the same format as `tests/sim/danger_phrases_independent_saad.json`: a list of `{"text": ..., "expected_danger": true/false}`. **Don't look at the detector's code or phrase lists first.** That's what makes the test independent. Commit it on the Day 4 branch.
- **Thursday evening:** read every Urdu and Roman Urdu line the agent wrote and fix the wording yourself. You are the native-speaker reviewer, and the PR says so.
- **Friday:** take 3–5 phone photos of fake handwritten prescriptions with a made-up name. Type out what each one says for the agent.
- **Any time this week:** wireframes (paper or Figma) for the risk card, trend arrows, the "Why this result?" box and the OCR confirm screen. Put photos or exports in `docs/wireframes/` in the Day 7 PR.

---

### DAY 1 — Monday 26 Oct — Refresh check + interview audit

```text
YOUR TASK (DAY 1, HASSAAN): an evidence-backed audit of the adaptive interview. You show exactly what v2 (production, INTERVIEW_ENGINE=v2) and v3 (behind the flag, INTERVIEW_ENGINE=v3) do today, by running real check-ins through the real API in-process and by reading the code. Today you change NO application code. Branch: docs/i2-4-interview-audit.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

READ FIRST (in full)
- docs/tasks/WEEK2_HASSAAN.md: Appendix A (handbook), Part 0, C5, C6, C15.
- backend-poc-technical/main.py: the check-in routes (/api/checkins/start, /answer, /complete). Note where INTERVIEW_ENGINE is read (os.environ.get("INTERVIEW_ENGINE", "v2"), around line 2455). It's read per request, so you can switch engines between probe runs in the same process by setting os.environ.
- backend-poc-technical/test_checkin_api.py and backend-poc-technical/conftest.py: how tests create a signed test user, give consent, confirm inclusion, set the profile and run a check-in. Reuse EXACTLY this approach. Don't invent a new auth bypass and don't disable auth.
- backend-poc-technical/agents/interview_v3_runner.py (start_v3_session, next_turn, finish_v3_session)
- backend-poc-technical/agents/interview_planner.py (plan_next_step, detect_historical_trends)
- backend-poc-technical/agents/answer_validation.py (_parse_number_words, validate_glucose_input, validate_bp_input)
- backend-poc-technical/agents/interview_bank/*.json and loader.py
- docs/CLINICAL_RULES.md sections 5, 7, 8, 10, 11; docs/CLINICIAN_RESPONSES.md; docs/INDEPENDENT_PHRASE_RESULTS_saad.md; docs/INTERVIEW_V3_SIM_REPORT.md

WHY THIS MATTERS
Days 2–4 rebuild how v3 understands answers, orders questions and speaks Urdu. Production can only move from v2 to v3 when v3 is at least as safe as v2 on every danger phrase and protocol. Today's audit is the baseline and the to-do list. Every claim in it must point at a line of code or a probe result.

PART A — Refresh check (pre-flight step 5 covers most of it)
Also run "npm run build" once and print the result. If anything fails on your freshly updated dev, STOP after the report. Don't fix it.

PART B — Probe tool: scripts/probe_interview.py
1. Runs scripted check-ins IN-PROCESS: FastAPI TestClient against the real app, a temporary SQLite file created with init_local_db's functions, and test tokens built the same way as in conftest.py / test_checkin_api.py. Nothing touches the live site or production DB.
2. CLI:
     python scripts/probe_interview.py --engine v2|v3|both --scenario <name>|all --out <file.md> [--json <file.json>]
3. For each scenario it:
   - creates a fresh test patient
   - grants both consents, confirms inclusion, and sets the profile (conditions, language, on_insulin_or_sulfonylurea, date_of_birth so that age = 45 unless the scenario says otherwise, sex_at_birth)
   - starts a check-in, then sends the scripted answers one by one. If the server asks something the script didn't plan for, it answers from the scenario's "fallback" list, or "I don't know", and RECORDS that it did so.
   - records per turn: step id, the question text exactly as served, why_text, options, can_skip, the answer sent, and the flags (complete, emergency, escalation_recorded, any system_note)
   - calls /complete (unless it ended in an emergency) and records: triage_level, reasons, factors, requires_review, max_severity, each intake's confidence_label, and any answered_by field
4. Output: one markdown section per scenario with a turn table and a result line, plus a summary table at the top (scenario | engine | questions asked | final level | emergency | notes). Optional JSON for machine comparison.
5. Windows: write files with encoding="utf-8". Don't print Urdu through a console that can't show it; write it to the file.

PART C — Scenarios: scripts/probe_scenarios.json (40 or more)
Each entry: name, group, conditions, language (en|ur|roman_ur), on_insulin, age, answers[], fallback[], what_we_are_testing.
Groups (cover every bullet):
 a) Normal: DM only (en, ur, roman_ur); HTN only (en, ur, roman_ur); both (en, ur, roman_ur).
 b) Dual-diagnosis order: both conditions, normal answers. Record the exact step order and whether any slot is asked twice.
 c) Unclear answers: "maybe", "shayad", "pata nahi", "پتہ نہیں", "kal tha", "👍", "...", "same as yesterday", "ok".
 d) Yes/no variants on a yes/no question: "haan", "ji", "jee haan", "bilkul", "han ji", "nahi", "nahin", "na", "bilkul nahi", "ہاں", "نہیں", "jee nahi", "thora sa", "kabhi kabhi", "no problem", "I don't know".
 e) Numbers in words and formats: "ek sau bees", "one hundred and twenty", "ek sau baais", "do sau tees", "ایک سو بیس", "120 by 80", "120 over 80", "ek sau bees bata assi", "120-80", "120 80", "١٢٠/٨٠", "۱۲۰/۸۰".
 f) Units: "6.5 mmol", "117 mg", a bare "7", a bare "45", "HI", "LO", "12/10" (date-like).
 g) Fasting and sick day: "haan aaj roza hai", "yes I am fasting", "ulti aur dast ho rahe hain", "I have diarrhoea and vomiting". Record whether the fasting and sick-day FOLLOW-UP questions (fasting.json and sick_day.json items with requires) are EVER asked under v3.
 h) Caregiver: "I am answering for my mother", "main apni ammi ki taraf se bata raha hoon", and a NON-caregiver trap: "my mother also has diabetes".
 i) Normal readings plus "yes" to sick day / foot problem / low sugar last week / associated symptoms (the known gap in CLINICAL_RULES.md section 8).
 j) All 30 phrases from tests/sim/danger_phrases_independent_saad.json, each given as the first free-text answer.
 k) "dil ki dharkan bohat tez hai", "I have palpitations", "I can't speak properly", "zabaan larkhara rahi hai".
 l) Off-topic: chitchat, abuse, a prompt-injection attempt, a dose request ("can I double my metformin"), and 4 off-topic answers in a row.
 m) Protocol triggers (to confirm parity): BP 185/125 then "no symptoms"; glucose 45 mg/dL with "I feel confused"; glucose 320.

PART D — Run it
  python scripts/probe_interview.py --engine both --scenario all --out docs/audit/interview_probe_day1.md --json docs/audit/interview_probe_day1.json
Print the summary table in the chat.

PART E — Phrase test, both engines
1. python scripts/eval_phrase_set.py tests/sim/danger_phrases_independent_saad.json
   NOTE: this measures ONLY the v3 screen (agents/input_triage.screen_multilingual_danger_phrases).
2. The v2 result for the same 30 phrases comes from group (j) of the probe (the production patterns in adaptive_interview_agent.run_stage1_red_flag_screen and the BP crisis check).
3. Print a side-by-side table: phrase | expected | v2 detected (category) | v3 detected (category) | agree?

PART F — Code reading checklist. Confirm or refute each item, with file:line quotes:
 1. interview_v3_runner.next_turn never writes yes/no answers into known_slots (only glucose_reading, bp_reading and missing_reading are written). So interview_planner.plan_next_step's checks known_slots.get("is_fasting_today") and known_slots.get("sick_vomiting_diarrhea") can never be true, and the fasting.json / sick_day.json follow-ups can never be asked. Prove it with the probe output from group (g).
 2. English-only patient text hard-coded in the v3 path: the unit clarification "Did you mean X mmol/L or X mg/dL?" with its why_text and options; the emergency system_note; the possible-low guidance; the summary options "Yes, submit" / "Need to change something". List every one, with file:line.
 3. The possible-low guidance tells the patient to "consume 15g fast-acting sugar". This is treatment advice, against the handbook's no-advice rule. Record it as a gap with "needs doctor decision". Do NOT change it.
 4. why_text exists only in English for all 37 bank items (there are no why_text_ur / why_text_roman_ur keys).
 5. _parse_number_words: list what it parses and what it can't (Roman Urdu 21–99 such as "baais", "ikattis", "pachpan"; "do sau tees"; "one hundred and twenty"; Urdu-script number words).
 6. v2 serves its questions in English only, even for an Urdu profile (CLINICAL_RULES.md section 7 says the interview is English only). Prove it from the probe.
 7. Anywhere an unclear answer could become a "no" or a safe value.
 8. Budget: base 8, expands to 12 when "concerning", hard_cap 14. Confirm the actual numbers in the code, and whether the progress_hint ever disagrees with the questions actually asked.

PART G — docs/INTERVIEW_AUDIT.md
- Summary: gap counts by category, and how many need a doctor.
- Gap table: ID (G-01…) | Gap | Category (understanding / slot-filling / dual-diagnosis / language / danger phrases / safety wording / doctor decision / budget) | Engine (v2 / v3 / both) | Evidence (file:line or probe scenario + turn) | Proposed fix (one line, no clinical content) | Day fixed (2/3/4/later) | Needs doctor? | Priority (P1 = safety or blocks a v3 switch, P2, P3)
- The side-by-side phrase table from Part E.
- "Works correctly": things you checked that pass, with evidence.
- "v3 production readiness checklist": what must be true before Usman switches production to v3:
  - danger-phrase parity with v2 or better on every phrase set
  - identical levels on every protocol scenario (group m)
  - all personas pass with no level lowered
  - test_engine_equivalence.py passing
  - no English-only patient text
  - the treatment-advice line decided by a doctor
  - Urdu reviewed by a native speaker
- You write NO medical wording and NO thresholds. Write "needs doctor decision" instead.

TRAPS
- conftest.py has an autouse fixture (manage_require_inclusion). The probe must handle inclusion properly, just as the API tests do.
- Engine switching: set os.environ["INTERVIEW_ENGINE"] before /start for each scenario, and reset it afterwards.
- One fresh patient per scenario. Otherwise the 14-day baseline and recent-history logic leak between scenarios.
- Write NO new danger patterns today, even if a miss is obvious. Record the miss as a gap.

ACCEPTANCE
 H1-01 Pre-flight and refresh check outputs pasted (pytest, npm test, npm run build)
 H1-02 The probe runs 40+ scenarios under both engines with no crash (summary table pasted)
 H1-03 Phrase table, v2 vs v3, pasted
 H1-04 Each of the 8 code-reading items has a verdict with file:line
 H1-05 INTERVIEW_AUDIT.md complete, with the readiness checklist
 H1-06 Protected-file hashes unchanged; no app code changed (git diff dev --stat shows only allowed files)
 H1-07 All end gates pass, or any pre-existing failure is shown as already failing in the baseline

FILES ALLOWED
Create: scripts/probe_interview.py, scripts/probe_scenarios.json, docs/INTERVIEW_AUDIT.md, docs/audit/interview_probe_day1.md, docs/audit/interview_probe_day1.json, docs/tasks/WEEK2_HASSAAN.md (this file, if it isn't committed yet)
Append: docs/ai-usage/hassaan.md (date, what the AI did, what you checked yourself)
Nothing else.

PR TITLE: I2-4 Day 1: interview audit (v2 vs v3, 40+ probes)
```

---

### DAY 2 — Tuesday 27 Oct — v3 answer understanding + slot filling

```text
YOUR TASK (DAY 2, HASSAAN): make v3 understand patients' answers the way Pakistani patients actually answer, in English, Roman Urdu and Urdu script. Make every yes/no slot the planner depends on get filled, so the fasting and sick-day follow-ups finally work. Production stays on v2. Branch: feat/i2-4-v3-answer-understanding.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: you MAY change backend-poc-technical/agents/answer_validation.py (only a thin wrapper and routing, as described below) and backend-poc-technical/agents/interview_v3_runner.py (NOT a protected file, but safety-relevant). Every other protected file stays byte-identical.

READ FIRST: docs/INTERVIEW_AUDIT.md (Day 1); the gaps marked "Day fixed: 2"; interview_v3_runner.py; answer_validation.py; interview_planner.py; interview_bank/*.json (every item whose answer_type is "yes_no", and every "requires" key); test_mutation_proofs_v3.py; scripts/verify_mutations.py.

THE RULE OF THE DAY: MORE ACCURATE, NEVER LESS CAUTIOUS
- A word you can't map with confidence stays "unknown".
- Nothing may turn an unclear answer into "no", "normal" or a safe value.
- If a change would make any persona's final level LOWER, that's a blocker: stop and report it.

PART A — New module: backend-poc-technical/agents/answer_understanding.py (pure functions, no I/O, no network, stdlib only)

A1. normalise_text(text) -> str
   - Unicode NFKC; Arabic → Urdu letters (ي→ی, ك→ک, ه→ہ where appropriate, ى→ی)
   - remove tatweel (ـ) and Urdu diacritics (zer, zabar, pesh, etc.)
   - Eastern Arabic and Urdu digits → ASCII (reuse answer_validation._EASTERN_DIGITS_TABLE by importing it; don't copy it)
   - collapse spaces; lower-case Latin only
   - unit tests for each

A2. parse_yes_no(text, lang=None) -> dict
   Returns {"value": "yes" | "no" | "unknown", "partial": bool, "evidence": <exact substring of the ORIGINAL text>, "confidence": "High" | "Medium" | "Low", "matched_rule": <rule id>}
   Word-boundary matching only ("know" must not match "no"; "nahin" must not match inside another word).
   - YES (High): yes, yeah, yep, yup, sure, of course, correct, right, I am, I do, I did, I have, haan, han, haanji, han ji, ji haan, jee haan, bilkul, zaroor, ہاں، جی ہاں، بالکل، ضرور
   - NO (High): no, nope, nah, not really, I am not, I don't, I didn't, I haven't, never, nahi, nahin, nai, na (ONLY as a whole answer or the first word, NOT the tag-question "na" at the end: "theek hai na?" stays unknown), ji nahi, jee nahi, bilkul nahi, kabhi nahi, نہیں، جی نہیں، بالکل نہیں، کبھی نہیں
   - "ji" / "jee" / "جی" ALONE → yes, Medium (it can be a polite acknowledgement)
   - Partial (value yes, partial true, Medium): thora sa, thoda, kabhi kabhi, sometimes, a little, a bit, تھوڑا، کبھی کبھی
   - Unknown (High): pata nahi, pta nahi, maloom nahi, معلوم نہیں, پتہ نہیں, I don't know, dont know, not sure, idk, shayad, maybe, perhaps, شاید
   - Traps:
     - "no problem", "no worries", "not bad" → NOT "no" (rule: phrase list checked before single words). Map "not bad" → unknown.
     - "I don't know" contains "no": the unknown phrases must be checked BEFORE the no-words.
     - Double negatives ("nahi aisa nahi hai") → unknown, Low.
     - Mixed ("haan... actually nahi") → the LAST clear statement wins, Medium, with both pieces in the evidence.
     - Emoji: 👍 → yes Low; 👎 → no Low; anything else → unknown.
     - An empty or whitespace answer → unknown.

A3. parse_number(text) -> {"value": float | None, "evidence": str, "kind": "digits" | "words" | None}
   - Digits after normalise_text, including decimals with "." or ",".
   - English words: zero … nineteen, tens, "hundred", "and", "a hundred", "one twenty" (= 120), "two thirty" (= 230).
   - Roman Urdu / Hindustani 0–100 IN FULL, including the irregular 21–99. Write the full table explicitly in code, with common spelling variants (ikkees/ikkis, baais/bais, teis/tees? careful: tees = 30, teis = 23; chaubees, pachchees/pachees, chhabbees, sattais, atthais, untees, ikattis, battees, taintees, chautees, paintees, chhattees, saintees, adtees, untaalees, chaalees/chalis, iktaalees, bayaalees, taintaalees, chawalees, pentaalees, chhiyaalees, saintaalees, adtaalees, unchaas, pachaas, ikyaavan, baavan, tirpan, chauvan, pachpan, chhappan, sattaavan, atthaavan, unsath, saath, iksath, baasath, tirsath, chausath, painsath, chhiyaasath, sarsath, adsath, unhattar, sattar, ikhattar, bahattar, tihattar, chauhattar, pachhattar, chhihattar, sathattar, athattar, unaasi, assi, ikyaasi, bayaasi, tiraasi, chauraasi, pachaasi, chhiyaasi, sattaasi, athaasi, navaasi, nabbe, ikyaanve, baanve, tiraanve, chauraanve, pachaanve, chhiyaanve, sattaanve, atthaanve, ninyaanve). A test for EVERY number 0–100 with its main spelling.
   - Hundreds: "ek sau", "aik sau", "do sau", "teen sau" + remainder ("ek sau baais" = 122, "do sau tees" = 230), "sau" alone = 100. "so" counts as hundred ONLY when the answer has a number word before it ("ek so bees"). English "so" in a sentence must not become 100.
   - Urdu-script words: ایک دو تین چار پانچ چھ سات آٹھ نو دس … بیس تیس چالیس پچاس ساٹھ ستر اسی نوے سو, and compounds like ایک سو بیس.
   - Ambiguous (two different numbers when one was expected, "ek do sau", "120 ya 130") → value None, kind None.
   - Dates and times must not be read as readings ("12/10", "subah 8 baje", "8am").

A4. parse_bp(text) -> {"value": [sys, dia] | None, "evidence": str}
   Accepts: "120/80", "120 / 80", "120 by 80", "120 over 80", "120-80", "120 80", "120 bata 80", "ek sau bees bata assi", "ek sau bees by assi", "١٢٠/٨٠", "۱۲۰/۸۰".
   Rejects: systolic <= diastolic; values outside the ranges already in the code (import the existing constants; don't type new numbers); three or more numbers; a single number.

A5. Every function returns its evidence substring from the ORIGINAL text, for the clinician record.

PART B — Wire into v3 (interview_v3_runner.next_turn)
B1. For every bank item (and probe) whose answer_type == "yes_no", call parse_yes_no and store:
    known_slots[slot] = True | False | "unknown"
    known_slots[slot + "__evidence"] = evidence
    known_slots[slot + "__partial"] = partial
B2. In interview_planner.plan_next_step, make sure "requires: true" conditions are satisfied ONLY by the boolean True, never by "unknown" or a truthy string. Read the code, then fix it if needed with the smallest change.
B3. A safety-class item answered "unknown": re-ask ONCE with a clarification. The text for it comes from the bank's responses or a new messages entry in all 3 languages. If you add a message, add en, ur and roman_ur, marked needs_native_review. If it's still unknown, keep "unknown", set needs_clinician_flag, and move on.
B4. Readings: before validate_glucose_input / validate_bp_input, run parse_number / parse_bp. Pass the cleaned numeric text on, so EVERY existing safety behaviour still applies unchanged:
    - unit clarification for 2–40 and 41–54 with no unit
    - possible-severe-low flags
    - ranges
    - mmol/L ×18.0
B5. answer_validation._parse_number_words becomes a thin wrapper around answer_understanding.parse_number (same signature and return type), so existing callers keep working. Change nothing else in answer_validation.py.
B6. Don't change any patient-facing wording today, except new clarification messages from B3.

PART C — Tests (add every new file to the ci.yml pytest list)
C1. backend-poc-technical/test_answer_understanding.py: 250+ table-driven cases with pytest.mark.parametrize:
    - normalise_text: digits, Arabic vs Urdu letters, diacritics
    - parse_yes_no: every rule above, every trap, all three languages
    - parse_number: every number 0–100 in Roman Urdu (one parametrized table), hundreds, English words, Urdu-script words, ambiguity, dates and times
    - parse_bp: every accepted format, every rejection
C2. backend-poc-technical/test_v3_slot_filling.py (end to end through start_v3_session / next_turn):
    - a fasting patient: "haan aaj roza hai" → fasting follow-up IS asked; "nahi" → NOT asked; "pata nahi" → NOT asked, stored as unknown
    - sick day: "ulti aur dast ho rahe hain" or "haan" → sick-day follow-up asked; "nahi" → not
    - a safety-class item answered "pata nahi" twice → unknown + needs_clinician_flag
    - "ek sau bees bata assi" stored as [120, 80]; "do sau tees" glucose → 230
    - a bare "7" still triggers unit clarification (unchanged)
C3. Mutation proofs: add them to scripts/verify_mutations.py the same way existing ones are written (read it first). Each must be KILLED by a test:
    M-H2-1 "pata nahi" mapped to "no"
    M-H2-2 "unknown" satisfies requires:true
    M-H2-3 parse_bp accepts systolic <= diastolic
    M-H2-4 the unit clarification skipped for a bare "7"
    M-H2-5 the tag-question "na" read as "no"
    Print the mutation summary before and after.

PART D — Regression evidence
D1. python scripts/run_v3_personas.py → all personas complete. Print a table: persona | expected level | final level BEFORE (dev) | final level AFTER (branch). Every change gets a reason. Any level that went DOWN is a blocker: stop.
D2. python -m pytest backend-poc-technical/test_engine_equivalence.py -q
D3. Re-run the Day 1 probe: python scripts/probe_interview.py --engine v3 --scenario all --out docs/audit/interview_probe_day2.md. Print a diff summary vs Day 1 (scenarios whose question list or result changed).
D4. Update docs/INTERVIEW_AUDIT.md: mark the gaps fixed today (status + evidence link). Add any new gap you found.

TRAPS
- Word boundaries in every regex (\b doesn't work for Urdu script: use explicit whitespace or punctuation boundaries, or token lists).
- Tokenise once and match phrases (multi-word) before single words.
- Don't make parse_yes_no clever with sentiment. It's a lookup with explicit rules.
- Persona expected levels in tests/sim/*.json are NOT to be edited, even if a test fails. Report it instead.

ACCEPTANCE
 H2-01 answer_understanding.py exists, pure, stdlib only; 250+ tests pass
 H2-02 Fasting and sick-day follow-ups are proven reachable (and not reachable on "nahi" / "pata nahi")
 H2-03 requires:true is satisfied only by True (test)
 H2-04 5 new mutations, all killed; mutation summary pasted
 H2-05 Personas: no level lowered (table pasted)
 H2-06 Equivalence test passes
 H2-07 Probe diff vs Day 1 pasted; audit updated
 H2-08 Protected hashes: only answer_validation.py changed (thin wrapper); everything else identical
 H2-09 All end gates green

FILES ALLOWED
Create: backend-poc-technical/agents/answer_understanding.py, backend-poc-technical/test_answer_understanding.py, backend-poc-technical/test_v3_slot_filling.py, docs/audit/interview_probe_day2.md
Change: backend-poc-technical/agents/interview_v3_runner.py, backend-poc-technical/agents/interview_planner.py (requires check only), backend-poc-technical/agents/answer_validation.py (wrapper only), backend-poc-technical/agents/interview_bank/responses.json or a new messages entry (B3 only), scripts/verify_mutations.py (append mutations), .github/workflows/ci.yml (pytest list), docs/INTERVIEW_AUDIT.md, docs/ai-usage/hassaan.md

PR TITLE: I2-4 Day 2: v3 answer understanding + slot filling
```

---

### DAY 3 — Wednesday 28 Oct — Dual diagnosis, de-duplication, caregiver, summary

```text
YOUR TASK (DAY 3, HASSAAN): a patient with BOTH type 2 diabetes and hypertension gets ONE clean v3 interview: readings first, no slot asked twice, shared symptoms asked once, medicines and lifestyle asked once, a correct progress count, and a summary covering both conditions that the patient can correct. The caregiver path works end to end. Production stays v2. Branch: feat/i2-4-v3-dual-diagnosis.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: you may change interview_planner.py, interview_v3_runner.py, the interview_bank JSON (METADATA ONLY: never wording, can_raise_level, rule_id, source or priority_class), interview_bank/loader.py, and the persona definitions used by scripts/run_v3_personas.py (ADD personas only; never edit existing ones). main.py ONLY for the caregiver field described in Part C, and only after you show the exact diff in your plan.

READ FIRST: docs/INTERVIEW_AUDIT.md (gaps marked Day 3); docs/INTERVIEW_V2_3_DESIGN.md §1.3 (v2's dual-diagnosis behaviour); docs/INTERVIEW_V3_RESEARCH_AND_DESIGN.md §3–6; interview_planner.py in full; interview_v3_runner.py in full; every bank module; where main.py turns the v3 session state into intakes for /complete (search for finish_v3_session and the v3 branch around the INTERVIEW_ENGINE check).

PART A — Write the rules first: docs/INTERVIEW_V3_FLOW_RULES.md
Write these in plain words, with a worked example for each case (DM only; HTN only; both; both + fasting; both + caregiver; both + a correction at the summary). Then implement EXACTLY them:
 R1 Safety-class items first (unchanged).
 R2 Then readings. For dual diagnosis, ask BOTH readings before any symptom question. Order:
    - if the recent history or record shows one condition was abnormal more recently, ask that reading first
    - otherwise glucose first
 R3 Then symptoms. A symptom that serves both conditions (dizziness, headache, blurred vision, tiredness, chest discomfort probes) is asked ONCE, and the answer fills every slot it serves.
 R4 Medication adherence: asked ONCE, covering all active medicines. Per-medicine follow-up only if the patient says they missed something.
 R5 Lifestyle and wellbeing: once, last.
 R6 Probes drill into the newest finding but never repeat an asked slot. A probe slot that serves both conditions is asked once.
 R7 Budget: a shared question counts ONCE. progress_hint shows the true asked count and the current budget, every turn.
 R8 Summary confirmation: lists both conditions' captured values, in the session language. "Need to change something" lets the patient pick ONE slot to correct; that slot is re-asked; then the summary is shown again. At most 2 correction rounds, then submit with a note.
 R9 Caregiver: once the session is marked answered_by=caregiver, it stays so. Questions use the caregiver variant if the bank has one (e.g. caregiver.json); otherwise the normal text, with the session note "answers are from a caregiver". Confidence is lowered by one level. The clinician sees answered_by.
 R10 A single-condition patient's flow must not change, except where a Day 2/3 fix requires it. Prove this with the equivalence test and a before/after question list.

PART B — Implement
- If the bank needs to know which slots serve both conditions, add a metadata field "also_fills": [...] (or "shared": true) to the relevant items. loader.py reads it, with a default for items that don't have it.
- The de-duplication guard lives in ONE place (the planner), with a comment pointing to R3/R6.
- The caregiver trap: "my mother also has diabetes" is family history, NOT a caregiver. Check input_triage's THIRD_PARTY_PATTERNS behaviour: if it would misfire, record it as a gap for Usman. Do NOT edit input_triage.py.

PART C — Carry answered_by to the result
- Find where main.py builds intakes from the v3 state for /complete. Make sure answered_by and the lowered confidence reach the stored result and the provider review detail. Make the smallest additive change (a new optional field), shown in your plan first.

PART D — Personas and tests
D1. Add 10+ personas (follow the existing persona format exactly): dual_normal_ur, dual_normal_roman_ur, dual_both_high, dual_glucose_low_bp_normal, dual_bp_crisis_first (must give EXACTLY today's emergency/urgent result), dual_fasting, dual_sick_day, dual_caregiver_roman_ur, dual_changes_answer_at_summary, dual_unclear_everything, dual_record_contradiction, family_history_not_caregiver. Expected levels: copy what today's rules produce, and mark each "expected level set by rules, needs doctor review". Don't invent clinical outcomes.
D2. backend-poc-technical/test_v3_dual_flow.py (add to CI):
    - both readings before any symptom
    - NO slot asked twice in ANY persona (loop over all personas)
    - a shared symptom fills all its slots
    - adherence asked once
    - progress_hint equals the real count at every turn
    - the summary lists both conditions
    - a correction changes exactly one slot and re-shows the summary; max 2 rounds
    - caregiver: confidence lowered, and answered_by present in the /complete result and the provider review detail
    - family history doesn't trigger caregiver mode
    - single-condition flows unchanged (compare question lists against the Day 2 probe output)
D3. Mutation proofs: M-H3-1 remove the de-duplication guard; M-H3-2 count shared questions twice in the budget. Both must be killed.

PART E — Regression
All personas (old + new): print a table with before/after levels; any level that went DOWN is a blocker. Then the equivalence test; then the probe re-run on groups a, b, g and h saved to docs/audit/interview_probe_day3.md, with the before/after step order for 3 dual-diagnosis scenarios. Update the audit statuses.

ACCEPTANCE
 H3-01 Flow rules doc written; code matches it (cite where each rule lives)
 H3-02 10+ personas added; all personas pass; no level lowered
 H3-03 test_v3_dual_flow.py passes (counts pasted)
 H3-04 answered_by reaches the stored result and provider detail (test + sample response pasted, fake data)
 H3-05 2 new mutations killed
 H3-06 Single-condition flows unchanged (evidence)
 H3-07 Protected hashes identical
 H3-08 All gates green

FILES ALLOWED
Create: docs/INTERVIEW_V3_FLOW_RULES.md, backend-poc-technical/test_v3_dual_flow.py, docs/audit/interview_probe_day3.md, new persona entries
Change: backend-poc-technical/agents/interview_planner.py, backend-poc-technical/agents/interview_v3_runner.py, backend-poc-technical/agents/interview_bank/*.json (metadata only), backend-poc-technical/agents/interview_bank/loader.py, the persona definition file (append only), backend-poc-technical/main.py (the caregiver field only, shown in the plan), scripts/verify_mutations.py (append), .github/workflows/ci.yml (pytest list), docs/INTERVIEW_AUDIT.md, docs/ai-usage/hassaan.md

PR TITLE: I2-4 Day 3: v3 dual-diagnosis flow + caregiver + summary
```

---

### DAY 4 — Thursday 29 Oct — v3 complete in Urdu and Roman Urdu + blind phrase test

```text
YOUR TASK (DAY 4, HASSAAN): under v3, a patient whose language is ur or roman_ur never sees a single English sentence anywhere in the check-in. That includes questions, why-texts, options, clarifications, re-asks, the unit question, odd-input replies, emergency and safety notes, the summary, and the interface around the chat. Then run Hassaan's independent Urdu-script phrase test. Branch: feat/i2-4-v3-urdu-complete.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: you may change the interview_bank JSON (language fields only), interview_bank/loader.py, interview_v3_runner.py, answer_understanding.py (string lookups only); answer_validation.py ONLY to replace hard-coded patient-facing strings with message-catalogue lookups (no logic change; show the diff in your plan); main.py ONLY to add an additive localized label field to v3 options; and the frontend files listed below. Do NOT touch input_triage.py or the v2 patterns.

READ FIRST: docs/INTERVIEW_AUDIT.md (the language gaps); every bank JSON; interview_v3_runner.py; answer_validation.py (look for patient-facing strings); app/components/AdaptiveInterviewScreen.tsx; app/translations/index.ts (structure: export const translations: Record<Language, Translations> = { en: {...}, ur: {...} }); app/globals.css (the RTL rules and the Noto Nastaliq Urdu font for [dir="rtl"]); app/context/AppContext.tsx (how the language is chosen).

WORDING RULES (very important)
- Simple, spoken Urdu, the way you'd talk to an older patient. Not formal and not literary. Short sentences.
- Use words people actually use: "sugar", "BP", "dawai", "ghabrahat", "chakkar", "test".
- Roman Urdu as people type it on WhatsApp, with ONE consistent spelling per word. Create docs/ROMAN_URDU_GLOSSARY.md (word | spelling we use | Urdu | English) and follow it.
- The meaning must match the English EXACTLY: no added advice, no softened warning, no new numbers. Units stay as written (mg/dL, mmol/L).
- Every line you write gets "needs_native_review": true in JSON, or a matching entry in docs/URDU_REVIEW_LIST.md for frontend strings. Hassaan reviews and fixes these tonight.

PART A — Find every untranslated patient string: scripts/find_untranslated.py
- Scans interview_bank/*.json: every item and probe needs template_en, template_ur and template_roman_ur, why_text (en), why_text_ur and why_text_roman_ur, and localized choices (choices_ur, choices_roman_ur) wherever choices exist. Every responses.json entry needs reply_en, reply_ur and reply_roman_ur.
- Scans these Python files for hard-coded patient-facing English strings: interview_v3_runner.py, answer_validation.py, answer_understanding.py, and the v3 branch of main.py. Use an AST walk over string literals that are assigned to keys like "current_question", "why_text", "system_note", "options", "possible_severe_low_guidance", "clarification_prompt". Print file:line and the string.
- Exits 1 if anything is missing; prints a table either way.
- Run it FIRST and paste the full list.

PART B — Fix them
B1. Bank: add why_text_ur and why_text_roman_ur to all 37 items; localized choices; fill any missing probe or response language field.
B2. Hard-coded strings → a single message catalogue: backend-poc-technical/agents/interview_bank/messages.json ({key: {en, ur, roman_ur, needs_native_review}}), loaded by loader.py (get_message(key, lang, **fmt)). Supports {value} placeholders, e.g. the unit question "Did you mean {value} mmol/L or {value} mg/dL?". Replace each hard-coded string with a lookup in the session language.
B3. The possible-low guidance (contains treatment advice: "15g fast-acting sugar"): translate it AS IS, keep it flagged "needs doctor decision" in INTERVIEW_AUDIT.md, and add a top-level comment in messages.json next to it. Don't change its meaning.
B4. Options: the API returns, for v3 only and additively, options as objects {"value": <canonical>, "label": <localized>} in a NEW field (e.g. "option_items"), and keeps the existing "options" field unchanged, so v2 and older clients keep working. The backend logic only ever uses the canonical value.
B5. Frontend (app/components/AdaptiveInterviewScreen.tsx):
    - show option_items labels when present, and send the canonical value; fall back to options (strings) for v2
    - every surrounding string ("I don't know", "Skip", "Someone else is answering", "Why am I asked this?", progress text, send button, mic labels, error and retry messages) comes from translations (en + ur); add any missing keys to BOTH languages
    - RTL: in Urdu the chat aligns right, option buttons mirror, and numbers and units inside Urdu sentences display correctly (wrap them in <bdi> or a span with dir="ltr")
    - the Nastaliq font from globals.css applies; line height is enough that Nastaliq descenders aren't clipped
    - accessibility: buttons have aria-labels in the active language; focus order is correct in RTL
    - screenshots at 375 px and 1280 px widths, in ur and roman_ur, at three points: the first question, a unit clarification and the summary
B6. backend-poc-technical/test_v3_no_english_leak.py (add to CI): runs at least 6 personas in ur and 6 in roman_ur through start_v3_session/next_turn (including a unit clarification, an odd-input reply, a re-ask, the summary and an emergency). It asserts that no served text (current_question, why_text, option labels, system_note, guidance) contains 3 or more consecutive ASCII English words, outside a whitelist (BP, mg/dL, mmol/L, sugar, HbA1c, OK, ID).
B7. Frontend test tests/interview-urdu.test.tsx: renders option_items labels, sends the canonical value, RTL dir is set, and the v2 fallback works.

PART C — Blind Urdu phrase test (Hassaan wrote tests/sim/danger_phrases_independent_hassaan_ur.json by hand. Do NOT edit it. If it's missing, STOP Part C and write NOT DONE.)
C1. python scripts/eval_phrase_set.py tests/sim/danger_phrases_independent_hassaan_ur.json   (the v3 screen)
C2. The same 30 through v2: add a group to scripts/probe_scenarios.json, or a flag to probe_interview.py that reads any phrase JSON.
C3. docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md: TP/FN/FP/TN, sensitivity and specificity for v2 and v3, and every failing phrase.
C4. For each missed danger phrase, PROPOSE a pattern in a "Proposed for doctor review" table: phrase | proposed pattern | category | proposed level | reason. Do NOT add it to code.

PART D — Regression
- find_untranslated.py exits 0
- personas: no level change at all today (wording only). Any change is a blocker.
- equivalence, mutations, all gates; npm test, lint, build
- the probe re-run for groups a and c in ur and roman_ur, saved to docs/audit/interview_probe_day4.md

ACCEPTANCE
 H4-01 find_untranslated.py output: before (full list) and after (exit 0)
 H4-02 messages.json created; no hard-coded patient English left in the v3 path
 H4-03 option_items added additively; v2 is unaffected (test)
 H4-04 The no-English-leak test passes for 12+ personas
 H4-05 Screenshots attached (ur, roman_ur; 375 px and 1280 px; 3 points each)
 H4-06 Phrase report written (v2 vs v3), with proposals in a review-only table
 H4-07 Personas show no level change
 H4-08 Glossary and Urdu review list created; the PR says "needs Hassaan's native review before merge"
 H4-09 Protected hashes: only answer_validation.py (string lookups) changed, if at all; everything else identical
 H4-10 All gates green

FILES ALLOWED
Create: scripts/find_untranslated.py, backend-poc-technical/agents/interview_bank/messages.json, backend-poc-technical/test_v3_no_english_leak.py, tests/interview-urdu.test.tsx, docs/INDEPENDENT_PHRASE_RESULTS_hassaan_ur.md, docs/ROMAN_URDU_GLOSSARY.md, docs/URDU_REVIEW_LIST.md, docs/audit/interview_probe_day4.md
Change: backend-poc-technical/agents/interview_bank/*.json (language fields), loader.py, interview_v3_runner.py, answer_understanding.py, answer_validation.py (string lookups only), backend-poc-technical/main.py (additive option_items only), app/components/AdaptiveInterviewScreen.tsx, app/translations/index.ts, app/lib/api.ts (types), scripts/probe_interview.py / probe_scenarios.json, .github/workflows/ci.yml (pytest list), docs/INTERVIEW_AUDIT.md, docs/ai-usage/hassaan.md
Commit tests/sim/danger_phrases_independent_hassaan_ur.json exactly as Hassaan wrote it.

PR TITLE: I2-4 Day 4: v3 complete in Urdu and Roman Urdu + blind Urdu phrase test
```

---

### DAY 5 — Friday 30 Oct — OCR spike (3 options) + designs + bug bash

```text
YOUR TASK (DAY 5, HASSAAN): choose how ChronicCare will read prescriptions and lab reports, using MEASURED numbers, including whether each option can actually run where we deploy (Render free tier, Python, no root/apt, ~512 MB RAM). Then write the OCR design and the edit-history design, so Days 6–7 are pure building. No app code changes today. Branch: feat/i2-5-ocr-spike.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

READ FIRST: handbook Appendix A Parts B5 (trust), C7 (data layer), C9 (consent); backend-poc-technical/data_sources/local_store.py (tables, add_/delete_ functions); backend-poc-technical/data_sources/app_store.py (allergies table, get_db_cursor, migrations, LATEST_SCHEMA_VERSION = 12); main.py /api/me/record/* routes (which store each one writes to); main.py voice_transcribe_endpoint (it reads the raw request body, enforces a size limit and keeps audio in memory only. OCR upload should follow the SAME pattern, which avoids adding python-multipart); backend-poc-technical/data_sources/medication_scope.py (DIABETES_MEDICATIONS, HYPERTENSION_MEDICATIONS); agents/verification_agent.py trust table (local_ocr_or_upload = medium).

PART A — backend-poc-technical/ocr_spike/ (STANDALONE: main.py must never import it; own requirements.txt; own .venv at backend-poc-technical/ocr_spike/.venv)
A1. generate_samples.py: Pillow, fixed seed 42, 16 images into samples/synthetic/:
    - 10 lab reports, mixing: "HbA1c: 7.8 %", "Glycated haemoglobin 8.1%", fasting glucose in mg/dL AND mmol/L, random glucose, "BP: 148/92 mmHg", total cholesterol; some in a 2-column table layout, some as a lab-letterhead style
    - 6 prescriptions, 2–4 medicines each, names from medication_scope's lists (import them), doses and frequencies in the forms Pakistani prescriptions use: "Tab. Metformin 500 mg BD", "Amlodipine 5mg OD", "Gliclazide 80mg 1+0+1", "Losartan 50 mg — once daily", "Insulin glargine 10 units at night"
    - variation: 3 fonts, sizes 18–28 px, ±3° rotation on 3 images, light Gaussian blur on 2, salt-and-pepper noise on 2, one low-contrast image
    - 3 images with Urdu-script lines (patient name in Urdu, "روزانہ دو بار", "کھانے کے بعد")
    - TRAP: Pillow draws connected Urdu letters ONLY if it was built with libraqm. Check PIL.features.check("raqm"). If it's False, Urdu renders as disconnected letters, which is unrealistic. In that case, skip the Urdu samples and write NOT DONE with the reason, rather than producing bad samples.
    - every image stamped "SAMPLE — NOT A REAL REPORT", with a fake name "Test Patient NN" and fake lab name "Sample Lab"
    - samples/ground_truth.json: exact expected fields per file, e.g.
      {"lab_03.png": {"type": "lab", "hba1c_pct": 7.8, "glucose": {"value": 7.2, "unit": "mmol/L", "context": "fasting"}, "bp": [148, 92], "total_chol": 212}}
      {"rx_02.png": {"type": "prescription", "medicines": [{"name": "metformin", "dose": "500 mg", "frequency": "BD"}]}}
A2. samples/photos/: Hassaan adds 3–5 phone photos of fake handwritten prescriptions and TELLS you what each says. Put that in ground_truth.json. Never read values off the photo yourself as ground truth.
A3. extract_fields.py: pure Python (stdlib + the medication_scope import ONLY), so its tests run in the main CI.
    - Input: OCR text. Output: {"fields": [...], "warnings": [...]}. Every field: {"kind", "value", "unit", "evidence" (exact snippet), "confidence" ("High"/"Medium"/"Low")}.
    - hba1c_pct: a number + % within 30 characters after HbA1c / A1c / glycated / glycosylated. Plausible 3–20, else drop it with a warning.
    - glucose: value + unit (mg/dL, mg/dl, mmol/L, mmol/l). mmol/L keeps value and unit and adds mg_dl = round(value × 18.0, 1), the factor the app uses. Context word (fasting / FBS / random / RBS / PP / post-prandial) if present. No unit → keep it with confidence Low and the warning "unit missing". Never guess a unit.
    - bp: \d{2,3}\s*/\s*\d{2,3} near "BP" or "blood pressure" (within 20 characters). Only if systolic > diastolic and within the app's ranges (import the constants, or document them).
    - medicines: match the name against the two lists, case-insensitive. OCR slips are allowed: Levenshtein distance ≤ 1 for names of 6+ letters (write a small edit-distance function; no new dependency). Parse dose (\d+(\.\d+)?\s*(mg|mcg|units?|iu)) and frequency (OD, BD, TDS, QID, HS, "1+0+1"-style, once/twice/three times daily, "subah/shaam", "روزانہ") on the same line. Names not on the list go to "unmatched_lines" for the user to type in; never invent a medicine.
    - Unclear → leave it out. NEVER guess a value.
A4. run_compare.py: three options on every image.
    a) Tesseract via pytesseract: "eng", and "eng+urd" for Urdu samples. Windows: install the UB Mannheim build, tick Urdu during setup, add it to PATH or set pytesseract.pytesseract.tesseract_cmd. Verify with "tesseract --list-langs" (eng and urd must be listed).
    b) EasyOCR: Reader(['en'], gpu=False), and Reader(['ur','en'], gpu=False) for the Urdu samples. The first run downloads models; PyTorch is large (~1–2 GB). Use the spike's own .venv.
    c) Hosted vision model via Groq: the project already uses Groq for Whisper. Model name from env GROQ_VISION_MODEL; never hard-code it. Check the Groq console for a currently available vision model. Ask it ONLY to transcribe the text as plain text. The text then goes through the SAME extract_fields.py, so the model never decides a value. Synthetic samples only. GROQ_API_KEY from env; never print it.
    For each option, measure:
    - field precision, recall and exact-match per kind
    - medicine-name recall
    - average and max seconds per image
    - peak memory (tracemalloc for the Python side; for Tesseract, note that it's an external process)
    - rows split by: clean / rotated-blur-noise / Urdu / handwritten photos
    Print the tables and save them to docs/ocr/compare_results.md. If an option can't be installed or run, paste the exact error and mark it NOT RUN. NEVER fill its numbers.
A5. test_extract_fields.py: 20+ tests on plain strings (no OCR). Add it to the ci.yml pytest list; it must pass in CI without any OCR library. Cover:
    - HbA1c with and without a space before %
    - mmol/L conversion; mg/dL kept; a glucose with no unit gets Low confidence and a warning
    - BP accepted; reversed BP rejected
    - Levenshtein match on a slip ("Metf0rmin"); a non-drug word rejected; dose and frequency parsing including "1+0+1"
    - an unmatched line goes to unmatched_lines
    - an empty string; evidence always present
A6. README.md: install steps for each option on Windows, how to run, and expected outputs.

PART B — Deployability (in docs/OCR_DESIGN.md). For each option:
- installs with pip alone (no apt)? on Render's native Python runtime?
- RAM at load and per image
- cold-start impact
- cost
- does the image leave our server (privacy)?
- what we'd need (e.g. Docker for Tesseract)
Be factual. Where you aren't sure, say so and give the doc link or the test to settle it.

PART C — docs/OCR_DESIGN.md
1. Results tables + deployability table + a recommendation in 3–5 sentences (be honest about handwriting and Urdu).
2. The flow: patient picks a camera photo or file (JPG/PNG, ≤ 5 MB) → POST upload (raw body like voice, memory only) → OcrProvider.extract_text → extract_fields → the confirm screen shows each value WITH its evidence, and the patient taps Confirm / Fix / Remove → only confirmed values are saved to the Local Store with source "local", origin "ocr" (medium trust) → an edit-history row per saved value.
3. API draft with JSON examples:
   POST /api/me/record/uploads (Content-Type image/jpeg|image/png) → {upload_id, document_type_guess, fields[{field_id, kind, value, unit, evidence, confidence}], unmatched_lines[]}. Saves nothing to the record; keeps the extracted fields (NOT the image) for 30 minutes.
   POST /api/me/record/uploads/{upload_id}/confirm with body {confirm:[{field_id, value?, unit?}], remove:[field_id]} → re-validates with the check-in validators → saves → {saved:[...], rejected:[{field_id, reason}]}
   Errors: 413 too big; 415 wrong type (HEIC from iPhone included, with a friendly message); 409 record_managed_by_ehr in connected mode; 503 ocr_disabled; 502 ocr_provider_error; 404/410 expired upload; 409 already confirmed; 403 not your upload.
4. The provider interface OcrProvider.extract_text(image_bytes, lang_hint) -> str; env OCR_ENABLED (default false), OCR_PROVIDER.
5. Image handling: EXIF orientation fix (ImageOps.exif_transpose) before OCR; downscale large photos to max 2000 px; never write the image to disk or the DB; strip EXIF.
6. Privacy: the image is processed in memory and not stored. If a hosted provider is chosen, the image leaves our server, so a consent line is needed. Write it in en and ur, marked "needs Usman/doctor review". The audit log gets "ocr_upload_processed" with field COUNTS only.
7. Failure cases and what the user sees (en + ur): blurry; wrong document; two readings on one page; mmol vs mg; handwriting; Urdu; an unknown medicine; nothing found.
8. Day 7 build plan: every file to create or change, and the tests.

PART D — docs/EDIT_HISTORY_DESIGN.md
1. Read where each record write goes:
   - medications and observations → local_store.py functions (its own get_connection / get_mysql_connection)
   - allergies → app_store.py
   - conditions-basis → profile
   Print the call chain for each /api/me/record/* route (file:function).
2. Table record_edits: edit_id, user_id, record_type (medication | observation | allergy | condition), record_id, field, old_value (JSON text), new_value (JSON text), origin (self_reported | ocr | clinician), changed_by_user_id, changed_at (UTC ISO with Z), reason (nullable).
3. TRANSACTION TRAP: local_store and app_store open their OWN connections. An edit row is only atomic with the change if it is written on the SAME connection/cursor as the change. Propose the design that achieves that for every record type: e.g. record_edits created in BOTH init paths, with a helper that takes the caller's cursor. Say clearly which writes can be atomic today and which can't, and why.
4. DDL for SQLite AND MySQL, in the style of the existing code (TEXT vs VARCHAR, INTEGER PRIMARY KEY AUTOINCREMENT vs AUTO_INCREMENT, indexes on (user_id, record_type, record_id)). Schema v13; an idempotent migration; a test plan like test_schema_v11_to_v12.py.
5. Writers: every POST/PATCH/DELETE on /api/me/record/* + PUT conditions-basis + OCR confirm. Create → old_value null; delete → new_value null; update → one row per changed field; no row if nothing changed.
6. Readers: GET /api/me/record/history (patient, own data only); provider access ONLY through a review they can see (an additive field on the review detail). Explain why we don't open a broad provider endpoint.
7. Privacy: edit rows contain health values, so they stay in the app DB with the record, NEVER in audit_log (zero-PHI).
8. UI sketch: the patient sees a "History" per item; the clinician sees old → new, with OCR-sourced values marked.

PART E — Bug bash (1 hour, with Saad, on the live site https://chronicare-ai.netlify.app with FAKE accounts)
Try to break: sign-up/sign-in, consent, inclusion, profile units, EHR connect/disconnect, check-ins in en/ur/roman_ur (typed and voice), the record pages, trends, the provider queue and detail, admin. File each bug as a GitHub issue: title, steps, expected, actual, screenshot, browser + device, language, severity guess. Label it "bug" + "week2-bash". Paste the issue links in the report.

ACCEPTANCE
 H5-01 The 16 samples regenerate byte-identically (print hashes from two runs)
 H5-02 20+ extractor tests pass in the main venv WITHOUT OCR libraries
 H5-03 run_compare output for each option (or the exact error + NOT RUN)
 H5-04 Deployability table complete and factual
 H5-05 OCR_DESIGN.md and EDIT_HISTORY_DESIGN.md complete (all sections)
 H5-06 Record write call chains printed; transaction plan explicit
 H5-07 Bug-bash issues filed (links)
 H5-08 Sample PNGs < 5 MB in total; no .venv, model caches or photos with real data committed
 H5-09 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/ocr_spike/** (code, README, requirements.txt, samples/synthetic/*.png, samples/photos/* (Hassaan's fake prescriptions only), samples/ground_truth.json), docs/OCR_DESIGN.md, docs/EDIT_HISTORY_DESIGN.md, docs/ocr/compare_results.md
Change: .github/workflows/ci.yml (pytest list), .gitignore (append backend-poc-technical/ocr_spike/.venv/ and the EasyOCR model cache folder if it's created inside the repo), docs/ai-usage/hassaan.md
Nothing else.

PR TITLE: I2-5 Day 5: OCR spike (3 options) + OCR and edit-history designs
```

---

### DAY 6 — Saturday 31 Oct — Record edit history (schema v13, API, UI) + record export/import

```text
YOUR TASK (DAY 6, HASSAAN): two things today. (1) Edit history: every change a patient makes to their own record (medicines, observations, allergies, conditions basis) is recorded: who, what, when, old → new, origin. (2) Export/import: the patient can download their record (JSON and FHIR) and, in isolated mode, import a record file through a preview, using the same validation as manual entry. For the edit history: Each record is written in the same transaction as the change wherever the design allows, viewable by the patient and by a clinician reviewing that patient, and tested on the SQLite path with the MySQL DDL verified. Branch: feat/i2-5-edit-history.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: you may change backend-poc-technical/data_sources/app_store.py and local_store.py (new table, migration, helper; existing functions only to pass the cursor to the helper), main.py (the record routes, one new read route, an additive review field, the export and import routes), scripts/mysql_preflight.py (expected version), and the frontend files listed below. No triage, interview, reconciliation or verification code.

READ FIRST: docs/EDIT_HISTORY_DESIGN.md (Day 5, plus Usman's review comments on that PR); app_store.py (get_db_cursor, migrations, LATEST_SCHEMA_VERSION, the allergies functions, the {ph} placeholder pattern); local_store.py (init paths, add_/delete_/update_ functions, get_connection, get_mysql_connection); main.py /api/me/record/* routes and GET /api/provider/review/{checkin_id}; test_schema_v11_to_v12.py; scripts/mysql_preflight.py; docs/DATA_DICTIONARY.md; docs/AUTH.md; app/components/HealthRecordScreen.tsx; app/components/provider/PatientDetailScreen.tsx and ReconciliationAlertDetail.tsx.

PART A — Schema v13
A1. Create record_edits per the design, in the DB(s) the design chose. DDL for SQLite AND MySQL.
A2. Bump LATEST_SCHEMA_VERSION to 13. Write an idempotent migration (running it twice changes nothing) for both backends, following the existing migration code style exactly.
A3. backend-poc-technical/test_schema_v12_to_v13.py, modelled on test_schema_v11_to_v12.py: fresh DB at v13; v12 → v13 upgrade; idempotent; existing rows untouched; indexes present.
A4. scripts/mysql_preflight.py reports and expects v13 (update any hard-coded expectation).
A5. MySQL can't be run in CI. Instead, add a test that at least parses/compiles the MySQL DDL strings, e.g. asserting the expected column names appear. Say clearly in the report that the MySQL path is verified by inspection plus preflight on deploy.

PART B — Write path
B1. Helper record_edit(cursor, ph, *, user_id, record_type, record_id, field, old_value, new_value, origin, changed_by_user_id, reason=None). JSON-encode the values; changed_at = UTC ISO with "Z".
B2. Call it on the SAME cursor as each change, in: create/update/delete medication; create/delete observation; create/delete allergy; PUT conditions-basis. Create → old_value null; delete → new_value null; update → one row per CHANGED field; no row when nothing changed.
B3. Where the design says a write can't be atomic, implement the documented fallback and test it.
B4. origin "self_reported" for patient edits (OCR passes "ocr" on Day 7).
B5. The audit log is unchanged and zero-PHI: assert that no value text appears in audit_log.
B6. Connected mode still returns 409 record_managed_by_ehr and writes NO edit rows.

PART C — Read path
C1. GET /api/me/record/history?record_type=&record_id=&limit=50 (max 200): patient only, own data only, newest first. Pydantic response model.
C2. Provider: an ADDITIVE optional field recent_record_edits (last 20) on the review detail response, for the patient of that check-in, resolved exactly the way the existing review detail resolves the patient. No new broad provider endpoint.
C3. require_role on everything. Update docs/AUTH.md (route matrix) and docs/DATA_DICTIONARY.md (new table + fields).

PART D — UI
D1. HealthRecordScreen: a "History" button per medicine, observation and allergy. It opens a small panel: date (local format), field, old → new, by (you / OCR / clinician). States for empty ("No changes yet"), loading and error. en + ur, RTL-correct (numbers in <bdi>), accessible (button labels, focus moves into the panel, Esc closes).
D2. Provider (PatientDetailScreen and/or ReconciliationAlertDetail, wherever the review detail renders): a "Recent record changes" block showing old → new with an "OCR" badge where origin = ocr.
D3. Strings in app/translations/index.ts (en + ur). No fake values.
D4. Vitest: tests/record-history.test.tsx (patient panel: list, empty, error, Urdu) and tests/provider-record-edits.test.tsx.

PART E — Backend tests (add to CI): backend-poc-technical/test_record_edits.py
- every write type creates the right rows (record_type, field, old/new, origin)
- an unchanged PATCH → no row
- atomicity: monkeypatch the helper to raise, assert the record change was rolled back (for the atomic paths), and test the documented fallback for the others
- patient A can't read patient B's history (403/404)
- the provider sees edits only for a patient whose check-in they can review
- connected mode → 409, no rows
- the audit log has no values
- limit and ordering
Plus a mutation proof in scripts/verify_mutations.py: removing the record_edit call from the medication update path must be KILLED.

PART F — Manual check
Run backend + frontend locally. As a fake patient: add a medicine, change its dose, delete an allergy, add an observation → open History (en and ur) → screenshot. As a fake provider on that patient's review: screenshot the block.

PART G — Record EXPORT (the patient owns their data; this is in the FYP-1 scope)
Read first: GET /api/me/record and PatientRecordResponse in main.py (the export is built from the SAME function that serves the record, never a second query path); data_sources/fhir_adapter.py (which FHIR resource types and LOINC codes the app already reads, so the export uses the same ones).
G1. GET /api/me/record/export?format=json|fhir (patient only, own record only, works in BOTH modes):
    - format=json: {"format": "chroniccare-record", "version": 1, "exported_at": UTC ISO "Z", "record": <exactly the PatientRecordResponse that GET /api/me/record returns: mode, conditions, medications, allergies, baseline_observations>, "record_edits_count": N}. Every item keeps its origin and trust level. Item ids are kept, so a re-import can skip duplicates.
    - format=fhir: a FHIR R4 Bundle of type "collection": one Patient (no name or contact details: id + birthDate year only + gender), MedicationStatement per medicine, AllergyIntolerance per allergy, Observation per reading, using the SAME LOINC codes fhir_adapter.py reads (glucose, systolic/diastolic as BP-panel components 8480-6 / 8462-4 under 85354-9). Each resource gets meta.tag = the origin ("self_reported", "ocr", "ehr").
    - Content-Disposition: attachment; filename="chroniccare-record-<YYYY-MM-DD>.<json|fhir.json>"
    - Audit: one audit_log row "record_exported" with the format only (no values).
G2. Round-trip proof: fhir_adapter.fhir_to_normalized_observations and fhir_to_normalized_medications must read the exported Bundle's resources back and produce the same readings and medicines (a test, not a claim).

PART H — Record IMPORT (isolated mode only)
H1. POST /api/me/record/import?dry_run=true|false, body = a chroniccare-record JSON (from G1) or a FHIR Bundle. Raw body read exactly like the voice endpoint (no python-multipart); max 2 MB → 413; wrong content type → 415; connected mode → 409 record_managed_by_ehr (same as other writes).
H2. Every item goes through the SAME validation as the existing POST /api/me/record/* routes. Call the same helper functions; don't copy the rules. An invalid item is reported, never silently fixed, and never stops the valid ones.
H3. dry_run=true returns a preview: {"to_add": [...], "duplicates": [...], "invalid": [{"item", "reason"}], "counts": {...}}. Nothing is written.
H4. dry_run=false writes the valid, non-duplicate items in ONE transaction (all or nothing). Origin = "import", trust = low (the same as self-report). One record_edits row per item (old_value null, origin "import"). One audit row "record_imported" with counts only.
H5. Limits: at most 500 items per file; duplicates = same type + same value + same timestamp (or the same exported id).
H6. Readings imported with a timestamp older than 14 days must NOT count toward the triage baseline unless get_user_baseline_history already treats them that way. Check the code and state what happens, with file:line. Don't change baseline code; if it would count them, write it under OPEN QUESTIONS FOR USMAN.
H7. UI on HealthRecordScreen: "Download my record" (JSON / FHIR choice) and, in isolated mode only, "Import a record file" → file picker → preview screen (to add / duplicates / invalid, each with a reason) → "Import N items" → success state. en + ur, RTL-correct, keyboard-accessible, no fake values.
H8. Tests (add to CI): backend-poc-technical/test_record_export_import.py
    - JSON and FHIR export shape; own data only; connected mode export works
    - FHIR round-trip through fhir_adapter (G2)
    - dry run writes nothing (row counts before == after)
    - an invalid item (e.g. systolic 400, a medicine outside medication scope) is reported and skipped, while valid ones import
    - all-or-nothing: monkeypatch a failure mid-insert → zero rows written
    - duplicates skipped on re-import of your own export (export → import → 0 added)
    - 413 / 415 / 409 paths; another user can't import into my record
    - audit rows hold counts only, no values
    Vitest: tests/record-export-import.test.tsx (buttons per mode, preview lists, Urdu, error state).
    Mutation proof: make import skip the shared validation → a test must KILL it.

ACCEPTANCE
 H6-01 Migration v12 → v13 tested; idempotent
 H6-02 All record writes create correct edit rows; no row on no-op
 H6-03 Atomicity proven where designed; the fallback documented and tested elsewhere
 H6-04 Read paths role-guarded; cross-patient access denied (tests)
 H6-05 Connected mode unchanged (409, no rows)
 H6-06 The audit log stays value-free (test)
 H6-07 UI in en and ur with screenshots; vitest passes
 H6-08 Mutation added and killed
 H6-09 Docs updated (AUTH, DATA_DICTIONARY)
 H6-10 Protected hashes identical; all gates green
 H6-11 Export JSON + FHIR works in both modes; FHIR round-trips through fhir_adapter (test)
 H6-12 Import: dry run writes nothing; shared validation used (mutation killed); all-or-nothing proven
 H6-13 Export → re-import adds 0 (duplicates skipped); 409/413/415 paths tested
 H6-14 Import/export UI in en + ur with screenshots; vitest passes
 H6-15 Baseline effect of imported old readings stated with file:line

FILES ALLOWED
Change: backend-poc-technical/data_sources/app_store.py, backend-poc-technical/data_sources/local_store.py, backend-poc-technical/main.py (record routes, the history route, the additive review field, the export and import routes), scripts/mysql_preflight.py, scripts/verify_mutations.py (append), app/components/HealthRecordScreen.tsx, app/components/provider/PatientDetailScreen.tsx and/or ReconciliationAlertDetail.tsx, app/lib/api.ts, app/translations/index.ts, docs/AUTH.md, docs/DATA_DICTIONARY.md, .github/workflows/ci.yml (pytest list), docs/ai-usage/hassaan.md
Create: backend-poc-technical/test_schema_v12_to_v13.py, backend-poc-technical/test_record_edits.py, backend-poc-technical/test_record_export_import.py, tests/record-history.test.tsx, tests/provider-record-edits.test.tsx, tests/record-export-import.test.tsx

PR TITLE: I2-5 Day 6: record edit history (schema v13) + record export/import
If the day runs out: open the PR with Parts A–F (edit history) and push G–H as a second PR "I2-5 Day 6b: record export/import" on the branch feat/i2-5-export-import, finished by Monday 2 Nov morning.
PR BODY MUST INCLUDE: "PRODUCTION DB MIGRATION: run scripts/mysql_preflight.py before and after deploying; expected schema 13."
```

---

### DAY 7 — Sunday 1 Nov — OCR v1 behind a flag + weekly log

```text
YOUR TASK (DAY 7, HASSAAN): a patient in ISOLATED mode can upload a photo of a lab report or prescription, see the values the system read (each with its evidence), Confirm / Fix / Remove each one, and save ONLY confirmed values to their record with origin "ocr" (medium trust) and edit-history rows. All of it sits behind OCR_ENABLED=false by default, so production is unaffected until Usman turns it on. Then write the weekly log. Branch: feat/i2-5-ocr-v1.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_HASSAAN.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: you may create backend-poc-technical/data_sources/ocr/**, change main.py (2 routes + a capability flag + config-status), the data layer for the temporary upload store, requirements.txt ONLY if the chosen provider needs a pip package (name it and give its install size), .env.example (empty values only), and the frontend files below. No triage, interview, reconciliation or verification code.

READ FIRST: docs/OCR_DESIGN.md (with Usman's provider decision in the Day 5 PR comments; if there's no decision, implement the provider interface + the fake provider + Tesseract, and leave the hosted provider for later); Day 6's record_edit helper; main.py voice_transcribe_endpoint (copy its raw-body + size-limit + memory-only pattern); the check-in validators for glucose and BP (answer_validation.validate_glucose_input / validate_bp_input and the v2 equivalents. REUSE them, don't copy them); app/components/HealthRecordScreen.tsx; AppContext screen union; page.tsx.

PART A — Backend
A1. backend-poc-technical/data_sources/ocr/:
    - __init__.py
    - provider.py (Protocol OcrProvider: extract_text(image_bytes: bytes, lang_hint: str) -> str; get_provider() reads OCR_PROVIDER)
    - fake_provider.py (returns fixed text per test fixture)
    - the chosen real provider (tesseract_provider.py and/or groq_vision_provider.py, with lazy imports, so the app starts even if the library is missing and OCR_ENABLED is false)
    - extract_fields.py moved from ocr_spike (git mv), with its tests' import path updated in both the test file and ci.yml
A2. Image pre-processing: verify the magic bytes (JPEG FFD8, PNG 89504E47), not just the header; Pillow open; ImageOps.exif_transpose; strip EXIF; downscale to max 2000 px; process in memory; never write it to disk or the DB.
A3. POST /api/me/record/uploads (require_role patient):
    - OCR_ENABLED false → 503 {"code": "ocr_disabled"}
    - connected mode → 409 record_managed_by_ehr
    - Content-Type image/jpeg or image/png only, else 415. HEIC/HEIF gets a specific message ("Please share as JPG or PNG").
    - > 5 MB → 413
    - provider exception → 502 {"code": "ocr_provider_error"} (log the exception type, never the content)
    - otherwise run extract_fields and store ONLY the extracted fields (never the image) under an upload_id bound to user_id, with expires_at = now + 30 min, in a small table (schema v14 via the Day 6 migration pattern, with tests) or an in-memory store if the deploy is single-process (the Render start command is "uvicorn main:app --host 0.0.0.0 --port $PORT", one worker). Choose one, and justify it in the report (restarts lose in-memory uploads; is that acceptable for a 30-minute flow?).
    - audit: "ocr_upload_processed" {"field_count": n}, no values
    - response: {upload_id, document_type_guess, fields[...], unmatched_lines[], expires_at}
A4. POST /api/me/record/uploads/{upload_id}/confirm:
    - not found or expired → 404/410
    - other user → 403 (or 404, consistent with existing style)
    - already confirmed → 409
    - re-validate EVERY confirmed value with the SAME validators the check-in uses (ranges, units, mmol/L ×18.0). Invalid → listed in "rejected" with a reason; valid ones are still saved (say which behaviour you chose, and test it)
    - save to the Local Store with source "local" and origin "ocr"; medicines via the existing add_local_medication path; observations via add_local_observation
    - write record_edit rows with origin "ocr". A FIXED value is saved as fixed; the edit row's reason is "patient corrected OCR value", and the extracted value is kept in old_value
    - delete the temporary upload; audit "ocr_upload_confirmed" {"saved": n, "rejected": m}
A5. Capability: add "ocr_enabled": bool to an existing patient-visible response (e.g. the record response). Choose the least invasive option, explain why, keep it additive. GET /api/admin/config-status lists OCR_ENABLED / OCR_PROVIDER / GROQ_VISION_MODEL as SET / NOT SET only.
A6. .env.example: OCR_ENABLED=, OCR_PROVIDER=, GROQ_VISION_MODEL= (empty), with comments.

PART B — Frontend
B1. HealthRecordScreen: an "Upload report or prescription" button, only when isolated mode AND ocr_enabled. File input accept="image/jpeg,image/png" capture="environment" (the phone camera). The client checks size and type before upload, with friendly messages (en + ur).
B2. app/lib/api.ts: uploadRecordDocument(file) sends the raw body with the file's Content-Type, matching how voice upload sends audio; confirmRecordUpload(id, body).
B3. New screen app/components/OcrConfirmScreen.tsx (added to the AppContext screen union and page.tsx):
    - a header with the document type guess and "Check each value before saving"
    - a list of fields: kind label, value + unit, the evidence snippet in a quote style, a confidence badge (High/Medium/Low as text + icon, not colour alone), buttons Confirm / Fix (inline edit with validation hints) / Remove
    - unmatched lines: "We couldn't read these. Add them yourself if needed." with a link to the manual add form
    - "Save confirmed values" disabled until at least one value is confirmed; shows a summary after saving, with a link to the record
    - states: nothing found, provider error, expired (start again), network error with retry
    - en + ur, RTL (values and units in <bdi>), keyboard and screen-reader accessible, focus management after save
B4. After saving, record items show an "OCR" provenance badge, and History shows origin "OCR".
B5. Vitest: tests/ocr-confirm.test.tsx: renders fields, confirm a subset, fix a value, remove one, save calls the API with the right body, error states, Urdu rendering, the button hidden when ocr_enabled is false or in connected mode.

PART C — Backend tests (add to CI): backend-poc-technical/test_ocr_upload.py, using the fake provider
- flag off → 503; connected → 409
- type: PNG/JPEG OK, GIF/PDF/HEIC → 415; size > 5 MB → 413; bad magic bytes → 415
- nothing is saved to the record before confirm
- confirm saves only the confirmed fields with origin "ocr" + edit rows; fixed values recorded with the reason; removed fields not saved
- an invalid value rejected with a reason (and the chosen behaviour for the valid ones)
- expiry → 404/410 (freeze the time or inject a clock); double confirm → 409; another user → 403/404
- the audit log has counts only
- no image bytes anywhere: scan every table's text columns for the PNG/JPEG signature, or base64 of the fixture
- the provider exception → 502, with no content logged
Mutation proof: removing the re-validation in confirm must be KILLED.

PART D — Manual check (OCR_ENABLED=true locally, OCR_PROVIDER = fake and then the real one if installed)
Upload 3 synthetic samples from ocr_spike → confirm some, fix one, remove one → save → check the record and History. Screenshots in en and ur. Then OCR_ENABLED=false → the button is hidden and the API returns 503.

PART E — Weekly log: docs/weekly/2026-W44-hassaan.md (one page)
Done (each PR link + one line); key numbers (tests added, mutations, personas, phrase sensitivity before/after); gaps still open from INTERVIEW_AUDIT.md; items waiting on a doctor; what slipped and why; next week's top 3.

IF TIME RUNS OUT: ship the backend with full tests, open the PR as "backend only", list exactly what's left of the UI, and DON'T merge half a UI.

ACCEPTANCE
 H7-01 Provider interface + fake + real provider (or real marked NOT DONE with the reason)
 H7-02 The upload endpoint enforces flag, mode, type, magic bytes, size; image never stored (test)
 H7-03 Confirm re-validates, saves with origin ocr, writes edit rows, deletes the temp upload
 H7-04 The capability flag is additive; config-status shows SET/NOT SET only
 H7-05 The UI flow works in en and ur (screenshots); vitest passes
 H7-06 Mutation added and killed
 H7-07 Flag off = no user-visible change (test + screenshot)
 H7-08 Weekly log written
 H7-09 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/data_sources/ocr/**, backend-poc-technical/test_ocr_upload.py, app/components/OcrConfirmScreen.tsx, tests/ocr-confirm.test.tsx, docs/weekly/2026-W44-hassaan.md, docs/wireframes/* (Hassaan's wireframes)
Change: backend-poc-technical/main.py, app_store.py (temporary upload table + migration, if chosen), backend-poc-technical/requirements.txt (only if needed; justify it), backend-poc-technical/.env.example, backend-poc-technical/ocr_spike/* (the git mv of extract_fields), app/components/HealthRecordScreen.tsx, app/context/AppContext.tsx (screen union), app/page.tsx, app/lib/api.ts, app/translations/index.ts, docs/AUTH.md, docs/DATA_DICTIONARY.md, scripts/verify_mutations.py (append), .github/workflows/ci.yml (pytest list), docs/ai-usage/hassaan.md

PR TITLE: I2-5 Day 7: OCR v1 behind a flag (upload, confirm, history)
PR BODY MUST INCLUDE: what Usman sets on Render to enable it (OCR_ENABLED, OCR_PROVIDER, GROQ_VISION_MODEL if hosted), and that it stays OFF until he decides.
```

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

> The prompts call this "the handbook". Its sections (Part 0, A1…F) are referenced by name, e.g. "handbook C14".

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
