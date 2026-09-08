# Operations runbook

Always select the intended project explicitly and avoid printing secrets. Start with request/correlation ID, document ID, processing run ID, task ID, and a narrow log time range.

## Processing incidents

- **Failed processing:** inspect `failure_category`, run status, object metadata, and worker logs; correct configuration before using the authorized retry endpoint. Non-retryable corrupt/password-protected files require a replacement upload.
- **Stuck queued document:** inspect the Tasks queue and task name stored on the processing run. Confirm queue is RUNNING and worker IAM/audience match; redelivery is safe because processing is idempotent.
- **Duplicate delivery:** do not delete results. Verify the second invocation reports replay and that only one final extraction/run attempt exists.
- **Expired upload:** create a new presign request with a new idempotency key; never lengthen an old signed URL.
- **Gemini quota/provider error:** check bounded retries and model/region. Pause new processing or use fake evaluation; never relabel fake results as live quality.

## Platform incidents

- **Migration failure:** stop rollout, preserve the error, inspect `alembic current/history`, and fix forward with a compatible migration. Do not force a destructive downgrade on production data.
- **Neon exhaustion:** verify pooled URL, reduce API/worker concurrency, inspect pool metrics, and terminate leaked sessions. Keep Cloud Run maximums conservative.
- **Firebase token errors:** confirm project/audience, server clock, authorized domains, and client config. Never bypass verification.
- **Cloud Run cold starts:** correlate startup latency and request duration; do not raise minimum instances without an explicit cost decision.
- **App Hosting failed rollout:** inspect build logs/config, keep the previous healthy rollout serving, fix on a branch, and rerun CI.
- **GCS denial:** verify bucket name, uniform access, signing permission, runtime service account, and object key. Never grant `allUsers`.
- **Tasks 401/403:** compare target URL, custom audience, invoker email, Run Invoker binding, and API `actAs` permission.
- **High log volume:** identify event/category, reduce repetition or sampling without removing security/audit essentials; 30-day retention limits accumulation.
- **Cost alert:** inspect billing by SKU, pause queues/runtime if appropriate, reduce retained data/builds/logs, and remember alerts do not cap spending.

## Rollback

List revisions and route 100% traffic to a known-good API/worker revision:

```bash
gcloud run revisions list --service SERVICE --region "$REGION" --project "$PROJECT_ID"
gcloud run services update-traffic SERVICE --to-revisions KNOWN_GOOD=100 --region "$REGION" --project "$PROJECT_ID"
```

Roll back the frontend from Firebase App Hosting rollout history. Database changes must remain backward compatible with both revisions.

## Secret rotation and deletion

Add a new Secret Manager version, deploy/test consumers, then disable the old version. Never download service-account keys. For user deletion, authorize the workspace, delete live documents/objects, execute retention purge, remove Firebase identity as a separately audited step, and account for provider backup retention.

## Teardown

Export only required non-sensitive evidence, disable traffic/queues, and review a Terraform destroy plan. The document/state buckets have deletion safeguards and require deliberate emptying; destroying the GCP project or billing configuration is outside repository automation.
