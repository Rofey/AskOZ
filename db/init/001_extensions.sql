-- Runs automatically the first time the Postgres container starts.
-- pgvector adds the `vector` column type plus similarity operators
-- (<=> cosine distance, <-> L2 distance, <#> inner product) and HNSW indexes.
CREATE EXTENSION IF NOT EXISTS vector;
