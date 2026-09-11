# AGENTS.md (global)

Rules that apply to all workspaces and projects.

## Behavioral guidelines (Karpathy principles)

Guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Deletion Safety

- All delete operations must be routed to the recycle bin. Direct deletion is forbidden.
- Never use `rm`, `del`, `Remove-Item` (without recycle), or any permanent-delete command on files or folders.
- To delete on Windows, move the target to the Recycle Bin (e.g. via PowerShell `Shell.Application` / `Microsoft.VisualBasic.FileIO.FileSystem.DeleteFile/DeleteDirectory` with `RecycleOption`).
- If a recycle-bin deletion is genuinely impossible (e.g. inside a sandbox or CI), stop and ask the user before doing anything destructive.

## Work Summaries

- Work summary files are stored in `D:\zcode-home\work-summaries\`.
- Files placed directly in `work-summaries\` are for long-term retention. Temporary summaries go in `work-summaries\temp\` and may be cleaned up later.
- Only create a summary file when the user explicitly asks for one; never generate summaries unprompted.

## Config Backup (git)

- `C:\Users\DELL\.zcode` is a git repository backing up to `https://github.com/0610name/zcode-config` (private).
- After every modification to this file (AGENTS.md) or anything under `skills\`, commit the change and push to GitHub.
- Keep commits small and descriptive; never force-push.

## Network / Proxy

- A Clash proxy runs locally at `http://127.0.0.1:7897` (mixed port), which can reach Google, GitHub, and other blocked sites.
- For command-line tools executed locally (curl, etc.), set `http_proxy`/`https_proxy` to this address for the duration of the command.
- Git is already configured to use this proxy for github.com only.
- Browser rules: Edge must NEVER go through Clash — its Google access is handled by its own Ghelper extension, and this applies to automation driving Edge too (no `--proxy-server` flag on Edge). Only when automation launches a non-Edge browser (e.g. a standalone Chromium), launch it with `--proxy-server=http://127.0.0.1:7897`. Do NOT rely on the system proxy — it is intentionally disabled on this machine.
- If a proxied request fails, the proxy may be off — tell the user instead of retrying indefinitely.

## File & Folder Naming

- Always name new files and folders in English only (ASCII letters, digits, hyphens/underscores, dots).
- No Chinese or other non-ASCII characters in file or folder names.
- If the user requests a name in another language, translate it to concise English first, and mention the translation you chose.
