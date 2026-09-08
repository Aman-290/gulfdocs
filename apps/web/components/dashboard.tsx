"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  FileText,
  Gauge,
  LoaderCircle,
  Search,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { ChangeEvent, useMemo, useState } from "react";
import { AppBar } from "@/components/app-bar";
import { GulfDocsApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";

const statusLabels: Record<string, string> = {
  pending_upload: "Awaiting upload",
  uploaded: "Uploaded",
  queued: "Queued",
  processing: "Processing",
  ready: "Ready",
  needs_review: "Needs review",
  approved: "Approved",
  failed: "Failed",
};
const processingStatuses = new Set([
  "pending_upload",
  "uploaded",
  "queued",
  "processing",
]);

function readableBytes(bytes: number | null) {
  if (!bytes) return "—";
  return bytes < 1_000_000
    ? `${Math.round(bytes / 1_000)} KB`
    : `${(bytes / 1_000_000).toFixed(1)} MB`;
}

export function Dashboard() {
  const { getToken } = useAuth();
  const api = useMemo(() => new GulfDocsApi(getToken), [getToken]);
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [documentType, setDocumentType] = useState("all");
  const [language, setLanguage] = useState("all");
  const [approval, setApproval] = useState("all");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
    refetchInterval: (query) =>
      query.state.data?.some((item) => processingStatuses.has(item.status))
        ? Math.min(
            30_000,
            2_000 * 2 ** Math.min(query.state.dataUpdateCount, 4),
          )
        : false,
  });
  const metrics = useQuery({
    queryKey: ["metrics"],
    queryFn: () => api.getMetrics(),
  });
  const upload = useMutation({
    mutationFn: (file: File) => api.upload(file, setUploadProgress),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      setUploadProgress(0);
    },
    onError: (error) =>
      setUploadError(error instanceof Error ? error.message : "Upload failed."),
  });

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setUploadError(null);
    if (!file) return;
    if (
      file.type !== "application/pdf" ||
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setUploadError("Choose a PDF file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError("PDFs are limited to 10 MB.");
      return;
    }
    upload.mutate(file);
    event.target.value = "";
  }

  const rows = (documents.data || []).filter(
    (document) =>
      (status === "all" || document.status === status) &&
      (documentType === "all" || document.document_type === documentType) &&
      (language === "all" || document.detected_language === language) &&
      (approval === "all" ||
        (approval === "approved"
          ? document.status === "approved"
          : document.status !== "approved")) &&
      document.filename
        .toLocaleLowerCase()
        .includes(search.trim().toLocaleLowerCase()),
  );
  const ready = (documents.data || []).filter((document) =>
    ["ready", "approved"].includes(document.status),
  ).length;
  const needsReview =
    metrics.data?.quality.needs_review_documents ??
    (documents.data || []).filter(
      (document) => document.status === "needs_review",
    ).length;
  const bytes = (documents.data || []).reduce(
    (sum, document) => sum + (document.size_bytes || 0),
    0,
  );
  const today = new Date().toISOString().slice(0, 10);
  const uploadedToday = (documents.data || []).filter(
    (document) => document.created_at.slice(0, 10) === today,
  ).length;

  return (
    <main id="main-content" className="app-shell shell">
      <AppBar title="Document workspace" />
      <section className="dashboard-hero">
        <div>
          <p className="kicker">Private workspace</p>
          <h2>Review business documents with evidence.</h2>
          <p>
            Upload Arabic or English PDFs, monitor extraction, correct flagged
            values, and ask grounded questions.
          </p>
        </div>
        <label
          className={`upload-control ${upload.isPending ? "disabled" : ""}`}
        >
          {upload.isPending ? (
            <LoaderCircle className="spin" />
          ) : (
            <UploadCloud />
          )}
          <span>
            <strong>
              {upload.isPending ? `Uploading ${uploadProgress}%` : "Upload PDF"}
            </strong>
            <small>Up to 10 MB · 50 pages</small>
          </span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            disabled={upload.isPending}
            onChange={chooseFile}
          />
        </label>
      </section>
      {uploadError ? (
        <div className="inline-error" role="alert">
          <AlertCircle size={17} />
          {uploadError}
        </div>
      ) : null}
      <section className="metric-grid" aria-label="Workspace usage">
        <article>
          <FileText />
          <span>
            <strong>
              {metrics.data?.quality.total_documents ??
                documents.data?.length ??
                0}
            </strong>
            Documents
          </span>
        </article>
        <article>
          <Gauge />
          <span>
            <strong>{ready}</strong>Ready or approved
            <small>
              {metrics.data?.quality.p95_processing_ms
                ? `p95 ${Math.round(metrics.data.quality.p95_processing_ms)} ms`
                : "Processing timing pending"}
            </small>
          </span>
        </article>
        <article>
          <AlertCircle />
          <span>
            <strong>{needsReview}</strong>Need review
            <small>
              {metrics.data
                ? `${Math.round(metrics.data.quality.failure_rate * 100)}% failure rate`
                : "Quality summary loading"}
            </small>
          </span>
        </article>
        <article>
          <UploadCloud />
          <span>
            <strong>
              {metrics.data?.usage.uploads_used ?? uploadedToday} /{" "}
              {metrics.data?.usage.uploads_limit ?? 5}
            </strong>
            Daily uploads · {readableBytes(bytes)} stored
            <small>
              {metrics.data
                ? `${metrics.data.usage.questions_used}/${metrics.data.usage.questions_limit} questions · ${metrics.data.usage.generated_tokens} tokens`
                : "Usage summary loading"}
            </small>
          </span>
        </article>
      </section>
      <section className="document-index">
        <div className="index-heading">
          <div>
            <h2>Documents</h2>
            <p>Status updates refresh while processing.</p>
          </div>
          <div className="document-filters">
            <label className="search-control">
              <span className="sr-only">Search documents</span>
              <Search size={15} />
              <input
                type="search"
                placeholder="Search filename"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <label>
              Status
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="all">All statuses</option>
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Type
              <select
                value={documentType}
                onChange={(event) => setDocumentType(event.target.value)}
              >
                <option value="all">All types</option>
                <option value="invoice">Invoice</option>
                <option value="quotation">Quotation</option>
                <option value="purchase_order">Purchase order</option>
                <option value="contract">Contract</option>
              </select>
            </label>
            <label>
              Language
              <select
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
              >
                <option value="all">All languages</option>
                <option value="en">English</option>
                <option value="ar">Arabic</option>
                <option value="mixed">Mixed</option>
              </select>
            </label>
            <label>
              Approval
              <select
                value={approval}
                onChange={(event) => setApproval(event.target.value)}
              >
                <option value="all">Any decision</option>
                <option value="approved">Approved</option>
                <option value="pending">Not approved</option>
              </select>
            </label>
          </div>
        </div>
        {documents.isLoading ? (
          <div className="state-card">
            <LoaderCircle className="spin" />
            <h3>Loading documents</h3>
            <p>Opening your workspace…</p>
          </div>
        ) : null}
        {documents.isError ? (
          <div className="state-card error">
            <AlertCircle />
            <h3>Could not load the workspace</h3>
            <p>{documents.error.message}</p>
            <button
              className="button button-secondary"
              onClick={() => documents.refetch()}
            >
              Try again
            </button>
          </div>
        ) : null}
        {!documents.isLoading && !documents.isError && rows.length === 0 ? (
          <div className="state-card">
            <FileText />
            <h3>
              {documents.data?.length
                ? "No documents match these filters"
                : "No documents yet"}
            </h3>
            <p>
              {documents.data?.length
                ? "Clear a search or choose broader filters."
                : "Upload a PDF to begin the extraction workflow."}
            </p>
          </div>
        ) : null}
        {rows.length ? (
          <div
            className="document-table-live"
            role="table"
            aria-label="Documents"
          >
            <div className="document-row document-row-head" role="row">
              <span>Name</span>
              <span>Status</span>
              <span>Type / language</span>
              <span>Pages</span>
              <span>Updated</span>
              <span aria-hidden="true" />
            </div>
            {rows.map((document) => (
              <Link
                role="row"
                href={`/documents/${document.id}`}
                className="document-row"
                key={document.id}
              >
                <span className="document-name" dir="auto">
                  <FileText size={17} />
                  {document.filename}
                </span>
                <span>
                  <b className={`status-pill status-${document.status}`}>
                    {statusLabels[document.status] || document.status}
                  </b>
                </span>
                <span>
                  {document.document_type
                    ? fieldType(document.document_type)
                    : "Detecting…"}
                  {document.detected_language
                    ? ` · ${document.detected_language.toUpperCase()}`
                    : ""}
                </span>
                <span>{document.page_count ?? "—"}</span>
                <span>
                  {new Intl.DateTimeFormat(undefined, {
                    dateStyle: "medium",
                  }).format(new Date(document.updated_at))}
                </span>
                <span>
                  <ArrowRight size={17} />
                </span>
              </Link>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

function fieldType(value: string) {
  return value
    .split("_")
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}
