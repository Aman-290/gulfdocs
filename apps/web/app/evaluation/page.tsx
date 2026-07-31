import type { Metadata } from "next";

export const metadata: Metadata = { title: "Evaluation" };

export default function EvaluationPage() {
  return (
    <main id="main-content" className="content-page shell">
      <div className="page-intro">
        <div>
          <p className="kicker">Evaluation</p>
          <h1>Measured results only.</h1>
          <p>
            Reproducible extraction, retrieval, citation, language, latency,
            token, and usage-cost measurements from versioned fictional
            fixtures.
          </p>
        </div>
      </div>
      <div className="empty-report measured-report">
        <span>FAKE PROVIDER · DATASET 2026-07-31.1 · 12 CASES</span>
        <h2>Deterministic local baseline</h2>
        <p>
          These values came from an executed local run over English, Arabic, and
          bilingual synthetic documents. They measure the deterministic fake
          provider—not production Gemini quality.
        </p>
        <div className="evaluation-metrics">
          <article>
            <strong>100%</strong>
            <span>Classification</span>
          </article>
          <article>
            <strong>99.07%</strong>
            <span>Field extraction</span>
          </article>
          <article>
            <strong>100%</strong>
            <span>Recall@3</span>
          </article>
          <article>
            <strong>100%</strong>
            <span>Citation precision</span>
          </article>
          <article>
            <strong>100%</strong>
            <span>Unsupported handling</span>
          </article>
          <article>
            <strong>1</strong>
            <span>Per-case failure</span>
          </article>
        </div>
        <p className="evaluation-caveat">
          Median latency was 31.922 ms and p95 was 85.014 ms on the measured
          machine. Fake-provider API cost was USD 0 because no billable model
          call occurred. Latency is environment-specific; token usage is a
          whitespace approximation on this path.
        </p>
        <p>
          <code>evaluation/results/latest.json</code> and <code>latest.md</code>{" "}
          contain the full report and per-case failures.
        </p>
      </div>
    </main>
  );
}
