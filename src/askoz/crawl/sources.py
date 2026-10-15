"""The sites we crawl, and which of their pages are in scope.

Scope is a quality decision as much as a cost one: every page we index is a
page the model might quote. Leaving out archived or irrelevant pages keeps
answers current and retrieval sharp.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

# A year from 2000-2023 in a URL path marks archived, year-specific guidance
# (e.g. ATO's "individual-tax-return-2019-instructions").
ARCHIVED_YEAR = r"(?<!\d)20(?:0\d|1\d|2[0-3])(?!\d)"


@dataclass(frozen=True)
class Source:
    name: str
    agency: str
    domain: str
    allow: tuple[str, ...]  # regexes on the URL path; a page must match at least one
    deny: tuple[str, ...] = ()  # regexes on the URL path; any match excludes the page
    sitemap_url: str | None = None
    start_paths: tuple[str, ...] = ()  # entry points for sites without a sitemap
    min_delay: float = 2.0  # seconds between requests; robots.txt Crawl-delay can raise it
    max_depth: int = 6  # link hops from a start page (link-following sources only)
    # What questions this source answers, in plain words. Used in the planner's
    # coverage rules and in "AskOz currently covers ..." messages.
    covers: str = ""
    # The referral agency (askoz.answer.agencies) this source replaces once live:
    # its questions become answerable instead of referred.
    replaces_referral: str | None = None

    def allows(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.hostname != self.domain:
            return False
        path = parts.path or "/"
        return any(re.search(p, path) for p in self.allow) and not any(
            re.search(p, path) for p in self.deny
        )


SOURCES: dict[str, Source] = {
    s.name: s
    for s in [
        Source(
            name="home_affairs",
            agency="Department of Home Affairs",
            domain="immi.homeaffairs.gov.au",
            # No sitemap, so we follow links from these sections.
            start_paths=(
                "/visas/getting-a-visa/visa-listing",
                "/citizenship",
                "/entering-and-leaving-australia",
                "/help-support",
            ),
            allow=(
                r"^/visas(/|$)",
                r"^/citizenship(/|$)",
                r"^/entering-and-leaving-australia(/|$)",
                r"^/help-support(/|$)",
            ),
            deny=(r"/Documents/", r"\.(pdf|docx?|xlsx?)$"),
            covers=(
                "visas (visitor, student, work, skilled, family and partner visas: "
                "eligibility, costs, conditions and how to apply), citizenship, and "
                "travelling to and from Australia"
            ),
            replaces_referral="home_affairs",
        ),
        Source(
            name="services_australia",
            agency="Services Australia",
            domain="www.servicesaustralia.gov.au",
            sitemap_url="https://www.servicesaustralia.gov.au/sitemap.xml",
            allow=(r"^/",),
            deny=(r"^/search(/|$)",),
            min_delay=10.0,  # their robots.txt asks for Crawl-delay: 10
            covers="Centrelink payments, Medicare enrolment and cards, and Child Support",
            replaces_referral="services_australia",
        ),
        Source(
            name="ato",
            agency="Australian Taxation Office",
            domain="www.ato.gov.au",
            sitemap_url="https://www.ato.gov.au/sitemap.xml",
            allow=(r"^/individuals-and-families/",),
            deny=(ARCHIVED_YEAR,),
            covers=(
                "tax for individuals: income tax, tax returns and refunds, deductions and "
                "offsets, tax file numbers, tax residency, superannuation, the Medicare "
                "levy and surcharge, private health insurance rebates on tax returns, "
                "HELP/study loan repayments, and paying the ATO"
            ),
        ),
    ]
}
