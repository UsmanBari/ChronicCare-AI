"""
Generate API contract examples for Risk Assessment, Guideline Explanation,
and Decision Trace across patient and provider endpoints.
Outputs docs/API_RISK_EXPLAIN.md with real, verified JSON responses.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import jwt
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend-poc-technical"
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set test environment flags
os.environ["RISK_ENABLED"] = "true"
os.environ["RISK_CAN_RAISE"] = "false"
os.environ["EXPLAIN_ENABLED"] = "true"
os.environ["EXPLAIN_MODE"] = "inline"
os.environ["ORCHESTRATOR"] = "direct"
os.environ["FIREBASE_PROJECT_ID"] = "chroniccare-contract-gen"
os.environ["DB_BACKEND"] = "sqlite"

from data_sources import app_store, local_store
import auth.firebase_verify as firebase_verify
from main import app
import rag.explainer as explainer_module

TEST_PROJECT_ID = "chroniccare-contract-gen"
TEST_KID = "test-key-contract-gen"


def setup_hermetic_db(tmp_db_path: str, rsa_key: rsa.RSAPrivateKey):
    """Initializes SQLite DB, migrations, and mock certs."""
    os.environ["LOCAL_DB_PATH"] = tmp_db_path
    app_store.migrate(db_path=tmp_db_path, backend="sqlite")
    local_store.init_db(db_path=tmp_db_path)

    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")]))
        .public_key(rsa_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=10))
        .sign(rsa_key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    mock_keys = {TEST_KID: cert_pem}
    firebase_verify._KEY_CACHE = {"keys": mock_keys, "expires_at": time.time() + 3600}
    firebase_verify.fetch_google_public_keys = lambda force_refresh=False: mock_keys

    # Seed guideline_chunks
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    chunks = [
        ("chunk_htn_stage1", "AHA_ACC_2017", "Blood Pressure Thresholds", "hypertension",
         "Stage 1 hypertension is defined as systolic 130-139 mmHg or diastolic 80-89 mmHg. Lifestyle modifications and monitoring are recommended.",
         now),
        ("chunk_htn_crisis", "AHA_ACC_2017", "Hypertensive Crisis", "hypertension",
         "Hypertensive crisis is defined as systolic over 180 mmHg or diastolic over 120 mmHg requiring prompt medical evaluation.",
         now),
        ("chunk_dm_routine", "ADA_2024", "Glycemic Targets", "diabetes",
         "A target fasting blood glucose of 80-130 mg/dL is recommended for nonpregnant adults.",
         now),
    ]
    with app_store.get_db_cursor(backend="sqlite", db_path=tmp_db_path) as (cur, be, ph):
        for cid, src, title, cond, text, updated in chunks:
            cur.execute(
                f"INSERT OR REPLACE INTO guideline_chunks (chunk_id, source_id, title, condition, text, loaded_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (cid, src, title, cond, text, updated),
            )


def make_token(rsa_key: rsa.RSAPrivateKey, uid: str, role: str = "patient") -> str:
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "name": f"User {uid}",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})


def create_user_and_profile(
    client: TestClient,
    token: str,
    uid: str,
    role: str,
    conditions: List[str],
    waist_cm: Optional[float] = 90.0,
    language: str = "en",
    sex: str = "male",
    dob: str = "1975-06-15",
    height_cm: float = 175.0,
    weight_kg: float = 80.0,
    smoking_status: str = "never",
):
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/auth/session", headers=headers)
    if role == "provider":
        with app_store.get_db_cursor(backend="sqlite") as (cur, be, ph):
            cur.execute(f"UPDATE users SET role = 'provider' WHERE user_id = {ph}", (uid,))
    else:
        local_store.add_local_patient_if_missing(f"local-{uid}", name=f"User {uid}", date_of_birth=dob)
        client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
        client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
        client.put(
            "/api/me/profile",
            headers=headers,
            json={
                "conditions": conditions,
                "on_insulin_or_sulfonylurea": False,
                "date_of_birth": dob,
                "inclusion_confirmed": True,
                "language": language,
                "sex_at_birth": sex,
                "waist_cm": waist_cm,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "smoking_status": smoking_status,
            },
        )
    return headers


def create_v3_checkin(
    uid: str,
    checkin_id: str,
    systolic: float,
    diastolic: float,
    emergency: bool = False,
    emergency_reason: Optional[str] = None,
    conditions_on_file: Optional[List[str]] = None,
):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if emergency:
        raw_state = {
            "engine": "v3",
            "stage1_red_flag": True,
            "stage1_reason": emergency_reason or "chest_pain",
            "intakes": [{"condition": "hypertension", "emergency": True, "reason": emergency_reason or "chest_pain"}],
            "findings": [],
        }
    else:
        raw_state = {
            "engine": "v3",
            "completed": True,
            "conditions_on_file": conditions_on_file or ["hypertension"],
            "readings": {
                "blood_pressure_systolic": systolic,
                "blood_pressure_diastolic": diastolic,
            },
            "findings": [],
        }

    app_store.create_checkin(
        checkin_id=checkin_id,
        user_id=uid,
        mode="isolated",
        record_patient_id=f"local-{uid}",
        state_dict=raw_state,
        status="in_progress" if not emergency else "emergency",
    )


def fake_llm(messages: List[Dict[str, str]], **kwargs) -> str:
    import re
    user_msg = messages[-1]["content"] if messages else ""
    sbp_match = re.search(r'"blood_pressure_systolic":\s*(\d+)', user_msg)
    sbp = sbp_match.group(1) if sbp_match else "136"

    if "Translate the following validated medical sentences into Urdu" in user_msg:
        return json.dumps({
            "sentences": [
                {
                    "text": f"طبی رہنما خطوط کے مطابق آپ کا سسٹولک بلڈ پریشر {sbp} mmHg قدرے زیادہ ہے۔",
                    "cites": ["S1"]
                },
                {
                    "text": "باقاعدگی سے بلڈ پریشر کی جانچ قلبی صحت کی بروقت دیکھ بھال میں مدد دیتی ہے۔",
                    "cites": ["S1"]
                }
            ]
        })
    return json.dumps({
        "sentences": [
            {
                "text": f"Your systolic blood pressure reading of {sbp} mmHg is slightly elevated according to clinical guidelines.",
                "cites": ["S1"]
            },
            {
                "text": "Regular blood pressure monitoring helps track cardiovascular risk over time.",
                "cites": ["S1"]
            }
        ]
    })


def main():
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tmp_db = str(REPO_ROOT / "scratch" / "contract_gen.db")
    os.makedirs(os.path.dirname(tmp_db), exist_ok=True)
    if os.path.exists(tmp_db):
        os.remove(tmp_db)

    setup_hermetic_db(tmp_db, rsa_key)
    client = TestClient(app)

    provider_uid = "doc_contract_01"
    provider_token = make_token(rsa_key, provider_uid, role="provider")
    provider_headers = create_user_and_profile(
        client, provider_token, provider_uid, role="provider", conditions=["hypertension"]
    )

    examples: Dict[str, Dict[str, Any]] = {}

    # Monkeypatch LLM client
    import llm.groq_client as groq_client
    groq_client.chat = fake_llm
    groq_client.is_configured = lambda: True

    # Case 1: OK (HTN patient, risk status ok, explanation llm/grounded)
    uid_ok = "pat_ok_01"
    cid_ok = "chk_contract_ok_01"
    tok_ok = make_token(rsa_key, uid_ok)
    h_ok = create_user_and_profile(client, tok_ok, uid_ok, "patient", ["hypertension"], waist_cm=90.0)
    create_v3_checkin(uid_ok, cid_ok, systolic=136.0, diastolic=86.0)

    resp_complete = client.post(f"/api/checkins/{cid_ok}/complete", headers=h_ok)
    resp_review = client.get(f"/api/provider/review/{cid_ok}", headers=provider_headers)
    examples["ok"] = {
        "patient_view": resp_complete.json(),
        "provider_view": resp_review.json(),
    }

    # Case 2: Not Enough Information (Missing waist)
    uid_noi = "pat_noi_02"
    cid_noi = "chk_contract_noi_02"
    tok_noi = make_token(rsa_key, uid_noi)
    h_noi = create_user_and_profile(client, tok_noi, uid_noi, "patient", ["hypertension"], waist_cm=None)
    create_v3_checkin(uid_noi, cid_noi, systolic=134.0, diastolic=84.0)

    resp_complete = client.post(f"/api/checkins/{cid_noi}/complete", headers=h_noi)
    resp_review = client.get(f"/api/provider/review/{cid_noi}", headers=provider_headers)
    examples["not_enough_information"] = {
        "patient_view": resp_complete.json(),
        "provider_view": resp_review.json(),
    }

    # Case 3: Not Applicable (Diabetes patient)
    uid_na = "pat_na_03"
    cid_na = "chk_contract_na_03"
    tok_na = make_token(rsa_key, uid_na)
    h_na = create_user_and_profile(client, tok_na, uid_na, "patient", ["diabetes", "hypertension"], waist_cm=90.0)
    create_v3_checkin(uid_na, cid_na, systolic=130.0, diastolic=82.0, conditions_on_file=["diabetes", "hypertension"])

    resp_complete = client.post(f"/api/checkins/{cid_na}/complete", headers=h_na)
    resp_review = client.get(f"/api/provider/review/{cid_na}", headers=provider_headers)
    examples["not_applicable"] = {
        "patient_view": resp_complete.json(),
        "provider_view": resp_review.json(),
    }

    # Case 4: Error handling (Risk agent raises unexpected error)
    uid_err = "pat_err_04"
    cid_err = "chk_contract_err_04"
    tok_err = make_token(rsa_key, uid_err)
    h_err = create_user_and_profile(client, tok_err, uid_err, "patient", ["hypertension"], waist_cm=90.0)
    create_v3_checkin(uid_err, cid_err, systolic=132.0, diastolic=82.0)

    import agents.risk_agent as ra
    original_assess = ra.assess
    def broken_assess(*args, **kwargs):
        raise RuntimeError("Simulated transient computation glitch")
    ra.assess = broken_assess

    try:
        resp_complete = client.post(f"/api/checkins/{cid_err}/complete", headers=h_err)
        resp_review = client.get(f"/api/provider/review/{cid_err}", headers=provider_headers)
        examples["error"] = {
            "patient_view": resp_complete.json(),
            "provider_view": resp_review.json(),
        }
    finally:
        ra.assess = original_assess

    # Case 5: Emergency (Stage 1 red flag / crisis)
    uid_emg = "pat_emg_05"
    cid_emg = "chk_contract_emg_05"
    tok_emg = make_token(rsa_key, uid_emg)
    h_emg = create_user_and_profile(client, tok_emg, uid_emg, "patient", ["hypertension"], waist_cm=90.0)
    create_v3_checkin(uid_emg, cid_emg, systolic=190.0, diastolic=125.0, emergency=True, emergency_reason="hypertensive_crisis_chest_pain")

    resp_complete = client.post(f"/api/checkins/{cid_emg}/complete", headers=h_emg)
    resp_review = client.get(f"/api/provider/review/{cid_emg}", headers=provider_headers)
    examples["emergency"] = {
        "patient_view": resp_complete.json(),
        "provider_view": resp_review.json(),
    }

    # Case 6: Template Mode Explanation (LLM disabled / None)
    uid_tmpl = "pat_tmpl_06"
    cid_tmpl = "chk_contract_tmpl_06"
    tok_tmpl = make_token(rsa_key, uid_tmpl)
    h_tmpl = create_user_and_profile(client, tok_tmpl, uid_tmpl, "patient", ["hypertension"], waist_cm=90.0)
    create_v3_checkin(uid_tmpl, cid_tmpl, systolic=135.0, diastolic=85.0)

    groq_client.is_configured = lambda: False
    try:
        resp_complete = client.post(f"/api/checkins/{cid_tmpl}/complete", headers=h_tmpl)
        resp_review = client.get(f"/api/provider/review/{cid_tmpl}", headers=provider_headers)
        examples["template_mode"] = {
            "patient_view": resp_complete.json(),
            "provider_view": resp_review.json(),
        }
    finally:
        groq_client.is_configured = lambda: True

    # Case 7: Urdu Explanation (Language="ur")
    uid_ur = "pat_ur_07"
    cid_ur = "chk_contract_ur_07"
    tok_ur = make_token(rsa_key, uid_ur)
    h_ur = create_user_and_profile(client, tok_ur, uid_ur, "patient", ["hypertension"], waist_cm=90.0, language="ur")
    create_v3_checkin(uid_ur, cid_ur, systolic=136.0, diastolic=86.0)

    resp_complete = client.post(f"/api/checkins/{cid_ur}/complete", headers=h_ur)
    resp_review = client.get(f"/api/provider/review/{cid_ur}", headers=provider_headers)
    examples["urdu"] = {
        "patient_view": resp_complete.json(),
        "provider_view": resp_review.json(),
    }

    # Build markdown documentation
    md_content = build_contract_markdown(examples)
    doc_path = REPO_ROOT / "docs" / "API_RISK_EXPLAIN.md"
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Generated {doc_path} successfully ({len(md_content)} bytes).")


def build_contract_markdown(examples: Dict[str, Dict[str, Any]]) -> str:
    """Builds the comprehensive Markdown document for Hassaan."""
    def j(obj: Any) -> str:
        return json.dumps(obj, indent=2, ensure_ascii=False)

    return f"""# API Contract: Risk Advisory, Guideline Explanation & Decision Trace

**Audience:** Frontend Engineers (Hassaan), Clinicians, and QA.  
**Version:** 1.0 (Schema v15, Feature flags: `RISK_ENABLED`, `EXPLAIN_ENABLED`, `RISK_CAN_RAISE`).  
**Generated By:** `scripts/gen_api_risk_explain_examples.py` using live test responses.

---

## 1. Architectural Summary & Field Naming

To protect clinical safety and prevent patient distress:
1. **Motto**: *"The model proposes, the rules decide."*
2. **Strict Leak Defense**:
   - On the **Patient endpoint** (`POST /api/checkins/{{id}}/complete`), the `risk` object contains **ONLY** qualitative bands (`low`, `moderate`, `high`) and clinical reasoning strings. **It strictly never contains numerical probabilities, regression logits, model names, or version strings.**
   - On the **Provider Review endpoint** (`GET /api/provider/review/{{id}}` and `POST /api/provider/review/{{id}}/action`):
     - `risk`: The **live** provider panel evaluated dynamically at review time (from PR #90 via `_compute_patient_risk_safe`).
     - `checkin_risk`: The **frozen risk record** evaluated and stored at check-in completion time. It includes `probability`, `model`, `version`, `raised`, and `caveats`.
     - `explanation`: Full guideline explanation payload with retrieved source chunks and mode.
     - `trace`: The audit decision trace sequence showing every executed pipeline node.
3. **Emergency Invariant**:
   - In any emergency check-in (stage 1 red flag or crisis vitals), **both risk and explanation are `null`**. No risk or guideline explanations are calculated or displayed during an emergency.
4. **Graceful Fallback**:
   - If `RISK_ENABLED=false` or `EXPLAIN_ENABLED=false`, both fields are `null`.
   - If an error occurs in the risk model or RAG explainer, the check-in completes safely, the clinical triage level is preserved intact, and safe fallback states (`status: "error"` or template mode) are returned.

---

## 2. Response Fields Reference Table

| Field Path | Endpoint | Type | Description |
|---|---|---|---|
| `risk` | `CheckinCompleteResponse` (Patient) | `Optional[Dict]` | Patient view: `band`, `reasons`, `caveats`. **No probability.** |
| `explanation` | `CheckinCompleteResponse` (Patient) | `Optional[Dict]` | Patient view: `sentences` and `sources` only. |
| `risk` | `ReviewDetailResponse` (Provider) | `Optional[Dict]` | Live provider risk panel computed dynamically on request. |
| `checkin_risk` | `ReviewDetailResponse` (Provider) | `Optional[Dict]` | Frozen risk snapshot stored at check-in time (`probability`, `band`, `raised`, `model`, `version`, `caveats`). |
| `explanation` | `ReviewDetailResponse` (Provider) | `Optional[Dict]` | Full guideline explanation object (`status`, `mode`, `sentences`, `sources`, `rejected_reasons`). |
| `trace` | `ReviewDetailResponse` (Provider) | `Optional[List[Dict]]` | Execution trace steps. Contains node names and aggregate counts; contains no PHI or reading values. |

---

## 3. Real JSON Payloads Across All States

### State 1: `ok` (Complete Hypertension Patient)
Hypertension patient with complete readings and profile. Risk is computed; explanation is grounded via LLM.

#### Patient View (`POST /api/checkins/{{id}}/complete`):
```json
{j(examples["ok"]["patient_view"])}
```

#### Provider View (`GET /api/provider/review/{{id}}`):
```json
{j(examples["ok"]["provider_view"])}
```

---

### State 2: `not_enough_information` (Missing Waist Circumference)
Patient has hypertension and blood pressure readings, but waist circumference is not recorded. Risk cannot be calculated.

#### Patient View:
```json
{j(examples["not_enough_information"]["patient_view"])}
```

#### Provider View:
```json
{j(examples["not_enough_information"]["provider_view"])}
```

---

### State 3: `not_applicable` (Diabetes Patient)
Diabetes patient: diabetes screening model not applicable; heart-disease model applies.

#### Patient View:
```json
{j(examples["not_applicable"]["patient_view"])}
```

#### Provider View:
```json
{j(examples["not_applicable"]["provider_view"])}
```

---

### State 4: `error` (Safe Handling of Computation Glitches)
If an unexpected error occurs during risk computation or RAG generation, the check-in completes normally without blocking the patient.

#### Patient View:
```json
{j(examples["error"]["patient_view"])}
```

#### Provider View:
```json
{j(examples["error"]["provider_view"])}
```

---

### State 5: `emergency` (Stage 1 Red Flag or Clinical Crisis)
During an emergency, all risk and explanation pipelines are bypassed. Both fields are strictly `null`.

#### Patient View:
```json
{j(examples["emergency"]["patient_view"])}
```

#### Provider View:
```json
{j(examples["emergency"]["provider_view"])}
```

---

### State 6: `template_mode` (Pre-verified Fallback Explanation)
When the LLM is offline or output fails strict clinical validation (V1-V5), the system deterministically falls back to pre-verified clinical templates.

#### Patient View:
```json
{j(examples["template_mode"]["patient_view"])}
```

#### Provider View:
```json
{j(examples["template_mode"]["provider_view"])}
```

---

### State 7: `urdu` (Patient Language = `ur`)
When the patient profile language is set to Urdu (`language="ur"`), explanation sentences are translated into Urdu while retaining clinical numbers and citation anchors `[S1]`.

#### Patient View:
```json
{j(examples["urdu"]["patient_view"])}
```

#### Provider View:
```json
{j(examples["urdu"]["provider_view"])}
```

---

## 4. UI Rendering & Wording Guidelines for Frontend

1. **Risk Card Presentation:**
   - **Low**: Display with a neutral/reassuring green badge (e.g. "Low Risk").
   - **Moderate**: Display with an amber/warning badge (e.g. "Moderate Risk"). Include bulleted reasons (e.g. "Elevated BMI", "Waist circumference above guideline threshold").
   - **High**: Display with a clinical review badge (e.g. "High Risk - Follow-up Recommended").
   - **Missing Data**: If `risk.status == "not_enough_information"`, display a card: *"To help assess your health trends, please record your waist circumference in your profile settings."*
2. **Guideline Explanations & Citations:**
   - Display explanation sentences directly below the triage summary.
   - Parse `[S1]`, `[S2]` tokens and render them as interactive superscript citation badges.
   - Clicking a citation badge expands a drawer or popover displaying the source guideline title and section from `sources`.
3. **Emergency Protection:**
   - When `emergency == true`, hide risk and explanation cards completely. Display only the emergency banner and instructions.
"""


if __name__ == "__main__":
    main()
