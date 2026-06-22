# Course Maps Index

## Collection Metadata
- document_type: collection_index
- schema_version: 1.0
- schema_path: data/course-maps/schema.md
- created_at: 2026-06-22
- updated_at: 2026-06-22
- source_system: local_course_maps_collection
- source_entity_type: collection_index
- collection_name: course-maps
- collection_path: data/course-maps
- document_count: 1
- purpose: Retrieval-friendly academic pathway documents for downstream RAG ingestion

## Documents
- document_id: ko-mathematics-bs-ey-fall-2025-and-beyond
  file_name: ko-mathematics-bs-ey-fall-2025-and-beyond.md
  pathway_name: KO- Mathematics BS - EY Fall 2025 and Beyond
  institution: Indiana University Kokomo
  program_code: KO-Mathematics BS-UGRD
  program_type: Bachelor of Science in Mathematics
  keywords:
    - mathematics
    - BS
    - Indiana University Kokomo
    - calculus
    - linear algebra
    - physics
    - upper-division mathematics
  summary: Four-year mathematics pathway with calculus, linear algebra and physics alternatives, upper-division mathematics requirement groups, science electives, and career preparation milestones.

## Ingestion Notes
- Each document in this directory is intended to be chunked independently.
- Prefer chunk boundaries at section headers such as Pathway Metadata, Milestones, Term Records, Flat Course Index, and Canonical Plain-Text Passage.
- Preserve course codes together with course names during chunking.
- Keep milestone records with their associated terms.