-- Managed Postgres (Neon/Supabase) doesn't run db/init, so production
-- enables the extension through migrations like everything else.
CREATE EXTENSION IF NOT EXISTS vector;
