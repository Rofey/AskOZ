import Link from "next/link";
import type { ReactNode } from "react";

/** Shared shell for the privacy and terms pages: plain, readable, no chat. */
export function LegalPage({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: ReactNode;
}) {
  return (
    <>
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <Link href="/" className="font-semibold text-foreground hover:text-accent">
            AskOz
          </Link>
          <Link href="/" className="text-sm text-accent hover:underline">
            Ask a question
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-4 py-10">
        <article className="legal">
          <h1>{title}</h1>
          <p className="text-sm text-muted">Last updated {updated}</p>
          {children}
        </article>
      </main>
      <LegalLinks />
    </>
  );
}

export function LegalLinks() {
  return (
    <nav aria-label="Legal" className="mx-auto max-w-5xl px-4 pb-8 text-xs text-muted">
      <Link href="/privacy" className="hover:text-accent hover:underline">
        Privacy
      </Link>
      <span aria-hidden="true"> · </span>
      <Link href="/terms" className="hover:text-accent hover:underline">
        Terms of use
      </Link>
    </nav>
  );
}
