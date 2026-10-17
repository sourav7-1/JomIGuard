import type { components, paths } from "./api-types";
import { strings } from "./strings";

const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export type LandIn = components["schemas"]["LandIn"];
export type LandOut = components["schemas"]["LandOut"];
export type DocumentStatusOut = components["schemas"]["DocumentStatusOut"];
export type AssessmentOut = components["schemas"]["AssessmentOut"];
export type DocType = components["schemas"]["DocType"];
export type DocStatus = components["schemas"]["DocStatus"];
export type DocStep = components["schemas"]["DocStep"];

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
  const url = endpoint.startsWith("http") ? endpoint : `${BASE_URL}${endpoint}`;
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
    });
  } catch {
    throw new ApiError(0, "Network Error", null, strings.error.networkError);
  }

  if (!res.ok) {
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

  getFieldsMeta: () =>
    apiFetch<FieldsMetaResponse>("/meta/fields", { method: "GET" }),

  getLandCaseView: (landId: string) =>
    apiFetch<LandCaseViewOut>(`/lands/${landId}/case-view`, { method: "GET" }),

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
  paths["/lands/{land_id}/case-view"]["get"]["responses"][200]["content"]["application/json"];
export type CaseViewDocOut = components["schemas"]["CaseViewDocOut"];
export type CaseViewExtractionOut = components["schemas"]["CaseViewExtractionOut"];
export type FieldMeta = components["schemas"]["FieldMeta"];
export type ExtractionOut = components["schemas"]["ExtractionOut"];
export type EditItem = components["schemas"]["EditItem"];
export type CorrectionRequest = components["schemas"]["CorrectionRequest"];

export type { paths };
