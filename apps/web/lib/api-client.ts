export type DocumentRecord = {
  id: string;
  filename: string;
  status: string;
  size_bytes: number | null;
  page_count: number | null;
  content_type: string | null;
  document_type: string | null;
  detected_language: string | null;
  created_at: string;
  updated_at: string;
};

export type ExtractionField = {
  key: string;
  value: string | string[] | null;
  confidence: number;
  citations: Array<{ page: number; quote?: string; [key: string]: unknown }>;
};

export type ValidationIssue = {
  code: string;
  severity: string;
  description: string;
  related_fields: string[];
  source_page: number | null;
  suggested_action: string;
  resolved: boolean;
};

export type Extraction = {
  document_id: string;
  schema_version: string;
  document_type: string | null;
  fields: ExtractionField[];
  issues: ValidationIssue[];
  approved_output: Record<string, unknown> | null;
};

export type Answer = {
  question_id: string;
  answer: string;
  citations: Array<{ page: number; quote?: string; chunk_id?: string }>;
  supported: boolean;
  model_name: string;
  prompt_version: string;
  latency_ms: number;
  created_at: string;
};

export type AuditEntry = {
  id: string;
  event_type: string;
  safe_metadata: Record<string, unknown>;
  created_at: string;
};

export type MetricsSummary = {
  generated_at: string;
  usage: {
    usage_date: string;
    uploads_used: number;
    uploads_limit: number;
    questions_used: number;
    questions_limit: number;
    generated_tokens: number;
  };
  quality: {
    total_documents: number;
    failed_documents: number;
    needs_review_documents: number;
    approved_documents: number;
    failure_rate: number;
    needs_review_rate: number;
    average_processing_ms: number | null;
    median_processing_ms: number | null;
    p95_processing_ms: number | null;
  };
  daily_tokens: Array<{ date: string; tokens: number }>;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId?: string,
  ) {
    super(message);
  }
}

const apiBase = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

async function parseError(response: Response) {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
    title?: string;
    request_id?: string;
  } | null;
  return new ApiError(
    body?.detail || body?.title || `Request failed (${response.status})`,
    response.status,
    body?.request_id || response.headers.get("x-request-id") || undefined,
  );
}

export class GulfDocsApi {
  constructor(private readonly getToken: () => Promise<string | null>) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = await this.getToken();
    if (!token) throw new ApiError("Sign in is required.", 401);
    const response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
    if (!response.ok) throw await parseError(response);
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  listDocuments() {
    return this.request<DocumentRecord[]>("/api/v1/documents");
  }

  getMetrics() {
    return this.request<MetricsSummary>("/api/v1/metrics/summary");
  }

  getDocument(documentId: string) {
    return this.request<DocumentRecord>(`/api/v1/documents/${documentId}`);
  }

  getExtraction(documentId: string) {
    return this.request<Extraction>(
      `/api/v1/documents/${documentId}/extraction`,
    );
  }

  getQuestions(documentId: string) {
    return this.request<Answer[]>(`/api/v1/documents/${documentId}/questions`);
  }

  getAudit(documentId: string) {
    return this.request<AuditEntry[]>(`/api/v1/documents/${documentId}/audit`);
  }

  async download(documentId: string) {
    const token = await this.getToken();
    if (!token) throw new ApiError("Sign in is required.", 401);
    const response = await fetch(
      `${apiBase}/api/v1/documents/${documentId}/download`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    if (!response.ok) throw await parseError(response);
    return response.blob();
  }

  async upload(file: File, onProgress?: (percent: number) => void) {
    const presigned = await this.request<{
      document_id: string;
      upload_url: string;
      required_headers: Record<string, string>;
    }>("/api/v1/uploads/presign", {
      method: "POST",
      headers: { "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({
        filename: file.name,
        size_bytes: file.size,
        content_type: "application/pdf",
      }),
    });
    onProgress?.(30);
    const uploaded = await fetch(presigned.upload_url, {
      method: "PUT",
      headers: presigned.required_headers,
      body: file,
    });
    if (!uploaded.ok) throw await parseError(uploaded);
    onProgress?.(75);
    const document = await this.request<DocumentRecord>(
      "/api/v1/uploads/complete",
      {
        method: "POST",
        body: JSON.stringify({ document_id: presigned.document_id }),
      },
    );
    onProgress?.(100);
    return document;
  }

  correctField(
    documentId: string,
    fieldKey: string,
    value: string,
    reason?: string,
  ) {
    return this.request<ExtractionField>(
      `/api/v1/documents/${documentId}/extraction`,
      {
        method: "PATCH",
        body: JSON.stringify({
          field_key: fieldKey,
          value,
          reason: reason || null,
        }),
      },
    );
  }

  approve(documentId: string, notes?: string) {
    return this.request<DocumentRecord>(
      `/api/v1/documents/${documentId}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ notes: notes || null }),
      },
    );
  }

  ask(documentId: string, question: string) {
    return this.request<Answer>(`/api/v1/documents/${documentId}/questions`, {
      method: "POST",
      body: JSON.stringify({ question }),
    });
  }

  retry(documentId: string) {
    return this.request<DocumentRecord>(
      `/api/v1/documents/${documentId}/retry`,
      {
        method: "POST",
      },
    );
  }
}
