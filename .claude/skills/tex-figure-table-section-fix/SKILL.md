---
name: tex-figure-table-section-fix
description: Use when targeted quality fixes are needed for figures, tables, or named sections, including verify-first remediation, scoped patching, and optional visual verification.
---

# Tex Figure Table Section Fix

## Overview
Use this skill for localized quality remediation. Keep scope tight: one target area at a time, evidence first, patch second.

## Executable Entry Points
- `scripts/verify_content_targets.py`: verifies one target scope at a time (`figures`, `tables`, or `section`) and outputs JSON issues.
- `scripts/rasterize_pdf_pages.py`: rasterizes paper PDF into ordered page PNGs for page-by-page visual layout review.
- `scripts/review_raster_pages.py`: builds per-page scoring templates and aggregate issue summary scaffold from rasterized images.

Example commands:
```bash
python scripts/verify_content_targets.py --project-root . --main-tex main.tex --target figures --pretty
python scripts/verify_content_targets.py --project-root . --main-tex main.tex --target tables --pretty
python scripts/verify_content_targets.py --project-root . --main-tex main.tex --target section --section-name Introduction --pretty
python scripts/rasterize_pdf_pages.py --project-root . --main-tex main.tex --compile-if-missing --pretty
python scripts/review_raster_pages.py --project-root . --images-dir .agents/renders/page_review --pretty
```

## Project Adaptation
1. Identify commands or scripts used to run figure/table/section checks.
2. Confirm local conventions (caption length, label format, booktabs policy, section style requirements).
3. Confirm whether visual verification is available (PDF render + vision review).

## Workflow
1. Choose one target scope:
   - figures
   - tables
   - specific section
2. Run verify-first checks via `scripts/verify_content_targets.py` and capture explicit issues.
3. Typical figure/table checks:
   - missing labels/captions
   - unreferenced labels
   - overflow width or placement issues
   - table formatting problems (for example missing booktabs style)
4. Typical section checks:
   - weak structure or flow
   - unsupported claims / missing citations
   - TODO markers and placeholder text
5. Generate minimal unified diffs with precise context.
6. Apply through approval flow.
7. If layout risk remains, run page-by-page visual review:
   - generate rasterized pages with `scripts/rasterize_pdf_pages.py`
   - build review scaffold with `scripts/review_raster_pages.py`
   - inspect PNGs in order and fill per-page score/issues
   - patch only confirmed, visible issues
8. Re-analyze and stop when residual issues are acceptable.

## Inputs and Outputs
- Input: parsed structure facts, target scope, optional user instruction.
- Output: scoped patch set and post-fix quality findings.

## Thesis Project Configuration

- **Thesis root**: `F:\人大管科\李良艳的大论文\`
- **Table style**: `booktabs` (三线表) — required by most Chinese university thesis templates
- **Figure format**: PDF vector graphics preferred; PNG at ≥300 DPI for raster
- **Caption conventions**: Bilingual (Chinese above, English below) or Chinese-only depending on university requirements
- **Section naming**: Chinese section titles with `\chapter{}`, `\section{}`, `\subsection{}`
- **Layout review**: Pay extra attention to figure/table placement in two-sided (twoside) thesis layout

## Common Mistakes
- Skipping verify and jumping straight to free-form edits.
- Combining figures/tables/sections into one broad patch batch.
- Ignoring visual verification for layout-sensitive issues.
- Continuing auto-fix after repeated quality regression.
