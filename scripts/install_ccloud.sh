#!/usr/bin/env bash
# 安装 ccloud CLI（Hackathon 第二工具之一）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/.tools/bin"
mkdir -p "$BIN"

if command -v ccloud >/dev/null 2>&1; then
  echo "已有 ccloud: $(command -v ccloud)"
  ccloud version || true
  exit 0
fi

if command -v brew >/dev/null 2>&1; then
  echo "→ brew install cockroachdb/tap/ccloud"
  if brew install cockroachdb/tap/ccloud; then
    echo "OK: $(command -v ccloud)"
    ccloud version || true
    exit 0
  fi
  echo "brew 失败（常见：需 sudo chown -R \"\$(whoami)\" /opt/homebrew），改下二进制…"
fi

ARCH="$(uname -m)"
case "$ARCH" in
  arm64|aarch64) FILE="ccloud_darwin-arm64_0.6.12.tar.gz" ;;
  x86_64) FILE="ccloud_darwin-amd64_0.6.12.tar.gz" ;;
  *) echo "不支持的架构: $ARCH"; exit 1 ;;
esac

TMP="$(mktemp -d)"
cd "$TMP"
echo "→ 下载 https://binaries.cockroachdb.com/ccloud/$FILE"
curl -fL "https://binaries.cockroachdb.com/ccloud/$FILE" | tar -xJ
cp -f ccloud "$BIN/ccloud"
chmod +x "$BIN/ccloud"
echo "已安装: $BIN/ccloud"
echo "请加入 PATH，例如："
echo "  export PATH=\"$BIN:\$PATH\""
"$BIN/ccloud" version || true
