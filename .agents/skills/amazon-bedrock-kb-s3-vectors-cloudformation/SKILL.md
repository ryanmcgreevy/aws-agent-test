---
name: amazon-bedrock-kb-s3-vectors-cloudformation
description: >-
  Build Amazon Bedrock Knowledge Bases with CloudFormation using an in-stack
  S3 Vectors bucket/index for retrieval storage and a separate S3 bucket for
  source documents. Use when creating or troubleshooting Knowledge Base
  infrastructure, S3 Vectors resources, Bedrock DataSource definitions,
  ingestion sync, or CloudFormation validation/deployment failures around KBs.
version: 1
---

# Amazon Bedrock Knowledge Bases with S3 Vectors and CloudFormation

## Overview

Use this skill when you want a Bedrock Knowledge Base defined in CloudFormation
with:

- an S3 Vectors bucket/index for vector storage
- a separate S3 bucket for source documents
- a Bedrock DataSource tied to the knowledge base
- a manual ingestion/sync step after documents are uploaded

This is the correct architecture for CloudFormation-managed RAG on Bedrock.

## Golden Path

1. Confirm AWS CLI v2 is available and the target region has Bedrock access.
2. Create or reuse a source-document S3 bucket.
3. Create an S3 Vectors bucket using AWS::S3Vectors::VectorBucket.
4. Create an S3 Vectors index using AWS::S3Vectors::Index.
5. Create the Bedrock Knowledge Base using AWS::Bedrock::KnowledgeBase.
6. Create a Bedrock DataSource using AWS::Bedrock::DataSource and point it at the source-document bucket.
7. Upload documents into the source bucket under the configured prefix.
8. Start an ingestion job to sync documents into the knowledge base.

## CloudFormation Blueprint

### 1. S3 source bucket

Use a normal AWS::S3::Bucket for the documents the knowledge base ingests.
This bucket is not the vector store.

Recommended settings:

- PublicAccessBlockConfiguration with all four values set to true
- BucketEncryption enabled
- VersioningConfiguration enabled
- bucket policy that allows Bedrock read access only as needed

### 2. S3 Vectors bucket

Create the vector bucket with:

- Type: AWS::S3Vectors::VectorBucket
- VectorBucketName

Keep the name lowercase, unique in the account/region, and 3-63 characters.

### 3. S3 Vectors index

Create the index with:

- Type: AWS::S3Vectors::Index
- VectorBucketArn or VectorBucketName
- IndexName
- DataType: float32
- Dimension: must match the embedding model output
- DistanceMetric: usually cosine

Recommended pattern:

- use !Ref to the AWS::S3Vectors::VectorBucket resource for VectorBucketArn
- use !Ref to the AWS::S3Vectors::Index resource for IndexArn when wiring the knowledge base

### 4. Bedrock Knowledge Base

Create the KB with:

- Type: AWS::Bedrock::KnowledgeBase
- KnowledgeBaseConfiguration.Type: VECTOR
- VectorKnowledgeBaseConfiguration.EmbeddingModelArn
- RoleArn
- StorageConfiguration.Type: S3_VECTORS
- StorageConfiguration.S3VectorsConfiguration

Important:

- use only one selector for the index wiring
- if your template starts failing schema validation, remove the duplicate index selector and keep the ARN-based reference

### 5. Bedrock DataSource

Create the data source with:

- Type: AWS::Bedrock::DataSource
- Name
- KnowledgeBaseId
- DataSourceConfiguration.Type: S3
- DataSourceConfiguration.S3Configuration.BucketArn
- DataSourceConfiguration.S3Configuration.InclusionPrefixes

The data source points to the source bucket, not the S3 Vectors bucket.

## Correct IAM Shape

Create a role for Bedrock to assume and grant it what each part needs:

- KB role trust policy: bedrock.amazonaws.com
- KB role permissions for S3 Vectors operations on the vector bucket/index
- KB role permissions for S3 read access on the source bucket
- if using KMS, grant the required KMS permissions to the relevant service

Use confused-deputy protection where possible:

- aws:SourceAccount
- aws:SourceArn when the service supports it

## Ingestion Flow

The source bucket is only the input location. Uploading a file to S3 does not make it searchable immediately.

The actual flow is:

1. Upload document to source bucket/prefix
2. Run Bedrock ingestion for the data source
3. Bedrock chunks and embeds the document
4. Bedrock stores vectors in the S3 Vectors bucket/index
5. Retrieval uses the KB against the vector store

## Common Failure Modes

### Using the wrong resource type

Do not use AWS::Bedrock::Agent::KnowledgeBase.
Use AWS::Bedrock::KnowledgeBase.

### Treating a normal S3 bucket as the vector store

The vector store must be an S3 Vectors resource, not AWS::S3::Bucket.

### Region mismatch

The S3 Vectors bucket/index must be in the same region as the knowledge base.

### Duplicate index selectors

If StorageConfiguration.S3VectorsConfiguration includes both IndexArn and IndexName, CloudFormation/Bedrock validation may fail. Prefer a single ARN-based reference in CloudFormation templates.

### Wrong source bucket

The Bedrock DataSource must point at the source-document bucket, not the vector bucket.

### No sync after upload

If documents are uploaded but search returns nothing, run ingestion again.

## Suggested CloudFormation Pattern

```yaml
Resources:
  SourceBucket:
    Type: AWS::S3::Bucket

  VectorBucket:
    Type: AWS::S3Vectors::VectorBucket
    Properties:
      VectorBucketName: my-vector-bucket

  VectorIndex:
    Type: AWS::S3Vectors::Index
    Properties:
      VectorBucketArn: !Ref VectorBucket
      IndexName: my-index
      DataType: float32
      Dimension: 1024
      DistanceMetric: cosine

  KnowledgeBaseRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole

  KnowledgeBase:
    Type: AWS::Bedrock::KnowledgeBase
    Properties:
      Name: my-kb
      RoleArn: !GetAtt KnowledgeBaseRole.Arn
      KnowledgeBaseConfiguration:
        Type: VECTOR
        VectorKnowledgeBaseConfiguration:
          EmbeddingModelArn: arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0
      StorageConfiguration:
        Type: S3_VECTORS
        S3VectorsConfiguration:
          VectorBucketArn: !Ref VectorBucket
          IndexArn: !Ref VectorIndex

  DataSource:
    Type: AWS::Bedrock::DataSource
    Properties:
      Name: my-source
      KnowledgeBaseId: !Ref KnowledgeBase
      DataSourceConfiguration:
        Type: S3
        S3Configuration:
          BucketArn: !GetAtt SourceBucket.Arn
          InclusionPrefixes:
            - kb-source/
```

## Validation Checklist

Before deploying:

1. Validate the template schema.
2. Check that the KB role can read the source bucket.
3. Check that the KB role can operate on the S3 Vectors bucket/index.
4. Confirm the embedding dimension matches the model.
5. Confirm the source bucket and vector bucket are in the same region as the KB.

After deploying:

1. Upload a test document to the source prefix.
2. Start an ingestion job.
3. Confirm the KB has a data source and ingestion succeeds.
4. Run a retrieval query against the KB.

## When to Use This Skill

Use this skill when the user asks to:

- create a Bedrock Knowledge Base with CloudFormation
- use S3 Vectors as the KB vector store
- use S3 as the data source for KB ingestion
- troubleshoot KB schema validation or region errors
- wire a knowledge base into an existing CloudFormation pipeline

## Do Not Use This Skill For

- generic Bedrock model invocation
- plain S3 object-storage workflows
- OpenSearch-based vector stores
- non-CloudFormation deployments unless the user explicitly wants an equivalent

## Reference Files

- [Knowledge base CloudFormation](references/knowledge-base-cloudformation.md)
- [Knowledge base ingestion](references/knowledge-base-ingestion.md)
- [Knowledge base troubleshooting](references/knowledge-base-troubleshooting.md)
- [Notes](references/notes.md)
- [Commands](references/commands.md)
