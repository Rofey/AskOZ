-- One row per crawled URL: the latest fetch of that page.
-- The HTML itself lives in blob storage (see askoz.storage); the database keeps
-- metadata, which stays small and fast to query.
CREATE TABLE raw_pages (
    url             text PRIMARY KEY,           -- canonical URL (see askoz.crawl.urls)
    source          text        NOT NULL,       -- key in askoz.crawl.sources.SOURCES
    http_status     smallint    NOT NULL,
    content_type    text,
    content_hash    text        NOT NULL,       -- sha256 of the raw body
    blob_key        text        NOT NULL,
    etag            text,                       -- for conditional re-fetches later
    last_modified   text,
    sitemap_lastmod timestamptz,                -- what the site's sitemap claimed
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    fetched_at      timestamptz NOT NULL DEFAULT now(),
    changed_at      timestamptz NOT NULL DEFAULT now()  -- last time content_hash changed
);

CREATE INDEX raw_pages_source_idx ON raw_pages (source);
-- Phase 3 ingestion asks "which pages changed since my last run?"
CREATE INDEX raw_pages_changed_at_idx ON raw_pages (changed_at);
