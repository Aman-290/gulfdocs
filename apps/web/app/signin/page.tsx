import type { Metadata } from "next";
import { LockKeyhole } from "lucide-react";
import { SignInForm } from "@/components/sign-in-form";

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
          Access the private workspace with Firebase Authentication. Local
          builds expose a clearly labelled development adapter.
        </p>
        <SignInForm />
        <small>
          Your private files and extracted values never appear in the public
          synthetic demo.
        </small>
      </section>
    </main>
  );
}
