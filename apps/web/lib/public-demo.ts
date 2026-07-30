export type DemoField = {
  label: string;
  value: string;
  confidence: number;
  page: number;
};

export type DemoQuestion = {
  id: string;
  question: string;
  answer: string;
  page: number;
  excerpt: string;
};

export const publicDemo = {
  id: "demo-invoice-en-001",
  name: "Northstar Office Trading — Invoice INV-GD-1042",
  type: "Invoice",
  language: "English",
  status: "needs_review",
  synthetic: true,
  pages: 2,
  processedAt: "2026-07-30T08:15:00Z",
  fields: [
    {
      label: "Supplier",
      value: "Northstar Office Trading LLC",
      confidence: 0.99,
      page: 1,
    },
    {
      label: "Invoice number",
      value: "INV-GD-1042",
      confidence: 0.99,
      page: 1,
    },
    { label: "Issue date", value: "22 July 2026", confidence: 0.97, page: 1 },
    { label: "Currency", value: "AED", confidence: 0.99, page: 1 },
    { label: "Subtotal", value: "11,500.00", confidence: 0.96, page: 1 },
    { label: "VAT", value: "575.00", confidence: 0.95, page: 1 },
    { label: "Total", value: "12,862.50", confidence: 0.98, page: 1 },
  ] satisfies DemoField[],
  issue: {
    severity: "error",
    code: "TOTAL_MISMATCH",
    description: "Subtotal plus VAT equals AED 12,075.00, not AED 12,862.50.",
    action: "Confirm the printed total with the supplier before approval.",
    page: 1,
  },
  questions: [
    {
      id: "payment-terms",
      question: "What are the payment terms?",
      answer: "Payment is due within 30 days of the invoice date.",
      page: 2,
      excerpt: "Payment terms: Net 30 days from invoice date.",
    },
    {
      id: "total-check",
      question: "Does the printed total match the line items?",
      answer:
        "No. The printed total is AED 12,862.50, while subtotal plus VAT is AED 12,075.00.",
      page: 1,
      excerpt: "Subtotal AED 11,500.00 · VAT AED 575.00 · Total AED 12,862.50",
    },
    {
      id: "delivery-address",
      question: "What is the delivery address?",
      answer:
        "I could not find enough evidence in the selected document to answer that question reliably.",
      page: 1,
      excerpt: "No delivery address was retrieved from the invoice.",
    },
  ] satisfies DemoQuestion[],
} as const;
