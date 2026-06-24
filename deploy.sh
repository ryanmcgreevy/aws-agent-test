#!/usr/bin/env bash
# deploy.sh — Bootstrap the CloudFormation stack that owns deployment.

set -euo pipefail

export AWS_PAGER=""

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
PIPELINE_STACK_NAME="${PIPELINE_STACK_NAME:-agent-pipeline}"
PIPELINE_TEMPLATE_FILE="${PIPELINE_TEMPLATE_FILE:-pipeline.yml}"

aws --version >/dev/null

echo "==> Deploying CloudFormation stack ${PIPELINE_STACK_NAME}"
aws cloudformation deploy \
  --stack-name "${PIPELINE_STACK_NAME}" \
  --template-file "${PIPELINE_TEMPLATE_FILE}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "${AWS_REGION}"

echo ""
echo "CloudFormation bootstrap complete. Authorize the CodeStar connection, then let CodePipeline handle subsequent builds and deployments."
