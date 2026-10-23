# AskOz API image, run on Google Cloud Run.
#
# Two stages: "build" has the tools to install dependencies and download the
# embedding model; "runtime" copies only the results, so the final image has
# no compilers, caches or uv, which means a smaller image and less to attack.

# --- build ---------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS build

# uv, pinned, copied from its official image rather than installed with pip.
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

# Compile .py to .pyc now (faster cold starts) and copy files into the venv
# instead of hard-linking (the cache is a different filesystem).
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, the project's own code second. Docker caches each step, so
# editing a .py file re-runs only the cheap last steps, not the ~2-minute install.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY db ./db
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Bake the embedding model into the image. Downloading it at startup would slow
# every cold start and make serving depend on Hugging Face being up.
ENV ASKOZ_MODELS_DIR=/app/models
RUN .venv/bin/python -c "from askoz.index import embed_model; embed_model().get_text_embedding('warm up')"

# --- runtime -------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

# Never run as root: if the app is ever compromised, the attacker is a nobody.
RUN useradd --system --uid 10001 --no-create-home askoz

WORKDIR /app
COPY --from=build --chown=askoz:askoz /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ASKOZ_ENV=prod \
    ASKOZ_MODELS_DIR=/app/models \
    HF_HUB_OFFLINE=1

USER askoz

# Cloud Run tells the container which port to listen on via $PORT (8080).
EXPOSE 8080
CMD ["sh", "-c", "exec askoz serve --host 0.0.0.0 --port ${PORT:-8080}"]
