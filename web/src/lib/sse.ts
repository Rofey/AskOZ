// Server-Sent Events parsing for fetch() responses.
//
// The browser's EventSource only supports GET, and we POST the question, so we
// read the response body ourselves. Network chunks don't line up with events: one
// chunk can hold several events, or end halfway through one, so we buffer until
// we see the blank line that ends each event.

export type SSEEvent = { event: string; data: string };

export function parseEvents(buffer: string): { events: SSEEvent[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n");
  const rest = blocks.pop() ?? ""; // incomplete final block: wait for more data
  const events: SSEEvent[] = [];
  for (const block of blocks) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length) events.push({ event, data: data.join("\n") });
  }
  return { events, rest };
}

export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<SSEEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }); // stream: true keeps split UTF-8 intact
      const { events, rest } = parseEvents(buffer);
      buffer = rest;
      yield* events;
    }
  } finally {
    reader.releaseLock();
  }
}
