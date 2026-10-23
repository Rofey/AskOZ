"""The search index: embedding model and pgvector store, shared by ingestion and retrieval.

Ingestion and search must use the *same* embedding model. Vectors from
different models live in different spaces, so comparing them is meaningless.
"""

import os
from typing import TypedDict

from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy.engine import make_url

from askoz.config import get_settings

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


class PgUrls(TypedDict):
    connection_string: str
    async_connection_string: str


def pg_urls() -> PgUrls:
    """SQLAlchemy URLs for LlamaIndex's Postgres stores, derived from DATABASE_URL.

    Their `from_params(host=..., port=...)` formats a URL by hand, which breaks
    on Unix sockets (how Cloud Run reaches Cloud SQL) and on passwords with
    URL-special characters. Parsing and re-rendering keeps both intact.
    """
    url = make_url(get_settings().database_url)

    def render(driver: str) -> str:
        return url.set(drivername=driver).render_as_string(hide_password=False)

    return {
        "connection_string": render("postgresql+psycopg2"),
        "async_connection_string": render("postgresql+asyncpg"),
    }


def embed_model() -> FastEmbedEmbedding:
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    return FastEmbedEmbedding(
        model_name=EMBED_MODEL, cache_dir=str(get_settings().models_dir.resolve())
    )


def vector_store() -> PGVectorStore:
    return PGVectorStore.from_params(
        **pg_urls(),
        table_name="chunks",  # LlamaIndex prefixes this: the table is `data_chunks`
        embed_dim=EMBED_DIM,
        hybrid_search=True,  # also maintains a tsvector column for keyword search
        text_search_config="english",
        hnsw_kwargs={
            "hnsw_m": 16,
            "hnsw_ef_construction": 64,
            "hnsw_ef_search": 40,
            "hnsw_dist_method": "vector_cosine_ops",
        },
    )
