CREATE TABLE IF NOT EXISTS agent_memory (
    tenant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    kind VARCHAR(8) NOT NULL CHECK (kind IN ('short', 'long')),
    namespace VARCHAR(64) NOT NULL,
    memory_key VARCHAR(64) NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, user_id, kind, namespace, memory_key)
);
CREATE INDEX IF NOT EXISTS ix_agent_memory_expiry ON agent_memory(expires_at);
