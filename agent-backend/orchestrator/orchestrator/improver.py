import json
import shutil
from datetime import datetime
from pathlib import Path

from google import genai


def _read_trace(trace_file: str) -> str:
    """Read and return the JSONL trace file contents."""
    path = Path(trace_file)
    if not path.exists():
        return "(no trace file found)"
    return path.read_text()


def _generate_contextual_summary(
    client: genai.Client,
    task: str,
    trace: str,
    user_feedback: str,
) -> str:
    """Generate a critical analysis of the agent's execution trace."""
    prompt = f"""Below is a trace of a browser automation agent's execution.

Task: {task}

User Feedback: {user_feedback}

Execution Trace:
{trace}

Write a critical analysis of the agent's performance:
- Did the agent follow a logical approach?
- Were there unnecessary steps or inefficiencies?
- Where did the agent's approach fail?
- What specific improvements to the agent's system prompt or configuration could fix this?

Keep your analysis concise (1-2 paragraphs)."""

    response = client.models.generate_content(
        # model="gemini-3.1-flash-lite-preview",
        model="gemini-3.1-pro-preview",
        contents=prompt,
        config={"system_instruction": "You are a critical evaluator of AI browser agent performance."},
    )
    return response.text or "(no summary generated)"


def _save_history(config_dir: Path) -> str:
    """Save current config and prompt to history/ with timestamp."""
    history_dir = config_dir / "history"
    history_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_dir = history_dir / timestamp
    version_dir.mkdir()

    shutil.copy(config_dir / "config.json", version_dir / "config.json")
    shutil.copy(config_dir / "system_prompt.md", version_dir / "system_prompt.md")

    return str(version_dir)


def improve(
    task: str,
    trace_file: str,
    user_feedback: str,
    config_dir: str,
) -> dict:
    """Analyze the failed run and improve the agent's config/prompt.

    Returns a dict with keys: analysis, config_changed, prompt_changed, history_path
    """
    config_path = Path(config_dir)
    current_config = json.loads((config_path / "config.json").read_text())
    current_prompt = (config_path / "system_prompt.md").read_text()
    trace = _read_trace(trace_file)

    client = genai.Client()

    # Step 1: Generate contextual summary
    print("\nAnalyzing execution trace...")
    summary = _generate_contextual_summary(client, task, trace, user_feedback)
    print(f"\nAnalysis:\n{summary}")

    # Step 2: Ask Gemini for improvements
    print("\nGenerating improvements...")
    improvement_prompt = f"""You are improving a browser automation agent that failed a task.

## Current System Prompt
{current_prompt}

## Current Config
{json.dumps(current_config, indent=2)}

## Task That Failed
{task}

## User Feedback
{user_feedback}

## Execution Analysis
{summary}

## Instructions
Based on the analysis, suggest improvements. Respond with valid JSON only:

{{
  "analysis": "Brief explanation of what to change and why",
  "config_changes": {{}} or null,
  "new_system_prompt": "full new system prompt text" or null
}}

Rules:
- `config_changes` is a partial JSON object that will be merged into the current config. Only include fields that need changing. Set to null if no config changes needed.
- `new_system_prompt` is the complete replacement system prompt. Only provide if the prompt needs changes. Set to null if no prompt changes needed.
- Focus on actionable, specific improvements. Don't make changes for the sake of it.
- Common improvements: adding specific instructions for the failed scenario, adjusting maxTurns, adding wait strategies, improving navigation patterns."""

    response = client.models.generate_content(
        # model="gemini-3.1-flash-lite-preview",
        model="gemini-3.1-pro-preview",
        contents=improvement_prompt,
        config={
            "system_instruction": "You are an expert at improving AI agent configurations. Respond with valid JSON only, no markdown fences.",
            "temperature": 0.7,
        },
    )

    raw_text = (response.text or "{}").strip()
    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3].strip()

    try:
        improvements = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse improvement response, skipping.")
        return {"analysis": "Failed to parse improvements", "config_changed": False, "prompt_changed": False, "history_path": ""}

    # Step 3: Save history
    history_path = _save_history(config_path)
    print(f"Saved previous version to {history_path}")

    # Step 4: Apply changes
    config_changed = False
    prompt_changed = False

    if improvements.get("config_changes"):
        current_config.update(improvements["config_changes"])
        (config_path / "config.json").write_text(json.dumps(current_config, indent=2) + "\n")
        config_changed = True
        print(f"Updated config: {json.dumps(improvements['config_changes'])}")

    if improvements.get("new_system_prompt"):
        (config_path / "system_prompt.md").write_text(improvements["new_system_prompt"])
        prompt_changed = True
        print("Updated system prompt")

    analysis = improvements.get("analysis", "No analysis provided")
    print(f"\nImprovement analysis: {analysis}")

    return {
        "analysis": analysis,
        "config_changed": config_changed,
        "prompt_changed": prompt_changed,
        "history_path": history_path,
    }
