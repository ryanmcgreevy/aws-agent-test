# Bedrock KB Notes

## Short Checklist

- Use `AWS::S3Vectors::VectorBucket` and `AWS::S3Vectors::Index` for vector storage.
- Use a separate `AWS::S3::Bucket` for source documents.
- Use `AWS::Bedrock::KnowledgeBase` for the KB resource.
- Use `AWS::Bedrock::DataSource` for the source bucket.
- Keep the source bucket, vector bucket, vector index, and KB in the same region.
- Set the KB embedding dimension to match the embedding model output.
- Prefer `IndexArn` in `S3VectorsConfiguration` to avoid schema ambiguity.
- Upload documents to the source bucket, then run ingestion; uploads alone do not make content searchable.

## Do Not Do This

- Do not use `AWS::Bedrock::Agent::KnowledgeBase`.
- Do not use a normal `AWS::S3::Bucket` as the vector store.
- Do not set both `IndexArn` and `IndexName` in the KB storage configuration.
- Do not point the data source at the vector bucket.
- Do not assume ingestion happens automatically after upload.

## Common Repair Steps

1. Validate the CloudFormation template.
2. Check that the KB role can read the source bucket.
3. Check that the KB role can operate on the S3 Vectors bucket and index.
4. Confirm the source bucket contains files under the configured prefix.
5. Run ingestion again and wait for `COMPLETE`.
6. If retrieval is empty, recheck the index dimension and region.
