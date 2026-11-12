# Clinician response record: Dr. Shaiza Jabbar

**Received:** 13 October 2026, WhatsApp voice note (about 51 seconds), transcribed by Usman.
**Form of evidence:** verbal reply by voice note. Not signed. Ask for a written confirmation to attach in Appendix F.
**Status:** the transcript ends in the middle of a sentence (Decision 5). Her full answer is not yet recorded.

## Her answers, as given

| # | Decision in the pack | What she said | How we record it |
|---|---|---|---|
| 3 | Red-flag symptoms | Chest pain: also treat **chest pain radiating to the left arm or the left jaw** as a red flag, because it is the most common heart-attack presentation. Also add **crushing-type chest pain**, which needs urgent review. | **Change.** Add "chest pain radiating to left arm / left jaw" and "crushing chest pain" to the chest-pain red flags. The level for crushing pain (urgent or emergency) is to be confirmed with her. |
| 3 | Red-flag symptoms (stroke) | Stroke: with **one-sided weakness and facial droop**, also include **dizziness, blurred vision and headache**. | **Change.** Add dizziness, blurred vision and headache to the stroke pattern. |
| 5 | "Confused" pattern | She did not understand why "confused by my morning pills" should be escalated to urgent. (Transcript cut off.) | **Pending.** Likely supports not escalating medicine-confusion. Do not write which of the three options she chose until the rest is available. |
| 1, 2, 4, 6, 7 | Other decisions | Not covered in the text received. | **Unresolved.** Do not mark approved. |

## What she needs to confirm (one short message)

1. The rest of her answer on "confused by my morning pills" (which option: keep, first-person plus a second symptom, or ask one clarifying question).
2. Crushing chest pain: **urgent** or **emergency**?
3. Chest pain to left arm or jaw: **emergency**?
4. Stroke symptoms: is one-sided weakness or facial droop **alone** an emergency, and do dizziness, blurred vision or headache **alone** raise a level?
5. Decisions 1, 2, 4, 6, 7: approve, change or not sure.
6. Her title and hospital for the report; permission to name her; a written confirmation.

## Code and test changes implied (do after she confirms)

- `agents/adaptive_interview_agent.py` (danger phrases): add chest pain with left arm, left jaw, jaw and "crushing" wording in English, Urdu and Roman Urdu.
- Stroke pattern: add dizziness, blurred vision and headache combined with one-sided weakness or facial droop.
- `docs/CLINICAL_RULES.md` and the review pack: update the register.
- Tests: add each new phrase to a test, plus a fresh independent set (do not re-use Saad's set to claim an improvement).
- Re-run the full suite and update the report numbers.


---
# Update 13 Oct 2026, 21:14 PKT: full replies from two clinicians

## Reviewer 1: Dr Shaiza Jabbar, Medical Officer, Hearts International Hospital
Source: replies relayed by Usman (verbal/WhatsApp). Not signed. Confirm permission to be named.

| # | Item | Her reply |
|---|------|-----------|
| 1 | Glucose thresholds, 18.0 factor | Approved |
| 2 | Blood pressure | Approved |
| 3 | Red flags | CHANGES (below) |
| 4 | Vomiting: emergency or urgent | "Rest approved" (unclear: keep emergency?) |
| 5 | "confused" | "Rest approved" (unclear; earlier she did not understand why it should escalate) |
| 6 | Four narrative-yes questions | Approved |
| 7 | Input handling | Approved |

Item 3 changes:
- Crushing chest pain: **emergency**.
- Chest pain radiating to the left arm, especially the left jaw: **emergency**.
- Stroke extras (dizziness, blurred vision, headache): raise the concern level when combined with weakness or facial droop.
- Stroke extras alone in a very old patient with several conditions (ischaemic heart disease, hypertension, diabetes) or any earlier heart or brain event: concerning on their own, go for an **urgent CT scan**.

## Reviewer 2: Captain Dr Talha Yasin, Army doctor
Source: replies relayed by Usman. Title, hospital and permission to be named: not yet confirmed.

| # | Item | His reply |
|---|------|-----------|
| 1 | Glucose | Approved |
| 2 | Blood pressure | Approved |
| 3 | Red flags | Approved |
| 4 | Vomiting | **Change**: nonstop vomiting is NOT emergency, it is an urgent review. No need to label it emergency. |
| 5 | "confused" | **Change**: do not trigger on the word. Ask "Is the patient oriented in time, place and person?" If not oriented: emergency. Otherwise: review. |
| 6 | Narrative-yes questions | New symptoms, and low sugar last week: go to **review** |
| 7 | Input handling | Approved |

## Conflicts and gaps (to settle before the final report)
1. **Item 4:** Talha says urgent. Shaiza's reply is unclear. Ask her one question (below).
2. **Item 5:** Talha's orientation rule is clear. Shaiza's reply is unclear but fits it (she did not want the word to escalate).
3. **Item 6:** Talha names two of the four (new symptoms, low sugar). Not stated: sick-day and foot problem. Shaiza approved "should any go to review".
4. **Stroke extras for the very old / comorbid patient:** needs a clear rule (age cut-off, which conditions) before coding. Ask Shaiza.

## Message to send Shaiza
"Thank you doctor. One last check: Dr Talha Yasin says nonstop vomiting should be an urgent review, not emergency, and the word 'confused' should only mean emergency if the patient is not oriented in time, place and person (otherwise review). Are you happy with that? And for the very old patient, what age should we treat as 'very old' (for example 75 or above)? May we write your name and 'Medical Officer, Hearts International Hospital' in our report?"

## Code that follows from this (not changed yet)
- Chest pain already gives emergency for any chest-pain phrase, so crushing and left-arm/jaw are covered when "chest pain" is said. Add phrases without those words (pain going down my left arm, jaw pain).
- Replace the "confused" trigger with an orientation question (emergency if not oriented, else review).
- Vomiting: move to urgent once settled (conflict 1).
- Stroke extras: raise a level when combined with weakness or droop; urgent-CT rule for the old and comorbid patient.
- Item 6: new symptoms and low sugar last week go to review.
- Then update CLINICAL_RULES.md, add tests, re-test on a fresh phrase set.


---
# Update 13 Oct 2026, 22:13 PKT
- Dr Shaiza Jabbar agreed to Dr Talha's two changes (vomiting = urgent review; "confused" = ask orientation) [relayed by Usman, "haan haan"]. Confirm in writing if possible.
- "Very old" patient = **65 years or above**.
- Both clinicians may be named in the report:
  - Dr Shaiza Jabbar, Medical Officer, Hearts International Hospital
  - Captain Dr Talha Yasin, Army doctor, CMH Rawalpindi (confirm exact title)
- Still open: item 6 for sick-day and foot problem (Talha named only new symptoms and low sugar last week).

## Final rule set to implement
1. Crushing chest pain: emergency. Chest pain to left arm or left jaw: emergency.
2. Vomiting nonstop / cannot keep fluids down: urgent (not emergency).
3. "confused": ask "Is the patient oriented in time, place and person?" Not oriented: emergency. Oriented: review.
4. Stroke extras (dizziness, blurred vision, headache) with weakness or droop: raise the level. Alone in a patient aged 65+ with a heart/brain history or several of IHD, hypertension, diabetes: urgent CT scan advice (urgent).
5. New symptoms, low sugar last week: review.

---
# Update 14 Oct 2026: third clinician (scanned checklist)
- Reviewer: Dr Anam Zafar. Signed and dated 14/10/26. She agreed to be named.
- Item 3 (chest pain): lists pain radiating to the left arm or jaw (already implemented), difficulty in speaking (partly covered by the stroke phrases) and palpitations (not implemented; she gave no level).
- Item 4 (vomiting): she marked **emergency**. Dr Shaiza and Capt Dr Talha said **urgent** (implemented). Open split, 2 urgent versus 1 emergency. Code is not changed. Plan: one joint written decision in Iteration 2.
- Item 5 (confusion): ask one clarifying question first. This matches the implementation.
- Item 6 left blank. Item 7 marked yes.
- Items 1 and 2: confirmed from the paper sheet, no objection recorded.

---

## Update 2 Nov 2026: Week 2 doctor pack sent
- Sent docs/clinical/ChronicCare_Doctor_Review_Pack_2026-11-02.pdf by WhatsApp on 2 Nov 2026 to Dr Shaiza Jabbar, Capt Dr Talha Yasin and Dr Anam Zafar.
- 11 decisions: the 9 in DOCTOR_REVIEW_PACK_W2.md plus (10) v2 bare sugar number 2-40 with unclear unit and (11) a check-in with no readings.
- Replies: none yet.
---

## Update 3 Nov 2026: replies to the Week 2 doctor pack

Sources: Dr Shaiza Jabbar: voice note (relayed by Usman). Dr Anam Zafar: marked PDF pages 2-5 (items 3-11), signed "Dr. Anam", 3 Nov 2026, plus a voice note on item 5; page 1 (items 1-2) not received. Doctor C (asked not to be named): voice note. Doctor C's answers are used but he is not named anywhere.

### Dr Shaiza Jabbar
- Low / high sugar (item 2): low sugar is an emergency if it is below 40 and comes with the item-3 symptoms (shaky, drowsy, dizzy). High sugar around 250 or above 300 without symptoms: diabetics usually just need diet control advice and to re-chart for at least 5 days; if it stays high after 250, or with blurred vision, headache, drowsiness or a change in consciousness, it is an emergency.
- BP (item 4): these are the right thresholds; add symptoms to the message with 180/120 (blurred vision, headache, numbness of one arm or leg, or the arm and leg on one side), because people say their BP is always high.
- Vomiting (item 5): very old patients are an emergency (risk to the kidneys' blood supply); a young patient below 50 is an urgent review, not an emergency.
- HbA1c (item 6): HbA1c reflects about 3 months; ideally test every 3 months, at most 6-9 months if delayed, never a full year without it.
- Risk panel (item 7): good, because diabetes and hypertension now appear early, around 35-40.
- Items 8 and 9: fine as they are.
- Item 10: glucometers show mg/dL, not mmol/L; ask once just in case.
- Item 11: review only if a symptom is reported, otherwise routine.

### Dr Anam Zafar
- Item 3: option B.
- Item 4: tick next to the first option (cite the 2025 AHA/ACC guideline, thresholds unchanged).
- Item 5 (voice note): option C, emergency when the patient vomits so much they cannot keep fluids down (needs IV; risk of death from low volume).
- Item 6: tick next to 12 months; wording approved.
- Item 7: not marked.
- Item 8: top of the hip bone (current); range 40-200 cm OK.
- Item 9: approve 10 / 5 / 20 and 5 readings.
- Item 10: ask once more; if still unclear, send to Review without saving a number.
- Item 11: routine if there are no symptoms; review if any symptom is reported.
- Items 1 and 2: page not received.

### Doctor C (asked not to be named)
- Item 1: approve the word-group approach: raise to review and show the call 1122 line; whether it is an emergency is the patient's call.
- Item 2: LO should be an emergency (the patient can become confused or faint); HI should be an emergency (risk of DKA).
- Item 3: replace with option B.
- Item 4: use the 2025 AHA guideline; don't change the thresholds.
- Item 5: urgent, unless there are signs of severe dehydration (sunken eyes, dry tongue), blood in the vomit, a change of colour (green / bilious), a severe persistent headache, high-grade fever, confusion, vertigo or dizziness, or vomiting for 24 hours / the patient cannot keep medicines down: then emergency.
- Item 6: approved, but the doctor decides, not the machine; send for review; if symptoms appear (numbness of feet or hands, confusion, persistent headache, slow wound healing) it should be reviewed and an HbA1c done.
- Item 7: approve, doctors only, experimental, never changing a level.
- Item 8: for medical use, measure at the WHO midpoint (between the lowest rib and the top of the iliac bone, about 2 inches above the navel); the hip-bone landmark is for clothing.
- Item 9: approved, but use 10 mg/dL for sugar instead of 20.
- Item 10: keep it (safer to over-react); meters use mg/dL; a reading of 1-20 could be treated as mmol/L and above about 25-30 as mg/dL, but his decision is to keep the safer path.
- Item 11: routine if no symptoms; review if any symptom is reported (for example severe headache for days or in episodes, migraine episodes, numbness in both feet or both hands, slow wound healing).

### Not answered (not followed up)
- Item 1: Dr Shaiza (not mentioned), Dr Anam (page 1 not received).
- Item 2: Dr Anam (page 1 not received).
- Item 3: Dr Shaiza (not mentioned).
- Item 5: Dr Shaiza gave no exact age cut-off ("very old" vs "below 50").

---
## Update 8 Nov 2026: Clinician guidance

Source: Answers sent by one doctor in a written message to Usman on 8 Nov 2026; doctor's name: PENDING (Usman to add).

### The 5 Answers (Verbatim / As Relayed):
1. **Risk model HIGH raising level**: Risk model HIGH may raise a Green (routine) check-in to Yellow (review): **YES**.
2. **Trend raise**: "5 check-ins / BP charting to be done before referring pt for review" -> The trend rule needs at least 5 check-ins with readings, and the provider must see the BP chart when a check-in is raised by trend.
3. **Heart-disease risk bands**: Heart-disease risk bands Low < 10%, Moderate 10-20%, High >= 20%: **YES**.
4. **Referral for dual conditions**: Referral for diabetes + hypertension together: **Internal Medicine**.
5. **Patient risk visibility**: Patients should see their risk band too: **YES**. (This changes the earlier provider-only decision D12; recorded as a change dated 8 Nov 2026 across `CLINICIAN_RESPONSES.md` and `docs/RISK_PANEL.md`).

