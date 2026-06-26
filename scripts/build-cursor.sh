#!/usr/bin/env bash
# build-cursor.sh — Generate Cursor slash commands from canonical SKILL.md files.
#
# Cursor cannot read SKILL.md natively (it uses .md command files / .mdc rules), so this
# transforms each skills/<name>/SKILL.md into dist/cursor/commands/<name>.md. The directory
# name becomes the slash command (/<name>); the SKILL.md body becomes the command prompt.
#
# Idempotent: the whole dist/cursor/commands/ dir is regenerated on each run.
# Usage: bash scripts/build-cursor.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/skills"
OUT_DIR="${REPO_ROOT}/dist/cursor/commands"

log() { printf '[build-cursor] %s\n' "$*"; }

[ -d "${SKILLS_DIR}" ] || { printf '[build-cursor] ERROR: %s not found\n' "${SKILLS_DIR}" >&2; exit 1; }

# Fresh output dir so deleted/renamed skills don't leave stale commands behind.
rm -rf "${OUT_DIR}"
mkdir -p "${OUT_DIR}"

count=0
for dir in "${SKILLS_DIR}"/*/; do
    [ -d "${dir}" ] || continue
    name="$(basename "${dir}")"
    skill_file="${dir}SKILL.md"
    [ -f "${skill_file}" ] || { log "skip ${name} (no SKILL.md)"; continue; }

    # Pull the description from frontmatter (first `description:` line, value after the colon).
    description="$(awk -F': ' '/^description:/{sub(/^description:[[:space:]]*/, ""); print; exit}' "${skill_file}")"

    # Body = everything after the closing frontmatter `---`. If there is no frontmatter,
    # emit the file verbatim.
    body="$(awk '
        NR==1 && $0=="---" { infm=1; next }
        infm && $0=="---"  { infm=0; started=1; next }
        infm { next }
        { print }
    ' "${skill_file}")"

    out_file="${OUT_DIR}/${name}.md"
    {
        printf -- '---\n'
        printf 'description: %s\n' "${description:-Run the ${name} skill}"
        printf -- '---\n\n'
        printf '# /%s\n\n' "${name}"
        printf '%s\n' "${body}"
    } > "${out_file}"
    count=$((count + 1))
done

log "Generated ${count} Cursor command(s) in ${OUT_DIR}"
