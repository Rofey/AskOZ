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
from collections.abc import Iterator
from dataclasses import dataclass

from llama_index.core import Document
from llama_index.core.ingestion import DocstoreStrategy, IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.storage.docstore.postgres import PostgresDocumentStore
from psycopg import sql

from askoz.config import get_settings
from askoz.crawl.sources import SOURCES
from askoz.db import connect
from askoz.index import embed_model, pg_params, vector_store
from askoz.ingest.clean import clean_html
from askoz.ingest.transforms import MergeSmallSections
from askoz.logging import get_logger
from askoz.storage import LocalBlobStore

log = get_logger(__name__)

CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 64
MIN_SECTION_CHARS = 300
BATCH_SIZE = 50  # documents per pipeline run; bounds memory and gives progress

# Metadata keys that are for us, not for the embedding model. Everything else
# (title, agency, header_path) is prepended to the chunk text before embedding,
# so "15% tax rate" in a chunk under "Working holiday makers" embeds as being
# about working holiday makers.
_NOT_EMBEDDED = ["url", "source", "last_updated"]
_NOT_FOR_LLM = ["source"]


@dataclass
class IngestStats:
    pages: int = 0
    skipped_no_content: int = 0
    failed: int = 0
    out_of_scope: int = 0  # stored pages the source no longer includes
    chunks_written: int = 0


def build_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        transformations=[
            MarkdownNodeParser(),
            MergeSmallSections(min_chars=MIN_SECTION_CHARS),
            SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP),
            embed_model(),
        ],
        docstore=PostgresDocumentStore.from_params(**pg_params(), table_name="docstore"),
        vector_store=vector_store(),
        docstore_strategy=DocstoreStrategy.UPSERTS,
    )


def load_documents(
    stats: IngestStats, *, source: str | None = None, limit: int | None = None
) -> Iterator[Document]:
    store = LocalBlobStore(get_settings().blob_dir)
    query = (
        "SELECT url, source, blob_key FROM raw_pages"
        " WHERE http_status = 200 AND (%(source)s::text IS NULL OR source = %(source)s)"
        " ORDER BY url LIMIT %(limit)s"
    )
    with connect() as conn:
        rows = conn.execute(query, {"source": source, "limit": limit}).fetchall()

    for url, page_source, blob_key in rows:
        stats.pages += 1
        if not SOURCES[page_source].allows(url):
            # Crawled before the source's scope was narrowed (e.g. the AEC's
            # statistics tables). The current scope always wins.
            stats.out_of_scope += 1
            continue
        try:
            page = clean_html(gzip.decompress(store.get(blob_key)), url)
        except Exception:
            # One odd page must not stop the whole run (nightly updates would
            # silently stall). Count it, log it with the URL, move on.
            stats.failed += 1
            log.exception("page_clean_failed", url=url)
            continue
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
                # No fetch time here: the docstore hashes metadata too, so a
                # timestamp would make every re-crawled page look changed and
                # get re-embedded even when its text is identical.
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
