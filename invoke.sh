#!/usr/bin/env bash
# invoke.sh — quick test helper for AgentCore runtime invocation.
#
# Usage:
#   ./invoke.sh "What is 2 + 2?"
#   ./invoke.sh --session-id my-session "Continue our conversation"
#
# Reads configuration from .env when present.

set -euo pipefail
export AWS_PAGER=""

# Load .env as data (not code) to avoid executing arbitrary shell content.
load_env_file() {
  local env_file=".env"
  local line key value

  [[ -f "${env_file}" ]] || return 0

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%$'\r'}"

    if [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    if [[ ! "${line}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      echo "Invalid .env entry: ${line}" >&2
      exit 1
    fi

    key="${line%%=*}"
    value="${line#*=}"

    if [[ "${value}" =~ ^\".*\"$ ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value}" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "${key}=${value}"
  done < "${env_file}"
}

load_env_file

: "${AWS_REGION:?Set AWS_REGION in .env}"
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID in .env}"

# Prefer explicit ARN, else runtime ID.
AGENT_RUNTIME_ARN="${AGENT_RUNTIME_ARN:-}"
AGENT_RUNTIME_ID="${AGENT_RUNTIME_ID:-}"
AGENT_ENDPOINT_NAME="${AGENT_ENDPOINT_NAME:-prod}"
SESSION_ID="${SESSION_ID:-}"

if [[ -z "${AGENT_RUNTIME_ARN}" && -z "${AGENT_RUNTIME_ID}" ]]; then
  echo "Set AGENT_RUNTIME_ARN or AGENT_RUNTIME_ID in .env"
  exit 1
fi

PROMPT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session-id)
      SESSION_ID="${2:-}"
      shift 2
      ;;
    --session-id=*)
      SESSION_ID="${1#*=}"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./invoke.sh [--session-id SESSION_ID] [prompt text]

If no prompt text is provided, a default greeting prompt is used.
EOF
      exit 0
      ;;
    *)
      if [[ -z "${PROMPT}" ]]; then
        PROMPT="$1"
      else
        PROMPT+=" $1"
      fi
      shift
      ;;
  esac
done

PROMPT="${PROMPT:-Hello from invoke.sh. Please reply with a short greeting.}"

payload_file="$(mktemp)"
response_file="$(mktemp)"

cleanup() {
  rm -f "${payload_file}" "${response_file}"
}
trap cleanup EXIT

python3 - <<'PY' "${payload_file}" "${PROMPT}" "${SESSION_ID}"
import json, sys
payload_path = sys.argv[1]
prompt = sys.argv[2]
session_id = sys.argv[3]
with open(payload_path, "w", encoding="utf-8") as f:
  payload = {"input": prompt}
  if session_id:
    payload["session_id"] = session_id
  json.dump(payload, f)
PY

cmd=(
  aws bedrock-agentcore invoke-agent-runtime
  --content-type application/json
  --accept application/json
  --qualifier "${AGENT_ENDPOINT_NAME}"
  --payload "fileb://${payload_file}"
  --region "${AWS_REGION}"
)

if [[ -n "${AGENT_RUNTIME_ARN}" ]]; then
  cmd+=(--agent-runtime-arn "${AGENT_RUNTIME_ARN}")
else
  cmd+=(--agent-runtime-arn "${AGENT_RUNTIME_ID}" --account-id "${AWS_ACCOUNT_ID}")
fi

cmd+=("${response_file}")

echo "Invoking runtime (${AGENT_ENDPOINT_NAME})..."
"${cmd[@]}" > /dev/null

echo "Response:"
cat "${response_file}"
echo ""
