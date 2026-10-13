# Independent Danger-Phrase Evaluation

Date: 2026-10-13

This report records the result produced by `scripts/eval_phrase_set.py` for `tests/sim/danger_phrases_independent_hassaan.json`.

The phrase file is currently a draft and uses `author: "draft"`. Review and replace the phrases with wording independently authored by Hassaan before presenting this as the final independent set.

## Command

```powershell
Set-Location "backend-poc-technical"
python ..\scripts\eval_phrase_set.py ..\tests\sim\danger_phrases_independent_hassaan.json
```

## Result

| Metric | Count |
|---|---:|
| Total | 30 |
| True positive (TP) | 7 |
| False negative (FN) | 8 |
| False positive (FP) | 0 |
| True negative (TN) | 15 |
| Sensitivity | 46.67% |
| Specificity | 100.00% |

The counts add up to 30: 7 + 8 + 0 + 15 = 30.

## Missed Danger Phrases

These expected-danger items were not detected by the current screen:

| Item | Category | Text |
|---:|---|---|
| 1 | chest_pain | My chest is crushing and very painful |
| 2 | breathing | Saans bilkul nahi aa rahi |
| 5 | loss_of_consciousness | Main behosh ho kar gir gaya |
| 6 | vision_loss | اچانک میری بینائی چلی گئی |
| 9 | chest_pain | My chest has severe pressure |
| 12 | loss_of_consciousness | Ghashi pari aur hosh nahi raha |
| 13 | severe_headache_thunderclap | اچانک بہت شدید سر درد شروع ہوا |
| 15 | vision_loss | Aankhon ke aage achanak andhera hai |

## Interpretation

The current draft set shows no false positives, but it misses 8 of 15 expected danger phrases. These misses should be reported as findings. The detector was not changed as part of this evaluation.
