#!/usr/bin/env python3
"""Trace viewer server: FastAPI + REST polling for live trace viewing."""

import json
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

TRACES_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "agent-backend" / "traces"
TRACES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/api/runs")
async def list_runs():
    runs = sorted(
        [d.name for d in TRACES_DIR.iterdir() if d.is_dir()],
        key=lambda n: n, reverse=True,
    )
    return runs


@app.get("/api/traces/{run}")
async def list_traces(run: str):
    run_dir = TRACES_DIR / run
    if not run_dir.is_dir():
        return JSONResponse([], status_code=404)
    traces = []
    for f in sorted(run_dir.glob("*.jsonl"), reverse=True):
        first = last = None
        try:
            with open(f) as fh:
                lines = fh.readlines()
                if lines:
                    first = json.loads(lines[0])
                    last = json.loads(lines[-1])
        except Exception:
            pass
        task = first.get("task", f.stem) if first else f.stem
        status = "pending"
        if last and last.get("type") == "result":
            status = "success" if last.get("success") else "failed"
        traces.append({"file": f.name, "task": task, "status": status, "timestamp": first.get("timestamp", "") if first else ""})
    return traces


@app.get("/api/trace/{run}/{file}")
async def get_trace(run: str, file: str):
    path = TRACES_DIR / run / file
    if not path.is_file():
        return JSONResponse([], status_code=404)
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


@app.post("/api/control/{run}")
async def post_control(run: str, request: Request):
    data = await request.json()
    control_path = TRACES_DIR / run / "control.json"
    control_path.write_text(json.dumps(data))
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
