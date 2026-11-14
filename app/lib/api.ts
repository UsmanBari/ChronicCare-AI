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

export interface ComorbiditiesMap {
  kidney_disease?: boolean | null;
  heart_disease?: boolean | null;
  stroke_or_tia?: boolean | null;
  eye_problems?: boolean | null;
  nerve_or_foot_problems?: boolean | null;
}

export interface ProfileUpdateRequest {
  conditions?: string[];
  on_insulin_or_sulfonylurea?: boolean;
  language?: string;
  date_of_birth?: string | null;
  inclusion_confirmed?: boolean | null;
  sex_at_birth?: "female" | "male" | "prefer_not_to_say" | string | null;
  pregnancy_status?: "no" | "yes" | "not_sure" | "not_applicable" | string | null;
  voice_enabled?: boolean | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  waist_cm?: number | null;
  diagnosis_year_diabetes?: number | null;
  diagnosis_year_hypertension?: number | null;
  smoking_status?: "never" | "former" | "current" | "prefer_not_to_say" | string | null;
  comorbidities?: ComorbiditiesMap | null;
}

export interface ProfileResponse {
  user_id: string;
  email?: string | null;
  display_name?: string | null;
  role?: string | null;
  conditions?: string[];
  on_insulin_or_sulfonylurea?: boolean;
  language?: string;
  date_of_birth?: string | null;
  inclusion_confirmed_at?: string | null;
  sex_at_birth?: string | null;
  pregnancy_status?: string | null;
  voice_enabled?: boolean | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  waist_cm?: number | null;
  diagnosis_year_diabetes?: number | null;
  diagnosis_year_hypertension?: number | null;
  smoking_status?: string | null;
  comorbidities?: Record<string, boolean> | null;
  consent_granted_at?: string | null;
  consent_revoked_at?: string | null;
  provider_notification_consent_at?: string | null;
  provider_notification_revoked_at?: string | null;
  updated_at?: string | null;
}

export interface PatientBackgroundResponse {
  height_cm?: number | null;
  weight_kg?: number | null;
  waist_cm?: number | null;
  bmi?: number | null;
  smoking_status?: string | null;
  diagnosis_year_diabetes?: number | null;
  diagnosis_year_hypertension?: number | null;
  comorbidities?: Record<string, boolean> | null;
  disclaimer?: string | null;
}

export interface VoiceTranscribeResponse {
  text: string;
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
  origin?: string | null;
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
  origin?: string | null;
}

export interface DoctorOnRecord {
  name: string;
  identifier?: string | null;
  source: "ehr_general_practitioner" | "ehr_encounter";
  as_of?: string | null;
}

export interface PatientRecordResponse {
  mode?: string;
  ocr_enabled?: boolean;
  conditions: RecordConditionItem[];
  medications: RecordMedicationItem[];
  allergies: RecordAllergyItem[];
  baseline_observations: RecordObservationItem[];
}

export interface OcrExtractedObservation {
  id?: string;
  type: string;
  value: number;
  unit: string;
  date?: string | null;
  evidence?: string | null;
  confidence?: string | null;
}

export interface OcrExtractedMedication {
  id?: string;
  name: string;
  dosage: string;
  status: string;
  evidence?: string | null;
  confidence?: string | null;
  dose?: string | null;
  frequency?: string | null;
}

export interface OcrExtractedAllergy {
  id?: string;
  substance: string;
  reaction?: string | null;
  severity?: string | null;
  status?: string | null;
  evidence?: string | null;
}

export interface OcrExtractedFields {
  observations: OcrExtractedObservation[];
  medications: OcrExtractedMedication[];
  allergies: OcrExtractedAllergy[];
  raw_lines?: string[];
  has_urdu?: boolean;
}

export interface OcrUploadResponse {
  upload_id: string;
  expires_in_seconds: number;
  extracted: OcrExtractedFields;
}

export interface ConfirmOcrItem {
  id?: string;
  type?: string;
  name?: string;
  substance?: string;
  dosage?: string;
  value?: number;
  unit?: string;
  reaction?: string | null;
  severity?: string | null;
  status?: string | null;
  date?: string | null;
  evidence?: string | null;
}

export interface ConfirmOcrUploadResponse {
  status: string;
  saved_count: number;
  saved_items: Array<{
    type: string;
    id: string;
    origin: string;
  }>;
  skipped_count: number;
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

export interface EHRAllergyItem {
  substance: string;
  criticality: string;
  verification_status: string;
  origin: "ehr";
  trust: "high";
}

export interface EHRMedicationItem {
  name: string;
  dosage?: string | null;
  status?: string;
  origin?: string;
  trust?: string;
}

export interface EHRConnectionResponse {
  mode: string;
  connection?: EHRConnectionInfo | null;
  system_id?: string | null;
  system_name?: string | null;
  sandbox_id?: string | null;
  patient_id?: string | null;
  display_name?: string | null;
  status?: string | null;
  last_sync?: string | null;
  kind?: string | null;
  record_source_label?: string | null;
  warning?: string | null;
  summary?: {
    recent_observations: number;
    active_medications: number;
  } | null;
  message?: string | null;
  doctor_on_record?: DoctorOnRecord | null;
  ehr_allergies?: EHRAllergyItem[];
  ehr_medications?: EHRMedicationItem[];
}

export interface OptionItem {
  value: string;
  label: string;
}

export interface CheckinStartResponse {
  checkin_id: string;
  question: string | null;
  mode: string;
  is_cold_start: boolean;
  step?: string | null;
  version?: number;
  record_source_label?: string | null;
  why_text?: string | null;
  options?: string[] | null;
  option_items?: OptionItem[] | null;
  system_note?: string | null;
  progress_hint?: string | null;
  language?: string | null;
  can_skip?: boolean | null;
  can_say_unknown?: boolean | null;
  engine?: string | null;
  safety_note?: string | null;
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
  why_text?: string | null;
  options?: string[] | null;
  option_items?: OptionItem[] | null;
  system_note?: string | null;
  progress_hint?: string | null;
  language?: string | null;
  can_skip?: boolean | null;
  can_say_unknown?: boolean | null;
  engine?: string | null;
  safety_note?: string | null;
}

export interface PatientExplanationSentence {
  text: string;
  cites?: string[];
}

export interface PatientExplanationSource {
  chunk_id: string;
  title: string;
  edition?: string | null;
  section_path?: string | null;
  page_start?: number | null;
  full_citation?: string | null;
  doi?: string | null;
}

export interface PatientExplanation {
  status?: string;
  sentences?: PatientExplanationSentence[];
  sources?: PatientExplanationSource[];
}

export interface AdminConfigItem {
  name: string;
  set: boolean;
}

export interface AdminConfigStatusResponse {
  settings: AdminConfigItem[];
  flags?: Record<string, boolean | string | number>;
  keys_and_models?: Record<string, string>;
  explainer_metrics?: {
    tokens_used_today?: number;
    tokens_used_by_provider?: Record<string, number>;
    cap?: number;
    caps?: Record<string, number>;
    breaker_state?: string;
    breaker_states?: Record<string, string>;
    cache_size?: number;
    cache_hits?: number;
    cache_misses?: number;
    llm_calls?: number;
    llm_calls_by_provider?: Record<string, number>;
    template_fallbacks_by_reason?: Record<string, number>;
    queue_length?: number;
    mode?: string;
    [key: string]: any;
  };
}

export interface VoiceStatusResponse {
  tts_enabled: boolean;
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
  safety_note?: string | null;
  explanation?: PatientExplanation | null;
  triage_colour?: string | null;
  triage_level?: string | null;
  risk_patient?: Array<{ model_key: string; band: string; message_key: string }> | null;
  appointment?: Appointment | null;
  provider_decision?: string | null;
  provider_level?: string | null;
  provider_reason?: string | null;
  patient_message?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
}

export interface Appointment {
  id: string;
  patient_id: string;
  checkin_id: string;
  provider_id: string;
  specialty: 'endocrinology' | 'cardiology_im' | 'internal_medicine' | 'general' | string;
  urgency: 'routine' | 'urgent';
  mode: 'in_person' | 'telehealth';
  status: 'offered' | 'booked' | 'cancelled' | 'attended';
  slot_date?: string | null;
  slot?: string | null;
  reason?: string | null;
  created_at: string;
  acknowledged_at?: string | null;
  admin_flagged_at?: string | null;
  escalation_state?: 'pending' | 're_notify' | 'admin_flag' | 'acknowledged' | 'none';
}

export interface ProviderDirectoryEntry {
  id: string;
  display_name: string;
  name?: string;
  clinic?: string;
  specialty: string;
  available: boolean;
  is_available?: boolean;
  created_at: string;
}

export interface InAppNotification {
  id: string;
  user_id: string;
  role: string;
  type: 'urgent_checkin' | 'escalation_renotify' | 'escalation_admin_flag' | 'daily_reminder' | string;
  title: string;
  body: string;
  reference_id?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: InAppNotification[];
  unread_count: number;
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
  triage_level?: string | null;
  triage_colour?: string | null;
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
  triage_level?: string | null;
  triage_colour?: string | null;
  risk_patient?: Array<{ model_key: string; band: string; message_key: string }> | null;
  provider_decision?: string | null;
  provider_level?: string | null;
  provider_reason?: string | null;
  patient_message?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
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
  triage_level?: string | null;
  triage_colour?: string | null;
}

export interface ReviewActionResponse {
  id: number;
  checkin_id: string;
  provider_user_id: string;
  action: string;
  note: string | null;
  ts: string;
  system_level?: string | null;
  provider_level?: string | null;
  reason?: string | null;
  patient_message?: string | null;
}

export interface TrendValue {
  value: number;
  at: string;
}

export interface TrendSeries {
  direction: "rising" | "falling" | "stable" | "not_enough_history";
  n: number;
  window_days: number;
  few_readings: boolean;
  first_at?: string | null;
  last_at?: string | null;
  median_earlier?: number | null;
  median_recent?: number | null;
  change?: number | null;
  slope_per_week?: number | null;
  values: TrendValue[];
  contexts_seen?: string[];
  mixed_contexts?: boolean;
}

export interface TrendsResponse {
  generated_at: string;
  advisory: boolean;
  window_days: number;
  excluded_count: number;
  trends: Record<string, TrendSeries>;
}

export interface RiskReason {
  feature: string;
  weight?: number;
  contribution?: number;
  label: string | Record<string, string>;
}

export interface RiskAssessmentResponse {
  model_name?: string;
  model_version?: string;
  model?: string;
  version?: string;
  disease?: string;
  status: "ok" | "not_enough_information" | "error";
  band?: "low" | "moderate" | "medium" | "high" | null;
  probability?: number | null;
  label_text?: Record<string, string> | null;
  reasons?: RiskReason[] | null;
  top_reasons?: RiskReason[] | null;
  caveats?: string[] | null;
  missing?: string[] | null;
  error?: string | null;
  audience?: string;
}

export interface CheckinRiskResponse {
  status: "ok" | "not_enough_information" | "error" | string;
  disease?: string;
  model_name?: string;
  model_version?: string;
  model?: string;
  version?: string;
  probability?: number | null;
  band?: "low" | "moderate" | "medium" | "high" | null;
  reasons?: RiskReason[] | null;
  top_reasons?: RiskReason[] | null;
  advisory?: boolean;
  audience?: string;
  label_text?: Record<string, string> | null;
  caveats?: string[] | null;
  raised?: boolean;
  missing?: string[] | null;
  error?: string | null;
}

export interface ProviderExplanationResponse {
  sentences?: PatientExplanationSentence[];
  sources?: PatientExplanationSource[];
  language?: string;
  mode?: "llm" | "cache" | "template" | string;
  reason?: string | null;
  rejected_reasons?: string[];
  version?: string;
  status?: string;
}

export interface TraceStepItem {
  node: string;
  started_at: string;
  summary: string;
  duration_ms?: number;
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
  patient_background?: PatientBackgroundResponse | null;
  trends?: TrendsResponse | null;
  risk?: RiskAssessmentResponse | null;
  checkin_risk?: CheckinRiskResponse | null;
  checkin_risk_results?: CheckinRiskResponse[] | null;
  explanation?: ProviderExplanationResponse | null;
  trace?: TraceStepItem[] | null;
  recent_record_edits?: RecordEditItem[] | null;
  danger_wordgroups?: string[] | null;
  triage_level?: string | null;
  triage_colour?: string | null;
  raised_by?: Array<{ source: string; detail: string; [key: string]: any }> | null;
  provider_decision?: string | null;
  provider_level?: string | null;
  provider_reason?: string | null;
  patient_message?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
}

export interface SoapNoteResponse {
  checkin_id: string;
  patient_id?: string;
  generated_at: string;
  subjective: string[];
  objective: string[];
  assessment: string[];
  plan: string[];
  data_sources: string[];
  plain_text: string;
}
export interface RecordEditItem {
  edit_id: string;
  id?: string;
  user_id?: string;
  record_type: string;
  record_id: string;
  field: string;
  old_value: any;
  new_value: any;
  origin: string;
  changed_by_user_id: string;
  changed_by_role?: string | null;
  changed_at: string;
  reason?: string | null;
}

export interface RecordHistoryResponse {
  edits: RecordEditItem[];
  count: number;
}

export interface ImportPreviewItem {
  name?: string;
  dosage?: string;
  status?: string;
  type?: string;
  observation_type?: string;
  value?: number;
  unit?: string;
  measured_at?: string;
  substance?: string;
  reaction?: string | null;
  confirmed?: boolean;
  condition?: string;
  basis?: string;
  will_import: boolean;
  reason?: string | null;
}

export interface RecordImportResponse {
  status?: string;
  dry_run: boolean;
  imported?: number;
  duplicates?: number;
  invalid?: number;
  counts?: { to_add: number; duplicates: number; invalid: number };
  imported_counts?: { medications: number; observations: number; allergies: number };
  duplicate_counts?: { medications: number; observations: number; allergies: number };
  preview?: {
    medications: ImportPreviewItem[];
    observations: ImportPreviewItem[];
    allergies: ImportPreviewItem[];
    conditions_basis: ImportPreviewItem[];
  };
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
    if (this.status >= 500) {
      return isUrdu
        ? "سرور میں تکنیکی مسئلہ پیش آیا ہے۔ براہ کرم کچھ دیر بعد دوبارہ کوشش کریں۔"
        : "A server error occurred. Please try again in a moment.";
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

let activeSlowRequestsCount = 0;

export function resetServerWakingState() {
  activeSlowRequestsCount = 0;
  setServerWaking(false);
}

function markSlowRequestStarted() {
  activeSlowRequestsCount++;
  setServerWaking(true);
}

function markSlowRequestEnded() {
  if (activeSlowRequestsCount > 0) {
    activeSlowRequestsCount--;
  }
  if (activeSlowRequestsCount === 0) {
    setServerWaking(false);
  }
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

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export function subscribeUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}

export function notifyUnauthorized() {
  unauthorizedListeners.forEach((fn) => {
    try {
      fn();
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

  const finalHeaders: Record<string, string> = {
    ...defaultHeaders,
    ...(options.headers as Record<string, string> | undefined),
  };

  if (typeof FormData !== "undefined" && options.body instanceof FormData) {
    delete finalHeaders["Content-Type"];
  }

  const controller = new AbortController();
  const abortTimeout = setTimeout(() => {
    controller.abort();
  }, 65000);

  // If request takes longer than ~4s, show cold-start / server waking banner
  let didMarkSlow = false;
  const slowTimer = setTimeout(() => {
    didMarkSlow = true;
    markSlowRequestStarted();
  }, 4000);

  try {
    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers: finalHeaders,
        signal: options.signal || controller.signal,
      });
    } catch (fetchErr: any) {
      // Network / timeout failure on fetch (e.g. backend sleeping or connection drop)
      if (retriesLeft > 0) {
        if (!didMarkSlow) {
          didMarkSlow = true;
          markSlowRequestStarted();
        }
        await new Promise((resolve) => setTimeout(resolve, 3000));
        return await request<T>(endpoint, options, retriesLeft - 1);
      }
      const isTimeout = fetchErr?.name === "AbortError";
      const status = isTimeout ? 504 : 0;
      const message = isTimeout
        ? "Server request timed out. Please try again."
        : (fetchErr?.message || "Network request failed");
      throw new ApiError(status, message);
    }

    // Detect waking / 502 / 503 / 504 server sleep states
    if ([502, 503, 504].includes(response.status) && retriesLeft > 0) {
      if (!didMarkSlow) {
        didMarkSlow = true;
        markSlowRequestStarted();
      }
      await new Promise((resolve) => setTimeout(resolve, 3000));
      return await request<T>(endpoint, options, retriesLeft - 1);
    }

    if (!response.ok) {
      if (response.status === 401) {
        notifyUnauthorized();
      }
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
  } finally {
    clearTimeout(abortTimeout);
    clearTimeout(slowTimer);
    if (didMarkSlow) {
      markSlowRequestEnded();
      didMarkSlow = false;
    }
  }
}

async function requestBlob(
  endpoint: string,
  options: RequestInit = {}
): Promise<Blob> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const defaultHeaders = await getAuthHeaders();
  delete defaultHeaders["Content-Type"];

  const finalHeaders: Record<string, string> = {
    ...defaultHeaders,
    ...(options.headers as Record<string, string> | undefined),
  };

  const response = await fetch(url, {
    ...options,
    headers: finalHeaders,
  });

  if (!response.ok) {
    if (response.status === 401) {
      notifyUnauthorized();
    }
    let detail = `HTTP ${response.status}`;
    let data: any = null;
    try {
      const errJson = await response.json();
      data = errJson;
      if (errJson && errJson.detail) {
        detail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // response is not JSON
    }
    throw new ApiError(response.status, detail, data);
  }

  return await response.blob();
}

const inFlightCompleteRequests = new Map<string, Promise<CheckinCompleteResponse>>();

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

  uploadOcrImage: async (file: File): Promise<OcrUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    return request<OcrUploadResponse>("/api/me/record/uploads", {
      method: "POST",
      body: formData,
    });
  },

  confirmOcrUpload: async (
    uploadId: string,
    confirmedItems: ConfirmOcrItem[]
  ): Promise<ConfirmOcrUploadResponse> => {
    return request<ConfirmOcrUploadResponse>(`/api/me/record/uploads/${uploadId}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmed_items: confirmedItems }),
    });
  },

  cancelOcrUpload: async (uploadId: string): Promise<{ status: string }> => {
    return request<{ status: string }>(`/api/me/record/uploads/${uploadId}`, {
      method: "DELETE",
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
    external_patient_id: string,
    confirm_identity_mismatch: boolean = false
  ): Promise<EHRConnectionResponse> => {
    return request<EHRConnectionResponse>("/api/ehr/connect", {
      method: "POST",
      body: JSON.stringify({ ehr_system_id, external_patient_id, confirm_identity_mismatch }),
    });
  },

  getEHRConnection: async (includeDetails: boolean = false): Promise<EHRConnectionResponse> => {
    const query = includeDetails ? "?include_details=true" : "";
    return request<EHRConnectionResponse>(`/api/ehr/connection${query}`, {
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
    const existing = inFlightCompleteRequests.get(checkin_id);
    if (existing) {
      return existing;
    }
    const flight = request<CheckinCompleteResponse>(
      `/api/checkins/${encodeURIComponent(checkin_id)}/complete`,
      {
        method: "POST",
      }
    ).finally(() => {
      inFlightCompleteRequests.delete(checkin_id);
    });
    inFlightCompleteRequests.set(checkin_id, flight);
    return flight;
  },

  getCheckinExplanation: async (
    checkin_id: string
  ): Promise<PatientExplanation> => {
    return request<PatientExplanation>(
      `/api/checkins/${encodeURIComponent(checkin_id)}/explanation`,
      {
        method: "GET",
      }
    );
  },

  getCheckinSpeech: async (
    checkin_id: string
  ): Promise<Blob> => {
    return requestBlob(
      `/api/checkins/${encodeURIComponent(checkin_id)}/speech`,
      {
        method: "POST",
      }
    );
  },

  getEmergencySpeech: async (
    lang?: string
  ): Promise<Blob> => {
    const query = lang ? `?lang=${encodeURIComponent(lang)}` : "";
    return requestBlob(
      `/api/emergency/speech${query}`,
      {
        method: "POST",
      }
    );
  },

  getVoiceStatus: async (): Promise<VoiceStatusResponse> => {
    return request<VoiceStatusResponse>("/api/voice/status", {
      method: "GET",
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

  getMyTrends: async (days = 30): Promise<TrendsResponse> => {
    return request<TrendsResponse>(`/api/me/trends?days=${encodeURIComponent(days)}`, {
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

  getProviderSoapNote: async (
    checkin_id: string
  ): Promise<SoapNoteResponse> => {
    return request<SoapNoteResponse>(`/api/provider/review/${encodeURIComponent(checkin_id)}/soap`, {
      method: "GET",
    });
  },

  postProviderReviewAction: async (
    checkin_id: string,
    actionOrPayload:
      | "acknowledge"
      | "resolve"
      | "escalate"
      | "approve"
      | "adjust"
      | {
          action: "acknowledge" | "resolve" | "escalate" | "approve" | "adjust";
          note?: string;
          adjusted_level?: "routine" | "review" | "urgent";
          reason?: string;
          patient_message?: string;
        },
    note?: string,
    extra?: {
      adjusted_level?: "routine" | "review" | "urgent";
      reason?: string;
      patient_message?: string;
    }
  ): Promise<ReviewDetailResponse> => {
    let body: any;
    if (typeof actionOrPayload === "object") {
      body = actionOrPayload;
    } else {
      body = {
        action: actionOrPayload,
        note: note || undefined,
        ...(extra || {}),
      };
    }
    return request<ReviewDetailResponse>(
      `/api/provider/review/${encodeURIComponent(checkin_id)}/action`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    );
  },

  // 6. Admin
  getAdminConfigStatus: async (): Promise<AdminConfigStatusResponse> => {
    return request<AdminConfigStatusResponse>("/api/admin/config-status", {
      method: "GET",
    });
  },

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

  // 7. Voice Transcription
  transcribeVoice: async (
    file: Blob | File,
    _filename: string = "audio.webm"
  ): Promise<VoiceTranscribeResponse> => {
    const contentType = file.type || "audio/webm";
    return request<VoiceTranscribeResponse>("/api/voice/transcribe", {
      method: "POST",
      headers: {
        "Content-Type": contentType,
      },
      body: file,
    });
  },

  // 8. Record Edit History, Export, and Import
  getRecordHistory: async (recordType?: string, recordId?: string, limit: number = 50): Promise<RecordHistoryResponse> => {
    const params = new URLSearchParams();
    if (recordType) params.set("record_type", recordType);
    if (recordId) params.set("record_id", recordId);
    params.set("limit", limit.toString());
    return request<RecordHistoryResponse>(`/api/me/record/history?${params.toString()}`);
  },

  exportRecord: async (format: "json" | "fhir" = "json"): Promise<Blob> => {
    const baseUrl = getBaseUrl();
    const headers = await getAuthHeaders();
    delete headers["Content-Type"];
    const res = await fetch(`${baseUrl}/api/me/record/export?format=${format}`, {
      headers,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Export failed" }));
      throw new ApiError(res.status, err.detail || "Export failed");
    }
    return res.blob();
  },

  importRecord: async (payload: any, isFhir: boolean = false, dryRun: boolean = true): Promise<RecordImportResponse> => {
    return request<RecordImportResponse>(`/api/me/record/import?dry_run=${dryRun}`, {
      method: "POST",
      headers: isFhir ? { "Content-Type": "application/fhir+json" } : { "Content-Type": "application/json" },
      body: typeof payload === "string" ? payload : JSON.stringify(payload),
    });
  },

  // 9. Appointments & Provider Directory (PR D / Proposal Sec 15)
  getMyAppointments: async (): Promise<{ appointments: Appointment[] }> => {
    return request<{ appointments: Appointment[] }>("/api/me/appointments");
  },

  bookAppointment: async (appointmentId: string, slotDate: string, mode: string = "telehealth"): Promise<Appointment> => {
    return request<Appointment>(`/api/me/appointments/${encodeURIComponent(appointmentId)}/book`, {
      method: "POST",
      body: JSON.stringify({ slot_date: slotDate, mode }),
    });
  },

  cancelAppointment: async (appointmentId: string): Promise<Appointment> => {
    return request<Appointment>(`/api/me/appointments/${encodeURIComponent(appointmentId)}/cancel`, {
      method: "POST",
    });
  },

  getProviderAppointments: async (): Promise<{ appointments: Appointment[] }> => {
    return request<{ appointments: Appointment[] }>("/api/provider/appointments");
  },

  acknowledgeAppointment: async (appointmentId: string): Promise<Appointment> => {
    return request<Appointment>(`/api/provider/appointments/${encodeURIComponent(appointmentId)}/acknowledge`, {
      method: "POST",
    });
  },

  markAppointmentAttended: async (appointmentId: string): Promise<Appointment> => {
    return request<Appointment>(`/api/provider/appointments/${encodeURIComponent(appointmentId)}/attended`, {
      method: "POST",
    });
  },

  getAdminProviders: async (): Promise<{ providers: ProviderDirectoryEntry[] }> => {
    return request<{ providers: ProviderDirectoryEntry[] }>("/api/admin/providers");
  },

  updateProviderAvailability: async (providerId: string, available: boolean): Promise<ProviderDirectoryEntry> => {
    return request<ProviderDirectoryEntry>(`/api/admin/providers/${encodeURIComponent(providerId)}`, {
      method: "PATCH",
      body: JSON.stringify({ available }),
    });
  },

  getAdminEscalations: async (): Promise<{ escalations: Appointment[] }> => {
    return request<{ escalations: Appointment[] }>("/api/admin/escalations");
  },

  getAdminStats: async (): Promise<{
    total_users: number;
    total_patients: number;
    total_providers: number;
    total_appointments: number;
    total_checkins: number;
    active_escalations: number;
  }> => {
    return request("/api/admin/stats");
  },

  getAdminUsers: async (): Promise<{ users: Array<{ user_id: string; email: string; role: string; created_at: string }> }> => {
    return request("/api/admin/users");
  },

  // 10. In-App Notifications & FCM Web Push (PR H / Proposal Sec 13.2 & 15)
  getMyNotifications: async (): Promise<NotificationListResponse> => {
    return request<NotificationListResponse>("/api/me/notifications");
  },

  markNotificationRead: async (notificationId: string): Promise<InAppNotification> => {
    return request<InAppNotification>(`/api/me/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: "POST",
    });
  },

  markAllNotificationsRead: async (): Promise<{ updated: number }> => {
    return request<{ updated: number }>("/api/me/notifications/read-all", {
      method: "POST",
    });
  },

  registerFcmToken: async (token: string, deviceInfo?: string): Promise<{ token: string; status: string }> => {
    return request<{ token: string; status: string }>("/api/me/fcm-token", {
      method: "POST",
      body: JSON.stringify({ token, device_info: deviceInfo }),
    });
  },

  deleteFcmToken: async (token: string): Promise<{ deleted: boolean }> => {
    return request<{ deleted: boolean }>("/api/me/fcm-token", {
      method: "DELETE",
      body: JSON.stringify({ token }),
    });
  },

  getProviderNotifications: async (): Promise<NotificationListResponse> => {
    return request<NotificationListResponse>("/api/provider/notifications");
  },

  markProviderNotificationRead: async (notificationId: string): Promise<InAppNotification> => {
    return request<InAppNotification>(`/api/provider/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: "POST",
    });
  },

  getAdminNotifications: async (): Promise<NotificationListResponse> => {
    return request<NotificationListResponse>("/api/admin/notifications");
  },

  markAdminNotificationRead: async (notificationId: string): Promise<InAppNotification> => {
    return request<InAppNotification>(`/api/admin/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: "POST",
    });
  },
};
