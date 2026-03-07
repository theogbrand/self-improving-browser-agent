# Trace Viewer UI — Updated Plan

## Context
CLI logs from a browser automation agent (Gemini hackathon) are saved as JSONL in `/Users/ob1/projects/hackathons/gemini-hackathon/traces/run_*/`. Currently only viewable in the terminal. We need a web UI to browse and view these traces with live auto-refresh, the ability to stop the agent, and inject human messages (human-in-the-loop) at any point — sending the full historical messages + logs each time.

## File Structure
```
/Users/ob1/projects/hackathons/gh-2/
  server.py    # ~150 lines: FastAPI server with WebSocket + control file API
  index.html   # ~450 lines: Single-file UI with inline CSS/JS
```

## Architecture

### Live updates: WebSocket (not REST polling)
WebSocket is required because we need bidirectional communication — the server pushes new log lines to the browser, and the browser sends stop/inject commands back. REST polling can't do the inject direction cleanly.

### Agent control: Control file
Between turns, the agent checks `{traceDir}/control.json`. The UI server writes this file to signal commands. This is the least invasive change to the agent — ~10 lines added to the existing loop.

```
agent loop iteration
  -> check {traceDir}/control.json
     -> {"action": "stop"}                    -> exit gracefully
     -> {"action": "inject", "message": "..."}  -> push msg into history[] as user turn, log it to trace, delete control file, continue
  -> call Gemini
  -> execute tools
  -> repeat
```

## Agent Changes — `browser-agent/src/agent.ts`

Add a `checkControl()` function and call it at the top of the `for` loop (line 118):

```typescript
function checkControl(traceDir: string): { action: string; message?: string } | null {
  const controlPath = resolve(traceDir, "control.json");
  if (!existsSync(controlPath)) return null;
  try {
    const data = JSON.parse(readFileSync(controlPath, "utf-8"));
    unlinkSync(controlPath);
    return data;
  } catch { return null; }
}
```

In the loop body (inside `for (let turn = 0; ...)`), before the Gemini call:
```typescript
const control = checkControl(traceDir);
if (control?.action === "stop") {
  trace.logResult(false, "Stopped by user");
  return { success: false, summary: "Stopped by user", traceFile: trace.getFilePath(), turns: trace.getTurnCount() };
}
if (control?.action === "inject") {
  const msg = control.message ?? "";
  history.push({ role: "user", parts: [{ text: msg }] });
  trace.logTurn("user", msg);
  console.log(`\n[Injected] ${msg}`);
}
```

## server.py — FastAPI + WebSocket

**Dependencies:** `fastapi`, `uvicorn`, `watchfiles` (for efficient file tailing)

**WebSocket endpoint `GET /ws`:**
- On connect: send all existing lines from the current JSONL file
- Tail the JSONL file (watch for appends) and push new lines as they arrive
- Accept incoming messages from client:
  - `{"action": "stop"}` -> write `{"action": "stop"}` to `{traceDir}/control.json`
  - `{"action": "inject", "message": "..."}` -> write to `control.json`

**REST endpoints (for browsing historical traces):**
- `GET /` -> serve `index.html`
- `GET /api/runs` -> list run directories
- `GET /api/traces/<run>` -> list trace files with metadata (task name, success status) by reading first+last lines of each JSONL
- `GET /api/trace/<run>/<file>` -> full JSONL parsed as JSON array

**Config:** Accept traces directory as CLI arg, default to `../gemini-hackathon/traces`. Serve on port 8000.

**File tailing approach:**
- Use `watchfiles` to detect file changes (uses OS-level fs events, not polling)
- Track byte offset per client; on change, read new bytes from offset, split into lines, push via WebSocket
- Fallback: if `watchfiles` is too heavy, use a simple 500ms `asyncio.sleep` poll loop checking file size

## index.html — Single-file SPA

**Dependencies (CDN only):** Tailwind CSS, Google Fonts (JetBrains Mono, Inter)

**Layout:** Single-column SPA with breadcrumb navigation between 3 views:

### 1. Runs view
Cards for each run directory.

### 2. Traces view
List of traces in a run, each showing task name + status dot (green/red/yellow).
Poll `/api/traces/<run>` every 5s to detect new trace files.

### 3. Detail view (live)
- Connect to `ws://<host>/ws?run=<run>&file=<file>`
- Render each JSONL line as it arrives into a hierarchical tree:
  - `start` event -> root header (task name, timestamp)
  - `turn` with `role:"model"` + subsequent `tool_result`(s) -> collapsible node showing tool name + command, with nested result (exit code, truncated stdout)
  - `turn` with `role:"user"` -> user message line (injected messages highlighted differently)
  - Model `content` (when non-empty) -> "thinking" text in blue
  - `result` event -> summary footer with success/fail status
- Auto-scroll to bottom on new events (with toggle to disable)
- Stop rendering new events when trace has a `result` event

**Control bar (sticky bottom):**
- Text input + "Send" button -> sends `{"action": "inject", "message": "..."}` via WebSocket
- "Stop" button (red) -> sends `{"action": "stop"}` via WebSocket
- Both disabled when trace is complete (has `result` event)

**Visual patterns (from SICA reference UI):**
- Status dots: green (success/exit 0), red (failed/nonzero exit), yellow (pending), blue pulsing (running)
- Vertical tree lines via `::before` pseudo-element
- Color-coded events: blue=model, purple=tool, gray=system, green=injected user message
- JetBrains Mono for log content, Inter for UI chrome
- Cards with shadows, `bg-gray-50` backgrounds
- Click to expand/collapse nodes; long stdout truncated with "Show more"

**ANSI stripping:** `str.replace(/\x1b\[[0-9;]*m/g, '')` on stdout fields.

## Implementation Sequence

1. Modify `browser-agent/src/agent.ts` — add control file check (~10 lines)
2. Create `gh-2/server.py` — FastAPI server with WebSocket + REST endpoints
3. Create `gh-2/index.html` — SPA with all three views, tree rendering, and control bar
4. Test end-to-end

## Verification

1. Start agent: `cd /Users/ob1/projects/hackathons/gemini-hackathon && npx tsx browser-agent/src/index.ts --task "test task"`
2. Start server: `cd /Users/ob1/projects/hackathons/gh-2 && python3 server.py`
3. Open `http://localhost:8000` — should see run cards
4. Click a run -> see trace list with status dots
5. Click an active trace -> see events appearing live via WebSocket
6. Type a message and click Send -> verify it appears in the trace as a user turn, agent responds to it
7. Click Stop -> verify agent exits gracefully with "Stopped by user" result
8. Verify ANSI codes are stripped from tool output
9. Verify completed traces show disabled controls
