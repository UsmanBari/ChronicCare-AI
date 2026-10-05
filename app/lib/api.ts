import { getFirebaseAuth, isFirebaseEnabled } from "./firebase";

export interface SessionResponse {
  user_id: string;
  email: string;
  role: string;
  display_name: string | null;
  status: string;
}

export interface UserResponse {
  user_id: string;
  email: string;
  role: string;
  display_name: string | null;
  status: string;
  created_at: string | null;
  last_login_at: string | null;
  mode: string | null;
}

export interface ProfileUpdateRequest {
  conditions: string[];
  on_insulin_or_sulfonylurea: boolean;
  language?: string;
}

export interface ProfileResponse {
  user_id: string;
  conditions: string[];
  on_insulin_or_sulfonylurea: boolean;
  language: string;
  consent_granted_at: string | null;
  consent_revoked_at: string | null;
  provider_notification_consent_at?: string | null;
  provider_notification_revoked_at?: string | null;
  updated_at: string | null;
}

export interface RecordConditionItem {
  name: string;
  basis: "clinician_diagnosed" | "self_reported" | "unsure" | string | null;
}

export interface RecordMedicationItem {
  id: string;
  name: string;
  dosage: string;
  status: "active" | "stopped" | string;
}

export interface RecordAllergyItem {
  id: string;
  substance: string;
  reaction?: string | null;
  confirmed: boolean;
}

export interface RecordObservationItem {
  id: string;
  observation_type: "glucose" | "blood_pressure_systolic" | "blood_pressure_diastolic" | "weight" | "hba1c" | string;
  value: number;
  unit: string;
  measured_at: string;
}

export interface PatientRecordResponse {
  mode: string;
  conditions: RecordConditionItem[];
  medications: RecordMedicationItem[];
  allergies: RecordAllergyItem[];
  baseline_observations: RecordObservationItem[];
}

export interface CreateMedicationRequest {
  name: string;
  dosage: string;
  status: "active" | "stopped";
}

export interface UpdateMedicationRequest {
  dosage?: string | null;
  status?: "active" | "stopped" | null;
}

export interface CreateAllergyRequest {
  substance: string;
  reaction?: string | null;
  confirmed: boolean;
}

export interface CreateObservationRequest {
  observation_type: string;
  value: number;
  measured_at?: string | null;
}

export interface SamplePatient {
  id: string;
  label: string;
  description: string;
}

export interface EHRSystemResponse {
  ehr_system_id: string;
  display_name: string;
  kind?: "simulated" | "public_sandbox" | "live_hospital" | string;
  description?: string;
  sample_patients?: SamplePatient[] | null;
  suggested_patient_ids?: string[] | null;
}

export interface EHRTestResponse {
  ok: boolean;
  latency_ms: number;
  kind: string;
  error_code?: string | null;
}

export interface EHRConnectionInfo {
  ehr_system_id: string;
  display_name: string;
  masked_patient_id: string;
  linked_at: string;
  last_verified_at: string | null;
}

export interface EHRConnectionResponse {
  mode: string;
  connection: EHRConnectionInfo | null;
  system_id?: string | null;
  kind?: string | null;
  record_source_label?: string | null;
  warning?: string | null;
  summary?: {
    recent_observations: number;
    active_medications: number;
  } | null;
  message?: string | null;
}

export interface CheckinStartResponse {
  checkin_id: string;
  question: string | null;
  mode: string;
  is_cold_start: boolean;
  step?: string | null;
  version?: number;
  record_source_label?: string | null;
}

export interface CheckinAnswerResponse {
  question: string | null;
  complete: boolean;
  emergency: boolean;
  emergency_reason: string | null;
  step?: string | null;
  version?: number;
  escalation_recorded?: boolean | null;
  phase?: string | null;
  triage?: Record<string, any> | null;
}

export interface CheckinCompleteResponse {
  emergency: boolean;
  intakes: Array<Record<string, any>>;
  reconciliation: Record<string, any> | null;
  verification: Record<string, any> | null;
  requires_review: boolean;
  max_severity: string | null;
  triage?: Record<string, any> | null;
  record_source_label?: string | null;
}

export interface UserCheckinSummaryResponse {
  checkin_id: string;
  mode: string;
  record_patient_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  emergency: boolean;
  requires_review: boolean;
  max_severity: string | null;
  review_status: string | null;
}

export interface UserCheckinDetailResponse {
  checkin_id: string;
  user_id: string;
  mode: string;
  record_patient_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  state: Record<string, any>;
  result: Record<string, any> | null;
}

export interface ReviewQueueItemResponse {
  checkin_id: string;
  patient_display: string;
  mode: string;
  created_at: string;
  max_severity: string | null;
  emergency: boolean;
  overdue: boolean;
  counts: Record<string, number>;
  trigger_category?: string | null;
  trigger_text?: string | null;
  trigger_reading?: Record<string, any> | string | null;
  escalated_at?: string | null;
}

export interface ReviewActionResponse {
  id: number;
  checkin_id: string;
  provider_user_id: string;
  action: string;
  note: string | null;
  ts: string;
}

export interface ReviewDetailResponse {
  checkin_id: string;
  patient_id: string;
  patient_display: string;
  mode: string;
  emergency: boolean;
  intakes: Array<Record<string, any>>;
  reconciliation: Record<string, any> | null;
  verification: Record<string, any> | null;
  requires_review: boolean;
  max_severity: string | null;
  review_status: string;
  created_at: string;
  actions: ReviewActionResponse[];
  trigger_category?: string | null;
  trigger_text?: string | null;
  trigger_reading?: Record<string, any> | string | null;
  escalated_at?: string | null;
}

export interface AuditLogRow {
  id: number;
  ts: string;
  actor_user_id: string | null;
  action: string;
  target: string | null;
  outcome: string;
  detail: Record<string, any>;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  data?: any;

  constructor(status: number, detail: string, data?: any) {
    super(`API Error ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
    this.data = data;
    this.name = "ApiError";
  }

  getFriendlyMessage(isUrdu: boolean): string {
    if (this.status === 401) {
      return isUrdu
        ? "آپ کا سیشن ختم ہو چکا ہے۔ براہ کرم دوبارہ لاگ ان کریں۔"
        : "Your session has expired. Please sign in again.";
    }
    if (this.status === 403) {
      return isUrdu
        ? "رسائی مسترد: آپ کے پاس اس کارروائی کی اجازت نہیں ہے۔"
        : "Access denied. You do not have permission for this action.";
    }
    if (this.status === 404) {
      return isUrdu
        ? "مطلوبہ ریکارڈ یا سروس موجود نہیں ہے۔"
        : "The requested resource or record was not found.";
    }
    if (this.status === 409) {
      return isUrdu
        ? "موجودہ ڈیٹا کے ساتھ تضاد پیش آیا ہے۔"
        : "A conflict occurred with existing data or state.";
    }
    if (this.status === 422) {
      return isUrdu
        ? "فراہم کردہ معلومات درست نہیں ہیں۔ براہ کرم دوبارہ چیک کریں۔"
        : "Invalid information provided. Please verify your input.";
    }
    if (this.status === 502 || this.status === 503 || this.status === 504 || this.status === 0) {
      return isUrdu
        ? "سرور اس وقت بیدار ہو رہا ہے یا مصروف ہے۔ براہ کرم انتظار کریں۔"
        : "The server is waking up or temporarily unavailable. Please wait a moment.";
    }
    return isUrdu
      ? `خرابی پیش آئی (${this.detail || "نامعلوم خرابی"})`
      : this.detail || "An unexpected error occurred. Please try again.";
  }
}

type WakingListener = (isWaking: boolean) => void;
const wakingListeners = new Set<WakingListener>();

export function subscribeServerWaking(listener: WakingListener): () => void {
  wakingListeners.add(listener);
  return () => {
    wakingListeners.delete(listener);
  };
}

function setServerWaking(isWaking: boolean) {
  wakingListeners.forEach((fn) => {
    try {
      fn(isWaking);
    } catch {
      // Ignore listener errors
    }
  });
}

function getBaseUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  return url.replace(/\/+$/, "");
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (isFirebaseEnabled()) {
    const auth = getFirebaseAuth();
    if (auth && auth.currentUser) {
      try {
        const token = await auth.currentUser.getIdToken();
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
      } catch {
        // Fallback without token if getIdToken fails
      }
    }
  }

  return headers;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  retriesLeft = 3
): Promise<T> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const defaultHeaders = await getAuthHeaders();

  const finalHeaders = {
    ...defaultHeaders,
    ...(options.headers as Record<string, string> | undefined),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers: finalHeaders,
    });

    // Detect waking / 502 / 503 / 504 server sleep states
    if ([502, 503, 504].includes(response.status) && retriesLeft > 0) {
      setServerWaking(true);
      await new Promise((resolve) => setTimeout(resolve, 3000));
      return request<T>(endpoint, options, retriesLeft - 1);
    }

    setServerWaking(false);

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      let data: any = null;
      try {
        const errJson = await response.json();
        data = errJson;
        if (errJson && errJson.detail) {
          detail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {
        // If response is not JSON
      }
      throw new ApiError(response.status, detail, data);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }

    // Network / fetch failures (e.g. backend sleeping or waking up)
    if (retriesLeft > 0) {
      setServerWaking(true);
      await new Promise((resolve) => setTimeout(resolve, 3000));
      return request<T>(endpoint, options, retriesLeft - 1);
    }

    setServerWaking(false);
    throw new ApiError(0, err?.message || "Network request failed");
  }
}

export const api = {
  // 1. Auth & Session
  authSession: async (): Promise<SessionResponse> => {
    return request<SessionResponse>("/api/auth/session", {
      method: "POST",
    });
  },

  getMe: async (): Promise<UserResponse> => {
    return request<UserResponse>("/api/me", {
      method: "GET",
    });
  },

  // 2. Profile & Consent
  getProfile: async (): Promise<ProfileResponse> => {
    return request<ProfileResponse>("/api/me/profile", {
      method: "GET",
    });
  },

  updateProfile: async (data: ProfileUpdateRequest): Promise<ProfileResponse> => {
    return request<ProfileResponse>("/api/me/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  setConsent: async (
    granted: boolean,
    provider_notification?: boolean
  ): Promise<ProfileResponse> => {
    return request<ProfileResponse>("/api/me/consent", {
      method: "POST",
      body: JSON.stringify({
        granted,
        ...(provider_notification !== undefined ? { provider_notification } : {}),
      }),
    });
  },

  setProviderNotificationConsent: async (
    granted: boolean
  ): Promise<ProfileResponse> => {
    return request<ProfileResponse>("/api/me/consent/provider-notification", {
      method: "POST",
      body: JSON.stringify({ granted }),
    });
  },

  // 2b. Patient Record Endpoints (Isolated Mode)
  getRecord: async (): Promise<PatientRecordResponse> => {
    return request<PatientRecordResponse>("/api/me/record", {
      method: "GET",
    });
  },

  updateConditionsBasis: async (
    basisMap: Record<string, string | null>
  ): Promise<{ status: string; conditions_basis: Record<string, string> }> => {
    return request<{ status: string; conditions_basis: Record<string, string> }>(
      "/api/me/record/conditions-basis",
      {
        method: "PUT",
        body: JSON.stringify(basisMap),
      }
    );
  },

  createRecordMedication: async (
    data: CreateMedicationRequest
  ): Promise<RecordMedicationItem> => {
    return request<RecordMedicationItem>("/api/me/record/medications", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateRecordMedication: async (
    med_id: string,
    data: UpdateMedicationRequest
  ): Promise<RecordMedicationItem> => {
    return request<RecordMedicationItem>(
      `/api/me/record/medications/${encodeURIComponent(med_id)}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      }
    );
  },

  deleteRecordMedication: async (med_id: string): Promise<{ status: string }> => {
    return request<{ status: string }>(
      `/api/me/record/medications/${encodeURIComponent(med_id)}`,
      {
        method: "DELETE",
      }
    );
  },

  createRecordAllergy: async (
    data: CreateAllergyRequest
  ): Promise<RecordAllergyItem> => {
    return request<RecordAllergyItem>("/api/me/record/allergies", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  deleteRecordAllergy: async (allergy_id: string): Promise<{ status: string }> => {
    return request<{ status: string }>(
      `/api/me/record/allergies/${encodeURIComponent(allergy_id)}`,
      {
        method: "DELETE",
      }
    );
  },

  createRecordObservation: async (
    data: CreateObservationRequest
  ): Promise<RecordObservationItem> => {
    return request<RecordObservationItem>("/api/me/record/observations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  deleteRecordObservation: async (obs_id: string): Promise<{ status: string }> => {
    return request<{ status: string }>(
      `/api/me/record/observations/${encodeURIComponent(obs_id)}`,
      {
        method: "DELETE",
      }
    );
  },

  // 3. EHR Connection
  getEHRSystems: async (): Promise<EHRSystemResponse[]> => {
    return request<EHRSystemResponse[]>("/api/ehr/systems", {
      method: "GET",
    });
  },

  testEHRConnection: async (ehr_system_id: string): Promise<EHRTestResponse> => {
    return request<EHRTestResponse>("/api/ehr/test", {
      method: "POST",
      body: JSON.stringify({ ehr_system_id }),
    });
  },

  connectEHR: async (
    ehr_system_id: string,
    external_patient_id: string
  ): Promise<EHRConnectionResponse> => {
    return request<EHRConnectionResponse>("/api/ehr/connect", {
      method: "POST",
      body: JSON.stringify({ ehr_system_id, external_patient_id }),
    });
  },

  getEHRConnection: async (): Promise<EHRConnectionResponse> => {
    return request<EHRConnectionResponse>("/api/ehr/connection", {
      method: "GET",
    });
  },

  disconnectEHR: async (): Promise<EHRConnectionResponse> => {
    return request<EHRConnectionResponse>("/api/ehr/connection", {
      method: "DELETE",
    });
  },

  // 4. Check-in Pipeline
  startCheckin: async (): Promise<CheckinStartResponse> => {
    return request<CheckinStartResponse>("/api/checkins/start", {
      method: "POST",
    });
  },

  answerCheckin: async (
    checkin_id: string,
    answer: string,
    step?: string | null
  ): Promise<CheckinAnswerResponse> => {
    return request<CheckinAnswerResponse>(`/api/checkins/${encodeURIComponent(checkin_id)}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer, step: step !== undefined ? step : undefined }),
    });
  },

  completeCheckin: async (
    checkin_id: string
  ): Promise<CheckinCompleteResponse> => {
    return request<CheckinCompleteResponse>(`/api/checkins/${encodeURIComponent(checkin_id)}/complete`, {
      method: "POST",
    });
  },

  getUserCheckins: async (): Promise<UserCheckinSummaryResponse[]> => {
    return request<UserCheckinSummaryResponse[]>("/api/checkins", {
      method: "GET",
    });
  },

  getUserCheckinDetail: async (
    checkin_id: string
  ): Promise<UserCheckinDetailResponse> => {
    return request<UserCheckinDetailResponse>(`/api/checkins/${encodeURIComponent(checkin_id)}`, {
      method: "GET",
    });
  },

  // 5. Provider Review
  getProviderReviewQueue: async (
    status?: string
  ): Promise<ReviewQueueItemResponse[]> => {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return request<ReviewQueueItemResponse[]>(`/api/provider/review-queue${query}`, {
      method: "GET",
    });
  },

  getProviderReviewDetail: async (
    checkin_id: string
  ): Promise<ReviewDetailResponse> => {
    return request<ReviewDetailResponse>(`/api/provider/review/${encodeURIComponent(checkin_id)}`, {
      method: "GET",
    });
  },

  postProviderReviewAction: async (
    checkin_id: string,
    action: "acknowledge" | "resolve" | "escalate",
    note?: string
  ): Promise<ReviewDetailResponse> => {
    return request<ReviewDetailResponse>(
      `/api/provider/review/${encodeURIComponent(checkin_id)}/action`,
      {
        method: "POST",
        body: JSON.stringify({ action, note: note || undefined }),
      }
    );
  },

  // 6. Admin
  getAdminAudit: async (): Promise<AuditLogRow[]> => {
    return request<AuditLogRow[]>("/api/admin/audit", {
      method: "GET",
    });
  },

  updateUserRole: async (
    user_id: string,
    role: string
  ): Promise<UserResponse> => {
    return request<UserResponse>(`/api/admin/users/${encodeURIComponent(user_id)}/role`, {
      method: "POST",
      body: JSON.stringify({ role }),
    });
  },
};
