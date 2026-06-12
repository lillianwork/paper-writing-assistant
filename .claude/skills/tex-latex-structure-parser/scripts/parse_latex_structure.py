#!/usr/bin/env python3
"""Parse LaTeX project structure and emit normalized consistency findings."""

from __future__ import annotations

import argparse
import json
import re
import sys
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

SECTION_LEVELS = {
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
    "paragraph": 4,
    "subparagraph": 5,
}

CITE_RE = re.compile(r"\\([A-Za-z]*cite[A-Za-z*]*)\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|autoref|eqref|[cC]ref)\{([^}]+)\}")
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,]+)\s*,", re.IGNORECASE)
SECTION_RE = re.compile(r"\\(section|subsection|subsubsection|paragraph|subparagraph)\*?\{([^}]+)\}")
INCLUDE_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")


def _is_ignored(root: Path, candidate: Path) -> bool:
    parts = set(candidate.relative_to(root).parts)
    return bool(parts & SKIP_DIRS)


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
    content = escaped.split("%", 1)[0]
    return content.replace("__PERCENT__", r"\%")


def _normalize_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _find_main_tex(tex_files: list[Path]) -> Path | None:
    for path in tex_files:
        if "\\documentclass" in _read_text(path):
            return path
    return tex_files[0] if tex_files else None


def _resolve_include(base_file: Path, include_target: str, project_root: Path) -> Path | None:
    candidate = include_target.strip()
    if not candidate:
        return None
    if not candidate.endswith(".tex"):
        candidate = f"{candidate}.tex"

    local = (base_file.parent / candidate).resolve()
    if local.exists() and local.is_file():
        return local

    project_relative = (project_root / candidate).resolve()
    if project_relative.exists() and project_relative.is_file():
        return project_relative

    return None


def _extract_sections(main_tex: Path, project_root: Path) -> tuple[list[dict[str, object]], set[Path]]:
    sections: list[dict[str, object]] = []
    visited: set[Path] = set()

    def walk(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visited:
            return
        visited.add(resolved)

        try:
            content = _read_text(resolved)
        except OSError:
            return

        for line_no, line in enumerate(content.splitlines(), 1):
            code = _strip_comment(line)

            for match in SECTION_RE.finditer(code):
                name = match.group(2).strip()
                command = match.group(1)
                sections.append(
                    {
                        "name": name,
                        "level": SECTION_LEVELS.get(command, 0),
                        "command": command,
                        "file": _normalize_path(resolved, project_root),
                        "line": line_no,
                    }
                )

            for include_match in INCLUDE_RE.finditer(code):
                include_path = _resolve_include(
                    resolved,
                    include_match.group(1),
                    project_root,
                )
                if include_path is not None:
                    walk(include_path)

    walk(main_tex)
    return sections, visited


def _extract_citations(tex_files: list[Path], project_root: Path) -> list[dict[str, object]]:
    citations: list[dict[str, object]] = []
    for tex_file in tex_files:
        content = _read_text(tex_file)
        rel = _normalize_path(tex_file, project_root)
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


def _extract_refs(tex_files: list[Path], project_root: Path) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for tex_file in tex_files:
        content = _read_text(tex_file)
        rel = _normalize_path(tex_file, project_root)
        for line_no, line in enumerate(content.splitlines(), 1):
            code = _strip_comment(line)
            for match in REF_RE.finditer(code):
                raw = match.group(1)
                for key in [k.strip() for k in raw.split(",") if k.strip()]:
                    refs.append({"key": key, "file": rel, "line": line_no})
    return refs


def _extract_bib_keys(bib_files: list[Path], project_root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for bib_file in bib_files:
        content = _read_text(bib_file)
        rel = _normalize_path(bib_file, project_root)
        for line_no, line in enumerate(content.splitlines(), 1):
            match = BIB_KEY_RE.search(line)
            if match:
                entries.append(
                    {
                        "key": match.group(1).strip(),
                        "file": rel,
                        "line": line_no,
                    }
                )
    return entries


def _extract_environments(
    tex_files: list[Path],
    project_root: Path,
    env_name: str,
    label_prefix: str,
) -> list[dict[str, object]]:
    env_re = re.compile(
        rf"\\begin\{{{env_name}\*?\}}(.*?)\\end\{{{env_name}\*?\}}",
        re.DOTALL,
    )
    label_re = re.compile(r"\\label\{([^}]+)\}")
    caption_re = re.compile(r"\\caption(?:\[[^\]]*\])?\{([^}]*)\}", re.DOTALL)

    results: list[dict[str, object]] = []
    for tex_file in tex_files:
        content = _read_text(tex_file)
        rel = _normalize_path(tex_file, project_root)
        for match in env_re.finditer(content):
            block = match.group(0)
            label_match = label_re.search(block)
            caption_match = caption_re.search(block)
            line_no = content.count("\n", 0, match.start()) + 1

            label = label_match.group(1).strip() if label_match else ""
            caption = ""
            if caption_match:
                caption = " ".join(caption_match.group(1).split())

            results.append(
                {
                    "file": rel,
                    "line": line_no,
                    "label": label,
                    "caption": caption,
                    "expected_prefix": label_prefix,
                    "has_label": bool(label),
                    "has_caption": bool(caption),
                }
            )

    return results


def _first_by_key(items: list[dict[str, object]], key_name: str, key_value: str) -> dict[str, object] | None:
    for item in items:
        if item.get(key_name) == key_value:
            return item
    return None


def _build_issues(
    citations: list[dict[str, object]],
    bib_entries: list[dict[str, object]],
    refs: list[dict[str, object]],
    figures: list[dict[str, object]],
    tables: list[dict[str, object]],
    max_issues: int,
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []

    cited_keys = {item["key"] for item in citations}
    bib_keys = {item["key"] for item in bib_entries}
    ref_keys = {item["key"] for item in refs}

    for key in sorted(cited_keys - bib_keys):
        where = _first_by_key(citations, "key", key)
        issues.append(
            {
                "type": "undefined_citation",
                "severity": "error",
                "key": key,
                "file": where.get("file") if where else None,
                "line": where.get("line") if where else None,
            }
        )

    for key in sorted(bib_keys - cited_keys):
        where = _first_by_key(bib_entries, "key", key)
        issues.append(
            {
                "type": "uncited_bibliography_entry",
                "severity": "warning",
                "key": key,
                "file": where.get("file") if where else None,
                "line": where.get("line") if where else None,
            }
        )

    figure_labels = {fig["label"] for fig in figures if fig.get("label")}
    table_labels = {tab["label"] for tab in tables if tab.get("label")}

    figure_refs = {k for k in ref_keys if str(k).startswith("fig:")}
    table_refs = {k for k in ref_keys if str(k).startswith("tab:")}

    for fig in figures:
        if not fig["has_label"]:
            issues.append(
                {
                    "type": "figure_missing_label",
                    "severity": "error",
                    "file": fig["file"],
                    "line": fig["line"],
                }
            )
        elif not str(fig["label"]).startswith("fig:"):
            issues.append(
                {
                    "type": "figure_label_prefix",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": fig["label"],
                    "expected": "fig:*",
                }
            )
        if not fig["has_caption"]:
            issues.append(
                {
                    "type": "figure_missing_caption",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": fig.get("label") or None,
                }
            )

    for tab in tables:
        if not tab["has_label"]:
            issues.append(
                {
                    "type": "table_missing_label",
                    "severity": "error",
                    "file": tab["file"],
                    "line": tab["line"],
                }
            )
        elif not str(tab["label"]).startswith("tab:"):
            issues.append(
                {
                    "type": "table_label_prefix",
                    "severity": "warning",
                    "file": tab["file"],
                    "line": tab["line"],
                    "label": tab["label"],
                    "expected": "tab:*",
                }
            )
        if not tab["has_caption"]:
            issues.append(
                {
                    "type": "table_missing_caption",
                    "severity": "warning",
                    "file": tab["file"],
                    "line": tab["line"],
                    "label": tab.get("label") or None,
                }
            )

    for label in sorted(figure_labels - figure_refs):
        where = _first_by_key(figures, "label", label)
        issues.append(
            {
                "type": "unreferenced_figure",
                "severity": "warning",
                "label": label,
                "file": where.get("file") if where else None,
                "line": where.get("line") if where else None,
            }
        )

    for label in sorted(table_labels - table_refs):
        where = _first_by_key(tables, "label", label)
        issues.append(
            {
                "type": "unreferenced_table",
                "severity": "warning",
                "label": label,
                "file": where.get("file") if where else None,
                "line": where.get("line") if where else None,
            }
        )

    return issues[:max_issues]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse LaTeX structure (sections/citations/figures/tables) and emit JSON findings."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Path to LaTeX project root (default: current directory).",
    )
    parser.add_argument(
        "--main-tex",
        default=None,
        help="Main .tex entry file path relative to project root.",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=500,
        help="Maximum number of issues to include in output (default: 500).",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"Invalid --project-root: {project_root}", file=sys.stderr)
        return 2

    tex_files = _iter_files(project_root, ".tex")
    bib_files = _iter_files(project_root, ".bib")

    if not tex_files:
        payload = {
            "summary": {
                "project_root": str(project_root),
                "tex_files": 0,
                "bib_files": len(bib_files),
            },
            "issues": [
                {
                    "type": "no_tex_files_found",
                    "severity": "error",
                }
            ],
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2 if args.pretty else None))
        return 1

    if args.main_tex:
        main_tex = (project_root / args.main_tex).resolve()
        if not main_tex.exists():
            print(f"Main TeX file not found: {main_tex}", file=sys.stderr)
            return 2
    else:
        guessed = _find_main_tex(tex_files)
        if guessed is None:
            print("Could not detect a main TeX file.", file=sys.stderr)
            return 2
        main_tex = guessed.resolve()

    sections, traversed = _extract_sections(main_tex, project_root)
    tex_subset = sorted(p for p in traversed if p.exists() and p.suffix == ".tex")
    parse_target_files = tex_subset if tex_subset else tex_files

    citations = _extract_citations(parse_target_files, project_root)
    refs = _extract_refs(parse_target_files, project_root)
    bib_entries = _extract_bib_keys(bib_files, project_root)
    figures = _extract_environments(parse_target_files, project_root, "figure", "fig:")
    tables = _extract_environments(parse_target_files, project_root, "table", "tab:")

    issues = _build_issues(
        citations=citations,
        bib_entries=bib_entries,
        refs=refs,
        figures=figures,
        tables=tables,
        max_issues=max(1, args.max_issues),
    )

    summary = {
        "project_root": str(project_root),
        "main_tex": _normalize_path(main_tex, project_root),
        "tex_files": len(parse_target_files),
        "bib_files": len(bib_files),
        "sections": len(sections),
        "citations": len(citations),
        "unique_citation_keys": len({c["key"] for c in citations}),
        "bib_keys": len({b["key"] for b in bib_entries}),
        "figures": len(figures),
        "tables": len(tables),
        "references": len(refs),
        "issues": len(issues),
    }

    payload = {
        "summary": summary,
        "files": {
            "tex": [_normalize_path(path, project_root) for path in parse_target_files],
            "bib": [_normalize_path(path, project_root) for path in bib_files],
        },
        "sections": sections,
        "citations": citations,
        "bibliography": {"entries": bib_entries},
        "figures": figures,
        "tables": tables,
        "references": refs,
        "issues": issues,
    }

    print(json.dumps(payload, ensure_ascii=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
