# CockroachDB Managed MCP Server

Hackathon 要求工具之一。用于在 **Cursor / Claude Code / VS Code** 中只读调试 Agent 记忆层。

## 配置步骤

1. 登录 [CockroachDB Cloud Console](https://cockroachlabs.cloud/)
2. 进入集群 → **Connect** → **MCP Server**
3. 复制配置片段到 Cursor：
   - macOS: `~/.cursor/mcp.json`
   - 或项目级: `.cursor/mcp.json`

参考模板见 [`mcp-config.example.json`](./mcp-config.example.json)。

官方 Endpoint: `https://cockroachlabs.cloud/mcp`

## 在本项目中的用途

| 调试场景 | MCP 查询示例 |
|---------|-------------|
| 验证 Agent 记忆 | `SELECT * FROM user_memory LIMIT 5` |
| 浏览轨迹 | `SELECT * FROM exploration_events ORDER BY created_at DESC LIMIT 10` |
| 向量检索 | `SELECT bridge_name, content_type FROM bridge_embeddings LIMIT 5` |
| 研学路线 | `SELECT * FROM agent_tasks WHERE task_type = 'study_path'` |
| 工具审计 | `SELECT tool_name, created_at FROM tool_calls ORDER BY created_at DESC LIMIT 20` |

## 安全说明

- MCP Server **默认只读**，符合 Hackathon 生产就绪要求
- 所有 MCP 查询有 **audit log**
- Agent 运行时通过应用层 `psycopg` 写入；MCP 仅用于开发者调试

## Demo 视频建议片段（30 秒）

1. 在 Cursor 打开 MCP
2. 查询 `exploration_events` 表，展示 bridge 图谱点击已写入 CRDB
3. 查询 `bridge_embeddings`，说明向量与事务数据同一库
