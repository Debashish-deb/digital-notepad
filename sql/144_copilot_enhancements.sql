-- Phase A/B: FTS on chunks, chat session memory, copilot feedback.

-- Full-text search on lab/project chunks (hybrid retrieval)
CREATE INDEX IF NOT EXISTS idx_rag_chunk_text_fts
  ON rag.document_chunk
  USING GIN (to_tsvector('english', coalesce(chunk_text, '')));

-- Conversation memory (per user, optional project scope)
CREATE TABLE IF NOT EXISTS platform.chat_session (
  session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email text NOT NULL,
  project_codes text[] NOT NULL DEFAULT '{}',
  title text,
  summary text NOT NULL DEFAULT '',
  turn_count integer NOT NULL DEFAULT 0,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_session_user_updated
  ON platform.chat_session (user_email, updated_at DESC);

CREATE TABLE IF NOT EXISTS platform.chat_turn (
  turn_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES platform.chat_session(session_id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content text NOT NULL,
  intent text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_turn_session
  ON platform.chat_turn (session_id, created_at);

-- User feedback for eval / self-learning pipeline
CREATE TABLE IF NOT EXISTS platform.copilot_feedback (
  feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email text NOT NULL,
  session_id uuid REFERENCES platform.chat_session(session_id) ON DELETE SET NULL,
  query_text text NOT NULL,
  answer_excerpt text,
  rating smallint CHECK (rating BETWEEN -1 AND 1),
  correction_note text,
  intent text,
  project_codes text[] NOT NULL DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_copilot_feedback_created
  ON platform.copilot_feedback (created_at DESC);
