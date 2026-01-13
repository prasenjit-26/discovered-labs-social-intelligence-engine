-- Level 0 Requirement: Entity Mentions with Context

CREATE TABLE IF NOT EXISTS entity_mentions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    entity_name TEXT NOT NULL REFERENCES entities(name),
    post_id TEXT NOT NULL REFERENCES posts(id),
    variation_used TEXT NOT NULL,
    confidence FLOAT,
    context TEXT, -- The surrounding text or full sentence
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups by entity
CREATE INDEX IF NOT EXISTS idx_entity_mentions_name ON entity_mentions(entity_name);
