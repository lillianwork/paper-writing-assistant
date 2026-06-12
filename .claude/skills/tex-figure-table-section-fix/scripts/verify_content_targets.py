#!/usr/bin/env python3
"""Verify figures, tables, or a specific section using deterministic checks."""

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

INCLUDE_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|autoref|eqref|[cC]ref)\{([^}]+)\}")
SECTION_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^}]+)\}")


def _is_ignored(root: Path, candidate: Path) -> bool:
    return bool(set(candidate.relative_to(root).parts) & SKIP_DIRS)


def _iter_tex_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.tex"):
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


def _find_main_tex(tex_files: list[Path]) -> Path | None:
    for path in tex_files:
        if "\\documentclass" in _read_text(path):
            return path
    return tex_files[0] if tex_files else None


def _resolve_include(base_file: Path, include_target: str, project_root: Path) -> Path | None:
    target = include_target.strip()
    if not target:
        return None
    if not target.endswith(".tex"):
        target = f"{target}.tex"

    local = (base_file.parent / target).resolve()
    if local.exists() and local.is_file():
        return local

    project_relative = (project_root / target).resolve()
    if project_relative.exists() and project_relative.is_file():
        return project_relative

    return None


def _collect_main_tex_tree(main_tex: Path, project_root: Path) -> list[Path]:
    visited: set[Path] = set()
    ordered: list[Path] = []

    def walk(path: Path) -> None:
        resolved = path.resolve()
        if resolved in visited:
            return
        visited.add(resolved)
        ordered.append(resolved)

        try:
            content = _read_text(resolved)
        except OSError:
            return

        for line in content.splitlines():
            code = _strip_comment(line)
            for match in INCLUDE_RE.finditer(code):
                include_path = _resolve_include(resolved, match.group(1), project_root)
                if include_path is not None:
                    walk(include_path)

    walk(main_tex)
    return ordered


def _extract_refs(tex_files: list[Path], root: Path) -> list[dict[str, object]]:
    refs: list[dict[str, object]] = []
    for tex_file in tex_files:
        rel = _normalize_path(tex_file, root)
        content = _read_text(tex_file)
        for line_no, line in enumerate(content.splitlines(), 1):
            code = _strip_comment(line)
            for match in REF_RE.finditer(code):
                for key in [k.strip() for k in match.group(1).split(",") if k.strip()]:
                    refs.append({"key": key, "file": rel, "line": line_no})
    return refs


def _extract_envs(tex_files: list[Path], root: Path, env_name: str) -> list[dict[str, object]]:
    env_re = re.compile(
        rf"\\begin\{{{env_name}\*?\}}(.*?)\\end\{{{env_name}\*?\}}",
        re.DOTALL,
    )
    label_re = re.compile(r"\\label\{([^}]+)\}")
    caption_re = re.compile(r"\\caption(?:\[[^\]]*\])?\{([^}]*)\}", re.DOTALL)

    items: list[dict[str, object]] = []
    for tex_file in tex_files:
        rel = _normalize_path(tex_file, root)
        content = _read_text(tex_file)
        for match in env_re.finditer(content):
            block = match.group(0)
            line_no = content.count("\n", 0, match.start()) + 1

            label_match = label_re.search(block)
            caption_match = caption_re.search(block)

            label = label_match.group(1).strip() if label_match else ""
            caption = ""
            if caption_match:
                caption = " ".join(caption_match.group(1).split())

            items.append(
                {
                    "file": rel,
                    "line": line_no,
                    "label": label,
                    "caption": caption,
                    "content": block,
                }
            )

    return items


def _verify_figures(tex_files: list[Path], refs: list[dict[str, object]], root: Path) -> dict[str, object]:
    figures = _extract_envs(tex_files, root, "figure")
    ref_keys = {ref["key"] for ref in refs}

    issues: list[dict[str, object]] = []
    entities: list[dict[str, object]] = []

    for fig in figures:
        label = str(fig.get("label", ""))
        caption = str(fig.get("caption", ""))
        content = str(fig.get("content", ""))
        ref_count = sum(1 for ref in refs if ref["key"] == label) if label else 0

        entities.append(
            {
                "file": fig["file"],
                "line": fig["line"],
                "label": label,
                "caption": caption,
                "ref_count": ref_count,
            }
        )

        if not label:
            issues.append(
                {
                    "type": "missing_label",
                    "severity": "error",
                    "file": fig["file"],
                    "line": fig["line"],
                }
            )
        elif not label.startswith("fig:"):
            issues.append(
                {
                    "type": "label_prefix",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": label,
                    "expected": "fig:*",
                }
            )
        elif label not in ref_keys:
            issues.append(
                {
                    "type": "unreferenced",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": label,
                }
            )

        if not caption:
            issues.append(
                {
                    "type": "missing_caption",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": label or None,
                }
            )
        elif len(caption) < 20:
            issues.append(
                {
                    "type": "caption_too_short",
                    "severity": "info",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": label or None,
                }
            )

        width_match = re.search(
            r"width\s*=\s*(\d+(?:\.\d+)?)\s*\\(?:columnwidth|textwidth)",
            content,
        )
        if width_match and float(width_match.group(1)) > 1.0:
            issues.append(
                {
                    "type": "overflow_width",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": label or None,
                    "value": width_match.group(1),
                }
            )

        if re.search(r"\\hspace\s*\{-", content):
            issues.append(
                {
                    "type": "negative_hspace",
                    "severity": "warning",
                    "file": fig["file"],
                    "line": fig["line"],
                    "label": label or None,
                }
            )

    return {"entities": entities, "issues": issues}


def _verify_tables(tex_files: list[Path], refs: list[dict[str, object]], root: Path) -> dict[str, object]:
    tables = _extract_envs(tex_files, root, "table")
    ref_keys = {ref["key"] for ref in refs}

    issues: list[dict[str, object]] = []
    entities: list[dict[str, object]] = []

    for table in tables:
        label = str(table.get("label", ""))
        caption = str(table.get("caption", ""))
        content = str(table.get("content", ""))
        ref_count = sum(1 for ref in refs if ref["key"] == label) if label else 0

        entities.append(
            {
                "file": table["file"],
                "line": table["line"],
                "label": label,
                "caption": caption,
                "ref_count": ref_count,
            }
        )

        if not label:
            issues.append(
                {
                    "type": "missing_label",
                    "severity": "error",
                    "file": table["file"],
                    "line": table["line"],
                }
            )
        elif not label.startswith("tab:"):
            issues.append(
                {
                    "type": "label_prefix",
                    "severity": "warning",
                    "file": table["file"],
                    "line": table["line"],
                    "label": label,
                    "expected": "tab:*",
                }
            )
        elif label not in ref_keys:
            issues.append(
                {
                    "type": "unreferenced",
                    "severity": "warning",
                    "file": table["file"],
                    "line": table["line"],
                    "label": label,
                }
            )

        if not caption:
            issues.append(
                {
                    "type": "missing_caption",
                    "severity": "warning",
                    "file": table["file"],
                    "line": table["line"],
                    "label": label or None,
                }
            )

        if "\\hline" in content and "\\toprule" not in content:
            issues.append(
                {
                    "type": "no_booktabs",
                    "severity": "info",
                    "file": table["file"],
                    "line": table["line"],
                    "label": label or None,
                }
            )

    return {"entities": entities, "issues": issues}


def _extract_sections(tex_files: list[Path], root: Path) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []

    for tex_file in tex_files:
        rel = _normalize_path(tex_file, root)
        lines = _read_text(tex_file).splitlines()

        current: dict[str, object] | None = None
        for line_no, line in enumerate(lines, 1):
            code = _strip_comment(line)
            match = SECTION_RE.search(code)
            if match:
                if current is not None:
                    current["content"] = "\n".join(current["content_lines"])
                    current.pop("content_lines", None)
                    sections.append(current)

                current = {
                    "name": match.group(2).strip(),
                    "level": match.group(1),
                    "file": rel,
                    "line": line_no,
                    "content_lines": [],
                }
                continue

            if current is not None:
                current["content_lines"].append(code)

        if current is not None:
            current["content"] = "\n".join(current["content_lines"])
            current.pop("content_lines", None)
            sections.append(current)

    return sections


def _verify_section(
    tex_files: list[Path],
    root: Path,
    section_name: str,
    min_words: int,
) -> dict[str, object]:
    sections = _extract_sections(tex_files, root)
    match = next((s for s in sections if section_name.lower() in str(s["name"]).lower()), None)

    if match is None:
        return {
            "entities": [],
            "issues": [
                {
                    "type": "section_not_found",
                    "severity": "error",
                    "section": section_name,
                }
            ],
            "available_sections": [s["name"] for s in sections],
        }

    content = str(match.get("content", ""))
    lines = content.splitlines()
    words = [w for w in re.split(r"\s+", content.strip()) if w]

    issues: list[dict[str, object]] = []

    if len(words) < min_words:
        issues.append(
            {
                "type": "section_too_short",
                "severity": "warning",
                "section": match["name"],
                "word_count": len(words),
                "minimum": min_words,
            }
        )

    placeholder_re = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b", re.IGNORECASE)
    for idx, line in enumerate(lines, 1):
        if placeholder_re.search(line):
            issues.append(
                {
                    "type": "placeholder_text",
                    "severity": "warning",
                    "section": match["name"],
                    "line": idx,
                    "content": line.strip(),
                }
            )

    claim_re = re.compile(r"\b(we show|we propose|our method|results show|outperform|state of the art)\b", re.IGNORECASE)
    for idx, line in enumerate(lines, 1):
        normalized = line.strip()
        if not normalized:
            continue
        if claim_re.search(normalized) and "\\cite" not in normalized and "\\ref" not in normalized:
            issues.append(
                {
                    "type": "potential_unsupported_claim",
                    "severity": "info",
                    "section": match["name"],
                    "line": idx,
                    "content": normalized,
                }
            )

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    for paragraph in paragraphs:
        paragraph_words = [w for w in re.split(r"\s+", paragraph) if w]
        if len(paragraph_words) > 220:
            issues.append(
                {
                    "type": "paragraph_too_long",
                    "severity": "info",
                    "section": match["name"],
                    "word_count": len(paragraph_words),
                }
            )

    return {
        "entities": [
            {
                "name": match["name"],
                "file": match["file"],
                "line": match["line"],
                "word_count": len(words),
            }
        ],
        "issues": issues,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify figures, tables, or a specific section and emit JSON findings."
    )
    parser.add_argument("--project-root", default=".", help="LaTeX project root.")
    parser.add_argument(
        "--main-tex",
        default=None,
        help="Main .tex file relative to project root. Default: auto-detect.",
    )
    parser.add_argument(
        "--target",
        choices=("figures", "tables", "section"),
        required=True,
        help="Verification target.",
    )
    parser.add_argument(
        "--section-name",
        default="",
        help="Section name (required when --target section).",
    )
    parser.add_argument(
        "--min-section-words",
        type=int,
        default=120,
        help="Minimum acceptable words for section checks (default: 120).",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.target == "section" and not args.section_name.strip():
        print("--section-name is required when --target section", file=sys.stderr)
        return 2

    project_root = Path(args.project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"Invalid --project-root: {project_root}", file=sys.stderr)
        return 2

    all_tex_files = _iter_tex_files(project_root)
    if not all_tex_files:
        print("No .tex files found.", file=sys.stderr)
        return 1

    if args.main_tex:
        main_tex = (project_root / args.main_tex).resolve()
        if not main_tex.exists():
            print(f"Main TeX not found: {main_tex}", file=sys.stderr)
            return 2
    else:
        detected = _find_main_tex(all_tex_files)
        if detected is None:
            print("Could not auto-detect main TeX file.", file=sys.stderr)
            return 2
        main_tex = detected.resolve()

    tex_files = _collect_main_tex_tree(main_tex, project_root)
    refs = _extract_refs(tex_files, project_root)

    if args.target == "figures":
        result = _verify_figures(tex_files, refs, project_root)
    elif args.target == "tables":
        result = _verify_tables(tex_files, refs, project_root)
    else:
        result = _verify_section(
            tex_files,
            project_root,
            args.section_name.strip(),
            max(1, args.min_section_words),
        )

    payload = {
        "target": args.target,
        "summary": {
            "project_root": str(project_root),
            "main_tex": _normalize_path(main_tex, project_root),
            "tex_files": len(tex_files),
            "references": len(refs),
            "entities": len(result.get("entities", [])),
            "issues": len(result.get("issues", [])),
        },
        "entities": result.get("entities", []),
        "issues": result.get("issues", []),
    }

    if args.target == "section" and "available_sections" in result:
        payload["available_sections"] = result["available_sections"]

    print(json.dumps(payload, ensure_ascii=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
