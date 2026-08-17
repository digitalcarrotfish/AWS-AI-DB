# CockroachDB × AWS Hackathon 提交指南

> **项目**：千古飞虹（博物馆）+ 飞虹智忆（Agent）— 同一仓库  
> **Devpost**：[cockroachdb-ai.devpost.com](https://cockroachdb-ai.devpost.com/)  
> **截止**：2026-08-18 17:00 EDT

---

## 一句话定位

**为中国古桥数字博物馆配备 CockroachDB 驱动的 AI 档案员** —— 记住浏览轨迹、研学路线与对话，向量语义检索 + 事务状态同一库，部署于 AWS Lambda + Bedrock。

---

## 架构图

```mermaid
flowchart TB
    subgraph Museum["博物馆静态站（仓库根目录）"]
        Map[museum.html 地图]
        Graph[knowledge.html 图谱]
        Detail[bridge-detail.html 档案]
    end

    subgraph SDK["assets/bridge-agent.js"]
        Events[浏览事件上报]
    end

    subgraph AWS["AWS"]
        APIGW[API Gateway HTTP API]
        Lambda[Lambda FastAPI]
        Bedrock[Amazon Bedrock Claude]
        S3[S3 研学报告桶]
    end

    subgraph CRDB["CockroachDB Agentic Memory"]
        KB[(bridges + culture)]
        VEC[(bridge_embeddings 向量索引)]
        EPIS[(messages + exploration_events)]
        SEM[(user_memory + dossier)]
        PROC[(agent_tasks 研学路线)]
        AUDIT[(tool_calls 审计)]
    end

    subgraph DevTools["CockroachDB 工具链"]
        MCP[MCP Server 只读调试]
        CLI[ccloud CLI 集群查询]
        Skills[Agent Skills Schema 规范]
    end

    Map --> Events
    Graph --> Events
    Detail --> Events
    Events --> APIGW --> Lambda
    Lambda --> Bedrock
    Lambda --> CRDB
    Lambda --> S3
    MCP -.-> CRDB
    CLI -.-> Lambda
    Skills -.-> Lambda
```

---

## Hackathon 要求对照

### 必须：CockroachDB 作为持久记忆层 ✅

| 记忆类型 | 表 | 用途 |
|---------|-----|------|
| 知识 | `bridges`, `bridge_culture`, `bridge_embeddings` | 34 座古桥 + 向量 RAG |
| 情景 | `messages`, `exploration_events` | 对话 + bridge 浏览轨迹 |
| 语义 | `user_memory` | 兴趣压缩摘要 |
| 程序 | `agent_tasks` | 研学路线进度 |
| 审计 | `tool_calls` | 检索 / ccloud / MCP 调试 |

### 必须：至少 2 种 CockroachDB 工具 ✅

| 工具 | 本项目用法 | 验证方式 |
|------|-----------|---------|
| **Distributed Vector Indexing** | `bridge_embeddings` + `CREATE VECTOR INDEX` | `scripts/import_bridge_data.py` + 语义检索 |
| **Managed MCP Server** | 开发者 Cursor 查记忆表 | [`docs/MCP.md`](./MCP.md) |
| **ccloud CLI** | `agent/tools/ccloud_tool.py` + 问「集群状态」 | `GET /api/cluster/status` |
| **Agent Skills** | Schema 设计规范 | [`docs/SKILLS.md`](./SKILLS.md) |

### 必须：至少 1 种 AWS 服务 ✅

详见 [`docs/AWS.md`](./AWS.md)。

| AWS 服务 | 用途 | 本地验证 |
|---------|------|----------|
| **Amazon S3** | 扫桥存证 + 研学报告导出 | `S3_BUCKET` → `/api/aws/status` |
| **Amazon Bedrock** | Claude 生成讲解 | `LLM_MODE=bedrock` |
| **AWS Lambda** | Agent API 运行时 | `infra/template.yaml` |
| **API Gateway** | HTTP 入口 | SAM `HttpApi` |

推荐提交路径：**S3 存证**（最快）或 Bedrock 讲解；SAM 部署则三者一起亮。

---

## 博物馆 ↔ Agent 接线

**同域托管**：`python -m api.main` 同时提供博物馆页面与 `/agent/`、`/api/*`。

`assets/bridge-agent.js`：

1. 浏览地图 / 档案 / 3D / 图谱 → `POST /api/events`（去重、会话校验）
2. 「问档案员」→ `/agent/`，携带同一 `qh_session_id`（同域 localStorage）
3. Agent 侧展示浏览轨迹 + 档案进度；仅显式 `autoAsk` 时自动发问

本地只需一个进程：http://127.0.0.1:8787/

---

## 3 分钟 Demo 脚本

| 时间 | 画面 | 话术要点 |
|------|------|---------|
| 0:00 | bridge 地图点赵州桥 | 「博物馆浏览」 |
| 0:30 | 点「问档案员」→ Agent | 「事件写入 CRDB exploration_events」 |
| 1:00 | Agent 对话 + 左栏档案 3/34 | 「记忆驱动行为，不是无状态 Chat」 |
| 1:30 | 「规划宋代桥梁研学路线」→ 继续 | 「agent_tasks 断点续跑」 |
| 2:00 | Cursor MCP 查 exploration_events | 「MCP 只读调试」 |
| 2:30 | 问「数据库集群状态」| 「ccloud CLI 集成」 |

---

## 提交清单

- [x] CockroachDB 本地记忆层（`STORAGE_MODE=cockroach` + 向量索引）— 见 [`MEMORY.md`](./MEMORY.md)
- [ ] 公开 GitHub 仓库（MIT License）
- [ ] README 含一键启动说明
- [ ] Demo URL（Lambda 部署 URL 或录屏 localhost）
- [ ] YouTube/Vimeo 视频 < 3 分钟
- [ ] Devpost 表单填写 CRDB 工具 + AWS 服务
- [ ] MCP / ccloud 二选一演示接好（建议 Cloud MCP）
- [ ] 可选：架构图（本文档已有）
- [ ] 可选：Bedrock / Lambda

### Devpost 表单参考文案

**CockroachDB 工具：**
- Vector Indexing：古桥知识语义检索，dynasty prefix column
- MCP Server：Cursor 调试 exploration_events / tool_calls
- ccloud CLI：Agent 查询集群列表与备份状态
- Agent Skills：向量 schema 与性能调优规范

**AWS 服务：**
- Bedrock Claude：文化讲解生成
- Lambda + API Gateway：Agent API
- S3：研学报告存储

---

## 部署步骤（提交前）

### 1. CockroachDB Cloud

```bash
# 创建 Serverless 集群，获取连接串
export DATABASE_URL="postgresql://user:pass@host:26257/qianhong?sslmode=verify-full"
export STORAGE_MODE=cockroach
python scripts/import_bridge_data.py
```

### 2. AWS SAM

```bash
cd infra
sam build
sam deploy --guided \
  --parameter-overrides DatabaseUrl="$DATABASE_URL" LlmMode=bedrock
```

### 3. bridge 前端

更新根目录 `config.js` 中 `QIANHONG_AGENT.apiBase` 为 Lambda URL。

---

## 自检 API

```bash
curl http://127.0.0.1:8787/api/hackathon/checklist | jq
```

---

## 与 bridge 的关系（评委叙事）

| bridge v1 | qianhong-agent v2 |
|-----------|-------------------|
| 静态博物馆 | Agent 记忆层 |
| 无持久记忆 | CockroachDB 五层记忆 |
| 浏览器内 AI | AWS Bedrock + Lambda |
| 孤立 Chat | 图谱/地图/档案联动 |

**创意点**：文化遗产 + Agentic Memory，不是通用 Chatbot。
