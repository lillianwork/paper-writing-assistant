---
name: tex-latex-structure-parser
description: Use when tasks require extracting or validating LaTeX document structure, including sections, citations, figures, tables, cross-references, and custom regex checks.
---

# Tex LaTeX Structure Parser

## Overview
Use this skill for read-only structure extraction before any fixing step. Build a factual map of the paper, then hand that evidence to other skills.

## Executable Entry Points
- `scripts/parse_latex_structure.py`: extracts sections, citations, bibliography keys, figures, tables, references, and cross-check issues as JSON.

Example command:
```bash
python scripts/parse_latex_structure.py --project-root . --main-tex main.tex --pretty
```

## Project Adaptation
1. Identify TeX entry file(s) and inclusion style (`\\input`, `\\include`, generated files).
2. Identify bibliography sources (`.bib`, inline bibliography, or mixed).
3. Identify directories to ignore (build, cache, backups, checkpoints).

## Workflow
1. Run `scripts/parse_latex_structure.py` against the target project root.
2. Extract core entities:
   - section hierarchy
   - citation keys used in TeX
   - bibliography keys defined
   - figure/table labels and captions
   - figure/table references (`\\ref`, `\\cref`, equivalents)
3. Run cross-checks from the JSON result:
   - undefined citations
   - uncited bibliography entries
   - unreferenced figures/tables
   - missing labels/captions
4. Apply project-specific regex checks (TODO markers, style constraints, forbidden patterns).
5. Produce a normalized issue list with file and line context.

## Inputs and Outputs
- Input: project root, TeX files, bibliography files, optional regex rules.
- Output: structured facts plus actionable consistency findings.

## Thesis Project Configuration

- **Thesis root**: `F:\人大管科\李良艳的大论文\`
- **Main TeX file**: typically `main.tex` or `thesis.tex`
- **Bibliography**: `.bib` file(s) using GB/T 7714-2015 style
- **Chinese-specific checks**: validate `\quad`, `\qquad` spacing, full-width punctuation in Chinese paragraphs, mixed Chinese-English font consistency
- **Expected structure**: 封面 → 摘要 → 目录 → 正文(6-8章) → 参考文献 → 附录 → 致谢

## Common Mistakes
- Running fixes before building a full structure map.
- Ignoring recursively included TeX files.
- Treating regex matches as final truth without reference cross-checks.
- Mixing parse evidence with subjective style feedback.
