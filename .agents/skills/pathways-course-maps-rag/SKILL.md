---
name: pathways-course-maps-rag
description: >-
  Use when browsing Indiana University Pathways pages, extracting pathway or
  course-plan information, and turning it into a retrieval-friendly course-maps
  document. Covers browser traversal, course/title extraction, schema-aligned
  pathway file creation, and index.md updates for the local data/course-maps
  collection.
version: 1
---

# Pathways Course Maps RAG

## Overview

Use this skill when the task is to:

- browse an Indiana University Pathways page in the browser
- inspect a pathway or course plan
- extract exact course names, milestones, requirements, and term structure
- create or update a course-maps markdown file under `data/course-maps`
- keep `data/course-maps/index.md` consistent with the current folder contents
- preserve a schema-friendly structure for RAG ingestion

This skill is for generating durable pathway artifacts from live browser content.
Do not guess missing course names when the planner truncates text; use only
high-confidence names that are visible in the planner markup or linked detail
views.

## Golden Path

1. Open the IU Pathways page in the browser.
2. Locate the target pathway using search, filters, or direct navigation.
3. Traverse the planner and inspect term sections, slots, milestones, and any
   linked course detail views.
4. Extract the exact pathway identity and all high-confidence course names.
5. Write a new pathway document in `data/course-maps` using the local schema.
6. Add or update the collection index so the new file is discoverable.
7. Validate the folder contents and confirm the metadata fields are aligned.

## Browser Traversal Workflow

When using the browser, prefer this order:

1. Load the pathway catalog or planner page.
2. Search for the target pathway title, program code, or keywords.
3. Open the pathway detail page.
4. Read the accessibility tree or page text to identify:
   - pathway name
   - institution
   - program code
   - term labels and credits
   - course codes and course names
   - milestone text
   - requirement slots or choice groups
5. If a label is truncated, open the linked course detail or adjacent planner
   context only when it exposes a full, exact title.
6. Avoid inventing titles from partial labels.

Preferred browser tools:

- `open_browser_page`
- `navigate_page`
- `read_page`
- `read_file` for captured snapshot text
- `click_element`
- `run_playwright_code` when DOM-level extraction is needed

## Extraction Rules

Capture these fields whenever available:

- `document_type`
- `document_id`
- `schema_version`
- `schema_path`
- `created_at`
- `updated_at`
- `source_system`
- `source_entity_type`
- `pathway_name`
- `institution`
- `program_code`
- `pathway_type`
- `visibility_context`
- `auto_apply`
- `total_active_terms`
- `total_years`
- `listed_summary`
- `visible_term_credit_total`
- `credit_target`
- `additional_requirements`
- `source_url`
- `extracted_at`

For term content, preserve:

- term label
- term credits
- course code
- course name
- requirement slots
- choice groups
- milestone text

If a page exposes exact planner text, quote it directly. If a label is truncated
and cannot be expanded from the UI, keep the truncated text or convert it into a
requirement slot instead of guessing.

## Course-Maps File Format

Create pathway documents under `data/course-maps` using the local schema.
The document should include:

- a top-level pathway title
- `## Pathway Metadata`
- `## Pathway Summary`
- `## Milestones`
- `## Retrieval Keywords`
- `## Term Records`
- optional exact-data sections when the planner exposes high-confidence data
- `## Canonical Plain-Text Passage`

Use the following metadata conventions:

- `document_type: pathway_document`
- `document_id` should match the markdown filename without `.md`
- `schema_version: 1.0`
- `schema_path: data/course-maps/schema.md`
- `created_at` and `updated_at` in `YYYY-MM-DD` format
- `source_system` should identify the upstream source, such as
  `Indiana University Pathways`
- `source_entity_type` should identify the upstream entity, such as
  `pathway_template`

## Index Update Workflow

When a new pathway file is added or an existing one changes, update
`data/course-maps/index.md` so it reflects the current folder contents.
The index should stay aligned with the schema contract and include:

- collection metadata
- document count
- one record per pathway file
- short ingestion notes

Make sure the index stays consistent with:

- the actual file names in `data/course-maps`
- matching `document_id` values
- the current count of pathway documents
- the same schema version used by the pathway files

## Validation Checklist

Before finishing, confirm:

1. The pathway document exists in `data/course-maps`.
2. The document contains the required metadata fields.
3. All course names are high-confidence and not guessed.
4. The index lists the new document.
5. The `document_id` matches the filename.
6. The schema path and schema version are consistent.
7. Any new or changed metadata is reflected in the schema document if the
   contract changed.

## Quality Rules

- Preserve exact planner language whenever possible.
- Do not replace `extracted_at` with `accessed_at` unless the schema is updated
  everywhere to define a different meaning.
- Prefer requirement slots over speculative course expansions.
- Keep the artifact RAG-friendly: structured headings, flat metadata, and clear
  term-by-term organization.
- Use ASCII unless the source page or existing file already requires otherwise.

## When to Use

Use this skill when a user asks to:

- extract a Pathways plan from the browser
- create a new course-maps file from an IU pathway
- keep `data/course-maps/index.md` synchronized
- produce a schema-aligned pathway artifact for LLM/RAG use

## When Not to Use

Do not use this skill for:

- general browser questions unrelated to pathway extraction
- unrelated markdown authoring
- arbitrary website scraping that is not about course pathways
- modifying the schema for reasons unrelated to pathway extraction and indexing
