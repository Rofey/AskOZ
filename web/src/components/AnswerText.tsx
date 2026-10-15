import ReactMarkdown from "react-markdown";

import type { Source } from "@/lib/ask";

// Turns Claude's "[2]" markers into links to the matching source below the answer.
// react-markdown never renders raw HTML from the text, so content that came from
// a crawled page can't inject scripts into ours.
function linkCitations(text: string): string {
  return text.replace(/\[(\d+)\]/g, (_match, n) => `[\\[${n}\\]](#cite-${n})`);
}

export function AnswerText({
  text,
  sources,
  idPrefix,
}: {
  text: string;
  sources: Source[];
  idPrefix: string;
}) {
  return (
    <div className="answer">
      <ReactMarkdown
        components={{
          a({ href, children }) {
            const cite = href?.match(/^#cite-(\d+)$/);
            if (cite) {
              const n = Number(cite[1]);
              const source = sources[n - 1];
              return (
                <sup>
                  <a
                    href={`#${idPrefix}-source-${n}`}
                    className="citation"
                    aria-label={source ? `Source ${n}: ${source.title}` : `Source ${n}`}
                  >
                    {n}
                  </a>
                </sup>
              );
            }
            // Ordinary links in an answer: only https, always in a new tab.
            if (!href?.startsWith("https://")) return <>{children}</>;
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {linkCitations(text)}
      </ReactMarkdown>
    </div>
  );
}
