# ADR 0005: Cloud Storage over PostgreSQL PDF blobs

- Status: Accepted

PDF bytes belong in a private object store with direct signed uploads, lifecycle rules, and object-level IAM. PostgreSQL stores opaque keys and metadata. This avoids large transactions/backups but requires coordinated object/database deletion.
