"""What AskOz can answer right now: the single source of truth.

A source is "live" once it's crawled, indexed and checked with evals; the
`live_sources` setting lists them. Everything that describes coverage (the
planner's rules, referral messages, the referral directory) is built from
here, so making a new source live is a one-line config change.
"""

from askoz.answer.agencies import AGENCIES, Agency
from askoz.config import get_settings
from askoz.crawl.sources import SOURCES, Source


def live_sources() -> list[Source]:
    names = get_settings().live_sources
    unknown = [n for n in names if n not in SOURCES]
    if unknown:
        raise ValueError(f"live_sources has unknown sources: {unknown}")
    return [SOURCES[n] for n in names]


def replaced_referrals() -> set[str]:
    """Referral agencies whose questions a live source now answers."""
    return {s.replaces_referral for s in live_sources() if s.replaces_referral}


def referral_agencies() -> list[Agency]:
    replaced = replaced_referrals()
    return [a for a in AGENCIES.values() if a.id not in replaced]


def coverage_rules() -> str:
    """One line per live source, for the planner prompt."""
    return "\n".join(f"- {s.agency}: {s.covers}" for s in live_sources())


def coverage_note() -> str:
    """Plain-English sentence for users: what AskOz currently covers."""
    agencies = [s.agency for s in live_sources()]
    named = agencies[0] if len(agencies) == 1 else ", ".join(agencies[:-1]) + " and " + agencies[-1]
    return f"It currently covers official information from the {named}."
