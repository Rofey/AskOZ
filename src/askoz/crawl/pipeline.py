"""Persist crawled pages: HTML to blob storage, metadata to Postgres."""

import gzip
import hashlib

import psycopg
import scrapy

from askoz.config import get_settings
from askoz.crawl.spiders import RawPage
from askoz.db import connect
from askoz.storage import LocalBlobStore

UPSERT = """
INSERT INTO raw_pages AS p
    (url, source, http_status, content_type, content_hash, blob_key,
     etag, last_modified, sitemap_lastmod)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (url) DO UPDATE SET
    source          = EXCLUDED.source,
    http_status     = EXCLUDED.http_status,
    content_type    = EXCLUDED.content_type,
    content_hash    = EXCLUDED.content_hash,
    blob_key        = EXCLUDED.blob_key,
    etag            = EXCLUDED.etag,
    last_modified   = EXCLUDED.last_modified,
    sitemap_lastmod = EXCLUDED.sitemap_lastmod,
    fetched_at      = now(),
    -- In ON CONFLICT, `p` is the existing row: only bump changed_at if the content differs.
    changed_at      = CASE WHEN p.content_hash IS DISTINCT FROM EXCLUDED.content_hash
                           THEN now() ELSE p.changed_at END
"""


class RawPagePipeline:
    conn: psycopg.Connection

    def open_spider(self, spider: scrapy.Spider) -> None:
        self.conn = connect(autocommit=True)
        self.store = LocalBlobStore(get_settings().blob_dir)

    def close_spider(self, spider: scrapy.Spider) -> None:
        self.conn.close()

    def process_item(self, item: RawPage, spider: scrapy.Spider) -> RawPage:
        digest = hashlib.sha256(item.body).hexdigest()
        # Content-addressed key: identical HTML is stored once, however many URLs serve it.
        key = f"raw/{item.source}/{digest[:2]}/{digest}.html.gz"
        if not self.store.exists(key):
            self.store.put(key, gzip.compress(item.body))

        previous = self.conn.execute(
            "SELECT content_hash FROM raw_pages WHERE url = %s", (item.url,)
        ).fetchone()
        self.conn.execute(
            UPSERT,
            (
                item.url,
                item.source,
                item.http_status,
                item.content_type,
                digest,
                key,
                item.etag,
                item.last_modified,
                item.sitemap_lastmod,
            ),
        )

        stats = spider.crawler.stats
        assert stats is not None
        if previous is None:
            stats.inc_value("askoz/pages_new")
        elif previous[0] != digest:
            stats.inc_value("askoz/pages_changed")
        else:
            stats.inc_value("askoz/pages_unchanged")
        return item
