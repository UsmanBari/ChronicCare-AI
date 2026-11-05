# American Diabetes Association (ADA) 2026 Guideline Permission Record

> **Notice:** The original written correspondence is confidential and kept privately by Usman Bari. It is never committed to Git. This document records the operational conditions, scope, and engineering enforcement rules.

---

## 1. Permission Summary

- **Grantor:** American Diabetes Association (ADA)
- **Grant Date:** 5 November 2026
- **Authorized Material:** *Standards of Care in Diabetes—2026*, specifically and exclusively the following six sections:
  1. **Section 2:** *Diagnosis and Classification of Diabetes* (`ada_2026_sec02`)
  2. **Section 5:** *Facilitating Positive Health Behaviors and Well-being to Improve Health Outcomes* (`ada_2026_sec05`)
  3. **Section 6:** *Glycemic Goals, Hypoglycemia, and Hyperglycemic Crises* (`ada_2026_sec06`)
  4. **Section 10:** *Cardiovascular Disease and Risk Management* (`ada_2026_sec10`)
  5. **Section 11:** *Chronic Kidney Disease and Risk Management* (`ada_2026_sec11`)
  6. **Section 13:** *Older Adults* (`ada_2026_sec13`)
- **Institution & Project:** ChronicCare AI at FAST-NUCES Islamabad, Pakistan.
- **Approved Scope:** Academic evaluation only.
- **Approved Period:** 1 November 2026 through 30 June 2027.
- **Scheduled Deletion Date:** 30 June 2027.
- **Excluded Guidelines:** American Heart Association / American College of Cardiology (*AHA/ACC 2025*, `aha_acc_2025`) is **not** covered and remains completely blocked.

---

## 2. Terms and Conditions (Paraphrased)

1. **Storage and Indexing:** The approved ADA material may be privately stored and indexed in the project database to retrieve relevant educational guidance for diabetes management.
2. **Patient Excerpts:** The prototype may display up to three (3) brief, unmodified excerpts per patient check-in. Every displayed excerpt must carry proper attribution: the full academic citation and the persistent DOI link.
3. **No Commercial Use or Redistribution:** No modification, redistribution, publication, commercial deployment, or public access is permitted without further written authorization.
4. **No Endorsement or Validation:** This permission is strictly an academic licence. **This permission is not an ADA endorsement, sponsorship or clinical validation.**
5. **No Promotional Use:** The American Diabetes Association name and logo must not be used for promotional purposes, marketing, or branding anywhere in the application or documentation.
6. **Data Deletion:** Stored ADA material must be kept secure and permanently deleted upon conclusion of the approved evaluation period on **30 June 2027**.

---

## 3. Explainer & LLM Clarification (5 Nov 2026)

In response to Usman's written clarification request regarding retrieval-augmented generation:
- **Plain-language Explanations:** The six approved sections may be processed by the clinical explainer to generate patient-facing plain-language explanations.
- **Urdu & Roman Urdu Translations:** Plain-language translations of guideline reasoning into Urdu and Roman Urdu are permitted.
- **Approved LLM Provider:** Processing is authorized exclusively through the **Groq API** (`allowed_llm_providers = ["groq"]`).
- **Prohibition on Gemini:** Chunks and excerpts from ADA guidelines must **never** be sent to Google Gemini under any circumstances (Rule G3), as third-party model ingestion without enterprise confidentiality guarantees constitutes redistribution under the licence agreement.

---

## 4. Deletion Procedure (Scheduled: 30 June 2027)

On or before 30 June 2027, all stored ADA guideline chunks must be permanently purged from the production and development databases:

```bash
# Verify chunks to be deleted (dry run)
python scripts/rag/delete_source.py --licence ada_2026

# Execute permanent deletion
python scripts/rag/delete_source.py --licence ada_2026 --yes
```

