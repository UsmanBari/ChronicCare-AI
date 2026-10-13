# Local load test results

Run: 2026-10-13 11:13 on one machine, real FastAPI app, temporary SQLite, signed RS256 tokens.

**Scope:** local only. Not the deployed Render/Aiven stack. SQLite allows one writer at a time, so write-heavy steps are the worst case.

## GET /api/health (10 concurrent clients)

| Requests | Errors | Median ms | p95 ms | Max ms | Requests/s |
|---|---|---|---|---|---|
| 1000 | 0 | 14.3 | 24.5 | 36.6 | 650 |

## Full check-in flow (session, consent, profile, start, 5 answers, complete)

| Simultaneous patients | Check-ins finished | Failed requests | Slowest step (p95 ms) | Complete p95 ms | Whole check-in median s | Check-ins/s |
|---|---|---|---|---|---|---|
| 1 | 1 | 0 | complete 16 | 16 | 0.11 | 9.2 |
| 5 | 5 | 0 | complete 279 | 279 | 0.46 | 9.0 |
| 10 | 10 | 0 | consent 293 | 150 | 0.66 | 13.7 |
| 25 | 25 | 0 | session 1339 | 372 | 1.79 | 12.2 |
| 50 | 50 | 0 | session 1946 | 780 | 3.67 | 11.8 |
| 100 | 100 | 0 | consent 2155 | 2055 | 8.47 | 10.4 |

## Per-step latency (median / p95 / max ms)

**1 simultaneous patients**

| Step | Calls | Median | p95 | Max |
|---|---|---|---|---|
| session | 1 | 10 | 10 | 10 |
| consent | 1 | 15 | 15 | 15 |
| profile | 1 | 12 | 12 | 12 |
| start | 1 | 13 | 13 | 13 |
| answer | 5 | 8 | 13 | 13 |
| complete | 1 | 16 | 16 | 16 |

**5 simultaneous patients**

| Step | Calls | Median | p95 | Max |
|---|---|---|---|---|
| session | 5 | 29 | 62 | 62 |
| consent | 5 | 33 | 34 | 34 |
| profile | 5 | 28 | 58 | 58 |
| start | 5 | 52 | 57 | 57 |
| answer | 25 | 26 | 165 | 208 |
| complete | 5 | 168 | 279 | 279 |

**10 simultaneous patients**

| Step | Calls | Median | p95 | Max |
|---|---|---|---|---|
| session | 10 | 56 | 134 | 134 |
| consent | 10 | 87 | 293 | 293 |
| profile | 10 | 53 | 82 | 82 |
| start | 10 | 84 | 156 | 156 |
| answer | 50 | 44 | 94 | 100 |
| complete | 10 | 95 | 150 | 150 |

**25 simultaneous patients**

| Step | Calls | Median | p95 | Max |
|---|---|---|---|---|
| session | 25 | 144 | 1339 | 1414 |
| consent | 25 | 187 | 878 | 1012 |
| profile | 25 | 158 | 355 | 469 |
| start | 25 | 200 | 550 | 670 |
| answer | 125 | 97 | 211 | 934 |
| complete | 25 | 215 | 372 | 455 |

**50 simultaneous patients**

| Step | Calls | Median | p95 | Max |
|---|---|---|---|---|
| session | 50 | 288 | 1946 | 3648 |
| consent | 50 | 361 | 1380 | 1642 |
| profile | 50 | 275 | 1334 | 2296 |
| start | 50 | 359 | 1567 | 2275 |
| answer | 250 | 199 | 572 | 1695 |
| complete | 50 | 335 | 780 | 1175 |

**100 simultaneous patients**

| Step | Calls | Median | p95 | Max |
|---|---|---|---|---|
| session | 100 | 376 | 1951 | 4668 |
| consent | 100 | 733 | 2155 | 4990 |
| profile | 100 | 746 | 1413 | 2183 |
| start | 100 | 937 | 1801 | 3087 |
| answer | 500 | 677 | 1163 | 3112 |
| complete | 100 | 1324 | 2055 | 2644 |

