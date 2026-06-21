# Bedrock Knowledge Base CloudFormation Build

## Overview

Use this reference when creating a Bedrock Knowledge Base in CloudFormation with:

- `AWS::S3Vectors::VectorBucket` for vector storage
- `AWS::S3Vectors::Index` for the vector index
- `AWS::S3::Bucket` for source documents
- `AWS::Bedrock::KnowledgeBase` for the KB itself
- `AWS::Bedrock::DataSource` for the source bucket integration

The vector store and the source bucket serve different purposes:

- **Source bucket**: documents that Bedrock ingests
- **S3 Vectors bucket/index**: embeddings used for retrieval

## Required Resources

### 1. Source bucket

Use a normal S3 bucket for documents.

Recommended properties:

- `BucketEncryption`
- `VersioningConfiguration`
- `PublicAccessBlockConfiguration`
- a bucket policy that allows Bedrock read access as needed

### 2. S3 Vectors bucket

Use:

```yaml
Type: AWS::S3Vectors::VectorBucket
Properties:
  VectorBucketName: my-vector-bucket
```

Notes:

- Name must be lowercase, 3-63 characters, account/region unique
- Do not use `AWS::S3::Bucket` for vector storage

### 3. S3 Vectors index

Use:

```yaml
Type: AWS::S3Vectors::Index
Properties:
  VectorBucketArn: !Ref VectorBucket
  IndexName: my-index
  DataType: float32
  Dimension: 1024
  DistanceMetric: cosine
```

Rules:

- `DataType` is currently `float32`
- `Dimension` must match the embedding model output
- `DistanceMetric` should usually be `cosine`
- `IndexArn` is returned by `!Ref` on the index resource

### 4. Bedrock Knowledge Base

Use:

```yaml
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
```

Important:

- Use only one index selector in `S3VectorsConfiguration`
- Prefer `IndexArn` to avoid schema ambiguity
- Keep the KB, vector bucket, and vector index in the same region

### 5. Bedrock DataSource

Use:

```yaml
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

Notes:

- The data source points to the source bucket, not the vector bucket
- `InclusionPrefixes` is the easiest way to scope documents for ingestion
- Changing the source bucket requires replacing the data source

## IAM Checklist

The KB service role should allow:

- `s3:GetObject`
- `s3:ListBucket`
- `s3:GetBucketLocation`
- `s3vectors:GetVectorBucket`
- `s3vectors:GetIndex`
- `s3vectors:ListIndexes`
- `s3vectors:ListVectors`
- `s3vectors:QueryVectors`
- `s3vectors:GetVectors`

Use `bedrock.amazonaws.com` as the trust principal and include `aws:SourceAccount` where possible.

## Template Validation Notes

If validation fails, check for these common mistakes:

- using `AWS::Bedrock::Agent::KnowledgeBase` instead of `AWS::Bedrock::KnowledgeBase`
- setting both `IndexArn` and `IndexName` on the KB storage config
- pointing the KB to a regular S3 bucket instead of a S3 Vectors bucket
- region mismatch between KB and vector store

## Minimal Skeleton

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
        Version: '2012-10-17'
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
