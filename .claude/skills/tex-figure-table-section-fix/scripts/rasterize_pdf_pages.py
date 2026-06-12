#!/usr/bin/env python3
"""Rasterize a paper PDF into page-by-page PNG images for visual review."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
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


def _iter_tex_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.tex"):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & SKIP_DIRS:
            continue
        files.append(path)
    return sorted(files)


def _find_main_tex(project_root: Path, main_tex_arg: str | None) -> Path | None:
    if main_tex_arg:
        candidate = (project_root / main_tex_arg).resolve()
        return candidate if candidate.exists() else None

    for tex_file in _iter_tex_files(project_root):
        content = tex_file.read_text(encoding="utf-8", errors="replace")
        if "\\documentclass" in content:
            return tex_file.resolve()
    return None


def _compile_pdf(main_tex: Path, timeout: int) -> tuple[bool, str]:
    latexmk = shutil.which("latexmk")
    if not latexmk:
        return False, "latexmk not found on PATH"

    cmd = [
        latexmk,
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        main_tex.name,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=main_tex.parent,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"latexmk timed out after {timeout}s"

    if result.returncode != 0:
        output_tail = "\n".join((result.stdout + "\n" + result.stderr).splitlines()[-20:])
        return False, f"latexmk failed with code {result.returncode}\n{output_tail}"

    return True, ""


def _rasterize_pdf(
    pdf_path: Path,
    output_dir: Path,
    dpi: int,
    first_page: int,
    last_page: int | None,
    timeout: int,
) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm not found on PATH")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"

    cmd = [pdftoppm, "-png", "-r", str(dpi), "-f", str(first_page)]
    if last_page is not None:
        cmd.extend(["-l", str(last_page)])
    cmd.extend([str(pdf_path), str(prefix)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed: {result.stderr.strip()}")

    png_files = sorted(output_dir.glob("page-*.png"), key=_page_number)
    return png_files


def _page_number(path: Path) -> int:
    match = re.search(r"-(\d+)$", path.stem)
    if not match:
        return 0
    return int(match.group(1))


def _select_pages(files: list[Path], max_pages: int | None) -> list[Path]:
    if max_pages is None or max_pages <= 0:
        return files
    return files[:max_pages]


def _relative_to_project_or_none(path: Path, project_root: Path) -> str | None:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rasterize a paper PDF into ordered page images. "
            "Designed for page-by-page layout review by an agent."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument(
        "--main-tex",
        default=None,
        help="Main TeX file relative to project root. Used to infer/compile PDF.",
    )
    parser.add_argument(
        "--pdf",
        default=None,
        help="PDF path (absolute or project-root relative). If omitted, inferred from main tex.",
    )
    parser.add_argument(
        "--output-dir",
        default=".agents/renders/page_review",
        help="Output directory for rasterized pages (default: .agents/renders/page_review).",
    )
    parser.add_argument("--dpi", type=int, default=170, help="Rasterization DPI (default: 170).")
    parser.add_argument("--first-page", type=int, default=1, help="First page to render (default: 1).")
    parser.add_argument(
        "--last-page",
        type=int,
        default=None,
        help="Last page to render (inclusive). Defaults to end of document.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit output manifest to first N rendered pages.",
    )
    parser.add_argument(
        "--compile-if-missing",
        action="store_true",
        help="Compile with latexmk if target PDF is missing.",
    )
    parser.add_argument(
        "--force-compile",
        action="store_true",
        help="Always run latexmk before rasterization (requires main tex).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help="Timeout in seconds for compile/rasterize commands (default: 240).",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"Invalid --project-root: {project_root}", file=sys.stderr)
        return 2

    main_tex = _find_main_tex(project_root, args.main_tex)

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_absolute():
            pdf_path = (project_root / pdf_path).resolve()
    else:
        if not main_tex:
            print("Could not infer PDF: provide --pdf or --main-tex", file=sys.stderr)
            return 2
        pdf_path = main_tex.with_suffix(".pdf")

    needs_compile = args.force_compile or (args.compile_if_missing and not pdf_path.exists())
    if needs_compile:
        if not main_tex:
            print("Compile requested but main TeX file could not be resolved", file=sys.stderr)
            return 2
        ok, err = _compile_pdf(main_tex, timeout=args.timeout)
        if not ok:
            print(err, file=sys.stderr)
            return 1

    if not pdf_path.exists():
        print(
            f"PDF not found: {pdf_path}. Use --compile-if-missing or provide an existing --pdf.",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (project_root / output_dir).resolve()

    try:
        rendered = _rasterize_pdf(
            pdf_path=pdf_path,
            output_dir=output_dir,
            dpi=max(72, args.dpi),
            first_page=max(1, args.first_page),
            last_page=args.last_page,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    selected = _select_pages(rendered, args.max_pages)
    pages = [
        {
            "page": _page_number(path),
            "image": str(path),
            "image_relative_to_project": _relative_to_project_or_none(path, project_root),
        }
        for path in selected
    ]

    payload = {
        "summary": {
            "project_root": str(project_root),
            "pdf": str(pdf_path),
            "output_dir": str(output_dir),
            "dpi": max(72, args.dpi),
            "rendered_pages": len(rendered),
            "listed_pages": len(pages),
        },
        "pages": pages,
        "review_instruction": (
            "Open each page image in order and inspect layout issues page by page "
            "(overflow, clipping, spacing, caption overlap, table alignment, figure placement)."
        ),
    }

    print(json.dumps(payload, ensure_ascii=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
