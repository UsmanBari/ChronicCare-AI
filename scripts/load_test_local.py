#!/usr/bin/env python3
"""
Local load test for the ChronicCare AI backend (Iteration 1 evidence, task I2-8 baseline).

What it does
  * Starts the REAL FastAPI app (main.app) under uvicorn on 127.0.0.1 with a temporary SQLite database.
  * Signs real RS256 test tokens (same method as the test-suite). Only the source of Google's public key is replaced
    by a local test key, so the whole token check still runs.
  * Runs N simulated patients at the same time. Each patient does a full check-in:
    POST /api/auth/session, consent, profile, POST /api/checkins/start, 5 x /answer, POST /complete.
  * Also hammers GET /api/health.
  * Prints per-step latency (median, p95, max), error counts and throughput for several concurrency levels.

What it does NOT measure (state this in the report)
  * The deployed Render/Aiven/Netlify stack, network latency, Firebase's real key fetch, the optional LLM or voice calls.
  * MySQL behaviour. This run uses SQLite, which allows one writer at a time.

Usage (from the repository root):
    python scripts/load_test_local.py                       # levels 1,5,10,25
    python scripts/load_test_local.py --levels 1 10 50 --out docs/LOAD_TEST_RESULTS.md
"""
import argparse, os, sys, tempfile, threading, time, datetime, statistics, socket, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend-poc-technical")
sys.path.insert(0, BACKEND)

PROJECT_ID = "test-chroniccare-ai"
KID = "load-test-key-1"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def pct(values, p):
    if not values: return 0.0
    v = sorted(values); k = min(len(v) - 1, int(round((p / 100.0) * (len(v) - 1)))); return v[k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 5, 10, 25])
    ap.add_argument("--health-requests", type=int, default=500)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="cc_load_")
    db = os.path.join(tmp, "load.db")
    os.environ.update({"LOCAL_DB_PATH": db, "DB_BACKEND": "sqlite", "FIREBASE_PROJECT_ID": PROJECT_ID})
    os.chdir(BACKEND)

    import jwt, requests, uvicorn
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from auth import firebase_verify
    from data_sources import app_store, local_store

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "securetoken@system.gserviceaccount.com")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=10)).sign(key, hashes.SHA256()))
    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    keys = {KID: pem}
    firebase_verify._KEY_CACHE = {"keys": keys, "expires_at": time.time() + 36000}
    firebase_verify.fetch_google_public_keys = lambda force_refresh=False: keys

    app_store.migrate(db_path=db, backend="sqlite")
    local_store.init_db(db_path=db)
    import main as appmod

    port = free_port()
    server = uvicorn.Server(uvicorn.Config(appmod.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True); th.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if requests.get(base + "/api/health", timeout=1).status_code == 200: break
        except Exception: time.sleep(0.1)

    def token(uid):
        t = int(time.time())
        return jwt.encode({"sub": uid, "user_id": uid, "email": f"{uid}@load.test", "name": uid, "aud": PROJECT_ID,
                           "iss": f"https://securetoken.google.com/{PROJECT_ID}", "iat": t, "exp": t + 3600, "auth_time": t},
                          key, algorithm="RS256", headers={"kid": KID})

    ANSWERS = ["I feel good today", "120 mg/dL", "No new symptoms", "Yes, took my metformin as prescribed", "No changes"]

    def one_patient(uid, lat, errs):
        s = requests.Session(); h = {"Authorization": f"Bearer {token(uid)}"}
        def call(step, method, path, **kw):
            t0 = time.perf_counter()
            try:
                r = s.request(method, base + path, headers=h, timeout=60, **kw)
                ok = r.status_code == 200
            except Exception as e:
                r = None; ok = False
            lat.setdefault(step, []).append((time.perf_counter() - t0) * 1000)
            if not ok: errs.append((step, None if r is None else r.status_code, "" if r is None else r.text[:120]))
            return r
        call("session", "POST", "/api/auth/session")
        call("consent", "POST", "/api/me/consent", json={"granted": True})
        call("profile", "PUT", "/api/me/profile", json={"conditions": ["diabetes"], "on_insulin_or_sulfonylurea": False, "language": "en", "date_of_birth": "1980-01-01", "inclusion_confirmed": True})
        r = call("start", "POST", "/api/checkins/start")
        if r is None or r.status_code != 200: return
        cid = r.json()["checkin_id"]
        for a in ANSWERS: call("answer", "POST", f"/api/checkins/{cid}/answer", json={"answer": a})
        call("complete", "POST", f"/api/checkins/{cid}/complete")

    report = ["# Local load test results", "",
              f"Run: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} on one machine, real FastAPI app, temporary SQLite, signed RS256 tokens.", "",
              "**Scope:** local only. Not the deployed Render/Aiven stack. SQLite allows one writer at a time, so write-heavy steps are the worst case.", ""]
    # Health
    lat = []; errs = []
    def hammer(n):
        s = requests.Session()
        for _ in range(n):
            t0 = time.perf_counter()
            try: ok = s.get(base + "/api/health", timeout=30).status_code == 200
            except Exception: ok = False
            lat.append((time.perf_counter() - t0) * 1000)
            if not ok: errs.append(1)
    t0 = time.perf_counter(); per = max(1, args.health_requests // 10)
    ths = [threading.Thread(target=hammer, args=(per,)) for _ in range(10)]
    [t.start() for t in ths]; [t.join() for t in ths]; dur = time.perf_counter() - t0
    report += ["## GET /api/health (10 concurrent clients)", "",
               "| Requests | Errors | Median ms | p95 ms | Max ms | Requests/s |", "|---|---|---|---|---|---|",
               f"| {len(lat)} | {len(errs)} | {statistics.median(lat):.1f} | {pct(lat,95):.1f} | {max(lat):.1f} | {len(lat)/dur:.0f} |", ""]
    # Full check-ins
    report += ["## Full check-in flow (session, consent, profile, start, 5 answers, complete)", "",
               "| Simultaneous patients | Check-ins finished | Failed requests | Slowest step (p95 ms) | Complete p95 ms | Whole check-in median s | Check-ins/s |", "|---|---|---|---|---|---|---|"]
    detail = []; counter = 0
    for n in args.levels:
        lat = {}; errs = []; totals = []
        def run(uid):
            t0 = time.perf_counter(); local = {}
            one_patient(uid, lat, errs); totals.append(time.perf_counter() - t0)
        t0 = time.perf_counter(); ths = []
        for i in range(n):
            counter += 1; ths.append(threading.Thread(target=run, args=(f"load-user-{counter}",)))
        [t.start() for t in ths]; [t.join() for t in ths]; dur = time.perf_counter() - t0
        steps = {k: pct(v, 95) for k, v in lat.items()}
        slow = max(steps.items(), key=lambda kv: kv[1])
        completed = len(lat.get("complete", []))
        report.append(f"| {n} | {completed} | {len(errs)} | {slow[0]} {slow[1]:.0f} | {steps.get('complete',0):.0f} | {statistics.median(totals):.2f} | {n/dur:.1f} |")
        detail.append((n, {k: (statistics.median(v), pct(v, 95), max(v), len(v)) for k, v in lat.items()}, errs[:3]))
    report += ["", "## Per-step latency (median / p95 / max ms)", ""]
    for n, d, e in detail:
        report.append(f"**{n} simultaneous patients**"); report.append("")
        report += ["| Step | Calls | Median | p95 | Max |", "|---|---|---|---|---|"]
        for k, (m, p, mx, c) in d.items(): report.append(f"| {k} | {c} | {m:.0f} | {p:.0f} | {mx:.0f} |")
        if e: report += ["", f"First errors: `{json.dumps(e)}`"]
        report.append("")
    out = "\n".join(report)
    print(out)
    if args.out:
        with open(os.path.join(ROOT, args.out) if not os.path.isabs(args.out) else args.out, "w", encoding="utf-8") as f: f.write(out + "\n")
    server.should_exit = True


if __name__ == "__main__":
    main()
