#!/usr/bin/env bash
# setup.sh — Wire one canonical skills/ dir into every supported agent.
#
# Canonical source of truth: ./skills/<name>/SKILL.md
# Four tools read SKILL.md natively (Claude Code, Hermes, Codex, OpenCode) and are wired via
# symlink. Cursor cannot read SKILL.md, so generated command files (scripts/build-cursor.sh)
# are linked into its commands directory instead.
#
# Usage: bash scripts/setup.sh [--global | --uninstall | --list | --new <skill-name>]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/skills"
CURSOR_DIST="${REPO_ROOT}/dist/cursor/commands"

# Tool home directories (global install targets).
CODEX_HOME="${CODEX_HOME:-${HOME}/.codex}"
declare -a NATIVE_GLOBAL=(
    "${HOME}/.claude/skills"
    "${HOME}/.hermes/skills"
    "${CODEX_HOME}/skills"
    "${HOME}/.config/opencode/skills"
)
CURSOR_GLOBAL="${HOME}/.cursor/commands"

# Global Claude Code memory (personal preferences applied to every project).
GLOBAL_CLAUDE_MD_SRC="${REPO_ROOT}/global/CLAUDE.md"
GLOBAL_CLAUDE_MD_DEST="${HOME}/.claude/CLAUDE.md"

# In-repo (project-local) symlinks pointing at the canonical skills dir.
declare -a NATIVE_LOCAL=(
    "${REPO_ROOT}/.claude/skills"
    "${REPO_ROOT}/.opencode/skills"
    "${REPO_ROOT}/.agents/skills"
)
CURSOR_LOCAL="${REPO_ROOT}/.cursor/commands"

log() { printf '[setup] %s\n' "$*"; }
err() { printf '[setup] ERROR: %s\n' "$*" >&2; exit 1; }

# ── Helpers ───────────────────────────────────────────────────────────────────

validate_skills() {
    log "Validating skill structure..."
    local INVALID=0 FOUND=0
    for dir in "${SKILLS_DIR}"/*/; do
        [ -d "$dir" ] || continue
        local skill_name; skill_name="$(basename "$dir")"
        FOUND=$((FOUND + 1))
        if [ ! -f "${dir}SKILL.md" ]; then
            log "  WARNING: ${skill_name} is missing SKILL.md"
            INVALID=$((INVALID + 1))
        fi
    done
    [ "${FOUND}" -eq 0 ] && log "No skills found in ${SKILLS_DIR}."
    [ "${INVALID}" -gt 0 ] && log "WARNING: ${INVALID} skill(s) are missing SKILL.md"
    log "Found ${FOUND} skill(s)."
}

# link_dir <link_path> <target> — idempotent symlink, never clobbers a real directory.
link_dir() {
    local link="$1" target="$2"
    mkdir -p "$(dirname "${link}")"
    if [ -L "${link}" ]; then
        ln -sfn "${target}" "${link}"
        log "  linked ${link} -> ${target}"
    elif [ -e "${link}" ]; then
        log "  SKIP ${link} (exists and is not a symlink — remove it manually to wire it up)"
    else
        ln -sfn "${target}" "${link}"
        log "  linked ${link} -> ${target}"
    fi
}

build_cursor() {
    bash "${REPO_ROOT}/scripts/build-cursor.sh"
}

# Per-file symlinks of generated Cursor commands into a target dir (won't hijack the dir).
link_cursor_files() {
    local dest="$1"
    mkdir -p "${dest}"
    local f name
    for f in "${CURSOR_DIST}"/*.md; do
        [ -e "$f" ] || continue
        name="$(basename "$f")"
        ln -sfn "$f" "${dest}/${name}"
    done
    log "  linked $(ls -1 "${CURSOR_DIST}"/*.md 2>/dev/null | wc -l | tr -d ' ') Cursor command(s) into ${dest}"
}

# Remove only the Cursor command symlinks that point back into this repo's dist dir.
unlink_cursor_files() {
    local dest="$1"
    [ -d "${dest}" ] || return 0
    local f target
    for f in "${dest}"/*.md; do
        [ -L "$f" ] || continue
        target="$(readlink "$f")"
        case "${target}" in
            "${CURSOR_DIST}"/*) rm "$f"; log "  removed ${f}" ;;
        esac
    done
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_install() {
    [ -d "${SKILLS_DIR}" ] || err "Canonical skills dir not found: ${SKILLS_DIR}"
    log "Wiring project-local tool directories..."
    local link
    for link in "${NATIVE_LOCAL[@]}"; do
        link_dir "${link}" "${SKILLS_DIR}"
    done
    build_cursor
    link_dir "${CURSOR_LOCAL}" "${CURSOR_DIST}"

    validate_skills
    log ""
    log "Project setup complete. To install for every tool on this machine:"
    log "  bash scripts/setup.sh --global"
}

cmd_install_global() {
    cmd_install
    log ""
    log "Wiring global (machine-wide) tool directories..."
    local link
    for link in "${NATIVE_GLOBAL[@]}"; do
        link_dir "${link}" "${SKILLS_DIR}"
    done
    link_cursor_files "${CURSOR_GLOBAL}"

    if [ -f "${GLOBAL_CLAUDE_MD_SRC}" ]; then
        log ""
        log "Wiring global Claude Code memory (~/.claude/CLAUDE.md)..."
        # link_dir never clobbers a real file — if a personal CLAUDE.md already
        # exists it is SKIPped; merge it into global/CLAUDE.md manually first.
        link_dir "${GLOBAL_CLAUDE_MD_DEST}" "${GLOBAL_CLAUDE_MD_SRC}"
    fi

    log ""
    log "Global install complete. Skills are available in Claude Code, Hermes, Codex,"
    log "OpenCode, and Cursor — in every project on this machine."
}

cmd_uninstall() {
    log "Removing global tool symlinks..."
    local link target
    for link in "${NATIVE_GLOBAL[@]}"; do
        if [ -L "${link}" ]; then
            target="$(readlink "${link}")"
            if [ "${target}" = "${SKILLS_DIR}" ]; then
                rm "${link}"; log "  removed ${link}"
            else
                log "  SKIP ${link} (points elsewhere: ${target})"
            fi
        elif [ -e "${link}" ]; then
            log "  SKIP ${link} (not a symlink)"
        fi
    done
    unlink_cursor_files "${CURSOR_GLOBAL}"
    if [ -L "${GLOBAL_CLAUDE_MD_DEST}" ] && [ "$(readlink "${GLOBAL_CLAUDE_MD_DEST}")" = "${GLOBAL_CLAUDE_MD_SRC}" ]; then
        rm "${GLOBAL_CLAUDE_MD_DEST}"; log "  removed ${GLOBAL_CLAUDE_MD_DEST}"
    fi
    log "Uninstall complete. The repo's skills/ directory is untouched."
}

cmd_list() {
    [ -d "${SKILLS_DIR}" ] || err "Skills directory not found: ${SKILLS_DIR}. Run setup first."
    local FOUND=0
    printf "\nInstalled skills\n"
    printf "%-22s  %s\n" "NAME" "DESCRIPTION"
    printf "%-22s  %s\n" "----" "-----------"
    for dir in "${SKILLS_DIR}"/*/; do
        [ -d "$dir" ] || continue
        local skill_name skill_file raw_desc short
        skill_name="$(basename "$dir")"
        skill_file="${dir}SKILL.md"
        if [ -f "${skill_file}" ]; then
            raw_desc="$(awk '/^description:/{$1=""; sub(/^ /, ""); print; exit}' "${skill_file}")"
            short="$(printf '%s' "${raw_desc}" | grep -oE '"[^"]+"' | head -1 | tr -d '"' || true)"
            [ -z "${short}" ] && short="${raw_desc:0:70}"
            printf "%-22s  %s\n" "${skill_name}" "${short}"
            FOUND=$((FOUND + 1))
        else
            printf "%-22s  %s\n" "${skill_name}" "(missing SKILL.md)"
        fi
    done
    printf "\n%d skill(s) in %s\n\n" "${FOUND}" "${SKILLS_DIR}"
    local link
    for link in "${NATIVE_GLOBAL[@]}"; do
        if [ -L "${link}" ]; then
            log "global: ${link} -> $(readlink "${link}")"
        fi
    done
}

cmd_new() {
    local skill_name="$1"
    if ! printf '%s' "${skill_name}" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
        err "Skill name must be kebab-case (e.g. my-skill). Got: ${skill_name}"
    fi
    local skill_dir="${SKILLS_DIR}/${skill_name}"
    local skill_file="${skill_dir}/SKILL.md"
    [ -e "${skill_dir}" ] && err "Skill already exists: ${skill_dir}"
    mkdir -p "${skill_dir}"
    cat > "${skill_file}" << EOF
---
name: ${skill_name}
description: This skill should be used when the user asks to "...", "...", or "...". One sentence explaining what it does.
---

# $(printf '%s' "${skill_name}" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')

<One-paragraph overview of purpose and approach.>

## Step 1 — <Heading>

<Imperative instructions. No second person.>

## Output Format

<Describe exactly what the skill produces and where it goes.>
EOF
    log "Created: ${skill_file}"
    log "Edit it, then run 'bash scripts/setup.sh' (or 'make build') to regenerate Cursor commands."
}

# ── Entry point ───────────────────────────────────────────────────────────────

case "${1:-}" in
    --global)    cmd_install_global ;;
    --uninstall) cmd_uninstall ;;
    --list)      cmd_list ;;
    --new)       [ -n "${2:-}" ] || err "Usage: bash scripts/setup.sh --new <skill-name>"; cmd_new "$2" ;;
    "")          cmd_install ;;
    *)           err "Unknown option: $1. Usage: setup.sh [--global | --uninstall | --list | --new <skill-name>]" ;;
esac
