"""
v3 Personas Real Runner (Stage 9A-5 Task C).
Executes all 52 personas from tests/sim/personas.json under INTERVIEW_ENGINE=v3.
Extracts engine, answers sent (60 chars), system notes returned, odd classes seen,
probes asked, final triage level, expected level, and PASS/FAIL.
Classifies all failures and prints raw responses.
"""

import os
import sys
import time
import json
import jwt
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ["INTERVIEW_ENGINE"] = "v3"

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID

from main import app
from auth import firebase_verify
from data_sources import app_store, local_store

TEST_PROJECT_ID = "test-personas-v3"
TEST_KID = "test-key-personas-v3"

test_db = str(BACKEND_DIR / "test_personas_v3_scratch.db")
os.environ["LOCAL_DB_PATH"] = test_db
os.environ["DB_BACKEND"] = "sqlite"
os.environ["FIREBASE_PROJECT_ID"] = TEST_PROJECT_ID

app_store.migrate(db_path=test_db, backend="sqlite")
local_store.init_db(db_path=test_db)

rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com"),
])
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
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

client = TestClient(app)

def get_token(uid: str):
    now = int(time.time())
    payload = {
        "sub": uid,
        "user_id": uid,
        "email": f"{uid}@demo.com",
        "name": f"Persona {uid}",
        "aud": TEST_PROJECT_ID,
        "iss": f"https://securetoken.google.com/{TEST_PROJECT_ID}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
    }
    return jwt.encode(payload, rsa_key, algorithm="RS256", headers={"kid": TEST_KID})

def bootstrap_patient(uid: str, conditions: list, lang: str = "en", on_insulin: bool = False):
    tok = get_token(uid)
    headers = {"Authorization": f"Bearer {tok}"}
    client.post("/api/auth/session", headers=headers)
    client.post("/api/me/consent", headers=headers, json={"granted": True, "provider_notification": True})
    client.post("/api/me/provider-notification-consent", headers=headers, json={"granted": True})
    prof_lang = "ur" if lang in ("ur", "roman_ur") else "en"
    client.put(
        "/api/me/profile",
        headers=headers,
        json={
            "conditions": conditions,
            "on_insulin_or_sulfonylurea": on_insulin,
            "date_of_birth": "1980-05-15",
            "inclusion_confirmed": True,
            "language": prof_lang,
        },
    )
    return headers

def run_all_personas():
    personas_path = REPO_ROOT / "tests" / "sim" / "personas.json"
    with open(personas_path, "r", encoding="utf-8") as f:
        personas = json.load(f)

    print("=" * 110)
    print(f"STAGE 9A-5 TASK C: 52 PERSONAS REAL v3 ENGINE RUN ({len(personas)} PERSONAS)")
    print("=" * 110)

    results = []

    for p in personas:
        p_id = p["id"]
        lang = p.get("language", "en")
        conditions = p.get("conditions", ["hypertension"])
        on_insulin = p.get("on_insulin", False)
        answers = p.get("answers", [])
        expected_level = p.get("expected_level", "routine").lower()

        uid = f"per_{p_id}_{int(time.time()*1000)%1000000}_{os.urandom(2).hex()}"
        headers = bootstrap_patient(uid, conditions, lang, on_insulin)

        start_resp = client.post("/api/checkins/start", headers=headers)
        if start_resp.status_code != 200:
            print(f"ERROR: failed to start checkin for {p_id}: {start_resp.text}")
            continue

        start_body = start_resp.json()
        c_id = start_body["checkin_id"]
        engine_start = start_body.get("engine", "unknown")

        answers_sent = []
        system_notes = []
        odd_classes = []
        probes_asked = []
        is_emergency = False
        emergency_reason = None
        engines_seen = {engine_start}

        last_ans_body = None

        for ans in answers:
            ans_trunc = ans[:60].replace("\n", " ")
            answers_sent.append(ans_trunc)

            ans_resp = client.post(f"/api/checkins/{c_id}/answer", headers=headers, json={"answer": ans})
            if ans_resp.status_code == 403 and "pregnant" in ans_resp.text:
                # Pregnancy eligibility exit: checkin stopped cleanly
                break
            if ans_resp.status_code != 200:
                print(f"Turn error {ans_resp.status_code} on {p_id}: {ans_resp.text}")
                break
            body = ans_resp.json()
            last_ans_body = body

            eng = body.get("engine")
            if eng:
                engines_seen.add(eng)

            sn = body.get("system_note")
            if sn and sn not in system_notes:
                system_notes.append(sn)

            odd_cls = body.get("last_odd_class")
            if odd_cls and odd_cls not in odd_classes:
                odd_classes.append(odd_cls)

            if body.get("is_probe") or (body.get("step") and str(body.get("step")).startswith("probe_")):
                probe_id = body.get("step") or "probe"
                if probe_id not in probes_asked:
                    probes_asked.append(probe_id)

            if body.get("emergency"):
                is_emergency = True
                emergency_reason = body.get("emergency_reason")
                break
            if body.get("complete"):
                break

        # Complete check-in
        comp_resp = client.post(f"/api/checkins/{c_id}/complete", headers=headers)
        comp_body = comp_resp.json() if comp_resp.status_code == 200 else {}

        if is_emergency:
            final_level = "emergency"
            raw_final = last_ans_body or comp_body
        else:
            triage_dict = comp_body.get("triage") or {}
            final_level = triage_dict.get("level", "routine").lower()
            raw_final = comp_body

        passed = (final_level == expected_level)
        results.append({
            "id": p_id,
            "name": p.get("name", p_id),
            "archetype": p.get("archetype", "unknown"),
            "engines": list(engines_seen),
            "answers_sent": answers_sent,
            "system_notes": system_notes,
            "odd_classes": odd_classes,
            "probes_asked": probes_asked,
            "final_level": final_level,
            "expected_level": expected_level,
            "passed": passed,
            "raw_response": raw_final,
        })

    # Print Table
    print("\n| ID | Archetype | Engine | Answers Sent (First 60 chars) | System Notes Returned | Odd Classes Seen | Probes Asked | Final Level | Expected | Status |")
    print("|:---|:---|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|")

    for r in results:
        eng_str = "/".join(r["engines"])
        ans_str = "; ".join(f"\"{a}\"" for a in r["answers_sent"][:2]) + (f" (+{len(r['answers_sent'])-2} more)" if len(r['answers_sent']) > 2 else "")
        sn_str = "; ".join(f"\"{s[:35]}...\"" for s in r["system_notes"]) if r["system_notes"] else "(none)"
        odd_str = ", ".join(r["odd_classes"]) if r["odd_classes"] else "none"
        probes_count = len(r["probes_asked"])
        status_str = "**PASS**" if r["passed"] else "**FAIL**"
        print(f"| `{r['id']}` | {r['archetype']} | {eng_str} | {ans_str} | {sn_str} | {odd_str} | {probes_count} | `{r['final_level']}` | `{r['expected_level']}` | {status_str} |")

    pass_count = sum(1 for r in results if r["passed"])
    fail_count = len(results) - pass_count
    print(f"\nTOTAL: {len(results)} personas | PASSED: {pass_count} | FAILED: {fail_count}")

    # Section for Failing Personas
    print("\n" + "=" * 110)
    print("DETAILED FAILURE CLASSIFICATION AND RAW RESPONSES")
    print("=" * 110)

    for r in results:
        if not r["passed"]:
            p_id = r["id"]
            final_lvl = r["final_level"]
            exp_lvl = r["expected_level"]

            # Classify
            if p_id == "p46_elderly_complex_meds":
                classification = "engine over-triage (red-flag pattern 'confused' in Turn 1 text 'Feeling a bit confused by all my morning pills')"
            elif LEVEL_RANK_VAL(final_lvl) < LEVEL_RANK_VAL(exp_lvl):
                classification = "engine under-triage"
            else:
                classification = "engine over-triage"

            print(f"\n### Persona: `{p_id}` ({r['name']})")
            print(f"- **Archetype:** {r['archetype']}")
            print(f"- **Final Level:** `{final_lvl}` vs **Expected:** `{exp_lvl}`")
            print(f"- **Classification:** `{classification}`")
            print(f"- **Raw Final API Response:**")
            print("```json")
            print(json.dumps(r["raw_response"], indent=2))
            print("```")

    return results

def LEVEL_RANK_VAL(lvl: str) -> int:
    ranks = {"routine": 0, "review": 1, "urgent": 2, "emergency": 3}
    return ranks.get(lvl, 0)

if __name__ == "__main__":
    run_all_personas()
