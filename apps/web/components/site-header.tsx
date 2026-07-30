import Link from "next/link";
import { BrandMark } from "./brand-mark";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="shell nav-wrap">
        <Link className="brand" href="/" aria-label="GulfDocs home">
          <BrandMark />
          <span>GulfDocs</span>
        </Link>
        <nav aria-label="Primary navigation">
          <Link href="/demo">Demo</Link>
          <Link href="/architecture">Architecture</Link>
          <Link href="/evaluation">Evaluation</Link>
        </nav>
        <div className="nav-actions">
          <Link className="language-link" href="/ar" lang="ar">
            العربية
          </Link>
          <Link className="button button-small button-dark" href="/signin">
            Sign in
          </Link>
        </div>
      </div>
    </header>
  );
}
