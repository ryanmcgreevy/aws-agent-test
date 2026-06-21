# Bedrock Knowledge Base Integration Guide

This document explains the S3-backed Bedrock Knowledge Base that has been added to your CloudFormation stack.

## Overview

Your deployment now includes:

- **S3 Vector Bucket**: Stores vector embeddings and documents for semantic search
- **Bedrock Knowledge Base**: Provides vector search capabilities with Titan embeddings
- **IAM Roles**: Properly configured permissions for the Knowledge Base and your agent

## Stack Resources

### New CloudFormation Resources

1. **VectorBucket** - S3 bucket for storing documents and vectors
   - Auto-generated name: `agent-vectors-{AccountId}-{Region}`
   - Versioning enabled for audit trails
   - Server-side encryption (AES256)
   - Secure transport enforced

2. **VectorBucketPolicy** - S3 bucket policy
   - Allows Bedrock service principal read access
   - Denies unencrypted transport

3. **KnowledgeBaseRole** - IAM service role
   - Assumed by Bedrock
   - Permissions to read from S3 vector bucket

4. **BedrockKnowledgeBase** - The knowledge base resource
   - Vector-based (semantic search)
   - Uses Titan Embed Text v2 embeddings
   - Backed by S3 storage

5. **AgentCoreExecutionRole** - Updated with
   - New `bedrock:Retrieve` permission for accessing the knowledge base

## Stack Parameters

You can customize the knowledge base when deploying by setting:

```yaml
KnowledgeBaseName: agent-knowledge-base  # Knowledge base name
KnowledgeBaseDescription: "Vector-backed knowledge base for the Strands agent"
```

## Outputs

After the stack deploys, you'll have these outputs:

- `KnowledgeBaseId`: The knowledge base ID (use for API calls)
- `KnowledgeBaseArn`: Full ARN of the knowledge base
- `VectorBucketName`: S3 bucket name for documents/vectors
- `KnowledgeBaseRoleArn`: Role ARN for the knowledge base

## Adding Documents to Your Knowledge Base

### Via AWS Console

1. Go to AWS Bedrock → Knowledge bases
2. Select your knowledge base
3. Click "Data source" → create new data source pointing to your S3 bucket
4. Upload documents (PDF, TXT, JSON, etc.)
5. Sync to generate embeddings

### Via AWS CLI

```bash
# List your knowledge base
aws bedrock-agent list-knowledge-bases

# Create a data source (replace KNOWLEDGE_BASE_ID)
aws bedrock-agent create-data-source \
  --knowledge-base-id KNOWLEDGE_BASE_ID \
  --name my-documents \
  --data-source-configuration s3Configuration='{bucketArn="arn:aws:s3:::YOUR_BUCKET"}'

# Ingest documents (ingests from S3)
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id KNOWLEDGE_BASE_ID \
  --data-source-id DATA_SOURCE_ID
```

### Via Python/Boto3

```python
import boto3

bedrock_agent = boto3.client('bedrock-agent')
s3 = boto3.client('s3')

# Upload a document to the vector bucket
s3.put_object(
    Bucket='agent-vectors-{AccountId}-{Region}',
    Key='documents/my-document.txt',
    Body=b'Your document content here'
)

# Create data source
response = bedrock_agent.create_data_source(
    knowledgeBaseId='YOUR_KB_ID',
    name='my-documents',
    dataSourceConfiguration={
        's3Configuration': {
            'bucketArn': 'arn:aws:s3:::agent-vectors-{AccountId}-{Region}'
        }
    }
)

# Start ingestion job
bedrock_agent.start_ingestion_job(
    knowledgeBaseId='YOUR_KB_ID',
    dataSourceId=response['dataSource']['dataSourceId']
)
```

## Using the Knowledge Base with Your Agent

### Retrieve Documents

In your agent code, use `bedrock:Retrieve` to search the knowledge base:

```python
import boto3
from typing import Optional

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

def retrieve_from_knowledge_base(
    knowledge_base_id: str,
    query: str,
    max_results: int = 5
) -> dict:
    """Retrieve documents from the knowledge base based on a query."""
    
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': max_results,
                'overrideSearchType': 'SEMANTIC'
            }
        },
        text=query
    )
    
    return response

# Example usage
results = retrieve_from_knowledge_base(
    knowledge_base_id='YOUR_KB_ID',
    query='How does feature X work?'
)

for result in results['retrievalResults']:
    print(f"Score: {result['score']}")
    print(f"Content: {result['content']['text']}")
```

### Integrate with Strands Agent

Update your agent to use the knowledge base as a context source:

```python
from strands import Agent
from strands.models import BedrockModel
import os
import boto3

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")

model = BedrockModel(model_id=MODEL_ID, max_tokens=2048)
bedrock_runtime = boto3.client('bedrock-agent-runtime')

def get_context_from_kb(query: str) -> str:
    """Retrieve context from knowledge base."""
    if not KNOWLEDGE_BASE_ID:
        return ""
    
    try:
        response = bedrock_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3
                }
            },
            text=query
        )
        
        context_parts = []
        for result in response.get('retrievalResults', []):
            context_parts.append(result['content']['text'])
        
        return "\n\n".join(context_parts)
    except Exception as e:
        print(f"Error retrieving from KB: {e}")
        return ""

agent = Agent(
    model=model,
    system_prompt=(
        "You are a helpful assistant. "
        "Use the provided context to answer questions accurately."
    ),
    tools=[]
)

def run(user_input: str) -> str:
    """Invoke the agent with RAG context from the knowledge base."""
    
    # Retrieve context from knowledge base
    context = get_context_from_kb(user_input)
    
    # Enhance prompt with context
    if context:
        enhanced_prompt = f"""
Use this context to help answer the question:

{context}

User question: {user_input}
"""
    else:
        enhanced_prompt = user_input
    
    response = agent(enhanced_prompt)
    return str(response)
```

## Pipeline Integration

The knowledge base stack resources are now part of your CloudFormation stack. When you update `pipeline.yml`, the stack update will be triggered automatically via CodePipeline.

### Trigger Pipeline Changes

The pipeline triggers on changes to `pipeline.yml`. To test the knowledge base:

1. Commit any changes to `pipeline.yml`
2. Push to your branch
3. Pipeline automatically detects the change and updates the stack
4. Wait for the Deploy stage to complete

### Monitor Stack Updates

```bash
# Watch the stack update
aws cloudformation describe-stack-events \
  --stack-name YOUR_STACK_NAME \
  --query 'StackEvents[0:10]' \
  --output table
```

## Security Best Practices

1. **Encryption**: Vector bucket uses AES256 encryption at rest
2. **Transport**: Enforced HTTPS/SecureTransport for all S3 operations
3. **IAM**: Granular permissions using service principals
4. **Source Account**: All cross-service permissions restricted to your account
5. **Public Access**: Bucket public access completely blocked

## Troubleshooting

### Knowledge Base Not Finding Documents

1. Check if documents were uploaded to the vector bucket
2. Verify ingestion job completed successfully
3. Check Knowledge Base data source status in console

### Retrieve Returns Empty Results

1. Verify the knowledge base has a data source with ingested documents
2. Check CloudWatch logs for ingestion errors
3. Confirm the knowledge base ID is correct

### Permission Denied Errors

1. Verify the `KnowledgeBaseRole` has S3 permissions
2. Check S3 bucket policy allows Bedrock service
3. Confirm agent execution role has `bedrock:Retrieve` permission

## Cost Considerations

- **Vector Storage**: ~$0.02 per 1M vectors
- **Retrievals**: ~$0.01 per retrieval request
- **Ingestion**: ~$0.10 per 1M tokens processed

See [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) for details.

## Next Steps

1. **Deploy the Stack**: Push `pipeline.yml` changes to trigger CodePipeline
2. **Add Documents**: Upload documents to the vector bucket
3. **Ingest Data**: Create data source and run ingestion job
4. **Test Retrieval**: Verify knowledge base searches work
5. **Integrate Agent**: Update your agent code to use the knowledge base
6. **Monitor**: Track usage and costs in CloudWatch
