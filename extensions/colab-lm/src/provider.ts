import * as vscode from "vscode";
import { BridgeClient, type BridgeMessage } from "./bridgeClient";
import {
  contentPartToText,
  formatToolsPrompt,
  parseToolCalls,
} from "./tools";

const DEFAULT_MAX_INPUT = 1_000_000;
const DEFAULT_MAX_OUTPUT = 8192;

const FALLBACK_MODELS = [
  { id: "gemini-3.6-flash", name: "Gemini 3.6 Flash" },
  { id: "gemini-3.1-pro", name: "Gemini 3.1 Pro" },
  { id: "gemini-3.5-flash-lite", name: "Gemini 3.5 Flash Lite" },
  { id: "gemini-3.5-flash", name: "Gemini 3.5 Flash" },
  { id: "gemini-3.0-flash", name: "Gemini 3.0 Flash" },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash" },
];

const DEFAULT_MODEL_ID = "gemini-3.6-flash";
const PINNED_MODEL_IDS = new Set([
  "gemini-3.6-flash",
  "gemini-3.1-pro",
  "gemini-3.5-flash-lite",
]);

function getBridgeClient(): BridgeClient {
  const config = vscode.workspace.getConfiguration("colabLm");
  const baseUrl = config.get<string>("bridgeUrl", "http://127.0.0.1:8787");
  return new BridgeClient(baseUrl.replace(/\/$/, ""));
}

function toBridgeMessages(
  messages: readonly vscode.LanguageModelChatRequestMessage[],
  tools?: readonly vscode.LanguageModelChatTool[],
  toolMode?: vscode.LanguageModelChatToolMode,
): BridgeMessage[] {
  const bridgeMessages: BridgeMessage[] = messages
    .map((message) => {
      const content = message.content
        .map(contentPartToText)
        .filter(Boolean)
        .join("\n");
      if (!content.trim()) {
        return null;
      }
      return {
        role:
          message.role === vscode.LanguageModelChatMessageRole.Assistant
            ? ("assistant" as const)
            : ("user" as const),
        content,
      };
    })
    .filter((message): message is BridgeMessage => message !== null);

  if (tools && tools.length > 0) {
    const mode = toolMode ?? vscode.LanguageModelChatToolMode.Auto;
    bridgeMessages.unshift({
      role: "user",
      content: formatToolsPrompt(tools, mode),
    });
  }

  return bridgeMessages;
}

function toModelInfo(
  model: { id: string; name: string },
  opts: { isDefault: boolean; isUserSelectable: boolean },
): vscode.LanguageModelChatInformation {
  // isDefault / isUserSelectable control picker default + pinned visibility;
  // not yet on the stable LanguageModelChatInformation type.
  return {
    id: model.id,
    name: model.name,
    family: "gemini",
    version: "1.0.0",
    maxInputTokens: DEFAULT_MAX_INPUT,
    maxOutputTokens: DEFAULT_MAX_OUTPUT,
    tooltip: "Gemini model via google.colab.ai",
    detail: "Colab AI",
    capabilities: {
      // Agent mode filters out models without tool calling (#277165).
      toolCalling: true,
      imageInput: false,
    },
    isDefault: opts.isDefault,
    isUserSelectable: opts.isUserSelectable,
  } as vscode.LanguageModelChatInformation;
}

function textLength(
  text: string | vscode.LanguageModelChatRequestMessage,
): number {
  if (typeof text === "string") {
    return text.length;
  }
  return text.content.map(contentPartToText).join("").length;
}

function isAbortError(err: unknown): boolean {
  if (!(err instanceof Error)) {
    return false;
  }
  return (
    err.name === "AbortError" ||
    err.message === "terminated" ||
    err.message.includes("aborted")
  );
}

function pickDefaultModelId(models: readonly { id: string }[]): string | undefined {
  return (
    models.find((m) => m.id === DEFAULT_MODEL_ID)?.id ??
    models.find((m) => PINNED_MODEL_IDS.has(m.id))?.id ??
    models[0]?.id
  );
}

function toModelInfos(
  models: readonly { id: string; name: string }[],
): vscode.LanguageModelChatInformation[] {
  const defaultId = pickDefaultModelId(models);
  // Prefer pinned models in the chat picker; if none of those are available
  // on this Colab runtime, surface every available model instead.
  const hasPinned = models.some((m) => PINNED_MODEL_IDS.has(m.id));
  return models.map((m) =>
    toModelInfo(m, {
      isDefault: m.id === defaultId,
      isUserSelectable: hasPinned ? PINNED_MODEL_IDS.has(m.id) : true,
    }),
  );
}

export class ColabChatModelProvider implements vscode.LanguageModelChatProvider {
  async provideLanguageModelChatInformation(
    _options: { silent: boolean },
    _token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelChatInformation[]> {
    // Always return models so silent discovery can populate the picker.
    // Connectivity failures surface when a chat request is actually sent.
    const client = getBridgeClient();
    try {
      const models = await client.listModels();
      if (models.length > 0) {
        return toModelInfos(models);
      }
    } catch {
      // fall through to defaults
    }
    return toModelInfos(FALLBACK_MODELS);
  }

  async provideLanguageModelChatResponse(
    model: vscode.LanguageModelChatInformation,
    messages: readonly vscode.LanguageModelChatRequestMessage[],
    options: vscode.ProvideLanguageModelChatResponseOptions,
    progress: vscode.Progress<vscode.LanguageModelResponsePart>,
    token: vscode.CancellationToken,
  ): Promise<void> {
    const client = getBridgeClient();
    const healthy = await client.health();
    if (!healthy) {
      throw new Error(
        "Colab AI bridge is not reachable. Run the vscolab AI notebook cell first.",
      );
    }

    const tools = options.tools ?? [];
    const bridgeMessages = toBridgeMessages(messages, tools, options.toolMode);
    const abort = new AbortController();
    const dispose = token.onCancellationRequested(() => abort.abort());

    try {
      if (tools.length === 0) {
        for await (const chunk of client.generate(
          bridgeMessages,
          model.id,
          abort.signal,
        )) {
          if (token.isCancellationRequested) {
            return;
          }
          progress.report(new vscode.LanguageModelTextPart(chunk));
        }
        return;
      }

      // Tool-enabled turns: buffer so we can parse <tool_call> blocks reliably.
      let full = "";
      for await (const chunk of client.generate(
        bridgeMessages,
        model.id,
        abort.signal,
      )) {
        if (token.isCancellationRequested) {
          return;
        }
        full += chunk;
      }

      const { text, toolCalls } = parseToolCalls(full);
      if (text) {
        progress.report(new vscode.LanguageModelTextPart(text));
      }
      for (const call of toolCalls) {
        progress.report(
          new vscode.LanguageModelToolCallPart(call.callId, call.name, call.input),
        );
      }
    } catch (err) {
      if (token.isCancellationRequested || abort.signal.aborted) {
        return;
      }
      if (isAbortError(err)) {
        throw new Error(
          "Colab AI bridge connection closed while generating. Check that the notebook cell is still running.",
        );
      }
      throw err;
    } finally {
      dispose.dispose();
    }
  }

  async provideTokenCount(
    _model: vscode.LanguageModelChatInformation,
    text: string | vscode.LanguageModelChatRequestMessage,
    _token: vscode.CancellationToken,
  ): Promise<number> {
    return Math.ceil(textLength(text) / 4);
  }
}
