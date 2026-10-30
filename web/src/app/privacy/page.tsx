import type { Metadata } from "next";

import { LegalPage } from "@/components/LegalPage";

export const metadata: Metadata = {
  title: "Privacy · AskOz",
  description: "What AskOz does with your questions, and what it keeps.",
};

// Every statement here must match what the code does. If you change logging,
// caching, rate limiting or a provider, update this page in the same change.
export default function Privacy() {
  return (
    <LegalPage title="Privacy" updated="30 October 2026">
      <p>
        AskOz is built to need as little information about you as possible. There are no
        accounts, no cookies and no advertising or analytics trackers. This page explains exactly
        what happens when you ask a question.
      </p>

      <h2>Please don&apos;t share personal details</h2>
      <p>
        You don&apos;t need to tell AskOz who you are to get an answer. Don&apos;t include your
        tax file number, Medicare number, passport number, name, address or other identifying
        details. AskOz checks for some of these in your browser and won&apos;t send a question
        that appears to contain one.
      </p>

      <h2>Your questions</h2>
      <ul>
        <li>
          <strong>We don&apos;t keep your questions.</strong> AskOz doesn&apos;t save the text of
          your questions in a database or in its logs.
        </li>
        <li>
          <strong>To write an answer</strong>, your question (and up to three earlier questions
          from the same conversation, so follow-up questions make sense) is sent to Anthropic, the
          company that makes the Claude AI model, together with the official web pages
          AskOz found. Anthropic processes it under its commercial terms and{" "}
          <a href="https://www.anthropic.com/legal/privacy">privacy policy</a>, which
          includes servers outside Australia.
        </li>
        <li>
          <strong>Answers are cached for up to 2 hours</strong> so that the same question asked
          again is answered instantly and cheaply. The cache stores the answer, filed under a
          one-way scrambled code (a &quot;hash&quot;) made from the question, not the question
          itself.
        </li>
      </ul>

      <h2>Your IP address</h2>
      <ul>
        <li>
          <strong>Fair-use limits.</strong> To stop any one person overloading the service,
          AskOz limits how many questions can be asked from one internet address. It does this
          with a scrambled code made from your IP address using a secret key, not the address
          itself, and forgets it within a day.
        </li>
        <li>
          <strong>Hosting logs.</strong> AskOz runs on Google Cloud and Firebase. Like most
          websites, these services keep standard technical logs of each request, including
          the IP address, browser type and time (but not your question), for about 30 days. They
          are used only to keep the service secure and working.
        </li>
      </ul>

      <h2>In your browser</h2>
      <p>
        Your conversation exists only in the open browser tab. Nothing is saved on your device,
        and closing or refreshing the page clears it.
      </p>

      <h2>Who provides the service</h2>
      <ul>
        <li>Google Cloud (the answering service and its database), in Sydney</li>
        <li>Firebase Hosting (the website itself), from Google&apos;s worldwide network</li>
        <li>Upstash (temporary cache and fair-use counters), in Sydney</li>
        <li>Anthropic (the AI model that writes answers), outside Australia</li>
      </ul>
      <p>None of them is given your name or contact details, because AskOz never asks for them.</p>

      <h2>Changes</h2>
      <p>If this page changes, the date at the top will change too.</p>
    </LegalPage>
  );
}
