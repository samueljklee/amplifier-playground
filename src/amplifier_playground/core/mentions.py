"""Pure text processing for @mentions - no file I/O."""

import re
from re import Pattern

# @mention pattern: matches @FILENAME or @path/to/file or @collection:path
# Negative lookbehind to exclude email addresses (no alphanumeric before @)
MENTION_PATTERN: Pattern = re.compile(r"(?<![a-zA-Z0-9])@([a-zA-Z0-9_\-/\.:]+)")

# @~/ pattern: matches @~/path/to/file
HOME_PATTERN: Pattern = re.compile(r"@~/([a-zA-Z0-9_\-/\.]*)")


def parse_mentions(text: str) -> list[str]:
    """Extract all @mentions from text, excluding examples in code/quotes."""
    # Filter out inline code and quotes
    text_filtered = re.sub(r"`[^`\n]+`", "", text)
    text_filtered = re.sub(r'"[^"\n]*"', "", text_filtered)
    text_filtered = re.sub(r"'[^'\n]*'", "", text_filtered)

    # Extract home mentions
    homes = [f"@~/{m}" if m else "@~/" for m in HOME_PATTERN.findall(text_filtered)]

    # Regular mentions
    all_at_mentions = MENTION_PATTERN.findall(text_filtered)
    regulars = []
    for m in all_at_mentions:
        idx = text_filtered.find(f"@{m}")
        if idx > 0:
            before = text_filtered[max(0, idx - 2) : idx]
            if before.endswith("~/"):
                continue
        if m == "mention":
            continue
        regulars.append(f"@{m}")

    return homes + regulars


def has_mentions(text: str) -> bool:
    """Check if text contains any @mentions."""
    return bool(MENTION_PATTERN.search(text))
