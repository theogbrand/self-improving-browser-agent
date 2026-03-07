import { GoogleGenAI, HarmBlockThreshold, HarmCategory, type Content, type Part, type SafetySetting } from "@google/genai";
import { execSync } from "child_process";
import { readFileSync } from "fs";
import { resolve } from "path";
import { toolDeclarations } from "./tools.js";
import { TraceLogger } from "./trace.js";

interface AgentConfig {
  model: string;
  maxTurns: number;
  autoConnect: boolean;
  cdpPort: number | null;
  headed: boolean;
  sessionName: string;
  downloadDir: string;
}

interface AgentResult {
  success: boolean;
  summary: string;
  traceFile: string;
  turns: number;
}

// Safety settings: disable all content filtering (matches SICA's GoogleProvider pattern)
const SAFETY_SETTINGS: SafetySetting[] = [
  HarmCategory.HARM_CATEGORY_HARASSMENT,
  HarmCategory.HARM_CATEGORY_HATE_SPEECH,
  HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
  HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
].map((category) => ({ category, threshold: HarmBlockThreshold.OFF }));

const MAX_API_RETRIES = 5;

async function callWithRetry(
  fn: () => Promise<any>,
  retries = MAX_API_RETRIES,
): Promise<any> {
  let lastError: unknown;
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
      console.error(`[Retry] API error (attempt ${attempt + 1}/${retries}): ${err}`);
      if (attempt < retries - 1) {
        await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

function buildBrowserPrefix(config: AgentConfig): string {
  const parts = ["npx", "agent-browser"];
  if (config.autoConnect) parts.push("--auto-connect");
  if (config.cdpPort) parts.push("--cdp", String(config.cdpPort));
  if (config.headed) parts.push("--headed");
  if (config.sessionName) parts.push("--session", config.sessionName);
  return parts.join(" ");
}

function execBrowserCommand(command: string, config: AgentConfig, cwd: string): { stdout: string; exitCode: number } {
  // The command may contain chained commands with &&
  // We need to prefix each agent-browser sub-command properly
  const prefix = buildBrowserPrefix(config);

  // Replace bare "agent-browser" in the command with the full prefix
  // The model sends commands like "open https://..." or "snapshot -i"
  // or chained: "open https://... && agent-browser snapshot -i"
  let fullCommand: string;
  if (command.includes("agent-browser")) {
    // Model included agent-browser in the command, replace all occurrences with prefix
    fullCommand = command.replace(/agent-browser/g, prefix);
  } else {
    // Simple command, just prefix it
    fullCommand = `${prefix} ${command}`;
  }

  try {
    const stdout = execSync(fullCommand, {
      cwd,
      encoding: "utf-8",
      timeout: 60_000,
      maxBuffer: 10 * 1024 * 1024,
      env: {
        ...process.env,
        AGENT_BROWSER_CONTENT_BOUNDARIES: "1",
        ...(config.downloadDir ? { AGENT_BROWSER_DOWNLOAD_PATH: config.downloadDir } : {}),
      },
    });
    return { stdout: stdout || "(no output)", exitCode: 0 };
  } catch (err: any) {
    const stdout = (err.stdout || "") + (err.stderr || "");
    return { stdout: stdout || err.message, exitCode: err.status ?? 1 };
  }
}

export async function runAgent(
  task: string,
  configPath: string,
  promptPath: string,
  traceDir: string,
  projectRoot: string,
): Promise<AgentResult> {
  const config: AgentConfig = JSON.parse(readFileSync(resolve(configPath), "utf-8"));
  const systemPrompt = readFileSync(resolve(promptPath), "utf-8");

  const client = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });
  const trace = new TraceLogger(traceDir, task);

  const history: Content[] = [];

  // Initial user message
  history.push({ role: "user", parts: [{ text: `Task: ${task}` }] });
  trace.logTurn("user", `Task: ${task}`);

  for (let turn = 0; turn < config.maxTurns; turn++) {
    const response = await callWithRetry(() =>
      client.models.generateContent({
        model: config.model,
        contents: history,
        config: {
          systemInstruction: systemPrompt,
          tools: [{ functionDeclarations: toolDeclarations }],
          temperature: 1.0,
          safetySettings: SAFETY_SETTINGS,
        },
      }),
    );

    const candidate = response.candidates?.[0];
    if (!candidate?.content?.parts) {
      const finishReason = candidate?.finishReason ?? "unknown";
      console.error(`[Agent] Empty response, finishReason=${finishReason}`);
      if (finishReason === "SAFETY") {
        // Safety block — log and continue, don't abort immediately
        history.push({ role: "model", parts: [{ text: "(response blocked by safety filter)" }] });
        history.push({ role: "user", parts: [{ text: "Your previous response was blocked. Please try a different approach." }] });
        continue;
      }
      trace.logResult(false, `Empty response from model (finishReason=${finishReason})`);
      return { success: false, summary: `Empty response from model (finishReason=${finishReason})`, traceFile: trace.getFilePath(), turns: trace.getTurnCount() };
    }

    const parts: Part[] = candidate.content.parts;
    const textParts = parts.filter((p: Part) => p.text).map((p: Part) => p.text!);
    const functionCalls = parts.filter((p: Part) => p.functionCall);

    // Log model response
    const modelText = textParts.join("\n");
    trace.logTurn(
      "model",
      modelText,
      functionCalls.map((fc: Part) => ({ name: fc.functionCall!.name, args: fc.functionCall!.args })),
    );

    // Add model response to history
    history.push({ role: "model", parts });

    if (modelText) {
      console.log(`\n[Agent] ${modelText}`);
    }

    // Process function calls
    if (functionCalls.length > 0) {
      const responseParts: Part[] = [];

      for (const fc of functionCalls) {
        const { name, args } = fc.functionCall!;

        if (name === "done") {
          const success = (args as any).success as boolean;
          const summary = (args as any).summary as string;
          trace.logResult(success, summary);
          console.log(`\n[Done] success=${success}: ${summary}`);
          return { success, summary, traceFile: trace.getFilePath(), turns: trace.getTurnCount() };
        }

        if (name === "browser_command") {
          const command = (args as any).command as string;
          console.log(`\n[Command] agent-browser ${command}`);
          const { stdout, exitCode } = execBrowserCommand(command, config, projectRoot);
          trace.logToolResult("browser_command", args as Record<string, unknown>, stdout, exitCode);

          const truncatedOutput = stdout.length > 8000 ? stdout.slice(0, 8000) + "\n...(truncated)" : stdout;
          console.log(`[Result] exit=${exitCode}, ${stdout.length} chars`);

          responseParts.push({
            functionResponse: {
              name: "browser_command",
              response: { exitCode, output: truncatedOutput },
            },
          });
        }
      }

      if (responseParts.length > 0) {
        history.push({ role: "user", parts: responseParts });
      }
    }
  }

  const summary = `Max turns (${config.maxTurns}) exceeded`;
  trace.logResult(false, summary);
  return { success: false, summary, traceFile: trace.getFilePath(), turns: trace.getTurnCount() };
}
