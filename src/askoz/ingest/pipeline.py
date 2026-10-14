"""LlamaIndex ingestion: clean pages -> chunks -> embeddings -> pgvector.

The flow for each page:

    raw_pages row + HTML blob
      -> clean_html()               Markdown with headings
      -> Document(id_=url)          one LlamaIndex Document per page
      -> MarkdownNodeParser         one node per heading section, tagged with header_path
      -> MergeSmallSections         heading-only sections folded into their neighbours
      -> SentenceSplitter           long sections cut to ~512 tokens, 64 overlapping
      -> FastEmbedEmbedding         each chunk becomes a 384-number vector
      -> PGVectorStore              stored with full-text index for hybrid search

The docstore makes re-runs incremental. It remembers a hash of every
Document; unchanged pages are skipped, and changed pages have their old
chunks deleted before the new ones are inserted (DocstoreStrategy.UPSERTS).

The docstore hashes the *Documents*, not the pipeline. If you change how pages
are cleaned or chunked, unchanged pages would still be skipped, so run with
`--rebuild` to re-index everything.
"""

import gzip
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypedDict

from llama_index.core import Document
from llama_index.core.ingestion import DocstoreStrategy, IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from llama_index.storage.docstore.postgres import PostgresDocumentStore
from llama_index.vector_stores.postgres import PGVectorStore
from psycopg import sql

from askoz.config import get_settings
from askoz.crawl.sources import SOURCES
from askoz.db import connect
from askoz.ingest.clean import clean_html
from askoz.ingest.transforms import MergeSmallSections
from askoz.logging import get_logger
from askoz.storage import LocalBlobStore

log = get_logger(__name__)

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 64
MIN_SECTION_CHARS = 300
BATCH_SIZE = 50  # documents per pipeline run; bounds memory and gives progress

# Metadata keys that are for us, not for the embedding model. Everything else
# (title, agency, header_path) is prepended to the chunk text before embedding,
# so "15% tax rate" in a chunk under "Working holiday makers" embeds as being
# about working holiday makers.
_NOT_EMBEDDED = ["url", "source", "fetched_at", "last_updated"]
_NOT_FOR_LLM = ["source", "fetched_at"]


@dataclass
class IngestStats:
    pages: int = 0
    skipped_no_content: int = 0
    chunks_written: int = 0


class PgParams(TypedDict):
    host: str
    port: str
    user: str
    password: str
    database: str


def _pg_params() -> PgParams:
    url = get_settings().database_url
    host = url.hosts()[0]
    return {
        "host": host["host"] or "localhost",
        "port": str(host["port"] or 5432),
        "user": host["username"] or "",
        "password": host["password"] or "",
        "database": (url.path or "").lstrip("/"),
    }


def embed_model() -> FastEmbedEmbedding:
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    return FastEmbedEmbedding(
        model_name=EMBED_MODEL, cache_dir=str(get_settings().models_dir.resolve())
    )


def vector_store() -> PGVectorStore:
    return PGVectorStore.from_params(
        **_pg_params(),
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


def build_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        transformations=[
            MarkdownNodeParser(),
            MergeSmallSections(min_chars=MIN_SECTION_CHARS),
            SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP),
            embed_model(),
        ],
        docstore=PostgresDocumentStore.from_params(**_pg_params(), table_name="docstore"),
        vector_store=vector_store(),
        docstore_strategy=DocstoreStrategy.UPSERTS,
    )


def load_documents(
    stats: IngestStats, *, source: str | None = None, limit: int | None = None
) -> Iterator[Document]:
    store = LocalBlobStore(get_settings().blob_dir)
    query = (
        "SELECT url, source, blob_key, fetched_at FROM raw_pages"
        " WHERE http_status = 200 AND (%(source)s::text IS NULL OR source = %(source)s)"
        " ORDER BY url LIMIT %(limit)s"
    )
    with connect() as conn:
        rows = conn.execute(query, {"source": source, "limit": limit}).fetchall()

    for url, page_source, blob_key, fetched_at in rows:
        stats.pages += 1
        page = clean_html(gzip.decompress(store.get(blob_key)))
        if page is None:
            stats.skipped_no_content += 1
            log.debug("page_skipped_no_content", url=url)
            continue
        yield Document(
            id_=url,
            text=page.text,
            metadata={
                "url": url,
                "title": page.title,
                "source": page_source,
                "agency": SOURCES[page_source].agency,
                "last_updated": page.last_updated.isoformat() if page.last_updated else None,
                "fetched_at": fetched_at.isoformat(),
            },
            excluded_embed_metadata_keys=_NOT_EMBEDDED,
            excluded_llm_metadata_keys=_NOT_FOR_LLM,
        )


def reset_index() -> None:
    """Empty the vector store and docstore so every page is re-processed."""
    with connect() as conn:
        for table in ("data_chunks", "data_docstore"):
            if conn.execute("SELECT to_regclass(%s)", (table,)).fetchone() != (None,):
                # Table names can't be %s parameters; sql.Identifier quotes them safely.
                conn.execute(sql.SQL("TRUNCATE {}").format(sql.Identifier(table)))
    log.info("index_reset")


def ingest(
    *, source: str | None = None, limit: int | None = None, rebuild: bool = False
) -> IngestStats:
    stats = IngestStats()
    if rebuild:
        reset_index()
    pipeline = build_pipeline()
    batch: list[Document] = []

    def flush() -> None:
        nodes = pipeline.run(documents=batch)
        stats.chunks_written += len(nodes)
        log.info("ingest_batch", docs=len(batch), chunks=len(nodes), pages_seen=stats.pages)
        batch.clear()

    for doc in load_documents(stats, source=source, limit=limit):
        batch.append(doc)
        if len(batch) >= BATCH_SIZE:
            flush()
    if batch:
        flush()
    return stats
