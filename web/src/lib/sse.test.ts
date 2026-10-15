import { describe, expect, it } from "vitest";

import { parseEvents, readEvents } from "./sse";

describe("parseEvents", () => {
  it("parses complete events and keeps the incomplete tail", () => {
    const input = 'event: text\ndata: {"text":"Hi"}\n\nevent: done\ndata: {}\n\nevent: te';
    const { events, rest } = parseEvents(input);
    expect(events).toEqual([
      { event: "text", data: '{"text":"Hi"}' },
      { event: "done", data: "{}" },
    ]);
    expect(rest).toBe("event: te");
  });

  it("handles CRLF line endings", () => {
    expect(parseEvents("event: done\r\ndata: {}\r\n\r\n").events).toEqual([
      { event: "done", data: "{}" },
    ]);
  });
});

describe("readEvents", () => {
  it("reassembles events split across network chunks, including split UTF-8", async () => {
    const bytes = new TextEncoder().encode('event: text\ndata: {"text":"you’re"}\n\n');
    const cut = bytes.indexOf(0x99); // in the middle of the 3-byte ’ character
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(bytes.slice(0, cut));
        controller.enqueue(bytes.slice(cut));
        controller.close();
      },
    });
    const events = [];
    for await (const e of readEvents(body)) events.push(e);
    expect(events).toEqual([{ event: "text", data: '{"text":"you’re"}' }]);
  });
});
