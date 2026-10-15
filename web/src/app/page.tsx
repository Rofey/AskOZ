import { Chat } from "@/components/Chat";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 pt-10">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">AskOz</h1>
        <p className="mt-2 text-muted">
          Plain-English answers from official Australian Government websites, with a source for
          every answer.
        </p>
        <p className="mt-3 inline-block rounded-md bg-note-bg px-3 py-1.5 text-xs text-note">
          Independent service. Not affiliated with or endorsed by the Australian Government.
        </p>
      </header>

      <Chat />

      <footer className="border-t border-line py-4 text-xs text-muted">
        General information only, not financial, tax, legal or migration advice. Always check the
        linked official page, or ask a registered tax agent or the agency itself. AskOz currently
        covers Australian Taxation Office pages for individuals.
      </footer>
    </main>
  );
}
