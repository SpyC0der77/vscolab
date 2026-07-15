export interface BridgeMessage {
  role: "user" | "assistant";
  content: string;
}

export interface BridgeModel {
  id: string;
  name: string;
}

const DEFAULT_MODELS: BridgeModel[] = [
  { id: "gemini-3.5-flash", name: "Gemini 3.5 Flash" },
  { id: "gemini-3.1-pro", name: "Gemini 3.1 Pro" },
  { id: "gemini-3.0-flash", name: "Gemini 3.0 Flash" },
  { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash" },
];

export class BridgeClient {
  constructor(private readonly baseUrl: string) {}

  async health(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      return res.ok;
    } catch {
      return false;
    }
  }

  async listModels(): Promise<BridgeModel[]> {
    try {
      const res = await fetch(`${this.baseUrl}/models`);
      if (!res.ok) {
        return DEFAULT_MODELS;
      }
      const data = (await res.json()) as { models?: string[] };
      const models = data.models ?? [];
      if (models.length === 0) {
        return DEFAULT_MODELS;
      }
      return models.map((id) => ({
        id,
        name: formatModelName(id),
      }));
    } catch {
      return DEFAULT_MODELS;
    }
  }

  async *generate(
    messages: BridgeMessage[],
    model: string,
    signal?: AbortSignal,
  ): AsyncGenerator<string> {
    let res: Response;
    try {
      res = await fetch(`${this.baseUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages, model, stream: true }),
        signal,
      });
    } catch (err) {
      if (signal?.aborted) {
        return;
      }
      throw err;
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Colab AI bridge error (${res.status}): ${text}`);
    }

    if (!res.body) {
      throw new Error("Colab AI bridge returned no response body.");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            continue;
          }
          const chunk = JSON.parse(trimmed) as { text?: string };
          if (chunk.text) {
            yield chunk.text;
          }
        }
      }
    } catch (err) {
      if (signal?.aborted) {
        return;
      }
      throw err;
    }

    const tail = buffer.trim();
    if (tail) {
      const chunk = JSON.parse(tail) as { text?: string };
      if (chunk.text) {
        yield chunk.text;
      }
    }
  }
}

function formatModelName(id: string): string {
  return id
    .replace(/^gemini-/, "Gemini ")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
