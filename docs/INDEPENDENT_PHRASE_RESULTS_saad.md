# Independent Danger-Phrase Evaluation — Saad

## Purpose

This evaluation tests the existing multilingual danger-phrase detector using an independent set of 30 phrases authored by Saad. The detector was not modified based on this phrase set.

The set contains:
- 15 danger/emergency phrases
- 15 non-danger or negated phrases
- English and Roman Urdu examples

The phrases cover chest pain, breathing difficulty, confusion/stroke symptoms, fainting, vision loss, vomiting with high glucose, and severe headache.

## Results

| Metric | Result |
|---|---:|
| Total phrases | 30 |
| True Positives (TP) | 7 |
| False Negatives (FN) | 8 |
| False Positives (FP) | 2 |
| True Negatives (TN) | 13 |
| Sensitivity | 46.67% |
| Specificity | 86.67% |

## Interpretation

A true positive is a danger phrase that the detector correctly identified as dangerous.

A false negative is a danger phrase that the detector failed to identify.

A false positive is a non-danger or negated phrase that the detector incorrectly identified as dangerous.

A true negative is a non-danger or negated phrase that the detector correctly did not flag.

The independent set produced 7 true positives and 8 false negatives out of 15 expected danger phrases, giving a sensitivity of 46.67%.

For the 15 expected non-danger phrases, 13 were correctly rejected and 2 were incorrectly flagged, giving a specificity of 86.67%.

## Failing Items

### False Negatives

1. "My chest feels very tight and painful"
   - Category: chest_pain

2. "Mere se saans nahi li ja rahi"
   - Category: breathing

3. "I am not breathing properly"
   - Category: breathing

4. "Mujhe saans lene mein bohat mushkil ho rahi hai"
   - Category: breathing

5. "Mera aik bazu achanak sunn ho gaya hai aur bolne mein mushkil hai"
   - Category: confusion_and_stroke

6. "One side of my face suddenly feels weak"
   - Category: confusion_and_stroke

7. "My sugar is extremely high and I keep vomiting"
   - Category: dka_vomiting_high_glucose

8. "Sugar bohat high hai aur mujhe bar bar ulti ho rahi hai"
   - Category: dka_vomiting_high_glucose

### False Positives

1. "I had chest pain last year but I am fine now"
   - Category: chest_pain
   - Detector category: chest_pain

2. "I had a severe headache yesterday but it is completely gone now"
   - Category: severe_headache
   - Detector category: severe_headache

## Finding

The independent evaluation found both missed danger expressions and incorrect flags of historical/resolved symptoms. No detector changes were made as part of this task. These results document the current detector behaviour on the independent phrase set.