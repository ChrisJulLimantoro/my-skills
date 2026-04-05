#!/usr/bin/env bash
# setup.sh — Initialize the AI Skills Repository
# Usage: bash scripts/setup.sh [--global | --uninstall | --list | --new <skill-name>]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="${REPO_ROOT}/.claude/skills"
OPENCLAW_DIR="${REPO_ROOT}/.openclaw"
OPENCLAW_LINK="${OPENCLAW_DIR}/skills"
GLOBAL_SKILLS_DIR="${HOME}/.claude/skills"

log() { printf '[setup] %s\n' "$*"; }
err() { printf '[setup] ERROR: %s\n' "$*" >&2; exit 1; }

# ── Helpers ───────────────────────────────────────────────────────────────────

validate_skills() {
    log "Validating skill structure..."
    local INVALID=0 FOUND=0
    for dir in "${SKILLS_DIR}"/*/; do
        [ -d "$dir" ] || continue
        skill_name="$(basename "$dir")"
        FOUND=$((FOUND + 1))
        if [ ! -f "${dir}SKILL.md" ]; then
            log "  WARNING: ${skill_name} is missing SKILL.md"
            INVALID=$((INVALID + 1))
        else
            log "  OK: ${skill_name}"
        fi
    done
    if [ "${FOUND}" -eq 0 ]; then
        log "No skills found yet. Add skills to ${SKILLS_DIR}/<skill-name>/SKILL.md"
    fi
    if [ "${INVALID}" -gt 0 ]; then
        log "WARNING: ${INVALID} skill(s) are missing SKILL.md"
    fi
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_install() {
    # 1. Create .claude/skills directory
    log "Creating .claude/skills directory..."
    mkdir -p "${SKILLS_DIR}"

    # 2. Create .openclaw directory and symlink (relative path for portability)
    log "Creating .openclaw/skills symlink..."
    mkdir -p "${OPENCLAW_DIR}"

    if [ -L "${OPENCLAW_LINK}" ]; then
        log ".openclaw/skills symlink already exists, skipping."
    elif [ -e "${OPENCLAW_LINK}" ]; then
        err ".openclaw/skills exists but is not a symlink. Remove it manually and re-run."
    else
        ln -sf "../.claude/skills" "${OPENCLAW_LINK}"
        log "Created symlink: .openclaw/skills -> ../.claude/skills"
    fi

    # 3. Create scripts directory (idempotent)
    mkdir -p "${REPO_ROOT}/scripts"

    validate_skills

    log ""
    log "Setup complete."
    log "  Skills directory: ${SKILLS_DIR}"
    log "  OpenClaw link:    ${OPENCLAW_LINK}"
    log ""
    log "To install globally: bash scripts/setup.sh --global"
}

cmd_install_global() {
    cmd_install

    log "Setting up global skills symlink at ${GLOBAL_SKILLS_DIR}..."
    mkdir -p "${HOME}/.claude"

    if [ -L "${GLOBAL_SKILLS_DIR}" ]; then
        log "Global symlink already exists at ${GLOBAL_SKILLS_DIR}, skipping."
    elif [ -d "${GLOBAL_SKILLS_DIR}" ] && [ ! -L "${GLOBAL_SKILLS_DIR}" ]; then
        log "WARNING: ${GLOBAL_SKILLS_DIR} is an existing directory (not a symlink)."
        log "To migrate: copy its contents into ${SKILLS_DIR}, remove the directory, then re-run."
    else
        ln -sf "${SKILLS_DIR}" "${GLOBAL_SKILLS_DIR}"
        log "Created global symlink: ${GLOBAL_SKILLS_DIR} -> ${SKILLS_DIR}"
    fi

    log ""
    log "Global install complete. Skills are now available in every project."
    log "  Global link: ${GLOBAL_SKILLS_DIR}"
}

cmd_uninstall() {
    if [ -L "${GLOBAL_SKILLS_DIR}" ]; then
        rm "${GLOBAL_SKILLS_DIR}"
        log "Removed global symlink: ${GLOBAL_SKILLS_DIR}"
    elif [ -e "${GLOBAL_SKILLS_DIR}" ]; then
        err "${GLOBAL_SKILLS_DIR} exists but is not a symlink — not removing. Delete it manually if intended."
    else
        log "No global symlink found at ${GLOBAL_SKILLS_DIR} — nothing to remove."
    fi

    if [ -L "${OPENCLAW_LINK}" ]; then
        rm "${OPENCLAW_LINK}"
        log "Removed OpenClaw symlink: ${OPENCLAW_LINK}"
    fi

    log "Uninstall complete."
}

cmd_list() {
    if [ ! -d "${SKILLS_DIR}" ]; then
        err "Skills directory not found: ${SKILLS_DIR}. Run setup first."
    fi

    local FOUND=0
    printf "\nInstalled skills\n"
    printf "%-20s  %-10s  %s\n" "NAME" "VERSION" "DESCRIPTION"
    printf "%-20s  %-10s  %s\n" "----" "-------" "-----------"

    for dir in "${SKILLS_DIR}"/*/; do
        [ -d "$dir" ] || continue
        skill_name="$(basename "$dir")"
        skill_file="${dir}SKILL.md"

        if [ -f "${skill_file}" ]; then
            version="$(awk '/^version:/{print $2; exit}' "${skill_file}")"
            # Extract description — strip leading "This skill should be used when the user asks to "
            raw_desc="$(awk '/^description:/{$1=""; sub(/^ /, ""); print; exit}' "${skill_file}")"
            short_desc="${raw_desc#This skill should be used when the user asks to }"
            # Trim to first quoted phrase
            first_phrase="$(printf '%s' "${short_desc}" | grep -oE '"[^"]+"' | head -1 | tr -d '"')"
            [ -z "${first_phrase}" ] && first_phrase="${short_desc:0:60}"
            printf "%-20s  %-10s  %s\n" "${skill_name}" "${version:-?}" "${first_phrase}"
            FOUND=$((FOUND + 1))
        else
            printf "%-20s  %-10s  %s\n" "${skill_name}" "?" "(missing SKILL.md)"
        fi
    done

    printf "\n%d skill(s) found in %s\n\n" "${FOUND}" "${SKILLS_DIR}"

    if [ -L "${GLOBAL_SKILLS_DIR}" ]; then
        log "Global install: active (${GLOBAL_SKILLS_DIR} -> $(readlink "${GLOBAL_SKILLS_DIR}"))"
    else
        log "Global install: not active. Run 'bash scripts/setup.sh --global' to enable."
    fi
}

cmd_new() {
    local skill_name="$1"

    # Validate: kebab-case letters, numbers, hyphens only
    if ! printf '%s' "${skill_name}" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
        err "Skill name must be kebab-case (e.g. my-skill). Got: ${skill_name}"
    fi

    local skill_dir="${SKILLS_DIR}/${skill_name}"
    local skill_file="${skill_dir}/SKILL.md"

    if [ -e "${skill_dir}" ]; then
        err "Skill already exists: ${skill_dir}"
    fi

    mkdir -p "${skill_dir}"
    cat > "${skill_file}" << EOF
---
name: ${skill_name}
description: This skill should be used when the user asks to "...", "...", or "...". One sentence explaining what it does.
version: 0.1.0
---

# $(printf '%s' "${skill_name}" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)} 1')

<One-paragraph overview of purpose and approach.>

## Step 1 — <Heading>

<Imperative instructions. No second person.>

## Step 2 — <Heading>

<Imperative instructions.>

## Output Format

<Describe exactly what the skill produces and where it goes.>
EOF

    log "Created: ${skill_file}"
    log ""
    log "Next steps:"
    log "  1. Edit ${skill_file}"
    log "  2. Fill in the description trigger phrases and body"
    log "  3. Run 'bash scripts/setup.sh' to validate"
}

# ── Entry point ───────────────────────────────────────────────────────────────

case "${1:-}" in
    --global)
        cmd_install_global
        ;;
    --uninstall)
        cmd_uninstall
        ;;
    --list)
        cmd_list
        ;;
    --new)
        [ -n "${2:-}" ] || err "Usage: bash scripts/setup.sh --new <skill-name>"
        cmd_new "$2"
        ;;
    "")
        cmd_install
        ;;
    *)
        err "Unknown option: $1. Usage: setup.sh [--global | --uninstall | --list | --new <skill-name>]"
        ;;
esac
