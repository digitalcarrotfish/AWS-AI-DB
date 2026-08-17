# CockroachDB Managed MCP Server

Hackathon 第二工具（推荐）：在 **Cursor** 里只读查询 Agent 记忆表。

官方文档：[Connect to the CockroachDB Cloud MCP Server](https://www.cockroachlabs.com/docs/cockroachcloud/connect-to-the-cockroachdb-cloud-mcp-server)

> 本地 Homebrew 单节点 **没有** Managed MCP。必须开 [CockroachDB Cloud](https://cockroachlabs.cloud/)（有免费 Serverless）。

---

## 15 分钟开通

### 1. 注册并建集群

1. 打开 https://cockroachlabs.cloud/ → Sign up（可用 GitHub / Google）
2. 创建 **Serverless** 集群（免费额度通常够 demo）
3. 记下 **Cluster ID**（Connect 对话框里可见）

### 2. 把记忆 schema 导入 Cloud（可选但强烈建议）

在 Cloud Console → Connect → 复制连接串，写入本机 `.env`：

```env
STORAGE_MODE=cockroach
DATABASE_URL=postgresql://...云连接串...
```

然后：

```bash
# 用 Cloud SQL 客户端或 psql 执行
# 或：cockroach sql --url "$DATABASE_URL" < db/schema.sql
source .venv/bin/activate
python scripts/import_bridge_data.py
```

本地单节点数据不会自动同步；Demo 可用 Cloud 新库，或继续本地开发、Cloud 只演示 MCP 查询副本。

### 3. 接入 Cursor MCP

**方式 A（推荐）**：Cloud Console → 集群 → **Connect** → **MCP** → 选 Cursor → **Add to Cursor**。

**方式 B**：项目内复制模板：

```bash
mkdir -p .cursor
cp docs/mcp-config.example.json .cursor/mcp.json
```

按 Console 提示补上 `headers`（如 `mcp-cluster-id`）。**不要把含密钥的 mcp.json 提交到公开仓库。**

重启 Cursor → Settings → MCP → 确认 `cockroachdb-cloud` 为绿色。

### 4. Demo 里问 Cursor

```text
用 CockroachDB MCP 执行：
SELECT event_type, bridge_name, created_at
FROM exploration_events
ORDER BY created_at DESC LIMIT 10;
```

---

## 与本项目的关系

| 角色 | 通道 |
|------|------|
| Agent 运行时写入 | 应用 `psycopg` → CRDB |
| 开发者只读调试 | Cursor ↔ Managed MCP |

Endpoint：`https://cockroachlabs.cloud/mcp`（默认只读 + 审计）。

---

## 备选：同一 Cloud 账号再开 ccloud

见 [`docs/CCLOUD.md`](./CCLOUD.md) 或直接：

```bash
bash scripts/install_ccloud.sh
ccloud auth login
ccloud cluster list
# Agent 对话问：「数据库集群状态」
```
