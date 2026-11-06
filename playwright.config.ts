import { defineConfig, devices } from "@playwright/test";
import path from "path";

export default defineConfig({
  testDir: path.resolve(__dirname, "tests-e2e"),
  testMatch: /.*\.playwright\.ts/,
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  expect: {
    timeout: 8000,
  },
  use: {
    baseURL: "http://localhost:3000",
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 720 },
      },
    },
  ],
  webServer: [
    {
      command: 'powershell -ExecutionPolicy Bypass -Command "backend-poc-technical\\.venv\\Scripts\\python.exe backend-poc-technical/init_local_db.py --reset; backend-poc-technical\\.venv\\Scripts\\python.exe -m uvicorn main:app --app-dir backend-poc-technical --host 127.0.0.1 --port 8000"',
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
      timeout: 60000,
      env: {
        RISK_ENABLED: "true",
        EXPLAIN_ENABLED: "true",
        OCR_ENABLED: "true",
        OCR_PROVIDER: "fake",
        DB_BACKEND: "sqlite",
      },
    },
    {
      command: "npx next dev -p 3000",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60000,
      env: {
        NEXT_PUBLIC_E2E_HOOKS: "1",
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000",
        NEXT_PUBLIC_RISK_ENABLED: "true",
        NEXT_PUBLIC_EXPLAIN_ENABLED: "true",
      },
    },
  ],
});

