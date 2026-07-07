# AuditHive

A multi-agent website audit pipeline for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). One command — `/audit <url>` — fans out **nine specialist auditors in parallel**, then fans their findings back in through a **fix strategist** that produces a single prioritized roadmap.

Point it at a URL, a set of screenshots, or a written flow description. Get back one report: what's broken, why it matters, and what to fix first.

## How it works

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/b05bc104-656e-4cbe-a2e8-8c4d92ff2a32" />


**Phase 0 — Intake.** The orchestrator parses the target (URL, file paths, or flow description) and an optional core task, and confirms the target is reachable before spending tokens on the fan-out.

**Phase 1 — Parallel fan-out.** All nine auditors launch simultaneously as independent subagents, each with its own context, specialty, and rigid output format. Findings are ID-prefixed per specialist (F- friction, A- accessibility, N- first-time-user, T- task-flow, E- error-handling, C- copy, V- visual, VC- vibe-coding, CP- compliance) so the synthesis step can cross-reference them.

**Phase 2 — Fan-in.** The fix-strategist consumes all nine reports and produces a prioritized roadmap — ranked by usability, accessibility, and conversion impact, with validation criteria for each fix.

**Phase 3 — Deliverable.** Everything lands in one markdown report: executive summary and roadmap up front, all nine raw specialist reports as an appendix.

## The nine auditors

| Agent | Specialty |
|---|---|
| `ux-friction-auditor` | Cognitive load, hesitation points, moments the interface makes users think too hard |
| `accessibility-auditor` | WCAG 2.1/2.2 AA — contrast, keyboard nav, screen-reader compatibility; blockers vs quality-of-life |
| `first-time-user-auditor` | Simulates a user with zero context: assumed knowledge, unclear terminology, ambiguous next steps |
| `task-flow-auditor` | Walks the primary task end-to-end; finds unnecessary steps and abandonment points |
| `error-handling-auditor` | Invalid input, wrong clicks, incomplete actions; blaming error messages and missing recovery paths |
| `ux-copy-auditor` | Buttons, labels, tooltips, messages — vague or inconsistent language, with rewrites |
| `visual-design-auditor` | Where aesthetics beat usability: contrast, tap targets, low-visibility elements |
| `vibe-coding-auditor` | Detects unreviewed AI-generated builds: leftover placeholders, template defaults, dead UI |
| `compliance-auditor` | Legal "site furniture": privacy policy, terms, cookie consent, CCPA links, plus industry-specific disclosures |

Plus the synthesis agent:

| Agent | Role |
|---|---|
| `fix-strategist` | Runs after all nine complete. Merges findings into a prioritized fix roadmap with validation criteria |

## Installation

Copy the files into your Claude Code config:

```
# personal (all projects)
cp agents/*.md   ~/.claude/agents/
cp commands/*.md ~/.claude/commands/

# or per-project
cp agents/*.md   your-project/.claude/agents/
cp commands/*.md your-project/.claude/commands/
```

That's it — no build step, no dependencies. The agents use only built-in Claude Code tools (WebFetch, WebSearch, Read, Glob, Bash).

## Usage

```
/audit https://example.com
/audit https://example.com core task: "book an appointment"
/audit screenshots/checkout-1.png screenshots/checkout-2.png core task: "complete checkout"
/audit flow-description.md
```

Passing a core task sharpens the task-flow audit; without one, the auditor infers the site's primary task.

The run ends with a short executive summary in chat, finding counts, and the full report at `audit-output/AUDIT-REPORT-[date].md`. The pipeline deliberately stops there — it never starts implementing fixes on its own.

## Design notes

- **Parallel by design.** The nine auditors are independent, so they run as a single parallel dispatch — wall-clock time is roughly one audit, not nine.
- **Strict output contracts.** Every auditor emits a fixed report format with ID-prefixed findings, which is what makes mechanical synthesis possible.
- **Scope discipline.** Each agent is told to stay in its lane (the copy auditor doesn't grade visuals, the compliance auditor doesn't grade copy), which minimizes duplicate findings.
- **Clean results are valid.** Auditors are instructed not to manufacture problems when something is genuinely fine.
- **Adapt the specialists.** Each auditor is a standalone markdown file — edit one, drop in your own, or tune the compliance auditor's industry checks to your domain without touching the rest of the pipeline.

## Customizing

- **Add an auditor:** create a new agent .md with a unique finding prefix, and add it to the Phase 1 list in `commands/audit.md`.
- **Remove one:** delete the agent file and its line in `commands/audit.md`.
- **Change models:** each agent's frontmatter declares its `model` — the nine auditors default to `sonnet`; the fix-strategist uses a heavier model for synthesis.

## License

[MIT](LICENSE)
