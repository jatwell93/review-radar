import csv
import io


_TEXT_CANDIDATES = [
    "text", "review_text", "comment", "comments", "review", "body", "content",
    "reviewer_comment", "review comment", "Review Text",
]

_DATE_CANDIDATES = ["date", "time", "created_at", "create_time", "published_at", "timestamp"]


def _detect_text_column(fieldnames: list[str]) -> str:
    # Priority: exact match against candidate list (case-sensitive)
    for candidate in _TEXT_CANDIDATES:
        if candidate in fieldnames:
            return candidate
    # Fallback: first column whose name contains "text" or "review" (case-insensitive)
    for name in fieldnames:
        lower = name.lower()
        if "text" in lower or "review" in lower:
            return name
    raise ValueError(
        "No identifiable review text column found. "
        "Expected a column named 'text', 'review_text', or similar."
    )


def _detect_date_column(fieldnames: list[str]) -> str | None:
    for candidate in _DATE_CANDIDATES:
        if candidate in fieldnames:
            return candidate
    return None


def parse_reviews(contents: bytes) -> list[dict]:
    # Decode: utf-8-sig first (strips BOM from Windows CSV exports), fallback latin-1
    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("CSV contains no header row.")

    fieldnames = list(reader.fieldnames)
    text_col = _detect_text_column(fieldnames)
    date_col = _detect_date_column(fieldnames)

    rows = []
    for row in reader:
        cell = row.get(text_col, "")
        if not cell or not cell.strip():
            continue
        rows.append({
            "text": cell.strip(),
            "date": row.get(date_col) if date_col else None,
        })

    if not rows:
        raise ValueError("CSV contains no review text rows after filtering.")

    return rows
