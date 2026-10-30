from askoz.retrieval.vocabulary import abbreviate, with_abbreviations


def test_full_names_become_the_pages_abbreviations() -> None:
    question = "How do I get a Tax File Number on a visa?"
    assert abbreviate(question) == "How do I get a TFN on a visa?"
    assert abbreviate("tax file numbers and ABNs") == "TFN and ABNs"


def test_abbreviated_queries_are_added_after_the_originals() -> None:
    queries = ["apply for a tax file number", "TFN for visa holders", "what is GST"]
    assert with_abbreviations(queries) == [*queries, "apply for a TFN"]
