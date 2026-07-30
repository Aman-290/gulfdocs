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
            GulfDocs will report extraction, retrieval, citation, language,
            latency, token, and estimated usage-cost metrics from versioned
            synthetic fixtures.
          </p>
        </div>
      </div>
      <div className="empty-report">
        <span>BASELINE STATUS</span>
        <h2>Evaluation pipeline scheduled for Phase 6</h2>
        <p>
          No benchmark values are shown because the evaluation suite has not run
          yet. This is intentional: the project never publishes invented
          accuracy or latency.
        </p>
        <ul>
          <li>Classification accuracy</li>
          <li>Field and line-item accuracy</li>
          <li>Retrieval recall@k</li>
          <li>Citation precision</li>
          <li>Arabic vs English slices</li>
          <li>Median and p95 latency</li>
        </ul>
      </div>
    </main>
  );
}
