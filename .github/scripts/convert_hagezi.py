#!/usr/bin/env python3
"""Convert HaGeZi's Wildcard Asterisk list to a Surge DOMAIN-SET list."""

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

    try:
        with urlopen(request, timeout=120) as response:
            raw = response.read()
    except Exception as exc:  # keep the old output if the source cannot be fetched
        fail(f"Download failed: {exc}")

    if len(raw) < MINIMUM_DOWNLOAD_BYTES:
        fail(f"Downloaded file is unexpectedly small ({len(raw)} bytes).")

    try:
        source_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        fail(f"Source is not valid UTF-8: {exc}")

    converted: list[str] = []
    invalid: list[tuple[int, str]] = []

    for line_number, raw_line in enumerate(source_text.splitlines(), start=1):
        line = raw_line.strip()

        # Ignore blank lines and common blocklist comment prefixes.
        if not line or line.startswith(("#", "!", ";", "//")):
            continue

        # The selected HaGeZi source is the Wildcard Asterisk format.
        # A leading "*." becomes Surge DOMAIN-SET's leading ".".
        if not line.startswith("*."):
            invalid.append((line_number, line))
            continue

        domain = line[2:].lower()
        if (
            not domain
            or "." not in domain
            or any(ch.isspace() for ch in domain)
            or any(ch in domain for ch in "*/\\,")
        ):
            invalid.append((line_number, line))
            continue

        converted.append("." + domain)

    if invalid:
        examples = "\n".join(
            f"  line {number}: {value}" for number, value in invalid[:5]
        )
        fail(
            "The source contains lines that do not match the expected '*.domain' "
            f"format. No output was replaced. Examples:\n{examples}"
        )

    # Deduplicate while preserving the source order.
    converted = list(dict.fromkeys(converted))

    if len(converted) < MINIMUM_ENTRIES:
        fail(
            f"Only {len(converted):,} entries were converted; expected at least "
            f"{MINIMUM_ENTRIES:,}. No output was replaced."
        )

    output = (
        "# HaGeZi Multi PRO++ converted for Surge DOMAIN-SET\n"
        f"# Source: {SOURCE_URL}\n"
        + "\n".join(converted)
        + "\n"
    )

    # Write atomically so an interrupted run cannot leave a truncated list.
    temporary_file = OUTPUT_FILE.with_name(OUTPUT_FILE.name + ".tmp")
    temporary_file.write_bytes(output.encode("utf-8"))
    temporary_file.replace(OUTPUT_FILE)

    print(
        f"Success: {len(converted):,} unique domains written to "
        f"{OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size:,} bytes)."
    )


if __name__ == "__main__":
    main()
