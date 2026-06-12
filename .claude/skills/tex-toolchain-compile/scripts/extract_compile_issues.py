#!/usr/bin/env python3
"""Extract actionable errors and warnings from LaTeX compile logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEX_LOG_LINE_WIDTH = 79


def _unwrap_log_lines(text: str) -> str:
    lines = text.split("\n")
    merged: list[str] = []
    i = 0
    while i < len(lines):
        current = lines[i]
        while len(current) >= TEX_LOG_LINE_WIDTH and i + 1 < len(lines):
            i += 1
            current += lines[i]
        merged.append(current)
        i += 1
    return "\n".join(merged)


def extract_errors(log: str, limit: int) -> list[str]:
    lines = _unwrap_log_lines(log).split("\n")
    errors: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("! "):
            entry = line
            for j in range(i + 1, min(i + 6, len(lines))):
                loc_match = re.match(r"^l\.(\d+)\s+(.*)$", lines[j].strip())
                if loc_match:
                    entry = f"{entry}  [l.{loc_match.group(1)}]"
                    i = j
                    break
            errors.append(entry)
        elif line.startswith("LaTeX Error:"):
            errors.append(line)
        elif re.match(r"^Package\s+\S+\s+Error:", line):
            errors.append(line)

        if len(errors) >= limit:
            break
        i += 1

    return errors


def extract_warnings(log: str, limit: int) -> list[str]:
    unwrapped = _unwrap_log_lines(log)
    warnings: list[str] = []

    patterns = [
        r"^LaTeX Warning: .+$",
        r"^Package \S+ Warning: .+$",
        r"^Overfull \\hbox.+$",
        r"^Underfull \\hbox.+$",
        r"^Overfull \\vbox.+$",
        r"^Underfull \\vbox.+$",
    ]

    for raw_line in unwrapped.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if any(re.match(pattern, line) for pattern in patterns):
            warnings.append(line)
            if len(warnings) >= limit:
                break

    return warnings


def _detect_fatal(log: str) -> bool:
    fatal_patterns = [
        r"Emergency stop",
        r"Fatal error occurred",
        r"No pages of output",
        r"error in previous invocation",
    ]
    return any(re.search(pattern, log, flags=re.IGNORECASE) for pattern in fatal_patterns)


def _load_log_text(args: argparse.Namespace) -> str:
    if args.log_file:
        return Path(args.log_file).read_text(errors="replace")
    if args.log_text is not None:
        return args.log_text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("Provide --log-file, --log-text, or pipe log content via stdin.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse LaTeX compile output and emit structured errors/warnings JSON."
    )
    parser.add_argument("--log-file", help="Path to a .log file or compile output file.")
    parser.add_argument("--log-text", help="Compile output passed as a direct string.")
    parser.add_argument(
        "--max-errors",
        type=int,
        default=20,
        help="Maximum number of extracted errors (default: 20).",
    )
    parser.add_argument(
        "--max-warnings",
        type=int,
        default=20,
        help="Maximum number of extracted warnings (default: 20).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--fail-on-errors",
        action="store_true",
        help="Exit with status 1 when fatal or non-empty errors are found.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        log_text = _load_log_text(args)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    errors = extract_errors(log_text, max(1, args.max_errors))
    warnings = extract_warnings(log_text, max(1, args.max_warnings))
    fatal = _detect_fatal(log_text)

    payload = {
        "fatal": fatal,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }

    indent = 2 if args.pretty else None
    print(json.dumps(payload, ensure_ascii=True, indent=indent))

    if args.fail_on_errors and (fatal or errors):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
