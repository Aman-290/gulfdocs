import type { Metadata } from "next";
import { Footer } from "@/components/footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "GulfDocs — Arabic-English document intelligence",
    template: "%s | GulfDocs",
  },
  description:
    "Extract, validate, review, and question synthetic business documents with page-level evidence.",
  applicationName: "GulfDocs",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <SiteHeader />
        {children}
        <Footer />
      </body>
    </html>
  );
}
