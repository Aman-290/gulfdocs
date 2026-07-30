import type { Metadata } from "next";
import { LockKeyhole } from "lucide-react";

export const metadata: Metadata = { title: "Sign in" };

export default function SignInPage() {
  return (
    <main id="main-content" className="auth-page shell">
      <section className="auth-card">
        <div className="auth-icon">
          <LockKeyhole size={24} />
        </div>
        <p className="kicker">Private workspace</p>
        <h1>Sign in to review your documents</h1>
        <p>
          Firebase Google and email authentication will be connected in Phase 2.
          The public synthetic demo is available now without an account.
        </p>
        <a className="button button-primary" href="/demo">
          Open public demo
        </a>
        <small>
          Authentication is not bypassed in development; automated tests use a
          deterministic auth adapter.
        </small>
      </section>
    </main>
  );
}
