"""
Processing order:
1. Read raw JSON records.
2. Apply Unicode NFC normalization and rule-based cleaning to
   both the headline and news content.
3. Remove records with empty headline/content after cleaning.
4. Remove exact duplicates using the cleaned headline-content pair.
5. Preserve all metadata fields and write cleaned JSON files.
6. Write detailed JSONL logs and a run-level summary.

Update DATASET_ROOTS and OUTPUT_ROOT before running.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_ROOTS = {
    "adaderana_english": Path(r"path/to/adaderana_english"),
}

# Cleaned files are written here.
# The original input files are never modified.
OUTPUT_ROOT = Path(r"path/to/preprocessed")
LOG_DIR = OUTPUT_ROOT / "logs"


# ============================================================
# TEXT NORMALIZATION AND CLEANING
# ============================================================

def normalize_and_clean_text(text: Any) -> tuple[str, list[str]]:
    """
    Apply Unicode normalization and rule-based cleaning.

    The same function is applied to both headlines and news content.
    Returns:
        cleaned_text: cleaned string
        changes: descriptions of applied operations
    """
    if text is None:
        return "", []

    text = str(text)
    if not text.strip():
        return "", []

    changes: list[str] = []

    # 1. Unicode NFC normalization
    normalized = unicodedata.normalize("NFC", text)
    if normalized != text:
        changes.append("Applied Unicode NFC normalization")
    text = normalized

    # 2. Remove BOM, zero-width, soft-hyphen and related artefacts
    new_text = re.sub(r"[\ufeff\u200b\u200c\u200d\u00ad]", "", text)
    if new_text != text:
        changes.append("Removed Unicode artefacts")
    text = new_text

    # 3. Remove emoji and pictographic symbols
    new_text = re.sub(
        r"[\U0001F300-\U0001F9FF"
        r"\U00002600-\U000027BF"
        r"\U0001FA00-\U0001FA6F"
        r"\U0001FA70-\U0001FAFF"
        r"\U00002702-\U000027B0"
        r"\U0000FE00-\U0000FE0F]+",
        " ",
        text,
    )
    if new_text != text:
        changes.append("Removed emoji/pictographic symbols")
    text = new_text

    # 4. Remove WordPress and embedded-media shortcodes
    shortcode_patterns = [
        r"\[ot-caption\b[^\]]*\](?:.*?\[/ot-caption\])?",
        r"\[ot-video\b[^\]]*\]?",
        r"\[MP3\].*?(?:\[/MP3\]|$)",
        r"\[[A-Za-z][A-Za-z0-9_-]*(?:\s+[^\]]*)?\]",
    ]

    for pattern in shortcode_patterns:
        new_text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if new_text != text:
            changes.append("Removed WordPress/embed shortcodes")
        text = new_text

    # 5. Remove malformed scraping artefacts
    new_text = re.sub(r"<>\s*\(([^()]*)\)\s*<>", r"(\1)", text)
    new_text = re.sub(
        r"\s*\w{0,10}<>\w{0,10}\s*$",
        " ",
        new_text,
        flags=re.MULTILINE,
    )
    new_text = re.sub(r"<>", " ", new_text)
    if new_text != text:
        changes.append("Removed malformed scraping artefacts")
    text = new_text

    # 6. Remove HTML/XML tags
    new_text = re.sub(r"<[^>]{1,200}>", " ", text)
    if new_text != text:
        changes.append("Removed HTML/XML tags")
    text = new_text

    # 7. Remove URLs
    new_text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    if new_text != text:
        changes.append("Removed URLs")
    text = new_text

    # 8. Remove update/timestamp headers
    new_text = re.sub(
        r"\bUpdated?\s*[:\-]?\s*"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*"
        r",?\s*"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)?\s*"
        r"\d{0,2},?\s*\d{0,4}\s*\d{0,2}[:.]\d{0,2}\s*"
        r"(?:am|pm)?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    if new_text != text:
        changes.append("Removed update/timestamp headers")
    text = new_text

    # 9. Remove separator/divider lines
    new_text = re.sub(r"[=_*\-]{3,}", " ", text)
    if new_text != text:
        changes.append("Removed separator/divider lines")
    text = new_text

    # 10. Remove stray JSON artefacts
    json_patterns = [
        r'"\s*\}\s*"?',
        r"^\s*\}\s*$",
        r'\[\s*\{["\']?',
        r'["\']?\}\s*\]',
    ]

    for pattern in json_patterns:
        new_text = re.sub(pattern, " ", text, flags=re.MULTILINE)
        if new_text != text:
            changes.append("Removed stray JSON artefacts")
        text = new_text

    # 11. Remove source/article-by attribution lines
    new_text = re.sub(
        r"^[\s\u200b]*(?:Source|Article\s*By)\s*:\s*"
        r"[^\n.।෴]{0,200}",
        " ",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if new_text != text:
        changes.append("Removed source/article-by attribution lines")
    text = new_text

    # 12. Remove trailing source attributions and reporter bylines
    original_text = text

    while True:
        previous_text = text

        # Examples: (BBC), (Ada Derana - Tamil)
        text = re.sub(r"\s*\([^()\n]*\)\s*$", "", text.rstrip())

        # Examples: - Reporter Name -, - Source Name -
        text = re.sub(r"\s*-\s*[^-\n]{2,60}\s*-\s*$", "", text.rstrip())

        if text == previous_text:
            break

        text = text.strip()

    if text != original_text:
        changes.append("Removed trailing source attributions/reporter bylines")

    # 13. Remove standalone timestamp-only lines
    timestamp_patterns = [
        r"^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"\s*(?:\d{1,2}:\d{2}(?::\d{2})?)?"
        r"\s*(?:am|pm)?\s*$",
        r"^\s*(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}"
        r"\s*\d{0,2}:?\d{0,2}\s*(?:am|pm)?\s*$",
    ]

    for pattern in timestamp_patterns:
        new_text = re.sub(
            pattern,
            " ",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        if new_text != text:
            changes.append("Removed standalone timestamp lines")
        text = new_text

    # 14. Remove navigation/breadcrumb lines beginning with dashes
    new_text = re.sub(
        r"^\s*-{2,}\s*.{0,80}$",
        " ",
        text,
        flags=re.MULTILINE,
    )
    if new_text != text:
        changes.append("Removed navigation/breadcrumb lines")
    text = new_text

    # 15. Standardize quotation marks and dashes
    new_text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("‟", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("‚", "'")
        .replace("‛", "'")
        .replace("–", "-")
        .replace("—", "-")
        .replace("―", "-")
    )
    if new_text != text:
        changes.append("Standardized quotation marks and dashes")
    text = new_text

    # 16. Normalize redundant whitespace
    new_text = re.sub(r"\r\n|\r", "\n", text)
    new_text = re.sub(r"[ \t]+", " ", new_text)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    new_text = new_text.strip()

    if new_text != text:
        changes.append("Collapsed redundant whitespace")

    return new_text, changes


# ============================================================
# FILE AND LOGGING UTILITIES
# ============================================================

def get_json_files(root_folder: Path) -> list[Path]:
    """Return all JSON files under a directory recursively."""
    return sorted(
        path for path in root_folder.rglob("*.json")
        if path.is_file()
    )


def create_output_path(
    input_path: Path,
    input_root: Path,
    output_root: Path,
) -> Path:
    """
    Preserve the source folder name and relative folder structure.

    Example:
        input_root:  .../itn_sinhala_preprocessed
        input_path:  .../itn_sinhala_preprocessed/2021/01/a.json
        output:      .../cleaned/itn_sinhala_preprocessed/2021/01/a.json
    """
    relative_path = input_path.relative_to(input_root)
    return output_root / input_root.name / relative_path


class CleaningLogger:
    """Write one JSON object per line for each processing event."""

    def __init__(self, log_path: Path) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.file = log_path.open("w", encoding="utf-8")

    def write(self, record: dict[str, Any]) -> None:
        self.file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )
        self.file.flush()

    def close(self) -> None:
        self.file.close()


# ============================================================
# MAIN PROCESSING
# ============================================================

def main() -> None:
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Global set: duplicates are removed across all configured sources.
    seen_pairs: set[tuple[str, str]] = set()

    summary_rows: list[dict[str, Any]] = []

    print("=" * 70)
    print("CeyNews preprocessing pipeline")
    print(f"Run timestamp: {run_timestamp}")
    print(f"Output root:   {OUTPUT_ROOT}")
    print(f"Log directory: {LOG_DIR}")
    print("=" * 70)

    for source_name, input_root in DATASET_ROOTS.items():
        print(f"\nProcessing source: {source_name}")
        print(f"Input:  {input_root}")

        if not input_root.exists():
            print("WARNING: Input directory does not exist. Skipping.")
            summary_rows.append({
                "source": source_name,
                "total": 0,
                "written": 0,
                "skipped": 0,
                "duplicates": 0,
                "errors": 0,
                "status": "missing_input_directory",
            })
            continue

        output_root = OUTPUT_ROOT
        log_path = LOG_DIR / f"{source_name}_preprocessing_log.jsonl"
        logger = CleaningLogger(log_path)

        total = 0
        written = 0
        skipped = 0
        duplicates = 0
        errors = 0

        json_files = get_json_files(input_root)
        print(f"JSON files found: {len(json_files):,}")

        for input_path in json_files:
            total += 1

            try:
                with input_path.open("r", encoding="utf-8") as file:
                    article = json.load(file)

                if not isinstance(article, dict):
                    skipped += 1
                    logger.write({
                        "status": "skipped",
                        "source": str(input_path),
                        "reason": "JSON record is not an object",
                    })
                    continue

                # Read the supported headline field.
                headline = article.get("Headline", "")
                raw_content = article.get("News Content", "")

                # Normalize and clean BOTH fields.
                cleaned_headline, headline_changes = (
                    normalize_and_clean_text(headline)
                )
                cleaned_content, content_changes = (
                    normalize_and_clean_text(raw_content)
                )

                # Check emptiness AFTER preprocessing.
                if not cleaned_headline:
                    skipped += 1
                    logger.write({
                        "status": "skipped",
                        "source": str(input_path),
                        "reason": "Headline empty after preprocessing",
                    })
                    continue

                if not cleaned_content:
                    skipped += 1
                    logger.write({
                        "status": "skipped",
                        "source": str(input_path),
                        "reason": "News Content empty after preprocessing",
                    })
                    continue

                # Exact duplicate detection using cleaned fields.
                duplicate_key = (cleaned_headline, cleaned_content)

                if duplicate_key in seen_pairs:
                    duplicates += 1
                    logger.write({
                        "status": "skipped",
                        "source": str(input_path),
                        "reason": (
                            "Exact duplicate based on cleaned "
                            "headline-content pair"
                        ),
                        "duplicate_key": {
                            "headline": cleaned_headline,
                            "content": cleaned_content,
                        },
                    })
                    continue

                seen_pairs.add(duplicate_key)

                # Update only the normalized/cleaned text fields.
                # All other metadata fields remain unchanged.
                article["Headline"] = cleaned_headline
                article["News Content"] = cleaned_content

                output_path = create_output_path(
                    input_path,
                    input_root,
                    output_root,
                )
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with output_path.open("w", encoding="utf-8") as file:
                    json.dump(
                        article,
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )

                written += 1

                logger.write({
                    "status": "written",
                    "source": str(input_path),
                    "output": str(output_path),
                    "headline_changes": headline_changes,
                    "content_changes": content_changes,
                })

            except json.JSONDecodeError as error:
                errors += 1
                logger.write({
                    "status": "error",
                    "source": str(input_path),
                    "error": f"JSONDecodeError: {error}",
                })

            except Exception as error:
                errors += 1
                logger.write({
                    "status": "error",
                    "source": str(input_path),
                    "error": repr(error),
                })

        logger.close()

        row = {
            "source": source_name,
            "total": total,
            "written": written,
            "skipped": skipped,
            "duplicates": duplicates,
            "errors": errors,
            "status": "completed",
        }
        summary_rows.append(row)

        print(f"Total:      {total:,}")
        print(f"Written:    {written:,}")
        print(f"Skipped:    {skipped:,}")
        print(f"Duplicates: {duplicates:,}")
        print(f"Errors:     {errors:,}")

    # Write a run-level summary.
    summary_path = LOG_DIR / f"summary_{run_timestamp}.json"

    totals = {
        "total": sum(row["total"] for row in summary_rows),
        "written": sum(row["written"] for row in summary_rows),
        "skipped": sum(row["skipped"] for row in summary_rows),
        "duplicates": sum(row["duplicates"] for row in summary_rows),
        "errors": sum(row["errors"] for row in summary_rows),
    }

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "run_timestamp": run_timestamp,
                "output_root": str(OUTPUT_ROOT),
                "log_directory": str(LOG_DIR),
                "sources": summary_rows,
                "totals": totals,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    for row in summary_rows:
        print(
            f"{row['source']}: "
            f"total={row['total']:,}, "
            f"written={row['written']:,}, "
            f"skipped={row['skipped']:,}, "
            f"duplicates={row['duplicates']:,}, "
            f"errors={row['errors']:,}"
        )

    print("-" * 70)
    print(
        f"TOTAL: total={totals['total']:,}, "
        f"written={totals['written']:,}, "
        f"skipped={totals['skipped']:,}, "
        f"duplicates={totals['duplicates']:,}, "
        f"errors={totals['errors']:,}"
    )
    print(f"\nRun summary: {summary_path}")
    print(f"Detailed logs: {LOG_DIR}")


if __name__ == "__main__":
    main()
