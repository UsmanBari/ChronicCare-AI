# Clinical Guideline Corpus Manifest

> **Location Notice:** Guideline PDFs, raw extracted text, and chunks live exclusively outside Git under `$CHRONICCARE_DATA_DIR/guidelines` and `$CHRONICCARE_DATA_DIR/rag`.
> **Licence Status Notice:** The American Diabetes Association (ADA) and American Heart Association / American College of Cardiology (AHA/ACC) guidelines carry text/data mining prohibitions or copyright restrictions. Permission was formally submitted on 27 Oct 2026 and is awaiting written clearance. Ingest skips all blocked sources until a `.granted` token is placed in `$CHRONICCARE_DATA_DIR/guidelines/permissions/<source_id>.granted`.

## Corpus Inventory & Licence Status

| Source ID | Title | Ed. | Priority | Pages | Allowed for RAG? | Status / Reason | Download Date | SHA-256 (first 12) | Terms of Use |
|---|---|---|---|---|---|---|---|---|---|
| `ada_2026_sec02` | ADA Standards of Care in Diabetes 2026 - Section 2: Diagnosis and Classification of Diabetes | 2026 | 2 | 23 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `b393a4c91ac1` | TO FILL BY USMAN |
| `ada_2026_sec05` | ADA Standards of Care in Diabetes 2026 - Section 5: Facilitating Positive Health Behaviors and Well-being to Improve Health Outcomes | 2026 | 2 | 43 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `e537eaf1a8a8` | TO FILL BY USMAN |
| `ada_2026_sec06` | ADA Standards of Care in Diabetes 2026 - Section 6: Glycemic Goals, Hypoglycemia, and Hyperglycemic Crises | 2026 | 2 | 18 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `ff05e98837e7` | TO FILL BY USMAN |
| `ada_2026_sec10` | ADA Standards of Care in Diabetes 2026 - Section 10: Cardiovascular Disease and Risk Management | 2026 | 2 | 30 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `4bf96af77261` | TO FILL BY USMAN |
| `ada_2026_sec11` | ADA Standards of Care in Diabetes 2026 - Section 11: Chronic Kidney Disease and Risk Management | 2026 | 2 | 15 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `a07be43925bb` | TO FILL BY USMAN |
| `ada_2026_sec13` | ADA Standards of Care in Diabetes 2026 - Section 13: Older Adults | 2026 | 2 | 20 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `49a36603341a` | TO FILL BY USMAN |
| `aha_acc_2025` | 2025 AHA/ACC Clinical Practice Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults | 2025 | 2 | 105 | **FALSE** | BLOCKED: licence (ADA/AHA permission pending since 27 Oct 2026) | 2026-10-27 | `68a80057e6ba` | TO FILL BY USMAN |
| `who_2021_htn` | Guideline for the Pharmacological Treatment of Hypertension in Adults | 2021 | 3 | 61 | **TRUE** | ALLOWED (CHECK: no TDM prohibition on pages 1-2) | 2026-10-27 | `57f6376d5c9b` | TO FILL BY USMAN |
| `ish_2020_htn` | 2020 International Society of Hypertension Global Hypertension Practice Guidelines | 2020 | 3 | 24 | **TRUE** | ALLOWED (CHECK: no TDM prohibition on pages 1-2) | 2026-10-27 | `ef877c7b8a2b` | TO FILL BY USMAN |
| `idf_dar_2021` | IDF-DAR Diabetes and Ramadan: Practical Guidelines 2021 | 2021 | 4 | 333 | **TRUE** | ALLOWED (CHECK: no TDM prohibition on pages 1-2) | 2026-10-27 | `615246041d28` | TO FILL BY USMAN |
| `pk_htn_women_2023` | Management of Hypertension in Women: Pakistan Hypertension Clinical Practice Guidelines | 2023 | 4 | 22 | **TRUE** | ALLOWED (CHECK: no TDM prohibition on pages 1-2) | 2026-10-27 | `57111036bb42` | TO FILL BY USMAN |
| `aku_diabetes_pk_2023` | Adolopment of Adult Diabetes Mellitus Management Guidelines for a Pakistani Context: Methodology and Challenges | 2023 | 4 | 12 | **TRUE** | ALLOWED (Creative Commons / Open Access) | 2026-10-27 | `b69d36aeb094` | TO FILL BY USMAN |

## Detailed Licence Snippets (First 2 Pages)

### `ada_2026_sec02` — ada2026_sec02_diagnosis.pdf
- **Publisher:** American Diabetes Association
- **URL / DOI:** https://doi.org/10.2337/dc26-S002
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"This publication and its contents may not be reproduced, distributed, or used for text or data mining, machine learning, or similar technologies without prior written permission."*
- **Full SHA-256:** `b393a4c91ac1b9af696268b3bcd161862ada66b5312e46e0f21b5949a9798f05`

### `ada_2026_sec05` — ada2026_sec05_lifestyle.pdf
- **Publisher:** American Diabetes Association
- **URL / DOI:** https://doi.org/10.2337/dc26-S005
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"This publication and its contents may not be reproduced, distributed, or used for text or data mining, machine learning, or similar technologies without prior written permission."*
- **Full SHA-256:** `e537eaf1a8a8a0e5f3f75678f646cb39ac379a6ed46caaa8481fa929aca63361`

### `ada_2026_sec06` — ada2026_sec06_glycemic_goals_hypoglycemia.pdf
- **Publisher:** American Diabetes Association
- **URL / DOI:** https://doi.org/10.2337/dc26-S006
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"This publication and its contents may not be reproduced, distributed, or used for text or data mining, machine learning, or similar technologies without prior written permission."*
- **Full SHA-256:** `ff05e98837e70b0fea8b78434e6a6202a23e5dd7ba445e3fac11657e0b6f6e76`

### `ada_2026_sec10` — ada2026_sec10_cvd_risk.pdf
- **Publisher:** American Diabetes Association
- **URL / DOI:** https://doi.org/10.2337/dc26-S010
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"This publication and its contents may not be reproduced, distributed, or used for text or data mining, machine learning, or similar technologies without prior written permission."*
- **Full SHA-256:** `4bf96af77261d4d8b75c2be9c7f3040061e2f00dbf246bf9f3b16c982cdad040`

### `ada_2026_sec11` — ada2026_sec11_ckd.pdf
- **Publisher:** American Diabetes Association
- **URL / DOI:** https://doi.org/10.2337/dc26-S011
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"This publication and its contents may not be reproduced, distributed, or used for text or data mining, machine learning, or similar technologies without prior written permission."*
- **Full SHA-256:** `a07be43925bb7e0f1c3e4cfbeafc6be0e607b0b909eed451ff2e8810f0433157`

### `ada_2026_sec13` — ada2026_sec13_older_adults.pdf
- **Publisher:** American Diabetes Association
- **URL / DOI:** https://doi.org/10.2337/dc26-S013
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"This publication and its contents may not be reproduced, distributed, or used for text or data mining, machine learning, or similar technologies without prior written permission."*
- **Full SHA-256:** `49a36603341af5eee7c182a959771cccfbf94e25755d99f1b8b37d495ab915de`

### `aha_acc_2025` — aha_acc_2025_hbp_guideline.pdf
- **Publisher:** American Heart Association / American College of Cardiology
- **URL / DOI:** https://doi.org/10.1161/HYP.0000000000000249
- **Allowed for RAG:** No (BLOCKED)
- **Licence Notice:** *"doi: 10.1161/HYP.0000000000000249 © 2025 by the American Heart Association, Inc."*
- **Full SHA-256:** `68a80057e6ba83d2e261e92cce4c20b5b13e47aff747226bb7832cf7f4557380`

### `who_2021_htn` — who_2021_htn_pharmacological.pdf
- **Publisher:** World Health Organization
- **URL / DOI:** https://www.who.int/publications/i/item/9789240033986
- **Allowed for RAG:** Yes
- **Licence Notice:** *"No explicit copyright notice found on pages 1-2."*
- **Full SHA-256:** `57f6376d5c9bc4ea6c44873625547c8a5443d5a6ad8c8c422733681563db05fb`

### `ish_2020_htn` — ish_2020_global_htn.pdf
- **Publisher:** International Society of Hypertension
- **URL / DOI:** https://doi.org/10.1161/HYPERTENSIONAHA.120.15026
- **Allowed for RAG:** Yes
- **Licence Notice:** *"Schutte © 2020 American Heart Association, Inc."*
- **Full SHA-256:** `ef877c7b8a2b21fa3497ce59e5d65d1722b7e5a231fb1d8fb28e621612796ce2`

### `idf_dar_2021` — idf_dar_ramadan_2021.pdf
- **Publisher:** International Diabetes Federation & DAR International Alliance
- **URL / DOI:** https://www.idf.org/our-activities/education/diabetes-and-ramadan.html
- **Allowed for RAG:** Yes
- **Licence Notice:** *"PUBLISHER: International Diabetes Federation and DAR International Alliance SUPPORT: The preparation of this document was made possible through an educational grant from © International Diabetes Federation and DAR International Alliance All rights reserved."*
- **Full SHA-256:** `615246041d280f5c90c42468a2a0f153e68b0d09dfab1e97c6eed2693f8dc279`

### `pk_htn_women_2023` — pk_htn_women_2023.pdf
- **Publisher:** Pakistan Cardiac Society / Task Force Go Red for Women-Pakistan
- **URL / DOI:** http://www.pakheartjournal.com
- **Allowed for RAG:** Yes
- **Licence Notice:** *"No explicit copyright notice found on pages 1-2."*
- **Full SHA-256:** `57111036bb425d6ff77643f101fe341dfbfef278938cfa480b9b9ef0954eab2f`

### `aku_diabetes_pk_2023` — aku_diabetes_pakistan_2023.pdf
- **Publisher:** Aga Khan University / Frontiers in Endocrinology
- **URL / DOI:** https://doi.org/10.3389/fendo.2022.1081361
- **Allowed for RAG:** Yes
- **Licence Notice:** *"This is an open- access article distributed under the terms of the Creative Commons Attribution License (CC BY).The use, distribution or reproduction in other forums is permitted, provided the original author(s) and the copyright owner(s) are credited and that the"*
- **Full SHA-256:** `b69d36aeb094099211fa1db8b305dd0f039a6706f85313cfc54409a740eb40ea`
