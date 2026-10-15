# AskOz

An independent AI assistant that answers questions about Australian government
services using only official `.gov.au` sources, with a citation for every answer.

> AskOz is not affiliated with, endorsed by, or operated by the Australian Government.

## Local setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker Desktop.

```bash
cp .env.example .env
docker compose up -d
uv sync
uv run askoz doctor
```

## Checks

```bash
uv run ruff format && uv run ruff check && uv run pyright && uv run pytest
uv run pytest -m integration   # needs docker compose services running
```

## Retrieval quality

`eval/golden.yaml` holds real-world questions with the pages that answer them.
Before merging any change to crawling, cleaning, chunking, embeddings or search:

```bash
uv run askoz eval --check        # fails if hit@5 drops versus eval/baseline.json
```

If a change is an improvement, update the baseline in the same commit with
`uv run askoz eval --save-baseline`. (This runs locally for now: it needs the
search index, which CI doesn't have yet.)

## About AskOzBot (for website operators)

If you've seen `AskOzBot` in your server logs: it's the crawler for this project.
It reads public pages from official Australian government websites so AskOz can
answer questions with citations that link back to the original page.

- Obeys `robots.txt`, including `Disallow` rules and `Crawl-delay`
- Sends at most one request at a time per site, 2 seconds apart or slower
- Only fetches public pages; never logs in, submits forms or runs searches
- User-Agent: `Mozilla/5.0 (compatible; AskOzBot/0.1; +<this page>; <contact email>)`

To ask us to slow down, exclude pages or stop, email the address in the
User-Agent, or block `AskOzBot` in your `robots.txt`.
