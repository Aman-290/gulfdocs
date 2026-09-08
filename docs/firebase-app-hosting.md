# Firebase App Hosting rollout

Firebase App Hosting is the only frontend deployment owner. GitHub Actions runs quality gates and deploys the API/worker; it intentionally contains no frontend deploy command. This prevents competing rollouts.

The Firebase project and Web app can be configured idempotently with:

```bash
PROJECT_ID=replace-with-project infrastructure/scripts/configure-firebase.sh
```

Then enable Google and Email/Password in Firebase Console → Authentication → Sign-in method. Copy only the public Web SDK fields into the App Hosting environment. Set `NEXT_PUBLIC_API_BASE_URL` to the deployed API origin and replace the placeholder in `apps/web/apphosting.yaml`; no backend secret may use a `NEXT_PUBLIC_` name.

When a GitHub repository exists, open Firebase Console → App Hosting → Get started, connect the approved repository, select `apps/web` as the app root, choose the production branch, and require the `CI` GitHub check before merge. The initial connection is intentionally manual because it authorizes Firebase's GitHub app for a repository/organization; Terraform must not guess that scope.

If console connection is unavailable, verify the current supported CLI flow with `firebase apphosting:backends:create --help` and create a single backend for the same app root. Do not add traditional Firebase Hosting or Vercel as a fallback. Record the backend ID and generated URL only after a successful rollout.
