"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

import { ArrowUp, Stop } from "@/components/icons";
import { MAX_QUESTION_CHARS } from "@/lib/ask";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  busy: boolean;
  size: "hero" | "docked";
};

// The question input, used both large on the landing view and docked at the
// bottom of the conversation. Grows with its content up to a limit.
export const PromptBox = forwardRef<HTMLTextAreaElement, Props>(function PromptBox(
  { value, onChange, onSubmit, onStop, busy, size },
  ref,
) {
  const inner = useRef<HTMLTextAreaElement>(null);
  useImperativeHandle(ref, () => inner.current as HTMLTextAreaElement);

  useEffect(() => {
    const el = inner.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const canSend = value.trim().length >= 3 && !busy;
  const hero = size === "hero";

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onSubmit();
      }}
    >
      <label htmlFor={`question-${size}`} className="sr-only">
        Your question
      </label>
      <div
        className={`flex items-end gap-2 rounded-2xl border border-line bg-white shadow-sm transition focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/10 ${
          hero ? "p-3" : "p-2"
        }`}
      >
        <textarea
          id={`question-${size}`}
          ref={inner}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (canSend) onSubmit();
            }
          }}
          maxLength={MAX_QUESTION_CHARS}
          rows={hero ? 2 : 1}
          placeholder={hero ? "Describe what you need to know…" : "Ask another question…"}
          aria-describedby={`privacy-${size}`}
          className={`flex-1 resize-none bg-transparent px-2 py-1.5 leading-6 text-foreground outline-none placeholder:text-muted ${
            hero ? "text-lg" : "text-base"
          }`}
        />
        {busy ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop answering"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-line text-foreground hover:bg-subtle"
          >
            <Stop className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSend}
            aria-label="Ask"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-white transition hover:bg-accent-strong disabled:bg-line disabled:text-muted"
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        )}
      </div>
      <p id={`privacy-${size}`} className="mt-2 flex justify-between gap-4 px-1 text-xs text-muted">
        <span>Don&apos;t include your TFN, Medicare or passport number. Questions aren&apos;t saved.</span>
        <span className="tabular-nums" aria-hidden={value.length < MAX_QUESTION_CHARS - 50}>
          {value.length}/{MAX_QUESTION_CHARS}
        </span>
      </p>
    </form>
  );
});
