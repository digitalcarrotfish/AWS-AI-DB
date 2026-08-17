# 千古飞虹 · 飞虹智忆

> CockroachDB × AWS Hackathon — [Build with Agentic Memory](https://cockroachdb-ai.devpost.com/)

**千古飞虹**：双语古桥数字博物馆（地图 / 档案 / 3D / 知识图谱）  
**飞虹智忆**：CockroachDB 驱动的 AI 档案员 —— 浏览轨迹、对话与研学路线写入同一记忆层，AWS Lambda + Bedrock 推理

📋 提交指南：[`docs/HACKATHON.md`](docs/HACKATHON.md)  
🧠 记忆层说明：[`docs/MEMORY.md`](docs/MEMORY.md)  
☁️ AWS（S3 / Bedrock）：[`docs/AWS.md`](docs/AWS.md)

---

## 仓库结构

```
AWS-AI-DB/
├── index.html … knowledge.html   # 博物馆静态站
├── data/                         # 古桥 JSON（博物馆 + Agent 共用）
├── assets/                       # i18n、bridge-agent、本地 AI、背景音乐
├── agent/                        # 记忆、检索、研学、ccloud tool
├── api/                          # FastAPI + Lambda handler
├── db/schema.sql                 # CockroachDB Agentic Memory
├── web/                          # Agent Chat UI
├── docs/                         # HACKATHON / MCP / SKILLS
├── infra/template.yaml           # AWS SAM
└── scripts/import_bridge_data.py # 导入 + embedding
```

---

## 一键本地运行（推荐）

博物馆与 Agent **同域托管**，共享 `localStorage` 会话，避免跨端口记忆断裂：

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m api.main
```

| 入口 | URL |
|------|-----|
| 博物馆封面 | http://127.0.0.1:8787/ |
| 图鉴地图 | http://127.0.0.1:8787/museum.html |
| 档案员 | http://127.0.0.1:8787/agent/ |
| 自检清单 | http://127.0.0.1:8787/api/hackathon/checklist |

默认本地可跑通「浏览 → 记忆 → 对话」。讲解接真模型见 [`docs/LLM.md`](docs/LLM.md)（Kimi / DeepSeek）。

Demo 路径：地图点开赵州桥 →「问档案员」→ 左侧出现浏览轨迹与档案进度。

### 仅预览静态博物馆（可选）

```bash
python3 -m http.server 8080
```

静态预览下 `bridge-agent.js` 会自动把 API 指到 `http://127.0.0.1:8787`（需另开 Agent 进程）。正式联调请用上面的同域方式。

- 天地图 key：复制 `config.example.js` → `config.js`
- UI 中英切换：`localStorage` 键 `gaoqiao_lang`
- 数据路径：`BRIDGE_DATA_DIR=data`

---

## Hackathon 工具覆盖

| 工具 | 说明 | 文档 |
|------|------|------|
| Distributed Vector Indexing | `bridge_embeddings` + VECTOR INDEX | `db/schema.sql` |
| Managed MCP Server | Cursor 只读调试记忆表 | [`docs/MCP.md`](docs/MCP.md) |
| ccloud CLI | Agent 可调用集群状态 | `agent/tools/ccloud_tool.py` |
| Agent Skills | Schema / 运维规范 | [`docs/SKILLS.md`](docs/SKILLS.md) |
| Amazon S3 | 扫桥存证 + 研学报告 | [`docs/AWS.md`](docs/AWS.md) |
| Kimi / DeepSeek | `LLM_MODE=openai` | [`docs/LLM.md`](docs/LLM.md) |
| Amazon Bedrock | `LLM_MODE=bedrock` | [`docs/AWS.md`](docs/AWS.md) |
| AWS Lambda + API GW | SAM 模板 | `infra/template.yaml` |

### CockroachDB 生产模式

```bash
docker compose up -d
export STORAGE_MODE=cockroach
export DATABASE_URL="postgresql://root@localhost:26257/defaultdb?sslmode=disable"
python scripts/import_bridge_data.py
python -m api.main
```

### AWS Lambda

```bash
cd infra && sam build && sam deploy --guided
```

---

## 核心能力（记忆驱动，不只对话）

| 能力 | 说明 |
|------|------|
| **浏览记忆** | 地图/档案/3D/图谱 → `exploration_events` |
| **我的档案** | 「我的档案」聚合已探索桥梁、轨迹与推荐 |
| **推荐下一座** | 按已看朝代/桥型/地域推荐未探索桥梁 |
| **足迹研学** | 「根据浏览规划研学路线」→ 多站任务；「继续」推进 |
| **讲解延伸** | 介绍某桥后附「尚未探索的相关桥」 |
| **结构化对比** | 「对比赵州桥和卢沟桥」输出对照表 |
| **ccloud 运维** | 问「集群状态」→ ccloud CLI |

Demo：http://127.0.0.1:8787/museum.html → 右下角悬浮「档案员」→「扫桥」上传 `桥/赵州桥 外观图.jpg` 或摄像头拍照 → 识别写入记忆 → 对话「讲解此桥」。


| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/hackathon/checklist` | 提交自检 |
| POST | `/api/chat` | Agent 对话 |
| POST | `/api/chat/stream` | SSE 白盒对话：会话→路由→向量检索→模型→持久化 |
| POST | `/api/events` | 博物馆浏览事件 |
| GET | `/api/dossier/{session_id}` | 个人档案 |
| GET | `/api/cluster/status` | ccloud CLI 集群状态 |

---

## License

MIT
