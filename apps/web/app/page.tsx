import {
  ArrowRight,
  BadgeCheck,
  Braces,
  FileCheck2,
  Languages,
  LockKeyhole,
  ScanText,
  SearchCheck,
} from "lucide-react";
import Link from "next/link";
import { ProductPreview } from "@/components/product-preview";

const capabilities = [
  {
    icon: ScanText,
    title: "Structured extraction",
    text: "Invoices, quotations, purchase orders, and contracts become reviewable business fields—not a wall of chat text.",
  },
  {
    icon: FileCheck2,
    title: "Deterministic validation",
    text: "Dates, currency, line items, tax, totals, and required identifiers are checked with explicit rules after extraction.",
  },
  {
    icon: BadgeCheck,
    title: "Human approval",
    text: "Reviewers can trace confidence and citations, correct a field, preserve the revision, and approve the final record.",
  },
  {
    icon: SearchCheck,
    title: "Grounded answers",
    text: "Hybrid retrieval constrains answers to authorized pages and returns evidence—or says when the document is insufficient.",
  },
];

const pipeline = [
  ["01", "Secure intake", "Private PDF, bounded size and pages"],
  ["02", "Parse & classify", "Page-aware English and Arabic text"],
  ["03", "Extract & validate", "Typed fields plus deterministic checks"],
  ["04", "Review & retrieve", "Corrections, approval, and cited Q&A"],
];

export default function Home() {
  return (
    <main id="main-content">
      <section className="hero shell">
        <div className="hero-copy">
          <div className="eyebrow">
            <Languages size={15} aria-hidden="true" />
            Arabic–English document intelligence
          </div>
          <h1>Business documents, made inspectable.</h1>
          <p className="hero-lede">
            GulfDocs extracts structured data, checks the numbers and dates,
            supports human review, and answers with page-level evidence.
          </p>
          <div className="hero-actions" aria-label="Primary actions">
            <Link className="button button-primary" href="/demo">
              Try public demo <ArrowRight size={17} aria-hidden="true" />
            </Link>
            <Link className="button button-secondary" href="/architecture">
              View architecture
            </Link>
          </div>
          <p className="demo-note">
            The public demo uses fictional, synthetic documents and requires no
            account. Anonymous uploads are disabled.
          </p>
        </div>
        <ProductPreview />
      </section>

      <section className="signal-strip" aria-label="Platform principles">
        <div className="shell signal-grid">
          <span>
            <Braces size={17} aria-hidden="true" /> Typed outputs
          </span>
          <span>
            <BadgeCheck size={17} aria-hidden="true" /> Human review
          </span>
          <span>
            <LockKeyhole size={17} aria-hidden="true" /> Workspace isolation
          </span>
          <span>
            <SearchCheck size={17} aria-hidden="true" /> Page citations
          </span>
        </div>
      </section>

      <section className="section shell" id="capabilities">
        <div className="section-heading">
          <p className="kicker">Beyond “chat with PDF”</p>
          <h2>A controlled document-processing system</h2>
          <p>
            Model output is one input to a traceable workflow. Rules,
            permissions, review, and evidence determine what reaches an approved
            record.
          </p>
        </div>
        <div className="capability-grid">
          {capabilities.map(({ icon: Icon, title, text }) => (
            <article className="capability-card" key={title}>
              <Icon size={22} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section section-ink" id="pipeline">
        <div className="shell">
          <div className="section-heading section-heading-light">
            <p className="kicker">Processing pipeline</p>
            <h2>Deterministic by design</h2>
            <p>
              Each stage records status, versions, timing, failures, and safe
              audit metadata.
            </p>
          </div>
          <ol className="pipeline-grid">
            {pipeline.map(([number, title, text]) => (
              <li key={number}>
                <span>{number}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section shell bilingual-section">
        <div>
          <p className="kicker">Built for bilingual evidence</p>
          <h2>English structure. Arabic context. One review trail.</h2>
          <p>
            Page boundaries and original Arabic characters stay attached to
            extracted fields and search chunks, while the interface supports
            both LTR and RTL reading.
          </p>
          <Link className="text-link" href="/ar">
            Explore the Arabic experience{" "}
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        <div className="arabic-card" lang="ar" dir="rtl">
          <span>فاتورة تجريبية · الصفحة ١</span>
          <strong>شركة المدار التجارية</strong>
          <p>الإجمالي المستخرج</p>
          <b>١٢٬٨٦٢٫٥٠ د.إ</b>
          <small>تم التحقق من المصدر والمجموع</small>
        </div>
      </section>

      <section className="section shell final-cta">
        <div>
          <p className="kicker">Evidence before confidence</p>
          <h2>Inspect the sample workflow yourself.</h2>
        </div>
        <Link className="button button-primary" href="/demo">
          Open the synthetic demo <ArrowRight size={17} aria-hidden="true" />
        </Link>
      </section>
    </main>
  );
}
