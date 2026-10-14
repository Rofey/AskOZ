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
