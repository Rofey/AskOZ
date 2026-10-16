import pytest

from askoz.answer.smalltalk import out_of_scope_text, smalltalk_reply


@pytest.mark.parametrize(
    "text", ["Hello", "HEllo", "hi!", "Hey there", "g'day", "Good morning AskOz", "  hiya :)"]
)
def test_greetings_get_a_friendly_reply(text: str) -> None:
    reply = smalltalk_reply(text)
    assert reply is not None and reply.startswith("Hi! I'm AskOz")


@pytest.mark.parametrize("text", ["thanks", "Thank you so much!", "cheers", "ta"])
def test_thanks(text: str) -> None:
    reply = smalltalk_reply(text)
    assert reply is not None and reply.startswith("You're welcome")


@pytest.mark.parametrize(
    "text",
    ["hello, how do I get a TFN?", "hi can I work on a student visa", "thanks but what about GST"],
)
def test_questions_with_a_greeting_still_get_answered(text: str) -> None:
    assert smalltalk_reply(text) is None


def test_coverage_text_is_built_from_live_sources() -> None:
    text = out_of_scope_text()
    assert "visas and citizenship" in text and "tax and super" in text
    assert "Medicare" not in text  # we only cover the tax side of Medicare
