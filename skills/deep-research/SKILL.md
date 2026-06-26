---
name: deep-research
description: This skill should be used when the user asks to "explore", "do a deep dive", "research in depth", "investigate", "survey the landscape of", or starts a request with "Exploration:" or "Deep Dive:". Conducts exhaustive multi-source research and produces a structured EXPLORATION_REPORT.md with conflict synthesis and gap analysis.
version: 0.1.0
---

# Deep Research

Conduct exhaustive, multi-source research and synthesize findings into a structured EXPLORATION_REPORT.md.

## Phase 1 — Source Discovery (minimum 8 unique sources)

Search across diverse, orthogonal source categories. Do not cluster sources within a single domain:

| Category | Examples |
|---|---|
| Official documentation | Language specs, RFC documents, vendor docs |
| Academic / research | arXiv, Google Scholar, ACM, IEEE |
| Industry analysis | Analyst reports, company engineering blogs |
| Community discourse | GitHub issues/discussions, Reddit, Hacker News threads |
| Practitioner writing | Dev blogs, newsletters, conference talks |
| Contrarian / critical | Critique articles, postmortems, "considered harmful" pieces |
| Recent news | Release announcements, changelogs |
| Adjacent domains | How similar problems are solved in related fields |

For each source, record:
- URL or full citation
- Publication date
- Author or organization
- Key claim or insight (one sentence)

**Minimum**: 8 distinct sources from at least 4 different categories, including at least one contrarian or critical source.

## Phase 2 — Conflict Synthesis

Identify where sources disagree. Conflicting viewpoints are as valuable as consensus:

1. Name the disagreement clearly (e.g., "Performance claim conflict between X and Y")
2. Summarize each position with its source
3. Assess which position has stronger evidence or more recent data
4. Note where the truth is genuinely uncertain or context-dependent

Do not paper over disagreements with "it depends" without specifying what it depends on.

## Phase 3 — Output: EXPLORATION_REPORT.md

Write the report to the current working directory using this structure:

```markdown
# Exploration Report: <Topic>

**Date**: <ISO date>
**Sources consulted**: <count>

## Executive Summary

<3–5 sentences synthesizing the most important findings. Write this last.>

## Landscape Map

### Current State
<What exists today, key players, dominant approaches>

### Emerging Trends
<What is changing, what is gaining or losing adoption>

### Key Trade-offs
<Core tensions practitioners navigate — be specific, not generic>

## Gap Analysis

### Unsolved Problems
<What the field has not yet adequately addressed>

### Conflicting Evidence
<Where sources disagree and the nature of the disagreement>

### Open Questions
<What remains unknown, debated, or highly context-dependent>

## Source Index

| # | Source | Date | Key Insight |
|---|---|---|---|
| 1 | <citation or URL> | <date> | <one-sentence insight> |
...

## Methodology Notes

<Caveats about source quality, recency gaps, coverage limitations, or search constraints>
```

## Quality Gates

Before writing the report, verify:
- At least 8 sources from at least 4 categories
- At least one contrarian or critical source is included
- At least one genuine conflict is documented in Phase 2
- Executive Summary is written after all other sections are complete
- No source is cited without a specific key insight attributed to it
