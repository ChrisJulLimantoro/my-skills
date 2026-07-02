# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

# Communication
When reporting information to me, be extremely concise and sacrifice grammar for the sake of concision. Unless I prompt you to be grammatically correct.

# Coding Style
Follow the **Five Lines of Code** principle (Christian Clausen) as the default style:
- Aim for the **least logic that covers every case while staying readable** — no duplicated or overlapping conditionals, no redundant flags/state.
- Keep functions small (~5 lines target), one job each; extract instead of growing.
- "Either call or pass, but not both" — one level of abstraction per function.
- `if` belongs at the start of a function (guard clauses / early returns); avoid nested or buried branching.
- Minimalism NEVER means code golf or cryptic names (`x`, `v`, `a`) — descriptive names and readable structure always win over saving characters.

# HARD RULES (NEVER violate)
- NEVER add "Co-Authored-By: Claude" or any AI model attribution to commit messages, PRs, or any commit to git.
- NEVER read any `.env` file except `.env.example`, on any occasions.
