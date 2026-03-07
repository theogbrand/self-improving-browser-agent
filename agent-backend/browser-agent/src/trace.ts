import { writeFileSync, mkdirSync, existsSync, appendFileSync } from "fs";
import { join } from "path";

export class TraceLogger {
  private filePath: string;
  private turnCount = 0;

  constructor(traceDir: string, taskName: string) {
    mkdirSync(traceDir, { recursive: true });
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    this.filePath = join(traceDir, `trace_${timestamp}.jsonl`);
    this.log({ type: "start", task: taskName, timestamp: new Date().toISOString() });
  }

  private log(entry: Record<string, unknown>) {
    appendFileSync(this.filePath, JSON.stringify(entry) + "\n");
  }

  logTurn(role: "model" | "user", content: string, functionCalls?: unknown[]) {
    this.turnCount++;
    this.log({
      type: "turn",
      turn: this.turnCount,
      role,
      content,
      ...(functionCalls ? { functionCalls } : {}),
    });
  }

  logToolResult(tool: string, args: Record<string, unknown>, stdout: string, exitCode: number) {
    this.log({ type: "tool_result", tool, args, stdout: stdout.slice(0, 5000), exitCode });
  }

  logResult(success: boolean, summary: string) {
    this.log({ type: "result", success, summary, totalTurns: this.turnCount });
  }

  getFilePath() {
    return this.filePath;
  }

  getTurnCount() {
    return this.turnCount;
  }
}
