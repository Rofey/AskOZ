"use client";

import { useEffect, useRef, useState } from "react";

import { AnswerText } from "@/components/AnswerText";
import { ask, AskError, MAX_QUESTION_CHARS, type Source } from "@/lib/ask";

type Exchange = {
  id: string;
  question: string;
  answer: string;
  sources: Source[];
  status: "streaming" | "done" | "error" | "stopped";
  error?: string;
};

const EXAMPLES = [
  "How much tax do backpackers pay?",
  "How do I get a TFN if I'm on a visa?",
  "Can I get my super back when I leave Australia?",
  "Do I have to pay the Medicare levy surcharge?",
];

export function Chat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [draft, setDraft] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const busy = exchanges.at(-1)?.status === "streaming";

  useEffect(() => () => abortRef.current?.abort(), []);

  function update(id: string, change: (e: Exchange) => Partial<Exchange>) {
    setExchanges((all) => all.map((e) => (e.id === id ? { ...e, ...change(e) } : e)));
  }

  async function submit(question: string) {
    const trimmed = question.trim();
    if (trimmed.length < 3 || busy) return;
    const id = crypto.randomUUID();
    const controller = new AbortController();
    abortRef.current = controller;
    setDraft("");
    setExchanges((all) => [
      ...all,
      { id, question: trimmed, answer: "", sources: [], status: "streaming" },
    ]);

    try {
      await ask(
        trimmed,
        {
          onText: (text) => update(id, (e) => ({ answer: e.answer + text })),
          onSources: (sources) => update(id, () => ({ sources })),
          onDone: () => update(id, () => ({ status: "done" })),
        },
        controller.signal,
      );
    } catch (error) {
      if (controller.signal.aborted) {
        update(id, () => ({ status: "stopped" }));
      } else {
        const message =
          error instanceof AskError ? error.message : "Sorry, something went wrong. Please try again.";
        update(id, () => ({ status: "error", error: message }));
      }
    } finally {
      inputRef.current?.focus();
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      {exchanges.length === 0 ? (
        <section aria-labelledby="examples-heading" className="mt-8">
          <h2 id="examples-heading" className="text-sm font-medium text-muted">
            Try asking
          </h2>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {EXAMPLES.map((example) => (
              <li key={example}>
                <button
                  type="button"
                  onClick={() => submit(example)}
                  className="w-full rounded-lg border border-line bg-surface px-4 py-3 text-left text-sm transition hover:border-accent focus-visible:outline-2 focus-visible:outline-accent"
                >
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <ol className="mt-6 flex flex-col gap-8" aria-label="Questions and answers">
          {exchanges.map((e) => (
            <li key={e.id}>
              <p className="font-semibold">{e.question}</p>
              {/* aria-live announces the answer to screen readers as it streams in */}
              <div aria-live="polite" aria-busy={e.status === "streaming"} className="mt-3">
                {e.answer ? (
                  <AnswerText text={e.answer} sources={e.sources} idPrefix={e.id} />
                ) : e.status === "streaming" ? (
                  <p className="text-muted">Searching official pages…</p>
                ) : null}
                {e.status === "error" && (
                  <p role="alert" className="mt-2 rounded-md bg-warn-bg px-3 py-2 text-sm text-warn">
                    {e.error}
                  </p>
                )}
                {e.status === "stopped" && <p className="mt-2 text-sm text-muted">Stopped.</p>}
              </div>
              {e.sources.length > 0 && (
                <section aria-label="Sources" className="mt-4 border-t border-line pt-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Sources</h3>
                  <ol className="mt-2 space-y-1 text-sm">
                    {e.sources.map((s, i) => (
                      <li key={s.url} id={`${e.id}-source-${i + 1}`} className="flex gap-2">
                        <span className="text-muted">{i + 1}.</span>
                        {s.url.startsWith("https://") ? (
                          <a href={s.url} target="_blank" rel="noopener noreferrer" className="underline decoration-line underline-offset-2 hover:decoration-accent">
                            {s.title}
                          </a>
                        ) : (
                          <span>{s.title}</span>
                        )}
                      </li>
                    ))}
                  </ol>
                </section>
              )}
            </li>
          ))}
        </ol>
      )}

      <form
        className="sticky bottom-0 mt-8 bg-background pb-4 pt-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit(draft);
        }}
      >
        <label htmlFor="question" className="sr-only">
          Your question
        </label>
        <div className="flex items-end gap-2 rounded-xl border border-line bg-surface p-2 focus-within:border-accent">
          <textarea
            id="question"
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit(draft);
              }
            }}
            maxLength={MAX_QUESTION_CHARS}
            rows={2}
            placeholder="Ask about tax, super, Medicare, study loans…"
            aria-describedby="privacy-note"
            className="flex-1 resize-none bg-transparent px-2 py-1 outline-none"
          />
          {busy ? (
            <button
              type="button"
              onClick={() => abortRef.current?.abort()}
              className="rounded-lg border border-line px-4 py-2 text-sm"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={draft.trim().length < 3}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent disabled:opacity-40"
            >
              Ask
            </button>
          )}
        </div>
        <p id="privacy-note" className="mt-2 text-xs text-muted">
          Don&apos;t include your TFN, Medicare or passport number. Questions aren&apos;t saved.
          <span className="float-right tabular-nums">
            {draft.length}/{MAX_QUESTION_CHARS}
          </span>
        </p>
      </form>
    </div>
  );
}
