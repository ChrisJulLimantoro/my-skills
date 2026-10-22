.PHONY: install install-global uninstall list new build help

SKILL_NAME ?=

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Set up skills for this project only (symlinks + Cursor commands)
	bash scripts/setup.sh

build: ## Regenerate Cursor commands from skills/*/SKILL.md
	bash scripts/build-cursor.sh

install-global: ## Link skills + AGENTS.md (all tools), CLAUDE.md/RTK.md (Claude)
	bash scripts/setup.sh --global

uninstall: ## Remove global skills + instruction-file links (all tools)
	bash scripts/setup.sh --uninstall

list: ## List all installed skills
	bash scripts/setup.sh --list

new: ## Scaffold a new skill: make new SKILL_NAME=my-skill
	@[ -n "$(SKILL_NAME)" ] || { echo "Usage: make new SKILL_NAME=<skill-name>"; exit 1; }
	bash scripts/setup.sh --new "$(SKILL_NAME)"

update: ## Pull latest changes and re-validate skills
	git pull --ff-only
	bash scripts/setup.sh
