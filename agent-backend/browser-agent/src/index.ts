import { parseArgs } from "util";
import { resolve } from "path";
import { runAgent } from "./agent.js";

const { values } = parseArgs({
  options: {
    task: { type: "string" },
    config: { type: "string", default: "../agent-config/config.json" },
    prompt: { type: "string", default: "../agent-config/system_prompt.md" },
    "trace-dir": { type: "string", default: "../traces" },
  },
  strict: true,
});

if (!values.task) {
  console.error("Usage: tsx src/index.ts --task <task description>");
  process.exit(2);
}

const projectRoot = resolve(import.meta.dirname, "../..");

const result = await runAgent(
  values.task,
  resolve(values.config!),
  resolve(values.prompt!),
  resolve(values["trace-dir"]!),
  projectRoot,
);

// Output result as JSON for orchestrator to parse
console.log("\n---RESULT_JSON---");
console.log(JSON.stringify(result));

process.exit(result.success ? 0 : 1);
