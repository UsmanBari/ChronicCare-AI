"""
Load test for the DEPLOYED ChronicCare AI stack (public endpoints only).
Standard library only. Run it from your own computer (the sandbox cannot reach the site).

Usage (PowerShell, repo root):
  python scripts/load_test_deployed.py --api https://YOUR-BACKEND.onrender.com --web https://chronicare-ai.netlify.app

What it measures (no login, no patient data, no writes):
  1. Cold start: time of the first GET /api/health (Render free tier may be asleep).
  2. GET /api/health at 1, 5, 10, 25, 50 simultaneous clients (20 requests per client).
  3. GET of the Netlify front page at the same levels.
It prints a Markdown table: requests, failures, median, p95, max (seconds), requests per second.
Be gentle: it stops a level early if more than 20% of requests fail.
"""
import argparse, statistics, threading, time, urllib.request, urllib.error

def hit(url, timeout=70):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "chroniccare-loadtest/1"}), timeout=timeout) as r:
            r.read(2048)
            ok = 200 <= r.status < 400
    except Exception:
        ok = False
    return ok, time.perf_counter() - t

def run_level(url, clients, per_client):
    lat, fails, lock = [], [0], threading.Lock()
    def worker():
        for _ in range(per_client):
            ok, dt = hit(url)
            with lock:
                lat.append(dt)
                if not ok: fails[0] += 1
    t0 = time.perf_counter()
    ts = [threading.Thread(target=worker) for _ in range(clients)]
    [t.start() for t in ts]; [t.join() for t in ts]
    wall = time.perf_counter() - t0
    lat.sort()
    p95 = lat[max(0, int(len(lat) * 0.95) - 1)]
    return len(lat), fails[0], statistics.median(lat), p95, lat[-1], len(lat) / wall

def table(name, url, levels, per_client):
    print(f"\n### {name}: {url}\n")
    print("| Clients | Requests | Failed | Median (s) | p95 (s) | Max (s) | Req/s |")
    print("|---|---|---|---|---|---|---|")
    for c in levels:
        n, f, med, p95, mx, rps = run_level(url, c, per_client)
        print(f"| {c} | {n} | {f} | {med:.3f} | {p95:.3f} | {mx:.3f} | {rps:.1f} |", flush=True)
        if f / n > 0.20:
            print("(stopped: more than 20% failed)"); break
        time.sleep(2)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True, help="backend base URL, e.g. https://xxx.onrender.com")
    ap.add_argument("--web", default="https://chronicare-ai.netlify.app", help="frontend URL")
    ap.add_argument("--per-client", type=int, default=20)
    a = ap.parse_args()
    api = a.api.rstrip("/") + "/api/health"
    print(f"Run at {time.strftime('%Y-%m-%d %H:%M:%S')} from this computer's network.")
    ok, dt = hit(api)
    print(f"\nFirst request (cold start if the server was asleep): {dt:.2f} s, ok={ok}")
    time.sleep(1)
    table("Backend /api/health", api, [1, 5, 10, 25, 50], a.per_client)
    table("Frontend page", a.web, [1, 5, 10, 25, 50], a.per_client)
    print("\nCopy everything above and paste it back in the chat (also save it as docs/LOAD_TEST_DEPLOYED.md).")
