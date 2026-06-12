#!/usr/bin/env python3
"""Check local LaTeX toolchain availability for portable Codex skills."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_TOOLS: list[tuple[str, str]] = [
    ("latexmk", "latex"),
    ("pdflatex", "latex"),
    ("pdfinfo", "poppler"),
    ("pdftoppm", "poppler"),
]


def _latex_search_paths() -> list[str]:
    paths: list[str] = []

    env_path = os.environ.get("LATEX_PATH", "").strip()
    if env_path:
        paths.append(env_path)

    system = platform.system()
    machine = platform.machine() or "x86_64"

    if system == "Darwin":
        paths.append(str(Path.home() / "Library/TinyTeX/bin/universal-darwin"))
        paths.extend(["/Library/TeX/texbin", "/usr/texbin"])  # MacTeX
    elif system == "Linux":
        paths.append(str(Path.home() / ".TinyTeX/bin/x86_64-linux"))
        paths.append(f"/usr/local/texlive/current/bin/{machine}-linux")

    paths.extend(["/usr/bin", "/usr/local/bin"])
    return paths


def _poppler_search_paths() -> list[str]:
    system = platform.system()
    machine = platform.machine() or ""
    if system == "Darwin" and machine == "arm64":
        return ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
    return ["/usr/bin", "/usr/local/bin"]


def _install_hint(tool: str) -> str:
    system = platform.system()
    hints: dict[str, dict[str, str]] = {
        "latexmk": {
            "Darwin": "Install TinyTeX or MacTeX (e.g. brew install --cask mactex-no-gui).",
            "Linux": "Install TeX Live (e.g. sudo apt install texlive-full).",
        },
        "pdflatex": {
            "Darwin": "Install TinyTeX or MacTeX.",
            "Linux": "Install TeX Live base (e.g. sudo apt install texlive-latex-base).",
        },
        "pdfinfo": {
            "Darwin": "Install Poppler (brew install poppler).",
            "Linux": "Install poppler-utils (sudo apt install poppler-utils).",
        },
        "pdftoppm": {
            "Darwin": "Install Poppler (brew install poppler).",
            "Linux": "Install poppler-utils (sudo apt install poppler-utils).",
        },
    }
    return hints.get(tool, {}).get(system, "Install and ensure this binary is on PATH.")


def _find_binary(name: str, category: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found

    search_dirs = _latex_search_paths() if category == "latex" else _poppler_search_paths()
    for directory in search_dirs:
        candidate = Path(directory) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _parse_tools(raw: str) -> list[tuple[str, str]]:
    tools: list[tuple[str, str]] = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if ":" in token:
            name, category = token.split(":", 1)
            tools.append((name.strip(), category.strip() or "latex"))
        else:
            tools.append((token, "latex"))
    return tools or DEFAULT_TOOLS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether required LaTeX and rendering binaries are available. "
            "Use <name> or <name:category> items in --tools (categories: latex,poppler)."
        )
    )
    parser.add_argument(
        "--tools",
        default=",".join(f"{name}:{category}" for name, category in DEFAULT_TOOLS),
        help="Comma-separated tools to check (default: latexmk,pdflatex,pdfinfo,pdftoppm).",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with status 1 when any required tool is missing.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    tools = _parse_tools(args.tools)

    statuses: list[dict[str, object]] = []
    for name, category in tools:
        path = _find_binary(name, category)
        found = path is not None
        item: dict[str, object] = {
            "name": name,
            "category": category,
            "found": found,
            "path": path,
        }
        if not found:
            item["install_hint"] = _install_hint(name)
        statuses.append(item)

    payload = {
        "checked_at": datetime.now(UTC).isoformat(),
        "all_found": all(item["found"] for item in statuses),
        "tools": statuses,
    }

    if args.format == "json":
        indent = 2 if args.pretty else None
        print(json.dumps(payload, ensure_ascii=True, indent=indent))
    else:
        for item in statuses:
            status = "OK" if item["found"] else "MISSING"
            line = f"[{status}] {item['name']} ({item['category']})"
            if item["path"]:
                line += f" -> {item['path']}"
            print(line)
            if item.get("install_hint"):
                print(f"  hint: {item['install_hint']}")

    if args.fail_on_missing and not payload["all_found"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
