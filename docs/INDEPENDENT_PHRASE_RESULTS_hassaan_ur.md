# Independent Urdu-Script Danger-Phrase Evaluation (Hassaan)

**Status:** NOT DONE  
**Reason:** The independent phrase test set `tests/sim/danger_phrases_independent_hassaan_ur.json` was not found on the branch or repository.

## Operational Protocol Adherence

Per Day 4 instructions:
> *"Hassaan wrote tests/sim/danger_phrases_independent_hassaan_ur.json by hand. Do NOT edit it. If it's missing, STOP Part C and write NOT DONE."*

As specified in the strict pre-flight rules, the model must not fabricate or hand-generate independent clinical test phrases. Because the independent dataset file was not present, Part C was safely stopped.

When Hassaan commits `tests/sim/danger_phrases_independent_hassaan_ur.json`, the evaluation can be executed using:
```powershell
python scripts/eval_phrase_set.py tests/sim/danger_phrases_independent_hassaan_ur.json
```
and the resulting TP/FN/FP/TN metrics and proposed review table will be populated here.

