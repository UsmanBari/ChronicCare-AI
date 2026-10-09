# ChronicCare AI: Adaptive Interview v3. Research and Design

Status: **Proposed, not reviewed by a clinician.** Every clinical rule below needs sign-off from a doctor before it is called "validated" in the report.

## 1. What is wrong today

The current interview is a fixed tree with keyword branches. It changes the next question only for a few cases (insulin or not, a missing number, dual diagnosis). It does not use the patient's last check-ins, does not question a suspicious answer, and does not change its wording for the person answering. That is why it feels scripted.

## 2. The design in one line

**The model proposes, the rules decide.** An LLM (Groq) may make the interview sound natural and may read free text into fields. It may never decide an emergency, a triage level, a threshold or any advice. All of that stays in the deterministic, hashed clinical modules.

## 3. How a turn works

1. **Safety screen first (deterministic, no LLM).** The danger-phrase screen runs on the raw answer, in English, Urdu script and Roman Urdu, with negation handling ("no chest pain" is not a red flag, "chest pain nahi" is not a red flag, "unknown" is never read as "no"). Unchanged module.
2. **Read the answer into fields.** Rules first (numbers, units, Urdu digits, "ek sau bees"). If the answer is free text and the LLM is on, Groq returns strict JSON. Every value must come with an exact quote from the patient's own words. A value without a matching quote is thrown away and the field stays "unknown".
3. **Validate.** Range, unit and plausibility checks, then cross-checks against the record (see section 5).
4. **Plan the next question (deterministic).** The planner scores every open field: safety first, then fields that were contradicted, then fields the last 7 check-ins make interesting (rising BP, repeated lows, a missed-dose pattern), then barriers (cost, no device, fasting), then wellbeing. It stops at a question budget (normal 8, extended 12 only if something is concerning). It never asks the same field twice unless it is correcting an answer.
5. **Word the question.** A fixed plain-language template always exists. If the LLM is on, it may rephrase that template for the person (language, reading level, tone). A checker rejects any rephrase that adds a number, advice, a diagnosis, a reassurance ("you are fine") or drops the original meaning, and then the template is used.
6. **Every screen offers** "I don't know", "Skip", "Someone else is answering", and a one-line "why am I being asked this".

If Groq is down, slow, rate-limited or switched off, the interview still works completely with templates. Nothing in a patient's safety depends on the network.

## 4. "Fine-tune Groq" (and why we don't)

I could not find any self-serve fine-tuning on Groq's public docs (the structured-outputs page does not mention it). We don't need it. A fine-tuned model would still be allowed to be wrong, so it would not change the safety design. What we do instead:
- a versioned **question bank** written by us (data, not code), with a source and a review status per question;
- **strict JSON output** where Groq supports it: its docs list strict `json_schema` for `openai/gpt-oss-20b`, `openai/gpt-oss-120b` and `qwen/qwen3.8-27b`, and note that the schema guarantees shape, not truth, and that streaming and tool use are not supported with it. Model names change, so the model is an environment variable and the team re-checks the console when deploying;
- **evidence-quote rule** (section 3 step 2) so the model cannot invent a value;
- a **test set of simulated patients** that measures the whole thing, so improvement is measured, not guessed.

## 5. Handling wrong, odd or contradictory answers

| Situation | What the interview does |
|---|---|
| Impossible number (glucose 5 or 5000, BP "12080", pulse 400) | Repeats it back once: "I heard 5. Is that mmol/L or mg/dL?" Gives a way to correct. |
| Unit confusion (7 vs 126) | Asks the unit, never guesses. |
| Second unclear answer | Stores "unknown, low confidence", moves on, flags for clinician review. Never stored as "no". |
| Contradiction with record (says no insulin, record lists insulin; says took all doses, then says ran out) | One gentle clarifying question, both versions kept, shown to the clinician side by side. |
| Minimiser ("just a little dizzy") | Asks for an anchor ("could you stand and walk to the kitchen?") instead of accepting the word. |
| Over-reporter / wants to please | Normalising wording ("many people miss doses; which days were hard?"). |
| Refuses, silent, or terse | Respects it. Records "declined". Does not nag. |
| Someone else answering | Recorded as `answered_by: caregiver`, confidence lowered, clinician sees it. |
| Rambling long text | Rules read the numbers and danger phrases; the LLM (if on) extracts with quotes; anything unclear is asked once. |
| Distress / hopelessness wording | Deterministic caring message, clinician review flag, no medical advice from the model. The crisis contact text is configuration the team must fill with a verified local number. We do not invent one. |

## 6. Patient types the question bank must cover

Newly diagnosed and long-standing; elderly and low health literacy; Urdu, Roman Urdu and English speakers; voice users; anxious about numbers; low mood or low motivation; caregiver answering; no glucometer or no BP cuff; cost-related skipping of medicines; Ramadan or other fasting (IDF-DAR 2021 gives the framework; our questions ask about fasting and hypoglycaemia risk, the clinician decides advice); shift workers; multimorbidity (diabetes and hypertension together, kidney problems); people on insulin or sulfonylureas (hypoglycaemia branch); people who are unwell (sick-day questions); people on over-the-counter medicines that raise BP; and the doctor-side view: short, structured, with quotes and a clear "patient said / system inferred / unknown" separation.

## 7. Where the clinical content comes from (honest version)

**No public dataset contains interview question flows.** Datasets can test the system, but they cannot teach it what to ask. The questions come from guidelines and validated tools, written in our own words, each with a status.

| Source | Use | Note |
|---|---|---|
| ADA Standards of Care in Diabetes 2026 (Sections 6 and 5; summaries seen at [PMC12690178](https://pmc.ncbi.nlm.nih.gov/articles/PMC12690178) and [Diabetes on the Net](https://diabetesonthenet.com/diabetes-primary-care/factsheet-2026-ada-standards)) | hypoglycaemia screening, fear of hypoglycaemia, psychosocial screening, CGM use | The Diabetes on the Net summary does not list the numeric hypoglycaemia levels; read Section 6 itself before writing thresholds. |
| 2025 AHA/ACC high blood pressure guideline (summary seen at [Medical Dialogues](https://medicaldialogues.in/cardiology-ctvs/guidelines/new-ahaacc-guideline-emphasizes-earlier-treatment-and-better-blood-pressure-control-179692)) | home BP technique, validated cuff, target below 130/80 | Secondary source only; the BP category numbers in that article look loosely written, so cite the guideline itself. |
| IDF-DAR Practical Guidelines 2021 ([IDF](https://idf.org/about-diabetes/resources/diabetes-and-ramadan-practical-guidelines-2021/)) | fasting-period questions | |
| PHQ-2 (public domain) | optional two-item mood screen | Clinician decides if and how results are shown. |
| Diabetes distress items (DDS-2 style) | optional | Check usage terms before copying wording; otherwise write our own plain question. |
| Morisky MMAS-8 | **do not use** | It is licensed. We write our own adherence questions. |
| Synthea (open synthetic patients) | realistic test profiles | Synthetic, not real people. |
| NHANES / similar public surveys | realistic value ranges for plausibility checks | Ranges only, nothing patient-level is needed. |
| MIMIC-III (credentialed, access pending) | not for the interview | Inpatient ICU data. Keep it for the report's data-governance story, not this feature. |
| Research on LLM guardrails for medical interviews (e.g. [CareGuardAI](https://arxiv.org/pdf/2604.26959), [arXiv 2606.18068](https://arxiv.org/pdf/2606.18068)) | supports the "rules decide" design in the report's related work | I only saw titles in search results; the team must read them before citing any claim. |

Anything above marked "check" or "read first" must be checked by a human before it goes into the final report.

## 8. How we will know it is good

A hermetic simulated-patient suite: 40+ scripted personas times scenarios, plus a seeded fuzz run. Hard invariants (any failure fails CI):
- recall of the gold danger-phrase list is 100%, including negation and Roman Urdu cases;
- "unknown" is never stored as "no";
- the same field is never asked twice without a correction reason;
- question count never exceeds the budget;
- the LLM path and the no-LLM path reach the same triage level on every scenario;
- any LLM output that adds a number, advice or a diagnosis is rejected.
Soft metrics are printed in a report file (average questions, fields captured, clarification rate). An offline script, not run in CI, can use an LLM as a simulated patient to find weak spots.

## 9. What still needs a human

A doctor must review the question bank and the thresholds. The team must check each source in the table. A real Groq key and real browsers are needed for the live test. Urdu wording should be read by a native speaker.

## 10. Delving into every answer (drill-down)

Every answer becomes a **finding**: what the patient reported (symptom, reading, medicine problem, lifestyle change, worry), the closed-vocabulary label for it, the attributes we know (when it started, how long, how bad, what brings it on, what eases it, what comes with it) and the exact quote. The bank holds **probe sets** per finding type (dizziness, headache, breathlessness, vision change, thirst or urination, foot problem, low-sugar episode, missed dose, swelling, tiredness, nausea or vomiting, pain, sleep, low mood, "something else"). The planner asks the missing attributes next, at most two follow-ups per finding, and stops probing the moment a danger phrase appears. Follow-ups quote the closed-vocabulary label, never raw patient text, so an answer cannot inject wording into the next question. Example: "dizzy" then "only when I stand up?" then "has it ever made you fall or nearly faint?".

## 11. Odd, off-topic and hostile input

Every answer is classified before it is used. Safety classes always win, and they are decided by rules only (danger phrases, self-harm or hopeless wording, pregnancy statement). The other classes may use the LLM as a hint, never as the decider.

| Class | Example | Response (fixed, short, kind, same in 3 languages) |
|---|---|---|
| Chit-chat / joke / test | "tell me a joke", "lol" | One neutral line, then the same question again. |
| Romantic or flirtatious | "I feel romantic", "I love you" | Polite, no mirroring: "Thank you. I'm an automated assistant, so I can only help with your health check-in." Then, because sexual health changes are a real and common side effect or complication in diabetes and high blood pressure, one optional question: "If you meant a change in desire or sexual function, your clinician wants to know. Add a note? (Yes / No / Skip)". Only a Yes is recorded, and only as a patient-reported note. |
| Insults, abuse | | Calm boundary once. Never answers back in kind. |
| Gibberish, emoji only, empty | "asdkj", "👍👍" | Ask to rephrase once, then offer buttons. |
| Asks for advice, diagnosis, dose change | "should I stop my tablet?" | "I can't advise on that. I've added it to your questions for your clinician." It appears on the provider card. |
| Fear or prognosis | "will I die?" | Caring fixed message, flagged for clinician review. No reassurance and no prediction. |
| Asks about the bot | "are you a doctor?" | Honest fixed answer: automated assistant, not a doctor. |
| Not the patient / third party | "my father feels dizzy" | Ask who is answering; record `answered_by`; keep father's symptoms separate from the patient's record. |
| Mentions being under 18 or pregnant | | Use the existing inclusion handling. |
| Prompt injection | "ignore your rules" | Treated as plain text, fixed reply, nothing executed. |
| Self-harm or hopelessness | | Rules only. Caring fixed message, clinician review flag, verified local help text from configuration. |

Strike rule: after two off-topic answers in a row the interview offers Continue, Skip this question, or Finish for now. After four it ends politely, keeps what it has, and marks "ended early: off-topic input". That mark is not a clinical alert.

## 12. Enterprise quality bar

Accessibility to WCAG 2.2 AA (keyboard only, screen-reader announcements for each new question, contrast, 200% zoom, reduced motion, Urdu right-to-left). A review-and-confirm screen before anything is sent. Resume after an interrupted session. Idempotent submit. Append-only audit trail of every turn (rule id, interview-bank version, no free text beyond what the patient chose to send). Structured logs with request ids and no personal data. Rate limits and size limits. Versioned interview definitions stamped on every check-in. A plain-language microcopy guide so every screen sounds the same. A clinician summary with four blocks: patient said, system read, unclear, questions from the patient.