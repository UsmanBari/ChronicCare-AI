#!/usr/bin/env python3
"""
Measurement script for OCR memory footprint.
Runs fresh process, imports main, executes N=5 uploads of rx_photo_01.jpg through TestClient.
Samples resident set size (RSS) every 50 ms using psutil.
Outputs:
- Idle RSS (MB)
- After first call RSS (MB)
- Steady after 5 calls RSS (MB)
- Peak RSS (MB)
"""

from __future__ import annotations

import os
import sys
import time
import shutil
import tempfile
import threading
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend-poc-technical"
SAMPLE_PHOTO = BACKEND_DIR / "ocr_spike" / "samples" / "photos" / "rx_photo_01.jpg"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Setup temporary SQLite database directory to protect backend-poc-technical/local_store.db
TEMP_DIR = tempfile.mkdtemp(prefix="chroniccare_ocr_mem_")
TEMP_DB_PATH = Path(TEMP_DIR) / "test_local_store.db"
REAL_DB_PATH = BACKEND_DIR / "local_store.db"
if REAL_DB_PATH.exists():
    shutil.copy2(REAL_DB_PATH, TEMP_DB_PATH)

# Configure environment for real RapidOCR execution
os.environ["OCR_ENABLED"] = "true"
os.environ["OCR_PROVIDER"] = "rapidocr"
os.environ["DB_BACKEND"] = "sqlite"
os.environ["LOCAL_DB_PATH"] = str(TEMP_DB_PATH)
os.environ["FIREBASE_PROJECT_ID"] = "test-chroniccare-ai"
os.environ["DEMO_ROLE_MAP"] = "patient@demo.com:patient"

import psutil

# Background RSS sampler
class MemorySampler:
    def __init__(self, interval_sec: float = 0.05):
        self.interval = interval_sec
        self.process = psutil.Process()
        self.peak_rss = self.process.memory_info().rss
        self._running = False
        self._thread = None

    def _sample(self):
        while self._running:
            try:
                total_rss = self.process.memory_info().rss
                for child in self.process.children(recursive=True):
                    try:
                        total_rss += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                if total_rss > self.peak_rss:
                    self.peak_rss = total_rss
            except Exception:
                pass
            time.sleep(self.interval)

    def start(self):
        self._running = True
        self.peak_rss = self.process.memory_info().rss
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        # Final check
        rss = self.process.memory_info().rss
        if rss > self.peak_rss:
            self.peak_rss = rss

def main():
    if not SAMPLE_PHOTO.exists():
        print(f"ERROR: Sample photo not found at {SAMPLE_PHOTO}", file=sys.stderr)
        sys.exit(1)

    with open(SAMPLE_PHOTO, "rb") as f:
        photo_bytes = f.read()

    # Step 1: Import main and initialize
    import main as backend_main
    from fastapi.testclient import TestClient
    from main import app
    from data_sources import app_store

    client = TestClient(app)

    # Use FastAPI dependency override for get_current_user
    user_id = "mem-test-patient"
    app_store.set_patient_consent(user_id=user_id, granted=True)
    backend_main.app.dependency_overrides[backend_main.get_current_user] = lambda: {
        "user_id": user_id,
        "sub": user_id,
        "email": "patient@demo.com",
        "role": "patient",
        "status": "active",
    }
    headers = {"Authorization": "Bearer mock-token"}

    process = psutil.Process()
    time.sleep(0.1)
    idle_rss = process.memory_info().rss

    sampler = MemorySampler(interval_sec=0.05)
    sampler.start()

    # Call 1
    t0 = time.time()
    resp1 = client.post(
        "/api/me/record/uploads",
        headers=headers,
        files={"file": ("rx_photo_01.jpg", photo_bytes, "image/jpeg")},
    )
    lat1 = time.time() - t0
    if resp1.status_code != 200:
        print(f"ERROR: Call 1 failed with {resp1.status_code}: {resp1.text}", file=sys.stderr)
        sys.exit(1)

    time.sleep(0.1)
    after_first_rss = process.memory_info().rss

    # Calls 2 through 5
    latencies = [lat1]
    for i in range(2, 6):
        t_start = time.time()
        resp = client.post(
            "/api/me/record/uploads",
            headers=headers,
            files={"file": (f"rx_photo_01_run{i}.jpg", photo_bytes, "image/jpeg")},
        )
        lat = time.time() - t_start
        latencies.append(lat)
        if resp.status_code != 200:
            print(f"ERROR: Call {i} failed with {resp.status_code}: {resp.text}", file=sys.stderr)
            sys.exit(1)
        time.sleep(0.05)

    steady_rss = process.memory_info().rss
    sampler.stop()
    peak_rss = sampler.peak_rss

    to_mb = lambda b: round(b / (1024 * 1024), 2)
    mean_lat = round(sum(latencies) / len(latencies), 3)

    print("--------------------------------------------------")
    print("OCR MEMORY & LATENCY MEASUREMENT REPORT")
    print(f"Sample: {SAMPLE_PHOTO.name} ({len(photo_bytes)} bytes)")
    print(f"Idle RSS:                {to_mb(idle_rss):.2f} MB")
    print(f"After First Call RSS:    {to_mb(after_first_rss):.2f} MB")
    print(f"Steady After 5 Calls RSS:{to_mb(steady_rss):.2f} MB")
    print(f"Peak RSS:                {to_mb(peak_rss):.2f} MB")
    print(f"Call Latencies (s):      {[round(l, 3) for l in latencies]}")
    print(f"Mean Latency:            {mean_lat:.3f} s")
    print("--------------------------------------------------")

if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
