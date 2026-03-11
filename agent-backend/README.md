# Continual Learning Browser Agent

If machines are exceeding human intelligence, why are humans still the ones improving them? We propose a shift: machines should improve *themselves*, so that humans are no longer the bottleneck on machine capability.

This project is a proof-of-concept **continual learning interface**. A Browser Agent receives human feedback and rewrites its own system, updating prompts, creating scripts, refining its orchestration via a meta-agent that modifies the very agent it governs. No retraining, but a loop of execution, feedback, and self-revision.

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


Improvements:
- Run-2 doesn't allow feedback currently
- For Inbox, can we make a complete clone before searching across all emails and downloading? safer and less likely to make mistakes
- Side by side view will be better UIUX, chat on left, browser working on right, while still allowing for easy intervention by human
- when bash commands fail, we should fix them with re-run before executing them to save tokens