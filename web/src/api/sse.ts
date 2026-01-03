const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8001";
const RUN_URL = `${API_BASE}/run`;

export async function streamRun(
  input: string,
  resume: any | null,
  onEvent: (e: any) => void,
  signal?: AbortSignal
) {
  const resp = await fetch(RUN_URL, {
    method: "POST",
    headers: {
      Accept: "text/event-stream",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ input, resume }),
    signal
  });
  if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    // Keep last partial line in buffer
    buffer = parts.pop() || "";
    for (const line of parts) {
      const s = line.trim();
      if (!s) continue;
      let content = s;
      if (content.startsWith("data:")) content = content.slice(5).trim();
      try {
        const obj = JSON.parse(content);
        onEvent(obj);
      } catch {
        // ignore parse errors
      }
    }
  }
}

