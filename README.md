# 飞虹智忆 · qianhong-agent

> CockroachDB × AWS Hackathon — [Build with Agentic Memory](https://cockroachdb-ai.devpost.com/)

**千古飞虹**（[`../bridge`](../bridge)）古桥数字博物馆的 AI 档案员。CockroachDB 作为唯一记忆源，AWS Lambda + Bedrock 驱动推理，bridge 博物馆浏览轨迹实时写入 Agent 记忆。

📋 **完整提交指南**：[`docs/HACKATHON.md`](docs/HACKATHON.md)

---

## 架构概览

```
bridge/（博物馆）  ──bridge-agent.js──→  qianhong-agent/（档案员 API）
                                              │
                                              ├─ Amazon Bedrock（Claude）
                                              ├─ AWS Lambda + API Gateway
                                              └─ CockroachDB（记忆 + 向量）
```

## Hackathon 工具覆盖

| 工具 | 状态 | 文档 |
|------|------|------|
| Distributed Vector Indexing | ✅ schema + import | `db/schema.sql` |
| Managed MCP Server | ✅ 调试文档 | [`docs/MCP.md`](docs/MCP.md) |
| ccloud CLI | ✅ Agent tool | `agent/tools/ccloud_tool.py` |
| Agent Skills | ✅ 集成说明 | [`docs/SKILLS.md`](docs/SKILLS.md) |
| AWS Bedrock | ✅ `LLM_MODE=bedrock` | `.env.example` |
| AWS Lambda | ✅ SAM 模板 | `infra/template.yaml` |
| Amazon S3 | ✅ SAM 模板 | `infra/template.yaml` |

---

## 快速开始（本地开发）

```bash
cd qianhong-agent
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m api.main
```

- Agent UI：http://127.0.0.1:8787/
- bridge 博物馆：http://127.0.0.1:8080/（另开终端 `cd ../bridge && python3 -m http.server 8080`）
- 自检：http://127.0.0.1:8787/api/hackathon/checklist

默认 `STORAGE_MODE=json` 无需 CRDB/AWS 即可演示核心流程。

---

## Hackathon 生产模式

### CockroachDB Cloud + 向量索引

```bash
docker compose up -d   # 或 CRDB Cloud 连接串
export STORAGE_MODE=cockroach
export DATABASE_URL="postgresql://root@localhost:26257/defaultdb?sslmode=disable"
python scripts/import_bridge_data.py
python -m api.main
```

### AWS Bedrock

```bash
LLM_MODE=bedrock
AWS_REGION=us-east-1
aws configure   # 或环境变量
```

### AWS Lambda 部署

```bash
cd infra && sam build && sam deploy --guided
```

---

## 核心能力（不止对话）

| 能力 | 说明 |
|------|------|
| **浏览记忆** | bridge 图谱/地图/档案点击 → `exploration_events` |
| **个人档案** | 已了解 N/34 座桥，左侧面板可视化 |
| **研学路线** | 「规划宋代桥梁路线」→ 多站任务 → 「继续」推进 |
| **向量检索** | CRDB 模式语义搜索古桥知识 |
| **ccloud 运维** | 问「集群状态」→ ccloud CLI 查询 |

---

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/hackathon/checklist` | 提交自检 |
| POST | `/api/chat` | Agent 对话 |
| POST | `/api/events` | bridge 浏览事件 |
| GET | `/api/dossier/{session_id}` | 个人档案 |
| GET | `/api/cluster/status` | ccloud CLI 集群状态 |

---

## 项目结构

```
qianhong-agent/
├── agent/              # 记忆、检索、研学路线、ccloud tool
├── api/                # FastAPI + Lambda handler
├── db/schema.sql       # CockroachDB Agentic Memory
├── docs/               # HACKATHON / MCP / SKILLS
├── infra/template.yaml # AWS SAM
├── scripts/            # bridge 数据导入 + embedding
└── web/                # 国风 Chat UI
```

---

## License

MIT
