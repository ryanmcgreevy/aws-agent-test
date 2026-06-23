---
name: course-scheduling-workflow
description: |
  Structured workflow for building student course schedules. Guides the agent through identifying student goals, 
  retrieving pathway information, gathering prerequisites and preferences, querying live schedule data, and 
  constructing conflict-free course schedules with clear reasoning.
instructions_version: "1.0"
allowed_tools:
  - access_RAG
  - query_schedule
tags:
  - scheduling
  - degree-planning
  - course-selection
  - pathway-mapping
---

# Course Scheduling Workflow

## Overview

Building a successful student schedule requires a structured, iterative process that combines program requirements (from the knowledge base) with live course availability (from the schedule database). This skill guides you through identifying the student's academic goals, gathering necessary context, retrieving relevant constraints and course information, and constructing a conflict-free schedule.

The workflow is **not strictly linear**—you will often cycle through these steps in different orders as new information emerges or as you refine the schedule.

## Core Workflow Steps

### Step 1: Identify the Student's Program, Major, Minor, or Area of Interest

**Goal:** Establish the academic program context.

**Questions to ask if not already stated:**
- "What is your major (or intended major)?"
- "Are you pursuing a specific degree type (Bachelor of Science, Bachelor of Arts, etc.)?"
- "Does your institution offer different degree options or pathways for the same major?"
- "Are you also pursuing a minor or certificate?"
- "Do you have a specific campus location or term-start date in mind?" (e.g., "Fall 2025 start, Kokomo campus")

**What to listen for:**
- Program name (e.g., "Mathematics BS", "Computer Science BA")
- Campus or location (e.g., "Indiana University Kokomo" vs. "IUPUI")
- Start term (e.g., "Fall 2025", "Spring 2026")
- Any non-traditional context (dual degree, accelerated track, etc.)

**How to proceed:** Move to **Step 2** once you have a clear program identity.

---

### Step 2: Retrieve Pathway Information and Program Requirements

**Goal:** Obtain the recommended course sequence, degree requirements, milestones, and credit targets.

**Use the `access_RAG` tool:**
- Query: `"[Program Name] pathway [Start Term]"` or `"[Program Name] degree requirements"`
- Example: `"Mathematics BS pathway Fall 2025"` or `"Computer Science Bachelor of Science requirements"`
- Also query: `"[Program Name] course options prerequisites"` to understand choice slots and alternatives

**What to extract from the results:**
- Total credit hours required (e.g., 120 credits)
- Term structure (e.g., 8 terms, 4 years)
- Required courses (fixed courses each term)
- Elective/choice slots (flexible options)
- Prerequisites and dependencies between courses
- Recommended term-by-term sequence
- Milestones (internship expectations, advising checkpoints, etc.)

**Note on pathway documents:**
- Pathway documents typically show an ideal, front-loaded course load
- They are **templates**, not the only valid schedules
- Students may need to adjust based on prior credits, prerequisites, or personal constraints

**How to proceed:** Move to **Step 3** with a clear picture of the requirements. If any information is unclear (e.g., which electives are available), move to **Step 4** to ask the student for clarification.

---

### Step 3: Retrieve Specific Course Information and Prerequisites

**Goal:** Understand the courses, their prerequisites, and any eligibility constraints.

**Use the `access_RAG` tool for detailed course info:**
- Query: `"[Course Code] prerequisites corequisites"` (e.g., `"MATH-M 215 prerequisites"`)
- Query: `"[Program Name] course descriptions [Subject Area]"` (e.g., `"Mathematics BS course descriptions calculus linear algebra"`)
- Query: `"[Elective Slot Name] course options"` if the pathway lists choice groups (e.g., `"upper-division mathematics electives"`)

**What to extract:**
- Prerequisites (must pass before enrolling)
- Corequisites (can be taken at the same time)
- Course descriptions and learning outcomes (context for student decisions)
- Eligibility constraints (e.g., "junior standing required", "department approval required")
- Common sequencing patterns (e.g., "Calculus I → Calculus II → Linear Algebra")

**How to proceed:** If prerequisites are satisfied or unknown, move to **Step 4**. If a student lacks a prerequisite, ask them directly how they want to handle it (retake, waive, adjust timing).

---

### Step 4: Ask Direct Follow-Up Questions About Prerequisites, Preferences, and Constraints

**Goal:** Gather the minimum additional information needed to build a valid and personalized schedule.

**Prerequisites and eligibility:**
- "Have you completed [Required Prerequisite Course]?"
- "Do you have any course waivers or prerequisite exemptions on file?"
- "Is there a specific reason you'd prefer to postpone [Course]?"

**Scheduling preferences:**
- "Do you prefer morning, afternoon, or evening classes?"
- "Do you have work or other commitments that limit your availability on certain days?"
- "Are you interested in fully online, hybrid, or in-person classes?"
- "Would you like classes clustered on specific days (e.g., MWF only, TTh only)?"

**Prior credit and standing:**
- "How many credits have you already completed?"
- "What is your current class standing (freshman, sophomore, etc.)?"
- "Are there any courses you've already completed that might satisfy degree requirements?"

**Degree timing and goals:**
- "What term are you starting?" (if not stated in Step 1)
- "Are you on track to graduate in the standard timeframe, or do you need to accelerate/delay?"
- "Are there specific semesters you plan to be unavailable (e.g., study abroad, internship term)?"

**Key principle:** Ask only the **minimum** information needed. Don't ask about every elective preference upfront—gather constraints first, then refine.

**How to proceed:** Once you have answers to critical blockers (prerequisites, availability windows, term start), move to **Step 5** to query the actual schedule.

---

### Step 5: Query the Schedule Database for Live Course Offerings

**Goal:** Find available sections of the required and elective courses that fit the student's constraints and have no conflicts.

**Use the `query_schedule` tool:**
- Query: `"[Course Code] [Term]"` (e.g., `"MATH-M 215 Fall 2025"`)
- Query: `"[Subject Area] [Term]"` for browsing electives (e.g., `"MATH Fall 2025"`)
- Query: `"[Campus Location] [Term]"` if filtering by location (e.g., `"Kokomo Fall 2025"`)

**What the tool returns:**
- Available sections (class numbers)
- Meeting times and days (e.g., "MWF 9:00–9:50 AM")
- Instructors
- Instruction mode (in-person, online, hybrid)
- Locations/facilities
- Current enrollment and seat availability (if available)

**Conflict detection:**
- **Time conflicts:** Same student cannot enroll in two sections that overlap.
- **Prerequisite conflicts:** Course must be taken after (or concurrently with) its prerequisites.
- **Capacity conflicts:** Sections with limited seats may not be available.
- **Location conflicts:** Back-to-back courses at different campuses might be infeasible.

**How to proceed:** Once you have section data, move to the **Iterative Refinement** phase (see below).

---

## Iterative Refinement: Repeating Steps to Build the Final Schedule

After the initial five steps, you will often need to **repeat steps in different orders** as you refine:

### Scenario 1: Prerequisite Conflict Discovered During Step 5
- **Trigger:** The required course for Year 1 has no conflict-free sections, or all sections require an unmet prerequisite.
- **Action:** Return to **Step 3** to understand alternatives. Then ask the student (**Step 4**) whether to:
  - Delay the course to the next term
  - Retake the prerequisite
  - Pursue an exemption or waiver
- **Then:** Return to **Step 5** with the revised constraint.

### Scenario 2: Student Discovers a Scheduling Preference Issue
- **Trigger:** While reviewing options, the student realizes they can't take all morning classes (or another preference).
- **Action:** Return to **Step 4** to gather the new constraint.
- **Then:** Return to **Step 5** with updated criteria.

### Scenario 3: Elective Choices Need Refinement
- **Trigger:** Multiple electives are available; the student needs guidance on which to choose.
- **Action:** Return to **Step 2/3** to retrieve course descriptions, then ask (**Step 4**) which aligns with their goals.
- **Then:** Return to **Step 5** to query sections for the chosen elective.

### Scenario 4: Term-by-Term Planning
- **Trigger:** Year 1 is scheduled; now building Year 2.
- **Action:** Return to **Step 2** to retrieve the Year 2 requirements from the pathway.
- **Then:** Work through **Steps 3–5** for the next term.

---

## Building the Final Schedule: Validation and Presentation

Once you have narrowed down course options:

1. **Verify no time conflicts:** List all selected sections with meeting times; ensure no overlaps.
2. **Verify prerequisites:** Confirm all prerequisites are met before the course.
3. **Confirm total credits:** Add up credits to ensure the term meets degree requirements (typically 12–18 credits per term).
4. **Check capacity:** Note if any sections are at or near capacity.
5. **Identify alternatives:** For each selected section, identify 1–2 backup options in case of enrollment issues.

**Present the schedule clearly:**
```
Year 1, Fall 2025 Schedule
─────────────────────────────────────────────────────────────────

Course: MATH-M 215 Calculus I
  Section: 4501 | Days/Times: MWF 9:00–9:50 AM | Location: MATH 215 | Instructor: Dr. Smith
  Credits: 4 | Prerequisite: High School Algebra (met)

Course: PHYS-P 201 General Physics I
  Section: 4502 | Days/Times: TTh 10:00–11:30 AM | Location: SCI 102 | Instructor: Dr. Jones
  Credits: 4 | Prerequisite: Calculus I (concurrent)

Course: ENG-W 131 Writing
  Section: 4503 | Days/Times: MWF 10:00–10:50 AM | Location: LANG 301 | Instructor: Dr. Brown
  Credits: 3 | Prerequisite: None (met)

Total Credits: 11
Conflicts: None detected
Notes: All sections are in-person. You have a 10-minute break between MATH-M 215 and ENG-W 131 on MWF.
```

6. **Offer next steps:**
   - "Ready to plan Year 1 Spring?"
   - "Would you like to adjust any of these courses?"
   - "Do you have questions about any course or instructor?"

---

## Common Clarifying Questions (Quick Reference)

### Program and Timing
- "Which degree are you pursuing?"
- "When do you plan to start?"
- "Do you need to graduate by a specific term?"

### Constraints and Preferences
- "Are you working while studying? If so, what are your available hours?"
- "Do you prefer online, hybrid, or in-person?"
- "Would you like classes on specific days (e.g., MWF only)?"

### Prerequisites and Credit
- "Have you taken [Prerequisite Course]?"
- "How many credits have you completed so far?"
- "Are there any previous courses I should know about that might count toward your degree?"

### Electives and Career Goals
- "What are your career goals or areas of interest within [Major]?"
- "Are there specific electives you've heard about or want to prioritize?"

---

## Handling Unknowns and Edge Cases

### What if the knowledge base doesn't have the pathway document?
- Try broader queries: `"[Program Name] requirements"` or `"[Institution] [Program Name]"`
- Ask the student for specifics: "Can you share the official program requirements or a link to the pathway?"

### What if the schedule database has no sections for a required course?
- Suggest alternatives: "This course isn't offered in [Term]. Would you like to take it in [Next Term] and adjust your schedule?"
- Check if prerequisites can be taken in the interim.

### What if a student doesn't know their prerequisites?
- Use `access_RAG` to retrieve prerequisites, then share with the student.
- Ask: "Would you like me to check if you meet these prerequisites?"

### What if prerequisites are unmet but the student wants to proceed?
- Explain the risk clearly.
- Ask: "Would you like to retake the prerequisite, request a waiver, or delay this course?"

### What if multiple valid schedules are possible?
- Present 2–3 alternatives with trade-offs highlighted:
  - "Option A has all morning classes but includes 5 electives to choose from."
  - "Option B has evening flexibility but limits you to 2 elective options."
- Let the student decide based on their preferences.

---

## Summary: Agent Behavior Checklist

When building a schedule, **always**:
- ✓ Identify the program and start term
- ✓ Retrieve pathway and requirements using `access_RAG`
- ✓ Ask clarifying questions about prerequisites and preferences
- ✓ Query live schedule data with `query_schedule`
- ✓ Detect and resolve conflicts
- ✓ Present schedules clearly with no conflicts
- ✓ Offer alternatives when multiple options exist
- ✓ Ask for minimum information upfront; refine iteratively

**Never**:
- ✗ Assume prerequisites are met without asking or checking
- ✗ Propose schedules with time conflicts
- ✗ Suggest courses without verifying they're available in the student's term
- ✗ Skip clarifying questions; ask directly if information is missing
- ✗ Present only one schedule option if alternatives are available
