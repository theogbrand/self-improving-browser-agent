import json
import subprocess
import sys
from pathlib import Path


def run_browser_agent(
    task: str,
    config_path: str,
    prompt_path: str,
    trace_dir: str,
    project_root: Path,
    timeout: int = 600,
) -> dict:
    """Launch the TypeScript browser agent as a subprocess and return its result."""
    cmd = [
        "npx", "tsx", "browser-agent/src/index.ts",
        "--task", task,
        "--config", config_path,
        "--prompt", prompt_path,
        "--trace-dir", trace_dir,
    ]

    print(f"\n{'='*60}")
    print(f"Running browser agent...")
    print(f"Task: {task}")
    print(f"{'='*60}\n")

    collected_output: list[str] = []

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in proc.stdout:  # type: ignore
            sys.stdout.write(line)
            sys.stdout.flush()
            collected_output.append(line)

        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {
            "success": False,
            "summary": f"Agent timed out after {timeout}s",
            "traceFile": "",
            "turns": 0,
        }

    stdout = "".join(collected_output)

    # Parse the JSON result marker from output
    if "---RESULT_JSON---" in stdout:
        try:
            json_str = stdout.split("---RESULT_JSON---")[1].strip().split("\n")[0]
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            pass

    return {
        "success": proc.returncode == 0,
        "summary": "Agent completed" if proc.returncode == 0 else "Agent failed",
        "traceFile": "",
        "turns": 0,
    }
