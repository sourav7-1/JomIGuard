import type { components, paths } from "./api-types";
import { strings } from "./strings";

const BASE_URL = "/api";

export type LandIn = components["schemas"]["LandIn"];
export type LandOut = components["schemas"]["LandOut"];
export type IdentityVerificationOut = {
  id: string; land_id: string | null; party: "buyer" | "seller";
  seller_name_on_deed: string | null; status: "pending" | "verified" | "failed";
  name_bn_as_per_nid: string | null; father_name_as_per_nid: string | null;
  provider: string; provider_ref: string; verified_at: string | null; created_at: string;
};
export type DocumentStatusOut = components["schemas"]["DocumentStatusOut"];
export type AssessmentOut = components["schemas"]["AssessmentOut"];
export type DocType = components["schemas"]["DocType"];
export type DocStatus = components["schemas"]["DocStatus"];
export type DocStep = components["schemas"]["DocStep"];
export type EnumOption = components["schemas"]["EnumOption"];

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: unknown,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function formatBanglaError(status: number, data?: unknown): string {
  if (data && typeof data === "object") {
    const errorObj = data as Record<string, unknown>;

    // FastAPI HTTPException { "detail": "message" }
    if (typeof errorObj.detail === "string" && errorObj.detail.trim().length > 0) {
      return errorObj.detail;
    }

    // FastAPI 422 RequestValidationError { "detail": [{ "loc": [...], "msg": "..." }] }
    if (Array.isArray(errorObj.detail) && errorObj.detail.length > 0) {
      const first = errorObj.detail[0];
      if (first && typeof first === "object" && "msg" in first) {
        return `${strings.error.validationError}: ${String((first as { msg: unknown }).msg)}`;
      }
    }
  }

  if (status === 404) return strings.error.notFound;
  if (status === 413) return strings.uploadFlow.errFileSize;
  if (status === 415) return strings.uploadFlow.errFileType;
  if (status === 422) return strings.error.validationError;
  if (status >= 500) return strings.error.serverError;
  return strings.error.defaultMessage;
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

export async function apiFetch<T>(endpoint: string, options: ApiFetchOptions = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  let body: BodyInit | null | undefined = undefined;
  if (options.body !== undefined) {
    if (options.body instanceof FormData || typeof options.body === "string") {
      body = options.body;
    } else {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(options.body);
    }
  }

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers,
      body,
      signal: options.signal ?? (endpoint === "/auth/me" ? AbortSignal.timeout(10_000) : undefined),
      credentials: options.credentials ?? "include",
    });
  } catch {
    if (typeof window !== "undefined") window.dispatchEvent(new Event("jomiguard:offline"));
    throw new ApiError(0, "Network Error", null, strings.error.offlineMessage);
  }

  if (!res.ok) {
    if (res.status === 401 && !endpoint.startsWith("/auth/") && typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.dispatchEvent(new Event("jomiguard:unauthorized"));
    }
    let errorData: unknown = null;
    try {
      errorData = await res.json();
    } catch {
      // not json
    }
    const message = formatBanglaError(res.status, errorData);
    throw new ApiError(res.status, res.statusText, errorData, message);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return (await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    apiFetch<{ id: string; username: string }>("/auth/login", { method: "POST", body: { username, password } }),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
  getMe: () => apiFetch<{ id: string; username: string }>("/auth/me", { method: "GET" }),
  getLands: () => apiFetch<LandOut[]>("/lands", { method: "GET" }),
  createSellerLink: (landId: string, sellerName: string) =>
    apiFetch<{ url: string; expires_at: string }>(`/lands/${landId}/seller-links`, {
      method: "POST", body: { seller_name_on_deed: sellerName },
    }),
  sellerAgreeEscrow: (token: string) => apiFetch<{ accepted: boolean }>(`/verify/${token}/escrow-agree`, { method: "POST" }),
  createEscrow: (landId: string, body: { price: string; bayna: string; deadline: string }) => apiFetch<EscrowOut>(`/lands/${landId}/escrow`, { method: "POST", body }),
  getDemoEscrow: (caseId: string) => apiFetch<EscrowOut>(`/demo/escrow/${caseId}`, { method: "GET" }),
  getEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}`, { method: "GET" }),
  agreeEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}/agree`, { method: "POST" }),
  depositEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}/deposit`, { method: "POST" }),
  checkEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}/check`, { method: "POST" }),
  registerEscrow: (id: string, deed_no: string, date: string) => apiFetch<EscrowOut>(`/escrow/${id}/registration`, { method: "POST", body: { deed_no, date } }),
  releaseEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}/release`, { method: "POST" }),
  cancelEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}/cancel`, { method: "POST" }),
  expireEscrow: (id: string) => apiFetch<EscrowOut>(`/escrow/${id}/demo/expire`, { method: "POST" }),
  downloadBaynanama: async (id: string) => {
    const response = await fetch(`${BASE_URL}/escrow/${id}/baynanama.pdf`, { credentials: "include" });
    if (!response.ok) throw new ApiError(response.status, response.statusText, null, strings.error.serverError);
    const url = URL.createObjectURL(await response.blob()); const link = document.createElement("a");
    link.href = url; link.download = `bayna-${id}.pdf`; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  getSellerLink: (token: string) =>
    apiFetch<{ mouza: string; dag_no: string; message_bn: string; escrow_agreement_requested: boolean }>(`/verify/${token}`, { method: "GET" }),
  consentSeller: (token: string) =>
    apiFetch<{ consented: boolean }>(`/verify/${token}/consent`, { method: "POST", body: { consent: true } }),
  completeSellerVerification: (token: string, body: { name: string; father_name: string; outcome: "verified" | "failed" | "pending" }) =>
    apiFetch<IdentityVerificationOut>(`/verify/${token}/complete`, { method: "POST", body }),
  deleteSellerVerification: (token: string) => apiFetch<void>(`/verify/${token}`, { method: "DELETE" }),
  verifyBuyer: (body: { name: string; father_name: string; outcome: "verified" | "failed" | "pending"; consent: true }) =>
    apiFetch<IdentityVerificationOut>("/me/verification", { method: "POST", body }),
  getBuyerVerifications: () => apiFetch<IdentityVerificationOut[]>("/me/verification", { method: "GET"}),
  deleteBuyerVerification: (id: string) => apiFetch<void>(`/me/verification/${id}`, { method: "DELETE" }),
  get: <T>(endpoint: string, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: "GET" }),
  post: <T>(endpoint: string, body?: unknown, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: "POST", body }),
  patch: <T>(endpoint: string, body?: unknown, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: "PATCH", body }),
  delete: <T>(endpoint: string, options?: ApiFetchOptions) =>
    apiFetch<T>(endpoint, { ...options, method: "DELETE" }),

  // Specific domain helpers
  createLand: (data: { mouza: string; dag_no?: string; upazila?: string; district?: string }) =>
    apiFetch<LandOut>("/lands", {
      method: "POST",
      body: {
        mouza: data.mouza,
        dag_no: data.dag_no || "",
        upazila: data.upazila || "",
        district: data.district || "",
      },
    }),

  getLand: (landId: string) => apiFetch<LandOut>(`/lands/${landId}`, { method: "GET" }),

  getLandDocuments: (landId: string) =>
    apiFetch<DocumentStatusOut[]>(`/lands/${landId}/documents`, { method: "GET" }),

  getDocument: (documentId: string) =>
    apiFetch<DocumentStatusOut>(`/documents/${documentId}`, { method: "GET" }),

  reprocessDocument: (documentId: string) =>
    apiFetch<DocumentStatusOut>(`/documents/${documentId}/reprocess`, { method: "POST" }),

  detachDocument: (documentId: string) =>
    apiFetch<unknown>(`/documents/${documentId}`, {
      method: "PATCH",
      body: { land_id: null },
    }),

  assessLand: (landId: string) =>
    apiFetch<AssessmentOut>(`/lands/${landId}/assess`, { method: "POST" }),

  getAssessments: (landId: string) =>
    apiFetch<AssessmentOut[]>(`/lands/${landId}/assessments`, { method: "GET" }),

  getAssessmentDiff: (landId: string, assessmentId: string) =>
    apiFetch<AssessmentDiff>(`/lands/${landId}/assessments/${assessmentId}/diff`, { method: "GET" }),

  updateAction: (landId: string, actionId: string, done: boolean) =>
    apiFetch<ActionOut>(`/lands/${landId}/actions/${encodeURIComponent(actionId)}`, {
      method: "PUT",
      body: { done },
    }),

  downloadReport: async (landId: string, assessmentId: string) => {
    const response = await fetch(`${BASE_URL}/lands/${landId}/assessments/${assessmentId}/report.pdf`, { credentials: "include" });
    if (!response.ok) throw new ApiError(response.status, response.statusText, null, strings.error.serverError);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `jomiguard-report-${landId}.pdf`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  getFieldsMeta: () =>
    apiFetch<FieldsMetaResponse>("/meta/fields", { method: "GET" }),

  getLandCaseView: (landId: string) =>
    apiFetch<LandCaseViewOut>(`/lands/${landId}/case-view`, { method: "GET" }),

  getLandDeeds: (landId: string) =>
    apiFetch<DeedArchiveOut>(`/lands/${landId}/deeds`, { method: "GET" }),

  compareLandDeeds: (landId: string, a: string, b: string) =>
    apiFetch<DeedCompareOut>(`/lands/${landId}/deeds/compare?a=${a}&b=${b}`, { method: "GET" }),

  updateDeedProvenance: (documentId: string, source_type: string) =>
    apiFetch<{ source_type: string; official_source_verified: false }>(`/documents/${documentId}/provenance`, { method: "PATCH", body: { source_type } }),

  verifyDocumentFingerprint: (documentId: string) =>
    apiFetch<FingerprintVerificationOut>(`/documents/${documentId}/fingerprint/verify`, { method: "POST" }),

  getTimeline: (landId: string) =>
    apiFetch<TimelineOut>(`/lands/${landId}/timeline`, { method: "GET" }),

  getGuardianLands: () => apiFetch<GuardianLandOut[]>("/guardian/lands", { method: "GET" }),
  addGuardianLand: (document_id: string) => apiFetch<GuardianLandOut>("/guardian/lands", { method: "POST", body: { document_id } }),
  checkGuardianLand: (id: string, document_id: string) => apiFetch<GuardianCheckOut>(`/guardian/lands/${id}/check`, { method: "POST", body: { document_id } }),
  runGuardianDemo: () => apiFetch<Array<{ land_id: string; severity: string; alert_id: string | null }>>("/guardian/demo-check", { method: "POST" }),
  getGuardianAlerts: (id: string) => apiFetch<GuardianAlertOut[]>(`/guardian/lands/${id}/alerts`, { method: "GET" }),
  readGuardianAlert: (id: string) => apiFetch<{ read: boolean }>(`/guardian/alerts/${id}/read`, { method: "POST" }),
  downloadGuardianCase: async (alertId: string) => {
    const response = await fetch(`${BASE_URL}/guardian/alerts/${alertId}/case-file`, { method: "POST", credentials: "include" });
    if (!response.ok) throw new ApiError(response.status, response.statusText, null, strings.error.serverError);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a"); link.href = url; link.download = `guardian-case-${alertId}.pdf`; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  uploadGuardianKhatian: async (file: File) => {
    const body = new FormData(); body.append("file", file); body.append("doc_type", "khatian");
    return apiFetch<DocumentStatusOut>("/documents", { method: "POST", body });
  },
  getObjectionGuide: () => apiFetch<{ text: string; notice_bn: string }>("/guardian/objection-guide", { method: "GET" }),

  getDocumentFile: (documentId: string) =>
    apiFetch<{ url: string }>(`/documents/${documentId}/file`, { method: "GET" }),

  patchDocumentExtraction: (documentId: string, body: CorrectionRequest) =>
    apiFetch<ExtractionOut>(`/documents/${documentId}/extraction`, {
      method: "PATCH",
      body,
    }),

  getDocumentExtractionHistory: (documentId: string) =>
    apiFetch<ExtractionOut[]>(`/documents/${documentId}/extraction?history=true`, {
      method: "GET",
    }),
};

export type FieldsMetaResponse =
  paths["/meta/fields"]["get"]["responses"][200]["content"]["application/json"];
export type LandCaseViewOut =
  paths["/lands/{land_id}/case-view"]["get"]["responses"][200]["content"]["application/json"] & {
    identity_verifications: IdentityVerificationOut[];
  };
export type CaseViewDocOut = components["schemas"]["CaseViewDocOut"];
export type CaseViewExtractionOut = components["schemas"]["CaseViewExtractionOut"];
export type DeedArchiveFieldOut = { key: string; label_bn: string; current: unknown; previous: unknown; current_field: string; previous_field: string };
export type DeedArchiveItemOut = { id: string; original_filename: string; file_url_endpoint: string; created_at: string; uploaded_at: string; uploaded_by: string | null; content_sha256: string | null; data: components["schemas"]["DeedData"]; previous_document_id: string | null; comparison: DeedArchiveFieldOut[]; source_type: string; integrity: string; verification_status: string; extraction_id: string | null; extraction_created_at: string | null; extraction_created_by: string | null; audit: Array<{ event: string; actor: string; created_at: string; details: Record<string, unknown> }> };
export type DeedArchiveOut = { items: DeedArchiveItemOut[]; official_source_verified: false; notice_bn: string };
export type DeedCompareOut = { a: string; b: string; older_document_id: string; newer_document_id: string; fields: DeedArchiveFieldOut[]; links: { buyer_to_seller: boolean; same_dag: boolean; area_within: boolean }; official_source_verified: false; verification_status: string };
export type FingerprintVerificationOut = { stored_sha256: string | null; current_sha256: string; unchanged_since_upload: boolean | null; official_source_verified: false; notice_bn: string };
export type FieldMeta = components["schemas"]["FieldMeta"];
export type ExtractionOut = components["schemas"]["ExtractionOut"];
export type EditItem = components["schemas"]["EditItem"];
export type CorrectionRequest = components["schemas"]["CorrectionRequest"];
export type ActionOut = components["schemas"]["Action"];
export type AssessmentDiff = {
  previous: { id: string; risk_level: string } | null;
  risk_level: string;
  added_findings: string[];
  removed_findings: string[];
};
export type TimelineSource = { source_id: string; label_bn: string; field_path: string; printed_text: string | null; value_bn: string; };
export type TimelineParty = { name: string; relation?: string | null; share_text: string | null; share_fraction: string | number | null; source_field: string; };
export type TimelineEvent = { year: number | null; kind: string; title_bn: string; detail_bn: string; from_owners: TimelineParty[]; to_owners: TimelineParty[]; area: string | null; sources: TimelineSource[]; source_ids: string[]; status: "ok" | "warn" | "bad"; finding_codes: string[]; };
export type TimelineOut = { title_bn: string; events: TimelineEvent[] };
export type GuardianLandOut = { id: string; label_bn: string; district: string; upazila: string; mouza: string; dag_no: string; khatian_no: string; last_checked_at: string | null; status: "ok" | "warn" | "bad"; unread_alerts: number; demo_document_id: string | null; documents: Array<{ id: string; original_filename: string; integrity: string }>; current_snapshot: Record<string, unknown> | null };
export type GuardianCheckOut = { alert_id: string | null; severity: string; changes: Array<{ field: string; old: unknown; new: unknown; severity: string; message_bn: string }> };
export type GuardianAlertOut = { id: string; severity: string; message_bn: string; changes: GuardianCheckOut["changes"]; created_at: string; read_at: string | null; old: Record<string, unknown>; new: Record<string, unknown> };
export type EscrowOut = { id: string; land_id: string; state: string; price_paisa: number; bayna_paisa: number; deadline: string; buyer_agreed: boolean; seller_agreed: boolean; conditions: { id: string; label_bn: string; met: boolean; detail_bn: string }[]; balances: { buyer_paisa: number; escrow_paisa: number; seller_paisa: number }; events: { event: string; from_state: string; to_state: string; actor: string; message_bn: string; created_at: string }[] };

export type { paths };
