"""
Evaluation script for Stage-1 Red Flag Patterns Round 4.
Computes confusion matrix on:
1. Canonical test set (N=300: 150 positives, 150 negatives)
2. Independent held-out test set (N=40: 20 positives, 20 negatives)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend-poc-technical"))

import agents.red_flag_patterns as rfp
from test_red_flag_patterns import ALL_POSITIVES, ALL_NEGATIVES
from test_red_flags_round4 import UNSEEN_20_POSITIVES, UNSEEN_20_NEGATIVES

cats = ['chest_pain', 'breathing', 'confusion_and_stroke', 'loss_of_consciousness', 'dka_vomiting_high_glucose']
matrix = {c: {'TP': 0, 'FN': 0, 'TN': 0, 'FP': 0} for c in cats}

for expected_cat, lang, text in ALL_POSITIVES:
    hit, detected = rfp.match(text)
    if hit and detected == expected_cat:
        matrix[expected_cat]['TP'] += 1
    else:
        matrix[expected_cat]['FN'] += 1

for neg_cat, lang, text in ALL_NEGATIVES:
    hit, detected = rfp.match(text)
    if not hit:
        matrix[neg_cat]['TN'] += 1
    else:
        matrix[neg_cat]['FP'] += 1

print("=" * 80)
print("TABLE 1: CANONICAL HELD-IN TEST SET (N=300)")
print("=" * 80)
print(f"{'Category':27} | {'TP':4} | {'FN':4} | {'TN':4} | {'FP':4} | {'Sensitivity':11} | {'Specificity':11}")
print("-" * 80)
total_tp, total_fn, total_tn, total_fp = 0, 0, 0, 0
for c in cats:
    m = matrix[c]
    sens = m['TP'] / (m['TP'] + m['FN']) * 100 if (m['TP'] + m['FN']) > 0 else 0
    spec = m['TN'] / (m['TN'] + m['FP']) * 100 if (m['TN'] + m['FP']) > 0 else 0
    print(f"{c:27} | {m['TP']:4} | {m['FN']:4} | {m['TN']:4} | {m['FP']:4} | {sens:10.1f}% | {spec:10.1f}%")
    total_tp += m['TP']
    total_fn += m['FN']
    total_tn += m['TN']
    total_fp += m['FP']
print("-" * 80)
tot_sens = total_tp / (total_tp + total_fn) * 100
tot_spec = total_tn / (total_tn + total_fp) * 100
print(f"{'TOTAL':27} | {total_tp:4} | {total_fn:4} | {total_tn:4} | {total_fp:4} | {tot_sens:10.1f}% | {tot_spec:10.1f}%")

u_tp, u_fn, u_tn, u_fp = 0, 0, 0, 0
for text, cat in UNSEEN_20_POSITIVES:
    hit, detected = rfp.match(text)
    if hit and detected == cat:
        u_tp += 1
    else:
        u_fn += 1

for text in UNSEEN_20_NEGATIVES:
    hit, detected = rfp.match(text)
    if not hit:
        u_tn += 1
    else:
        u_fp += 1

print("\n" + "=" * 80)
print("TABLE 2: INDEPENDENT HELD-OUT TEST SET (N=40, Written After Code, Never Tuned)")
print("=" * 80)
print(f"{'Metric':25} | {'Count':5} | {'Percentage':10}")
print("-" * 45)
print(f"{'True Positives (TP)':25} | {u_tp:5} | {u_tp/len(UNSEEN_20_POSITIVES)*100:9.1f}%")
print(f"{'False Negatives (FN)':25} | {u_fn:5} | {u_fn/len(UNSEEN_20_POSITIVES)*100:9.1f}%")
print(f"{'True Negatives (TN)':25} | {u_tn:5} | {u_tn/len(UNSEEN_20_NEGATIVES)*100:9.1f}%")
print(f"{'False Positives (FP)':25} | {u_fp:5} | {u_fp/len(UNSEEN_20_NEGATIVES)*100:9.1f}%")
print("-" * 45)
print(f"{'Overall Sensitivity':25} | {u_tp:5}/20 | {u_tp/(u_tp+u_fn)*100:9.1f}%")
print(f"{'Overall Specificity':25} | {u_tn:5}/20 | {u_tn/(u_tn+u_fp)*100:9.1f}%")
print("=" * 80)
