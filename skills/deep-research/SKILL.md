---
name: deep-research
description: This skill should be used when the user asks to "deep research", "do a deep dive", "research in depth", "investigate", "survey the landscape of", "combine research", "multi-agent deep research", or "deep research report". Orchestrates multi-agent deep research — generates intensive per-agent research prompts (Claude, ChatGPT, Gemini, others), runs Claude's own research leg, then combines all deep-research-<agent>.md results into a single structured deep-research-report.md.
version: 1.0.0
---

# Deep Research (Multi-Agent Orchestrator)

Coordinate deep research across multiple AI research agents and synthesize their outputs into one research report.

## Setup — Inputs and Mode Detection

Gather from the prompt (ask only if missing and undeterminable):
- **Topic** — the research question.
- **Objective type** — technology survey / adopt-vs-not decision / comparison / feasibility. This shapes the final action items.
- **Sources or source directory** — if a directory of prior material is given, read it before generating prompts.
- **Research directory** — where result files live and outputs are written. Default: current working directory.
- **Agent roster** — default: `claude`, `chatgpt`, `gemini`; add more if named (e.g., `perplexity`, `grok`).

Detect the phase:
- Directory contains ≥2 `deep-research-<agent>.md` result files → **Phase 2 (Synthesis)**.
- Otherwise → **Phase 1 (Fan-out)**.
- Explicit user words override detection: "plan"/"prompts" forces Phase 1; "combine"/"report"/"synthesize" forces Phase 2.

## Phase 1 — Prompt Fan-out + Own Research

### 1. Record the plan

Write `deep-research-plan.md` containing: topic, objective type, agent roster, expected result filenames (`deep-research-<agent>.md` each), and the date. Phase 2 in a later session reads this for context.

### 2. Generate one prompt per agent

Write `deep-research-prompts.md` with one copy-paste-ready section per agent. Overlapping coverage between agents is encouraged — it enables cross-validation in Phase 2. Each prompt must:

- State the topic, the objective type, and that agent's specific angle or source emphasis. Assign angles that play to each platform's strengths (e.g., academic literature, industry/vendor material, community discourse, recent news) while requiring every agent to also cover the core question.
- Require full **Six Thinking Hats** coverage:

| Hat | Requirement in the prompt |
|---|---|
| White | Hard facts, data, benchmarks, dates |
| Red | Community sentiment, practitioner intuitions |
| Black | Risks, criticism, failure stories, limitations |
| Yellow | Benefits, opportunities, success stories |
| Green | Alternatives, creative options, adjacent approaches |
| Blue | Output must be a well-organized markdown paper |

- Require for every source: URL or full citation, publication date, author/organization, and a one-sentence key insight.
- Require at least one contrarian or critical source.
- Instruct that the final output be a markdown paper named `deep-research-<agent>.md`.

### 3. Run the Claude leg

Execute the `claude` prompt directly in this session and write `deep-research-claude.md`. Follow the same six-hats structure demanded of the other agents, plus these source rules:

- Minimum **8 distinct sources** from at least **4 categories**: official documentation, academic/research, industry analysis, community discourse, practitioner writing, contrarian/critical, recent news, adjacent domains.
- At least one contrarian or critical source.
- Record URL, date, author, and key insight per source.
- Document at least one genuine disagreement between sources: name it, summarize each position, assess evidence strength, and state where truth is genuinely uncertain — never a bare "it depends".

### 4. Hand off

Tell the user to run the remaining prompts in their respective agents, drop the results into the research directory as `deep-research-<agent>.md`, then re-invoke `/deep-research` to combine.

## Phase 2 — Synthesis into deep-research-report.md

### 1. Ingest

Read `deep-research-plan.md` (if present) for topic and objective, then read every `deep-research-*.md` result file.

### 2. Cross-validate

Compare claims across the input files:
- Where inputs agree, treat the claim as consensus and cite the strongest underlying source.
- Where inputs conflict: name the disagreement, summarize each position with its underlying source, assess which has stronger or more recent evidence, and give a verdict — or state precisely what the answer depends on.
- Deduplicate sources cited by multiple inputs.

### 3. Write the report

Write `deep-research-report.md`. The report must read like a human-authored research paper: never mention six hats, the input files, or which AI agent contributed what. Attribute claims to the underlying sources (websites, papers, docs) only.

Fixed frame, with a body outline designed per topic:

1. **Executive Summary** — written last, placed first. A fast, self-sufficient read: verdict or answer to the research question, the key reasons, and the main risk. A reader stopping here must already have the answer.
2. **Body** — a topic-driven outline (e.g., background → landscape → comparison → trade-offs → risks), organized by idea, never by input file. Prefer tables for any comparison and Mermaid diagrams (flowchart, quadrantChart, timeline) over prose wherever the content allows. Present source conflicts with evidence and a verdict inside the relevant section.
3. **Action Items / Recommendation** — shaped by the objective type:
   - Adopt-vs-not → recommendation, pros/cons table, next steps.
   - Technology survey → what to watch, what to try, what to skip.
   - Comparison → the pick, and when to choose the alternative.
   - Feasibility → go/no-go, blockers, prerequisites.
4. **Terminologies** — term/definition table, always present, placed at the back of the report before references.
5. **References** — deduplicated citations (URL, date) merged across all inputs.

### 4. Quality gates (internal — never printed in the report)

- Executive summary alone answers the research question.
- Six-hats audit passes: facts, sentiment, risks, benefits, and alternatives are all covered somewhere in the body.
- At least one table and one Mermaid diagram.
- Terminologies section present, at the back.
- Every major claim traceable to a cited source; conflicts resolved or precisely scoped, not papered over.
- No agent names, input filenames, or six-hats vocabulary anywhere in the report.
