# AuditHive

A multi-agent website audit pipeline for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). One command — `/audit <url>` — fans out **ten specialist auditors in parallel**, then fans their findings back in through a **fix strategist** that produces a single scored, prioritized roadmap.

Point it at a URL, a set of screenshots, or a written flow description. Get back one report: what's broken, why it matters, and what to fix first.

## How it works

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/b05bc104-656e-4cbe-a2e8-8c4d92ff2a32" />

**Phase -1 — Config.** Optional `audithive.config.json`: disable agents, preset the compliance industry, set screenshot viewports, toggle the HTML report.

**Phase 0 — Intake.** The orchestrator parses the target (URL, file paths, or flow description), an optional core task, and the `--verify` / `--benchmark` flags, and confirms the target is reachable before spending tokens on the fan-out.

**Phase 0.5 — Rendered capture.** Raw HTML fetches miss everything JavaScript renders, so the orchestrator captures full-page desktop and mobile screenshots via Playwright first and hands them to every auditor. If Playwright isn't available it falls back to HTML-only and says so in the report.

**Phase 1 — Parallel fan-out.** All ten auditors launch simultaneously as independent subagents, each with its own context, specialty, and rigid output format. Findings are ID-prefixed per specialist (F- friction, A- accessibility, N- first-time-user, T- task-flow, E- error-handling, C- copy, V- visual, VC- vibe-coding, CP- compliance, PS- performance) so the synthesis step can cross-reference them.

**Phase 2 — Fan-in.** The fix-strategist consumes all reports and produces 0–100 health scores per category plus a prioritized roadmap — ranked by usability, accessibility, and conversion impact, with validation criteria for each fix.

**Phase 3 — Deliverables.** A markdown report (roadmap and scores up front, raw specialist reports as an appendix) plus a self-contained HTML dashboard with score cards and collapsible findings.

## The ten auditors

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
| `performance-auditor` | Core Web Vitals (LCP, INP, CLS) via the PageSpeed Insights API, mobile and desktop |

Plus the synthesis agent:

| Agent | Role |
|---|---|
| `fix-strategist` | Runs after the auditors complete. Merges findings into health scores and a prioritized fix roadmap with validation criteria; handles re-audit diffs and competitor comparisons |

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

No build step. The agents use built-in Claude Code tools (WebFetch, WebSearch, Read, Glob, Bash). [Playwright](https://playwright.dev) is an optional dependency — with it, auditors see real rendered pages instead of raw HTML; without it, the pipeline still runs.

## Usage

```
/audit https://example.com
/audit https://example.com core task: "book an appointment"
/audit screenshots/checkout-1.png screenshots/checkout-2.png core task: "complete checkout"
/audit flow-description.md
```

Re-audit after shipping fixes — findings get classified RESOLVED / PERSISTING / NEW, with score deltas:

```
/audit https://example.com --verify audit-output/AUDIT-REPORT-20260701.md
```

Benchmark against a competitor — same pipeline runs on both, and the roadmap includes a category-by-category comparison:

```
/audit https://example.com --benchmark https://competitor.com
```

Optional `audithive.config.json` in the working directory:

```json
{
  "disabled_agents": ["vibe-coding-auditor"],
  "industry": "e-commerce",
  "viewports": { "desktop": [1440, 900], "mobile": [390, 844] },
  "html_report": true
}
```

The run ends with a short executive summary in chat, finding counts, the overall health score, and the full report at `audit-output/AUDIT-REPORT-[date].md` (+ `.html` dashboard). The pipeline deliberately stops there — it never starts implementing fixes on its own.

## Design notes

- **Parallel by design.** The ten auditors are independent, so they run as a single parallel dispatch — wall-clock time is roughly one audit, not ten.
- **Strict output contracts.** Every auditor emits a fixed report format with ID-prefixed findings, which is what makes mechanical synthesis, scoring, and re-audit diffs possible.
- **Scope discipline.** Each agent is told to stay in its lane (the copy auditor doesn't grade visuals, the compliance auditor doesn't grade copy), which minimizes duplicate findings.
- **Clean results are valid.** Auditors are instructed not to manufacture problems when something is genuinely fine.
- **Measured, not guessed.** Performance comes from the PageSpeed API and screenshots come from a real browser; where measurement fails, findings are marked UNVERIFIED instead of invented.
- **Adapt the specialists.** Each auditor is a standalone markdown file — edit one, drop in your own, or tune the compliance auditor's industry checks to your domain without touching the rest of the pipeline.

## Customizing

- **Add an auditor:** create a new agent .md with a unique finding prefix, and add it to the Phase 1 list in `commands/audit.md`.
- **Remove one:** delete the agent file and its line in `commands/audit.md` — or just list it in `disabled_agents` in the config.
- **Change models:** each agent's frontmatter declares its `model` — the ten auditors default to `sonnet`; the fix-strategist uses a heavier model for synthesis.

## License

[MIT](LICENSE)
