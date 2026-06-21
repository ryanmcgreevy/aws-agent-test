# Bedrock Knowledge Base Commands

## CloudFormation Deployment

### Validate the template

```bash
aws cloudformation validate-template \
  --template-body file://kb-template.yml \
  --region us-east-1
```

### Create the stack

```bash
aws cloudformation create-stack \
  --stack-name my-kb-stack \
  --template-body file://kb-template.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Update the stack

```bash
aws cloudformation update-stack \
  --stack-name my-kb-stack \
  --template-body file://kb-template.yml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Check stack status

```bash
aws cloudformation describe-stacks \
  --stack-name my-kb-stack \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus' \
  --output text
```

## Ingestion

### Start ingestion job

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id> \
  --region us-east-1
```

### Get ingestion job status

```bash
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id> \
  --ingestion-job-id <job-id> \
  --region us-east-1 \
  --query 'ingestionJob.status' \
  --output text
```

### List ingestion jobs

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id> \
  --region us-east-1
```

## Retrieval

### Retrieve documents

```bash
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id <kb-id> \
  --retrieval-query '{"text":"<your-question>"}' \
  --region us-east-1
```

### Retrieve and generate answer

```bash
aws bedrock-agent-runtime retrieve-and-generate \
  --input '{"text":"<your-question>"}' \
  --retrieve-and-generate-configuration '{
    "type":"KNOWLEDGE_BASE",
    "knowledgeBaseConfiguration":{
      "knowledgeBaseId":"<kb-id>",
      "modelArn":"arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
    }
  }' \
  --region us-east-1
```

## Knowledge Base Operations

### Get KB details

```bash
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id <kb-id> \
  --region us-east-1
```

### List data sources

```bash
aws bedrock-agent list-data-sources \
  --knowledge-base-id <kb-id> \
  --region us-east-1
```

### Get data source details

```bash
aws bedrock-agent get-data-source \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id> \
  --region us-east-1
```

## S3 Operations

### Upload documents to source bucket

```bash
aws s3 cp my-document.pdf \
  s3://my-source-bucket/kb-source/my-document.pdf
```

### List documents in source bucket

```bash
aws s3 ls s3://my-source-bucket/kb-source/ \
  --recursive
```

## Useful Queries

### Get KB ID from stack outputs

```bash
aws cloudformation describe-stacks \
  --stack-name my-kb-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
  --output text
```

### Get data source ID from stack outputs

```bash
aws cloudformation describe-stacks \
  --stack-name my-kb-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' \
  --output text
```

### Poll ingestion job until complete

```bash
kb_id=<kb-id>
ds_id=<data-source-id>
job_id=<job-id>

while true; do
  status=$(aws bedrock-agent get-ingestion-job \
    --knowledge-base-id $kb_id \
    --data-source-id $ds_id \
    --ingestion-job-id $job_id \
    --region us-east-1 \
    --query 'ingestionJob.status' \
    --output text)
  
  echo "Status: $status"
  
  if [[ "$status" == "COMPLETE" || "$status" == "FAILED" ]]; then
    break
  fi
  
  sleep 10
done
```
