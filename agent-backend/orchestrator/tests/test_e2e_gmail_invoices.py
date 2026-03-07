"""E2E regression test: launch Brave, run orchestrator against Gmail, verify invoice downloads."""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

# pytest tests/test_e2e_gmail_invoices.py -v -s
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BRAVE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
CDP_PORT = 9222
BRAVE_USER_DATA_DIR = "/tmp/brave-debug"

TASK_PROMPT = (
    "Go to gmail and download the latest invoice from each of these companies: "
    "X, Warp, Cognition. Save them all to ~/Downloads/march-claims/"
)

OUTPUT_DIR = Path.home() / "Downloads" / "march-claims"
EXPECTED_FILES = ["X-invoice.pdf", "Warp-invoice.pdf", "Cognition-invoice.pdf"]

ORCHESTRATOR_TIMEOUT = 600  # seconds – passed to the orchestrator CLI
TEST_TIMEOUT = 720  # seconds – pytest-level safety net

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port: int, timeout: int = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(port):
            return
        time.sleep(0.5)
    raise TimeoutError(f"Port {port} did not open within {timeout}s")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def brave_browser():
    """Launch Brave with remote debugging enabled; tear down after session."""
    proc = subprocess.Popen(
        [
            BRAVE_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={BRAVE_USER_DATA_DIR}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_port(CDP_PORT)
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture()
def clean_output_dir():
    """Remove output directory before test; leave it after for inspection."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.timeout(TEST_TIMEOUT)
def test_download_gmail_invoices(brave_browser, clean_output_dir):
    """Run the orchestrator and verify all expected invoices are downloaded."""
    project_root = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [
            "python", "-m", "orchestrator",
            TASK_PROMPT,
            "--max-improvements", "0",
            "--timeout", str(ORCHESTRATOR_TIMEOUT),
        ],
        capture_output=True,
        text=True,
        timeout=ORCHESTRATOR_TIMEOUT + 60,
        cwd=str(project_root),
    )

    # Print output for debugging (last 80 lines)
    stdout_lines = (result.stdout or "").splitlines()
    stderr_lines = (result.stderr or "").splitlines()
    print("\n--- STDOUT (last 80 lines) ---")
    print("\n".join(stdout_lines[-80:]))
    print("\n--- STDERR (last 80 lines) ---")
    print("\n".join(stderr_lines[-80:]))

    # Do NOT assert on exit code — cli.py unconditionally calls sys.exit(1)

    # Verify each expected file exists and is non-empty
    for filename in EXPECTED_FILES:
        filepath = OUTPUT_DIR / filename
        assert filepath.exists(), f"Missing expected file: {filepath}"
        assert filepath.stat().st_size > 0, f"File is empty: {filepath}"
