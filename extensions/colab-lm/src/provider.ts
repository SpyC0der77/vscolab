import * as vscode from "vscode";
import { BridgeClient, type BridgeMessage } from "./bridgeClient";

const DEFAULT_MAX_INPUT = 1_000_000;
const DEFAULT_MAX_OUTPUT = 8192;

function getBridgeClient(): BridgeClient {
  const config = vscode.workspace.getConfiguration("colabLm");
  const baseUrl = config.get<string>("bridgeUrl", "http://127.0.0.1:8787");
  return new BridgeClient(baseUrl.replace(/\/$/, ""));
}

function toBridgeMessages(
  messages: readonly vscode.LanguageModelChatRequestMessage[],
): BridgeMessage[] {
  return messages.map((message) => ({
    role:
      message.role === vscode.LanguageModelChatMessageRole.Assistant
        ? "assistant"
        : "user",
    content: message.content
      .filter((part): part is vscode.LanguageModelTextPart =>
        part instanceof vscode.LanguageModelTextPart,
      )
      .map((part) => part.value)
      .join(""),
  }));
}

function toModelInfo(model: { id: string; name: string }): vscode.LanguageModelChatInformation {
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
      toolCalling: false,
      imageInput: false,
    },
  };
}

function textLength(
  text: string | vscode.LanguageModelChatRequestMessage,
): number {
  if (typeof text === "string") {
    return text.length;
  }
  return text.content
    .filter((part): part is vscode.LanguageModelTextPart =>
      part instanceof vscode.LanguageModelTextPart,
    )
    .map((part) => part.value)
    .join("").length;
}

export class ColabChatModelProvider implements vscode.LanguageModelChatProvider {
  async provideLanguageModelChatInformation(
    options: { silent: boolean },
    _token: vscode.CancellationToken,
  ): Promise<vscode.LanguageModelChatInformation[]> {
    const client = getBridgeClient();
    const healthy = await client.health();
    if (!healthy) {
      if (options.silent) {
        return [];
      }
      throw new Error(
        "Colab AI bridge is not reachable. Run the vscolab AI notebook cell first.",
      );
    }

    const models = await client.listModels();
    return models.map(toModelInfo);
  }

  async provideLanguageModelChatResponse(
    model: vscode.LanguageModelChatInformation,
    messages: readonly vscode.LanguageModelChatRequestMessage[],
    _options: vscode.ProvideLanguageModelChatResponseOptions,
    progress: vscode.Progress<vscode.LanguageModelResponsePart>,
    token: vscode.CancellationToken,
  ): Promise<void> {
    const client = getBridgeClient();
    const bridgeMessages = toBridgeMessages(messages);
    const abort = new AbortController();

    const dispose = token.onCancellationRequested(() => abort.abort());
    try {
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
