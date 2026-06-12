---
name: tex-citation-validate-fix
description: Use when citation integrity work is needed, including undefined refs, citation style normalization, external metadata validation, hallucination detection, and patch-based correction.
---

# Tex Citation Validate Fix

## Overview
Use this skill for end-to-end citation integrity: local consistency checks, external validation, then minimal corrective patches.

## Executable Entry Points
- `scripts/validate_citations.py`: runs local citation integrity checks and optional Crossref validation.

Example commands:
```bash
python scripts/validate_citations.py --project-root . --main-tex main.tex --pretty
python scripts/validate_citations.py --project-root . --remote --timeout 8 --pretty
```

## Project Adaptation
1. Identify citation commands used (`\\cite`, `\\citep`, `\\citet`, custom macros).
2. Identify bibliography source(s) and preferred BibTeX style rules.
3. Confirm external validation source(s): DOI resolver, CrossRef, Semantic Scholar, arXiv, or internal catalog.

## Workflow
1. Run `scripts/validate_citations.py` for local integrity checks:
   - undefined citation keys
   - uncited bibliography entries
   - style inconsistencies (for example `\\cite` vs project-preferred forms)
2. Run with `--remote` to validate entries against external sources by DOI/title.
3. Classify each problematic entry as:
   - `valid`
   - `needs_correction`
   - `likely_hallucinated`
   - `not_found`
4. Generate minimal unified diffs for `.bib` and TeX files, preserving existing key naming where possible.
5. Apply patches with review and rerun integrity checks.

## Inputs and Outputs
- Input: TeX source, bibliography source, validation results, style constraints.
- Output: verification summary and auditable patch set for citation fixes.

## Thesis Project Configuration

- **Thesis root**: `F:\人大管科\李良艳的大论文\`
- **Citation style**: GB/T 7714-2015 (Chinese national standard) via `biblatex-gb7714-2015`
- **Preferred citation commands**: `\cite{}` for general, `\parencite{}` for parenthetical
- **Key validation sources**: CNKI (中国知网), Wanfang (万方), DOI resolver, Semantic Scholar
- **Chinese citation caveat**: Many Chinese references lack DOI; validate via CNKI title search instead

## Common Mistakes
- Fixing citations before running external validation.
- Replacing keys aggressively instead of preserving stable key names.
- Applying mixed style and metadata rewrites in one oversized patch.
- Skipping post-apply revalidation.
