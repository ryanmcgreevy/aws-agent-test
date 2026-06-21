# Bedrock Knowledge Base Troubleshooting

## Overview

Use this reference when CloudFormation or Bedrock rejects a KB stack, or when the KB deploys but ingestion or retrieval does not work.

## Common Error Patterns

### Invalid resource type

Symptoms:

- CloudFormation validation fails before deployment
- Type name errors mention a 4-part resource type

Fix:

- Use `AWS::Bedrock::KnowledgeBase`
- Do not use `AWS::Bedrock::Agent::KnowledgeBase`

### Invalid S3 Vectors schema

Symptoms:

- StorageConfiguration validation fails
- Bedrock complains about subschema matches

Fix:

- In `S3VectorsConfiguration`, use only one index selector
- Prefer `IndexArn` only
- Do not mix `IndexArn` and `IndexName` in the KB storage block

### Wrong vector store type

Symptoms:

- Bedrock says the vector store is invalid or in the wrong region
- The stack uses a normal `AWS::S3::Bucket` as the vector store

Fix:

- Create `AWS::S3Vectors::VectorBucket`
- Create `AWS::S3Vectors::Index`
- Wire the KB to those S3 Vectors resources

### Region mismatch

Symptoms:

- Bedrock says the vector store must be in the same region

Fix:

- Keep the KB, S3 Vectors bucket, and S3 Vectors index in the same region
- Avoid cross-region bucket/index wiring for the KB

### Data source points to the wrong bucket

Symptoms:

- KB creates, but ingestion never finds the source documents

Fix:

- The `AWS::Bedrock::DataSource` must point to the source-document S3 bucket
- The KB vector bucket is not the document source

### Ingestion appears to do nothing

Symptoms:

- Data source exists
- KB exists
- Retrieval returns empty or irrelevant results

Fix:

- Upload documents under the configured inclusion prefix
- Start an ingestion job manually
- Wait for the ingestion job to complete
- Re-run ingestion after document updates

## Failure Triage Checklist

1. Validate the template with CloudFormation before deployment
2. Review the latest stack event or change-set failure reason
3. Confirm the resource type names exactly match AWS docs
4. Confirm the vector index dimensions match the embedding model
5. Confirm the source bucket and vector store are in the same region
6. Confirm the KB role can read the source bucket and operate on the vector store

## Useful Diagnostics

- CloudFormation validation errors usually indicate a template schema issue
- Bedrock `Resource handler returned message` errors often indicate a runtime config mismatch
- If a stack update worked once and then fails later, compare the current template to the last known good version for resource-property drift

## Decision Guide

- If the error is about YAML/JSON structure or invalid property names, fix the template
- If the error is about permissions, region, or resource state, fix the AWS environment
- If the error is about missing documents or empty results, fix ingestion and verify the source bucket contents
