# Example: a README contract in `CLAUDE.md` / `AGENTS.md`

Drop this into a repository's `CLAUDE.md` (or `AGENTS.md`). It does two jobs: it tells the agent
when to run `readme-update`, and it declares the attributes that repo's README must satisfy.

The skill reads this section, layers it over any `README_TEMPLATE.md` in the repo, and falls
back to the bundled default template for anything the contract does not specify.

---

```markdown
## README

`README.md` is a build artifact of this repo's actual state. After any change to setup steps,
CLI flags, environment variables, or public API, run the `readme-update` skill. Do not
hand-edit README.md outside `<!-- readme:keep -->` blocks.

### Required sections, in order

1. Title + one-line description
2. Badges (CI status, npm version) — directly under the title, not above it
3. Overview — 2–4 sentences, no feature bullets
4. Getting Started — must remain executable in 3 commands; if a change pushes it past 3,
   surface that as a finding instead of silently documenting a longer path
5. Usage — minimum 3 examples: basic invocation, `--json` output mode, programmatic import
6. Configuration — table generated from `.env.example`, one row per variable
7. Development — test, lint, typecheck, build; commands must match `.github/workflows/ci.yml`
8. Contributing — link only, to CONTRIBUTING.md
9. License

### Attributes

- **Tone**: terse, imperative, no marketing language ("blazing fast", "seamless" are banned).
- **Code blocks**: every fence declares a language. Shell examples show the `$` prompt and the
  real captured output beneath.
- **Versions**: pin every prerequisite to the version in `.nvmrc` / `engines` — never "latest".
- **Scope**: document the public API only. Skip internal `_`-prefixed modules and anything
  under `src/internal/`.
- **Links**: relative links to in-repo files; absolute only for external docs.
- **Length**: hard cap of 250 lines. Overflow goes to `docs/`, linked from the README.

### Preserved by hand

The "Why not X?" comparison section and the acknowledgements are human-written. They live
inside `<!-- readme:keep -->` markers and must survive every regeneration untouched.
```

---

## Manual invocation

The contract does not prevent running the skill by hand:

```
/readme-update            # rewrite README.md
/readme-update --check    # report drift, write nothing (good for CI / pre-PR)
```
