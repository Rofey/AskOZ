"""Greetings and thanks: friendly replies with no Claude call.

"Hello" isn't an off-topic question, and treating it as one ("I can only help
with...") feels cold. A short pattern catches the common cases for free;
anything else, however short, still goes to the planner.
"""

import re

from askoz.answer.coverage import topics_phrase

_GREETING = re.compile(
    r"(hi|hiya|hello|hey|g'?day|good (morning|afternoon|evening)|howdy|yo)"
    r"( there| askoz)?",
    re.IGNORECASE,
)
_THANKS = re.compile(
    r"(thanks|thank you|thank u|ta|cheers|thx|ty)( (so|very) much| a lot)?( askoz)?",
    re.IGNORECASE,
)


def _bare(text: str) -> str:
    return re.sub(r"[\s!.,?:)(\-]+$", "", text.strip())


def smalltalk_reply(text: str) -> str | None:
    """A reply if `text` is only a greeting or thanks, else None."""
    bare = _bare(text)
    if _GREETING.fullmatch(bare):
        return (
            "Hi! I'm AskOz. I answer questions using official Australian Government "
            "information, with a link to every source.\n\n"
            f"Right now I can help with {topics_phrase()}. What would you like to know?"
        )
    if _THANKS.fullmatch(bare):
        return f"You're welcome! Ask me anything else about {topics_phrase()}."
    return None


def out_of_scope_text() -> str:
    return (
        "I can only help with questions about Australian Government information. "
        f"Right now that's {topics_phrase()}."
    )
