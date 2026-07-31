import type { Metadata } from "next";
import { DocumentWorkspace } from "@/components/document-workspace";
import { ProtectedRoute } from "@/components/protected-route";

export const metadata: Metadata = { title: "Document review" };

export default async function DocumentPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  return (
    <ProtectedRoute>
      <DocumentWorkspace documentId={documentId} />
    </ProtectedRoute>
  );
}
