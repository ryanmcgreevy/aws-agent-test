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
  -d '{"input":"what is 2+2?"}'
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

- Builds a JSON payload (`{"input": "..."}`)
- Calls `aws bedrock-agentcore invoke-agent-runtime`
- Prints response body

## Runtime Behavior Notes

- Endpoint network mode can be `PUBLIC` or `VPC` (set via deployment config)
- Even with `PUBLIC` network mode, requests still require AWS auth + IAM permission to invoke
- Runtime sessions have lifecycle controls (`idleRuntimeSessionTimeout`, `maxLifetime`) that can be tuned for cost/latency tradeoffs

## Bedrock Knowledge Base (RAG Integration)

This project now includes a **Bedrock Knowledge Base** backed by S3 vectors. This enables Retrieval Augmented Generation (RAG) — your agent can search a collection of documents for context before answering questions.

### Knowledge Base Architecture

The CloudFormation stack (`pipeline.yml`) creates:

- **Vector Storage Bucket** (`agent-vectors-{AccountId}-{Region}`): S3 bucket for storing documents and embeddings
- **Knowledge Base Role**: IAM role for Bedrock to access S3
- **Bedrock Knowledge Base**: Vector-based knowledge base using Titan Embed Text v2 embeddings
- **Agent Execution Role Updates**: Added `bedrock:Retrieve` permissions

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

1. **Upload documents to the vector bucket** (any format: PDF, TXT, JSON, Markdown, etc.):

```bash
aws s3 cp my-document.pdf s3://agent-vectors-{AccountId}-{Region}/documents/
```

2. **Create a data source in the knowledge base** (AWS Console or CLI):

```bash
# Get the Knowledge Base ID from stack outputs
KB_ID=$(aws cloudformation describe-stacks \
  --stack-name agent-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
  --output text)

# Create data source
aws bedrock-agent create-data-source \
  --knowledge-base-id $KB_ID \
  --name my-documents \
  --data-source-configuration s3Configuration='{bucketArn="arn:aws:s3:::agent-vectors-{AccountId}-{Region}"}'
```

3. **Start ingestion to generate embeddings**:

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id <data-source-id>
```

### Using the Knowledge Base with Your Agent

The agent code (`agent.py`) is already updated to support RAG:

```python
# Retrieve context from knowledge base
def retrieve_from_knowledge_base(query: str, max_results: int = 3) -> str:
    # Returns relevant document chunks based on semantic similarity
    ...

# The run() function automatically augments prompts with KB context
def run(user_input: str) -> str:
    context = retrieve_from_knowledge_base(user_input)
    augmented_input = f"Context: {context}\n\nQuestion: {user_input}"
    return agent(augmented_input)
```

To enable the knowledge base at runtime, set the `KNOWLEDGE_BASE_ID` environment variable in your deployment configuration.

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