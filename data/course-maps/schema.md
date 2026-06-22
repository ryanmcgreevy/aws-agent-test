# Course Maps Schema

## Schema Metadata
- document_type: schema_document
- schema_name: course-maps-markdown
- schema_version: 1.0
- schema_scope: pathway_documents_and_index
- created_at: 2026-06-22
- updated_at: 2026-06-22
- source_system: local_course_maps_collection
- source_entity_type: schema_document

## Purpose
This document defines the expected structure for pathway files stored in `data/course-maps`. These files are designed for retrieval-augmented generation workflows, document chunking, and lightweight human inspection.

## File Naming Convention
- Use lowercase kebab-case file names.
- Use the normalized pathway title as the base name when practical.
- Example: `ko-mathematics-bs-ey-fall-2025-and-beyond.md`

## Required Document Sections
Each pathway document should contain the following top-level sections in this order:

1. `# Pathway Document: <pathway name>`
2. `## Pathway Metadata`
3. `## Pathway Summary`
4. `## Milestones`
5. `## Retrieval Keywords`
6. `## Term Records`
7. `## Canonical Plain-Text Passage`

Optional sections may appear between `## Term Records` and `## Canonical Plain-Text Passage` when they contain high-confidence structured data. Example optional sections include `## Program Description`, `## Known Explicit Course Options`, and other exact requirement-expansion sections.

Every pathway document must include `source_url` and `extracted_at` in `## Pathway Metadata` as mandatory provenance fields.

## Pathway Metadata Schema
The `## Pathway Metadata` section should be a flat bullet list with this shape. All fields listed below are required unless explicitly marked optional:

- `document_type`: fixed string `pathway_document`
- `document_id`: stable kebab-case identifier that should match the document filename without the `.md` suffix
- `pathway_name`: string
- `created_at`: ISO date string in `YYYY-MM-DD` format
- `updated_at`: ISO date string in `YYYY-MM-DD` format
- `source_system`: string
- `source_entity_type`: string, typically `pathway_template`
- `institution`: string
- `program_code`: string
- `pathway_type`: string
- `visibility_context`: string
- `auto_apply`: boolean-like string (`true` or `false`)
- `total_active_terms`: integer
- `total_years`: integer
- `listed_summary`: string
- `visible_term_credit_total`: integer or approximate integer
- `credit_target`: integer
- `additional_requirements`: list of strings
- `source_url`: required absolute URL string pointing to the source pathway page
- `extracted_at`: required ISO date string in `YYYY-MM-DD` format representing when the pathway was extracted

## Milestones Schema
The `## Milestones` section should be a flat list of milestone records. Each milestone record should contain:

- `milestone_term`: string
- `milestone_type`: string
- `milestone_name`: string

## Retrieval Keywords Schema
The `## Retrieval Keywords` section should be a simple bullet list of short phrases. Include:

- program name
- credential type
- campus or institution
- primary subject area
- major requirement themes
- career or milestone terms when relevant

## Term Records Schema
The `## Term Records` section should contain one subsection per academic term.

Each term subsection must start with:

- `### Term: <term label>`
- `term_label`: string
- `term_credits`: integer
- `items`: list

Each item in `items` must declare `item_type` and then follow one of these shapes.

### Item Type: course
- `item_type`: `course`
- `course_code`: string
- `course_name`: string

### Item Type: course_choice
- `item_type`: `course_choice`
- `requirement_name`: string
- `options`: list of exact option strings in the form `CODE | NAME`

### Item Type: requirement_slot
- `item_type`: `requirement_slot`
- `requirement_name`: string
- `requirement_detail`: optional string

### Item Type: milestone
- `item_type`: `milestone`
- `milestone_name`: string

## Canonical Plain-Text Passage Schema
The `## Canonical Plain-Text Passage` section must contain one dense paragraph that restates the pathway in natural language. It should:

- include institution and program identity
- include overall duration and structure
- describe each active term in order
- preserve exact course codes and course names where known
- preserve milestone names where known
- avoid speculative expansion of truncated planner labels

## Optional Exact-Data Sections
Optional sections are allowed only when the data is exact or quoted directly from the planner. Good examples:

- `## Program Description`
- `## Known Explicit Course Options`
- `## Requirement Notes`

Avoid including low-confidence expansions or guessed course titles.

## Quality Rules
- Preserve exact planner wording when available.
- Do not invent full course names from truncated labels.
- Prefer requirement-slot records over guessed course records.
- Keep course codes attached to course names whenever possible.
- Keep milestone actions in the term where they appear.
- Use ASCII only unless the source text requires otherwise.

## Chunking Guidance
Recommended chunk boundaries for RAG ingestion:

1. Pathway Metadata
2. Pathway Summary and Milestones
3. Retrieval Keywords
4. Each individual term subsection
5. Optional exact-data sections
6. Canonical Plain-Text Passage

Do not split a single item record across chunks when avoidable.

## Index Schema
The `data/course-maps/index.md` file should contain:

- collection metadata
- document count
- one record per pathway document
- short ingestion notes

Each index record should include:

- `document_id`
- `file_name`
- `pathway_name`
- `institution`
- `program_code`
- `program_type`
- `keywords`
- `summary`

The `## Collection Metadata` section should also include:

- `document_type`: fixed string `collection_index`
- `schema_version`: string
- `schema_path`: string
- `created_at`: ISO date string in `YYYY-MM-DD` format
- `updated_at`: ISO date string in `YYYY-MM-DD` format
- `source_system`: string
- `source_entity_type`: fixed string `collection_index`

## Schema Document Metadata
The schema document itself should include:

- `document_type`: fixed string `schema_document`
- `schema_name`: string
- `schema_version`: string
- `schema_scope`: string
- `created_at`: ISO date string in `YYYY-MM-DD` format
- `updated_at`: ISO date string in `YYYY-MM-DD` format
- `source_system`: string
- `source_entity_type`: fixed string `schema_document`