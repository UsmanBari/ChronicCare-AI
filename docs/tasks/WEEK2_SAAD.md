# ChronicCare AI — Week 2 (26 Oct – 1 Nov 2026) — Saad

> **This is the only file you need this week.** It has the one-time setup, the daily workflow, how your work gets checked, all 7 Antigravity prompts, who does what, and the full project handbook (Appendix A).
> **Give the whole file to your AI first** ("read this whole file; it's the context for everything I'll ask"), then paste one day's prompt at a time.
> Save it in the repo as `docs/tasks/WEEK2_SAAD.md` (Part 1.5). Every prompt tells the agent to read it from there.

**Your focus this week:** helping Usman with the ML (he owns the models; you build the data pipeline, the time-based split, the evaluation toolkit his code calls, and external validation of his saved models), and the trend agent, which is fully yours, from the module all the way to arrows on the live site.

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
The email must be the one on your earlier commits, so GitHub keeps counting them as yours: `muhammad.saadd06@gmail.com`. Your earlier commits used two different names (`msaadd25` and `Muhammad Saad`). Pick one and keep it this week:
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
Save this file as `docs/tasks/WEEK2_SAAD.md` in your clone. Every day's prompt tells the agent to read it from there. It gets committed in your Day 1 PR.

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


### 1.6 Saad-only setup (data)
1. **Usman sends you his dataset folder.** Put it at `C:\Users\<you>\Desktop\Chronicare-data\`, outside the repo and never inside `Chronicare\`. Keep the names exactly as they are. It looks like this:
   ```
   Chronicare-data\
     get_nhanes.py, get_brfss.py   the two data scripts (Day 1 copies them into the repo)
     nhanes\                       nhanes_core.csv, nhanes_full.parquet, raw\<cycle>\*.xpt (11 cycles)
     brfss\                        brfss_core.parquet, brfss_core_sample.csv, zips\LLCP20xxXPT.zip (5 files)
     brfss2015_kaggle\             the 3 diabetes_*_BRFSS2015.csv files (Kaggle)
     cardio70k\                    cardio_train.csv (Kaggle)
     framingham\                   framingham.csv (Kaggle)
     pima\                         the Pima Indians diabetes .csv
   ```
   If it arrives inside an extra folder (e.g. `Chronicare-data\Chronicare-data\...`), move the contents up one level. If something is missing, tell Usman; don't download it yourself.
2. **Every terminal**, before anything ML-related:
   ```powershell
   $env:CHRONICCARE_DATA_DIR = "C:\Users\<you>\Desktop\Chronicare-data"
   ```
   To make it permanent: `[Environment]::SetEnvironmentVariable("CHRONICCARE_DATA_DIR", "C:\Users\<you>\Desktop\Chronicare-data", "User")`, then open a new terminal.
3. **ML packages** (in the same backend venv): `python -m pip install -r backend-poc-technical/ml/requirements.txt pyarrow`.
4. **Check the layout** (it prints paths only, never data):
   ```powershell
   $d = $env:CHRONICCARE_DATA_DIR
   $need = "get_nhanes.py", "get_brfss.py", "nhanes\nhanes_core.csv", "nhanes\raw", "brfss\brfss_core.parquet", "brfss\zips", "brfss2015_kaggle\*.csv", "cardio70k\*.csv", "framingham\*.csv", "pima\*.csv"
   foreach ($p in $need) { if (Test-Path (Join-Path $d $p)) { "OK       $p" } else { "MISSING  $p" } }
   ```
   All 10 lines must say OK before Day 1. Screenshot it for Usman.
5. **MIMIC-IV (PhysioNet rules, not optional).**
   - Keep it in a separate folder, e.g. `C:\Users\<you>\Documents\mimic-private\`. **Never** put it inside the repo or `Chronicare-data`, and never open that folder in Antigravity.
   - No MIMIC row, file, screenshot or column dump goes into Antigravity, Claude, ChatGPT, WhatsApp or GitHub. Only counts and summaries that a script prints.
   - MIMIC is **not** in Usman's dataset folder. You already have your own BigQuery export: keep it in your private folder. From now on, don't send the files to anyone (WhatsApp included), teammates included. Delete any copies from chats.
6. **DHS** (India / Bangladesh / Nepal / Pakistan) is waiting for approval. Same rules as MIMIC once it arrives: the files stay local and only aggregates are shared.
7. **A quick check that works:** `python -c "import os; print('SET' if os.environ.get('CHRONICCARE_DATA_DIR') else 'NOT SET')"`

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

**ML ownership: the ML is mainly Usman's; you help.**
| Usman (owner) | Saad (helping) |
|---|---|
| `docs/ML_PLAN.md`: final labels, features, models | Data scripts, data checks, the time-based split (Days 1–2) |
| The experiment harness, training, tuning, model selection | **Drafts** of the feature map and label catalogue, for Usman to decide on (Day 2) |
| SHAP explanations and the risk card in the app | The evaluation toolkit his harness calls, plus the model-file format (Day 3) |
| Final ML numbers in the report and viva | Other-dataset loaders + external validation of **his** saved models (Day 6) |
| | MIMIC / DHS loaders (aggregates only) |

You never pick a label, feature or model, and you never edit `backend-poc-technical/ml/experiments/` or `docs/ML_PLAN.md`. If you think a choice is wrong, write it under "OPEN QUESTIONS FOR USMAN / DOCTOR". The trend agent (Days 4–5) is fully yours; it's rules and statistics, not ML.

**Hand-offs to Usman:** Day 2 feature map + label catalogue → he writes `ML_PLAN.md`. Day 3 `ML_INTERFACES.md` → he approves the model-file format before his harness saves models in it. Day 6 → you run external validation on whatever models he has saved by then.

| Day | Date | Focus | Branch | PR title |
|---|---|---|---|---|
| 1 | Mon 26 Oct | Refresh check, ignore rules, data scripts in repo, data checks report, ML CI job | `feat/i2-1-data-checks` | I2-1 Day 1: data scripts + data checks |
| 2 | Tue 27 Oct | Time-based split, fair baseline re-run, feature map, label catalogue | `feat/i2-1-split-baseline-featuremap` | I2-1 Day 2: temporal split, fair baseline, feature map, label catalogue |
| 3 | Wed 28 Oct | Evaluation toolkit for Usman's models (thresholds, CIs, calibration, subgroups, leakage check) + model-file contract | `feat/i2-1-eval-toolkit` | I2-1 Day 3: ML evaluation toolkit + model artifact contract |
| 4 | Thu 29 Oct | Trend agent: spec, pure module, reading history, 40+ tests | `feat/i2-6-trend-agent` | I2-6 Day 4: trend agent module + reading history + tests |
| 5 | Fri 30 Oct | Trends live: API, patient screen fix + arrows, provider detail; bug bash | `feat/i2-6-trend-live` | I2-6 Day 5: trends live (API, patient screen, provider detail) |
| 6 | Sat 31 Oct | Dataset loaders + external validation of Usman's saved models + DHS skeleton | `feat/i2-1-external-validation` | I2-1 Day 6: external validation + dataset loaders + DHS skeleton |
| 7 | Sun 1 Nov | Coverage, regression tests, bug-bash fixes, MIMIC sanity script, RAG retrieval test set, phrase test round 2, weekly log | `test/i2-8-hardening` | I2-8 Day 7: coverage, fixes, MIMIC script, RAG test set, phrase test r2, weekly log |

**Things you do by hand, not the AI:**
- **Data folder.** Create `C:\Users\<you>\Desktop\Chronicare-data\` (outside the repo). In every terminal you open, set `$env:CHRONICCARE_DATA_DIR = "C:\Users\<you>\Desktop\Chronicare-data"`.
- **Dataset folder from Usman (before Day 1).** Put it at `Chronicare-data\` exactly as Part 1.6 shows, without MIMIC, and run the check command there. You download nothing yourself.
- **MIMIC.** Keep MIMIC-IV in a folder the agent is **never** shown, for example `C:\Users\<you>\Documents\mimic-private\`. On Day 7 the agent only **writes** a script. **You** run it in a normal PowerShell window outside Antigravity, and paste only the summary it prints.
- **The scripts.** `get_nhanes.py` and `get_brfss.py` are at the top level of Usman's dataset folder. Day 1 copies them into the repo.
- **Saturday evening (for Day 7):** write 30 NEW phrases yourself (15 danger, 15 safe or negated; English, Roman Urdu and Urdu script) into `tests/sim/danger_phrases_independent_saad_r2.json`, in the same format as your S-1 file (`text`, `expected_danger`, `category`, `language`, `author`). Don't look at the detector's code first. Commit it on the Day 7 branch before the agent starts Part G.

---

### DAY 1 — Monday 26 Oct — Refresh check, data scripts, data checks

```text
YOUR TASK (DAY 1, SAAD): make the public datasets reproducible from the repo and produce a trustworthy data-quality report that everything in Usman's risk models builds on. Add an ML test job to CI. Branch: feat/i2-1-data-checks.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

READ FIRST: docs/tasks/WEEK2_SAAD.md Appendix A (handbook): Part 0, B8 (risk model design), C14 (ML today), D4 (data). backend-poc-technical/ml/ (README.md, load_data.py, train_baseline.py, explain.py, requirements.txt). The root .gitignore. .github/workflows/ci.yml.

DATA LOCATION: everything under $env:CHRONICCARE_DATA_DIR (outside the repo). Check it's set: print only SET / NOT SET. If it's NOT SET, STOP.

PART A — Ignore rules. The existing backend-poc-technical/ml/data/ rule (your S-6 XPT files) stays; don't move, rename or delete those files or the S-6 scripts. Append to the root .gitignore (remove nothing):
  # ML / datasets — never commit
  dataset/
  Chronicare-data/
  *.parquet
  *.xpt
  *.XPT
  backend-poc-technical/ml/outputs/
Then git status: show that no data file is untracked or staged.

PART B — Data scripts
B1. Copy get_nhanes.py and get_brfss.py from the top level of $CHRONICCARE_DATA_DIR (they came in Usman's dataset folder) UNCHANGED into backend-poc-technical/ml/data_prep/. They write to $CHRONICCARE_DATA_DIR/nhanes and /brfss and stop with a clear message if the variable isn't set. Print their SHA-256 so the review can confirm they're unchanged before your edit in B2.
B2. One fix to get_brfss.py's CANDIDATES map:
    - kidney_disease is missing for 2015 and 2017
    - has_insurance is missing for 2023
    Find the right variable names in the CDC BRFSS codebooks (https://www.cdc.gov/brfss/annual_data/annual_<year>.html → "Codebook"). Add the correct names to the candidate lists. In the report, name the codebook URL and the variable label for each.
B3. backend-poc-technical/ml/data_prep/README.md covering:
    - setting CHRONICCARE_DATA_DIR
    - NHANES by script: 11 cycles 1999–2023, ~10–20 min; 2019–2020 isn't released separately (it's inside the 2017–Mar 2020 pre-pandemic files, which overlap 2017–2018, so they're skipped)
    - BRFSS: download IN A BROWSER into brfss/zips/, because www.cdc.gov returns 403 to scripts:
      https://www.cdc.gov/brfss/annual_data/2015/files/LLCP2015XPT.zip
      https://www.cdc.gov/brfss/annual_data/2017/files/LLCP2017XPT.zip
      https://www.cdc.gov/brfss/annual_data/2019/files/LLCP2019XPT.zip
      https://www.cdc.gov/brfss/annual_data/2021/files/LLCP2021XPT.zip
      https://www.cdc.gov/brfss/annual_data/2023/files/LLCP2023XPT.zip
      Odd years only, because the high-BP questions are asked in odd years.
    - expected outputs and counts
B4. Saad runs (with the venv active and the ML requirements installed):
      python backend-poc-technical/ml/data_prep/get_nhanes.py
      python backend-poc-technical/ml/data_prep/get_brfss.py
    The raw files from Usman's dataset folder are already in nhanes/raw/ and brfss/zips/, so neither script should download anything (both skip files that already exist). If either starts downloading, STOP: the folder layout is wrong. Compare it with Part 1.6 of WEEK2_SAAD.md. Re-running the scripts rebuilds nhanes_core.csv and brfss_core.parquet from the raw files. That's the point: it proves the processed files are reproducible from the committed scripts.
    Paste both SUMMARY blocks. Expected: NHANES all participants 113,249, adults 67,357, adults with HbA1c 59,412, with BP 60,000, with fasting glucose 29,218; BRFSS total 2,181,756. Explain any difference. After B2, BRFSS must no longer report kidney_disease missing for 2015/2017, nor has_insurance for 2023.

PART C — backend-poc-technical/ml/common.py (shared all week)
- data_dir() -> Path (clear error if not set); nhanes_core_path(); brfss_core_path()
- load_nhanes_core(columns=None) and load_brfss_core(columns=None) (column-selected reads; brfss uses pyarrow)
- ADULT_MIN_AGE = 18; SEED = 42
- small pure helpers used by data_checks (each unit-testable on a tiny DataFrame)

PART D — backend-poc-technical/ml/data_checks.py → writes docs/DATA_CHECKS.md (AGGREGATES ONLY; never a row, a seqn or an id)
NHANES (nhanes_core.csv columns: seqn, cycle, age, sex_male, race_eth, income_poverty_ratio, bmi, waist_cm, height_cm, weight_kg, sbp, dbp, pulse, hba1c, fasting_glucose, total_chol, told_diabetes, takes_insulin, takes_diabetes_pills, told_high_bp, takes_bp_meds, family_hx_diabetes, ever_smoked_100, exam_weight_2yr, borderline_diabetes). Adults unless stated:
 D1. Rows and adults per cycle; duplicate seqn count (must be 0).
 D2. Missing % per column × cycle (one wide table).
 D3. Implausible-value counts (count, don't drop): sbp < 60 or > 260; dbp < 30 or > 160; dbp == 0; sbp <= dbp; bmi < 12 or > 80; waist_cm < 40 or > 200; hba1c < 3 or > 20; fasting_glucose < 20 or > 600. Max age per cycle: say which cycles top-code at 80 and which at 85 (read it from the data; don't assume).
 D4. Label counts and rates per cycle (DESCRIPTIVE ONLY; Usman decides the real labels):
     - told_diabetes; borderline_diabetes
     - measured diabetes = hba1c ≥ 6.5 OR fasting_glucose ≥ 126
     - undiagnosed = measured AND told_diabetes == 0
     - told_high_bp; takes_bp_meds
     - BP ≥ 130/80 (2025 AHA/ACC stage 1 or higher) and BP ≥ 140/90 (stage 2)
     - uncontrolled = told_high_bp == 1 AND BP ≥ 140/90
     Always show both the denominator and the numerator.
 D5. Weighted prevalence for told_diabetes and measured diabetes using exam_weight_2yr. When pooling cycles, NHANES guidance is to divide the 2-year weights by the number of cycles pooled. Do that and say so in the doc. Show unweighted next to weighted.
 D6. "Notes": anything odd, each with the number that shows it.
BRFSS (brfss_core.parquet columns: year, diabetes, prediabetes, diabetes_3class, high_bp, borderline_bp, bp_meds, high_chol, sex_male, age_group, age, bmi, smoker_status, ever_smoker, phys_active, heavy_drinker, gen_health, phys_hlth_days, ment_hlth_days, heart_disease, stroke, kidney_disease, education, income_group, race, has_insurance, survey_weight):
 D7. Rows per year; missing % per column per year.
 D8. diabetes and high_bp rates per year, unweighted and survey_weight-weighted.
 D9. bmi < 12 or > 80 counts; the age_group distribution.
 D10. Notes.
Rules: deterministic; re-running overwrites the doc; prints the path written; reads only the columns it needs (2.18M BRFSS rows).

PART E — ML tests + CI job
 E1. backend-poc-technical/ml/tests/__init__.py, test_common.py, test_data_checks.py. Use TINY synthetic DataFrames built inside the tests (never real data). Cover:
     - the missing-env-var error
     - implausible-value counting at each boundary (59/60, 260/261, sbp == dbp)
     - label counting, including undiagnosed
     - the weight division when pooling
     - no row-level data in the generated markdown: run the doc builder on a synthetic frame and assert no seqn-like ids appear
 E2. Add a NEW job "ml-tests" to .github/workflows/ci.yml:
       runs-on: ubuntu-latest
       actions/checkout@v4
       actions/setup-python@v5 with python-version 3.11 and pip cache keyed on backend-poc-technical/ml/requirements.txt
       run: pip install -r backend-poc-technical/ml/requirements.txt pytest
       run: python -m pytest backend-poc-technical/ml/tests -q
     Do NOT modify the existing job.
 E3. backend-poc-technical/ml/requirements.txt: add only what you import (numpy, pyarrow, …), pinned to the exact installed versions (pip freeze | Select-String).

TRAPS
- pandas.read_sas on .xpt is slow; the scripts already cache. Don't re-download.
- BRFSS parquet: read with columns=[...] to save memory.
- NHANES codes 7/9 (refused / don't know) were mapped to NaN by get_nhanes.py's yes_no(). Don't treat NaN as "no".
- borderline_diabetes is 0 when DIQ010 is missing (it's computed as DIQ010 == 3). Mention this in the notes; don't "fix" the core file.

ACCEPTANCE
 S1-01 Refresh check pasted
 S1-02 .gitignore updated; git status clean of data
 S1-03 Scripts added; B2 variables found with codebook evidence
 S1-04 Both SUMMARY blocks pasted and matching (or differences explained)
 S1-05 DATA_CHECKS.md generated; contains no row-level data
 S1-06 ML tests pass locally (output pasted); ml-tests CI job added
 S1-07 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/ml/data_prep/{get_nhanes.py, get_brfss.py, README.md}, backend-poc-technical/ml/common.py, backend-poc-technical/ml/data_checks.py, backend-poc-technical/ml/tests/{__init__.py, test_common.py, test_data_checks.py}, docs/DATA_CHECKS.md, docs/tasks/WEEK2_SAAD.md (this file, if not yet committed)
Change: .gitignore (append), .github/workflows/ci.yml (new job only), backend-poc-technical/ml/requirements.txt, docs/ai-usage/saad.md (append)

PR TITLE: I2-1 Day 1: data scripts + data checks
```

---

### DAY 2 — Tuesday 27 Oct — Split, fair baseline, feature map, label catalogue

```text
YOUR TASK (DAY 2, SAAD): give Usman (the ML owner) the four things he needs to write ML_PLAN.md: an honest time-based split, a fair re-run of your own S-6 baseline (backend-poc-technical/ml/train_baseline.py, merged in PR #61), a map of which features the APP can actually collect, and a catalogue of possible label definitions with their prevalence. Branch: feat/i2-1-split-baseline-featuremap.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

READ FIRST: docs/DATA_CHECKS.md (Day 1); handbook B8; backend-poc-technical/main.py: the ProfileUpdateRequest model and the profile response model, the check-in reading types (observation_type values like glucose, blood_pressure_systolic and blood_pressure_diastolic), and how the patient profile is stored (data_sources/app_store.py, patient_profiles plus the ALTER TABLE migrations); app/components/HealthProfileScreen.tsx (what the onboarding UI asks for); backend-poc-technical/ml/train_baseline.py.

PART A — backend-poc-technical/ml/splits.py
- NHANES adults (age ≥ 18).
- test = cycles 2017-2018 + 2021-2023
- validation = 2013-2014 + 2015-2016
- train_core = 1999-2000 … 2011-2012
- Write $CHRONICCARE_DATA_DIR/splits/nhanes_temporal_v1.json with {"version": "nhanes_temporal_v1", "created_with_commit": <git rev-parse HEAD>, "train_core": [seqn...], "validation": [...], "test": [...]}. These are SEQN lists only, never data.
- Asserts: disjoint; their union equals all adults; each split's cycles are exactly as above.
- load_split(name) -> dict of sets, in common.py.
- Append a "Split" section to docs/DATA_CHECKS.md: counts per split, and told_diabetes / measured diabetes / BP ≥ 130/80 rates per split (numerator/denominator).

PART B — backend-poc-technical/ml/baseline_temporal.py (old train_baseline.py UNTOUCHED)
- Features age, sex_male, bmi; label told_diabetes (the same as the old baseline); drop rows with any missing value. Report how many were dropped per split.
- Models: LogisticRegression(max_iter=1000, random_state=42) with and without class_weight="balanced", each in a StandardScaler pipeline, fitted on train_core only.
- Threshold: chosen on VALIDATION only. The highest threshold whose validation sensitivity ≥ 0.80; ties go to the higher specificity. Applied UNCHANGED to test.
- Test metrics: AUROC with a 95% bootstrap CI (1,000 resamples stratified by label, seed 42); sensitivity, specificity, PPV and NPV at 0.5 AND at the chosen threshold; confusion counts; Brier score.
- docs/ML_BASELINE_TEMPORAL.md: setup in 5 lines, the results table, then 3–5 honest sentences comparing with the old baseline (AUROC 0.7507, sensitivity 3.55% at 0.5, random 80/20 split, one cycle 2021–2023, 6,014 adults). Explain why a time split is a stricter, more honest test. No over-claiming.

PART C — docs/ML_FEATURE_MAP.md (the most important output today)
A model only helps if the app can give it the same inputs at check-in time. One row per candidate feature, with columns:
| Feature | App field today (exact name + file:line in main.py / app_store.py, or "not collected") | How the app gets it (profile / check-in reading / record / derived) | NHANES column (nhanes_core) | BRFSS column (brfss_core) | Units + conversion | Missing % NHANES adults / BRFSS | Suggested for basic model? (Usman decides) | Suggested for full model? (Usman decides) | Leakage risk (which label it would leak) |
Candidates at minimum: age (from date_of_birth), sex (sex_at_birth), height, weight, BMI (derived), waist, smoking (smoking_status vs ever_smoked_100 / smoker_status), family history of diabetes, physical activity, diabetes diagnosis year (→ duration), hypertension diagnosis year, comorbidities (comorbidities json: list its keys from the code), on_insulin_or_sulfonylurea, BP meds, glucose reading, BP reading, HbA1c, total cholesterol, income/education (and say why we should NOT use them in a clinical tool).
Fill the app column FROM THE CODE (cite file:line). Don't trust this prompt's list.
Then a section "Features the app would need to start collecting": each with a proposed question wording (en + ur), marked "proposed, needs Usman + doctor review". Don't add them to the app.

PART D — docs/ML_LABEL_CATALOGUE.md
Per disease, the possible label definitions, each with: exact formula on nhanes_core columns (and the BRFSS equivalent if one exists); prevalence per split (numerator/denominator); the list of FORBIDDEN input features under the leakage rule; and a 3-line trade-off note. At least:
- diabetes: told; measured (hba1c ≥ 6.5 or fpg ≥ 126); told OR measured; undiagnosed only; prediabetes (hba1c 5.7–6.4 or fpg 100–125, not diabetic)
- hypertension: told; on meds; told OR meds; measured ≥ 130/80; measured ≥ 140/90; told OR meds OR measured ≥ 130/80
DON'T choose. Give the facts and the trade-offs; Usman chooses in ML_PLAN.md. Put "DRAFT FOR USMAN" at the top of both the feature map and the label catalogue.
Also create backend-poc-technical/ml/labels.py: a LABELS registry (name → function(df) -> Series[int|NaN], plus a forbidden_features list), implementing exactly the catalogue. No eval of strings.

PART E — Tests (ml-tests job)
- test_splits.py: disjointness, union, the cycle rule, JSON shape (on a synthetic frame with fake cycles)
- test_baseline_temporal.py: on a synthetic frame, the threshold is chosen ONLY from validation. Build the test so that if test data were used, the chosen threshold would differ and the assert would fail.
- test_labels.py: every label on hand-made rows (including NaN handling: missing inputs give NaN, never 0), and forbidden_features correct for each

TRAPS
- NaN in a label column means "unknown", never 0. Drop or keep explicitly, and report counts.
- Bootstrap: resample indices with replacement within each label class, so tiny positive counts don't produce degenerate AUROCs.
- Age top-coding (80/85) is a small bias. Mention it.

ACCEPTANCE
 S2-01 Split JSON written; asserts pass (output pasted)
 S2-02 Baseline doc regenerated (output pasted); threshold from validation only (test)
 S2-03 Feature map: every row filled; app fields cited with file:line
 S2-04 Label catalogue + labels.py registry; tests pass
 S2-05 Protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/ml/{splits.py, baseline_temporal.py, labels.py}, backend-poc-technical/ml/tests/{test_splits.py, test_baseline_temporal.py, test_labels.py}, docs/ML_BASELINE_TEMPORAL.md, docs/ML_FEATURE_MAP.md, docs/ML_LABEL_CATALOGUE.md
Change: backend-poc-technical/ml/common.py, docs/DATA_CHECKS.md (Split section), backend-poc-technical/ml/requirements.txt (if needed), docs/ai-usage/saad.md

PR TITLE: I2-1 Day 2: temporal split, fair baseline, feature map, label catalogue
```

---

### DAY 3 — Wednesday 28 Oct — Evaluation toolkit for Usman's models + model artifact contract

```text
YOUR TASK (DAY 3, SAAD): build the tested evaluation toolkit that Usman's training code will call: threshold choice, metrics with confidence intervals, calibration, subgroup breakdowns, the leakage check and the report writer. Also write the "model artifact contract", the exact format in which Usman's code saves a trained model so your external-validation code (Day 6) can load it. You do NOT choose labels, features or models, and you do NOT train risk models today. That is Usman's part. Branch: feat/i2-1-eval-toolkit.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

WHO OWNS WHAT (read this twice)
- USMAN owns the modelling: docs/ML_PLAN.md, the final labels and features, the experiment harness (backend-poc-technical/ml/experiments/), the model training and tuning, model selection, the SHAP explanations, and wiring the risk card into the app.
- SAAD (you, today) builds the tools Usman's code calls, and proves they are correct. Your code is a library: pure functions with no hidden choices. Every choice is an argument with a documented default.
- If backend-poc-technical/ml/experiments/ already exists (Usman may have started it), DON'T edit it. Read it, so your function signatures fit how it calls things, and list any mismatch in "OPEN QUESTIONS FOR USMAN / DOCTOR".

READ FIRST: docs/ML_FEATURE_MAP.md and docs/ML_LABEL_CATALOGUE.md (Day 2); backend-poc-technical/ml/labels.py, splits.py, common.py, baseline_temporal.py; docs/ML_PLAN.md and backend-poc-technical/ml/experiments/ if they exist; handbook B8 (risk model design) and C14 (ML today).

PART A — backend-poc-technical/ml/evaluation.py (pure functions; numpy / pandas / scikit-learn only; every random step takes a seed)
 A1. choose_threshold(y_val, p_val, policy) -> dict
     - policy {"type": "min_sensitivity", "value": 0.80}: the HIGHEST threshold whose sensitivity on the given data is ≥ value; ties → the higher specificity. If no threshold reaches it, return the one with the highest sensitivity and set "met": false.
     - policy {"type": "fixed", "value": x}: returns x
     - policy {"type": "youden"}: maximises sensitivity + specificity − 1
     - It only ever receives VALIDATION arrays. Its docstring says so in capitals.
     - Returns {"threshold", "policy", "met", "val_sensitivity", "val_specificity"}.
 A2. metrics_at_threshold(y, p, t) -> dict: tp, fp, tn, fn, sensitivity, specificity, ppv, npv, f1, plus prevalence and n. A zero denominator gives None, never a crash or a fake 0.
 A3. bootstrap_ci(y, p, metric_fn, n_boot=1000, seed=42, stratified=True, alpha=0.05) -> (point, low, high). Resample within each label class. A resample with only one class is skipped and counted; report the skipped count.
 A4. auroc(y, p) and auprc(y, p): thin wrappers over sklearn that return None when only one class is present.
 A5. calibration(y, p, n_bins=10) -> dict:
     - Brier score
     - calibration-in-the-large (mean p − mean y)
     - intercept and slope from a logistic regression of y on logit(p), with p clipped to [1e-6, 1 − 1e-6]
     - reliability table: quantile bins with n, mean_p and observed rate
 A6. subgroup_report(df, y_col, p_col, threshold, groups, min_n=50) -> list of rows
     - default groups: sex_male; age band (18–39, 40–59, 60+); race_eth (with its NHANES code meanings as labels); cycle
     - per group: n, prevalence, AUROC, and sensitivity/specificity at the SAME threshold
     - a group with n < min_n or fewer than 10 positives → the metrics are "too few" (never computed)
     - Why it matters: a model that misses many diabetics in one group is unsafe even with a good overall AUROC.
 A7. check_leakage(label_name, features) -> None. Raises LeakageError naming every forbidden feature, using labels.LABELS[label_name].forbidden_features. Also raises if a feature isn't a column of nhanes_core. It's called BEFORE any data is loaded.
 A8. write_eval_report(path, sections: dict) -> None: writes a markdown report with the fixed sections "Config", "Data", "Validation", "Test", "Calibration", "Subgroups", "Limitations". A missing section is written as "NOT RUN", never left out. The Limitations section always includes: US survey population, not South Asian; survey weights not used in training; NHANES age top-coding; self-report labels where the label uses them.
 A9. plots.py (optional, matplotlib): roc_plot, reliability_plot. Save only to backend-poc-technical/ml/outputs/ (git-ignored). Never commit PNGs.

PART B — The model artifact contract: docs/ML_INTERFACES.md + backend-poc-technical/ml/artifacts.py
 B1. A trained model is a folder backend-poc-technical/ml/outputs/models/<model_name>/ with:
     - model.joblib: the full fitted sklearn Pipeline (preprocessing + model), so predict_proba works on raw feature columns
     - model_card.json with the required keys: name, owner, created_at (UTC ISO), git_commit, label (a key in labels.LABELS), features (an ordered list), threshold, threshold_policy, split (e.g. "nhanes_temporal_v1"), model_type, hyperparameters, sklearn_version, train_rows, val_rows, val_auroc, notes
 B2. artifacts.py:
     - save_model_artifact(pipeline, card, out_dir)
     - load_model_artifact(dir) -> (pipeline, card)
     - validate_model_card(card): a clear error for a missing or unknown key, an unknown label, a feature list that fails check_leakage, a threshold outside [0, 1], or a sklearn_version different from the installed one (that one is a WARNING, not an error)
 B3. docs/ML_INTERFACES.md:
     - the folder layout, every card key with its type and an example
     - which function Usman's harness calls at which step (check_leakage → fit → choose_threshold on validation → metrics/calibration/subgroups on test → save_model_artifact)
     - what Day 6's external validation reads
     - the header "DRAFT — Usman approves or changes this before his harness depends on it"

PART C — Use the toolkit on YOUR OWN baseline only (proves it works end to end; no new modelling)
 C1. Refactor baseline_temporal.py (Day 2) to call evaluation.py instead of its own metric code. The numbers must come out the same: paste both outputs side by side. A difference has to be explained.
 C2. Save the class_weight="balanced" baseline as the artifact outputs/models/baseline_temporal_lr/ (owner "saad", notes "S-6 features age/sex/BMI on the temporal split; a reference point, not a product model").
 C3. Regenerate docs/ML_BASELINE_TEMPORAL.md with the new sections: calibration (Brier, intercept, slope, reliability table) and subgroups.
 C4. 3–5 honest sentences on what the subgroup table shows (e.g. whether sensitivity differs by age band or race_eth). No over-claiming.

PART D — Tests (ml-tests job): backend-poc-technical/ml/tests/test_evaluation.py and test_artifacts.py, synthetic data only
 - choose_threshold: hand-made arrays with a known answer for each policy; the "met": false path; the tie rule
 - metrics_at_threshold: the exact confusion counts on a 10-row example; zero denominators → None
 - bootstrap_ci: the same seed → identical results; a different seed → a different interval; stratification keeps the class counts; the single-class skip count
 - calibration: perfectly calibrated synthetic data (y ~ Bernoulli(p), n = 20,000, seed 42) → slope within 0.9–1.1 and intercept within ±0.1; p squeezed toward 0.5 → slope > 1 (shows it detects under-confidence)
 - subgroup_report: a group under min_n → "too few"; the threshold is the same across groups
 - check_leakage: hba1c as a feature for a measured-diabetes label → LeakageError naming hba1c; an unknown feature → an error
 - write_eval_report: every section heading is present; a missing section prints NOT RUN
 - artifacts: a round trip (save → load → the same predictions on 5 rows); every validate_model_card failure; the version-mismatch warning (pytest.warns)
 - a "no test peeking" guard test: monkeypatch choose_threshold, run baseline_temporal's main flow on a synthetic split, and assert the arrays it received are exactly the validation rows (compare the index sets)

TRAPS
- sklearn's roc_curve thresholds include inf. Drop it before choosing.
- Don't compute the calibration slope with p of exactly 0 or 1 (logit = ±inf): clip.
- joblib files can be large. They live only under ml/outputs/, which is git-ignored (Day 1). Check git status before committing.
- A sklearn version mismatch between machines can break joblib loading. That's why the card stores sklearn_version.

ACCEPTANCE
 S3-01 evaluation.py functions all implemented; tests pass (counts pasted)
 S3-02 Calibration test proves slope ≈ 1 on calibrated data and > 1 on squeezed data
 S3-03 Artifact contract doc + artifacts.py; round-trip test passes
 S3-04 Baseline refactored onto the toolkit; numbers unchanged (shown side by side)
 S3-05 baseline_temporal_lr artifact saved locally (path shown, NOT committed); ML_BASELINE_TEMPORAL.md regenerated with calibration + subgroups
 S3-06 No training of new risk models, no edits to ml/experiments/ (git diff --stat proves it)
 S3-07 No outputs/ or data in git; protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/ml/{evaluation.py, artifacts.py, plots.py}, backend-poc-technical/ml/tests/{test_evaluation.py, test_artifacts.py}, docs/ML_INTERFACES.md
Change: backend-poc-technical/ml/baseline_temporal.py, backend-poc-technical/ml/common.py, backend-poc-technical/ml/requirements.txt (joblib/matplotlib pinned, if not already present), docs/ML_BASELINE_TEMPORAL.md, docs/ai-usage/saad.md
Never: backend-poc-technical/ml/experiments/ (Usman's), docs/ML_PLAN.md (Usman's), labels.py label definitions (if one looks wrong, list it as an open question)

PR TITLE: I2-1 Day 3: ML evaluation toolkit + model artifact contract
```

---

### DAY 4 — Thursday 29 Oct — Trend agent: spec, module, reading history, tests

```text
YOUR TASK (DAY 4, SAAD): a pure, well-tested trend agent that tells the patient and clinician, per reading type, whether it is rising, stable, falling, or there isn't enough history yet. It is ADVISORY: it never changes a triage level. Branch: feat/i2-6-trend-agent.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: you may ADD one new read-only function to backend-poc-technical/data_sources/app_store.py. You may import constants from agents/triage_protocol.py (read-only). No other changes to existing backend code.

READ FIRST: handbook B2/B3 (trend agent), C5 (baseline rule); backend-poc-technical/agents/triage_protocol.py (compute_baseline, BASELINE_WINDOW_DAYS = 14, BASELINE_MAX_READINGS = 7, BASELINE_MIN_READINGS = 3); backend-poc-technical/data_sources/app_store.py get_user_baseline_history (around line 1890: it reads completed, non-emergency check-ins' intakes_json readings plus isolated-mode Local Store observations); how intakes store readings (search main.py for intake.get("readings") and observation_type); whether a glucose context (fasting / before meal / after meal / bedtime) is stored anywhere in the intake (search for glucose_context).

PART A — docs/TREND_AGENT.md (write it first; then build exactly this)
 1. Purpose and the advisory-only rule (never changes a level; never shown as a diagnosis).
 2. Inputs: the same sources as get_user_baseline_history, but a configurable window (default 30 days for the trend view). The 14-day triage baseline is untouched.
 3. Types: blood_pressure_systolic, blood_pressure_diastolic, glucose. Glucose by context: if intakes store a glucose context, compare only within the same context. If not, treat all glucose as one series and record that as a limitation.
 4. Method:
    - sort by time and de-duplicate identical timestamps (keep the latest)
    - n < BASELINE_MIN_READINGS (import it) → "not_enough_history"
    - split into an earlier half and a recent half (for odd n, the middle reading goes to the recent half)
    - change = median(recent) − median(earlier)
    - Theil–Sen slope per week as a cross-check: the median of the pairwise slopes, implemented in pure Python (n ≤ 14 pairs is fine). NO scipy: the backend requirements don't include it.
    - "rising" only if change ≥ +threshold AND the slope is > 0; "falling" only if change ≤ −threshold AND the slope is < 0; otherwise "stable"
 5. Thresholds in ONE constants block, each commented "PROPOSED — needs Usman + doctor review": systolic 10 mmHg, diastolic 5 mmHg, glucose 20 mg/dL.
 6. Output per type: {"direction", "n", "window_days", "first_at", "last_at", "median_earlier", "median_recent", "change", "slope_per_week", "values": [{"value", "at"}] (max 14, oldest → newest)}, plus top-level {"generated_at", "advisory": true}.
 7. Labels in en / ur / roman_ur for the 4 directions + "n readings in N days" (simple Urdu, marked needs_native_review).
 8. Edge cases: one outlier (must not flip direction by itself: show why the median plus slope agreement protects against it); a long gap; None values; non-numeric values; values outside the app's plausible ranges (excluded, and counted in "excluded"); timezone handling (all UTC ISO with "Z").

PART B — Code
 B1. backend-poc-technical/agents/trend_agent.py: pure, stdlib only, no I/O:
       compute_trends(history: list[dict], now: str | None = None, window_days: int = 30) -> dict
     A `now` argument for deterministic tests. Imports BASELINE_MIN_READINGS from agents.triage_protocol (never copies the number). Exposes the TREND_LABELS dict.
 B2. backend-poc-technical/data_sources/app_store.py: ADD
       get_user_reading_history(user_id, days=30, backend=None, db_path=None, mysql_url=None, ssl_ca=None) -> list[dict]
     modelled on get_user_baseline_history (same scoping, same exclusions: completed, non-emergency; plus isolated-mode Local Store observations), returning {"observation_type", "value", "timestamp", "source": "checkin" | "local_store", "checkin_id" (if any), "glucose_context" (if stored)}. Do NOT modify get_user_baseline_history or any existing function.
 B3. No API and no UI today.

PART C — Tests (add both files to the ci.yml pytest list)
 C1. backend-poc-technical/test_trend_agent.py: 40+ cases with parametrize:
     - 0/1/2 readings → not_enough_history; exactly 3 → a direction
     - clear rising / falling / stable for each type
     - just below and just at the threshold
     - a single spike doesn't flip direction
     - median and slope disagreeing → stable
     - the window boundary (a reading 31 days old ignored at window 30)
     - None / non-numeric / out-of-range excluded and counted
     - duplicate timestamps
     - values capped at 14, oldest → newest
     - odd/even n split rule
     - the exact output schema keys
     - labels present in en/ur/roman_ur
     - monkeypatch BASELINE_MIN_READINGS to 4 → the behaviour changes (proves the import is used)
     - "advisory": true always
     - the module exposes no function that returns or modifies a triage level (inspect the module's names)
 C2. backend-poc-technical/test_reading_history.py, against a temp SQLite DB (use the same fixtures as the existing app_store tests; read them first):
     - only the user's own readings appear
     - emergency check-ins are excluded; incomplete check-ins are excluded
     - the window is respected
     - isolated-mode Local Store observations are included, with source "local_store"
     - CHECKIN- copies in the Local Store are not double-counted (mirror the baseline function's rule)
 C3. Mutation proof in scripts/verify_mutations.py: make compute_trends ignore the median-and-slope agreement rule (use the median alone) → a test must KILL it.

ACCEPTANCE
 S4-01 The spec is written, and every rule maps to code (cite the lines)
 S4-02 The module is pure stdlib, with the imported constant used
 S4-03 40+ trend tests and the reading-history tests pass (counts pasted)
 S4-04 app_store.py gained exactly one function (show git diff for that file)
 S4-05 Mutation added and killed
 S4-06 Protected hashes identical; all gates green
 S4-07 3 worked examples (input → output JSON) pasted in the report

FILES ALLOWED
Create: docs/TREND_AGENT.md, backend-poc-technical/agents/trend_agent.py, backend-poc-technical/test_trend_agent.py, backend-poc-technical/test_reading_history.py
Change: backend-poc-technical/data_sources/app_store.py (ADD one function only), scripts/verify_mutations.py (append), .github/workflows/ci.yml (pytest list), docs/ai-usage/saad.md

PR TITLE: I2-6 Day 4: trend agent module + reading history + tests
```

---

### DAY 5 — Friday 30 Oct — Trends live (API, patient screen, provider detail) + bug bash

```text
YOUR TASK (DAY 5, SAAD): trend arrows visible on the site, for the patient on the trend screen and for the clinician in review detail, in English and Urdu, with real data and never fake values. First, find out whether the live trend screen even shows data today. Branch: feat/i2-6-trend-live.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: main.py (ONE new route + ONE additive optional field on ReviewDetailResponse), app/components/TrendScreen.tsx, the provider detail component(s), app/lib/api.ts, app/translations/index.ts, docs/AUTH.md. No triage, interview, reconciliation or verification code.

READ FIRST: docs/TREND_AGENT.md; agents/trend_agent.py; app_store.get_user_reading_history; main.py: GET /api/checkins (UserCheckinSummaryResponse: checkin_id, mode, record_patient_id, status, version, started_at, completed_at, emergency, requires_review, max_severity, review_status — NO readings), GET /api/provider/review/{checkin_id} and ReviewDetailResponse (and how it resolves the patient); app/components/TrendScreen.tsx (live mode loads check-in summaries, then looks for c.primary_reading / c.observations, which the summary response doesn't contain); app/components/provider/PatientDetailScreen.tsx and ReconciliationAlertDetail.tsx; app/translations/index.ts; app/context/AppContext.tsx (isLiveMode).

PART A — Diagnose the current live trend screen (no fix yet)
 A1. Run the backend + frontend locally in live mode (Firebase auth mode as in docs/LOCAL_SETUP_VERIFIED.md, or the test-auth path the team uses locally; follow the docs). As a fake patient, complete 3 check-ins with readings.
 A2. Open the trend screen and screenshot it. State, with the code lines, whether the charts are empty and why.
 A3. If you can't run live mode locally, show the problem with a Vitest test that renders TrendScreen in live mode with a mocked GET /api/checkins response shaped exactly like UserCheckinSummaryResponse, and assert what it shows.

PART B — Backend
 B1. GET /api/me/trends?days=30 (require_role patient; days 7–90, else 422). It calls get_user_reading_history + compute_trends and returns the schema from TREND_AGENT.md. Add a Pydantic response model (TrendSeries, TrendsResponse).
 B2. Add an optional field `trends: Optional[TrendsResponse] = None` to ReviewDetailResponse, filled for the patient of that check-in, resolved EXACTLY as the review detail already resolves the patient (don't add a new lookup path). Window 30 days. If the trend computation fails, return trends = null and log the exception type only. The review must never fail because of trends.
 B3. docs/AUTH.md: add the new route to the matrix.
 B4. backend-poc-technical/test_trends_api.py (add to CI):
     - 401 without a token; 403 for the provider role on /api/me/trends
     - a patient only sees their own trends
     - days validation
     - no readings → every type not_enough_history
     - mixed types
     - emergency check-ins excluded
     - exact response shape
     - provider review detail contains trends for the right patient and null when computation raises (monkeypatch)

PART C — Frontend
 C1. app/lib/api.ts: types + getMyTrends(days=30).
 C2. TrendScreen, LIVE mode only (demo mode untouched):
     - load GET /api/me/trends instead of deriving readings from check-in summaries
     - charts plot the real values (values[]) for each type the patient has (conditions from the profile)
     - per type, a badge: icon (↑ / → / ↓ / "…") + text label (translated) + "N readings in 30 days". Colour is never the only cue.
     - not_enough_history: "Not enough readings yet. Trends appear after 3 check-ins." (translated)
     - an API error shows an error state with retry, NEVER a default "stable"
     - loading skeleton
     - RTL in Urdu; numbers and units in <bdi>; dates in a locale-appropriate format
     - aria-label on each badge ("Systolic blood pressure rising, 5 readings in 30 days")
 C3. Provider detail (wherever the review detail renders): a compact "Trends (30 days)" row per type: the badge + the last 3 values with dates. Hidden if trends is null; "not enough history" shown as text.
 C4. app/translations/index.ts: every new key in en AND ur.
 C5. Vitest: tests/trends.test.tsx:
     - each direction renders its icon and text
     - not_enough_history text
     - error state (no arrow shown)
     - Urdu rendering (dir="rtl")
     - the provider row renders and hides on null
     - no-fake-values: no badge when data is absent

PART D — Manual check
Re-run the Part A setup → screenshot the patient trend screen (en + ur) and the provider review detail with trends.

PART E — Bug bash (1 hour, with Hassaan, on https://chronicare-ai.netlify.app with FAKE accounts)
Try to break: sign-up/sign-in, consent, inclusion, profile units, EHR connect/disconnect, check-ins en/ur/roman_ur (typed + voice), the record pages, trends, the provider queue/detail, admin. File GitHub issues: title, steps, expected, actual, screenshot, browser/device, language, severity guess. Labels: "bug", "week2-bash". Paste the links.

ACCEPTANCE
 S5-01 The Part A diagnosis is pasted, with a screenshot or test
 S5-02 The new route + additive field; tests pass (counts)
 S5-03 TrendScreen live uses /api/me/trends; demo mode unchanged
 S5-04 Provider row shown; the review never fails because of trends (test)
 S5-05 en + ur screenshots; vitest passes
 S5-06 Bug-bash issues filed
 S5-07 Protected hashes identical; all gates green

FILES ALLOWED
Change: backend-poc-technical/main.py (one route + one optional field + models), app/components/TrendScreen.tsx, app/components/provider/PatientDetailScreen.tsx and/or ReconciliationAlertDetail.tsx, app/lib/api.ts, app/translations/index.ts, docs/AUTH.md, .github/workflows/ci.yml (pytest list), docs/ai-usage/saad.md
Create: backend-poc-technical/test_trends_api.py, tests/trends.test.tsx

PR TITLE: I2-6 Day 5: trends live (API, patient screen, provider detail)
```

---

### DAY 6 — Saturday 31 Oct — Dataset loaders + external validation + DHS skeleton

```text
YOUR TASK (DAY 6, SAAD): test whether the models USMAN trained and saved hold up on DIFFERENT data (external validation), and prepare a loader for the South Asian DHS data so it plugs in the day approval arrives. Branch: feat/i2-1-external-validation.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

READ FIRST: docs/ML_INTERFACES.md, backend-poc-technical/ml/artifacts.py and evaluation.py (Day 3; reuse them, don't copy them); docs/ML_PLAN.md and docs/ml/EXPERIMENTS_SUMMARY.md if Usman has written them; docs/ML_FEATURE_MAP.md; labels.py.

MODELS TO VALIDATE: every folder under backend-poc-technical/ml/outputs/models/ (Usman's saved models + your baseline_temporal_lr reference). Print the list of model names and their card labels/features (never data). If Usman has saved none yet, validate baseline_temporal_lr only, and say so at the top of the doc: "Only the reference baseline was available; Usman's models are to be added by re-running this script."

DATA (from Usman's dataset folder, already under $CHRONICCARE_DATA_DIR; check each exists and print only the paths found / missing, never the contents. File names inside a folder may differ slightly: list the .csv names in each folder (names only) and pick the one matching the description):
  cardio70k/cardio_train.csv            (semicolon-separated; age in DAYS; ap_hi/ap_lo; gender; cholesterol and gluc are categorical 1/2/3; cardio target)
  framingham/framingham.csv             (4,238 rows)
  brfss2015_kaggle/diabetes_binary_health_indicators_BRFSS2015.csv (and the other 2)
  pima/<the .csv in that folder>        (no header: Pregnancies, Glucose, BloodPressure, SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome)
If a file is missing, skip that dataset and write NOT RUN for it.

PART A — backend-poc-technical/ml/datasets/ (one loader per dataset; each returns (df_with_standard_names, cleaning_report: dict); pure pandas)
 A1. cardio70k.py:
     - age_years = age_days / 365.25
     - gender: the dataset's own description says which code is which. CHECK it against the data (the group with the greater mean height should be men) and print the evidence. Never assume.
     - BP cleaning, with a count for every rule:
       (1) negative → NaN
       (2) ap_hi < ap_lo: swap only if BOTH are in range after swapping, else NaN
       (3) values like 1100, 14020, 16020 → NaN (no "divide by 10" guessing)
       (4) out of the app ranges (systolic 60–260, diastolic 30–160) → NaN
       (5) systolic <= diastolic after the steps above → NaN
     - bmi from height and weight (with plausibility 12–80)
     - standard names: age, sex_male, bmi, sbp, dbp, current_smoker, chol_cat, gluc_cat, cvd
 A2. framingham.py: age, sex_male (from "male"), bmi, sbp (sysBP), dbp (diaBP), current_smoker, diabetes, prevalent_hyp, glucose, total_chol (totChol), bp_meds (BPMeds). Report the NA count per column.
 A3. brfss2015_kaggle.py: map the 21 indicators to our names (HighBP → high_bp, HighChol, BMI → bmi, Smoker → ever_smoker, PhysActivity → phys_active, Sex → sex_male (check the coding), Age (13 groups) → age_group plus age_mid (the documented midpoint per group: 18–24 → 21, …, 80+ → 82), Diabetes_binary → diabetes).
 A4. pima.py: zeros in Glucose, BloodPressure, SkinThickness, Insulin and BMI are MISSING values in this dataset → NaN, with counts; standard names.
 A5. All loaders: deterministic, with the cleaning report printed and saved to docs/ml/datasets/<name>_cleaning.md (counts only).

PART B — backend-poc-technical/ml/external_validation.py
 B1. CLI: python backend-poc-technical/ml/external_validation.py [--models <name> ...]   (default: all saved models). Re-running it later with Usman's new models must need no code change.
 B2. For each (model, external dataset) pair whose label has an equivalent in that dataset (the table in B4):
     - If every feature in the card exists in the dataset (after the loader's mapping): load the pipeline and score directly ("as-saved").
     - If some features are missing: list them, and ALSO run an "overlap refit". Refit the SAME model_type + hyperparameters from the card on NHANES train_core using only the overlapping features, then choose the threshold on NHANES validation with the card's threshold_policy (evaluation.choose_threshold). This is mechanical, not a modelling choice; label it "overlap refit, not Usman's saved model" everywhere it appears.
     - If the overlap is under 2 features: NOT RUN, with the reason.
 B3. The threshold is the card's (as-saved) or the NHANES-validation one (overlap refit). It is NEVER re-tuned on external data.
 B4. Label equivalents (a pair runs only if the model's card label matches the left side):
     - diabetes labels (told / told_or_measured) → Kaggle BRFSS 2015 Diabetes_binary; our brfss_core diabetes; Pima Outcome (women 21+, Pima heritage, measured OGTT label)
     - hypertension labels (told / told_or_meds / …) → Framingham prevalent_hyp; brfss_core high_bp; cardio70k "BP ≥ 130/80 from the cleaned readings" (ONLY for models with no BP feature)
     Per pair: n, prevalence, AUROC + 95% bootstrap CI (evaluation.bootstrap_ci), sensitivity/specificity at the threshold, calibration-in-the-large, Brier, mode (as-saved / overlap refit), and the missing features.
 B5. docs/ML_EXTERNAL_VALIDATION.md: the results table plus an honest discussion of:
     - label differences (self-report vs measured vs OGTT)
     - population differences (US national survey vs a 1940s–1960s US cohort vs one ethnic group vs online cardio data)
     - feature-mapping losses (age groups → midpoints)
     - what the drop in AUROC (if any) means
     - an explicit statement that NONE of these is a South Asian population, so DHS validation is still required

PART C — DHS skeleton (no data yet): backend-poc-technical/ml/datasets/dhs.py
 - The loader interface: load_dhs(country: "india_nfhs5" | "bangladesh_2017" | "nepal_2022", path) → (df, report), via pandas.read_stata (DHS distributes Stata .DTA among other formats).
 - If the files are missing: raise DhsDataNotAvailable with a clear message.
 - EXPECTED_VARIABLES: a dict of the measures we need (systolic and diastolic BP readings, random/fasting blood glucose, age, sex, height, weight, current BP medicine). EVERY variable code is marked "TO CONFIRM against the DHS recode manual when the files arrive". Don't present guessed codes as facts.
 - Docstring: DHS household-member (PR) recode files usually hold the biomarker measurements; confirm this from the dataset's documentation on arrival.
 - Test: missing files → DhsDataNotAvailable.

PART D — Tests (ml-tests job)
 - test_datasets.py: per loader, on TINY synthetic frames: each cleaning rule and its count (cardio swap rule, the 16020 rule, Pima zeros, the BRFSS age midpoints)
 - test_external_validation.py (using a tiny synthetic artifact saved with artifacts.save_model_artifact): the threshold is never re-tuned on external data (spy on choose_threshold: only NHANES-validation arrays are ever passed); as-saved vs overlap-refit mode chosen correctly; the overlap < 2 → NOT RUN; a missing dataset → NOT RUN, not a crash; a label with no equivalent → the pair is skipped
 - test_dhs.py: the clear error when files are absent

ACCEPTANCE
 S6-01 Every loader's cleaning report pasted (counts only)
 S6-02 The cardio gender coding verified with evidence
 S6-03 External validation run on every saved model; table pasted; the threshold not re-tuned (test); no new models designed
 S6-04 ML_EXTERNAL_VALIDATION.md honest and complete
 S6-05 The DHS skeleton with every code marked TO CONFIRM; test passes
 S6-06 No data in git; protected hashes identical; all gates green

FILES ALLOWED
Create: backend-poc-technical/ml/datasets/{__init__.py, cardio70k.py, framingham.py, brfss2015_kaggle.py, pima.py, dhs.py}, backend-poc-technical/ml/external_validation.py, backend-poc-technical/ml/tests/{test_datasets.py, test_external_validation.py, test_dhs.py}, docs/ML_EXTERNAL_VALIDATION.md, docs/ml/datasets/*.md
Change: backend-poc-technical/ml/common.py, backend-poc-technical/ml/data_prep/README.md (where to put the Kaggle files), backend-poc-technical/ml/requirements.txt (if needed), docs/ai-usage/saad.md

PR TITLE: I2-1 Day 6: external validation + dataset loaders + DHS skeleton
```

---

### DAY 7 — Sunday 1 Nov — Coverage, fixes, MIMIC script, RAG test set, phrase test round 2, weekly log

```text
YOUR TASK (DAY 7, SAAD): leave the codebase stronger than you found it. Measure test coverage, close real gaps with tests, fix the week's NON-safety bugs (each with a regression test), write the MIMIC trend sanity script for Saad to run HIMSELF outside any AI tool, and write the weekly log. Branch: test/i2-8-hardening.

================ COMMON RULES (apply to everything in this prompt) ================

CONTEXT
- Repo: github.com/UsmanBari/ChronicCare-AI. Backend in backend-poc-technical/ (FastAPI, Python 3.11). Frontend in the repo root (Next.js 14 static export, TypeScript, Tailwind). Docs in docs/.
- This is a medical decision-support prototype for adults with type 2 diabetes and/or hypertension. It never diagnoses, never gives treatment or dose advice, and never lowers a triage level. Motto: "the model proposes, the rules decide".
- The full project handbook is Appendix A of docs/tasks/WEEK2_SAAD.md. Read Part 0 of it before doing anything, and the parts this prompt points to.
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

PERMISSION FOR TODAY: new test files anywhere under backend-poc-technical/ and tests/; NON-safety source files ONLY where a bug-bash fix requires it (one minimal change per issue). Safety files: tests may be ADDED that document current behaviour, but their code is never changed.

ABSOLUTE RULE: you never open, list, read, run or print anything from MIMIC. You only WRITE the script in Part D.

READ FIRST: the GitHub issues labelled "week2-bash" (gh issue list --label week2-bash --state open, or the links Saad pastes); handbook C3 (repo map) and C12 (evidence).

PART A — Coverage
 A1. pip install pytest-cov into the venv (NOT into requirements.txt). Run:
       python -m pytest backend-poc-technical/scenarios/ backend-poc-technical/test_*.py -q -k "not run_source_blind_test" --cov=backend-poc-technical --cov-report=term-missing
     Save the summary. For the frontend: if vitest coverage works without adding heavy dependencies, run it; otherwise write NOT RUN with the reason.
 A2. docs/TEST_COVERAGE.md: the overall %, per-module % (backend), the 10 least-covered modules, and for each, the important behaviours that are untested (read the code; be specific: function + branch).

PART B — New tests (≥ 30, meaningful; no "assert True")
Target the least-covered NON-safety modules first: data_sources/fhir_adapter.py edge cases (missing units, components in BP panels, unknown LOINC), data_sources/medication_scope.py (status filter, de-duplication, limit 8, ordering), data_sources/local_store.py and app_store.py read functions, auth error paths (expired, wrong audience, missing kid), and main.py error responses (404/409/422/403 on record, EHR and review routes).
For safety modules you may ADD tests that pin current behaviour. If such a test exposes a REAL bug, DON'T fix it: mark it pytest.mark.xfail(strict=True, reason="<issue link>"), open a GitHub issue assigned to Usman, and list it in the report.
Re-run coverage and paste the before/after numbers.

PART C — Bug-bash fixes (NON-safety areas only: UI, record pages, trends, admin, provider display, translations, docs)
For each such issue:
 1. write a FAILING regression test that reproduces it (run it, show it fails)
 2. fix it with the smallest change
 3. show the test passing
 4. commit "fix(<area>): <what> (closes #NN)"
For issues in SAFETY areas (triage, interview, red flags, reconciliation, verification): don't fix them. Comment your analysis on the issue, assign it to Usman, and list it in the report.

PART D — MIMIC trend sanity script (WRITE ONLY)
 D1. backend-poc-technical/ml/mimic/trend_sanity.py:
     - CLI: python backend-poc-technical/ml/mimic/trend_sanity.py --omr <path to omr.csv>   (REQUIRED argument, no default; refuse if the path is inside the repo)
     - Reads the MIMIC-IV hosp omr export with columns subject_id, chartdate, seq_num, result_name, result_value. Blood pressure rows have result_name "Blood Pressure" and result_value like "120/80". Parse them with the same plausibility ranges the app uses.
     - For each subject, slide 30-day windows. For each window with ≥ 3 BP readings, run agents/trend_agent.compute_trends (import it) on systolic and diastolic.
     - Builds ONE report dict of aggregates only:
       - subjects with ≥ 1 evaluable window; windows evaluated
       - the direction distribution (%) for systolic and diastolic
       - how often the direction flips between consecutive windows of the same subject
       - the median |change|
       - the share of windows where a naive "last minus first" method would disagree with ours
       - parse failures (count)
     - Prints ONLY that dict (json.dumps with indent). It must never print a subject_id, date, row or value list.
 D2. backend-poc-technical/ml/mimic/README.md, in bold at the top: "Run this yourself in a normal PowerShell window, NOT inside Antigravity or any AI tool. Paste only the printed summary into the PR."
 D3. backend-poc-technical/ml/tests/test_mimic_trend_sanity.py: on a tiny FAKE omr-like frame (made-up subject ids like 900001), check the aggregates, and that the printed output contains none of the fake subject ids or dates (capture stdout).
 D4. YOU DO NOT RUN IT ON REAL DATA. Saad runs it himself and pastes the summary into the PR description.

PART E — Weekly log: docs/weekly/2026-W44-saad.md (one page)
Done (each PR link + one line); numbers (rows checked, toolkit tests, external-validation pairs run with their AUROCs, trend tests, coverage before/after, tests added, issues closed); what slipped and why; open questions for Usman (label and feature choices for ML_PLAN.md, trend thresholds for doctor review); next week's top 3.

PART F — RAG retrieval test set (Usman builds the guideline RAG; you build the exam it must pass)
Read first: handbook B2 (explanation / RAG agent) and D5 (guideline corpus); docs/CLINICAL_RULES.md (what the app may and may not say).
F1. docs/rag/retrieval_test_set.json: 60 items, each:
    {"id": "R001", "condition": "diabetes"|"hypertension"|"both", "topic": short slug, "question_en": ..., "question_ur": ..., "question_roman_ur": ...,
     "expected_source": the guideline + section you expect to answer it (e.g. "ADA Standards of Care 2026 — Section 6, Glycemic Goals"), "expected_source_status": "TO CONFIRM against Usman's corpus",
     "answer_points": 2–4 short facts a correct answer must contain, "must_not": what a safe answer must never do (e.g. "give a dose", "say the patient has diabetes"), "kind": "explain" | "safety_redirect"}
    Mix: 25 diabetes, 25 hypertension, 10 both. At least 12 "safety_redirect" items where the right answer is to NOT advise and to send the patient to their clinician or emergency care (dose changes, stopping a medicine, chest pain with high BP, glucose 40 with confusion, pregnancy). Questions are written the way a patient types them, not like a textbook; at least 15 have spelling mistakes or mixed Urdu/English.
    Every answer_point must be checkable against a real guideline. Where you are not sure, mark "expected_source_status": "UNSURE" instead of guessing.
F2. scripts/rag/validate_test_set.py: schema check (all keys, unique ids, counts per condition/kind, all three languages non-empty, Urdu text actually in Urdu script). It prints the counts table. Add backend-poc-technical/test_rag_test_set.py, which runs the validator on the file (add it to CI).
F3. The Urdu and Roman Urdu are YOURS to check by hand (or Hassaan's). Mark the PR "Urdu reviewed by: <name>".

PART G — Independent phrase test, round 2 (your S-1 test found only 6 of 15 danger phrases)
G1. By hand, NOT by the AI, and without looking at the detector's phrase lists: write 30 NEW phrases into tests/sim/danger_phrases_independent_saad_r2.json, in the same format as your S-1 file: 15 danger + 15 safe or negated, mixing English, Roman Urdu and Urdu script. Commit it yourself before the agent starts Part G.
G2. The agent runs the existing phrase evaluator (scripts/eval_phrase_set.py; read how it's invoked) on the S-1 set AND the r2 set, against the CURRENT detector on dev (both interview engines if the evaluator supports it). Paste TP / FN / FP / TN, sensitivity and specificity for each set, and list every missed danger phrase.
G3. docs/INDEPENDENT_PHRASE_RESULTS_saad_r2.md: the two result tables, S-1 then vs now, and the missed phrases. DON'T change the detector (it's a protected safety file). Missed phrases go to Usman as one GitHub issue labelled "safety".

ACCEPTANCE
 S7-01 Coverage before/after pasted; TEST_COVERAGE.md written
 S7-02 ≥ 30 new meaningful tests passing (count pasted)
 S7-03 Each fixed issue: failing test shown → fix → passing; closing commit
 S7-04 Safety-area issues left unfixed with analysis and assignment
 S7-05 MIMIC script + README + fake-data test; the script never prints identifiers (test)
 S7-06 Weekly log written
 S7-07 Protected hashes identical; all gates green
 S7-08 RAG test set: 60 items, validator passes, counts table pasted, ≥ 12 safety_redirect items
 S7-09 Phrase test r2: hand-written file committed by Saad first; results for S-1 and r2 pasted; safety issue opened

FILES ALLOWED
Create: docs/TEST_COVERAGE.md, new test files (add every new backend test file to the ci.yml pytest list; ML tests go under ml/tests), backend-poc-technical/ml/mimic/{__init__.py, trend_sanity.py, README.md}, backend-poc-technical/ml/tests/test_mimic_trend_sanity.py, docs/weekly/2026-W44-saad.md, docs/rag/retrieval_test_set.json, scripts/rag/validate_test_set.py, backend-poc-technical/test_rag_test_set.py, docs/INDEPENDENT_PHRASE_RESULTS_saad_r2.md (tests/sim/danger_phrases_independent_saad_r2.json is committed by Saad by hand, not the agent)
Change: non-safety source files ONLY for bug-bash fixes (list each with its issue), .github/workflows/ci.yml (pytest list), docs/ai-usage/saad.md
Never: safety files' code, MIMIC data, the main requirements.txt.

PR TITLE: I2-8 Day 7: coverage, fixes, MIMIC script, RAG test set, phrase test r2, weekly log
If the day runs out: Parts F–G go in a second PR "I2-8 Day 7b: RAG test set + phrase test r2" by Monday 2 Nov morning.
PR BODY: Saad pastes the MIMIC summary (aggregates only) from his own run, or writes "MIMIC NOT RUN".
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
