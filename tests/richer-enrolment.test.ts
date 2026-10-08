import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, ApiError, ProfileUpdateRequest, ReviewDetailResponse } from "../app/lib/api";

describe("Stage 8 Part B: Richer Enrolment & Clinician BMI Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("updates profile with height, weight, diagnosis years, smoking status, and comorbidities", async () => {
    const mockProfileResponse = {
      user_id: "user-123",
      conditions: ["diabetes", "hypertension"],
      on_insulin_or_sulfonylurea: true,
      language: "en",
      date_of_birth: "1980-05-15",
      inclusion_confirmed_at: "2026-10-01T00:00:00Z",
      sex_at_birth: "female",
      pregnancy_status: "no",
      voice_enabled: true,
      height_cm: 175.5,
      weight_kg: 82.0,
      diagnosis_year_diabetes: 2015,
      diagnosis_year_hypertension: 2018,
      smoking_status: "former",
      comorbidities: {
        kidney_disease: false,
        heart_disease: true,
        stroke_or_tia: false,
        eye_problems: true,
        nerve_or_foot_problems: false,
      },
      consent_granted_at: "2026-10-01T00:00:00Z",
      consent_revoked_at: null,
      updated_at: "2026-10-01T00:00:00Z",
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockProfileResponse,
    });
    global.fetch = mockFetch;

    const payload: ProfileUpdateRequest = {
      conditions: ["diabetes", "hypertension"],
      on_insulin_or_sulfonylurea: true,
      height_cm: 175.5,
      weight_kg: 82.0,
      diagnosis_year_diabetes: 2015,
      diagnosis_year_hypertension: 2018,
      smoking_status: "former",
      voice_enabled: true,
      comorbidities: {
        heart_disease: true,
        eye_problems: true,
      },
    };

    const res = await api.updateProfile(payload);
    expect(res.height_cm).toBe(175.5);
    expect(res.weight_kg).toBe(82.0);
    expect(res.diagnosis_year_diabetes).toBe(2015);
    expect(res.diagnosis_year_hypertension).toBe(2018);
    expect(res.smoking_status).toBe("former");
    expect(res.voice_enabled).toBe(true);
    expect(res.comorbidities?.heart_disease).toBe(true);
    expect(res.comorbidities?.eye_problems).toBe(true);

    const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(callBody.height_cm).toBe(175.5);
    expect(callBody.weight_kg).toBe(82.0);
    expect(callBody.diagnosis_year_diabetes).toBe(2015);
  });

  it("fetches provider review detail containing patient_background with clinician-only BMI", async () => {
    const mockReviewDetail: ReviewDetailResponse = {
      checkin_id: "chk-001",
      patient_id: "pat-999",
      patient_display: "Tariq Mahmood",
      mode: "fhir",
      emergency: false,
      intakes: [],
      reconciliation: null,
      verification: null,
      requires_review: true,
      max_severity: "moderate",
      review_status: "pending",
      created_at: "2026-10-05T12:00:00Z",
      actions: [],
      patient_background: {
        height_cm: 180,
        weight_kg: 90,
        bmi: 27.8,
        smoking_status: "current",
        diagnosis_year_diabetes: 2012,
        diagnosis_year_hypertension: 2016,
        comorbidities: {
          kidney_disease: true,
          heart_disease: false,
        },
        disclaimer: "Self-reported background details provided by patient during enrolment. Not clinically verified.",
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockReviewDetail,
    });

    const detail = await api.getProviderReviewDetail("chk-001");
    expect(detail.patient_background).toBeDefined();
    expect(detail.patient_background?.bmi).toBe(27.8);
    expect(detail.patient_background?.disclaimer).toContain("Not clinically verified");
    expect(detail.patient_background?.smoking_status).toBe("current");
  });
});
