import type { Metadata } from "next";
import { Dashboard } from "@/components/dashboard";
import { ProtectedRoute } from "@/components/protected-route";

export const metadata: Metadata = { title: "Workspace" };

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
