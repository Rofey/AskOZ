"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { AnswerText } from "@/components/AnswerText";
import {
  ExternalLink,
  EyeOff,
  Briefcase,
  HeartPulse,
  LogoMark,
  Passport,
  PiggyBank,
  Plane,
  Plus,
  Quote,
  Receipt,
  ShieldCheck,
} from "@/components/icons";
import { PromptBox } from "@/components/PromptBox";
import { ReferralCard } from "@/components/ReferralCard";
import { ask, AskError, type Referral, type Source } from "@/lib/ask";
import { findIdentifiers } from "@/lib/pii";

type Exchange = {
  id: string;
  question: string;
  answer: string;
  sources: Source[];
  referral?: Referral;
  options?: string[]; // when ambiguous: specific questions to choose from
  route?: string; // how the API handled it (answered, referral, clarify, ...)
  status: "streaming" | "done" | "error" | "stopped";
  error?: string;
};

const CONTEXT_ROUTES = new Set(["answered", "referral", "nothing_found"]);

const EXAMPLES = [
  "Can I work while studying on a student visa?",
  "How much tax do backpackers pay?",
  "Can I get my super back when I leave Australia?",
];

const TOPICS = [
  { icon: Passport, title: "Visas & citizenship", text: "Visitor, student, work and partner visas", prompt: "What visa can I get after I finish studying in Australia?" },
  { icon: Plane, title: "New to Australia", text: "TFNs, residency, working holiday tax", prompt: "How do I get a tax file number if I'm on a visa?" },
  { icon: Receipt, title: "Tax returns", text: "Lodging, refunds, amendments", prompt: "How do I lodge my first tax return?" },
  { icon: PiggyBank, title: "Super", text: "Employer super, access, DASP", prompt: "When can I access my super?" },
  { icon: HeartPulse, title: "Medicare levy", text: "Levy, surcharge and the private health rebate", prompt: "Do I have to pay the Medicare levy surcharge?" },
  { icon: Briefcase, title: "Gig work & small business", text: "ABN, GST, rideshare, sole traders", prompt: "Do I need an ABN to drive for Uber?" },
];

const TRUST = [
  { icon: ShieldCheck, text: "Answers only from official .gov.au pages" },
  { icon: Quote, text: "Every answer links to its sources" },
  { icon: EyeOff, text: "Questions aren't saved" },
];

// Distance from the bottom (px) within which we keep following a streaming answer.
const FOLLOW_THRESHOLD = 96;

export function Chat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [draft, setDraft] = useState("");
  const [following, setFollowing] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const busy = exchanges.at(-1)?.status === "streaming";
  const started = exchanges.length > 0;

  useEffect(() => () => abortRef.current?.abort(), []);

  // Follow the answer as it streams, but only while the reader is at the bottom:
  // if they scroll up to read, we stop moving the page under them.
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el && following) el.scrollTop = el.scrollHeight;
  }, [exchanges, following]);

  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (el) setFollowing(el.scrollHeight - el.scrollTop - el.clientHeight < FOLLOW_THRESHOLD);
  }, []);

  function fillPrompt(text: string) {
    setDraft(text);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      el?.focus();
      el?.setSelectionRange(text.length, text.length);
    });
  }

  function update(id: string, change: (e: Exchange) => Partial<Exchange>) {
    setExchanges((all) => all.map((e) => (e.id === id ? { ...e, ...change(e) } : e)));
  }

  function newConversation() {
    abortRef.current?.abort();
    setExchanges([]);
    setDraft("");
    setFollowing(true);
  }

  // Earlier questions that were actually answered give context to follow-ups
  // ("can I extend it?"). Blocked, off-topic and "which did you mean?" turns don't.
  const history = exchanges
    .filter((e) => e.status === "done" && e.route && CONTEXT_ROUTES.has(e.route))
    .map((e) => e.question);

  async function submit(text?: string) {
    const question = (text ?? draft).trim();
    // The prompt box already blocks these; this covers every other way in.
    if (question.length < 3 || busy || findIdentifiers(question).length > 0) return;
    const id = crypto.randomUUID();
    const controller = new AbortController();
    abortRef.current = controller;
    if (text === undefined) setDraft("");
    setFollowing(true);
    setExchanges((all) => [...all, { id, question, answer: "", sources: [], status: "streaming" }]);

    try {
      await ask(
        question,
        history,
        {
          onText: (text) => update(id, (e) => ({ answer: e.answer + text })),
          onReferral: (referral) => update(id, () => ({ referral })),
          onClarify: (options) => update(id, () => ({ options })),
          onSources: (sources) => update(id, () => ({ sources })),
          onDone: ({ route }) => update(id, () => ({ status: "done", route })),
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

  const prompt = (size: "hero" | "docked") => (
    <PromptBox
      ref={inputRef}
      size={size}
      value={draft}
      onChange={setDraft}
      onSubmit={() => submit()}
      onStop={() => abortRef.current?.abort()}
      busy={busy}
    />
  );

  return (
    <div className="flex h-dvh flex-col bg-white">
      <header className="shrink-0 border-b border-line">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4">
          <button
            type="button"
            onClick={newConversation}
            className="flex items-center gap-2.5 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
            aria-label="AskOz home"
          >
            <LogoMark className="h-8 w-8" />
            <span className="text-lg font-semibold tracking-tight">AskOz</span>
          </button>
          <div className="flex items-center gap-3">
            <span className="hidden rounded-full bg-subtle px-3 py-1 text-xs text-muted sm:inline">
              Independent · not a government website
            </span>
            {started && (
              <button
                type="button"
                onClick={newConversation}
                aria-label="New question"
                className="flex shrink-0 items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-sm font-medium hover:bg-subtle sm:px-3"
              >
                <Plus className="h-4 w-4" />
                <span className="hidden sm:inline">New question</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {!started ? (
        <main className="flex-1 overflow-y-auto">
          <section className="mx-auto max-w-3xl px-4 pb-10 pt-14 text-center sm:pt-20">
            <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Government info, <span className="text-accent">in plain English</span>
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-lg text-muted text-pretty">
              Ask about visas, citizenship, tax, super or running a small business. Answers come
              only from official Australian Government websites, with a link to every source.
            </p>
            <div className="mt-8 text-left">{prompt("hero")}</div>
            <div className="mt-4 flex flex-wrap justify-center gap-2" aria-label="Example questions">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => fillPrompt(example)}
                  className="rounded-full border border-line px-3.5 py-1.5 text-sm text-foreground transition hover:border-accent hover:text-accent"
                >
                  {example}
                </button>
              ))}
            </div>
          </section>

          <section aria-labelledby="topics-heading" className="mx-auto max-w-5xl px-4 pb-12">
            <h2 id="topics-heading" className="text-center text-sm font-semibold uppercase tracking-wider text-muted">
              Browse by topic
            </h2>
            <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {TOPICS.map(({ icon: Icon, title, text, prompt: topicPrompt }) => (
                <li key={title}>
                  <button
                    type="button"
                    onClick={() => fillPrompt(topicPrompt)}
                    className="group flex w-full items-start gap-3 rounded-xl border border-line p-4 text-left transition hover:border-accent hover:shadow-sm"
                  >
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span>
                      <span className="block font-medium group-hover:text-accent">{title}</span>
                      <span className="mt-0.5 block text-sm text-muted">{text}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section aria-label="Why AskOz" className="border-t border-line bg-subtle">
            <ul className="mx-auto grid max-w-5xl gap-4 px-4 py-8 sm:grid-cols-3">
              {TRUST.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-3 text-sm">
                  <Icon className="h-5 w-5 shrink-0 text-accent" />
                  {text}
                </li>
              ))}
            </ul>
            <p className="mx-auto max-w-5xl px-4 pb-8 text-xs leading-5 text-muted">
              AskOz is an independent service, not affiliated with or endorsed by the Australian
              Government. It gives general information only, not financial, tax, legal or migration
              advice. Always check the linked official page, or ask a registered tax agent or the
              agency. AskOz currently covers the Department of Home Affairs (visas and
              citizenship), the Australian Taxation Office (tax and super for individuals,
              sole traders and small businesses) and Study Australia.
            </p>
          </section>
        </main>
      ) : (
        <>
          <div ref={scrollRef} onScroll={onScroll} className="relative flex-1 overflow-y-auto">
            <main className="mx-auto max-w-3xl px-4 py-8">
              <ol className="flex flex-col gap-10" aria-label="Questions and answers">
                {exchanges.map((e) => (
                  <li key={e.id}>
                    <div className="flex justify-end">
                      <p className="max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-white">
                        {e.question}
                      </p>
                    </div>
                    {/* aria-live announces the answer to screen readers as it streams in */}
                    <div aria-live="polite" aria-busy={e.status === "streaming"} className="mt-5 flex gap-3">
                      <LogoMark className="mt-0.5 h-7 w-7 shrink-0" />
                      <div className="min-w-0 flex-1">
                        {e.answer ? (
                          <AnswerText text={e.answer} sources={e.sources} idPrefix={e.id} />
                        ) : e.status === "streaming" ? (
                          <p className="flex items-center gap-2 text-muted">
                            <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                            Searching official pages…
                          </p>
                        ) : null}
                        {e.status === "error" && (
                          <p role="alert" className="mt-2 rounded-lg bg-warn-bg px-3 py-2 text-sm text-warn">
                            {e.error}
                          </p>
                        )}
                        {e.status === "stopped" && <p className="mt-2 text-sm text-muted">Stopped.</p>}
                        {e.options && e.options.length > 0 && (
                          <ul className="mt-3 flex flex-col gap-2" aria-label="Choose what you mean">
                            {e.options.map((option) => (
                              <li key={option}>
                                <button
                                  type="button"
                                  disabled={busy}
                                  onClick={() => submit(option)}
                                  className="w-full rounded-xl border border-line px-4 py-2.5 text-left text-sm transition hover:border-accent hover:text-accent disabled:opacity-50"
                                >
                                  {option}
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                        {e.referral && <ReferralCard referral={e.referral} onAsk={fillPrompt} />}
                        {e.sources.length > 0 && (
                          <section aria-label="Sources" className="mt-5">
                            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
                              Sources
                            </h3>
                            <ol className="mt-2 grid gap-2">
                              {e.sources.map((s, i) => (
                                <li key={s.url} id={`${e.id}-source-${i + 1}`}>
                                  {s.url.startsWith("https://") ? (
                                    <a
                                      href={s.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="group flex items-center gap-3 rounded-lg border border-line px-3 py-2 text-sm transition hover:border-accent"
                                    >
                                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-accent-soft text-xs font-semibold text-accent">
                                        {i + 1}
                                      </span>
                                      <span className="min-w-0 flex-1">
                                        <span className="block truncate font-medium group-hover:text-accent">{s.title}</span>
                                        <span className="block truncate text-xs text-muted">
                                          {new URL(s.url).hostname}
                                        </span>
                                      </span>
                                      <ExternalLink className="h-4 w-4 shrink-0 text-muted" />
                                    </a>
                                  ) : (
                                    <span className="text-sm">{s.title}</span>
                                  )}
                                </li>
                              ))}
                            </ol>
                          </section>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </main>
            {!following && busy && (
              <button
                type="button"
                onClick={() => setFollowing(true)}
                className="sticky bottom-4 left-1/2 mx-auto block -translate-x-0 rounded-full border border-line bg-white px-4 py-1.5 text-sm shadow-md"
              >
                ↓ Follow the answer
              </button>
            )}
          </div>
          <div className="shrink-0 border-t border-line bg-white">
            <div className="mx-auto max-w-3xl px-4 pb-3 pt-3">{prompt("docked")}</div>
          </div>
        </>
      )}
    </div>
  );
}
