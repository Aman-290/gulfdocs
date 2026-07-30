import Link from "next/link";
import { BrandMark } from "./brand-mark";

export function Footer() {
  return (
    <footer className="footer">
      <div className="shell footer-grid">
        <div>
          <div className="brand footer-brand">
            <BrandMark />
            <span>GulfDocs</span>
          </div>
          <p>Bilingual document intelligence with reviewable evidence.</p>
        </div>
        <div className="footer-links">
          <Link href="/demo">Public demo</Link>
          <Link href="/architecture">Architecture</Link>
          <Link href="/evaluation">Evaluation</Link>
        </div>
        <p className="footer-caveat">
          Portfolio project · Synthetic public data · No compliance
          certification claims
        </p>
      </div>
    </footer>
  );
}
