#!/usr/bin/env python3
"""Trace viewer server: FastAPI + WebSocket for live trace tailing."""

import asyncio
import json
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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


@app.websocket("/ws")
async def ws_tail(ws: WebSocket):
    await ws.accept()
    run = ws.query_params.get("run", "")
    file = ws.query_params.get("file", "")
    path = TRACES_DIR / run / file
    if not path.is_file():
        await ws.close(1008, "File not found")
        return

    # Send existing lines
    offset = 0
    with open(path, "rb") as f:
        data = f.read()
        offset = len(data)
    for line in data.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            await ws.send_text(line)

    # Tail loop
    async def tail():
        nonlocal offset
        while True:
            await asyncio.sleep(0.5)
            try:
                size = path.stat().st_size
            except FileNotFoundError:
                break
            if size > offset:
                with open(path, "rb") as f:
                    f.seek(offset)
                    new = f.read()
                    offset += len(new)
                for line in new.decode("utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line:
                        await ws.send_text(line)

    async def receive():
        while True:
            msg = await ws.receive_text()
            try:
                data = json.loads(msg)
                control_path = TRACES_DIR / run / "control.json"
                control_path.write_text(json.dumps(data))
            except Exception:
                pass

    try:
        await asyncio.gather(tail(), receive())
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
