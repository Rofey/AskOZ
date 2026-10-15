"""Where to send questions AskOz can't answer yet.

A fixed, human-checked list. The planner can only pick an `id` from it
(enforced by structured output), so a referral can never contain a made-up
URL. When AskOz starts crawling one of these agencies, its questions move from
"referral" to "covered" and the entry stays as the fallback.

Run `uv run askoz check-links` to confirm every URL still resolves. Last
checked October 2026; australia.gov.au now redirects to myGov's service
directory, and Scamwatch was dropped because it blocks automated checks.
"""

from dataclasses import dataclass
from typing import Literal

AgencyId = Literal[
    "home_affairs",
    "passports",
    "services_australia",
    "my_gov",
    "fair_work",
    "ndis",
    "study_assist",
    "ato_business",
    "ato_scams",
    "business_gov",
    "moneysmart",
    "healthdirect",
    "state_government",
    "gov_services_directory",
]


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class Agency:
    id: AgencyId
    name: str
    covers: str  # shown to the planner and to the user: what this agency handles
    links: tuple[Link, ...]


def _one(id: AgencyId, name: str, url: str, covers: str) -> Agency:
    return Agency(id=id, name=name, covers=covers, links=(Link(name, url),))


AGENCIES: dict[str, Agency] = {
    a.id: a
    for a in [
        _one(
            "home_affairs",
            "Department of Home Affairs",
            "https://immi.homeaffairs.gov.au",
            "visas, citizenship and travelling to and from Australia",
        ),
        _one(
            "passports",
            "Australian Passport Office",
            "https://www.passports.gov.au",
            "applying for and renewing Australian passports",
        ),
        _one(
            "services_australia",
            "Services Australia",
            "https://www.servicesaustralia.gov.au",
            "Centrelink payments and eligibility, Medicare enrolment and cards, and Child Support",
        ),
        _one(
            "my_gov", "myGov", "https://my.gov.au", "myGov accounts, sign-in and linking services"
        ),
        _one(
            "fair_work",
            "Fair Work Ombudsman",
            "https://www.fairwork.gov.au",
            "pay rates, minimum wage, leave, workplace rights and employment conditions",
        ),
        _one(
            "ndis",
            "National Disability Insurance Scheme",
            "https://www.ndis.gov.au",
            "NDIS eligibility, plans and disability supports",
        ),
        _one(
            "study_assist",
            "StudyAssist",
            "https://www.studyassist.gov.au",
            "eligibility for HELP loans and Commonwealth supported places",
        ),
        _one(
            "ato_business",
            "Australian Taxation Office (businesses)",
            "https://www.ato.gov.au/businesses-and-organisations",
            "tax for businesses, GST, BAS and employer obligations",
        ),
        _one(
            "ato_scams",
            "the ATO's scams and identity protection guidance",
            "https://www.ato.gov.au/online-services/scams-cyber-safety-and-identity-protection",
            "checking whether ATO calls, texts or emails are genuine, and reporting scams "
            "and identity theft",
        ),
        _one(
            "business_gov",
            "business.gov.au",
            "https://business.gov.au",
            "starting and running a business, ABN and business name registration",
        ),
        _one(
            "moneysmart",
            "Moneysmart",
            "https://moneysmart.gov.au",
            "budgeting, debt, scams, investing, insurance and choosing financial products",
        ),
        _one(
            "healthdirect",
            "healthdirect",
            "https://www.healthdirect.gov.au",
            "health advice and finding health services",
        ),
        Agency(
            id="state_government",
            name="your state or territory government",
            covers=(
                "driver licences, car registration, housing, schools, police checks "
                "and other state services"
            ),
            links=(
                Link("NSW", "https://www.nsw.gov.au"),
                Link("VIC", "https://www.vic.gov.au"),
                Link("QLD", "https://www.qld.gov.au"),
                Link("WA", "https://www.wa.gov.au"),
                Link("SA", "https://www.sa.gov.au"),
                Link("TAS", "https://www.tas.gov.au"),
                Link("ACT", "https://www.act.gov.au"),
                Link("NT", "https://nt.gov.au"),
            ),
        ),
        _one(
            "gov_services_directory",
            "myGov's government services directory",
            "https://my.gov.au/en/services",
            "finding the right Australian Government service for anything else",
        ),
    ]
}


def directory_for_prompt() -> str:
    return "\n".join(f"- {a.id}: {a.name} ({a.covers})" for a in AGENCIES.values())
