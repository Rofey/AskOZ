"""The sites we crawl, and which of their pages are in scope.

Scope is a quality decision as much as a cost one: every page we index is a
page the model might quote. Leaving out archived or irrelevant pages keeps
answers current and retrieval sharp.
"""

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from askoz.crawl.urls import canonicalize

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
    # A few words for users ("visas and citizenship"), listed in greetings and
    # "what I can help with" messages.
    topics: str = ""
    # The referral agency (askoz.answer.agencies) this source replaces once live:
    # its questions become answerable instead of referred.
    replaces_referral: str | None = None
    # trafilatura mode. "precision" drops anything doubtful (it keeps the ATO's
    # link-only hub pages out of the index); "recall" keeps styled and linked
    # words that some sites put mid-sentence ("access to **fair treatment**
    # when buying..."), which precision silently deletes. Measure before changing.
    extraction: Literal["precision", "recall"] = "precision"
    # Some servers ignore case in paths (/Voting/ and /voting/ are one page).
    # Lowercasing stops the crawler storing duplicates.
    lowercase_paths: bool = False

    def canonical(self, url: str) -> str:
        """The one URL we store for a page, including this site's quirks."""
        url = canonicalize(url)
        if self.lowercase_paths:
            parts = urlsplit(url)
            url = parts._replace(path=parts.path.lower()).geturl()
        return url

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
            topics="visas and citizenship",
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
            topics="Centrelink, Medicare cards and Child Support",
        ),
        Source(
            name="study_australia",
            agency="Study Australia (Australian Government)",
            domain="www.studyaustralia.gov.au",
            sitemap_url="https://www.studyaustralia.gov.au/sitemap.xml",
            allow=(
                r"^/en/(plan-your-studies|plan-your-move|life-in-australia|work-in-australia)/",
            ),
            # Course-category marketing, the course search tool, and pages for
            # education agents aren't answers to international students' questions.
            deny=(r"/areas-of-study(/|$)", r"/find-a-course(/|$)", r"(?i)/agent-hub(/|$)"),
            # Precision dropped key words from 28% of the text here, junk unchanged.
            extraction="recall",
            topics="studying in Australia",
            covers=(
                "studying in Australia as an international student: choosing and changing "
                "courses or providers, costs of living, accommodation, student support and "
                "safety, working while studying, and preparing to move"
            ),
        ),
        Source(
            name="abf",
            agency="Australian Border Force",
            domain="www.abf.gov.au",
            # SharePoint like Home Affairs (links live in navigation JSON), but
            # page content is ordinary HTML, so no special extractor is needed.
            start_paths=(
                "/entering-and-leaving-australia",
                "/entering-and-leaving-australia/can-you-bring-it-in",
                "/entering-and-leaving-australia/duty-free",
            ),
            allow=(r"^/entering-and-leaving-australia(/|$)",),
            deny=(r"/Documents/", r"\.(pdf|docx?|xlsx?)$"),
            covers=(
                "arriving in and leaving Australia: what you can and can't bring in, "
                "declaring items, duty-free allowances, carrying cash, medicines and "
                "prohibited or restricted goods, and crossing the border"
            ),
            topics="what you can bring into Australia",
        ),
        Source(
            name="aec",
            agency="Australian Electoral Commission",
            domain="www.aec.gov.au",
            start_paths=(
                "/enrol/",
                "/voting/",
                "/faqs/",
                "/news/new-citizens.htm",
                "/assistance/",
            ),
            # Voter-facing parts only. Left out: parties, candidates, funding
            # disclosure, redistributions, employment and publications.
            allow=(
                r"^/(enrol|enrolling_to_vote|voting|faqs|assistance)(/|$)",
                r"^/news/new-citizens\.htm$",
            ),
            # enrolment_stats: hundreds of per-electorate statistics tables (257
            # of the first 336 pages crawled); files/ and pdf/: document listings.
            deny=(
                r"\.(pdf|docx?|xlsx?)$",
                r"/enrolment_stats(/|$)",
                r"/(files|pdf)(/|$)",
            ),
            lowercase_paths=True,  # the server ignores case: /Voting/ == /voting/
            covers=(
                "enrolling to vote and keeping your enrolment up to date, who has to "
                "enrol and vote (including new citizens), ways to vote (early, postal "
                "and from overseas), and what happens if you don't vote"
            ),
            topics="enrolling to vote",
        ),
        Source(
            name="ato_business",
            agency="Australian Taxation Office",
            domain="www.ato.gov.au",
            sitemap_url="https://www.ato.gov.au/sitemap.xml",
            # For sole traders, gig workers and small employers. Left out: corporate
            # tax, not-for-profits, international tax, trusts, e-invoicing, excise
            # and other industry taxes, and the newsrooms (dated announcements that
            # would be quoted as if current).
            allow=(
                r"^/businesses-and-organisations/(starting-registering-or-closing-a-business"
                r"|preparing-lodging-and-paying|hiring-and-paying-your-workers"
                r"|super-for-employers|assets-and-property|income-deductions-and-concessions)(/|$)",
                r"^/businesses-and-organisations/gst-excise-and-indirect-taxes/gst(/|$)",
            ),
            # Benchmarks are industry ratio tables: data, not answers.
            deny=(ARCHIVED_YEAR, r"/small-business-benchmarks(/|$)"),
            covers=(
                "tax for sole traders, gig workers and small businesses: ABNs and "
                "registering or closing a business, GST and BAS, business income and "
                "deductions, the sharing economy (rideshare, delivery, renting out), "
                "personal services income, and employer obligations (PAYG withholding "
                "and super for employees)"
            ),
            replaces_referral="ato_business",
            topics="small business tax (ABNs and GST)",
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
            topics="tax and super",
        ),
    ]
}


def source_for_url(url: str) -> Source | None:
    """The source whose scope includes `url`. Several sources can share a domain
    (the ATO's individuals and business sections), so scope decides, not host."""
    return next((s for s in SOURCES.values() if s.allows(url)), None)
