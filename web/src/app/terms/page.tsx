import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";

export const metadata: Metadata = {
  title: "Terms of use · AskOz",
  description: "What AskOz is, what it isn't, and the rules for using it.",
};

export default function Terms() {
  return (
    <LegalPage title="Terms of use" updated="30 October 2026">
      <p>By using AskOz, you agree to these terms. Please read them, especially the first two.</p>

      <h2>AskOz is not the government</h2>
      <p>
        AskOz is an independent service. It is not affiliated with, endorsed by or operated by
        the Australian Government or any of its agencies, including the Australian Taxation
        Office, the Department of Home Affairs, the Australian Border Force, the Australian
        Electoral Commission or Study Australia.
      </p>

      <h2>General information, not advice</h2>
      <ul>
        <li>
          AskOz gives general information only. It is not financial, tax, legal, migration or
          any other professional advice, and it doesn&apos;t consider your personal
          circumstances.
        </li>
        <li>
          Answers are written by an AI model from official web pages. AI can misread, leave out
          or wrongly combine information, and government pages change. An answer may be
          incomplete, out of date or wrong.
        </li>
        <li>
          <strong>Always check the linked official page</strong> before you rely on an answer,
          especially for deadlines, amounts, eligibility or anything with legal or financial
          consequences. For advice about your situation, contact the agency, a registered tax
          agent or a registered migration agent.
        </li>
      </ul>

      <h2>Fair use</h2>
      <p>To keep AskOz free and available to everyone, please don&apos;t:</p>
      <ul>
        <li>send automated or bulk requests, or try to get around the usage limits</li>
        <li>try to disrupt, overload or break into the service</li>
        <li>use AskOz to do anything unlawful</li>
      </ul>
      <p>AskOz may limit or block access that breaks these rules.</p>

      <h2>Content from official websites</h2>
      <p>
        Answers quote and summarise information published on official Australian Government
        websites, which remains the property of the relevant agencies. Every answer links to its
        sources so you can read the original.
      </p>

      <h2>No guarantee</h2>
      <p>
        AskOz is provided free and &quot;as is&quot;. It may be unavailable, slow or changed at
        any time. To the extent the law allows, AskOz is not liable for any loss arising from
        your use of it or reliance on its answers. Nothing in these terms excludes rights you
        have under the Australian Consumer Law that can&apos;t be excluded.
      </p>

      <h2>Changes</h2>
      <p>These terms may be updated; the date at the top shows when.</p>
    </LegalPage>
  );
}
