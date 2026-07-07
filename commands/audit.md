---
description: Run the full 9-agent parallel UX/accessibility/compliance audit on a URL, screenshots, or flow description, and synthesize a prioritized roadmap.
argument-hint: <url-or-file-paths> [core task: "..."]
---

# AuditHive - UX Audit Pipeline

Target: $ARGUMENTS

You are the orchestrator for a fan-out/fan-in audit pipeline. Follow these phases exactly.

## Phase 0 - Intake

Parse the arguments:
- TARGET: a URL, one or more screenshot/file paths, or a flow description
- CORE_TASK: if the arguments include a quoted core task (e.g. core task: "book an appointment"), extract it. If absent, note that the task-flow auditor must infer it.

If the target is a URL, fetch it once yourself to confirm it is reachable before spending tokens on the fan-out. If unreachable, stop and report. If the target is file paths, confirm the files exist.

## Phase 1 - Parallel fan-out (9 agents)

Dispatch ALL NINE audit subagents IN PARALLEL in a single message (do not wait for one before launching the next):

1. ux-friction-auditor
2. accessibility-auditor
3. first-time-user-auditor
4. task-flow-auditor (include CORE_TASK in its prompt, or instruct it to infer one)
5. error-handling-auditor
6. ux-copy-auditor
7. visual-design-auditor
8. vibe-coding-auditor
9. compliance-auditor

Each dispatch prompt MUST include: the TARGET (full URL or exact file paths), the CORE_TASK if known, and the instruction to follow its own output format exactly. Subagents have no access to this conversation, so pass everything they need.

Do NOT dispatch fix-strategist in this phase. It depends on the others' output.

## Phase 2 - Sequential fan-in (synthesis)

When all nine reports have returned, dispatch the fix-strategist subagent ONCE, passing the nine complete reports verbatim in its prompt. It will return the prioritized fix roadmap.

## Phase 3 - Deliverable

Write one file to an audit-output/ directory (create it if needed), then present it to the user:

### audit-output/AUDIT-REPORT-[YYYYMMDD].md
Assemble in this order:
- The fix-strategist's full roadmap (executive summary first)
- A findings appendix containing all nine raw specialist reports

## Phase 4 - Handoff to the user

End your response with:
1. A five-line-max executive summary in chat
2. The counts: total findings, blockers, NOW-tier items
3. This exact closing: "Review AUDIT-REPORT-[date].md for the full roadmap and findings."

Do NOT begin implementing any fixes yourself. Your job ends at the reviewed prompt.
