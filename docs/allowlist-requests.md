# Crawler allowlisting requests

Services Australia and the Fair Work Ombudsman silently block self-identified
crawlers (requests time out), even though Services Australia's robots.txt
explicitly permits crawling with a 10-second delay. AskOz won't disguise its
crawler, so the way in is to ask. Send these from rofey.dev@gmail.com.

Where to send: each site's "Contact us" / website feedback form, or their web or
digital team if you can find a direct address. Ask the form to route it to the
team that manages the website or its firewall.

---

## Services Australia

**Subject:** Request to allowlist a polite, self-identified crawler (AskOzBot)

Hello,

I'm building AskOz, an independent, free service that helps people, especially
those new to Australia, find official government information in plain English.
Every answer links back to the official page it came from, so it sends readers
to your website rather than replacing it.

Your robots.txt permits crawling with a 10-second crawl delay, but requests from
our crawler time out, which suggests a firewall rule is blocking self-identified
bots. We'd like to crawl only your public information pages, and we'd follow
these rules:

- User-Agent: `Mozilla/5.0 (compatible; AskOzBot/0.1; +https://github.com/Rofey/AskOZ; rofey.dev@gmail.com)`
- Obeys robots.txt, including your 10-second Crawl-delay (one request at a time)
- Public pages only: no logins, forms, searches or myGov/Centrelink online accounts
- A full crawl roughly once a week, then only pages whose sitemap date changed

Could you allowlist this User-Agent, or tell me the right way to request access?
I'm also happy to use an official data feed if one exists. Details about the bot
are at https://github.com/Rofey/AskOZ.

Thank you,
[Your name]
rofey.dev@gmail.com

---

## Fair Work Ombudsman

**Subject:** Request to allowlist a polite, self-identified crawler (AskOzBot)

Hello,

I'm building AskOz, an independent, free service that helps people, especially
those new to Australia, find official government information in plain English.
Every answer links back to the official page it came from, so it sends readers
to your website rather than replacing it.

Requests from our crawler to fairwork.gov.au time out, which suggests a firewall
rule is blocking self-identified bots. We'd like to crawl your public guidance
pages (pay, leave, employment conditions), and we'd follow these rules:

- User-Agent: `Mozilla/5.0 (compatible; AskOzBot/0.1; +https://github.com/Rofey/AskOZ; rofey.dev@gmail.com)`
- Obeys robots.txt and any crawl delay you set (one request at a time, 2+ seconds apart)
- Public pages only: no logins, forms, calculators or the Pay and Conditions Tool
- A full crawl roughly once a week, then only changed pages

Could you allowlist this User-Agent, or point me to the right team? If you offer
an official data feed or API for pay rates and guidance, I'd happily use that
instead. Details about the bot are at https://github.com/Rofey/AskOZ.

Thank you,
[Your name]
rofey.dev@gmail.com
