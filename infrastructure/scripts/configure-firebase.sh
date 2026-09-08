#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
APP_DISPLAY_NAME="${APP_DISPLAY_NAME:-gulfdocs-web}"

if ! firebase projects:list --json | grep -q "\"projectId\": \"${PROJECT_ID}\""; then
  firebase projects:addfirebase "${PROJECT_ID}" --non-interactive
fi

app_id="$(firebase apps:list WEB --project "${PROJECT_ID}" --json | \
  APP_DISPLAY_NAME="${APP_DISPLAY_NAME}" node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const j=JSON.parse(s);const a=(j.result||[]).find(x=>x.displayName===process.env.APP_DISPLAY_NAME);if(a)process.stdout.write(a.appId)})')"
if [[ -z "${app_id}" ]]; then
  app_id="$(firebase apps:create WEB "${APP_DISPLAY_NAME}" --project "${PROJECT_ID}" --json | \
    node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>process.stdout.write(JSON.parse(s).result.appId))')"
fi

firebase apps:sdkconfig WEB "${app_id}" --project "${PROJECT_ID}"
cat <<'EOF'

Firebase project and Web app are configured. Enable Google and Email/Password providers in
Firebase Console > Authentication > Sign-in method. App Hosting GitHub rollout ownership
requires a GitHub remote; follow docs/firebase-app-hosting.md after the repository is approved.
EOF
