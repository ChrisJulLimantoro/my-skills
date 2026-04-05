---
name: skill-creator
description: This skill should be used when the user asks to "create a skill", "build a skill", "make a new skill", "I need a skill that", "add a skill for", or "write a SKILL.md". Interviews the user with targeted questions to understand the skill's purpose, then generates and refines a properly-formatted SKILL.md file.
version: 0.1.0
---

# Skill Creator

Interview the user, draft a SKILL.md, refine it based on feedback, then write the file.

## Phase 1 — Interview

Ask these questions. Batch related ones into a single message — do not ask all at once:

**Round 1 — Purpose and Trigger** (ask together):
1. What does this skill do? Describe it in one or two sentences.
2. What phrases or requests from the user should trigger it? (Give 3–5 examples of what you'd type to activate it.)
3. Should it trigger automatically in certain situations, or only when explicitly invoked?

**Round 2 — Behavior and Output** (ask after Round 1):
4. Walk me through the workflow step by step. What should the skill do first, second, third?
5. What does the final output look like? (e.g., a file written to disk, a structured report in the chat, modified code, a terminal command to run)
6. Are there any quality gates or conditions that must be met before the skill completes?

**Round 3 — Constraints** (ask only if needed after Round 2):
7. Should only the user be able to invoke this, or should Claude be able to trigger it automatically?
8. Are there any tools this skill specifically requires (web search, file reads, bash commands)?
9. What should it NOT do? (Helps define boundaries.)

Do not proceed to drafting until you have clear answers to at least questions 1–5.

## Phase 2 — Draft

Generate a SKILL.md draft using the answers:

```markdown
---
name: <kebab-case-name>
description: This skill should be used when the user asks to "<trigger phrase 1>", "<trigger phrase 2>", or "<trigger phrase 3>". <One sentence explaining what it does.>
version: 0.1.0
---

# <Skill Title>

<One-paragraph overview of purpose and approach.>

## <Workflow Step 1 Heading>

<Imperative instructions. No second person.>

## <Workflow Step 2 Heading>

<Imperative instructions.>

## Output Format

<Describe exactly what the skill produces and where it goes.>

## Quality Gates (if applicable)

<Conditions that must be met before the skill is considered complete.>
```

**Frontmatter rules**:
- `name`: kebab-case, matches the directory name this file will live in
- `description`: third-person, opens with "This skill should be used when the user asks to", includes specific quoted trigger phrases
- `version`: start at `0.1.0`

**Body rules**:
- Imperative/infinitive verb form throughout ("Run the diff." not "You should run the diff.")
- No second person ("you")
- Target 600–1,500 words for the body; move large reference material to a `references/` subdirectory if needed

## Phase 3 — Review and Refine

Present the full draft and ask:
"Here's the draft SKILL.md. Does this capture the behavior you want, or should I adjust anything before writing the file?"

Incorporate feedback. Repeat until the user confirms it's correct.

## Phase 4 — Write the File

Once confirmed:

1. Determine the skill name from the frontmatter `name` field
2. Write to `.claude/skills/<skill-name>/SKILL.md` relative to the current project root
3. Confirm the file path that was written
4. Remind the user to run `bash scripts/setup.sh` to validate the new skill is detected

If `.claude/skills/` does not exist in the current directory, ask the user whether to create it or write the file to a different location.
