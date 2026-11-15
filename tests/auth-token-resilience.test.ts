// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "fs";
import path from "path";
import { api, getAuthHeaders, ALLOWED_REVIEW_QUEUE_STATUSES, ApiError } from "../app/lib/api";

let mockCurrentUser: any = null;
let mockAuthStateReady: (() => Promise<void>) | null = null;
let onAuthCallbacks: Array<(user: any) => void> = [];

vi.mock("../app/lib/firebase", () => ({
  isFirebaseEnabled: () => true,
  isFirebaseConfigured: () => true,
  getFirebaseAuth: () => ({
    get currentUser() {
      return mockCurrentUser;
    },
    authStateReady: () => {
      if (mockAuthStateReady) {
        return mockAuthStateReady();
      }
      return Promise.resolve();
    },
  }),
}));

vi.mock("firebase/auth", () => ({
  onAuthStateChanged: (_auth: any, callback: (user: any) => void) => {
    onAuthCallbacks.push(callback);
    return () => {
      onAuthCallbacks = onAuthCallbacks.filter((cb) => cb !== callback);
    };
  },
}));

describe("P0-6 & P1-7: Auth Token Resilience & Provider Review Queue Contract", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    mockCurrentUser = null;
    mockAuthStateReady = null;
    onAuthCallbacks = [];
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("waits for auth to be ready when currentUser is initially null and sends Bearer token", async () => {
    // Initially null, but becomes available via authStateReady
    mockAuthStateReady = async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
      mockCurrentUser = {
        getIdToken: vi.fn().mockResolvedValue("mock-bearer-token-123"),
      };
    };

    const headers = await getAuthHeaders("/api/provider/review-queue");
    expect(headers["Authorization"]).toBe("Bearer mock-bearer-token-123");
  });

  it("waits for onAuthStateChanged when currentUser is initially null and authStateReady does not immediately set user", async () => {
    // currentUser null, onAuthStateChanged fires after 40ms
    setTimeout(() => {
      mockCurrentUser = {
        getIdToken: vi.fn().mockResolvedValue("mock-async-token-456"),
      };
      onAuthCallbacks.forEach((cb) => cb(mockCurrentUser));
    }, 40);

    const headers = await getAuthHeaders("/api/provider/review-queue");
    expect(headers["Authorization"]).toBe("Bearer mock-async-token-456");
  });

  it("retries once with getIdToken(true) when getIdToken() throws on first call", async () => {
    const getIdTokenMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("Transient token error"))
      .mockResolvedValueOnce("force-refreshed-token-789");

    mockCurrentUser = {
      getIdToken: getIdTokenMock,
    };

    const headers = await getAuthHeaders("/api/provider/review-queue");
    expect(getIdTokenMock).toHaveBeenCalledTimes(2);
    expect(getIdTokenMock).toHaveBeenLastCalledWith(true);
    expect(headers["Authorization"]).toBe("Bearer force-refreshed-token-789");
  });

  it("never silently sends an authenticated endpoint without a token when currentUser remains null", async () => {
    mockCurrentUser = null;
    mockAuthStateReady = () => Promise.resolve();

    await expect(getAuthHeaders("/api/provider/review-queue")).rejects.toThrow(
      "Authentication required: no active user session"
    );
  });

  it("retries request once on 401 response with a force-refreshed token", async () => {
    const getIdTokenMock = vi
      .fn()
      .mockResolvedValueOnce("expired-token")
      .mockResolvedValueOnce("fresh-token");

    mockCurrentUser = {
      getIdToken: getIdTokenMock,
    };

    let callCount = 0;
    global.fetch = vi.fn().mockImplementation(async (_url, options) => {
      callCount++;
      const authHeader = options?.headers?.["Authorization"];
      if (callCount === 1) {
        expect(authHeader).toBe("Bearer expired-token");
        return new Response(JSON.stringify({ detail: "Invalid or expired token" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      }
      expect(authHeader).toBe("Bearer fresh-token");
      return new Response(JSON.stringify([{ checkin_id: "c1", patient_display: "Ali Khan" }]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const res = await api.getProviderReviewQueue("open");
    expect(callCount).toBe(2);
    expect(getIdTokenMock).toHaveBeenCalledWith(true);
    expect(res).toHaveLength(1);
    expect(res[0].checkin_id).toBe("c1");
  });

  it("contract test: every frontend review-queue status matches backend regex pattern in main.py", () => {
    // 1. Read pattern from backend-poc-technical/main.py
    const mainPyPath = path.resolve(__dirname, "../backend-poc-technical/main.py");
    const mainPyContent = fs.readFileSync(mainPyPath, "utf-8");

    // Match status Query pattern specifically in get_provider_review_queue_endpoint
    const endpointIndex = mainPyContent.indexOf("def get_provider_review_queue_endpoint");
    expect(endpointIndex).toBeGreaterThan(-1);
    const reviewQueueEndpointBlock = mainPyContent.slice(endpointIndex, endpointIndex + 500);
    const match = reviewQueueEndpointBlock.match(/pattern="(\^?\([^)]+\)\$?)"/);
    expect(match).not.toBeNull();
    const regexPattern = new RegExp(match![1]);

    // 2. Validate all allowed statuses defined in frontend
    expect(ALLOWED_REVIEW_QUEUE_STATUSES.length).toBeGreaterThan(0);
    ALLOWED_REVIEW_QUEUE_STATUSES.forEach((st) => {
      expect(st).toMatch(regexPattern);
    });

    // 3. Scan frontend components for getProviderReviewQueue calls
    const componentsDir = path.resolve(__dirname, "../app/components/provider");
    const files = fs.readdirSync(componentsDir).filter((f) => f.endsWith(".tsx") || f.endsWith(".ts"));

    files.forEach((file) => {
      const content = fs.readFileSync(path.join(componentsDir, file), "utf-8");
      // Find all api.getProviderReviewQueue("...") calls with string literals
      const callRegex = /getProviderReviewQueue\(\s*["']([^"']+)["']\s*\)/g;
      let m: RegExpExecArray | null;
      while ((m = callRegex.exec(content)) !== null) {
        const statusArg = m[1];
        expect(
          ALLOWED_REVIEW_QUEUE_STATUSES.includes(statusArg as any),
          `Found invalid review queue status argument "${statusArg}" in ${file}`
        ).toBe(true);
        expect(statusArg).toMatch(regexPattern);
      }
    });
  });
});
