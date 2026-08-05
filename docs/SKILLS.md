# CockroachDB Agent Skills

Hackathon 要求工具之一：[cockroachlabs/cockroachdb-skills](https://github.com/cockroachlabs/cockroachdb-skills)

## 安装（Cursor / Claude）

```bash
npx skills add cockroachlabs/cockroachdb-skills
```

## 在本项目中的用途

| Skill 域 | 用途 |
|---------|------|
| `query-and-schema-design` | 设计 `bridge_embeddings` 向量表 + prefix column |
| `performance-and-scaling` | 调优 `CREATE VECTOR INDEX` 与 dynasty 前缀过滤 |
| `security-and-governance` | RBAC、只读 MCP、tool_calls 审计 |
| `observability-and-diagnostics` | 解释 `/api/cluster/status` ccloud 输出 |

## Schema 设计决策（答辩要点）

1. **向量 + 事务同一库** — `bridges` 与 `bridge_embeddings` 同库，无 Pinecone 分裂
2. **prefix column `dynasty`** — 向量索引按朝代过滤，匹配「宋代桥梁研学」场景
3. **exploration_events** — bridge 博物馆浏览轨迹，非 Chat 附属记忆
4. **agent_tasks** — 研学路线断点续跑，Agent 状态持久化

## 可选反馈（Hackathon 加分）

- Skills 可增加「Agentic Memory 五层模型」示例
-  vector index + graph RAG 联合检索 recipe
