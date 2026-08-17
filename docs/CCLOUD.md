# ccloud CLI（Hackathon 工具）

Agent 可通过 `GET /api/cluster/status` 或对话「集群状态」调用只读 `ccloud` 命令。

## 安装（在本机终端执行）

Agent 沙箱里无法写入 Homebrew / 官方二进制常 403，请在 **Terminal.app** 跑：

```bash
cd ~/Desktop/AWS-AI-DB

# 若 brew 报 Cellar 不可写：
sudo chown -R "$(whoami)" /opt/homebrew ~/Library/Logs/Homebrew

bash scripts/install_ccloud.sh
# 或：brew install cockroachdb/tap/ccloud

# 若装到项目目录：
export PATH="$PWD/.tools/bin:$PATH"
```

## 登录 + 验证

```bash
ccloud auth login          # 浏览器登录 Cloud
ccloud cluster list        # 应列出你的 Serverless 集群
curl -s http://127.0.0.1:8787/api/cluster/status | python3 -m json.tool
```

在 `/agent/` 发送：**数据库集群状态**

## 允许的命令（白名单）

- `ccloud cluster list`
- `ccloud cluster describe …`
- `ccloud cluster backup list …`
- `ccloud organization list`

## 提交话术

> 使用 **ccloud CLI**：档案员可查询 CockroachDB Cloud 集群列表与健康状态，运维能力进入 Agent 工具链（非仅 SQL）。
