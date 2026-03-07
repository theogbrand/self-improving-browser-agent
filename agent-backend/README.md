# Self-Improving Browser Agent

A browser automation system that combines Vercel's Agent Browser with a self-improving loop. The agent attempts a task, and if it fails, an improver analyzes the execution trace + your feedback to rewrite the agent's config and system prompt, then retries.

## Architecture

```
                          YOU (terminal)
                           |
                           | "Go to Gmail and download invoices"
                           v
                   ┌──────────────┐
                   |   cli.py     |  Python orchestrator
                   |  (the loop)  |  Runs up to 3 attempts (1 + 2 improvements)
                   └──────┬───────┘
                          |
             ┌────────────┼─────────────────┐
             |            |                 |
             v            v                 v
        Attempt 1    Attempt 2          Attempt 3
             |        (after improve)   (after improve)
             |
             v
    ┌─────────────────┐
    |   runner.py     |  Launches TS agent as subprocess
    |  (subprocess)   |  Streams output, parses JSON result
    └────────┬────────┘
             |
             v
    ┌─────────────────┐        ┌─────────────────┐
    |   agent.ts      | -----> |  agent-browser   |  CLI that talks to
    |  (Gemini loop)  | <----- |  (via execSync)  |  Chrome over CDP
    └────────┬────────┘        └─────────────────┘
             |
             | writes every turn
             v
    ┌─────────────────┐
    |  traces/*.jsonl |  The "black box recorder"
    └─────────────────┘

    On failure:
    ┌─────────────────┐
    | YOU type feedback| ---> improver.py ---> rewrites config.json
    |  "it couldn't   |                       & system_prompt.md
    |   find the btn" |                       in agent-config/
    └─────────────────┘
```

## Setup

```bash
# Install agent-browser
cd agent-browser && npm install

# Install browser agent
cd browser-agent && npm install

# Install orchestrator
cd orchestrator && uv venv && source .venv/bin/activate && uv pip install -e .

# Set API key
export GEMINI_API_KEY=your-key
```

## Usage

```bash
# Start Brave with remote debugging (supports Gmail auth, unlike Chrome DevTools)
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222

# Run via orchestrator (recommended)
cd orchestrator && source .venv/bin/activate
python -m orchestrator "Go to HackerNews and find the most relevant top related news for AI researchers and startup founders"

# Run the TS agent directly
cd browser-agent && npx tsx src/index.ts --task "Go to HackerNews and find the most relevant top related news for AI researchers and startup founders"
```

## Key Paths

| What | Path |
|------|------|
| Agent config (editable surface) | `agent-config/config.json` |
| System prompt (editable surface) | `agent-config/system_prompt.md` |
| Config history (rollback) | `agent-config/history/` |
| Execution traces | `traces/` |
| Browser agent (Gemini loop) | `browser-agent/src/agent.ts` |
| Orchestrator entry point | `orchestrator/orchestrator/cli.py` |
| Self-improvement engine | `orchestrator/orchestrator/improver.py` |
