#!/usr/bin/env python3
"""Validate citation integrity with local checks and optional Crossref lookups."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".texguardian",
    "_original",
    "backup",
    "build",
    "dist",
    "node_modules",
    "__pycache__",
}

CITE_RE = re.compile(r"\\([A-Za-z]*cite[A-Za-z*]*)\{([^}]+)\}")


@dataclass
class BibEntry:
    key: str
    entry_type: str
    file: str
    line: int
    title: str = ""
    author: str = ""
    year: str = ""
    doi: str = ""
    arxiv: str = ""


def _is_ignored(root: Path, candidate: Path) -> bool:
    return bool(set(candidate.relative_to(root).parts) & SKIP_DIRS)


def _iter_files(root: Path, suffix: str) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob(f"*{suffix}"):
        if path.is_file() and not _is_ignored(root, path):
            files.append(path)
    return sorted(files)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_comment(line: str) -> str:
    escaped = line.replace(r"\%", "__PERCENT__")
    code = escaped.split("%", 1)[0]
    return code.replace("__PERCENT__", r"\%")


def _normalize_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _extract_citations(tex_files: list[Path], root: Path) -> list[dict[str, object]]:
    citations: list[dict[str, object]] = []
    for tex_file in tex_files:
        rel = _normalize_path(tex_file, root)
        content = _read_text(tex_file)
        for line_no, line in enumerate(content.splitlines(), 1):
            code = _strip_comment(line)
            for match in CITE_RE.finditer(code):
                command = match.group(1)
                keys = [k.strip() for k in match.group(2).split(",") if k.strip()]
                for key in keys:
                    citations.append(
                        {
                            "key": key,
                            "command": command,
                            "file": rel,
                            "line": line_no,
                        }
                    )
    return citations


def _parse_bib_fields(fields_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    i = 0
    n = len(fields_text)

    while i < n:
        while i < n and fields_text[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break

        match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", fields_text[i:])
        if not match:
            i += 1
            continue

        field_name = match.group(1).lower()
        i += match.end()

        while i < n and fields_text[i].isspace():
            i += 1
        if i >= n:
            break

        value = ""
        if fields_text[i] == "{":
            depth = 1
            i += 1
            start = i
            while i < n and depth > 0:
                char = fields_text[i]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                i += 1
            value = fields_text[start : i - 1] if depth == 0 else fields_text[start:]
        elif fields_text[i] == '"':
            i += 1
            start = i
            while i < n:
                if fields_text[i] == '"' and fields_text[i - 1] != "\\":
                    break
                i += 1
            value = fields_text[start:i]
            if i < n and fields_text[i] == '"':
                i += 1
        else:
            start = i
            while i < n and fields_text[i] not in ",\n\r":
                i += 1
            value = fields_text[start:i]

        fields[field_name] = " ".join(value.strip().split())

    return fields


def _parse_bib_entries(bib_files: list[Path], root: Path) -> list[BibEntry]:
    entries: list[BibEntry] = []

    for bib_file in bib_files:
        content = _read_text(bib_file)
        rel = _normalize_path(bib_file, root)

        i = 0
        while i < len(content):
            at_index = content.find("@", i)
            if at_index < 0:
                break

            header_match = re.match(r"@(\w+)\s*\{", content[at_index:])
            if not header_match:
                i = at_index + 1
                continue

            entry_type = header_match.group(1).lower()
            open_brace = at_index + header_match.end() - 1

            depth = 1
            j = open_brace + 1
            while j < len(content) and depth > 0:
                char = content[j]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                j += 1

            if depth != 0:
                break

            block = content[open_brace + 1 : j - 1]
            comma_index = block.find(",")
            if comma_index < 0:
                i = j
                continue

            key = block[:comma_index].strip()
            fields_text = block[comma_index + 1 :]
            fields = _parse_bib_fields(fields_text)
            line_no = content.count("\n", 0, at_index) + 1

            entries.append(
                BibEntry(
                    key=key,
                    entry_type=entry_type,
                    file=rel,
                    line=line_no,
                    title=fields.get("title", ""),
                    author=fields.get("author", ""),
                    year=fields.get("year", ""),
                    doi=fields.get("doi", ""),
                    arxiv=fields.get("eprint", fields.get("arxiv", "")),
                )
            )

            i = j

    return entries


def _normalize_title(title: str) -> str:
    if not title:
        return ""

    cleaned = title
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?\{([^}]*)\}", r"\2", cleaned)
    cleaned = re.sub(r"[{}]", "", cleaned)
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().lower()


def _title_match_score(a: str, b: str) -> float:
    na = _normalize_title(a)
    nb = _normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.9

    set_a = set(na.split())
    set_b = set(nb.split())
    if not set_a or not set_b:
        return 0.0
    overlap = len(set_a & set_b)
    union = len(set_a | set_b)
    return overlap / union


def _http_get_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "portable-codex-skill-citation-validator/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read().decode("utf-8", errors="replace")
    return json.loads(data)


def _validate_by_doi(entry: BibEntry, timeout: float) -> dict[str, object]:
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", entry.doi.strip(), flags=re.IGNORECASE)
    if not doi:
        return {"status": "not_found", "message": "Empty DOI"}

    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"

    try:
        payload = _http_get_json(url, timeout)
    except urllib.error.URLError as exc:
        return {"status": "not_found", "message": f"DOI lookup failed: {exc.reason}"}
    except Exception as exc:
        return {"status": "not_found", "message": f"DOI lookup failed: {exc}"}

    message = payload.get("message", {})
    remote_title = ""
    if isinstance(message.get("title"), list) and message["title"]:
        remote_title = str(message["title"][0])

    score = _title_match_score(entry.title, remote_title)
    if score >= 0.6:
        return {
            "status": "valid",
            "confidence": round(score, 3),
            "message": "DOI verified in Crossref",
            "remote": {"doi": doi, "title": remote_title},
        }

    return {
        "status": "needs_correction",
        "confidence": round(score, 3),
        "message": "DOI exists but title mismatch",
        "remote": {"doi": doi, "title": remote_title},
    }


def _validate_by_title(entry: BibEntry, timeout: float) -> dict[str, object]:
    if not entry.title.strip():
        return {"status": "not_found", "message": "No title for remote validation"}

    params = urllib.parse.urlencode(
        {
            "query.title": entry.title,
            "rows": 3,
            "select": "DOI,title,published-print",
        }
    )
    url = f"https://api.crossref.org/works?{params}"

    try:
        payload = _http_get_json(url, timeout)
    except urllib.error.URLError as exc:
        return {"status": "not_found", "message": f"Title lookup failed: {exc.reason}"}
    except Exception as exc:
        return {"status": "not_found", "message": f"Title lookup failed: {exc}"}

    items = payload.get("message", {}).get("items", [])
    if not items:
        return {"status": "likely_hallucinated", "message": "No Crossref results for title"}

    best: dict[str, object] | None = None
    best_score = 0.0
    for item in items:
        remote_title = ""
        titles = item.get("title", [])
        if isinstance(titles, list) and titles:
            remote_title = str(titles[0])

        score = _title_match_score(entry.title, remote_title)
        if score > best_score:
            best_score = score
            best = {
                "title": remote_title,
                "doi": item.get("DOI", ""),
            }

    if best is None:
        return {"status": "likely_hallucinated", "message": "No usable Crossref match"}

    if best_score >= 0.75:
        if entry.doi and best.get("doi") and entry.doi.strip().lower() != str(best["doi"]).lower():
            return {
                "status": "needs_correction",
                "confidence": round(best_score, 3),
                "message": "Best title match suggests DOI correction",
                "remote": best,
            }
        if not entry.doi and best.get("doi"):
            return {
                "status": "needs_correction",
                "confidence": round(best_score, 3),
                "message": "Matching paper found; DOI can be added",
                "remote": best,
            }
        return {
            "status": "valid",
            "confidence": round(best_score, 3),
            "message": "Title validated against Crossref",
            "remote": best,
        }

    return {
        "status": "needs_correction",
        "confidence": round(best_score, 3),
        "message": "Only weak title match found",
        "remote": best,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate citation integrity: local undefined/uncited/style checks, "
            "plus optional remote Crossref verification."
        )
    )
    parser.add_argument("--project-root", default=".", help="Project root path.")
    parser.add_argument(
        "--main-tex",
        default=None,
        help="Main TeX file relative to project root. Defaults to all .tex files.",
    )
    parser.add_argument(
        "--bib-file",
        default=None,
        help="Specific .bib file relative to project root. Defaults to all .bib files.",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Enable remote Crossref validation (network call).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="HTTP timeout in seconds for remote checks (default: 8.0).",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"Invalid --project-root: {project_root}", file=sys.stderr)
        return 2

    if args.main_tex:
        main_tex = (project_root / args.main_tex).resolve()
        if not main_tex.exists():
            print(f"Main TeX not found: {main_tex}", file=sys.stderr)
            return 2
        tex_files = [main_tex]
    else:
        tex_files = _iter_files(project_root, ".tex")

    if args.bib_file:
        bib_path = (project_root / args.bib_file).resolve()
        if not bib_path.exists():
            print(f"Bib file not found: {bib_path}", file=sys.stderr)
            return 2
        bib_files = [bib_path]
    else:
        bib_files = _iter_files(project_root, ".bib")

    citations = _extract_citations(tex_files, project_root)
    bib_entries = _parse_bib_entries(bib_files, project_root)

    cited_keys = {c["key"] for c in citations}
    bib_key_map = {entry.key: entry for entry in bib_entries}
    bib_keys = set(bib_key_map)

    undefined_keys = sorted(cited_keys - bib_keys)
    uncited_keys = sorted(bib_keys - cited_keys)

    local_issues: list[dict[str, object]] = []

    for key in undefined_keys:
        first = next(c for c in citations if c["key"] == key)
        local_issues.append(
            {
                "type": "undefined_citation",
                "severity": "error",
                "key": key,
                "file": first["file"],
                "line": first["line"],
            }
        )

    for key in uncited_keys:
        entry = bib_key_map[key]
        local_issues.append(
            {
                "type": "uncited_bibliography_entry",
                "severity": "warning",
                "key": key,
                "file": entry.file,
                "line": entry.line,
            }
        )

    style_issues = [
        c
        for c in citations
        if str(c.get("command", "")).lower() == "cite"
    ]
    for issue in style_issues:
        local_issues.append(
            {
                "type": "citation_style_generic_cite",
                "severity": "info",
                "key": issue["key"],
                "file": issue["file"],
                "line": issue["line"],
                "message": "Consider replacing \\cite with \\citep or \\citet based on sentence usage.",
            }
        )

    validation_results: list[dict[str, object]] = []
    if args.remote:
        for entry in bib_entries:
            result: dict[str, object]
            if entry.doi:
                result = _validate_by_doi(entry, args.timeout)
                if result.get("status") == "not_found" and entry.title:
                    fallback = _validate_by_title(entry, args.timeout)
                    if fallback.get("status") != "not_found":
                        result = fallback
            elif entry.title:
                result = _validate_by_title(entry, args.timeout)
            else:
                result = {
                    "status": "not_found",
                    "message": "No title or DOI for remote validation",
                }

            validation_results.append(
                {
                    "key": entry.key,
                    "status": result.get("status", "not_found"),
                    "confidence": result.get("confidence", 0.0),
                    "message": result.get("message", ""),
                    "remote": result.get("remote"),
                }
            )

    status_counts: dict[str, int] = {}
    for result in validation_results:
        status = str(result["status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    payload = {
        "summary": {
            "project_root": str(project_root),
            "tex_files": len(tex_files),
            "bib_files": len(bib_files),
            "citations": len(citations),
            "unique_citation_keys": len(cited_keys),
            "bib_entries": len(bib_entries),
            "undefined_citations": len(undefined_keys),
            "uncited_bibliography_entries": len(uncited_keys),
            "style_issues": len(style_issues),
            "remote_validation_enabled": bool(args.remote),
            "remote_status_counts": status_counts,
        },
        "local_issues": local_issues,
        "validation_results": validation_results,
    }

    indent = 2 if args.pretty else None
    print(json.dumps(payload, ensure_ascii=True, indent=indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
