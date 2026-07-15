import * as vscode from "vscode";
import { randomUUID } from "crypto";

export interface ParsedToolCall {
  callId: string;
  name: string;
  input: object;
}

const TOOL_CALL_RE = /<tool_call>\s*([\s\S]*?)\s*<\/tool_call>/gi;

export function contentPartToText(part: unknown): string {
  if (part instanceof vscode.LanguageModelTextPart) {
    return part.value;
  }
  if (part instanceof vscode.LanguageModelToolCallPart) {
    return [
      "<tool_call>",
      JSON.stringify({ name: part.name, arguments: part.input, call_id: part.callId }),
      "</tool_call>",
    ].join("\n");
  }
  if (part instanceof vscode.LanguageModelToolResultPart) {
    const body = part.content
      .map((item) => {
        if (item instanceof vscode.LanguageModelTextPart) {
          return item.value;
        }
        return typeof item === "string" ? item : JSON.stringify(item);
      })
      .join("\n");
    return `<tool_result call_id="${part.callId}">\n${body}\n</tool_result>`;
  }
  return "";
}

export function formatToolsPrompt(
  tools: readonly vscode.LanguageModelChatTool[],
  toolMode: vscode.LanguageModelChatToolMode,
): string {
  const lines = [
    "You can call tools by emitting one or more of these blocks:",
    "",
    "<tool_call>",
    '{"name": "TOOL_NAME", "arguments": {"param": "value"}}',
    "</tool_call>",
    "",
    "Rules:",
    "- Use only the tools listed below.",
    "- Put valid JSON inside each <tool_call> block.",
    "- If you need a tool, emit the tool call(s) and stop. Do not invent tool results.",
    "- After tool results are provided, continue with a normal answer or more tool calls.",
    "",
    "Available tools:",
  ];

  for (const tool of tools) {
    lines.push(`- ${tool.name}: ${tool.description}`);
    if (tool.inputSchema) {
      lines.push(`  Input schema: ${JSON.stringify(tool.inputSchema)}`);
    }
  }

  if (toolMode === vscode.LanguageModelChatToolMode.Required) {
    lines.push(
      "",
      "You MUST call at least one tool using a <tool_call> block. Do not answer with plain text only.",
    );
  }

  return lines.join("\n");
}

export function parseToolCalls(text: string): {
  text: string;
  toolCalls: ParsedToolCall[];
} {
  const toolCalls: ParsedToolCall[] = [];
  let cleaned = text;

  for (const match of text.matchAll(TOOL_CALL_RE)) {
    const raw = (match[1] ?? "").trim();
    if (!raw) {
      continue;
    }
    try {
      const parsed = JSON.parse(raw) as {
        name?: string;
        arguments?: unknown;
        input?: unknown;
        call_id?: string;
        callId?: string;
      };
      if (!parsed.name || typeof parsed.name !== "string") {
        continue;
      }
      const inputRaw = parsed.arguments ?? parsed.input ?? {};
      const input =
        inputRaw && typeof inputRaw === "object" && !Array.isArray(inputRaw)
          ? (inputRaw as object)
          : { value: inputRaw };
      toolCalls.push({
        callId:
          (typeof parsed.call_id === "string" && parsed.call_id) ||
          (typeof parsed.callId === "string" && parsed.callId) ||
          randomUUID(),
        name: parsed.name,
        input,
      });
    } catch {
      // Ignore malformed tool blocks; keep surrounding text.
    }
  }

  if (toolCalls.length > 0) {
    cleaned = text.replace(TOOL_CALL_RE, "").trim();
  }

  return { text: cleaned, toolCalls };
}
