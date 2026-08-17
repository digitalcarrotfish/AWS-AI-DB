# 接入真模型（Kimi / DeepSeek）

默认讲解走本地检索。填入 OpenAI 兼容密钥后，档案员用大模型生成，失败自动回退检索。

## 最快：Kimi（Moonshot）

1. 打开 [Moonshot 开放平台](https://platform.moonshot.cn/console/api-keys) 创建 API Key  
2. 写入项目 `.env`（勿提交）：

```env
LLM_MODE=openai
OPENAI_API_BASE=https://api.moonshot.cn/v1
OPENAI_API_KEY=sk-你的密钥
OPENAI_MODEL=kimi-k2.5
```

新账号请用 `kimi-k2.5`（`moonshot-v1-8k` 将于 2026-08-31 下线）。国际站 base 为 `https://api.moonshot.ai/v1`。

3. 重启 `python -m api.main`  
4. 打开 `/agent/`，顶栏应显示 `LLM：Kimi · kimi-k2.5`  
5. 问「介绍赵州桥」——气泡 meta 为「大模型增强」即走通

## 备选：DeepSeek

```env
LLM_MODE=openai
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_API_KEY=sk-你的密钥
OPENAI_MODEL=deepseek-chat
```

## 行为说明

- 检索仍用 CockroachDB 向量表；模型只负责把检索到的图鉴写成讲解  
- 无密钥 / 调用失败 → 自动回退 `retrieval`，博物馆不中断  
- embedding 仍是本地哈希（不依赖 Kimi）；要换 Titan 需 `LLM_MODE=bedrock` 并重跑导入
