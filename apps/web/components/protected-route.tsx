"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { useAuth } from "@/lib/auth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { loading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/signin");
  }, [loading, router, user]);

  if (loading || !user) {
    return (
      <main id="main-content" className="app-loading" aria-live="polite">
        <LoaderCircle className="spin" aria-hidden="true" />
        <p>
          {loading
            ? "Restoring your secure session…"
            : "Redirecting to sign in…"}
        </p>
      </main>
    );
  }
  return children;
}
