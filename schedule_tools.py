"""Helpers for querying the schedule CSV exports used by the Strands agent."""

import csv
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from strands import tool

logger = logging.getLogger(__name__)

SCHEDULE_DATA_DIR = Path(__file__).resolve().parent / "data" / "schedules"

SCHEDULE_FILE_METADATA = {
    "4258": "Fall 2025",
    "4262": "Spring 2026",
}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _clean_field(value: str | None) -> str:
    return (value or "").strip()


def _format_time(value: str | None) -> str:
    cleaned = _clean_field(value)
    if not cleaned:
        return ""
    return cleaned.lstrip("0") if cleaned.startswith("0") else cleaned


def _semester_from_path(path: Path) -> tuple[str, str]:
    semester_code = path.stem.split("-")[0]
    semester_label = SCHEDULE_FILE_METADATA.get(semester_code, semester_code)
    return semester_code, semester_label


def _instructor_key(row: dict[str, str]) -> tuple[str, str]:
    return (_clean_field(row.get("Instructor Name")), _clean_field(row.get("Instructor Role Description")))


@lru_cache(maxsize=1)
def _load_schedule_sections() -> tuple[dict[str, Any], ...]:
    sections: list[dict[str, Any]] = []

    if not SCHEDULE_DATA_DIR.exists():
        logger.warning("Schedule data directory not found: %s", SCHEDULE_DATA_DIR)
        return tuple(sections)

    for csv_path in sorted(SCHEDULE_DATA_DIR.glob("*.csv")):
        semester_code, semester_label = _semester_from_path(csv_path)
        try:
            with csv_path.open(newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.DictReader(handle))
        except Exception as exc:
            logger.warning("Failed to load schedule CSV %s: %s", csv_path, exc)
            continue

        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            class_number = _clean_field(row.get("Class Number")) or "unknown"
            group = grouped.setdefault(
                class_number,
                {
                    "semester_code": semester_code,
                    "semester_label": semester_label,
                    "class_number": class_number,
                    "subject_area": _clean_field(row.get("Subject Area")),
                    "course_catalog_number": _clean_field(row.get("Course Catalog Number")),
                    "course_component": _clean_field(row.get("Course Component Short Description")),
                    "class_session_code": _clean_field(row.get("Class Session Code")),
                    "class_start_date": _clean_field(row.get("Class Start Date")),
                    "end_date": _clean_field(row.get("End Date")),
                    "instruction_mode": _clean_field(row.get("Instruction Mode Description")),
                    "facility_id": _clean_field(row.get("Facility ID")),
                    "start_time": _clean_field(row.get("Start Time")),
                    "end_time": _clean_field(row.get("End Time")),
                    "meeting_pattern": _clean_field(row.get("Derived Meeting Pattern")),
                    "instructors": [],
                    "roles": [],
                    "row_count": 0,
                },
            )
            group["row_count"] += 1

            instructor = _instructor_key(row)
            if instructor not in group["instructors"]:
                group["instructors"].append(instructor)

            role = _clean_field(row.get("Instructor Role Description"))
            if role and role not in group["roles"]:
                group["roles"].append(role)

        for group in grouped.values():
            instructors = group.pop("instructors")
            roles = group.pop("roles")
            if instructors:
                group["instructor_text"] = "; ".join(
                    f"{name} ({role})" if role else name for name, role in instructors
                )
            else:
                group["instructor_text"] = ""
            group["role_text"] = ", ".join(roles)
            sections.append(group)

    return tuple(sections)


def _section_search_text(section: dict[str, Any]) -> str:
    parts = [
        section.get("semester_code", ""),
        section.get("semester_label", ""),
        section.get("subject_area", ""),
        section.get("course_catalog_number", ""),
        section.get("class_number", ""),
        section.get("course_component", ""),
        section.get("class_session_code", ""),
        section.get("instruction_mode", ""),
        section.get("facility_id", ""),
        section.get("meeting_pattern", ""),
        section.get("instructor_text", ""),
        section.get("role_text", ""),
    ]
    return _normalize_text(" ".join(str(part) for part in parts))


def _format_schedule_section(section: dict[str, Any]) -> str:
    fields: list[str] = [
        f"Semester: {section['semester_code']} ({section['semester_label']})",
        f"Course: {section['subject_area']} {section['course_catalog_number']}",
        f"Class Number: {section['class_number']}",
        f"Component: {section['course_component']}",
    ]

    meeting_pattern = _clean_field(section.get("meeting_pattern"))
    start_time = _format_time(section.get("start_time"))
    end_time = _format_time(section.get("end_time"))
    facility_id = _clean_field(section.get("facility_id"))
    instruction_mode = _clean_field(section.get("instruction_mode"))
    class_start_date = _clean_field(section.get("class_start_date"))
    end_date = _clean_field(section.get("end_date"))
    instructor_text = _clean_field(section.get("instructor_text"))

    if meeting_pattern:
        fields.append(f"Meeting Pattern: {meeting_pattern}")
    if start_time or end_time:
        time_value = " - ".join(part for part in [start_time, end_time] if part)
        fields.append(f"Time: {time_value}")
    if facility_id:
        fields.append(f"Facility: {facility_id}")
    if instruction_mode:
        fields.append(f"Instruction Mode: {instruction_mode}")
    if class_start_date or end_date:
        date_value = " - ".join(part for part in [class_start_date, end_date] if part)
        fields.append(f"Dates: {date_value}")
    if instructor_text:
        fields.append(f"Instructors: {instructor_text}")

    notes: list[str] = []
    if section.get("row_count", 0) > 1:
        notes.append(f"merged {section['row_count']} CSV rows")
    if not facility_id:
        notes.append("no facility listed")
    if not start_time or not end_time:
        notes.append("missing time fields")
    if notes:
        fields.append(f"Notes: {', '.join(notes)}")

    return "\n".join(fields)


def _semester_matches(section: dict[str, Any], semester: str) -> bool:
    if not semester:
        return True

    target = _normalize_text(semester)
    semester_code = _normalize_text(section.get("semester_code"))
    semester_label = _normalize_text(section.get("semester_label"))
    return target in {semester_code, semester_label} or target in semester_code or target in semester_label


def _score_section(section: dict[str, Any], query: str) -> int:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return 1

    search_text = _section_search_text(section)
    subject_area = _normalize_text(section.get("subject_area"))
    course_catalog_number = _normalize_text(section.get("course_catalog_number"))

    explicit_course_code = re.search(r"\b([a-z]{2,5}-[a-z]{1,2})\s*([0-9]{3})\b", normalized_query)
    if explicit_course_code:
        expected_subject_area = explicit_course_code.group(1)
        expected_course_number = explicit_course_code.group(2)
        if subject_area != expected_subject_area or course_catalog_number != expected_course_number:
            return 0
        return 100

    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_query) if token]
    if not tokens:
        return 0

    score = sum(1 for token in tokens if token in search_text)
    if subject_area and course_catalog_number and subject_area in normalized_query and course_catalog_number in normalized_query:
        score += 25
    return score


@tool
def query_schedule(semester: str = "", query: str = "", limit: int = 10) -> str:
    """Query the grouped class-schedule CSV data. This function is used by the agent to retrieve relevant class section information 
       based on the user's query and optional semester filter, and returns a compact text block containing one summary per matching class section.
       Use this function when the user asks about schedules, class offerings, times, instructors, or rooms in the schedule.
    Args:
        semester: Optional semester code or label, such as 4258 or Fall 2025.
        query: Optional freeform search text for course codes, instructors, rooms, or meeting details.
        limit: Maximum number of grouped class sections to return.

    Returns:
        A compact text block containing one summary per matching class section.
    """
    sections = [section for section in _load_schedule_sections() if _semester_matches(section, semester)]

    if not sections:
        return "No schedule data found for the requested semester."

    scored_sections = []
    for section in sections:
        score = _score_section(section, query)
        if query and score == 0:
            continue
        scored_sections.append((score, section))

    if not scored_sections:
        return "No matching class sections found."

    scored_sections.sort(
        key=lambda item: (
            -item[0],
            item[1].get("subject_area", ""),
            item[1].get("course_catalog_number", ""),
            item[1].get("class_number", ""),
        )
    )

    limited_sections = [section for _, section in scored_sections[: max(1, limit)]]
    return "\n\n---\n\n".join(_format_schedule_section(section) for section in limited_sections)
