import { Type, type FunctionDeclaration } from "@google/genai";

export const toolDeclarations: FunctionDeclaration[] = [
  {
    name: "browser_command",
    description:
      "Execute an agent-browser CLI command. Pass the full command string (everything after 'agent-browser'). " +
      "Examples: 'open https://example.com', 'snapshot -i', 'click @e1', 'fill @e2 \"text\"'. " +
      "Commands can be chained with && for efficiency.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        command: {
          type: Type.STRING,
          description: "The agent-browser command to execute (without the 'agent-browser' prefix)",
        },
      },
      required: ["command"],
    },
  },
  {
    name: "done",
    description: "Signal that the task is complete. Call this when you have finished the task or determined it cannot be completed.",
    parameters: {
      type: Type.OBJECT,
      properties: {
        success: {
          type: Type.BOOLEAN,
          description: "Whether the task was completed successfully",
        },
        summary: {
          type: Type.STRING,
          description: "A summary of what was accomplished or what went wrong",
        },
      },
      required: ["success", "summary"],
    },
  },
];
