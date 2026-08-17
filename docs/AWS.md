# AWS 接入（Hackathon ≥1 服务）

本项目用 **Amazon S3**（默认）和/或 **Amazon Bedrock** 满足「至少 1 个 AWS」。

| 服务 | 用途 | 本地开关 |
|------|------|----------|
| **Amazon S3** | 扫桥照片存证 + 研学报告 JSON 导出 | `S3_BUCKET=...` |
| **Amazon Bedrock** | Claude 讲解生成 | `LLM_MODE=bedrock` |
| Lambda + API GW | 生产部署 | `infra/template.yaml` |

自检：`GET http://127.0.0.1:8787/api/aws/status`  
清单：`GET /api/hackathon/checklist` → `requirement_aws_met: true`

---

## 最快路径：只开 S3（推荐）

### 1. 凭证

```bash
# 任选其一
aws configure   # 写入 ~/.aws/credentials
# 或在 .env：
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_REGION=us-east-1
```

### 2. 建桶并写入 `.env`

```bash
aws s3 mb s3://qianhong-agent-$(whoami)-$(date +%Y%m%d) --region us-east-1
```

```env
AWS_REGION=us-east-1
S3_BUCKET=你的桶名
S3_PREFIX=qianhong
```

重启 `python -m api.main` 后：

```bash
curl -s http://127.0.0.1:8787/api/aws/status | python -m json.tool
```

`s3.ok` 应为 `true`。

### 3. 业务怎么用到 S3

| 动作 | API | 对象前缀 |
|------|-----|----------|
| 扫桥识别成功 | `POST /api/identify` | `qianhong/scans/...` |
| 导出研学报告 | `POST /api/reports/export` `{"session_id":"..."}` | `qianhong/reports/...` |

---

## 可选：Bedrock

1. 控制台开通模型访问（如 Claude 3.5 Sonnet）。
2. `.env`：

```env
LLM_MODE=bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
AWS_REGION=us-east-1
```

3. Agent 对话走 `agent/llm.py`（Converse → InvokeModel 回退）。

---

## SAM 一键（Lambda + S3 + Bedrock IAM）

模板已注入 `S3_BUCKET` / `S3_PREFIX`，并给函数 S3 写权限 + Bedrock Invoke/Converse。

```bash
sam build
sam deploy --guided \
  --parameter-overrides DatabaseUrl="$DATABASE_URL" LlmMode=bedrock
```

输出 `ReportsBucket` 即生产桶名。

---

## Devpost 填写建议

- **AWS services used:** Amazon S3（扫桥存证与研学报告）；可选 Amazon Bedrock / Lambda  
- Demo：扫桥一次 → 控制台看 `s3://.../scans/`；或点导出 → `reports/`  
