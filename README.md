# Self Improving Browser Agent

A browser agent that improves itself through human feedback. When the agent goes wrong, you can intervene with realtime feedback, and a meta-agent rewrites the agent's system prompt and config to improve it for the next run. This loop of execution, feedback, and self-revision helps the agent get better at more tasks over time, and also allows users to get better at collaboration with the agent.

## Architecture

```
You (CLI) ──> Orchestrator (Python) ──> Browser Agent (TS + Gemini) ──> Chrome via CDP
                  │                              │
                  │ when the agent goes wrong:                  └──> traces/*.jsonl
                  │ human feedback
                  v
             Improver ──> rewrites system_prompt.md & config.json
```

The orchestrator runs up to 3 attempts (1 initial + 2 improvements) currently but this can be configured with CLI arguments. Each improvement cycle incorporates your feedback to rewrite the agent's configuration before retrying.

## Setup

```bash
git clone --recurse-submodules https://github.com/theogbrand/self-improving-browser-agent && cd self-improving-browser-agent

# agent-browser (submodule)
cd agent-backend/agent-browser && pnpm install && agent-browser install

# orchestrator
cd ../orchestrator && uv venv .venv && source .venv/bin/activate && uv pip install -e .

# API keys
export GEMINI_API_KEY="your-key"
```

## Usage

```bash
# Terminal 1: Launch browser with CDP
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222

# Terminal 2: Trace viewer
source .venv/bin/activate && python server.py   # http://localhost:8000

# Terminal 3: Run a task
cd agent-backend/orchestrator && source .venv/bin/activate
python -m orchestrator "Go to Gmail and download this month's receipts (March 2026) for Screenplay Studios (Graphite), Warp.dev, Cognition Labs (Devin)" 
```

## Key Paths

| Path | Purpose |
|------|---------|
| `agent-backend/agent-config/system_prompt.md` | System prompt (editable surface) |
| `agent-backend/agent-config/config.json` | Runtime config (editable surface) |
| `agent-backend/browser-agent/src/index.ts` | TS agent entry point |
| `agent-backend/orchestrator/orchestrator/cli.py` | Orchestrator entry point |
| `agent-backend/orchestrator/orchestrator/improver.py` | Self-improvement engine |
| `agent-backend/traces/` | Execution traces |
| `server.py` / `index.html` | Trace viewer |
