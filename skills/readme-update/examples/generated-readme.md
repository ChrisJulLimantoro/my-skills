# Example: a README produced from the contract

This is what `readme-update` produces for a fictional CLI (`envcheck`) whose `CLAUDE.md`
contains the contract in `claude-md-readme-contract.md`. Note what the contract forced:
badges *under* the title, Getting Started at exactly 3 commands, three usage examples
(one of them `--json`), a config table sourced from `.env.example`, dev commands lifted from
`ci.yml`, and a `readme:keep` block carried through untouched.

---

````markdown
# envcheck

Validates that a project's `.env` file matches its `.env.example` before the app boots.

[![CI](https://github.com/acme/envcheck/actions/workflows/ci.yml/badge.svg)](https://github.com/acme/envcheck/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/envcheck.svg)](https://www.npmjs.com/package/envcheck)

## Overview

envcheck compares the environment variables a project declares in `.env.example` against the
ones actually present at runtime, and fails loudly when they drift. It is meant for the gap
between "works on my machine" and a container that boots with a silently missing secret. Run it
as a preflight step in CI, or as the first line of an app's entrypoint.

## Getting Started

### Prerequisites

- Node 20.x (pinned in `.nvmrc`)

### Install and run

```bash
npm install -g envcheck
envcheck init
envcheck
```

`envcheck init` writes a `.envcheckrc`; the bare `envcheck` validates the current directory and
prints `✓ 12/12 variables present` on success. A missing variable exits non-zero.

## Usage

### Validate the current directory

```bash
$ envcheck
✓ DATABASE_URL
✓ REDIS_URL
✗ STRIPE_SECRET_KEY — declared in .env.example, missing from environment

1 of 3 variables missing
```

### Machine-readable output for CI

```bash
$ envcheck --json
{
  "ok": false,
  "missing": ["STRIPE_SECRET_KEY"],
  "present": ["DATABASE_URL", "REDIS_URL"]
}
```

Exit code is `1` when `ok` is `false`, so `envcheck --json > report.json` fails the job on drift.

### Programmatic use

```javascript
import { check } from "envcheck";

const { ok, missing } = await check({ cwd: process.cwd() });
if (!ok) throw new Error(`Missing env vars: ${missing.join(", ")}`);
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENVCHECK_FILE` | no | `.env.example` | Path to the declaration file to validate against |
| `ENVCHECK_STRICT` | no | `false` | Also fail on variables present but *not* declared |

## Development

```bash
npm test          # vitest run
npm run lint      # eslint .
npm run typecheck # tsc --noEmit
npm run build     # tsup src/index.ts
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

<!-- readme:keep -->
## Why not dotenv-safe?

dotenv-safe validates at import time and throws inside your process. envcheck runs as a separate
binary before the process starts, which means it works for non-Node services too — we use it in
front of a Go worker and a Rails app in the same monorepo.
<!-- /readme:keep -->

## License

MIT — see [LICENSE](LICENSE).
````

---

## What the skill reported afterwards

```
Template: .github/README_TEMPLATE.md, layered with the README contract in CLAUDE.md.

Changed:
  + Usage → added "Programmatic use" example (src/index.ts now exports check())
  ~ Configuration → ENVCHECK_STRICT added; ENVCHECK_VERBOSE removed (gone from src/cli.ts)
  ~ Development → npm run typecheck added, matches ci.yml
  = "Why not dotenv-safe?" preserved verbatim (readme:keep)

Verified: all 4 Development commands executed and passed. Examples 1–3 executed;
output captured verbatim.

Gaps:
  - Getting Started is 3 commands. Within the contract's limit.
  - CONTRIBUTING.md is linked but does not exist in the repo.
```
