
#!/usr/bin/env python3
"""Convert HaGeZi wildcard lists to Surge DOMAIN-SET."""

from pathlib import Path
from urllib.request import Request, urlopen
import re
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent

# Sources and corresponding output filenames
SOURCES = [
    {
        "name": "HaGeZi Multi PRO++",
        "url": (
            "https://raw.githubusercontent.com/hagezi/dns-blocklists/"
            "refs/heads/main/wildcard/pro.plus.txt"
        ),
        "output": "ph-pro++.list",
    },
    {
        "name": "HaGeZi Multi LIGHT",
        "url": (
            "https://raw.githubusercontent.com/hagezi/dns-blocklists/"
            "refs/heads/main/wildcard/light.txt"
        ),
        "output": "tv-light.list",
    },
]

MINIMUM_DOWNLOAD_BYTES = 250_000


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def convert_source(name: str, source_url: str) -> str:
    print(f"Downloading: {name}")

    request = Request(
        source_url,
        headers={"User-Agent": "hagezi-surge-list-builder/1.0"},
    )

    try:
        with urlopen(request, timeout=120) as response:
            raw = response.read()
    except Exception as exc:
        fail(f"{name}: Download failed: {exc}")

    if len(raw) < MINIMUM_DOWNLOAD_BYTES:
        fail(f"{name}: Downloaded file is unexpectedly small.")

    try:
        source_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        fail(f"{name}: Invalid UTF-8: {exc}")

    # Read original entry count from HaGeZi header
    match = re.search(
        r"^# Number of entries:\s*([\d,]+)\s*$",
        source_text,
        re.MULTILINE,
    )

    if not match:
        fail(f"{name}: Cannot find original entry count.")

    expected_count = int(match.group(1).replace(",", ""))

    output_lines = []
    entry_count = 0
    invalid_lines = []

    for line_number, line in enumerate(
        source_text.splitlines(), start=1
    ):
        # Preserve original comments and blank lines
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
        fail(f"{name}: Unexpected source entries:\n{examples}")

    # Verify converted entries against original metadata
    if entry_count != expected_count:
        fail(
            f"{name}: Entry count mismatch. "
            f"Expected {expected_count:,}, got {entry_count:,}."
        )

    print(f"Validated: {name} ({entry_count:,} entries)")

    # Preserve original header and entry order
    return "\n".join(output_lines) + "\n"


def main() -> None:
    converted = {}

    # Download and validate every source before updating outputs
    for source in SOURCES:
        content = convert_source(
            source["name"],
            source["url"],
        )
        converted[source["output"]] = content

    # Write outputs only after every source passes validation
    for filename, content in converted.items():
        output_file = ROOT_DIR / filename
        temporary_file = output_file.with_name(
            output_file.name + ".tmp"
        )

        temporary_file.write_bytes(content.encode("utf-8"))
        temporary_file.replace(output_file)

        print(f"Generated: {filename}")

    print("All HaGeZi lists updated successfully.")


if __name__ == "__main__":
    main()
