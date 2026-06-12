#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Run all portable LaTeX skill scripts against a target project.

Usage:
  ./run_all_skill_checks.sh --project-root <path> [--main-tex <file>] [--section-name <name>] [--remote-citations]

Options:
  --project-root <path>   LaTeX project directory to analyze (required)
  --main-tex <file>       Main TeX file relative to project root (optional)
  --section-name <name>   Section name for section check (default: Introduction)
  --remote-citations      Enable remote Crossref citation validation
  -h, --help              Show help
USAGE
}

PROJECT_ROOT=""
MAIN_TEX=""
SECTION_NAME="Introduction"
REMOTE_CITATIONS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root)
      [[ $# -ge 2 ]] || { echo "Error: --project-root requires a value" >&2; exit 2; }
      PROJECT_ROOT="$2"
      shift 2
      ;;
    --main-tex)
      [[ $# -ge 2 ]] || { echo "Error: --main-tex requires a value" >&2; exit 2; }
      MAIN_TEX="$2"
      shift 2
      ;;
    --section-name)
      [[ $# -ge 2 ]] || { echo "Error: --section-name requires a value" >&2; exit 2; }
      SECTION_NAME="$2"
      shift 2
      ;;
    --remote-citations)
      REMOTE_CITATIONS=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$PROJECT_ROOT" ]] || { echo "Error: --project-root is required" >&2; usage; exit 2; }
[[ -d "$PROJECT_ROOT" ]] || { echo "Error: project root does not exist: $PROJECT_ROOT" >&2; exit 2; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$ROOT_DIR"
OUT_DIR="$PROJECT_ROOT/.latex-checks"
mkdir -p "$OUT_DIR"

check_toolchain="$SKILLS_DIR/tex-toolchain-compile/scripts/check_toolchain.py"
extract_compile="$SKILLS_DIR/tex-toolchain-compile/scripts/extract_compile_issues.py"
parse_structure="$SKILLS_DIR/tex-latex-structure-parser/scripts/parse_latex_structure.py"
validate_citations="$SKILLS_DIR/tex-citation-validate-fix/scripts/validate_citations.py"
verify_targets="$SKILLS_DIR/tex-figure-table-section-fix/scripts/verify_content_targets.py"
rasterize_pages="$SKILLS_DIR/tex-figure-table-section-fix/scripts/rasterize_pdf_pages.py"
review_pages="$SKILLS_DIR/tex-figure-table-section-fix/scripts/review_raster_pages.py"

for script in "$check_toolchain" "$extract_compile" "$parse_structure" "$validate_citations" "$verify_targets" "$rasterize_pages" "$review_pages"; do
  [[ -f "$script" ]] || { echo "Error: missing script: $script" >&2; exit 2; }
done

common_args=(--project-root "$PROJECT_ROOT")
if [[ -n "$MAIN_TEX" ]]; then
  common_args+=(--main-tex "$MAIN_TEX")
fi

echo "[1/7] Toolchain check"
python "$check_toolchain" --pretty

echo "[2/7] Compile issue parser smoke check"
python "$extract_compile" --log-text "LaTeX Warning: Example warning" --pretty

echo "[3/7] Structure parse"
python "$parse_structure" "${common_args[@]}" --pretty > "$OUT_DIR/out_structure.json"

echo "[4/7] Citation validation"
citation_args=("${common_args[@]}")
if [[ "$REMOTE_CITATIONS" -eq 1 ]]; then
  citation_args+=(--remote)
fi
python "$validate_citations" "${citation_args[@]}" --pretty > "$OUT_DIR/out_citations.json"

echo "[5/7] Figure checks"
python "$verify_targets" "${common_args[@]}" --target figures --pretty > "$OUT_DIR/out_figures.json"

echo "[6/7] Table checks"
python "$verify_targets" "${common_args[@]}" --target tables --pretty > "$OUT_DIR/out_tables.json"

echo "[7/9] Section checks"
python "$verify_targets" "${common_args[@]}" --target section --section-name "$SECTION_NAME" --pretty > "$OUT_DIR/out_section.json"

echo "[8/9] Rasterize pages for visual review"
python "$rasterize_pages" "${common_args[@]}" --compile-if-missing --pretty > "$OUT_DIR/out_raster_pages.json"

echo "[9/9] Build page-by-page review template"
python "$review_pages" --project-root "$PROJECT_ROOT" --manifest "$OUT_DIR/out_raster_pages.json" --pretty > "$OUT_DIR/out_page_review.json"

echo "Done. Reports written to:"
echo "  $OUT_DIR/out_structure.json"
echo "  $OUT_DIR/out_citations.json"
echo "  $OUT_DIR/out_figures.json"
echo "  $OUT_DIR/out_tables.json"
echo "  $OUT_DIR/out_section.json"
echo "  $OUT_DIR/out_raster_pages.json"
echo "  $OUT_DIR/out_page_review.json"
