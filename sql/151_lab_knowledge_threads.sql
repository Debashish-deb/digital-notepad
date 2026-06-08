-- Lab Knowledge Threads — challenge / correct / refine AI answers (Layer 1)

CREATE SCHEMA IF NOT EXISTS platform;

CREATE TABLE IF NOT EXISTS platform.lab_knowledge_threads (
    thread_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    hypothesis text,
    created_by text,
    status text NOT NULL DEFAULT 'open',
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT lab_knowledge_threads_status_chk CHECK (status IN ('open', 'revised', 'accepted', 'archived'))
);

CREATE TABLE IF NOT EXISTS platform.lab_knowledge_thread_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id uuid NOT NULL REFERENCES platform.lab_knowledge_threads(thread_id) ON DELETE CASCADE,
    event_type text NOT NULL,
    content text,
    response_id uuid,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT lab_knowledge_thread_events_type_chk CHECK (
        event_type IN ('answer', 'challenge', 'challenge_revision', 'accepted', 'comment')
    )
);

CREATE INDEX IF NOT EXISTS idx_lab_knowledge_threads_created_by
    ON platform.lab_knowledge_threads (created_by);
CREATE INDEX IF NOT EXISTS idx_lab_knowledge_thread_events_thread
    ON platform.lab_knowledge_thread_events (thread_id, created_at);
