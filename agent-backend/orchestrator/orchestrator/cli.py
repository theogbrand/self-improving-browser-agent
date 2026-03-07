import argparse
import json
import sys
import time
from pathlib import Path

from .runner import run_browser_agent
from .improver import improve


def wait_for_web_feedback(trace_file):
    """Append a feedback_request event and poll control.json for a response."""
    trace_path = Path(trace_file)
    trace_dir = trace_path.parent
    control_path = trace_dir / "control.json"

    # Append feedback_request event to the trace
    with open(trace_path, "a") as f:
        f.write(json.dumps({"type": "feedback_request"}) + "\n")

    # Remove stale control.json
    control_path.unlink(missing_ok=True)

    print("Waiting for feedback from web UI...")
    while True:
        time.sleep(1)
        if control_path.exists():
            try:
                data = json.loads(control_path.read_text())
                control_path.unlink(missing_ok=True)
                return data
            except (json.JSONDecodeError, OSError):
                continue


def main():
    parser = argparse.ArgumentParser(description="Self-improving browser automation agent")
    parser.add_argument("task", help="The browser task to accomplish")
    parser.add_argument("--config-dir", default="agent-config", help="Path to agent config directory")
    parser.add_argument("--max-improvements", type=int, default=2, help="Max improvement iterations")
    parser.add_argument("--timeout", type=int, default=600, help="Agent timeout in seconds")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    config_dir = project_root / args.config_dir
    config_path = str(config_dir / "config.json")
    prompt_path = str(config_dir / "system_prompt.md")

    for iteration in range(1 + args.max_improvements):
        run_num = iteration + 1
        trace_dir = str(project_root / "traces" / f"run_{run_num}")

        print(f"\n{'#'*60}")
        print(f"# Attempt {run_num}")
        print(f"{'#'*60}")

        result = run_browser_agent(
            task=args.task,
            config_path=config_path,
            prompt_path=prompt_path,
            trace_dir=trace_dir,
            project_root=project_root,
            timeout=args.timeout,
        )

        print(f"\n{'='*60}")
        print(f"Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Summary: {result['summary']}")
        print(f"Trace: {result.get('traceFile', 'N/A')}")
        print(f"{'='*60}")

        if result["success"]:
            print("\nAgent thinks task was completed successfully, pls verify!")

        # Ask for feedback
        if iteration >= args.max_improvements:
            print(f"\nMax improvement iterations ({args.max_improvements}) reached.")
            break

        trace_file = result.get("traceFile")
        if trace_file and Path(trace_file).exists():
            feedback = wait_for_web_feedback(trace_file)
            action = feedback.get("action", "")
            if action in ("quit", "accept"):
                print(f"User chose: {action}. Exiting.")
                break
            user_input = feedback.get("message", "").strip()
            if not user_input:
                print("No feedback provided. Exiting.")
                break
        else:
            print("\nWould you like to improve and retry? (y/n)")
            user_input = input("Feedback (or 'q' to quit): ").strip()
            if user_input.lower() in ("q", "quit", "exit", "n", "no"):
                print("Exiting.")
                break

        # Run improvement
        improvement = improve(
            task=args.task,
            trace_file=result.get("traceFile", ""),
            user_feedback=user_input,
            config_dir=str(config_dir),
        )

        if not improvement["config_changed"] and not improvement["prompt_changed"]:
            print("\nNo improvements were suggested. Exiting.")
            break

        print("\nRetrying with improved configuration...")

    sys.exit(1)


if __name__ == "__main__":
    main()
