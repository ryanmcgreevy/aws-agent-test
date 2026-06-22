#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy the Strands agent to AgentCore Runtime.
#
# Prerequisites:
#   - AWS CLI v2 configured with valid credentials
#   - Docker with buildx support (docker buildx version)
#   - An ECR repository and an IAM execution role (see .env.example)
#
# Usage:
#   cp .env.example .env   # fill in values
#   ./deploy.sh

set -euo pipefail

# Prevent AWS CLI from invoking an interactive pager in automation.
export AWS_PAGER=""

# Load .env as data (not code) to avoid executing arbitrary shell content.
load_env_file() {
  local env_file=".env"
  local line key value

  [[ -f "${env_file}" ]] || return 0

  while IFS= read -r line || [[ -n "${line}" ]]; do
    line="${line%$'\r'}"

    # Skip comments and blank lines.
    if [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    # Enforce strict KEY=VALUE format to keep parsing predictable.
    if [[ ! "${line}" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      echo "Invalid .env entry: ${line}" >&2
      exit 1
    fi

    key="${line%%=*}"
    value="${line#*=}"

    # Remove optional wrapping quotes for convenience.
    if [[ "${value}" =~ ^\".*\"$ ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "${value}" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "${key}=${value}"
  done < "${env_file}"
}

load_env_file

# ── Validate required environment variables ──────────────────────────────────
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID in .env}"
: "${AWS_REGION:?Set AWS_REGION in .env}"
: "${ECR_REPO_NAME:?Set ECR_REPO_NAME in .env}"
: "${AGENTCORE_EXECUTION_ROLE_ARN:?Set AGENTCORE_EXECUTION_ROLE_ARN in .env}"
: "${AGENT_RUNTIME_NAME:?Set AGENT_RUNTIME_NAME in .env}"

# Optional networking mode: PUBLIC (default) or VPC.
AGENT_NETWORK_MODE="${AGENT_NETWORK_MODE:-PUBLIC}"
SESSION_BUCKET_NAME="${SESSION_BUCKET_NAME:-}"
SESSION_BUCKET_PREFIX="${SESSION_BUCKET_PREFIX:-sessions}"

# AgentCore runtime names must match: [a-zA-Z][a-zA-Z0-9_]{0,47}
AGENT_RUNTIME_NAME_SANITIZED="$(echo "${AGENT_RUNTIME_NAME}" | sed 's/[^a-zA-Z0-9_]/_/g')"
if [[ ! "${AGENT_RUNTIME_NAME_SANITIZED}" =~ ^[a-zA-Z] ]]; then
  AGENT_RUNTIME_NAME_SANITIZED="A_${AGENT_RUNTIME_NAME_SANITIZED}"
fi
AGENT_RUNTIME_NAME_SANITIZED="${AGENT_RUNTIME_NAME_SANITIZED:0:48}"

if [[ "${AGENT_RUNTIME_NAME_SANITIZED}" != "${AGENT_RUNTIME_NAME}" ]]; then
  echo "Note: AGENT_RUNTIME_NAME adjusted to '${AGENT_RUNTIME_NAME_SANITIZED}' to meet AgentCore naming rules"
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
IMAGE_TAG="${ECR_URI}:latest"

NETWORK_CONFIGURATION_JSON='{"networkMode":"PUBLIC"}'
if [[ "${AGENT_NETWORK_MODE}" == "VPC" ]]; then
  : "${AGENT_SUBNET_IDS:?Set AGENT_SUBNET_IDS (comma-separated) when AGENT_NETWORK_MODE=VPC}"
  : "${AGENT_SECURITY_GROUP_IDS:?Set AGENT_SECURITY_GROUP_IDS (comma-separated) when AGENT_NETWORK_MODE=VPC}"

  IFS=',' read -r -a _subnets <<< "${AGENT_SUBNET_IDS}"
  IFS=',' read -r -a _sgs <<< "${AGENT_SECURITY_GROUP_IDS}"

  _subnets_json=""
  for s in "${_subnets[@]}"; do
    s_trimmed="$(echo "${s}" | xargs)"
    [[ -n "${s_trimmed}" ]] && _subnets_json+="\"${s_trimmed}\"," 
  done
  _subnets_json="[${_subnets_json%,}]"

  _sgs_json=""
  for g in "${_sgs[@]}"; do
    g_trimmed="$(echo "${g}" | xargs)"
    [[ -n "${g_trimmed}" ]] && _sgs_json+="\"${g_trimmed}\"," 
  done
  _sgs_json="[${_sgs_json%,}]"

  NETWORK_CONFIGURATION_JSON="{\"networkMode\":\"VPC\",\"networkModeConfig\":{\"subnets\":${_subnets_json},\"securityGroups\":${_sgs_json}}}"
fi

ENVIRONMENT_VARIABLES_JSON='{}'
if [[ -n "${SESSION_BUCKET_NAME}" ]]; then
  ENVIRONMENT_VARIABLES_JSON="{\"SESSION_BUCKET_NAME\":\"${SESSION_BUCKET_NAME}\",\"SESSION_BUCKET_PREFIX\":\"${SESSION_BUCKET_PREFIX}\"}"
fi

echo "==> [1/7] Verifying tools"
aws --version
docker buildx version

echo "==> [2/7] Ensuring ECR repository exists"
aws ecr describe-repositories \
  --repository-names "${ECR_REPO_NAME}" \
  --region "${AWS_REGION}" > /dev/null 2>&1 \
|| aws ecr create-repository \
     --repository-name "${ECR_REPO_NAME}" \
     --region "${AWS_REGION}" \
     --image-scanning-configuration scanOnPush=true

echo "==> [3/7] Authenticating Docker to ECR"
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin \
      "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> [4/7] Ensuring ARM64 emulation is available"
BINFMT_IMAGE="${BINFMT_IMAGE:-tonistiigi/binfmt@sha256:400a4873b838d1b89194d982c45e5fb3cda4593fbfd7e08a02e76b03b21166f0}"
docker run --privileged --rm "${BINFMT_IMAGE}" --install arm64 > /dev/null

echo "==> [5/7] Creating/selecting buildx builder"
if docker buildx inspect agentcore-builder > /dev/null 2>&1; then
  docker buildx use agentcore-builder
else
  docker buildx create --name agentcore-builder --driver docker-container --use
fi
docker buildx inspect --bootstrap > /dev/null

echo "==> [6/7] Building and pushing ARM64 image"
docker buildx build \
  --platform linux/arm64 \
  --push \
  -t "${IMAGE_TAG}" \
  .

echo "==> [7/7] Creating or updating AgentCore Runtime"
set +e
RUNTIME_RESPONSE=$(aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name "${AGENT_RUNTIME_NAME_SANITIZED}" \
  --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${IMAGE_TAG}\"}}" \
  --role-arn "${AGENTCORE_EXECUTION_ROLE_ARN}" \
  --network-configuration "${NETWORK_CONFIGURATION_JSON}" \
  --protocol-configuration '{"serverProtocol":"HTTP"}' \
  --environment-variables "${ENVIRONMENT_VARIABLES_JSON}" \
  --region "${AWS_REGION}" \
  --output json 2>&1)
CREATE_EXIT=$?
set -e

if [[ $CREATE_EXIT -eq 0 ]]; then
  RUNTIME_ID=$(echo "${RUNTIME_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['agentRuntimeId'])")
  echo "Runtime created: ${RUNTIME_ID}"
else
  if echo "${RUNTIME_RESPONSE}" | grep -q "ConflictException"; then
    echo "Runtime name already exists; looking up existing runtime ID by name"
    EXISTING_ID=$(aws bedrock-agentcore-control list-agent-runtimes \
      --region "${AWS_REGION}" \
      --query "agentRuntimes[?agentRuntimeName=='${AGENT_RUNTIME_NAME_SANITIZED}'].agentRuntimeId | [0]" \
      --output text)
    if [[ -z "${EXISTING_ID}" || "${EXISTING_ID}" == "None" || "${EXISTING_ID}" == "null" ]]; then
      echo "Conflict detected, but existing runtime ID could not be resolved. Aborting."
      echo "${RUNTIME_RESPONSE}"
      exit 1
    fi
    RUNTIME_ID="${EXISTING_ID}"
    echo "Adopted existing runtime: ${RUNTIME_ID}"
    
    echo "==> Updating runtime ${RUNTIME_ID} with latest container image"
    aws bedrock-agentcore-control update-agent-runtime \
      --agent-runtime-id "${RUNTIME_ID}" \
      --agent-runtime-artifact "{\"containerConfiguration\":{\"containerUri\":\"${IMAGE_TAG}\"}}" \
      --role-arn "${AGENTCORE_EXECUTION_ROLE_ARN}" \
      --network-configuration "${NETWORK_CONFIGURATION_JSON}" \
      --protocol-configuration '{"serverProtocol":"HTTP"}' \
      --environment-variables "${ENVIRONMENT_VARIABLES_JSON}" \
      --region "${AWS_REGION}"
  else
    echo "create-agent-runtime failed:"
    echo "${RUNTIME_RESPONSE}"
    exit 1
  fi
fi

echo "==> Waiting for runtime to become READY"
for i in {1..60}; do
  RUNTIME_STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id "${RUNTIME_ID}" \
    --region "${AWS_REGION}" \
    --query 'status' \
    --output text)

  echo "Runtime status: ${RUNTIME_STATUS} (attempt ${i}/60)"
  if [[ "${RUNTIME_STATUS}" == "READY" ]]; then
    break
  fi

  if [[ "${RUNTIME_STATUS}" == "FAILED" ]]; then
    echo "Runtime entered FAILED state. Aborting."
    exit 1
  fi

  sleep 10
done

if [[ "${RUNTIME_STATUS}" != "READY" ]]; then
  echo "Runtime did not become READY in time. Aborting endpoint creation."
  exit 1
fi

echo "==> Creating Runtime Endpoint"
ENDPOINT_RESPONSE=$(aws bedrock-agentcore-control create-agent-runtime-endpoint \
  --agent-runtime-id "${RUNTIME_ID}" \
  --name prod \
  --region "${AWS_REGION}" \
  --output json)

ENDPOINT_ID=$(echo "${ENDPOINT_RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id', d.get('endpointId', 'prod')))" 2>/dev/null || echo "prod")
echo "Endpoint created: ${ENDPOINT_ID}"

echo ""
echo "Deployment complete. Check endpoint status with:"
echo "  aws bedrock-agentcore-control get-agent-runtime-endpoint \\"
echo "    --agent-runtime-id ${RUNTIME_ID} \\"
echo "    --endpoint-name ${ENDPOINT_ID} \\" 
echo "    --region ${AWS_REGION}"
echo ""
echo "Endpoint is ready when status is READY."
