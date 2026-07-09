# <Project Name>

<One sentence. What this is, for someone who has never heard of it.>

## Overview

<2–4 sentences: what it does, who it's for, why it exists. Not a feature list.>

## Getting Started

### Prerequisites

- <Runtime + pinned version, e.g. Node 20.x (see `.nvmrc`)>
- <Any service that must be running, e.g. Postgres 15>

### Install and run

```bash
git clone <repo-url> && cd <repo-name>
<install command>
<run command>
```

<What success looks like — the URL that serves, the line that prints.>

## Usage

### <The happy path>

```bash
$ <command>
<real captured output>
```

### <A real task>

```bash
$ <command with a flag that changes behavior>
<real captured output>
```

## Configuration

<Include only if the repo has configuration. Source from `.env.example` — never `.env`.>

| Variable | Required | Default | Description |
|---|---|---|---|
| `<NAME>` | yes | — | <what it does> |

## Project Structure

<Include only if the layout is not self-evident.>

```
src/          <what lives here>
tests/        <what lives here>
```

## Development

```bash
<test command>     # sourced from CI workflow or package scripts
<lint command>
<build command>
```

## Contributing

<Link to CONTRIBUTING.md if present, else a two-line branch/PR note.>

## License

<SPDX identifier> — see [LICENSE](LICENSE).
