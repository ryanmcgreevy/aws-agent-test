# Bedrock Knowledge Base Ingestion and Sync

## Overview

Use this reference when documents have already been uploaded to the source bucket and you need to ingest or re-ingest them into the knowledge base.

The key idea:

- uploading files to S3 does not make them searchable
- ingestion must be run to chunk, embed, and sync documents into the KB

## Ingestion Flow

1. Upload documents to the source bucket/prefix
2. Start an ingestion job for the Bedrock data source
3. Wait for the ingestion job to finish
4. Query the KB to verify results

## Useful Commands

### Start ingestion

```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id>
```

### Check ingestion status

```bash
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id <kb-id> \
  --data-source-id <data-source-id> \
  --ingestion-job-id <job-id>
```

Wait until status is `COMPLETE`. If it is `FAILED`, check the failure details before retrying.

### Query the KB

Retrieve raw results:

```bash
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id <kb-id> \
  --retrieval-query '{"text":"<query>"}'
```

Retrieve and generate an answer:

```bash
aws bedrock-agent-runtime retrieve-and-generate \
  --input '{"text":"<query>"}' \
  --retrieve-and-generate-configuration '{"type":"KNOWLEDGE_BASE","knowledgeBaseConfiguration":{"knowledgeBaseId":"<kb-id>","modelArn":"<model-arn>"}}'
```

## Source Bucket Layout

Recommended default layout:

- `kb-source/` for ingested source documents
- optional subfolders for topics or document sets

Examples:

- `kb-source/policies/`
- `kb-source/manuals/`
- `kb-source/faq/`

## Ingestion Failure Checks

If ingestion fails or returns no useful results, check:

1. The source bucket contains documents under the inclusion prefix
2. The KB role has `s3:GetObject` and `s3:ListBucket`
3. The document format is supported
4. The S3 Vectors index dimension matches the embedding model
5. The data source and KB are in the same region
6. The vector bucket/index are accessible and not partially configured

## Verification Checklist

After ingestion:

1. Run a retrieval query for a known phrase from a document
2. Confirm the query returns results with relevance scores
3. Try 2-3 different queries to check retrieval quality
4. If results are empty, verify the ingestion job completed successfully

## Operational Guidance

- Re-run ingestion after adding or modifying documents
- Keep the source bucket prefix stable to avoid accidental broad scans
- Use the data source name to separate multiple document sets if needed

## Common Mistakes

- Forgetting to run ingestion after uploading files
- Pointing the data source at the S3 Vectors bucket instead of the source bucket
- Using a KB vector index dimension that does not match the embedding model
- Assuming ingestion is automatic just because files are present in S3
