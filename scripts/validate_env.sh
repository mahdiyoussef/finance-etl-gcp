#!/usr/bin/env bash
# validate_env.sh — Pre-flight environment check before GCP deployment.
set -euo pipefail

ERRORS=0

check() {
  local name="$1"
  local value="${!name:-}"
  if [ -z "$value" ]; then
    echo "  MISSING: $name"
    ERRORS=$((ERRORS + 1))
  else
    echo "  OK:      $name"
  fi
}

echo "==> Checking required environment variables..."
check GCP_PROJECT_ID
check TF_VAR_billing_account_id

echo ""
echo "==> Checking required tools..."

tools=("python3" "terraform" "gcloud" "dbt")
for tool in "${tools[@]}"; do
  if command -v "$tool" &>/dev/null; then
    echo "  OK:      $tool ($(command -v "$tool"))"
  else
    echo "  MISSING: $tool"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "==> $ERRORS check(s) failed. Fix the above before deploying."
  exit 1
else
  echo "==> All checks passed."
fi

