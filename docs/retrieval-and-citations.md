# Retrieval and citations

GulfDocs indexes page-confined chunks in PostgreSQL. Every chunk carries its workspace,
document, page, language, parser version, token estimate, generated `tsvector`, and a
768-dimension embedding. Both retrieval branches apply workspace and document predicates before
ranking.

The lexical branch uses PostgreSQL `simple` text search after removing a small set of English and
Arabic question words. The semantic branch uses pgvector cosine distance and rejects weak matches.
Reciprocal-rank fusion combines the independent rankings without treating their raw scores as
comparable. Context assembly keeps chunk page numbers and stops at the configured character limit.

The answer provider receives only the bounded retrieved context. Returned citations are checked
against the retrieved page set; an answer citing another page is rejected. When neither branch
provides adequate evidence, the API stores and returns the explicit unsupported response without a
citation.

## Bilingual limitations

PostgreSQL's `simple` configuration preserves Arabic tokens but does not provide Arabic stemming or
English morphological normalization. This avoids applying an incorrect English stemmer to mixed
text, but lexical recall is lower for inflected forms and spelling variants. Semantic retrieval can
recover some paraphrases, although embedding quality varies with document layout and language. The
evaluation suite must report English, Arabic, and bilingual retrieval slices separately.
