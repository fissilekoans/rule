
#!/usr/bin/env python3
"""Convert HaGeZi Wildcard Asterisk list to Surge DOMAIN-SET."""

from pathlib import Path
from urllib.request import Request, urlopen
import sys

SOURCE_URL = (
    "https://raw.githubusercontent.com/hagezi/dns-blocklists/refs/heads/main/"
    "wildcard/pro.plus.txt"
)

OUTPUT_FILE = Path("hagezi-pro-plus-surge.list")

MINIMUM_ENTRIES = 100_000
MINIMUM_DOWNLOAD_BYTES = 250_000


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    request = Request(
        SOURCE_URL,
        headers={"User-Agent": "hagezi-surge-list-builder/1.0"},
    )

    # Download source
    try:
        with urlopen(request, timeout=120) as response:
            raw = response.read()
    except Exception as exc:
        fail(f"Download failed: {exc}")

    if len(raw) < MINIMUM_DOWNLOAD_BYTES:
        fail(f"Downloaded file is unexpectedly small: {len(raw)} bytes.")

    try:
        source_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        fail(f"Invalid UTF-8: {exc}")

    output_lines = []
    entry_count = 0
    invalid_lines = []

    for line_number, line in enumerate(source_text.splitlines(), start=1):

        # Preserve all original comments and blank lines
        if not line.strip() or line.startswith(("#", "!", ";", "//")):
            output_lines.append(line)
            continue

        # Convert *.domain.com to .domain.com
        if line.startswith("*."):
            domain = line[2:]

            if (
                not domain
                or any(ch.isspace() for ch in domain)
                or any(ch in domain for ch in "*/\\,")
                or "." not in domain
            ):
                invalid_lines.append((line_number, line))
                continue

            output_lines.append("." + domain)
            entry_count += 1

        else:
            invalid_lines.append((line_number, line))

    if invalid_lines:
        examples = "\n".join(
            f"Line {number}: {value}"
            for number, value in invalid_lines[:5]
        )
        fail(f"Unexpected source entries:\n{examples}")

    if entry_count < MINIMUM_ENTRIES:
        fail(
            f"Only {entry_count:,} entries converted. "
            "Keeping existing output."
        )

    # Preserve original header and entry order.
    # Only the leading '*' of each domain has been removed.
    output = "\n".join(output_lines) + "\n"

    # Atomic write
    temporary_file = OUTPUT_FILE.with_name(OUTPUT_FILE.name + ".tmp")
    temporary_file.write_bytes(output.encode("utf-8"))
    temporary_file.replace(OUTPUT_FILE)

    print(
        f"Success: {entry_count:,} entries converted."
        f" Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
