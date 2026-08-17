# 记忆层怎么做的（对照 Hackathon）

> Devpost：[CockroachDB × AWS — Build with Agentic Memory](https://cockroachdb-ai.devpost.com/)

## 一句话

**浏览 / 对话 / 研学 / 向量检索 / 扫桥** 全部落到同一套持久记忆上。开发默认可 `json`；提交与生产用 **CockroachDB**（本仓库已切通本地单节点）。

---

## 记忆分层（对应评审「Agentic Memory Design」）

| 层 | 表 / 存储 | 写入时机 | Agent 怎么用 |
|----|-----------|----------|--------------|
| 知识 | `bridges` + `bridge_culture` | `import_bridge_data.py` | 档案讲解、对比、列表 |
| 向量 | `bridge_embeddings` + **VECTOR INDEX** | 导入时 `embed_text` | 语义检索（如「敞肩石拱桥」） |
| 情景 | `exploration_events` + `messages` | 浏览/扫桥/对话 | 「您刚关注了…」、档案进度 |
| 语义 | `user_memory` | 每轮对话后压缩 | 兴趣标签、推荐 |
| 程序 | `agent_tasks` | 研学规划 /「继续」 | 多站断点续跑 |
| 审计 | `tool_calls` | 检索 / 识别 / ccloud | MCP 可查、可演示 |

Schema：[`db/schema.sql`](../db/schema.sql)

---

## 双模式实现

```text
STORAGE_MODE=json      →  JsonMemoryStore（data/sessions/*.json，开箱演示）
STORAGE_MODE=cockroach →  CockroachMemoryStore（psycopg → CRDB）
```

入口：`agent/storage.py` → `get_store()`

---

## 已完成的本地 CRDB 步骤（本机）

1. 安装并启动单节点（无 Docker 时用 Homebrew）：

```bash
brew install cockroachdb/tap/cockroach
cockroach start-single-node \
  --store=./.crdb-data \
  --listen-addr=localhost:26257 \
  --http-addr=localhost:26258 \
  --insecure --advertise-addr=localhost:26257
```

2. `.env`（勿提交）：

```bash
STORAGE_MODE=cockroach
DATABASE_URL=postgresql://root@localhost:26257/defaultdb?sslmode=disable
BRIDGE_DATA_DIR=data
LLM_MODE=openai
# OPENAI_API_KEY=sk-... 见 docs/LLM.md；未填则自动回退检索
```

3. 建库 + 导入 34 桥 + 向量：

```bash
source .venv/bin/activate
python scripts/import_bridge_data.py
# → vector_index.enabled = true
# → 已导入 34 座桥梁；embeddings ~100+；idx_bridge_embeddings_vector
```

4. 启动 API：

```bash
python -m api.main
# 打开 http://127.0.0.1:8787/api/hackathon/checklist
# 期望：storage_mode=cockroach，vector_indexing.active=true
```

5. 自检 SQL：

```sql
SET DATABASE = qianhong;
SELECT count(*) FROM bridges;            -- 34
SELECT count(*) FROM bridge_embeddings;  -- >0
SHOW INDEXES FROM bridge_embeddings;     -- idx_bridge_embeddings_vector
SELECT * FROM exploration_events ORDER BY created_at DESC LIMIT 5;
```

Admin UI：http://localhost:26258

---

## 数据流（博物馆 → 记忆）

```text
悬浮助手 / 地图 / 档案 / 扫桥
    │  track() / POST /api/events / POST /api/identify
    ▼
exploration_events  (+ focus_bridge)
    │
POST /api/chat → orchestrator
    ├─ 读 events / user_memory / study_path
    ├─ search_bridges（CRDB：embedding <=> query）
    ├─ 写 messages + user_memory + agent_tasks
    └─ 讲解：Kimi（LLM_MODE=openai）或 Bedrock；失败回退检索
```

---

## 对照比赛「至少 2 个 Cockroach 工具」

| 工具 | 状态 | 你怎么演示 |
|------|------|------------|
| **Distributed Vector Indexing** | ✅ 已导入 + 索引 | 问语义问题；SQL 看 `bridge_embeddings` |
| **Managed MCP Server** | 需 Cloud | [`MCP.md`](./MCP.md) — Console → Connect → MCP → Cursor |
| **ccloud CLI** | 代码就绪 | [`CCLOUD.md`](./CCLOUD.md) — `bash scripts/install_ccloud.sh` |
| **Agent Skills** | 可选 | `npx skills add cockroachlabs/cockroachdb-skills -y` |

**建议提交组合**：Vector Indexing（已亮）+ **Managed MCP**（或 ccloud）。

---

## 对照「至少 1 个 AWS」

详见 [`docs/AWS.md`](./AWS.md)。

| 服务 | 配置 | 说明 |
|------|------|------|
| **Amazon S3**（推荐先开） | `S3_BUCKET` + AWS 凭证 | 扫桥存证、`POST /api/reports/export` |
| Bedrock | `LLM_MODE=bedrock` + 凭证 | 讲解生成 |
| Lambda + API GW + S3 | `infra/template.yaml` | `sam build && sam deploy --guided` |

自检：`/api/aws/status`、`/api/hackathon/checklist`（`requirement_aws_met`）。

本地无 AWS 时用 `LLM_MODE=retrieval` 仍可完整演示记忆层；**提交前**至少打开 S3 或 Bedrock 之一。

---

## 提交前清单

- [x] CockroachDB 持久记忆（非玩具 JSON）
- [x] Vector index + 导入脚本
- [ ] **≥1 AWS**：`S3_BUCKET` 或 `LLM_MODE=bedrock`（见 [`docs/AWS.md`](./AWS.md)）
- [ ] CockroachDB Cloud 集群（可选但加分）+ MCP 接到 Cursor
- [ ] 安装 `ccloud` 并演示「集群状态」
- [ ] （可选）Bedrock / Lambda 部署
- [ ] Demo 视频：地图浏览 → 扫桥/问档案员 → SQL/MCP 查 `exploration_events`
- [ ] 公开仓库 + MIT LICENSE + README

---

## 常用命令速查

```bash
# 启 CRDB（若已停）
cockroach start-single-node --store=./.crdb-data \
  --listen-addr=localhost:26257 --http-addr=localhost:26258 \
  --insecure --advertise-addr=localhost:26257

# 启 API
source .venv/bin/activate && python -m api.main

# 重新导入
python scripts/import_bridge_data.py
```
