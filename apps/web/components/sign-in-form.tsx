"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound, Mail } from "lucide-react";
import { useAuth } from "@/lib/auth";

export function SignInForm() {
  const auth = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localName, setLocalName] = useState("reviewer");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<void> | void) {
    setBusy(true);
    setError(null);
    try {
      await action();
      router.push("/dashboard");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Authentication failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (auth.loading) return <p aria-live="polite">Restoring session…</p>;

  return (
    <div className="signin-options">
      {error ? (
        <div className="form-error" role="alert">
          {error}
        </div>
      ) : null}
      {auth.firebaseConfigured ? (
        <>
          <button
            className="button button-primary full-button"
            disabled={busy}
            onClick={() => run(auth.signInGoogle)}
          >
            <KeyRound size={17} /> Continue with Google
          </button>
          <div className="form-divider">
            <span>or use email</span>
          </div>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              minLength={6}
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <div className="signin-actions">
            <button
              className="button button-primary"
              disabled={busy || !email || password.length < 6}
              onClick={() =>
                run(() => auth.signInEmail(email, password, false))
              }
            >
              <Mail size={16} /> Sign in
            </button>
            <button
              className="button button-secondary"
              disabled={busy || !email || password.length < 6}
              onClick={() => run(() => auth.signInEmail(email, password, true))}
            >
              Create account
            </button>
          </div>
        </>
      ) : process.env.NODE_ENV !== "production" ? (
        <div className="development-auth">
          <p>
            <strong>Local development adapter</strong>
            <br />
            Uses the API’s deterministic development token verifier. It is
            unavailable in production.
          </p>
          <label>
            Test identity
            <input
              value={localName}
              pattern="[a-zA-Z0-9_-]+"
              onChange={(event) => setLocalName(event.target.value)}
            />
          </label>
          <button
            className="button button-primary full-button"
            disabled={busy || !localName}
            onClick={() => run(() => auth.signInLocal(localName))}
          >
            Enter local workspace
          </button>
        </div>
      ) : (
        <div className="form-error" role="alert">
          Firebase configuration is missing. Authentication is closed.
        </div>
      )}
    </div>
  );
}
