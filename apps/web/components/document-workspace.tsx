"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ExternalLink,
  FileQuestion,
  LoaderCircle,
  MessageSquareText,
  RotateCcw,
  Save,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AppBar } from "@/components/app-bar";
import { Answer, ExtractionField, GulfDocsApi } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";

const questionSchema = z.object({
  question: z.string().trim().min(3, "Enter at least 3 characters.").max(500),
});
type QuestionForm = z.infer<typeof questionSchema>;
const terminalStatuses = new Set([
  "ready",
  "needs_review",
  "approved",
  "failed",
]);

function fieldLabel(key: string) {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function FieldEditor({
  field,
  documentId,
  api,
}: {
  field: ExtractionField;
  documentId: string;
  api: GulfDocsApi;
}) {
  const queryClient = useQueryClient();
  const initial = Array.isArray(field.value)
    ? field.value.join(", ")
    : field.value || "";
  const [value, setValue] = useState(initial);
  const [editing, setEditing] = useState(false);
  const correction = useMutation({
    mutationFn: () =>
      api.correctField(
        documentId,
        field.key,
        value,
        "Reviewer correction from document workspace",
      ),
    onSuccess: async () => {
      setEditing(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["extraction", documentId] }),
        queryClient.invalidateQueries({ queryKey: ["audit", documentId] }),
      ]);
    },
  });
  return (
    <div className="extraction-field">
      <div>
        <span>{fieldLabel(field.key)}</span>
        <small>{Math.round(field.confidence * 100)}% confidence</small>
      </div>
      {editing ? (
        <div className="field-edit">
          <input
            dir="auto"
            aria-label={`Correct ${fieldLabel(field.key)}`}
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
          <button
            type="button"
            className="icon-button"
            aria-label={`Save ${fieldLabel(field.key)}`}
            disabled={correction.isPending}
            onClick={() => correction.mutate()}
          >
            {correction.isPending ? (
              <LoaderCircle className="spin" />
            ) : (
              <Save />
            )}
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="field-value"
          onClick={() => setEditing(true)}
        >
          <strong dir="auto">{initial || "Not found"}</strong>
          <span>Edit</span>
        </button>
      )}
      <div className="field-evidence">
        {field.citations.length ? (
          field.citations.map((citation, index) => (
            <span key={`${citation.page}-${index}`}>
              Page {citation.page}
              {citation.quote ? ` · “${citation.quote}”` : ""}
            </span>
          ))
        ) : (
          <span>No source citation</span>
        )}
      </div>
      {correction.isError ? (
        <small className="error-text">{correction.error.message}</small>
      ) : null}
    </div>
  );
}

function SecurePdf({
  documentId,
  api,
}: {
  documentId: string;
  api: GulfDocsApi;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let objectUrl: string | null = null;
    let active = true;
    api
      .download(documentId)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(
        (caught) =>
          active &&
          setError(
            caught instanceof Error
              ? caught.message
              : "PDF could not be loaded.",
          ),
      );
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [api, documentId]);
  if (error)
    return (
      <div className="pdf-state">
        <AlertCircle />
        <p>{error}</p>
      </div>
    );
  if (!url)
    return (
      <div className="pdf-state">
        <LoaderCircle className="spin" />
        <p>Loading protected PDF…</p>
      </div>
    );
  return (
    <iframe
      className="secure-pdf"
      title="Authenticated document PDF viewer"
      src={`${url}#toolbar=1&navpanes=0`}
    />
  );
}

function AnswerCard({ answer }: { answer: Answer }) {
  return (
    <article className={`qa-answer ${answer.supported ? "" : "unsupported"}`}>
      <div>
        <strong>
          {answer.supported
            ? "Grounded answer"
            : "Not supported by this document"}
        </strong>
        <span>{answer.latency_ms} ms</span>
      </div>
      <p dir="auto">{answer.answer}</p>
      {answer.citations.length ? (
        <ul>
          {answer.citations.map((citation, index) => (
            <li key={`${citation.page}-${index}`}>
              <a href={`#page-${citation.page}`}>
                Page {citation.page} <ExternalLink size={12} />
              </a>
              {citation.quote ? (
                <blockquote>“{citation.quote}”</blockquote>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <small>
          No citation was returned; treat this response as unsupported.
        </small>
      )}
      <footer>
        {answer.model_name} · {answer.prompt_version}
      </footer>
    </article>
  );
}

export function DocumentWorkspace({ documentId }: { documentId: string }) {
  const { getToken } = useAuth();
  const api = useMemo(() => new GulfDocsApi(getToken), [getToken]);
  const queryClient = useQueryClient();
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api.getDocument(documentId),
    refetchInterval: (query) =>
      query.state.data && !terminalStatuses.has(query.state.data.status)
        ? Math.min(
            30_000,
            2_000 * 2 ** Math.min(query.state.dataUpdateCount, 4),
          )
        : false,
  });
  const canReview =
    document.data &&
    ["ready", "needs_review", "approved"].includes(document.data.status);
  const extraction = useQuery({
    queryKey: ["extraction", documentId],
    queryFn: () => api.getExtraction(documentId),
    enabled: Boolean(canReview),
  });
  const questions = useQuery({
    queryKey: ["questions", documentId],
    queryFn: () => api.getQuestions(documentId),
    enabled: Boolean(canReview),
  });
  const audit = useQuery({
    queryKey: ["audit", documentId],
    queryFn: () => api.getAudit(documentId),
  });
  const [tab, setTab] = useState<"fields" | "questions" | "activity">("fields");
  const form = useForm<QuestionForm>({
    resolver: zodResolver(questionSchema),
    defaultValues: { question: "" },
  });
  const ask = useMutation({
    mutationFn: ({ question }: QuestionForm) => api.ask(documentId, question),
    onSuccess: async () => {
      form.reset();
      await queryClient.invalidateQueries({
        queryKey: ["questions", documentId],
      });
    },
  });
  const approve = useMutation({
    mutationFn: () => api.approve(documentId, "Approved in document workspace"),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["document", documentId] }),
        queryClient.invalidateQueries({ queryKey: ["extraction", documentId] }),
        queryClient.invalidateQueries({ queryKey: ["audit", documentId] }),
      ]);
    },
  });
  const retry = useMutation({
    mutationFn: () => api.retry(documentId),
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: ["document", documentId] }),
  });

  if (document.isLoading)
    return (
      <main id="main-content" className="app-loading">
        <LoaderCircle className="spin" />
        <p>Opening document…</p>
      </main>
    );
  if (document.isError || !document.data)
    return (
      <main id="main-content" className="app-loading error">
        <AlertCircle />
        <h1>Document unavailable</h1>
        <p>
          {document.error?.message ||
            "The document could not be found in this workspace."}
        </p>
        <Link className="button button-secondary" href="/dashboard">
          Return to workspace
        </Link>
      </main>
    );
  const unresolved =
    extraction.data?.issues.filter((issue) => !issue.resolved) || [];
  const processing = !terminalStatuses.has(document.data.status);

  return (
    <main id="main-content" className="app-shell shell document-app">
      <AppBar title={document.data.filename} />
      <div className="document-command">
        <Link href="/dashboard">
          <ArrowLeft size={15} /> All documents
        </Link>
        <div>
          <b className={`status-pill status-${document.data.status}`}>
            {document.data.status.replaceAll("_", " ")}
          </b>
          <span>{document.data.page_count ?? "—"} pages</span>
          {document.data.status === "failed" ? (
            <button
              className="button button-small button-secondary"
              disabled={retry.isPending}
              onClick={() => retry.mutate()}
            >
              <RotateCcw size={14} />
              Retry
            </button>
          ) : null}
        </div>
      </div>
      {processing ? (
        <section className="processing-banner" aria-live="polite">
          <LoaderCircle className="spin" />
          <div>
            <strong>Document processing is in progress</strong>
            <p>
              GulfDocs is validating, extracting, and indexing this file. This
              view refreshes automatically.
            </p>
          </div>
        </section>
      ) : null}
      <section className="review-workspace">
        <div className="pdf-pane">
          <div className="pane-heading">
            <span>Source document</span>
            <small>Authenticated browser PDF viewer</small>
          </div>
          <SecurePdf documentId={documentId} api={api} />
        </div>
        <div className="inspector-pane">
          <div className="workspace-tabs" role="tablist">
            <button
              role="tab"
              aria-selected={tab === "fields"}
              onClick={() => setTab("fields")}
            >
              Fields {unresolved.length ? <b>{unresolved.length}</b> : null}
            </button>
            <button
              role="tab"
              aria-selected={tab === "questions"}
              onClick={() => setTab("questions")}
            >
              Q&amp;A
            </button>
            <button
              role="tab"
              aria-selected={tab === "activity"}
              onClick={() => setTab("activity")}
            >
              Activity
            </button>
          </div>
          {tab === "fields" ? (
            <div className="inspector-content">
              {!canReview ? (
                <div className="state-card compact">
                  <FileQuestion />
                  <h3>Extraction is not ready</h3>
                  <p>Fields will appear after processing completes.</p>
                </div>
              ) : extraction.isLoading ? (
                <div className="state-card compact">
                  <LoaderCircle className="spin" />
                  <p>Loading extraction…</p>
                </div>
              ) : extraction.isError ? (
                <div className="inline-error">
                  <AlertCircle />
                  {extraction.error.message}
                </div>
              ) : (
                <>
                  <div className="extraction-summary">
                    <div>
                      <span>Detected type</span>
                      <strong>
                        {extraction.data?.document_type || "Unknown"}
                      </strong>
                    </div>
                    <div>
                      <span>Schema</span>
                      <strong>{extraction.data?.schema_version}</strong>
                    </div>
                  </div>
                  {unresolved.length ? (
                    <div className="issue-list">
                      <h3>Validation issues</h3>
                      {unresolved.map((issue) => (
                        <article key={`${issue.code}-${issue.source_page}`}>
                          <AlertCircle />
                          <div>
                            <strong>{issue.description}</strong>
                            <p>{issue.suggested_action}</p>
                            <small>
                              {issue.severity}
                              {issue.source_page
                                ? ` · Page ${issue.source_page}`
                                : ""}
                            </small>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="validation-clear">
                      <CheckCircle2 />
                      No unresolved validation issues
                    </div>
                  )}
                  <div className="live-field-list">
                    {extraction.data?.fields.map((field) => (
                      <FieldEditor
                        key={field.key}
                        field={field}
                        documentId={documentId}
                        api={api}
                      />
                    ))}
                  </div>
                  <div className="approval-box">
                    <ShieldCheck />
                    <div>
                      <strong>
                        {document.data.status === "approved"
                          ? "Approved output locked"
                          : "Ready for reviewer decision"}
                      </strong>
                      <p>
                        Approval is blocked while critical validation issues
                        remain unresolved.
                      </p>
                    </div>
                    {document.data.status !== "approved" ? (
                      <button
                        className="button button-primary"
                        disabled={
                          approve.isPending ||
                          unresolved.some((issue) =>
                            ["error", "critical"].includes(issue.severity),
                          )
                        }
                        onClick={() => approve.mutate()}
                      >
                        {approve.isPending ? (
                          <LoaderCircle className="spin" />
                        ) : (
                          <Check />
                        )}
                        Approve
                      </button>
                    ) : null}
                  </div>
                  {approve.isError ? (
                    <div className="inline-error">
                      <AlertCircle />
                      {approve.error.message}
                    </div>
                  ) : null}
                </>
              )}
            </div>
          ) : null}
          {tab === "questions" ? (
            <div className="inspector-content qa-pane">
              <div className="qa-intro">
                <MessageSquareText />
                <div>
                  <h2>Ask this document</h2>
                  <p>
                    Answers are restricted to retrieved page evidence.
                    Unsupported questions are declined.
                  </p>
                </div>
              </div>
              <form
                onSubmit={form.handleSubmit((values) => ask.mutate(values))}
              >
                <label htmlFor="question">Question</label>
                <textarea
                  id="question"
                  rows={3}
                  placeholder="What is the payment due date?"
                  {...form.register("question")}
                />
                <div>
                  <small className="error-text">
                    {form.formState.errors.question?.message}
                  </small>
                  <button
                    className="button button-primary"
                    disabled={!canReview || ask.isPending}
                  >
                    {ask.isPending ? (
                      <LoaderCircle className="spin" />
                    ) : (
                      <MessageSquareText />
                    )}
                    Ask
                  </button>
                </div>
              </form>
              {ask.isError ? (
                <div className="inline-error">
                  <AlertCircle />
                  {ask.error.message}
                </div>
              ) : null}
              <div className="answer-history">
                {questions.isLoading ? (
                  <p>Loading question history…</p>
                ) : questions.data?.length ? (
                  questions.data.map((answer) => (
                    <AnswerCard key={answer.question_id} answer={answer} />
                  ))
                ) : (
                  <div className="state-card compact">
                    <MessageSquareText />
                    <h3>No questions yet</h3>
                    <p>
                      Ask about a date, party, total, term, or line item in this
                      PDF.
                    </p>
                  </div>
                )}
              </div>
            </div>
          ) : null}
          {tab === "activity" ? (
            <div className="inspector-content">
              <div className="qa-intro">
                <ShieldCheck />
                <div>
                  <h2>Audit history</h2>
                  <p>
                    Only safe event metadata is recorded; document text is
                    excluded.
                  </p>
                </div>
              </div>
              {audit.isLoading ? (
                <p>Loading activity…</p>
              ) : audit.isError ? (
                <div className="inline-error">
                  <AlertCircle />
                  {audit.error.message}
                </div>
              ) : (
                <ol className="audit-list">
                  {audit.data?.map((entry) => (
                    <li key={entry.id}>
                      <span />
                      <div>
                        <strong>{entry.event_type.replaceAll("_", " ")}</strong>
                        <time dateTime={entry.created_at}>
                          {new Intl.DateTimeFormat(undefined, {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(entry.created_at))}
                        </time>
                        <small>
                          {Object.keys(entry.safe_metadata).length
                            ? JSON.stringify(entry.safe_metadata)
                            : "No additional metadata"}
                        </small>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
