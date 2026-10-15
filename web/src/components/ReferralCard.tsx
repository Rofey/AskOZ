import { ExternalLink } from "@/components/icons";
import type { Referral } from "@/lib/ask";

export function ReferralCard({
  referral,
  onAsk,
}: {
  referral: Referral;
  onAsk: (question: string) => void;
}) {
  const many = referral.links.length > 1;
  return (
    <section
      aria-label="Where to go instead"
      className="mt-5 rounded-xl border border-line bg-subtle p-4"
    >
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">Where to go</h3>
      <p className="mt-1.5 text-sm">
        <span className="font-medium">
          {referral.name.charAt(0).toUpperCase() + referral.name.slice(1)}
        </span>
        <span className="text-muted"> handles {referral.covers}.</span>
      </p>
      <ul className={`mt-3 ${many ? "flex flex-wrap gap-2" : ""}`}>
        {referral.links
          .filter((link) => link.url.startsWith("https://"))
          .map((link) => (
            <li key={link.url}>
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center gap-1.5 rounded-lg border border-line bg-white text-sm font-medium transition hover:border-accent hover:text-accent ${
                  many ? "px-3 py-1.5" : "px-3.5 py-2"
                }`}
              >
                {many ? link.label : `Go to ${link.label}`}
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </li>
          ))}
      </ul>
      {referral.suggestion && (
        <p className="mt-4 text-sm">
          <span className="text-muted">AskOz can help with: </span>
          <button
            type="button"
            onClick={() => onAsk(referral.suggestion!)}
            className="text-left font-medium text-accent underline underline-offset-2 hover:text-accent-strong"
          >
            {referral.suggestion}
          </button>
        </p>
      )}
    </section>
  );
}
