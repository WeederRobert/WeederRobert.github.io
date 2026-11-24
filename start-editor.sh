#!/usr/bin/env bash
# 启动 MyBlog 本地文章编辑器（Git Bash / WSL / Linux / macOS 通用）。
#
# 用法：
#   ./start-editor.sh                  # 默认 127.0.0.1:8765，自动打开浏览器
#   ./start-editor.sh --port 8800      # 换端口
#   ./start-editor.sh --no-browser     # 不自动开浏览器
#   ./start-editor.sh --help           # 原样透传给 editor/server.py
#
# 端口优先级：--port= / --port N > 环境变量 MYBLOG_EDITOR_PORT > 8765
set -euo pipefail

die() {
  printf '\033[31m%s\033[0m\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 向上找到含 posts.json 的仓库根，脚本放在根目录或 editor/ 下都能用。
ROOT="$SCRIPT_DIR"
while [ ! -f "$ROOT/posts.json" ]; do
  if [ -z "$ROOT" ] || [ "$ROOT" = "/" ]; then
    die "没找到 posts.json —— 请在 MyBlog 仓库里运行本脚本。"
  fi
  ROOT="$(dirname "$ROOT")"
done
SERVER="$ROOT/editor/server.py"

[ -f "$SERVER" ] || die "找不到 $SERVER —— 请在 MyBlog 仓库根目录下放置并运行本脚本。"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  die "找不到 python3 / python —— 编辑器需要 Python 3.11+。"
fi

if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  die "$("$PY" -V 2>&1) 版本过低 —— 编辑器需要 Python 3.11+（用到 datetime.UTC）。"
fi

# 端口预检用 Python socket：Git Bash / WSL / macOS 上不保证有 ss、lsof、netstat。
port_free() {
  "$PY" - "$1" <<'PY'
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
}

PORT="${MYBLOG_EDITOR_PORT:-8765}"
ARGS=("$@")
for ((i = 0; i < ${#ARGS[@]}; i++)); do
  case "${ARGS[i]}" in
    --port) PORT="${ARGS[i+1]:-}" ;;
    --port=*) PORT="${ARGS[i]#--port=}" ;;
  esac
done

case "$PORT" in
  '' | *[!0-9]*) ;;  # 非数字就交给 server.py 自己报错
  *)
    if ! port_free "$PORT"; then
      printf '\033[33m端口 %s 已被占用，编辑器没有启动。\033[0m\n' "$PORT" >&2
      printf '  · 如果编辑器已经在跑：直接刷新原来的标签页（服务重启过就用终端新打印的带 key 链接）\n' >&2
      printf '  · 想再开一个：%s --port 8800\n' "$0" >&2
      exit 1
    fi
    ;;
esac

cd "$ROOT"
# -u：不让 stdout 缓冲，保证带 ?key= 的链接立刻出现在终端。
exec "$PY" -u "$SERVER" "${ARGS[@]+"${ARGS[@]}"}"
