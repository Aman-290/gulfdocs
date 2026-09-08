# ADR 0008: Firebase Authentication

- Status: Accepted

Firebase supplies managed Google/email identity compatible with App Hosting. FastAPI verifies ID tokens and maps subjects to workspace memberships. Authorization stays in GulfDocs; identity alone never grants document access.
