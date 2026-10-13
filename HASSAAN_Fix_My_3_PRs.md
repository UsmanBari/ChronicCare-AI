# Hassaan: fix your 3 PRs (about 20 minutes)

Do these in PowerShell, from your repo folder. Each fix goes on the SAME branch, so the PR updates by itself. No new PR.

I already ran both fixed test files here: **16 passed, 2 xfailed**, nothing failing.

---
## Fix 1: PR #51 (Urdu answer validation)
Problem: `test_glucose_do_sau_with_unit` fails because "do sau mg/dl" is not parsed yet. That is a real known gap, so we mark it `xfail` (expected to fail), not delete it.

```powershell
git checkout test/h3-answer-validation-urdu
git pull
```
Open `backend-poc-technical/agents/test_answer_validation.py`. Find:
```python
def test_glucose_do_sau_with_unit():
```
Put this directly ABOVE it:
```python
@pytest.mark.xfail(
    reason="Known gap: a spoken number word followed by a unit ('do sau mg/dl') is not parsed yet. Planned for Iteration 2.",
    strict=False,
)
```
(Or copy the whole fixed file `HASSAAN_fixed_test_answer_validation.py` over it.)
```powershell
cd backend-poc-technical
python -m pytest agents/test_answer_validation.py -q
cd ..
git add backend-poc-technical/agents/test_answer_validation.py
git commit -m "test: mark 'do sau mg/dl' as a known gap (xfail)"
git push
```
Expected output: `... passed, 2 xfailed`.

---
## Fix 2: PR #53 (Local Store cross-patient access)
Problem: your test asks for `temp_db`, but that fixture does not exist.

```powershell
git checkout test/h4-local-store-ownership
git pull
```
Copy the whole fixed file `HASSAAN_fixed_test_local_store_ownership.py` over
`backend-poc-technical/agents/test_local_store_ownership.py`.
The only change: it adds this at the top, before your test:
```python
@pytest.fixture
def temp_db(tmp_path):
    """A fresh, empty SQLite store for each test."""
    path = str(tmp_path / "local_store_test.db")
    init_db(db_path=path, backend="sqlite")
    return path
```
```powershell
cd backend-poc-technical
python -m pytest agents/test_local_store_ownership.py -q
cd ..
git add backend-poc-technical/agents/test_local_store_ownership.py
git commit -m "test: add temp_db fixture for Local Store ownership test"
git push
```
Expected output: `1 passed`.

---
## Fix 3: PR #50 (independent Urdu phrases): files are empty
Problem: all 3 files are 0 bytes. Also Saad already added `scripts/eval_phrase_set.py` on dev, so do NOT add your own copy (it conflicts). Use his.

```powershell
git checkout test/h1-independent-urdu-phrases   # use the exact branch name of PR #50
git pull
git rm scripts/eval_phrase_set.py
git fetch origin
git merge origin/dev
```

**Step A: write your phrases (yourself, you are the native speaker).**
File: `tests/sim/danger_phrases_independent_hassaan.json`. About 30 items: roughly half dangerous, half safe. Mix Urdu script and Roman Urdu. Include some tricky safe ones (past events, "my father had chest pain last year"). Do not look at the rules file while writing them. Format:
```json
[
  {"text": "<your phrase>", "expected_danger": true,  "language": "roman_urdu"},
  {"text": "<your phrase>", "expected_danger": false, "language": "urdu"}
]
```
`language` is `english`, `roman_urdu` or `urdu`. Write them yourself. Do not ask an AI for the phrases, or the test is not independent.

**Step B: run it.**
```powershell
python scripts/eval_phrase_set.py tests/sim/danger_phrases_independent_hassaan.json
```
It prints TP, FN, FP, TN, sensitivity, specificity and the failing phrases.

**Step C: record the real result.**
File: `docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md`:
```
# Independent phrase set (Hassaan)
Author: Hassaan Mudassar. Written by me, without looking at the rules.
Date: 2026-10-13
Command: python scripts/eval_phrase_set.py tests/sim/danger_phrases_independent_hassaan.json

| TP | FN | FP | TN | Sensitivity | Specificity |
|----|----|----|----|-------------|-------------|
| ?  | ?  | ?  | ?  | ?%          | ?%          |

Failing phrases (paste the list the script printed):
- ...

What I learned: (2 lines, in your own words)
```
Fill in the real numbers. A low number is fine and honest. Do not change phrases to make it look better.

```powershell
git add tests/sim/danger_phrases_independent_hassaan.json docs/INDEPENDENT_PHRASE_RESULTS_hassaan.md
git commit -m "test: independent Urdu and Roman Urdu danger phrases with results"
git push
```
Then tell Usman the 3 PRs are updated.

---
## After that: H-6 (accessibility)
Open the chat, result and provider screens and check keyboard-only use, labels, contrast and zoom. Put the findings in `docs/ACCESSIBILITY_CHECK_hassaan.md` with a table of screen / check / pass or fail / note. Commit and open a PR to `dev`.

## Add to your AI log
One row per PR where you used AI. Say what you asked, what it gave, and what you checked or changed. Be honest.
