"use client";

import { LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export function AppBar({ title }: { title: string }) {
  const { user, signOut } = useAuth();
  const router = useRouter();

  return (
    <div className="app-bar">
      <div>
        <Link href="/dashboard" className="app-breadcrumb">
          Workspace
        </Link>
        <h1>{title}</h1>
      </div>
      <div className="identity-chip">
        <UserRound size={16} aria-hidden="true" />
        <span>{user?.displayName}</span>
        <button
          type="button"
          aria-label="Sign out"
          onClick={async () => {
            await signOut();
            router.replace("/signin");
          }}
        >
          <LogOut size={15} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
