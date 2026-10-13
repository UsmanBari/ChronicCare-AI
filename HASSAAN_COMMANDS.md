# Hassaan Task Command Sheet

This sheet turns `HASSAAN_Engineering_Guide_Commits_and_Viva.md` into copy-paste commands.

Use only commands for work you actually completed. Do not create empty commits, repeat the same change, or invent test results.

## 0. Initial Setup

Run once from PowerShell:

```powershell
$ErrorActionPreference = "Stop"
Set-Location "C:\Users\Dell\Documents\ChronicCare-AI"
git status --short --branch
git config user.name "Hassaan Mudassar"
git config user.email "i230536@isb.nu.edu.pk"
```

Check the current identity and branch:

```powershell
git config user.name
git config user.email
git branch --show-current
git remote -v
```

## 1. Start A Task Branch

Do not run this while you have uncommitted work. Check first:

```powershell
git status --short
```

For each task, start from the latest `dev` branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c <task-branch-name>
```

Use one of these branch names:

```text
test/h1-independent-urdu-phrases
test/h2-reconciliation-boundaries
test/h3-answer-validation-urdu
test/h4-local-store-ownership
docs/h5-system-test-results
test/h6-accessibility-remaining
```

If a branch already exists locally, use this instead:

```powershell
git switch <task-branch-name>
git pull --ff-only origin <task-branch-name>
```

## 2. Before Every Commit

Run these commands from the repository root:

```powershell
git status --short
git diff --check
git diff
```

Run the backend test suite from `backend-poc-technical`:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q
Set-Location ..
```

For frontend changes, also run from the repository root:

```powershell
npm test
```

Review only the files intended for this task:

```powershell
git status --short
git diff --stat
git diff -- <file-or-folder>
```

## 3. H-1: Independent Urdu Danger Phrases

Start the task branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c test/h1-independent-urdu-phrases
```

Open the required files and create the phrase set yourself:

```powershell
code tests/sim/danger_phrases_independent_hassaan.json
code docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md
code scripts/eval_phrase_set.py
```

Confirm both input files exist before running the evaluator:

```powershell
Test-Path "tests/sim/danger_phrases_independent_hassaan.json"
Test-Path "scripts/eval_phrase_set.py"
```

Run the evaluator from the backend directory:

```powershell
Set-Location "backend-poc-technical"
python ..\scripts\eval_phrase_set.py ..\tests\sim\danger_phrases_independent_hassaan.json
Set-Location ..
```

Run the focused tests:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q test_input_triage.py test_interview_bank.py
Set-Location ..
```

Review the actual files and commit only what you created or changed:

```powershell
git diff --check
git diff -- tests/sim/danger_phrases_independent_hassaan.json docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md scripts/eval_phrase_set.py
git add tests/sim/danger_phrases_independent_hassaan.json docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md scripts/eval_phrase_set.py
git diff --cached --check
git commit -m "test: add independent Urdu danger-phrase set and results"
git push -u origin test/h1-independent-urdu-phrases
```

Do not fill in TP, FN, FP, TN, sensitivity, or specificity until you have actually run the evaluator.

## 4. H-2: Reconciliation Boundary Tests

Start the task branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c test/h2-reconciliation-boundaries
```

Read the nearby fixture and implementation, then edit the test file:

```powershell
code backend-poc-technical/scenarios/fixtures.py
code backend-poc-technical/agents/reconciliation_agent.py
code backend-poc-technical/test_reconciliation_boundaries.py
```

Run the focused test:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q test_reconciliation_boundaries.py
Set-Location ..
```

Run the full backend suite before committing:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q
Set-Location ..
```

Review and commit the test file. Include implementation changes only if a real bug was found and intentionally fixed:

```powershell
git diff --check
git diff -- backend-poc-technical/test_reconciliation_boundaries.py backend-poc-technical/agents/reconciliation_agent.py
git add backend-poc-technical/test_reconciliation_boundaries.py
# Add the implementation file only if you made and verified a real fix:
# git add backend-poc-technical/agents/reconciliation_agent.py
git diff --cached --check
git commit -m "test: boundary cases for reconciliation window and thresholds"
git push -u origin test/h2-reconciliation-boundaries
```

## 5. H-3: Urdu And Roman Urdu Validation Tests

Start the task branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c test/h3-answer-validation-urdu
```

Open the implementation and test file:

```powershell
code backend-poc-technical/agents/answer_validation.py
code backend-poc-technical/test_answer_validation.py
```

Run the focused test:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q test_answer_validation.py
Set-Location ..
```

Run the full backend suite:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q
Set-Location ..
```

Commit only the test changes unless a separate, verified bug fix was genuinely required:

```powershell
git diff --check
git diff -- backend-poc-technical/test_answer_validation.py backend-poc-technical/agents/answer_validation.py
git add backend-poc-technical/test_answer_validation.py
# Add the implementation file only if you made and verified a real fix:
# git add backend-poc-technical/agents/answer_validation.py
git diff --cached --check
git commit -m "test: Urdu and Roman Urdu answer validation cases"
git push -u origin test/h3-answer-validation-urdu
```

Keep unexpected behavior as an honest `xfail` with a reason. Do not change expected values just to make a test pass.

## 6. H-4: Local Store Ownership Tests

Start the task branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c test/h4-local-store-ownership
```

Read the Local Store and create the ownership test:

```powershell
code backend-poc-technical/data_sources/local_store.py
code backend-poc-technical/test_local_store_ownership.py
```

Run the focused test and then the full backend suite:

```powershell
Set-Location "backend-poc-technical"
python -m pytest -q test_local_store_ownership.py
python -m pytest -q
Set-Location ..
```

Commit the test. Include `local_store.py` only if the test found and you fixed a real ownership bug:

```powershell
git diff --check
git diff -- backend-poc-technical/test_local_store_ownership.py backend-poc-technical/data_sources/local_store.py
git add backend-poc-technical/test_local_store_ownership.py
# Add the implementation file only if you made and verified a real fix:
# git add backend-poc-technical/data_sources/local_store.py
git diff --cached --check
git commit -m "test: Local Store cross-patient access"
git push -u origin test/h4-local-store-ownership
```

## 7. H-5: System-Test Results

Start the task branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c docs/h5-system-test-results
```

Open the results file and record only tests you really ran:

```powershell
code docs/SYSTEM_TEST_RESULTS_Hassaan.md
```

Check the documentation change:

```powershell
git diff --check
git diff -- docs/SYSTEM_TEST_RESULTS_Hassaan.md
```

Commit and push:

```powershell
git add docs/SYSTEM_TEST_RESULTS_Hassaan.md
git diff --cached --check
git commit -m "docs: record real system-test results"
git push -u origin docs/h5-system-test-results
```

Use `NOT DONE` where you have no evidence. Do not mark tests as passed because another person ran them.

## 8. H-6: Accessibility Results

Start the task branch:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c test/h6-accessibility-remaining
```

Open the checklist and record real observations from the live site:

```powershell
code docs/ACCESSIBILITY_CHECK.md
```

After testing keyboard navigation, 200 percent zoom, and 320 pixel width, review and commit:

```powershell
git diff --check
git diff -- docs/ACCESSIBILITY_CHECK.md
git add docs/ACCESSIBILITY_CHECK.md
git diff --cached --check
git commit -m "docs: accessibility results for chat, result and provider screens"
git push -u origin test/h6-accessibility-remaining
```

Leave untested cells as `NOT DONE`. Do not claim that a screenshot exists unless you actually captured it.

## 9. AI Usage Log

Use a separate documentation branch only when you have real new entries:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c docs/hassaan-ai-usage
code docs/ai-usage/hassaan.md
```

Review, validate, commit, and push:

```powershell
git diff --check
git diff -- docs/ai-usage/hassaan.md
git add docs/ai-usage/hassaan.md
git diff --cached --check
git commit -m "docs: Hassaan AI usage log"
git push -u origin docs/hassaan-ai-usage
```

Delete rows that did not happen. Add only tasks, prompts, checks, and files that are true.

## 10. Pull Request Checklist

After pushing a task branch, print the branch and latest commit:

```powershell
git branch --show-current
git log -1 --oneline
git status --short --branch
```

Open the repository in your browser:

```powershell
Start-Process "https://github.com/UsmanBari/chroniccare-ai"
```

Create a pull request into `dev`. Include:

```text
Summary:
- What I added or documented.
- Which command I ran.
- The exact result I observed.
- What I reviewed or changed after the AI draft.

Tests:
- <exact command>
- <pass, fail, or expected xfail result>

Files:
- <actual files changed>
```

Do not say that a pull request is merged until GitHub shows it as merged.

## 11. Final Verification

Run this before reporting your work:

```powershell
git status --short --branch
git log --author="Hassaan" --oneline -20
git diff origin/$(git branch --show-current)..HEAD --stat
```

If the branch has no uncommitted changes and the push succeeded, the local branch is clean. The commit count is not a substitute for real work or test evidence.
