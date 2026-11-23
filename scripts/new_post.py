"""新建文章并同步 posts.json / feed.xml / sitemap.xml（仅用标准库）。

用法：
    python scripts/new_post.py --title "标题" --slug my-post --summary "摘要" --tags 随笔,工具
    python scripts/new_post.py --rebuild          # 只按 posts.json 重算 feed / sitemap
    python scripts/new_post.py ... --dry-run      # 只打印将要做的事
"""

from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "posts.json"
FEED = ROOT / "feed.xml"
SITEMAP = ROOT / "sitemap.xml"
POSTS_DIR = ROOT / "posts"

ATOM_NS = "http://www.w3.org/2005/Atom"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

POST_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · CM233 的记事本</title>
<meta name="description" content="__SUMMARY__">
<script>
  (function () {
    try {
      var saved = localStorage.getItem('blog-theme');
      var theme = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.dataset.theme = theme;
    } catch (error) {}
  })();
</script>
<link rel="stylesheet" href="../assets/style.css">
<link rel="alternate" type="application/rss+xml" title="RSS" href="../feed.xml">
</head>
<body>
<a class="skip-link" href="#main">跳到正文</a>
<header class="site-header">
  <a class="brand" href="../index.html">CM233 的记事本</a>
  <nav class="site-nav" aria-label="主导航">
    <a href="../index.html">文章</a>
    <a href="../about.html">关于</a>
  </nav>
  <button class="theme-toggle" type="button" data-theme-toggle aria-label="切换深浅色">☾</button>
</header>
<main id="main">
  <article class="post">
    <header class="post-header">
      <h1>__TITLE__</h1>
      <p class="post-meta"><time datetime="__DATE__">__DATE_TEXT__</time></p>
    </header>
    <div class="post-body">
      <p>__SUMMARY__</p>
      <!-- 在这里写正文：直接用 <p> / <h2> / <ul> / <pre><code> 即可。 -->
    </div>
    <footer class="post-footer">
      <a href="../index.html">← 返回文章列表</a>
    </footer>
  </article>
</main>
<footer class="site-footer">
  <span>© <span data-year>__YEAR__</span> CM233</span>
  <span><a href="../feed.xml">RSS</a></span>
</footer>
<script src="../assets/app.js" defer></script>
</body>
</html>
"""


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as fp:
        return json.load(fp)


def save_manifest(data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    MANIFEST.write_bytes(text.encode("utf-8"))


def parse_date(value: str) -> str:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise SystemExit(f"日期应为 YYYY-MM-DD：{value}") from None
    return value


def display_date(value: str) -> str:
    taken = datetime.fromisoformat(value)
    return f"{taken.year}年{taken.month}月{taken.day}日"


def post_url(site: dict, post: dict) -> str:
    return f"{site['url'].rstrip('/')}/{post['file'].lstrip('/')}"


def rfc822(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def write_xml(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def build_feed(data: dict) -> ET.Element:
    site, posts = data["site"], data["posts"]
    base = site["url"].rstrip("/")
    ET.register_namespace("atom", ATOM_NS)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = site["title"]
    ET.SubElement(channel, "link").text = f"{base}/"
    ET.SubElement(channel, "description").text = site["description"]
    ET.SubElement(channel, "language").text = "zh-CN"
    ET.SubElement(
        channel,
        f"{{{ATOM_NS}}}link",
        {"href": f"{base}/feed.xml", "rel": "self", "type": "application/rss+xml"},
    )
    if posts:
        newest = max(post["date"] for post in posts)
        ET.SubElement(channel, "lastBuildDate").text = format_datetime(rfc822(newest), usegmt=True)

    for post in sorted(posts, key=lambda item: item["date"], reverse=True):
        url = post_url(site, post)
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post["title"]
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = url
        ET.SubElement(item, "pubDate").text = format_datetime(rfc822(post["date"]), usegmt=True)
        ET.SubElement(item, "description").text = post.get("summary", "")
    return rss


def build_sitemap(data: dict) -> ET.Element:
    site, posts = data["site"], data["posts"]
    base = site["url"].rstrip("/")
    latest = max((post["date"] for post in posts), default=None)
    ET.register_namespace("", SITEMAP_NS)

    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    pages = [("", latest), ("about.html", latest)]
    pages += [(post["file"], post["date"]) for post in posts]

    for path, lastmod in pages:
        node = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = f"{base}/{path}"
        if lastmod:
            ET.SubElement(node, f"{{{SITEMAP_NS}}}lastmod").text = lastmod
    return urlset


def rebuild(dry_run: bool) -> None:
    data = load_manifest()
    if dry_run:
        print("[dry-run] 将按 posts.json 重新生成 feed.xml 与 sitemap.xml")
        return
    write_xml(build_feed(data), FEED)
    write_xml(build_sitemap(data), SITEMAP)
    print("已重新生成 feed.xml 与 sitemap.xml")


def add_post(title: str, slug: str, summary: str, tags: list[str], date: str, dry_run: bool) -> None:
    if not SLUG_RE.fullmatch(slug):
        raise SystemExit("slug 只能用小写字母、数字和连字符，例如 first-post")
    parse_date(date)

    data = load_manifest()
    if any(post["slug"] == slug for post in data["posts"]):
        raise SystemExit(f"posts.json 里已有 slug：{slug}")
    target = POSTS_DIR / f"{slug}.html"
    if target.exists():
        raise SystemExit(f"文件已存在：{target.relative_to(ROOT)}")

    if dry_run:
        print(f"[dry-run] 将新建 {target.relative_to(ROOT)}")
        print(f"[dry-run] 将把 {slug}（{date}）登记到 posts.json")
        print("[dry-run] 将重新生成 feed.xml 与 sitemap.xml")
        return

    page = (
        POST_TEMPLATE.replace("__TITLE__", html.escape(title))
        .replace("__SUMMARY__", html.escape(summary))
        .replace("__DATE_TEXT__", display_date(date))
        .replace("__DATE__", date)
        .replace("__YEAR__", date[:4])
    )
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    target.write_bytes(page.encode("utf-8"))

    entry = {
        "slug": slug,
        "title": title,
        "date": date,
        "summary": summary,
        "tags": tags,
        "file": f"posts/{slug}.html",
    }
    data["posts"].insert(0, entry)
    save_manifest(data)
    write_xml(build_feed(data), FEED)
    write_xml(build_sitemap(data), SITEMAP)

    print(f"已新建 {target.relative_to(ROOT)}，并更新 posts.json / feed.xml / sitemap.xml")
    print("下一步：编辑正文，然后 python -m http.server 8000 本地预览")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="新建文章并同步 posts.json / feed.xml / sitemap.xml")
    parser.add_argument("--title", help="文章标题")
    parser.add_argument("--slug", help="URL 片段：小写字母、数字、连字符")
    parser.add_argument("--summary", default="", help="一句话摘要，用于列表与 RSS")
    parser.add_argument("--tags", default="", help="标签，逗号分隔")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="日期，默认今天")
    parser.add_argument("--rebuild", action="store_true", help="只按 posts.json 重算 feed 与 sitemap")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要做的改动")
    args = parser.parse_args(argv)

    if args.rebuild:
        rebuild(args.dry_run)
        return 0

    missing = [name for name in ("title", "slug") if not getattr(args, name)]
    if missing:
        parser.error("缺少参数：" + "、".join("--" + name for name in missing))

    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    add_post(args.title.strip(), args.slug.strip(), args.summary.strip(), tags, args.date, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
