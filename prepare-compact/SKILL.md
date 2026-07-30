---
name: prepare-compact
description: Prepare this chat session for a context compaction (/compact) so no in-flight work, agreed plan, or supervision state is lost. Use immediately before compacting a long-running session, especially one that has delegated background agents, uncommitted work-in-progress, or a freshly agreed multi-step plan not yet executed.
---

# Prepare for compaction

A context compaction has the same practical effect on this agent as starting a fresh chat: everything not written to a durable artifact is reduced to a condensed summary, and any live handle to a background process is gone unless it is independently re-derivable from repository state. Losing track of a delegated background agent this way is a known, generally-observed failure mode of compaction, not a hypothetical edge case — a task can keep running with no one checking on it until the user has to ask directly. Treat this skill as the standing mitigation for that risk, not a one-off cleanup.

Do not run this skill's steps from memory of what it says below once invoked in a future session — re-read this file fresh each time, and re-derive the governing requirements from this project's own actual current source files rather than assuming they match what's written here.

## 1. Confirm it is actually safe to prepare now

- Check whether any background agents/tasks are currently running (probe the task registry or equivalent mechanism this environment provides for listing in-flight delegated work). If any are running:
  - Either wait for them to finish before proceeding, or
  - If the user wants to proceed anyway, explicitly record their exact identity, assigned task, and expected next checkpoint in the handover (step 4) — do not compact with a live, undocumented agent in flight.
- Run a full repository-wide `git status --short` (not scoped to files you remember touching) to get a complete, current accounting of dirty state. Compare it against what you expect; investigate and explain anything unexpected before proceeding — git status should always be checked before any operation that could discard uncommitted work.

## 2. Read the governing requirements fresh, don't assume them

- Look for this project's own documented protocol for session records and handovers — a governing doc that specifies what a session-state file or handover artifact must contain and when it must be updated, if this project has formalized one. If it exists, read it fresh rather than assuming it matches a prior session's understanding of it. This skill's remaining steps operationalize that kind of protocol for a same-chat compaction, not only whatever cross-chat "switching sessions" trigger it may name explicitly — the practical memory-loss risk is the same in both cases, so the same rigor applies. If no such protocol doc exists in this project, proceed with steps 3 onward using ordinary judgment about what state matters.
- Find this project's active-session or engineering-state record — a living document tracking current work-in-progress, if this project keeps one — and its handover file(s), if any, and read what they currently claim before rewriting either. A stale prior state is itself information (it tells you what's actually changed since it was last updated). If this project has no such records at all, note that explicitly and skip ahead to producing one from scratch in step 4, or to skipping steps 4-5 entirely if a durable record genuinely isn't this project's convention.

## 3. Account for every piece of in-flight state

Before writing anything, make sure you can answer each of these from actual current evidence (re-check live files/commits, don't recall from earlier in the conversation):

- What has genuinely completed and been committed/pushed this session (condensed to pointers — commit hashes, file paths — not exhaustive prose)?
- Is there any uncommitted work sitting in the working tree? For each dirty file or group of files: why is it there, is it safe to commit, safe to discard, or must it be left exactly as-is pending a specific next action? Never silently commit or discard working-tree state you can't explain.
- Is there an explicit plan or decision the user just gave that has not yet been executed? Capture its exact intent and ordering, not a paraphrase that loses the sequencing or the reasoning behind it.
- Are there standing risks, stop-on conditions, or authority boundaries already recorded that remain valid? Carry them forward — do not drop a still-true boundary just because it wasn't touched this session.
- Are there decisions still pending the user's (not this agent's) judgment? Name them explicitly as open rather than letting them disappear into a summary.

## 4. Update the active-session record

If this project keeps an active-session or engineering-state record, rewrite its current-state, immediate-next-action, and current-boundaries sections (add an explicit agreed-plan section when step 3 found one) to reflect everything gathered above. Prefer pointers to authoritative files (a work order, a ledger, a specific commit) over restating their content. State the exact next action to take on resumption plainly enough that a fresh read of only this file (no conversation memory) is sufficient to resume correctly. If this project has no such record, and the state gathered in step 3 is non-trivial, create a minimal one now (or write the equivalent directly into the handover artifact in step 5) rather than letting that state exist only in the conversation about to be compacted.

## 5. Regenerate the handover artifact through its real generator, if one exists

If this project has a dedicated handover-generation script or tool, never hand-edit the handover file(s) directly — use the generator, following this rough shape:

1. Read the current handover artifact's fields describing the latest completed and currently-executing work to find the correct arguments to pass the generator (reuse them unchanged unless the underlying work identities have actually changed this session). Check the generator's help output or source for its actual argument names rather than guessing.
2. Run the generator with those arguments.
3. If the generator supports a validate-only or dry-run mode, run it and confirm the result is valid before proceeding. If it fails, fix the actual cause — a stale reference, a contradictory pair of fields, a missing input — rather than working around the validator.

If no such generator exists in this project, hand-editing the handover/session file directly is the only option — in that case, be extra careful to preserve its existing schema, format, and structure exactly, changing only the content that has genuinely changed.

## 6. Commit exactly what changed, nothing else

`git status --short` again and confirm only the session/handover files (and anything else this skill's run genuinely produced, e.g. a new backlog entry the user asked to log first) are staged — never a broad `git add`. Commit with an explicit pathspec and push. Leave any other in-flight/blocked work (per step 3) exactly as it was found.

## 7. Report readiness plainly

Tell the user, in plain terms: what was saved and where, what (if anything) is still uncommitted and why that's correct, and the exact next action recorded for resumption. Only after this should compaction actually proceed.

## Note on location

This skill file must live under the **primary working directory's** `.claude/skills/` to be invocable as `/prepare-compact` — Claude Code does not scan `.claude/skills/` in additional working directories for slash-command registration. If you use this skill from multiple repositories or working-directory setups, keep a copy in each one's own `.claude/skills/prepare-compact/SKILL.md` and update all copies when this file changes. A newly added or edited skill file also typically requires a fresh session before Claude Code picks it up.
