#!/usr/bin/env python3
"""Build page-by-page layout review templates from rasterized PDF pages.

This script does not call any external vision API. It prepares a deterministic
review scaffold so an agent (or human) can inspect each page image in order.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

DEFAULT_CHECKS = [
    "overflow_or_clipping",
    "figure_table_placement",
    "caption_overlap",
    "spacing_and_alignment",
    "font_or_resolution_consistency",
]


def _parse_png_dimensions(path: Path) -> tuple[int | None, int | None]:
    """Read PNG width/height from IHDR without external dependencies."""
    try:
        data = path.read_bytes()
    except OSError:
        return None, None

    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        return None, None

    # Bytes 16..24 are IHDR width and height (big-endian uint32)
    try:
        width, height = struct.unpack(">II", data[16:24])
    except struct.error:
        return None, None
    return width, height


def _extract_page_number(path: Path) -> int:
    match = re.search(r"(\d+)", path.stem)
    if not match:
        return 0
    return int(match.group(1))


def _iter_pages_from_images_dir(images_dir: Path, pattern: str) -> list[dict[str, object]]:
    if not images_dir.exists() or not images_dir.is_dir():
        return []

    pages: list[dict[str, object]] = []
    for image in sorted(images_dir.glob(pattern), key=_extract_page_number):
        if image.is_file():
            pages.append({"page": _extract_page_number(image), "image": str(image.resolve())})
    return pages


def _iter_pages_from_manifest(manifest_path: Path, project_root: Path) -> list[dict[str, object]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_pages = payload.get("pages", [])
    pages: list[dict[str, object]] = []

    for item in raw_pages:
        if not isinstance(item, dict):
            continue

        page_num = int(item.get("page", 0))
        image_path = item.get("image")
        if not image_path:
            rel = item.get("image_relative_to_project")
            if rel:
                image_path = str((project_root / str(rel)).resolve())

        if image_path:
            pages.append({"page": page_num, "image": str(Path(str(image_path)).resolve())})

    pages.sort(key=lambda x: int(x.get("page", 0)))
    return pages


def _auto_flags(page: dict[str, object], dominant_size: tuple[int, int] | None) -> list[str]:
    flags: list[str] = []

    width = page.get("width")
    height = page.get("height")
    size_bytes = page.get("bytes", 0)

    if isinstance(width, int) and isinstance(height, int):
        if width < 900 or height < 1200:
            flags.append("low_resolution_risk")
        if dominant_size and (width, height) != dominant_size:
            flags.append("size_inconsistency")

    if isinstance(size_bytes, int) and size_bytes < 25_000:
        flags.append("possible_sparse_or_blank_page")

    return flags


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create page-by-page layout review templates from rasterized images. "
            "No external vision API is used."
        )
    )
    parser.add_argument("--project-root", default=".", help="Project root directory.")
    parser.add_argument(
        "--manifest",
        default=None,
        help="JSON manifest from rasterize_pdf_pages.py (preferred input).",
    )
    parser.add_argument(
        "--images-dir",
        default=".agents/renders/page_review",
        help="Directory containing rasterized page images.",
    )
    parser.add_argument(
        "--glob",
        default="page-*.png",
        help="Glob pattern when scanning --images-dir (default: page-*.png).",
    )
    parser.add_argument(
        "--checks",
        default=",".join(DEFAULT_CHECKS),
        help="Comma-separated checklist items for each page review template.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write JSON output. If omitted, prints to stdout.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"Invalid --project-root: {project_root}", file=sys.stderr)
        return 2

    checks = [c.strip() for c in str(args.checks).split(",") if c.strip()]
    if not checks:
        checks = list(DEFAULT_CHECKS)

    pages: list[dict[str, object]]
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = (project_root / manifest_path).resolve()
        if not manifest_path.exists():
            print(f"Manifest not found: {manifest_path}", file=sys.stderr)
            return 2
        pages = _iter_pages_from_manifest(manifest_path, project_root)
    else:
        images_dir = Path(args.images_dir)
        if not images_dir.is_absolute():
            images_dir = (project_root / images_dir).resolve()
        pages = _iter_pages_from_images_dir(images_dir, args.glob)

    if not pages:
        print("No page images found. Run rasterize_pdf_pages.py first.", file=sys.stderr)
        return 1

    # Compute metadata and dominant dimensions
    enriched: list[dict[str, object]] = []
    dims: list[tuple[int, int]] = []

    for page in pages:
        image_path = Path(str(page["image"]))
        width, height = _parse_png_dimensions(image_path)
        size_bytes = image_path.stat().st_size if image_path.exists() else 0

        if isinstance(width, int) and isinstance(height, int):
            dims.append((width, height))

        enriched.append(
            {
                "page": int(page.get("page", 0)),
                "image": str(image_path),
                "image_relative_to_project": (
                    str(image_path.relative_to(project_root))
                    if image_path.is_absolute() and str(image_path).startswith(str(project_root))
                    else None
                ),
                "width": width,
                "height": height,
                "bytes": size_bytes,
            }
        )

    dominant_size: tuple[int, int] | None = None
    if dims:
        dominant_size = Counter(dims).most_common(1)[0][0]

    review_pages: list[dict[str, object]] = []
    for page in enriched:
        flags = _auto_flags(page, dominant_size)
        review_pages.append(
            {
                "page": page["page"],
                "image": page["image"],
                "image_relative_to_project": page["image_relative_to_project"],
                "metadata": {
                    "width": page["width"],
                    "height": page["height"],
                    "bytes": page["bytes"],
                },
                "auto_flags": flags,
                "review_template": {
                    "page_score": None,
                    "status": "pending",
                    "checks": [{"name": c, "result": "pending", "note": ""} for c in checks],
                    "issues": [],
                    "notes": "",
                },
            }
        )

    payload = {
        "summary": {
            "project_root": str(project_root),
            "total_pages": len(review_pages),
            "dominant_image_size": {
                "width": dominant_size[0],
                "height": dominant_size[1],
            }
            if dominant_size
            else None,
            "auto_flag_counts": Counter(
                flag for p in review_pages for flag in p.get("auto_flags", [])
            ),
            "overall_status": "pending_manual_review",
        },
        "pages": review_pages,
        "aggregate_template": {
            "overall_score": None,
            "blocking_issues": [],
            "high_priority_fixes": [],
            "page_order_reviewed": [],
            "final_notes": "",
        },
        "review_instruction": (
            "Inspect images page by page in ascending order. Fill each page's review_template, "
            "then complete aggregate_template for final layout decision."
        ),
    }

    # Convert Counter to plain dict for stable JSON output
    payload["summary"]["auto_flag_counts"] = dict(payload["summary"]["auto_flag_counts"])

    text = json.dumps(payload, ensure_ascii=True, indent=2 if args.pretty else None)
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = (project_root / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
