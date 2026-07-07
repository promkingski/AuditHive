# AuditHive

A multi-agent website audit pipeline for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). One command — `/audit <url>` — fans out **eleven specialist auditors in parallel**, then fans their findings back in through a **fix strategist** that produces a single scored, prioritized roadmap. A live browser dashboard shows the run as it happens.

Point it at a URL, a set of screenshots, or a written flow description. Get back one report: what's broken, why it matters, and what to fix first.

## How it works

<img width="1254" height="1254" alt="AuditHiveDiragram" src="https://github.com/user-attachments/assets/a8b3b53c-b487-45b7-93c7-9224bdf166fb" />


**Phase D — Dashboard bootstrap.** The orchestrator starts a tiny Python-stdlib server and opens a browser dashboard that polls the run's `status.json`, so you can watch every phase and agent live. See [Live dashboard](#live-dashboard) below.

**Phase -1 — Config.** Optional `audithive.config.json`: disable agents, preset the compliance industry, set screenshot viewports, toggle the HTML report.

**Phase 0 — Intake.** The orchestrator parses the target (URL, file paths, or flow description), an optional core task, and the `--verify` / `--benchmark` flags, and confirms the target is reachable before spending tokens on the fan-out.

**Phase 0.5 — Rendered capture.** Raw HTML fetches miss everything JavaScript renders, so the orchestrator captures full-page desktop and mobile screenshots via Playwright first and hands them to every auditor. If Playwright isn't available it falls back to HTML-only and says so in the report.

**Phase 1 — Parallel fan-out.** All eleven auditors launch simultaneously as independent subagents, each with its own context, specialty, and rigid output format. Findings are ID-prefixed per specialist (F- friction, A- accessibility, N- first-time-user, T- task-flow, E- error-handling, C- copy, V- visual, VC- vibe-coding, CP- compliance, PS- performance, H- hate-agent) so the synthesis step can cross-reference them.

**Phase 2 — Fan-in.** The fix-strategist consumes all reports and produces 0–100 health scores per category plus a prioritized roadmap — ranked by usability, accessibility, and conversion impact, with validation criteria for each fix. The adversarial hate-agent's findings are weighed as devil's-advocate input — promoted only when corroborated, and never counted toward the health scores.

**Phase 3 — Deliverables.** A markdown report (roadmap and scores up front, raw specialist reports as an appendix) plus a self-contained HTML dashboard with score cards and collapsible findings.

## The eleven auditors

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
| `hate-agent` | Deliberate devil's advocate — tears holes in the design and argues it's worse than everyone thinks; self-rates each jab LEGIT / SPICY / PURE VENOM. Advisory pressure-testing, not verified defects |

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

## Live dashboard

Every `/audit` run opens a browser dashboard that shows the run as it happens. It is a single self-contained page served by a tiny Python-stdlib server — no npm, no pip, no frameworks, no CDNs.

```
dashboard/dashboard.html   # the UI (inline CSS/JS)
dashboard/serve.py         # http.server-based backend
```

The orchestrator starts it automatically (Phase D), but you can also run it standalone to configure a run before launching:

```
python C:\Users\carte\.claude\dashboard\serve.py [AGENTS_DIR] [--port N]
# AGENTS_DIR defaults to C:\Users\carte\.claude\agents
```

It picks a free port (preferring 8787), prints `AuditHive dashboard: http://localhost:PORT/`, and serves the working directory's `audit-output/` for reports and screenshots.

**Three views in one page:**

- **Launcher** — a form for the target URL, core task, `--benchmark` rival, `--verify` previous report, industry preset, and viewport sizes, plus a checkbox per agent (to disable it) and a **model dropdown** per agent. **Save config & models** writes `audithive.config.json` to the working directory *and* applies the model changes to the agent files. **Copy command** builds the exact `/audit …` string (with `--verify` / `--benchmark` flags) to paste into Claude Code — the GUI can't launch Claude itself.
- **Live progress** — polls `audit-output/status.json` every 2s: a phase banner (config → intake → screenshots → fan-out → benchmark → synthesis → report → complete), a card per agent showing QUEUED / RUNNING / DONE (with finding count) / SKIPPED / FAILED and the model it ran on, and a live elapsed timer.
- **Report** — once the run reaches `complete`, loads that run's `AUDIT-REPORT-*.html` inline, with a collapsible "Run prompt" section showing the exact command, config, and per-agent models used.

### Model switching from the GUI

The Launcher's per-agent model dropdowns (`haiku` / `sonnet` / `opus` / `fable`) let you retune which model each agent runs on without hand-editing frontmatter. On save, the server (`POST /models`) edits **only** the `model:` line inside each agent's frontmatter:

- The chosen model is validated against the allowlist (`haiku`, `sonnet`, `opus`, `fable`); anything else is rejected and the file is left untouched.
- If an agent has no `model:` line, one is inserted into the frontmatter rather than rewriting the file.
- Nothing below the frontmatter is ever touched.

### `.bak` backups

The **first** time the server modifies a given agent file, it writes a one-time `<agent>.md.bak` alongside it holding the original contents. Subsequent model changes to that same file do **not** overwrite the backup — so `<agent>.md.bak` always preserves the original frontmatter you started with. To restore an agent, copy its `.bak` back over the `.md`. The backups are safe to delete once you're happy with your model choices.

> The dashboard is best-effort: if Python isn't available or the server can't start, the audit still runs headless and `status.json` is still written — it just isn't being served.

## Design notes

- **Parallel by design.** The eleven auditors are independent, so they run as a single parallel dispatch — wall-clock time is roughly one audit, not eleven.
- **Strict output contracts.** Every auditor emits a fixed report format with ID-prefixed findings, which is what makes mechanical synthesis, scoring, and re-audit diffs possible.
- **Scope discipline.** Each agent is told to stay in its lane (the copy auditor doesn't grade visuals, the compliance auditor doesn't grade copy), which minimizes duplicate findings.
- **Clean results are valid.** Auditors are instructed not to manufacture problems when something is genuinely fine.
- **Measured, not guessed.** Performance comes from the PageSpeed API and screenshots come from a real browser; where measurement fails, findings are marked UNVERIFIED instead of invented.
- **Adapt the specialists.** Each auditor is a standalone markdown file — edit one, drop in your own, or tune the compliance auditor's industry checks to your domain without touching the rest of the pipeline.

## Customizing

- **Add an auditor:** create a new agent .md with a unique finding prefix, and add it to the Phase 1 list in `commands/audit.md`.
- **Remove one:** delete the agent file and its line in `commands/audit.md` — or just list it in `disabled_agents` in the config.
- **Change models:** each agent's frontmatter declares its `model` — the eleven auditors default to `sonnet`; the fix-strategist uses a heavier model for synthesis. You can also switch models per agent from the [live dashboard](#live-dashboard) launcher without editing files by hand.

## License

[MIT](LICENSE)
