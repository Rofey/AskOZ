// Client for the AskOz API's POST /v1/ask endpoint.

import { readEvents } from "./sse";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const MAX_QUESTION_CHARS = 500; // keep in step with the API's max_question_chars

export type Source = { title: string; url: string };

// Where to go for (part of) a question AskOz doesn't cover.
export type Referral = {
  name: string;
  covers: string;
  links: { label: string; url: string }[];
  suggestion: string | null; // a related question AskOz can answer
};

export type AskHandlers = {
  onText: (text: string) => void;
  onReferral: (referral: Referral) => void;
  onClarify: (options: string[]) => void; // the question was ambiguous: pick one
  onSources: (sources: Source[]) => void;
  onDone: (info: { route: string; cached: boolean }) => void;
};

// An error with a message that is safe and useful to show the person.
export class AskError extends Error {}

// "about 3 minutes", "about 14 hours". Seconds come from the API's Retry-After.
export function waitText(seconds: number): string {
  const minutes = Math.max(1, Math.ceil(seconds / 60));
  if (minutes < 90) return `about ${minutes} minute${minutes === 1 ? "" : "s"}`;
  const hours = Math.round(minutes / 60);
  return `about ${hours} hour${hours === 1 ? "" : "s"}`;
}

function messageFor(status: number, detail: string | undefined, retryAfter: string | null): string {
  if (status === 429) {
    const seconds = Number(retryAfter);
    if (!retryAfter || !Number.isFinite(seconds)) {
      return "You've reached the question limit. Please try again later.";
    }
    return `You've reached the question limit. Please try again in ${waitText(seconds)}.`;
  }
  if (status === 422) return `Questions need to be between 3 and ${MAX_QUESTION_CHARS} characters.`;
  if (status === 503) return detail ?? "AskOz is busy right now. Please try again shortly.";
  return "Sorry, something went wrong. Please try again.";
}

export const MAX_HISTORY = 3; // keep in step with the API's AskRequest.history limit

// `history`: the conversation's earlier questions (never answers), oldest first.
// It lives only in this browser tab; the server uses it for this one request.
export async function ask(
  question: string,
  history: string[],
  handlers: AskHandlers,
  signal: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/v1/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question, history: history.slice(-MAX_HISTORY) }),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new AskError("Couldn't reach AskOz. Check your connection and try again.");
  }

  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({}));
    throw new AskError(messageFor(response.status, body.error, response.headers.get("retry-after")));
  }

  for await (const { event, data } of readEvents(response.body)) {
    const payload = JSON.parse(data);
    if (event === "text") handlers.onText(payload.text);
    else if (event === "referral") handlers.onReferral(payload);
    else if (event === "clarify") handlers.onClarify(payload.options);
    else if (event === "sources") handlers.onSources(payload);
    else if (event === "done") handlers.onDone(payload);
    else if (event === "error") throw new AskError(payload.message);
  }
}
