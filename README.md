# AWS Strands + AgentCore Sandbox

This repository is a **personal testing and learning project** for:

- [AWS Strands SDK](https://strandsagents.com/)
- Amazon Bedrock AgentCore Runtime

It is intentionally small and practical, designed to help me learn how to:

1. Build a basic Strands agent in Python
2. Wrap it with FastAPI using an HTTP runtime contract
3. Trigger the CloudFormation + CodePipeline deployment flow
4. Invoke the deployed endpoint from the AWS CLI

## Project Status

This project is currently functioning as a working end-to-end learning setup:

- Local API app runs via FastAPI
- CodePipeline builds and deploys the runtime after stack bootstrap
- AgentCore Runtime endpoint can be invoked

## Important Note

This is **not production-ready** code. It is for experimentation, validation, and learning AWS deployment workflows.

## Repository Layout

- `agent.py`: Defines the Strands agent and `run()` function
- `main.py`: FastAPI app exposing health and invoke routes
- `requirements.txt`: Python dependencies
- `Dockerfile`: ARM64 container build used by the pipeline
- `deploy.sh`: CloudFormation bootstrap helper for the pipeline stack
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

1. Deploy the CloudFormation stack using `./deploy.sh`
   ```bash
   ./deploy.sh
   ```
  This creates the pipeline that builds the image and deploys the runtime.

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
- Bedrock model access enabled in your AWS region

Deployment and IAM are defined in `pipeline.yml`.

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

- `AWS_REGION`

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
2. Runs `aws cloudformation deploy` for `pipeline.yml`
3. Hands off builds and runtime deployment to CodePipeline

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

2. Retrieve the CodeStar Connections ARN from stack outputs and authorize GitHub:

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

This project uses an AWS Managed Knowledge Base for RAG retrieval.

Today, that managed knowledge base must be created and configured outside this CloudFormation stack (for example in the AWS Console or via CLI). The pipeline then references the existing knowledge base by ID and handles runtime wiring, data source sync, and retrieval integration.

For source document updates, the CloudFormation stack provisions an EventBridge rule and Lambda function that automatically start ingestion sync when new files are uploaded to the configured S3 knowledge base source prefix.

Once CloudFormation adds full support for managed knowledge base creation, this can move fully into IaC.

## Learning Goals / Future Ideas

- Add tool usage in Strands (`strands-agents-tools`)
- Add CI smoke test for endpoint readiness + invoke success
- Add structured logging and basic observability checks

## Cleanup (Optional)

If you want to tear down resources later, remove:

- AgentCore runtime endpoint
- AgentCore runtime
- ECR repository/images
- The CloudFormation stack and its pipeline resources

---

Personal note: this repository exists to learn by doing, iterate quickly, and document practical AWS Strands + AgentCore deployment patterns.