---
name: code-reviewer
description: This skill should be used after code is written or edited, or when the user asks to "review this code", "check my code", "look over what I just wrote", or "soft review". Performs a lightweight advisory review covering logic, edge cases, error handling, naming, conventions, and light security — non-blocking, always advisory.
version: 0.1.0
---

# Code Reviewer

Perform a soft, advisory review of newly written or modified code. Surface observations — never block the task.

## Tone and Scope

This is a lightweight review, not a full audit. The goal is to catch what the author's eye might miss immediately after writing. Keep it brief and useful:

- Maximum 10 observations total
- If nothing worth flagging: output a single line — "Looks good — no significant issues found."
- Advisory only — offer the observation and a concrete suggestion, then move on

## Review Checklist

Work through these in order. Stop at 10 total observations across all categories.

### 1. Logic Correctness

Does the code do what the surrounding context implies it should?

- Trace the primary execution path mentally
- Check that return values, mutations, and side effects match the stated intent
- Look for off-by-one errors, wrong comparison operators (`>` vs `>=`), or inverted conditions

### 2. Edge Cases

What inputs or states could cause unexpected behavior?

- Null / nil / undefined / None
- Empty collections (zero items, empty string)
- Boundary values (zero, negative numbers, maximum integer, empty/single-character strings)
- Concurrent or re-entrant calls (if the code is stateful)

### 3. Error Handling

Are errors handled at the right level?

- Are exceptions or errors caught too broadly (bare `except`, `catch (e) {}`)
- Are errors swallowed silently without logging or re-throwing
- Are error messages specific enough to diagnose the problem

### 4. Naming and Clarity

Do names communicate intent accurately?

- Variable or function names that are misleading or too generic (`data`, `temp`, `result`, `flag`)
- Boolean names that don't read naturally as a condition (`isValid`, `hasItems` are good; `check`, `status` are not)
- Functions that do more than their name implies

### 5. Project Conventions

Does the new code match the existing codebase style?

- Compare imports, function signatures, error handling patterns, and naming to nearby code
- Note if a pattern is used elsewhere but not here (e.g., the rest of the file uses Result types but this function throws)
- Flag if a utility or helper that already exists in the codebase was reimplemented

### 6. Light Security Flags

Obvious issues only — this is not a security audit:

- String interpolation or concatenation directly into SQL or shell commands
- Hardcoded credentials, API keys, or tokens
- User input passed to `eval`, `exec`, or `Function()`
- HTTP (not HTTPS) hardcoded URLs in non-test code

## Output Format

```
CODE REVIEW
===========
File(s): <filename(s)>

[Suggestion] <category> — <file>:<line if known>
  <Observation in one sentence.>
  → <Concrete suggestion.>

[Minor] <category> — <file>:<line if known>
  <Observation.>
  → <Suggestion.>

[Note] <category>
  <Informational observation with no required action.>
```

Severity levels:
- **Suggestion** — worth fixing before merge; clear improvement
- **Minor** — small issue; fix if convenient
- **Note** — informational; no action required

End with a one-line summary:
- "X suggestion(s), Y minor issue(s) — all non-blocking."
- Or: "Looks good — no significant issues found."

## What Not to Flag

- Style preferences that are not objectively wrong and not inconsistent with the codebase
- Refactoring opportunities unrelated to the change at hand
- Missing features or functionality outside the scope of what was asked
- Things already caught by the project's linter or formatter (if one is configured)
