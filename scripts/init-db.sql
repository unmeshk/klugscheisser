-- Grant necessary privileges to the klugbot user
GRANT USAGE ON SCHEMA public TO klugbot;
GRANT CREATE ON SCHEMA public TO klugbot;
GRANT ALL ON ALL TABLES IN SCHEMA public TO klugbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO klugbot;

-- Create the knowledge_entries table if it doesn't exist
CREATE TABLE IF NOT EXISTS knowledge_entries (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    slack_username TEXT NOT NULL,
    slack_timestamp TEXT NOT NULL,
    source_url TEXT,
    tags TEXT[],
    additional_metadata JSONB,
    embedding FLOAT[]
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_tags ON knowledge_entries USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_created ON knowledge_entries (created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_slack_username ON knowledge_entries (slack_username);