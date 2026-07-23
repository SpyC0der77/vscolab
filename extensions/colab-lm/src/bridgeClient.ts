export interface BridgeMessage {
  role: "user" | "assistant";
  content: string;
}

export interface BridgeModel {
  id: string;
  name: string;
}

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
    const res = await fetch(`${this.baseUrl}/models`);
    if (!res.ok) {
      return [];
    }
    const data = (await res.json()) as { models?: string[] };
    return (data.models ?? []).map((id) => ({
      id,
      name: formatModelName(id),
    }));
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
          const chunk = JSON.parse(trimmed) as { text?: string | null };
          if (typeof chunk.text === "string" && chunk.text.length > 0) {
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
      const chunk = JSON.parse(tail) as { text?: string | null };
      if (typeof chunk.text === "string" && chunk.text.length > 0) {
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
