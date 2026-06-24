# AWS Strands + AgentCore Sandbox

This repository is a **personal testing and learning project** for:

- [AWS Strands SDK](https://strandsagents.com/)
- Amazon Bedrock AgentCore Runtime

It is intentionally small and practical, designed to help me learn how to:

1. Build a basic Strands agent in Python
2. Wrap it with FastAPI using an HTTP runtime contract
3. Containerize for ARM64
4. Deploy to AgentCore Runtime
5. Invoke the deployed endpoint from the AWS CLI

## Project Status

This project is currently functioning as a working end-to-end learning setup:

- Local API app runs via FastAPI
- ARM64 image builds and pushes to ECR
- AgentCore Runtime deploys and endpoint can be invoked

## Important Note

This is **not production-ready** code. It is for experimentation, validation, and learning AWS deployment workflows.

## Repository Layout

- `agent.py`: Defines the Strands agent and `run()` function
- `main.py`: FastAPI app exposing health and invoke routes
- `requirements.txt`: Python dependencies
- `Dockerfile`: ARM64 container build for AgentCore
- `deploy.sh`: Local build + push + deploy helper script
- `invoke.sh`: Quick test invoke script for deployed runtime
- `.env.example`: Environment variable template
- `pipeline.yml`: CloudFormation template for CI/CD pipeline
- `buildspec-build.yml`: CodeBuild buildspec for Docker image build and push
- `buildspec-deploy.yml`: CodeBuild buildspec for AgentCore runtime/endpoint deployment
- `ui.html`: Web-based testing UI for the agent (local and remote modes)

## Testing UI

A minimal web-based testing interface is included for quick experimentation and debugging during development.

### Running the UI

1. Start the FastAPI server:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8080
   ```

2. Open your browser to `http://localhost:8080/`

### Features

The UI provides:
- **Chat-like interface** with message history
- **Session management** — agent sessions persist across multiple messages
- **Local mode** — test your agent running locally (default)
- **Remote mode** — test the deployed AgentCore Runtime endpoint (when configured)
- **Mode toggle** — switch between local and remote testing in real-time
- **Debug panel** — view raw request/response JSON, latency, and message metrics
- **Responsive design** — works on desktop and mobile

### Local Testing

By default, the UI connects to the FastAPI server running locally. Simply type messages and chat with your agent.

### Remote Testing

To test against your deployed AgentCore Runtime endpoint:

1. Deploy your agent using `./deploy.sh`
   ```bash
   ./deploy.sh
   ```
   The output will display your `AGENT_RUNTIME_ARN`, `AGENT_RUNTIME_ID`, and `AGENT_ENDPOINT_NAME`.

2. Set environment variables for the FastAPI server:
   ```bash
   # Either use AGENT_RUNTIME_ARN (recommended):
   export AGENT_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/my_agent-abc123"
   export AGENT_ENDPOINT_NAME="prod"
   
   # OR use AGENT_RUNTIME_ID + AWS_ACCOUNT_ID:
   export AGENT_RUNTIME_ID="my_agent-abc123"
   export AWS_ACCOUNT_ID="123456789012"
   export AGENT_ENDPOINT_NAME="prod"
   
   # Optional (defaults to us-east-1):
   export AWS_REGION="us-east-1"
   ```

3. Restart the FastAPI server (so it picks up the new environment variables)

4. Reload the UI in your browser — the "Remote" button will now be enabled

5. Click the "Remote" button to switch modes, then test your deployed agent

**Security Note:** AWS credentials are handled server-side only. No credentials are stored in the UI or transmitted to the browser. The FastAPI server uses your AWS credentials from environment variables, IAM role, or `~/.aws/credentials` to authenticate with AgentCore.

## Prerequisites

- Python 3.12+
- AWS CLI v2 configured with credentials
- Docker with `buildx`
- Bedrock model access enabled in your AWS region
- IAM execution role for AgentCore runtime with at least:
  - `bedrock:InvokeModel`
  - `bedrock:InvokeModelWithResponseStream`
  - `ecr:GetAuthorizationToken`
  - `ecr:BatchGetImage`
  - `ecr:GetDownloadUrlForLayer`

If you enable session persistence, the runtime execution role also needs access to the session bucket:

- `s3:ListBucket`
- `s3:GetBucketLocation`
- `s3:GetObject`
- `s3:GetObjectVersion`
- `s3:PutObject`
- `s3:DeleteObject`

## Execution Role IAM Permissions

The runtime execution role (for example `AgentCoreExecutionRole`) should include these permissions.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBedrockModelInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowEcrAuthToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowEcrImagePull",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "arn:aws:ecr:<region>:<account-id>:repository/<repo-name>"
    }
  ]
}
```

For least privilege, scope ECR permissions to the exact repository and scope Bedrock permissions to only the model or inference profile ARNs you use.

## Local Development

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run locally:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

Quick local check:

```bash
curl -s -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"input":"what is 2+2?","session_id":"demo-session"}'
```

If session persistence is configured, include a `session_id` to continue the same conversation:

```bash
curl -s -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"input":"remember this","session_id":"demo-session"}'
```

## Configure Environment

Copy and edit env values:

```bash
cp .env.example .env
```

Set required fields in `.env`:

- `AWS_ACCOUNT_ID`
- `AWS_REGION`
- `ECR_REPO_NAME`
- `AGENTCORE_EXECUTION_ROLE_ARN`
- `AGENT_RUNTIME_NAME`

After deployment, also set either:

- `AGENT_RUNTIME_ID` (recommended), or
- `AGENT_RUNTIME_ARN`

And endpoint qualifier:

- `AGENT_ENDPOINT_NAME` (default `prod`)

For local session persistence tests, set:

- `SESSION_BUCKET_NAME`
- `SESSION_BUCKET_PREFIX` (optional, defaults to `sessions`)

If `SESSION_BUCKET_NAME` is not set, the agent falls back to local file-backed sessions using:

- `LOCAL_SESSION_STORAGE_DIR` (optional, defaults to `.sessions`)

## Deploy to AgentCore

Run:

```bash
./deploy.sh
```

What `deploy.sh` does:

1. Loads `.env`
2. Verifies AWS CLI and Docker buildx
3. Ensures ECR repo exists
4. Logs Docker into ECR
5. Builds and pushes ARM64 image
6. Creates AgentCore runtime with HTTP protocol
7. Waits for runtime `READY`
8. Creates endpoint (name `prod`)

## CI/CD Pipeline (CloudFormation + AWS CodePipeline)

This project includes an automated CI/CD pipeline defined in `pipeline.yml` (CloudFormation) that orchestrates build, test, and deployment of the agent.

### Pipeline Architecture

- **Source**: GitHub repository (via CodeStar Connections)
- **Build Stage**: AWS CodeBuild compiles the Dockerfile and pushes to ECR
- **Deploy Stage**: AWS CodeBuild runs `bedrock-agentcore-control` commands to update the runtime and endpoint

### Initial Setup

1. Deploy the CloudFormation stack:

```bash
aws cloudformation deploy \
  --stack-name agent-pipeline \
  --template-file pipeline.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

2. Retrieve the CloudStar Connections ARN from stack outputs and authorize GitHub:

```bash
aws cloudformation describe-stacks \
  --stack-name agent-pipeline \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`GitHubConnectionArn`].OutputValue' \
  --output text
```

3. Go to [AWS CodePipeline Settings > Connections](https://console.aws.amazon.com/codesuite/settings/connections) in the AWS Console and authorize the pending GitHub App connection.

### Pipeline Triggers

Once the connection is authorized, the pipeline automatically triggers on:
- Push to the `master` branch
- Changes to source files or CI/CD configuration

### Build Stage

The build stage (`buildspec-build.yml`):

- Authenticates Docker to ECR
- Builds a multi-stage Dockerfile targeting ARM64
- Pushes images tagged with the commit short-SHA and `latest`
- Exports `imageUri.txt` artifact for the deploy stage

### Deploy Stage

The deploy stage (`buildspec-deploy.yml`):

- Reads the built image URI from the build artifact
- Checks SSM for an existing runtime ID
- **First run**: Creates AgentCore runtime or adopts existing runtime if name conflict
- **Subsequent runs**: Updates runtime with new image
- Waits for runtime to become `READY`
- Creates or updates the endpoint

### Local Deployment vs. Pipeline

Both `deploy.sh` (local) and the pipeline use identical conflict-handling logic:

- If a runtime with the same name already exists, both adopt it and update with the new image
- If no endpoint exists, both create one
- If endpoint exists, both update it to the latest runtime version

You can use either method interchangeably; the pipeline is useful for automated deployments on repository changes.

## Invoke Deployed Runtime

Use:

```bash
./invoke.sh "what is 2+2?"
```

This script:

- Builds a JSON payload (`{"input": "...", "session_id": "..."}` when provided)
- Calls `aws bedrock-agentcore invoke-agent-runtime`
- Prints response body

Pass a session ID to reuse conversation state:

```bash
./invoke.sh --session-id demo-session "What did I just ask you?"
```

## Runtime Behavior Notes

- Endpoint network mode can be `PUBLIC` or `VPC` (set via deployment config)
- Even with `PUBLIC` network mode, requests still require AWS auth + IAM permission to invoke
- Runtime sessions have lifecycle controls (`idleRuntimeSessionTimeout`, `maxLifetime`) that can be tuned for cost/latency tradeoffs

## Session Persistence

The agent can persist conversation state using either:

- Strands `S3SessionManager` when `SESSION_BUCKET_NAME` is configured
- Strands `FileSessionManager` for local testing when `SESSION_BUCKET_NAME` is not configured

### Session Flow

- The caller may send `session_id` in the invoke payload.
- If no `session_id` is provided, the agent generates one and returns it in the response.
- Reusing the same `session_id` restores the prior conversation from S3.

### Runtime Environment

The runtime reads these environment variables:

- `SESSION_BUCKET_NAME` - S3 bucket that stores session data
- `SESSION_BUCKET_PREFIX` - optional key prefix for session objects
- `LOCAL_SESSION_STORAGE_DIR` - local directory for file-backed sessions when S3 settings are not provided

The CloudFormation pipeline stack creates the S3 bucket and injects the S3 values into the runtime.
For local development without S3, only `LOCAL_SESSION_STORAGE_DIR` is needed (or use the default `.sessions`).

### Invoke Example

```bash
./invoke.sh --session-id demo-session "continue our previous conversation"
```

The API response includes the effective `session_id`, so clients can reuse it on the next turn.

## Bedrock Knowledge Base (RAG Integration)

This project includes a **Bedrock Managed Knowledge Base**. This enables Retrieval Augmented Generation (RAG) without managing vector-store infrastructure directly.

### Knowledge Base Architecture

The CloudFormation stack (`pipeline.yml`) creates:

- **Source Document Bucket** (`agent-vectors-{AccountId}-{Region}`): S3 bucket that stores source files under a configurable prefix (`kb-source/` by default)
- **Knowledge Base Role**: IAM role for Bedrock managed knowledge base to read source documents from S3
- **Bedrock Managed Knowledge Base**: `Type: MANAGED` with AWS-managed embedding model
- **Auto-Sync Lambda + EventBridge Rule**: Starts ingestion jobs when new source files are uploaded
- **Deploy Stage Data Source Automation**: Pipeline deploy step ensures the managed S3 connector data source exists and triggers initial ingestion when first created
- **Agent Execution Role Updates**: Includes `bedrock:Retrieve` permissions for KB retrieval

### Configuration

You can customize the knowledge base when deploying:

```bash
aws cloudformation deploy \
  --stack-name agent-pipeline \
  --template-file pipeline.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    KnowledgeBaseName=my-custom-kb \
    KnowledgeBaseDescription="My custom knowledge base" \
  --region us-east-1
```

### Adding Documents

1. **Upload documents to the source prefix** (any format supported by Bedrock connectors, such as PDF, TXT, JSON, Markdown):

```bash
aws s3 cp my-document.pdf s3://agent-vectors-{AccountId}-{Region}/kb-source/
```

2. **Auto-sync handles ingestion for uploads**:

- EventBridge detects object creation
- Lambda resolves the data source by name and calls `start-ingestion-job`

3. **Optional manual sync commands** (for troubleshooting or bulk refresh):

```bash
# Get the Knowledge Base ID from stack outputs
KB_ID=$(aws cloudformation describe-stacks \
  --stack-name agent-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
  --output text)

# Discover managed data source ID by configured name
DS_NAME=$(aws cloudformation describe-stacks \
  --stack-name agent-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseDataSourceName`].OutputValue' \
  --output text)

DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id "$KB_ID" \
  --query "dataSourceSummaries[?name=='$DS_NAME'].dataSourceId | [0]" \
  --output text)

# Start ingestion manually if needed
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id "$KB_ID" \
  --data-source-id "$DS_ID"
```

### Using the Knowledge Base with Your Agent

The agent code (`agent.py`) is already updated to support RAG:

```python
# Retrieve context from knowledge base
def retrieve_from_knowledge_base(query: str, max_results: int = 3) -> str:
    # Returns relevant document chunks based on semantic similarity
    ...

# The run() function automatically augments prompts with KB context
# and returns the response plus the effective session_id.
def run(user_input: str, session_id: str | None = None) -> tuple[str, str]:
    context = retrieve_from_knowledge_base(user_input)
    augmented_input = f"Context: {context}\n\nQuestion: {user_input}"
  return agent(augmented_input), session_id or "generated-session-id"
```

To enable the knowledge base at runtime, set the `KNOWLEDGE_BASE_ID` environment variable in your deployment configuration. In this project, the value is injected automatically by the CloudFormation pipeline stack.

For comprehensive documentation, see [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md).

## Learning Goals / Future Ideas

- Add tool usage in Strands (`strands-agents-tools`)
- Add CI smoke test for endpoint readiness + invoke success
- Add structured logging and basic observability checks
- Add least-privilege IAM policy docs for runtime and caller

## Cleanup (Optional)

If you want to tear down resources later, remove:

- AgentCore runtime endpoint
- AgentCore runtime
- ECR repository/images
- IAM role/policies created for this test

---

Personal note: this repository exists to learn by doing, iterate quickly, and document practical AWS Strands + AgentCore deployment patterns.