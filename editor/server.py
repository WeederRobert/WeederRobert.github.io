"""MyBlog 本地文章编辑器（仅标准库；只监听 127.0.0.1，并需要一次性的访问令牌）。

用法：
    python editor/server.py                  # 打开带 key 的链接
    python editor/server.py --port 8800 --no-browser

访问控制（详见 README「本地编辑器的访问控制」）：
- 只绑定 127.0.0.1：局域网与外网都连不上，不依赖防火墙；
- 每次启动生成随机 token，只在启动终端打印、不落盘；重启后旧链接与旧 Cookie 立刻失效；
- 令牌校验通过后下发 HttpOnly + SameSite=Strict 的会话 Cookie；
- 写接口另外要求 `X-Editor: 1` 与同源 `Origin`，跨站页面无法借你的浏览器改文件；
- `Host` 只接受 127.0.0.1 / localhost，防 DNS rebinding；
- 刻意不提供 `--host`，也没有账号体系 —— 这是单人本机工具，不要暴露到公网。
"""

from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import re
import secrets
import sys
import threading
import webbrowser
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import blog_core  # noqa: E402  （先补 sys.path 再导入同项目的核心模块）

POST_PATH = re.compile(r"^/api/posts/([^/]+)$")
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
COOKIE_NAME = "myblog_editor"
MAX_BODY = 2 * 1024 * 1024
EDITOR_PATHS = {"/editor", "/editor/", "/editor/index.html"}

FORBIDDEN_PAGE = """<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>需要访问令牌</title>
<body style="font:15px/1.7 system-ui,'Microsoft YaHei',sans-serif;max-width:40rem;margin:12vh auto;padding:0 1.5rem;color:#222">
<h1 style="font-size:1.2rem">打不开本地编辑器</h1>
<p>{reason}</p>
<p>请在启动 <code>python editor/server.py</code> 的终端里复制打印出来的完整链接（带 <code>?key=…</code>）再打开。
令牌只在本次进程内存里有效，重启服务后旧链接会立即失效。</p>
</body>
</html>
"""


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _coerce_date(value) -> str:
    """边输入边预览时日期可能为空或没写完，回落到今天，避免 500。"""
    text = str(value or "").strip()
    try:
        blog_core.parse_date(text)
    except ValueError:
        return _today()
    return text


def _coerce_tags(value) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(part).strip() for part in (value or []) if str(part).strip()]


class EditorHandler(BaseHTTPRequestHandler):
    server_version = "MyBlogEditor/2.0"
    token: str = ""

    # ---------- 基础 ----------

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[editor] " + (fmt % args) + "\n")

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip()
        if host.startswith("["):  # IPv6 字面量，本机用不到
            return False
        return host.rsplit(":", 1)[0].lower() in LOCAL_HOSTS

    def _cookie_token(self) -> str:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel else ""

    def _authorized(self) -> bool:
        return bool(self.token) and hmac.compare_digest(self._cookie_token(), self.token)

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True  # 非浏览器客户端（curl / 测试）不带 Origin
        port = self.server.server_port
        return origin in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _forbidden(self, reason: str, *, as_page: bool = False) -> None:
        if as_page:
            body = FORBIDDEN_PAGE.replace("{reason}", reason).encode("utf-8")
            self.send_response(403)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json({"error": reason}, 403)

    def _send_file(self, path: Path) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self._send_bytes(path.read_bytes(), content_type)

    def _resolve_static(self, url_path: str) -> Path | None:
        rel = unquote(url_path).lstrip("/")
        if not rel or any(part.startswith(".") for part in Path(rel).parts):
            return None
        candidate = (ROOT / rel).resolve()
        if not candidate.is_relative_to(ROOT):
            return None
        if candidate.is_dir():
            candidate = candidate / "index.html"
        return candidate if candidate.is_file() else None

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("请求体为空")
        if length > MAX_BODY:
            raise ValueError("请求体过大")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("请求体不是合法 JSON") from None
        if not isinstance(payload, dict):
            raise ValueError("请求体应为 JSON 对象")
        return payload

    # ---------- GET ----------

    def do_GET(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._forbidden("Host 不是 127.0.0.1 / localhost。", as_page=True)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/editor/")
            self.end_headers()
            return

        if path in EDITOR_PATHS:
            key = parse_qs(parsed.query).get("key", [""])[0]
            if key and not hmac.compare_digest(key, self.token):
                self._forbidden("链接里的 key 不正确（可能是旧的，或服务已重启）。", as_page=True)
                return
            if not key and not self._authorized():
                self._forbidden("还没有访问令牌。", as_page=True)
                return
            extra = {}
            if key:
                extra["Set-Cookie"] = f"{COOKIE_NAME}={self.token}; Path=/; HttpOnly; SameSite=Strict"
            self._send_bytes((ROOT / "editor" / "index.html").read_bytes(), "text/html; charset=utf-8", extra)
            return

        if not self._authorized():
            self._forbidden("缺少有效的编辑器访问令牌。")
            return

        if path == "/api/posts":
            data = blog_core.load_manifest()
            posts = sorted(data["posts"], key=lambda post: post["date"], reverse=True)
            tags = sorted({tag for post in posts for tag in post.get("tags") or []})
            self._send_json({"site": data["site"], "posts": posts, "tags": tags})
            return

        match = POST_PATH.match(path)
        if match:
            slug = unquote(match.group(1))
            data = blog_core.load_manifest()
            entry = blog_core.find_post(data, slug)
            if entry is None:
                self._send_json({"error": f"找不到文章：{slug}"}, 404)
                return
            try:
                self._send_json(blog_core.read_post(entry))
            except OSError as exc:
                self._send_json({"error": f"读取文章失败：{exc}"}, 500)
            return

        target = self._resolve_static(path)
        if target is None:
            self._send_json({"error": f"没有这个路径：{path}"}, 404)
            return
        self._send_file(target)

    # ---------- POST ----------

    def do_POST(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._forbidden("Host 不是 127.0.0.1 / localhost。")
            return
        if not self._authorized():
            self._forbidden("缺少有效的编辑器访问令牌。")
            return
        if not self._origin_ok():
            self._forbidden("Origin 不是本机编辑器页面。")
            return
        if self.headers.get("X-Editor") != "1":
            self._forbidden("缺少 X-Editor 请求头。")
            return

        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
            return

        if path == "/api/render":
            self._send_json({"html": self._render_preview(payload)})
            return

        if path == "/api/posts":
            slug = str(payload.get("slug") or "").strip()
        else:
            match = POST_PATH.match(path)
            if match is None:
                self._send_json({"error": f"没有这个接口：{path}"}, 404)
                return
            slug = unquote(match.group(1))
            if payload.get("slug") and str(payload["slug"]).strip() != slug:
                self._send_json({"error": "URL 里的 slug 与请求体不一致"}, 400)
                return

        try:
            result = blog_core.save_post(
                slug=slug,
                title=str(payload.get("title") or ""),
                summary=str(payload.get("summary") or ""),
                tags=_coerce_tags(payload.get("tags")),
                date=str(payload.get("date") or "").strip(),
                body=str(payload.get("body") or ""),
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        except OSError as exc:
            self._send_json({"error": f"写入失败：{exc}"}, 500)
            return

        self._send_json({"ok": True, **result, "url": f"/{result['file']}"})

    def _render_preview(self, payload: dict) -> str:
        data = blog_core.load_manifest()
        slug = str(payload.get("slug") or "preview").strip() or "preview"
        entry = blog_core.build_entry(
            slug,
            str(payload.get("title") or "未命名"),
            str(payload.get("summary") or ""),
            _coerce_tags(payload.get("tags")),
            _coerce_date(payload.get("date")),
        )
        return blog_core.render_post_page(data["site"], entry, str(payload.get("body") or ""))


def make_handler(token: str) -> type[EditorHandler]:
    return type("TokenBoundEditorHandler", (EditorHandler,), {"token": token})


def create_server(port: int, token: str) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(token))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="启动 MyBlog 本地文章编辑器（只监听本机）")
    parser.add_argument("--port", type=int, default=8765, help="端口，默认 8765")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args(argv)

    token = secrets.token_urlsafe(24)
    try:
        server = create_server(args.port, token)
    except OSError as exc:
        print(f"端口 {args.port} 不可用：{exc}（换一个：--port 8766）", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{args.port}/editor/?key={token}"
    print("MyBlog 编辑器（仅本机可访问）")
    print(f"  打开：{url}")
    print(f"  项目根目录：{ROOT}")
    print("  令牌只存在于本次进程内存，重启即失效；链接不要分享，也不要暴露到公网")
    print("  保存会直接写 posts/ 与 posts.json，并重建 feed.xml / sitemap.xml；Ctrl+C 退出")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
