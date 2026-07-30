import { AlertTriangle, Check, FileText, Search } from "lucide-react";

export function ProductPreview() {
  return (
    <div
      className="product-preview"
      aria-label="Preview of an invoice review in GulfDocs"
    >
      <div className="preview-topbar">
        <div className="preview-dots">
          <i />
          <i />
          <i />
        </div>
        <span>Invoice review</span>
        <b>Needs review</b>
      </div>
      <div className="preview-body">
        <div className="preview-document">
          <div className="document-title">
            <FileText size={15} /> INVOICE
          </div>
          <div className="document-lines">
            <i />
            <i />
            <i />
          </div>
          <div className="document-table">
            <span>Service</span>
            <span>AED 8,500</span>
            <span>Support</span>
            <span>AED 3,000</span>
          </div>
          <div className="document-total">
            <span>Total</span>
            <strong>AED 12,862.50</strong>
          </div>
          <div className="citation-box">Page 1 · source region</div>
        </div>
        <div className="preview-panel">
          <div className="preview-tabs">
            <b>Fields</b>
            <span>Issues</span>
            <span>Ask</span>
          </div>
          <label>
            Invoice number <strong>INV-GD-1042</strong>
          </label>
          <label>
            Supplier <strong>Northstar Office Trading</strong>
          </label>
          <label>
            Total{" "}
            <strong>
              AED 12,862.50 <em>98%</em>
            </strong>
          </label>
          <div className="issue">
            <AlertTriangle size={15} />
            <span>
              <b>Total mismatch</b>Expected AED 12,075.00
            </span>
          </div>
          <div className="preview-search">
            <Search size={14} />
            <span>Ask this document…</span>
          </div>
          <button tabIndex={-1}>
            <Check size={14} /> Ready after correction
          </button>
        </div>
      </div>
    </div>
  );
}
