# ADR 0006: Hybrid retrieval over vector-only search

- Status: Accepted

PostgreSQL full-text search preserves exact identifiers/terms while pgvector captures semantic similarity. Reciprocal-rank fusion combines them without score calibration. Bilingual tokenization remains limited and evaluation must be sliced by language.
