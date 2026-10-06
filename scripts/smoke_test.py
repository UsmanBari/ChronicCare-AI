#!/usr/bin/env python3
"""
Post-deployment smoke test. Standard library only. Read-only. Never prints tokens or secrets.

Usage:
    python scripts/smoke_test.py --backend https://example.onrender.com --frontend https://example.netlify.app
    python scripts/smoke_test.py --backend http://localhost:8000 --frontend http://localhost:3000 --wait 0

Checks:
 1. GET  {backend}/api/health                        -> 200 and the body says "healthy"
    (a sleeping free host is given up to --wait seconds to wake up)
 2. GET  {backend}/api/me/profile with no token      -> 401 (protected routes are closed)
 3. POST {backend}/api/auth/session with a fake token -> 401. A 503 means sign-in is not configured
    (FIREBASE_PROJECT_ID missing), which is reported as a failure with that hint.
 4. OPTIONS {backend}/api/me/profile from the frontend origin -> Access-Control-Allow-Origin equals
    that origin (CORS is configured for the deployed frontend)
 5. GET  {frontend}/                                  -> 200 and the page mentions ChronicCare

Exit code 0 when every check passes, 1 otherwise.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FAKE_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IngiLCJ0eXAiOiJKV1QifQ.e30.YWJj"   # valid shape, not a real token


def call(method, url, headers=None, timeout=30):
    """One request. Never raises. Returns (status or None, headers dict (lower-case keys), body text, error)."""
    request = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            pass
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, body, None
    except Exception as exc:
        return None, {}, "", f"{type(exc).__name__}: {str(exc)[:120]}"


def origin_of(url):
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def main():
    parser = argparse.ArgumentParser(description="Post-deployment smoke test (read-only).")
    parser.add_argument("--backend", required=True)
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--wait", type=float, default=600, help="seconds to wait for a sleeping backend (default 600)")
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    backend, frontend = args.backend.rstrip("/"), args.frontend.rstrip("/")
    results = []

    def record(name, ok, detail):
        results.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    # 1. health, with patience for a free host that is waking up
    deadline = time.monotonic() + max(args.wait, 0)
    attempt, status, body, error = 0, None, "", None
    started = time.monotonic()
    while True:
        attempt += 1
        status, _, body, error = call("GET", f"{backend}/api/health", timeout=30)
        if status == 200 or time.monotonic() >= deadline:
            break
        time.sleep(args.interval)
    waited = round(time.monotonic() - started)
    healthy = status == 200 and "healthy" in body.lower()
    record("backend health", healthy,
           f"status={status} after {attempt} attempt(s), {waited}s" + (f", error={error}" if error else ""))

    # 2. a protected route without a token
    status, _, _, error = call("GET", f"{backend}/api/me/profile")
    record("protected route is closed", status == 401, f"status={status}" + (f", error={error}" if error else ""))

    # 3. the sign-in configuration (a fake token must be answered 401, never 503)
    status, _, body, error = call("POST", f"{backend}/api/auth/session", headers={"Authorization": f"Bearer {FAKE_TOKEN}"})
    hint = " (503: sign-in is not configured; set FIREBASE_PROJECT_ID on the backend)" if status == 503 else ""
    record("sign-in configured", status == 401, f"status={status}{hint}" + (f", error={error}" if error else ""))

    # 4. CORS for the deployed frontend
    origin = origin_of(frontend)
    status, headers, _, error = call("OPTIONS", f"{backend}/api/me/profile", headers={
        "Origin": origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"})
    allowed = headers.get("access-control-allow-origin")
    record("CORS allows the frontend", status in (200, 204) and allowed == origin,
           f"status={status}, allow-origin={allowed!r}, expected={origin!r}" + (f", error={error}" if error else ""))

    # 5. the frontend is served
    status, _, body, error = call("GET", f"{frontend}/")
    record("frontend is served", status == 200 and "chroniccare" in body.lower(),
           f"status={status}" + (f", error={error}" if error else ""))

    print(f"\n{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
