---
name: resume
description: Resume a chat session after a context compaction or other memory-losing interruption, so nothing durable gets missed or trusted from a lossy summary. Use immediately after a compaction (manual or automatic), at the start of a session continuing prior work, or any time you suspect the conversation's own memory of session state may be stale or incomplete.
---

# Resume

The symmetric counterpart to `prepare-compact`. That skill exists because a compaction has the same practical effect as starting a fresh chat: everything not written to a durable artifact is reduced to a condensed summary. This skill exists because the summary side of that exchange is a known, generally-observed failure mode, not a hypothetical edge case: a durable session record can correctly capture that some piece of work genuinely completed, while the auto-generated compaction summary drops that detail anyway — and a resumed session that trusts the summary (or a separately-tracked status field that was never reconciled against the record) over the durable record itself can end up redoing, or worse duplicating, work that was already done. Treat this skill as the standing mitigation for that risk on the resume side, the same way `prepare-compact` is the standing mitigation on the departure side.

Do not run this skill's steps from memory of what it says below once invoked in a future session — re-read this file fresh each time, and re-derive the governing requirements from this project's own actual current source files rather than assuming they match what's written here.

**This is a state-recovery pass, not a fresh investigation.** Its job is to reconstruct accurate context from durable artifacts that already exist — a project's own session/state record, its handover artifact if it has one, live git state, and any still-running background agents — not to re-derive conclusions those artifacts already recorded, and not to re-audit work that was already independently verified and committed. If a step below tempts you into re-running full test suites or re-litigating a closed decision, stop; that belongs to whatever task comes after resume, not to resume itself.

## 1. Re-ground in this project's own governing requirements, don't assume them from memory

A compaction can lose track of project-specific governance or process rules just as easily as ordinary state. Look for, and read fresh:

- Any documented governing-rules or process-framework file this project has adopted (a constitution, a contributor/process guide, a numbered rules document) — a rule may have been added or amended in a part of the conversation the summary compressed away. If this project has none, skip ahead.
- Any project-specific extension or profile layer on top of a shared/portable framework, if this project's own setup has one (e.g. a local overlay of rules/conventions distinct from an upstream shared framework it's built on). Skipping this means operating on a framework's generic defaults instead of this project's own actual current rules.

## 2. Read the designed bootstrap artifact, if this project has one

Many projects with a formal session/handover protocol name a specific artifact as the intended entry point for a new or resuming session (sometimes explicitly documented as the sole such input). If this project has one, read it as designed, before anything else project-specific — it exists to be read first. If this project has no such artifact, skip ahead.

## 3. Read the active-session or engineering-state record in full

If this project keeps a living document tracking current work-in-progress (an active-session record, an engineering-state file, a running log), read it start to finish. Not a grep for a keyword, not the sections a handover or the compaction summary happened to reference, not a repeat of a partial read from earlier in the conversation before it was last updated — the whole file, fresh, every time this skill runs. It is the authoritative record of current state precisely because it is maintained continuously through execution, not only at closure — treat anything the compaction summary claims that this record does not corroborate as unconfirmed, and anything this record states that the summary omitted as still true. If this project has no such record, note that explicitly and rely more heavily on steps 4-5 below.

## 4. Verify live execution state, don't assume it from either artifact

- Probe for live background agents (a non-existent-task-ID probe's error response, or whatever equivalent mechanism this environment provides, lists any genuinely running agents). A compaction can sever a session's own memory of having dispatched something without severing the agent itself — if one is still running, its identity, task, and expected checkpoint must be reconciled, not silently rediscovered later or duplicated by a redundant dispatch.
- Fetch before comparing local and remote state (a local-only status check cannot see remote drift), then run a full repository-wide status check (not scoped to files a handover or session record happens to mention) to get a complete, current accounting of dirty and ahead/behind state, and compare both against what the records above lead you to expect.
- If any dirty path or unexpected commit doesn't match what the records above lead you to expect, check for whatever mechanism, if any, this project uses to declare which concurrent stream (a parallel session, a scheduled job, another contributor) owns which in-flight state — a lease file, a coordination protocol, a lock — before treating it as anomalous. Reconcile against its declared ownership rather than committing, discarding, or otherwise acting on state you haven't confirmed is actually yours to touch.

## 5. Cross-check claimed-complete work against real history before acting near it

For any item you are about to act on, or dispatch further work against, where a session record, handover, or separately-tracked status/lifecycle field claims a status: verify that status against actual repository history (commit log) for a matching completion before trusting the field alone. A status field can lag genuinely completed work, and lagging status is not itself evidence that the work remains undone. Apply this before dispatching new implementation work on anything a backlog, roadmap, or tracking file presents as open, not only when something already feels suspicious — this is the specific, mechanical check whose omission is what this skill exists to prevent.

## 6. Report plainly, then proceed

Tell the user, in plain terms, what the durable records actually show now that they've been re-read in full: what's genuinely done, what's genuinely still open, what's live and running, and what the recorded next action is. If the compaction summary and the durable records agree, say so briefly and move directly into the recorded next action rather than re-litigating it or re-asking permission for already-authorized, in-progress scope. If they disagree on anything material — a claimed-done item that history doesn't corroborate, a claimed-open item that's actually already shipped, a background agent the summary didn't mention — surface the discrepancy plainly before proceeding.

## Note on location

This skill file must live under the **primary working directory's** `.claude/skills/` to be invocable as `/resume` — Claude Code does not scan `.claude/skills/` in additional working directories for slash-command registration. If you use this skill from multiple repositories or working-directory setups, keep a copy in each one's own `.claude/skills/resume/SKILL.md` and update all copies when this file changes, the same convention `prepare-compact` already uses. A newly added or edited skill file also typically requires a fresh session before Claude Code picks it up.

If a given project also maintains a project-specific, non-generic variant of this skill (naming its own concrete files, governance documents, and incident history), that variant is the one to actually invoke and keep current for that project — this generic version is the portable baseline to adapt from, not a replacement for a project's own tailored copy where one already exists.
