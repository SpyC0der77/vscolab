import * as vscode from "vscode";
import { BridgeClient, type BridgeMessage } from "./bridgeClient";
import {
  contentPartToText,
  formatToolsPrompt,
  parseToolCalls,
} from "./tools";

const DEFAULT_MAX_INPUT = 1_000_000;
const DEFAULT_MAX_OUTPUT = 8192;

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
  isDefault: boolean,
): vscode.LanguageModelChatInformation {
  // isDefault / isUserSelectable control picker default + visibility;
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
    isDefault,
    isUserSelectable: true,
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

export class ColabChatModelProvider implements vscode.LanguageModelChatProvider {
  async provideLanguageModelChatInformation(
    _options: { silent: boolean },
    _token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelChatInformation[]> {
    try {
      const models = await getBridgeClient().listModels();
      return models.map((m, i) => toModelInfo(m, i === 0));
    } catch {
      return [];
    }
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
