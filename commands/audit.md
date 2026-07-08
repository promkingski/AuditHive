---
description: Run the full parallel UX/accessibility/compliance/performance audit on a URL, screenshots, or flow description, and synthesize a scored, prioritized roadmap. Opens a live browser dashboard, and supports re-audit diffs (--verify), competitor benchmarks (--benchmark), and an optional config file.
argument-hint: <url-or-file-paths> [core task: "..."] [--verify <previous-report.md>] [--benchmark <competitor-url>]
---

# AuditHive - UX Audit Pipeline

Target: $ARGUMENTS

You are the orchestrator for a fan-out/fan-in audit pipeline. Follow these phases exactly.

Throughout the run you maintain a live status file, `audit-output/status.json`, that a browser dashboard polls. Its schema is:

```json
{
  "run_id": "AUDIT-20260707-<hhmmss>",
  "started_at": "<ISO-8601>",
  "phase": "config|intake|screenshots|fan-out|benchmark|synthesis|report|complete",
  "target": "<url or paths or description>",
  "core_task": "<string or null>",
  "benchmark_url": "<url or null>",
  "agents": {
    "<agent-name>": { "state": "queued|running|done|skipped|failed", "model": "<model>", "findings": <int or null> }
  },
  "report_md": "<path or null>",
  "report_html": "<path or null>",
  "fix_prompt": "<path or null>",
  "totals": { "findings": <int>, "blockers": <int>, "now_items": <int>, "overall_score": <int> }
}
```

Rewrite the whole file (not append) at every phase transition so `phase` is always current. Never let a stale phase linger. If any status write fails, keep going — the audit itself must not be blocked by the dashboard.

## Phase D - Dashboard bootstrap (do this first)

1. Create `audit-output/` if it does not exist.
2. Start the dashboard server in the background from the working directory:
   `python C:\Users\carte\.claude\dashboard\serve.py C:\Users\carte\.claude\agents`
   It picks a free port (preferring 8787), prints `AuditHive dashboard: http://localhost:PORT/`, and writes that URL to `audit-output/.dashboard-url`. Capture the port from either.
3. Open the browser to that URL: on Windows, `start "" http://localhost:PORT/`.
4. Write the initial `status.json` with `phase: "config"`, the `run_id`, `started_at`, `target`, `core_task`, `benchmark_url`, and an `agents` map of every agent you intend to dispatch set to `state: "queued"` with `findings: null`. Populate each agent's `model` by reading the `model:` frontmatter line of its file in `C:\Users\carte\.claude\agents\` (an agent with no `model:` line inherits the default — record `"default"`). Include `fix-strategist` in the map too.
5. If Python is unavailable or the server fails to start, note it and continue the audit headless — every later phase still writes `status.json`, it just is not being served.

The dashboard's launcher can also be used before a run to edit `audithive.config.json` and per-agent models; those edits land in the same files this pipeline reads, so honor whatever is there when Phase -1 runs.

## Phase -1 - Config (optional)

If `audithive.config.json` exists in the working directory, read it. Recognized keys (all optional):

```json
{
  "disabled_agents": ["vibe-coding-auditor"],
  "industry": "e-commerce",
  "viewports": { "desktop": [1440, 900], "mobile": [390, 844] },
  "html_report": true
}
```

- `disabled_agents`: skip these in the fan-out (never disable fix-strategist).
- `industry`: pass to the compliance-auditor as its assumed industry.
- `viewports`: screenshot sizes for Phase 0.5.
- `html_report`: set false to skip the HTML dashboard. Default true.

No config file means all agents enabled and defaults used.

## Phase 0 - Intake

Parse the arguments:
- TARGET: a URL, one or more screenshot/file paths, or a flow description
- CORE_TASK: if the arguments include a quoted core task (e.g. core task: "book an appointment"), extract it. If absent, note that the task-flow auditor must infer it.
- VERIFY_REPORT: if `--verify <path>` is present, read that previous AUDIT-REPORT file. If it does not exist, stop and report.
- BENCHMARK_URL: if `--benchmark <url>` is present, capture the competitor URL.

Set `status.json` `phase` to `"intake"`. If the target is a URL, fetch it once yourself to confirm it is reachable before spending tokens on the fan-out. If unreachable, set `phase: "failed"` in status.json, stop, and report. If the target is file paths, confirm the files exist.

## Phase 0.5 - Rendered capture (URL targets only)

Set `status.json` `phase` to `"screenshots"`. WebFetch returns raw HTML without executing JavaScript, so on client-rendered sites the auditors would grade an empty shell. Capture real rendered screenshots first:

1. Check Playwright: `npx playwright --version`. If missing, try `npm install -D playwright && npx playwright install chromium --with-deps` (ask the user before installing if this is an interactive session).
2. Capture full-page screenshots of TARGET at the desktop and mobile viewports into `audit-output/screenshots/` (`desktop.png`, `mobile.png`), e.g.:
   `npx playwright screenshot --viewport-size=1440,900 --full-page <TARGET> audit-output/screenshots/desktop.png`
   `npx playwright screenshot --viewport-size=390,844 --full-page <TARGET> audit-output/screenshots/mobile.png`
3. If BENCHMARK_URL is set, capture the same pair into `audit-output/screenshots/competitor-*.png`.
4. If Playwright is unavailable or capture fails, proceed WebFetch-only, and record in the final report that findings are based on unrendered HTML.

Pass the screenshot file paths to every auditor in Phase 1 alongside the URL.

## Phase 1 - Parallel fan-out (11 agents)

Set `status.json` `phase` to `"fan-out"`. For any agent skipped by config or inapplicability (e.g. performance-auditor on a non-URL target), set its state to `"skipped"` now. As you dispatch, set each dispatched agent's state to `"running"`; as each report returns, set it to `"done"` and fill `findings` with that report's finding count (or `"failed"` if it errored). Rewrite status.json each time a state changes so the dashboard reflects live progress.

Dispatch ALL enabled audit subagents IN PARALLEL in a single message (do not wait for one before launching the next):

1. ux-friction-auditor
2. accessibility-auditor
3. first-time-user-auditor
4. task-flow-auditor (include CORE_TASK in its prompt, or instruct it to infer one)
5. error-handling-auditor
6. ux-copy-auditor
7. visual-design-auditor
8. vibe-coding-auditor
9. compliance-auditor (include `industry` from config if set)
10. performance-auditor (URL targets only - skip for screenshot/description targets)
11. hate-agent (devil's advocate - see weighting note below)

Each dispatch prompt MUST include: the TARGET (full URL or exact file paths), the screenshot paths from Phase 0.5 (tell the auditor to Read them - they show the rendered page), the CORE_TASK if known, and the instruction to follow its own output format exactly. Subagents have no access to this conversation, so pass everything they need.

The hate-agent is a deliberate devil's advocate. Its report is adversarial pressure-testing, NOT a list of verified defects. It is disabled by the same `disabled_agents` config as any other agent. Keep its report clearly labeled so the fix-strategist knows to weigh it, not obey it.

Do NOT dispatch fix-strategist in this phase. It depends on the others' output.

## Phase 1.5 - Benchmark fan-out (only if --benchmark)

Set `status.json` `phase` to `"benchmark"`. After the Phase 1 reports return, run the same parallel fan-out once more against BENCHMARK_URL (competitor screenshots included). Keep the two report sets clearly labeled TARGET and COMPETITOR. (Competitor runs do not need their own agent state entries in status.json.)

## Phase 2 - Sequential fan-in (synthesis)

Set `status.json` `phase` to `"synthesis"` and set the fix-strategist's state to `"running"`. When all reports have returned, dispatch the fix-strategist subagent ONCE. Pass in its prompt:
- the complete TARGET reports, verbatim (including the hate-agent report if it ran - tell the strategist to treat H- findings as advisory devil's-advocate input per its own weighting rules, not as verified defects)
- the previous report, verbatim, if VERIFY_REPORT is set (tell it to run its verify-mode diff)
- the COMPETITOR reports, verbatim, if benchmarking (tell it to run its benchmark comparison)

It will return the scored, prioritized fix roadmap.

## Phase 3 - Deliverables

Set `status.json` `phase` to `"report"` and the fix-strategist's state to `"done"`. Write to an `audit-output/` directory (create it if needed), then present the files to the user:

### audit-output/AUDIT-REPORT-[YYYYMMDD].md
Assemble in this order:
- The fix-strategist's full roadmap (executive summary and health scores first)
- A findings appendix containing all raw specialist reports (competitor reports last, if any)

### audit-output/AUDIT-REPORT-[YYYYMMDD].html (unless html_report is false)
A single self-contained HTML file (inline CSS, no external requests) rendering the same content as a dashboard:
- Health-score cards across the top (score, category, delta if verify mode)
- The NOW / NEXT / LATER roadmap tables
- Collapsible `<details>` sections for each specialist's raw report
Keep it clean and printable; no JavaScript frameworks.

### audit-output/FIX-PROMPT-[YYYYMMDD].md
The fix-strategist's "Fix prompt" section, written out as its own file so it can be handed straight to a coding agent without opening the full report. Take the content of the fenced `text` block verbatim (unwrap the fence - the file IS the prompt), and prepend nothing but a one-line `<!-- Generated by AuditHive from AUDIT-REPORT-[date] -->` comment. Confirm it covers every NOW/NEXT/LATER item; if the strategist truncated it, fill it in from the roadmap before writing. This file must stand alone - no reference back to the report.

## Phase 4 - Handoff to the user

Final status write: set `status.json` `phase` to `"complete"`, fill `report_md`, `report_html`, and `fix_prompt` with the deliverable paths (relative to the working directory, e.g. `audit-output/AUDIT-REPORT-20260707.html` and `audit-output/FIX-PROMPT-20260707.md`; leave `report_html` null if `html_report` was false), and fill `totals` with `findings`, `blockers`, `now_items`, and `overall_score` from the fix-strategist's roadmap. The dashboard's Report view loads the HTML report, links the fix prompt, and shows the run's command and per-agent models once it sees `phase: "complete"`.

End your response with:
1. A five-line-max executive summary in chat
2. The counts: total findings, blockers, NOW-tier items, and the overall health score (with delta if verify mode)
3. This exact closing: "Review AUDIT-REPORT-[date].md for the full roadmap, or hand FIX-PROMPT-[date].md straight to a coding agent to implement the fixes."

Do NOT begin implementing any fixes yourself. Your job ends at the reviewed report.
