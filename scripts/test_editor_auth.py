"""编辑器访问控制的最小回归测试（仅标准库，只读，不写仓库文件）。

运行：python -m unittest discover -s scripts -p "test_*.py"
"""

from __future__ import annotations

import importlib.util
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("myblog_editor_server", ROOT / "editor" / "server.py")
editor_server = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(editor_server)


def request(port: int, path: str, *, cookie: str = "", method: str = "GET", headers: dict | None = None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method)
    if cookie:
        req.add_header("Cookie", cookie)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


class EditorAuthTest(unittest.TestCase):
    TOKEN = "test-token-1234567890"

    @classmethod
    def setUpClass(cls) -> None:
        editor_server.EditorHandler.log_message = lambda *args, **kwargs: None
        cls.servers: list = []
        cls.server = editor_server.create_server(0, cls.TOKEN)
        cls.servers.append(cls.server)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.cookie = f"myblog_editor={cls.TOKEN}"

    @classmethod
    def tearDownClass(cls) -> None:
        for server in cls.servers:
            server.shutdown()
            server.server_close()

    def test_api_requires_token_cookie(self) -> None:
        status, _, _ = request(self.port, "/api/posts")
        self.assertEqual(status, 403)
        status, _, body = request(self.port, "/api/posts", cookie=self.cookie)
        self.assertEqual(status, 200)
        self.assertIn("posts", body.decode("utf-8"))

    def test_editor_page_needs_correct_key(self) -> None:
        status, _, _ = request(self.port, "/editor/")
        self.assertEqual(status, 403)
        status, _, _ = request(self.port, "/editor/?key=wrong-token")
        self.assertEqual(status, 403)
        status, headers, _ = request(self.port, f"/editor/?key={self.TOKEN}")
        self.assertEqual(status, 200)
        self.assertIn(f"myblog_editor={self.TOKEN}", headers.get("Set-Cookie", ""))

    def test_rejects_foreign_host(self) -> None:
        status, _, _ = request(self.port, "/api/posts", cookie=self.cookie, headers={"Host": "evil.example"})
        self.assertEqual(status, 403)

    def test_write_needs_editor_header_and_same_origin(self) -> None:
        status, _, _ = request(self.port, "/api/posts/hello-world", cookie=self.cookie, method="POST")
        self.assertEqual(status, 403)
        status, _, _ = request(
            self.port,
            "/api/posts/hello-world",
            cookie=self.cookie,
            method="POST",
            headers={"X-Editor": "1", "Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)

    def test_restart_with_new_token_rejects_old_cookie(self) -> None:
        other = editor_server.create_server(0, "another-token")
        self.servers.append(other)
        threading.Thread(target=other.serve_forever, daemon=True).start()
        status, _, _ = request(other.server_address[1], "/api/posts", cookie=self.cookie)
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
