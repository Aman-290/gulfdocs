# Synthetic document fixtures

Every PDF in this directory is generated from [`evaluation/cases.json`](../../evaluation/cases.json) and contains fictional data created only for GulfDocs testing and evaluation.

Regenerate the corpus with:

```bash
uv run python -m evaluation.generate_documents
```

Do not add real invoices, contracts, personal data, customer files, or private-specification content here.
