# Bedrock Managed Knowledge Base Integration Guide

This document explains the managed Bedrock Knowledge Base setup in this repository.

## Overview

Your deployment includes a Bedrock managed knowledge base and automation around ingestion:

- **Source S3 Bucket**: Stores source documents under a prefix (default: `kb-source/`)
- **Bedrock Managed Knowledge Base**: `Type: MANAGED` with AWS-managed embeddings
- **Managed Data Source Automation**: Deploy stage ensures the managed S3 connector exists
- **Auto-Sync Ingestion**: EventBridge + Lambda start ingestion jobs on new uploads
- **Agent Retrieval Permissions**: Agent execution role can call `bedrock:Retrieve`

This replaces the previous self-managed S3 Vectors setup.

## Stack Resources

### CloudFormation Resources

1. **VectorBucket**
   - Purpose: Source document bucket (not a vector-store resource)
   - Name pattern: `agent-vectors-{AccountId}-{Region}`
   - Security: encryption at rest, public access block, secure transport enforcement
   - EventBridge notifications enabled for object-created events

2. **VectorBucketPolicy**
   - Allows Bedrock service read access to source documents
   - Denies insecure transport (`aws:SecureTransport=false`)

3. **KnowledgeBaseRole**
   - Service role assumed by Bedrock
   - Grants read/list access to the source S3 bucket

4. **BedrockKnowledgeBase**
   - Type: `MANAGED`
   - Managed embedding model (`EmbeddingModelType: MANAGED`)

5. **KnowledgeBaseAutoSyncFunction** and **KnowledgeBaseAutoSyncRule**
   - Trigger on S3 object creation under `KnowledgeBaseSourcePrefix`
   - Lambda resolves data source by name (`list_data_sources`) and starts ingestion

6. **CodeBuildDeployProject + buildspec-deploy.yml logic**
   - Ensures managed KB data source exists
   - Creates the data source if missing using `MANAGED_KNOWLEDGE_BASE_CONNECTOR`
   - Starts an initial ingestion when a new data source is created

## Stack Parameters

Current KB-related parameters:

```yaml
KnowledgeBaseName: agent-knowledge-base
KnowledgeBaseDescription: "Managed knowledge base for the Strands agent"
KnowledgeBaseDataSourceName: agent-kb-source
KnowledgeBaseSourcePrefix: kb-source/
```

Removed from the stack during migration:

- `KnowledgeBaseVectorIndexName`
- `KnowledgeBaseVectorBucketName`
- `KnowledgeBaseVectorDimension`

## Outputs

After deployment, use these outputs:

- `KnowledgeBaseId`
- `KnowledgeBaseArn`
- `KnowledgeBaseDataSourceName`
- `KnowledgeBaseSourceBucketName`
- `KnowledgeBaseSourceBucketArn`
- `KnowledgeBaseRoleArn`
- `KnowledgeBaseAutoSyncFunctionName`
- `KnowledgeBaseAutoSyncRuleArn`

## Document Ingestion Flow

### Automatic Path (recommended)

1. Upload files to the source bucket prefix:

```bash
aws s3 cp my-document.pdf s3://agent-vectors-{AccountId}-{Region}/kb-source/
```

2. EventBridge receives object-created event.
3. Auto-sync Lambda verifies the key matches `KnowledgeBaseSourcePrefix`.
4. Lambda finds data source ID by configured name.
5. Lambda calls `start-ingestion-job`.

### Manual Path (troubleshooting)

```bash
# Get KB ID from CloudFormation output
KB_ID=$(aws cloudformation describe-stacks \
  --stack-name agent-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
  --output text)

# Get data source name from stack output
DS_NAME=$(aws cloudformation describe-stacks \
  --stack-name agent-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseDataSourceName`].OutputValue' \
  --output text)

# Resolve data source ID
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id "$KB_ID" \
  --query "dataSourceSummaries[?name=='$DS_NAME'].dataSourceId | [0]" \
  --output text)

# Start ingestion manually
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id "$KB_ID" \
  --data-source-id "$DS_ID" \
  --description "Manual re-sync"
```

## Deploy/Pipeline Behavior

Deploy stage (`buildspec-deploy.yml`) now does two things:

1. Deploys AgentCore runtime/endpoint as before
2. Ensures managed KB data source exists:
   - `list-data-sources`
   - `create-data-source` if missing (S3 managed connector)
   - `start-ingestion-job` once on creation

This means first deployment after migration bootstraps the data source automatically.

## Using the KB from Agent Code

No special managed-KB code path is needed in the app. Retrieval API is the same:

```python
response = bedrock_agent_runtime.retrieve(
    knowledgeBaseId=KNOWLEDGE_BASE_ID,
    retrievalConfiguration={
        "vectorSearchConfiguration": {
            "numberOfResults": 3,
            "overrideSearchType": "SEMANTIC",
        }
    },
    text=query,
)
```

The app expects `KNOWLEDGE_BASE_ID` in environment variables. In this repo, CloudFormation injects it into deployment configuration.

## Security Notes

- S3 source bucket enforces TLS and blocks public access
- Bedrock role uses least-privilege bucket read permissions
- Auto-sync Lambda is scoped to knowledge-base and data-source ARNs
- Agent execution role grants `bedrock:Retrieve` for KB access

## Troubleshooting

### Upload occurred but no ingestion started

1. Check EventBridge rule is enabled (`KnowledgeBaseAutoSyncRuleArn`)
2. Confirm object key starts with `KnowledgeBaseSourcePrefix` (default `kb-source/`)
3. Check Lambda logs for `data_source_not_found`
4. Verify data source exists with expected name:

```bash
aws bedrock-agent list-data-sources --knowledge-base-id "$KB_ID"
```

### Ingestion fails

1. Describe latest ingestion jobs:

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id "$KB_ID" \
  --data-source-id "$DS_ID"
```

2. Inspect job details:

```bash
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id "$KB_ID" \
  --data-source-id "$DS_ID" \
  --ingestion-job-id <job-id>
```

3. Confirm Bedrock role can read source bucket and objects.

### Retrieval returns empty results

1. Ensure ingestion jobs complete successfully
2. Validate that uploaded files are in the configured prefix
3. Test with broader user queries and increased `numberOfResults`

## Migration Notes

This repository previously used a self-managed KB backed by S3 Vectors. The managed migration removes vector-store resource management and avoids metadata-size constraints previously encountered in S3Vectors ingestion.

## Next Steps

1. Deploy the updated stack and pipeline
2. Confirm deploy stage creates/validates the managed data source
3. Upload test files to `kb-source/`
4. Verify auto-sync starts ingestion and completes successfully
5. Test end-to-end agent retrieval quality
