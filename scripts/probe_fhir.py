#!/usr/bin/env python3
"""
Probe FHIR R4 servers: is the server reachable, what does it say about itself, does it have
patients, and (for one patient) which vital-sign, lab and medication data does it hold?

Standard library only. Read-only (GET requests). No secrets are used or printed.

Usage:
    python scripts/probe_fhir.py
    python scripts/probe_fhir.py --base https://example.org/fhir --patient 12345
    python scripts/probe_fhir.py --timeout 15 --out fhir_probe_report.json

With no --base the script probes the public test servers below, plus the FHIR_BASE_URL found in
backend-poc-technical/.env (only that one key is read) or in the environment.
"""
import argparse
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

PUBLIC_SERVERS = [
    "https://r4.smarthealthit.org",
    "https://hapi.fhir.org/baseR4",
    "https://server.fire.ly/r4",
    "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d",
    "https://launch.smarthealthit.org/v/r4/fhir",
]
HEADERS = {"Accept": "application/fhir+json", "User-Agent": "ChronicCare-AI-probe/1.0"}


def get(url, timeout):
    """One GET. Never raises. error_kind: dns, timeout, tls, connection, http, invalid_json."""
    started = time.monotonic()
    result = {"url": url, "ok": False, "status": None, "ms": None, "error_kind": None, "error": None, "json": None}
    try:
        request = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            result["status"] = response.status
            try:
                result["json"] = json.loads(raw.decode("utf-8"))
                result["ok"] = 200 <= response.status < 300
            except ValueError:
                result["error_kind"] = "invalid_json"
                result["error"] = "response is not JSON"
    except urllib.error.HTTPError as exc:
        result["status"] = exc.code
        result["error_kind"] = "http"
        result["error"] = f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.gaierror):
            result["error_kind"] = "dns"
        elif isinstance(reason, (socket.timeout, TimeoutError)):
            result["error_kind"] = "timeout"
        elif isinstance(reason, ssl.SSLError):
            result["error_kind"] = "tls"
        else:
            result["error_kind"] = "connection"
        result["error"] = str(reason)[:160]
    except (socket.timeout, TimeoutError):
        result["error_kind"], result["error"] = "timeout", "timed out"
    except Exception as exc:  # last resort so one bad server never stops the run
        result["error_kind"], result["error"] = "connection", f"{type(exc).__name__}: {exc}"[:160]
    result["ms"] = round((time.monotonic() - started) * 1000)
    return result


def entries(bundle):
    if isinstance(bundle, dict) and bundle.get("resourceType") == "Bundle":
        return [e.get("resource") or {} for e in bundle.get("entry", [])]
    return []


def loinc_codes(resources):
    counts = Counter()
    for res in resources:
        for coding in (res.get("code") or {}).get("coding", []):
            if coding.get("system", "").endswith("loinc.org") and coding.get("code"):
                counts[f"{coding['code']} {coding.get('display', '')[:28]}".strip()] += 1
        for comp in res.get("component", []):
            for coding in (comp.get("code") or {}).get("coding", []):
                if coding.get("system", "").endswith("loinc.org") and coding.get("code"):
                    counts[f"{coding['code']} (component)"] += 1
    return counts.most_common(8)


def configured_base():
    value = os.environ.get("FHIR_BASE_URL", "").strip()
    env_path = os.path.join("backend-poc-technical", ".env")
    if not value and os.path.exists(env_path):
        with open(env_path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if line.strip().startswith("FHIR_BASE_URL="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
    return value.rstrip("/")


def probe_server(base, patient, timeout):
    base = base.rstrip("/")
    report = {"base": base}
    meta = get(f"{base}/metadata?_summary=true", timeout)
    body = meta["json"] or {}
    report["metadata"] = {"ok": meta["ok"], "status": meta["status"], "ms": meta["ms"],
                          "error_kind": meta["error_kind"], "error": meta["error"],
                          "fhir_version": body.get("fhirVersion"),
                          "software": (body.get("software") or {}).get("name")}
    search = get(f"{base}/Patient?_count=3&_elements=id,birthDate,gender", timeout)
    patients = entries(search["json"])
    report["patient_search"] = {"ok": search["ok"], "status": search["status"], "ms": search["ms"],
                                "error_kind": search["error_kind"], "count": len(patients),
                                "ids": [p.get("id") for p in patients]}
    chosen = patient or (patients[0].get("id") if patients else None)
    if chosen:
        quoted = urllib.parse.quote(str(chosen))
        one = get(f"{base}/Patient/{quoted}", timeout)
        obs = get(f"{base}/Observation?patient={quoted}&_count=50&_sort=-date", timeout)
        meds = get(f"{base}/MedicationRequest?patient={quoted}&_count=50", timeout)
        conds = get(f"{base}/Condition?patient={quoted}&_count=50", timeout)
        obs_res = entries(obs["json"])
        report["patient"] = {
            "id": chosen,
            "read": {"ok": one["ok"], "status": one["status"], "ms": one["ms"], "error_kind": one["error_kind"],
                     "birthDate": (one["json"] or {}).get("birthDate")},
            "observations": {"ok": obs["ok"], "status": obs["status"], "ms": obs["ms"], "count": len(obs_res),
                             "latest": next((o.get("effectiveDateTime") or o.get("issued") for o in obs_res), None),
                             "top_codes": loinc_codes(obs_res)},
            "medication_requests": {"ok": meds["ok"], "status": meds["status"], "count": len(entries(meds["json"]))},
            "conditions": {"ok": conds["ok"], "status": conds["status"], "count": len(entries(conds["json"]))},
        }
    return report


def verdict(report):
    meta, search = report["metadata"], report["patient_search"]
    if not meta["ok"] and not search["ok"]:
        return f"DOWN ({meta['error_kind'] or meta['status']})"
    patient = report.get("patient")
    if patient and patient["observations"]["count"] == 0:
        return "UP, but the chosen patient has no observations"
    if search["ok"] and meta["ok"]:
        return "UP"
    return "PARTLY UP (check the details)"


def main():
    parser = argparse.ArgumentParser(description="Probe FHIR R4 servers (read-only).")
    parser.add_argument("--base", action="append", help="FHIR base URL (repeatable)")
    parser.add_argument("--patient", help="patient id to inspect on every server")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--out", default="fhir_probe_report.json")
    args = parser.parse_args()

    bases = list(args.base or [])
    if not bases:
        configured = configured_base()
        if configured:
            bases.append(configured)
        bases.extend(s for s in PUBLIC_SERVERS if s not in bases)

    reports = []
    for base in bases:
        print(f"\n=== {base}")
        report = probe_server(base, args.patient, args.timeout)
        reports.append(report)
        meta, search = report["metadata"], report["patient_search"]
        print(f"  metadata        : {'ok' if meta['ok'] else 'FAIL'}  status={meta['status']}  {meta['ms']} ms"
              f"  fhir={meta['fhir_version']}  software={meta['software']}  error={meta['error_kind'] or '-'}")
        print(f"  patient search  : {'ok' if search['ok'] else 'FAIL'}  status={search['status']}  {search['ms']} ms"
              f"  found={search['count']}  ids={search['ids']}  error={search['error_kind'] or '-'}")
        p = report.get("patient")
        if p:
            print(f"  patient {p['id']}: read={p['read']['status']} birthDate={p['read']['birthDate']}")
            print(f"    observations  : status={p['observations']['status']} count={p['observations']['count']} latest={p['observations']['latest']}")
            print(f"    top LOINC     : {p['observations']['top_codes']}")
            print(f"    medications   : status={p['medication_requests']['status']} count={p['medication_requests']['count']}")
            print(f"    conditions    : status={p['conditions']['status']} count={p['conditions']['count']}")
        print(f"  VERDICT         : {verdict(report)}")

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"probed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "reports": reports}, handle, indent=2)
    print(f"\nFull report written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
