-- qianhong-agent CockroachDB schema
-- Hackathon: Agentic Memory + Distributed Vector Indexing

CREATE DATABASE IF NOT EXISTS qianhong;
SET DATABASE = qianhong;

-- 古桥结构化知识（来自 bridge/data/bridges.json）
CREATE TABLE IF NOT EXISTS bridges (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        STRING NOT NULL UNIQUE,
  dynasty     STRING,
  year        INT,
  province    STRING,
  city        STRING,
  lon         FLOAT8,
  lat         FLOAT8,
  length      FLOAT8,
  span        FLOAT8,
  width       FLOAT8,
  bridge_type STRING,
  material    STRING,
  protection  STRING,
  poetry      STRING,
  intro       STRING,
  raw_json    JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bridges_dynasty ON bridges (dynasty);
CREATE INDEX IF NOT EXISTS idx_bridges_type ON bridges (bridge_type);

-- 文化扩展（来自 bridge/data/poetry-culture.json）
CREATE TABLE IF NOT EXISTS bridge_culture (
  bridge_id         UUID PRIMARY KEY REFERENCES bridges(id) ON DELETE CASCADE,
  anecdote          STRING,
  poetry_refs       STRING,
  cultural_insight  STRING
);

-- 向量知识层（Bedrock Titan 或开发回退 embedding）
CREATE TABLE IF NOT EXISTS bridge_embeddings (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bridge_id    UUID NOT NULL REFERENCES bridges(id) ON DELETE CASCADE,
  dynasty      STRING,
  content_type STRING NOT NULL,
  content_text STRING NOT NULL,
  embedding    VECTOR(1024),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (bridge_id, content_type)
);

CREATE VECTOR INDEX IF NOT EXISTS idx_bridge_embeddings_vector
  ON bridge_embeddings (embedding vector_cosine_ops);

-- Agent 会话与多轮对话
CREATE TABLE IF NOT EXISTS sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  focus_bridge_id UUID REFERENCES bridges(id),
  user_label      STRING,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role       STRING NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content    STRING NOT NULL,
  sources    STRING[],
  mode       STRING,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, created_at);

-- 长期记忆摘要（跨会话压缩）
CREATE TABLE IF NOT EXISTS user_memory (
  session_id UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
  summary    STRING NOT NULL,
  interests  STRING[],
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 多步 Agent 任务状态
CREATE TABLE IF NOT EXISTS agent_tasks (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  task_type  STRING NOT NULL,
  status     STRING NOT NULL DEFAULT 'pending',
  payload    JSONB,
  result     JSONB,
  step       INT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 工具调用审计（MCP / 检索 / ccloud CLI）
CREATE TABLE IF NOT EXISTS tool_calls (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id),
  tool_name  STRING NOT NULL,
  input      JSONB,
  output     JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls (session_id, created_at);

-- bridge 博物馆浏览轨迹（图谱 / 地图 / 档案页）
CREATE TABLE IF NOT EXISTS exploration_events (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  event_type STRING NOT NULL,
  source     STRING NOT NULL,
  bridge_id  UUID REFERENCES bridges(id),
  bridge_name STRING,
  meta       JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_exploration_session ON exploration_events (session_id, created_at);
