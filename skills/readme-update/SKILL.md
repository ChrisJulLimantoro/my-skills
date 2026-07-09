---
name: readme-update
description: This skill should be used when the user asks to "update the README", "generate a README", "write README.md", "refresh the docs", "the README is out of date", "fill out the README template", or when a repository's CLAUDE.md/AGENTS.md instructs the agent to keep README.md in sync after changes. Reads the repo's README template (from a template file, or a README contract in CLAUDE.md/AGENTS.md, or the bundled default), verifies every command against the actual repo, and rewrites README.md while preserving human-authored prose. Trigger - /readme-update
trigger: /readme-update
model: sonnet
---

# /readme-update

Rewrite `README.md` so it matches the repository's README template and the repository's actual,
verified state. Never invent a command, flag, or dependency that cannot be traced back to a file
in the repo.

Two ways in:

- **Manually** — `/readme-update [--check]`
- **Automatically** — a repository's `CLAUDE.md` / `AGENTS.md` tells the agent to run this skill
  after changes that affect setup, commands, or public API. See "Wiring into a repo" below.

## Step 1 — Resolve the template

Resolve in this order and stop at the first hit:

1. **An explicit template file**, first match of:
   `.github/README_TEMPLATE.md`, `docs/README_TEMPLATE.md`, `.readme-template.md`
2. **A README contract** in the repo's `CLAUDE.md` or `AGENTS.md` — a `## README` (or
   `## README Attributes`) section listing required sections, ordering, tone, or badges.
3. **The bundled default** at `references/readme-template.md` in this skill directory.

Layer 2 on top of layer 1 when both exist: the template file supplies structure, the CLAUDE.md
contract supplies repo-specific attributes and additions. When the contract and the template
disagree on a section, the CLAUDE.md contract wins — it is the more local instruction.

Never restructure a resolved template. Fill its blanks, keep its section names and order, and
append only the sections the contract requires.

## Step 2 — Establish the mandatory floor

Whatever the template says, the final README must contain at least these, in this order. If the
resolved template lacks one, add it; if the template orders them differently, follow the template.

1. **Title + one-line description** — what this repo is, in a single sentence a stranger
   understands. No badges above the title unless the template asks for them.
2. **Overview** — 2–4 sentences: what it does, who it is for, why it exists. Not a feature list.
3. **Getting Started** — the single shortest path from `git clone` to a working thing.
   This is the one non-negotiable section. Rules:
   - Prerequisites first, with versions (read them from `.nvmrc`, `.python-version`, `go.mod`,
     `pyproject.toml`, `package.json` `engines`, `Dockerfile`, CI workflow files).
   - Then a copy-pasteable block: install → configure → run. Three commands is the target;
     if it takes more than five, that is a finding worth telling the user about.
   - End with what success looks like (the URL that serves, the output line that prints).
   - No prose between the commands that a reader must interpret.
4. **Usage / Examples** — at least two concrete, runnable examples (see Step 4).
5. **Development** — how to run tests, lint, and build. Only commands that exist.
6. **License** — link to the `LICENSE` file; do not inline the license text.

Include these only when the repo actually has them:

- **Configuration** — a table of env vars / flags, sourced from `.env.example`, config schema
  files, or flag definitions. Read `.env.example` only, never `.env`.
- **Project Structure** — an annotated tree, only when the layout is not self-evident.
- **Architecture** — only when a design decision is load-bearing for a contributor.
- **Contributing** — link to `CONTRIBUTING.md` if present; otherwise a two-line PR/branch note.

Omit an empty section rather than writing "TBD" or "Coming soon" under it.

## Step 3 — Read the repo before writing a word

Gather facts, not impressions. At minimum:

```
ls                                        # top-level layout
cat package.json / pyproject.toml / go.mod / Cargo.toml / Makefile   # whichever exist
cat .env.example                          # config surface (NEVER .env)
ls .github/workflows/                     # the CI commands are the true build/test commands
git log --oneline -15                     # what this repo has been doing lately
cat README.md                             # the current one — for prose worth keeping
```

Derive install/test/build/run commands from **script definitions and CI workflows**, in that
order of trust. A command in `.github/workflows/ci.yml` is proven to work; a command in an old
README is a rumor. When the two disagree, the workflow wins and the README is wrong.

If a command cannot be sourced from any file, do not write it. Flag it in the final report as a
gap for the user to fill.

## Step 4 — Write examples that were actually run

Every example must be concrete: real flags, real file paths, real output. No `foo`/`bar`, no
`<your-value-here>` where a real default exists.

Provide at least two, escalating:

- **Example 1 — the happy path.** The smallest useful invocation, the one from Getting Started
  taken one step further.
- **Example 2 — a real task.** Something a user genuinely wants: a second command, a flag that
  changes behavior, an API call with its response body.

Then, where the repo supports it, a third for the non-obvious case (error handling, CI usage,
programmatic import).

Show expected output beneath each example, in the same fenced block or an adjacent one:

````
```bash
$ mytool build --watch
[build] watching src/ …
[build] wrote dist/index.js in 240ms
```
````

**Run the examples.** For any example that is safe and local (a `--help`, a build, a test, a
CLI invocation with no network writes and no destructive flags), execute it and paste the real
output. If an example cannot be run — needs secrets, a live service, a GPU, or would mutate
something — mark it clearly rather than fabricating output:

> `⚠️ Not executed locally — requires a running Postgres instance.`

Never present invented output as if it were captured. That is the fastest way to make a README
untrustworthy.

## Step 5 — Preserve what humans wrote

A README rewrite is a merge, not a replacement.

- Carry over hand-written prose that is still accurate — voice, motivation, war stories,
  acknowledgements, FAQ entries. Rewrite only what the repo has contradicted.
- Preserve anything between `<!-- readme:keep -->` and `<!-- /readme:keep -->` byte-for-byte.
- Keep existing badges, images, and their alt text unless the underlying thing is gone.
- Keep anchors that other docs link to. Renaming a heading breaks `#section` links; when a
  rename is necessary, grep the repo for the old anchor and update the links too.

Delete a section only when the thing it documents no longer exists in the repo. Say so in the
report.

## Step 6 — Verify, then write

Before writing `README.md`:

- Every fenced command block traces to a script, workflow, or Makefile target.
- Every internal link resolves to a real path (`ls` each one).
- Every claimed version matches the pin in the repo.
- The Getting Started block was executed, or is explicitly flagged as unverified.

Then overwrite `README.md` at the repo root. Do not commit, branch, or push unless asked.

## Step 7 — Report

Tell the user, briefly:

- Which template was resolved, and from where.
- What changed: sections added, rewritten, deleted.
- Which examples were executed and passed, and which are flagged unverified.
- Gaps found: commands that could not be sourced, a Getting Started longer than five steps, a
  documented flag that no longer exists in the code.

## `--check` mode

`/readme-update --check` runs Steps 1–6 but writes nothing. It reports drift only: which
mandatory sections are missing, which documented commands no longer exist, which links are dead.
Suitable for calling from CI or a pre-PR check. Exit the skill with a clear
`README is in sync` / `README has N drift findings` line.

## Wiring into a repo

To have this run automatically, add a `README` contract to the repository's `CLAUDE.md` or
`AGENTS.md`. The contract does two jobs: it triggers the skill, and it declares repo-specific
attributes.

```markdown
## README

Keep `README.md` in sync. After any change to setup steps, CLI flags, env vars, or public API,
run the `readme-update` skill.

Required sections, in order:
1. Title + one-liner
2. Overview
3. Getting Started      — must stay under 4 commands
4. Usage / Examples     — minimum 2, at least one showing the `--json` output mode
5. Configuration        — table sourced from `.env.example`
6. Development
7. License

Attributes:
- Badges: CI status, npm version. Above the title.
- Tone: terse, second person, no marketing language.
- Every code block must specify a language.
- Do not document internal `_`-prefixed modules.
```

See `examples/claude-md-readme-contract.md` for a fuller version and
`examples/generated-readme.md` for what this skill produces from it.
