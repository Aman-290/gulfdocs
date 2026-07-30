import type { Metadata } from "next";
import {
  ArrowDown,
  Cloud,
  Database,
  FileLock2,
  Globe2,
  Workflow,
} from "lucide-react";

export const metadata: Metadata = { title: "Architecture" };

const layers = [
  [
    Globe2,
    "Firebase App Hosting",
    "Next.js public demo and authenticated workspace",
  ],
  [
    Cloud,
    "Cloud Run API",
    "FastAPI authentication, authorization, uploads, and document APIs",
  ],
  [
    Workflow,
    "Cloud Tasks → private worker",
    "OIDC delivery and idempotent document processing",
  ],
  [
    FileLock2,
    "Cloud Storage + Gemini",
    "Private PDFs and provider-backed document understanding",
  ],
  [
    Database,
    "Neon PostgreSQL",
    "Relational data, full-text search, and pgvector",
  ],
] as const;

export default function ArchitecturePage() {
  return (
    <main id="main-content" className="content-page shell">
      <div className="page-intro">
        <div>
          <p className="kicker">Architecture</p>
          <h1>Separated services, explicit trust boundaries.</h1>
          <p>
            The public API never performs long-running PDF work. A private,
            authenticated worker processes identifier-only tasks.
          </p>
        </div>
      </div>
      <div className="architecture-stack">
        {layers.map(([Icon, title, text], index) => (
          <div key={title} className="architecture-layer">
            <Icon size={23} />
            <div>
              <h2>{title}</h2>
              <p>{text}</p>
            </div>
            {index < layers.length - 1 && (
              <ArrowDown
                className="architecture-arrow"
                size={19}
                aria-hidden="true"
              />
            )}
          </div>
        ))}
      </div>
      <section className="principle-grid">
        <article>
          <h2>Least privilege</h2>
          <p>
            Separate runtime and deployment identities receive only the
            permissions required for their role.
          </p>
        </article>
        <article>
          <h2>Local parity</h2>
          <p>
            Filesystem, inline queue, development auth, and fake AI adapters
            preserve cloud-facing domain interfaces.
          </p>
        </article>
        <article>
          <h2>Cost bounds</h2>
          <p>
            Scale-to-zero services, strict instance caps, upload limits, queue
            throttles, and lifecycle cleanup constrain low-use costs without
            promising permanent zero cost.
          </p>
        </article>
      </section>
    </main>
  );
}
