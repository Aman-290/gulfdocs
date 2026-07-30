import type { Metadata } from "next";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  ShieldCheck,
} from "lucide-react";
import { DemoQuestionPanel } from "@/components/demo-question-panel";
import { publicDemo } from "@/lib/public-demo";

export const metadata: Metadata = {
  title: "Public demo",
  description:
    "Inspect a seeded synthetic GulfDocs document without creating an account.",
};

export default function DemoPage() {
  return (
    <main id="main-content" className="demo-page shell">
      <div className="page-intro">
        <div>
          <p className="kicker">Public demo · no registration</p>
          <h1>Inspect the evidence, not just the answer.</h1>
          <p>
            This seeded result remains usable when external AI quota is
            unavailable.
          </p>
        </div>
        <div className="synthetic-badge">
          <ShieldCheck size={17} /> Synthetic document
        </div>
      </div>

      <div className="demo-workspace">
        <section className="pdf-surface" aria-label="Synthetic PDF preview">
          <div className="pdf-toolbar">
            <span>
              <FileText size={16} /> {publicDemo.name}
            </span>
            <b>1 / {publicDemo.pages}</b>
          </div>
          <article className="paper" id="page-1">
            <div className="paper-brand">NORTHSTAR</div>
            <div className="paper-title">
              <h2>INVOICE</h2>
              <p>INV-GD-1042</p>
            </div>
            <div className="paper-meta">
              <p>
                <b>Supplier</b>Northstar Office Trading LLC
              </p>
              <p>
                <b>Issue date</b>22 July 2026
              </p>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Description</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Workspace equipment package</td>
                  <td>AED 8,500.00</td>
                </tr>
                <tr>
                  <td>Installation and support</td>
                  <td>AED 3,000.00</td>
                </tr>
              </tbody>
            </table>
            <div className="paper-totals">
              <span>
                Subtotal <b>AED 11,500.00</b>
              </span>
              <span>
                VAT 5% <b>AED 575.00</b>
              </span>
              <span className="mismatch">
                Total <b>AED 12,862.50</b>
              </span>
            </div>
            <small>Fictional data created for the GulfDocs public demo.</small>
          </article>
          <article className="paper second-page" id="page-2">
            <h2>Terms</h2>
            <p>Payment terms: Net 30 days from invoice date.</p>
            <p>
              All names, values, and entities in this document are synthetic.
            </p>
          </article>
        </section>

        <aside className="review-panel">
          <div className="document-summary">
            <div>
              <span>{publicDemo.type}</span>
              <b>{publicDemo.language}</b>
            </div>
            <div className="review-status">
              <AlertTriangle size={16} /> Needs review
            </div>
          </div>
          <div
            className="review-tabs"
            aria-label="Document information sections"
          >
            <b>Extracted fields</b>
            <span>Validation</span>
            <span>Audit</span>
          </div>
          <section className="field-list" aria-label="Extracted fields">
            {publicDemo.fields.map((field) => (
              <div key={field.label}>
                <span>
                  {field.label}
                  <small>Page {field.page}</small>
                </span>
                <strong>
                  {field.value}
                  <em>{Math.round(field.confidence * 100)}%</em>
                </strong>
              </div>
            ))}
          </section>
          <section className="validation-card">
            <AlertTriangle size={18} aria-hidden="true" />
            <div>
              <span>{publicDemo.issue.code}</span>
              <strong>{publicDemo.issue.description}</strong>
              <p>{publicDemo.issue.action}</p>
            </div>
          </section>
          <div className="processing-line">
            <CheckCircle2 size={16} />
            <span>Parsed and extracted</span>
            <Clock3 size={16} />
            <span>Review pending</span>
          </div>
          <DemoQuestionPanel questions={publicDemo.questions} />
        </aside>
      </div>
      <div className="privacy-warning">
        <AlertTriangle size={18} />
        <p>
          <b>Do not upload sensitive material.</b> When configured with a free
          AI API tier, GulfDocs must not receive confidential, personal, legally
          sensitive, or commercially sensitive documents. Anonymous uploads are
          disabled.
        </p>
      </div>
    </main>
  );
}
