"""blog_core 的最小回归测试（仅标准库）。

运行：python -m unittest discover -s scripts -p "test_*.py"
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import blog_core as core


class BlogCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "posts").mkdir()
        shutil.copy(core.ROOT / "posts.json", root / "posts.json")
        shutil.copy(core.ROOT / "posts" / "hello-world.html", root / "posts" / "hello-world.html")

        self._saved = (core.ROOT, core.MANIFEST, core.FEED, core.SITEMAP, core.POSTS_DIR)
        core.ROOT = root
        core.MANIFEST = root / "posts.json"
        core.FEED = root / "feed.xml"
        core.SITEMAP = root / "sitemap.xml"
        core.POSTS_DIR = root / "posts"

    def tearDown(self) -> None:
        core.ROOT, core.MANIFEST, core.FEED, core.SITEMAP, core.POSTS_DIR = self._saved
        self.tmp.cleanup()

    def test_hello_world_round_trip(self) -> None:
        """解析再渲染必须逐字还原，否则编辑器「打开即保存」会产生无意义改动。"""
        data = core.load_manifest()
        entry = next(post for post in data["posts"] if post["slug"] == "hello-world")
        original = (core.ROOT / entry["file"]).read_text(encoding="utf-8")

        page = core.parse_post_page(original)
        self.assertEqual(page["title"], entry["title"])
        self.assertEqual(page["summary"], entry["summary"])
        self.assertEqual(page["date"], entry["date"])
        self.assertEqual(page["tags"], entry["tags"])
        self.assertEqual(core.render_post_page(data["site"], entry, page["body"]), original)

    def test_save_new_post_writes_page_manifest_and_feeds(self) -> None:
        result = core.save_post(
            slug="editor-test",
            title="测试文章",
            summary="一句话摘要",
            tags=["工具"],
            date="2026-11-24",
            body="<p>正文</p>",
            create_only=True,
        )
        self.assertTrue(result["created"])

        page = (core.POSTS_DIR / "editor-test.html").read_text(encoding="utf-8")
        self.assertIn('<header class="topbar">', page)
        self.assertIn('<div class="post-body">', page)

        data = json.loads(core.MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["posts"][0]["slug"], "editor-test")
        self.assertIn("测试文章", core.FEED.read_text(encoding="utf-8"))
        self.assertIn(f"{data['site']['url']}/posts/editor-test.html", core.SITEMAP.read_text(encoding="utf-8"))

    def test_save_keeps_existing_line_endings(self) -> None:
        """Windows 工作区是 CRLF 时，保存不能把整个文件改成 LF。"""
        path = core.POSTS_DIR / "hello-world.html"
        crlf = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        path.write_bytes(crlf)

        data = core.load_manifest()
        entry = next(post for post in data["posts"] if post["slug"] == "hello-world")
        page = core.parse_post_page(crlf.decode("utf-8"))
        core.save_post(
            slug=entry["slug"],
            title=entry["title"],
            summary=entry["summary"],
            tags=entry["tags"],
            date=entry["date"],
            body=page["body"],
        )

        self.assertEqual(path.read_bytes(), crlf)

    def test_rejects_invalid_input_without_writing(self) -> None:
        cases = {
            "slug 含大写与空格": dict(slug="Bad Slug", title="x", date="2026-11-24"),
            "slug 已存在": dict(slug="hello-world", title="x", date="2026-11-24"),
            "标题为空": dict(slug="ok-slug", title="   ", date="2026-11-24"),
            "日期为空": dict(slug="ok-slug", title="x", date="  "),
            "日期非法": dict(slug="ok-slug", title="x", date="2026/11/24"),
        }
        for label, case in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                core.save_post(summary="", tags=[], body="<p>x</p>", create_only=True, **case)

        self.assertEqual([path.name for path in core.POSTS_DIR.iterdir()], ["hello-world.html"])


if __name__ == "__main__":
    unittest.main()
