"""MyBlog 站点共享核心：清单读写、文章页渲染 / 解析、feed 与 sitemap 重建（仅标准库）。

`scripts/new_post.py`（CLI）、`scripts/set_site.py` 与 `editor/server.py` 都从这里取逻辑，
避免「建页」与「重建 feed」各写一份。
"""

from __future__ import annotations

import html
import io
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

# 文章页在文件里的正文缩进；编辑器里按公共缩进去掉显示，保存时恢复，保证往返零 diff。
BODY_INDENT = " " * 6

PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · __SITE_TITLE__</title>
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
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand" href="../index.html">__BRAND__</a>
    <nav class="nav" aria-label="主导航">
      <a href="../index.html" aria-current="page">文章</a>
      <a href="../about.html">关于</a>
      <a href="../feed.xml">RSS</a>
      <a href="__PROFILE__" rel="me noopener">GitHub</a>
    </nav>
    <button class="theme-toggle" type="button" data-theme-toggle aria-label="切换深浅色">☾</button>
  </div>
</header>
<main id="main">
  <article class="post">
    <header class="post-header">
      <h1>__TITLE__</h1>
__META__
    </header>
    <div class="post-body">
__BODY__
    </div>
    <footer class="post-footer">
      <a href="../index.html">← 返回文章列表</a>
    </footer>
  </article>
</main>
<footer class="site-footer page-footer">
  <span>© <span data-year>__YEAR__</span> __BRAND__</span>
  <span><a href="../feed.xml">RSS</a> · <a href="__PROFILE__" rel="me noopener">GitHub</a></span>
</footer>
<script src="../assets/app.js" defer></script>
</body>
</html>
"""


# ---------- 清单 ----------


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as fp:
        return json.load(fp)


def save_manifest(data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    _write_preserving_newlines(MANIFEST, text.encode("utf-8"))


def _uses_crlf(path: Path) -> bool:
    try:
        return b"\r\n" in path.read_bytes()
    except OSError:
        return False


def _write_preserving_newlines(path: Path, data: bytes) -> None:
    """沿用已有文件的行尾风格，避免 Windows 工作区每次保存都改行尾。"""
    data = data.replace(b"\r\n", b"\n")
    if _uses_crlf(path):
        data = data.replace(b"\n", b"\r\n")
    path.write_bytes(data)


def validate_slug(slug: str) -> str:
    if not SLUG_RE.fullmatch(slug or ""):
        raise ValueError("slug 只能用小写字母、数字和连字符，例如 first-post")
    return slug


def parse_date(value: str) -> str:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"日期应为 YYYY-MM-DD：{value}") from None
    return value


def display_date(value: str) -> str:
    taken = datetime.fromisoformat(value)
    return f"{taken.year}年{taken.month}月{taken.day}日"


def post_url(site: dict, post: dict) -> str:
    return f"{site['url'].rstrip('/')}/{post['file'].lstrip('/')}"


def find_post(data: dict, slug: str) -> dict | None:
    return next((post for post in data["posts"] if post["slug"] == slug), None)


# ---------- 文章页 ----------


def default_body(summary: str) -> str:
    return (
        f"<p>{html.escape(summary)}</p>\n"
        "<!-- 在这里写正文：直接用 <p> / <h2> / <ul> / <pre><code> 即可。 -->"
    )


def dedent_body(raw: str) -> str:
    """把文件里的正文（统一缩进 6 空格）还原成编辑态。"""
    lines = raw.strip("\n").split("\n")
    widths = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    shift = min(widths) if widths else 0
    return "\n".join(line[shift:] if line.strip() else "" for line in lines)


def indent_body(body: str, prefix: str = BODY_INDENT) -> str:
    return "\n".join((prefix + line) if line.strip() else "" for line in body.strip("\n").split("\n"))


def render_post_page(site: dict, entry: dict, body: str) -> str:
    title = html.escape(entry["title"])
    date = entry["date"]
    meta = [
        '      <p class="post-meta">',
        f'        <time datetime="{html.escape(date, quote=True)}">{display_date(date)}</time>',
    ]
    meta += [f'        <span class="tag">{html.escape(tag)}</span>' for tag in entry.get("tags") or []]
    meta.append("      </p>")

    brand = site.get("author") or site.get("github_user") or ""
    replacements = (
        ("__SITE_TITLE__", html.escape(site.get("title", ""))),
        ("__SUMMARY__", html.escape(entry.get("summary", ""), quote=True)),
        ("__PROFILE__", html.escape(f"https://github.com/{site.get('github_user', '')}", quote=True)),
        ("__BRAND__", html.escape(brand)),
        ("__META__", "\n".join(meta)),
        ("__YEAR__", date[:4]),
        ("__BODY__", indent_body(body)),
        ("__TITLE__", title),
    )
    page = PAGE_TEMPLATE
    for key, value in replacements:
        page = page.replace(key, value)
    return page


def _first(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.S)
    return match.group(1) if match else ""


def _extract_div(text: str, class_name: str) -> str | None:
    """按 div 嵌套层数切出指定 class 的 div 内容（正文里可能有嵌套 div / pre）。"""
    opening = re.search(rf'<div class="{re.escape(class_name)}">', text)
    if not opening:
        return None
    start = opening.end()
    depth = 1
    for tag in re.finditer(r"<(/?)div\b[^>]*>", text[start:], re.I):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return text[start : start + tag.start()]
    return None


def parse_post_page(text: str) -> dict:
    text = text.replace("\r\n", "\n")
    return {
        "title": html.unescape(_first(r"<h1>(.*?)</h1>", text)),
        "summary": html.unescape(_first(r'<meta name="description" content="(.*?)">', text)),
        "date": _first(r'<time datetime="([^"]+)">', text),
        "tags": [html.unescape(tag) for tag in re.findall(r'<span class="tag">(.*?)</span>', text)],
        "body": dedent_body(_extract_div(text, "post-body") or ""),
    }


def read_post(entry: dict) -> dict:
    """返回编辑态数据；drift 列出页面与 posts.json 不一致的字段。"""
    page = parse_post_page((ROOT / entry["file"]).read_text(encoding="utf-8"))
    drift = [key for key in ("title", "summary", "date", "tags") if page[key] != entry.get(key)]
    return {"slug": entry["slug"], "file": entry["file"], **page, "drift": drift}


def write_post(site: dict, entry: dict, body: str) -> Path:
    target = POSTS_DIR / f"{entry['slug']}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_preserving_newlines(target, render_post_page(site, entry, body).encode("utf-8"))
    return target


def upsert_post(data: dict, entry: dict) -> bool:
    """按 slug 覆盖或插到最前；返回是否新建。"""
    for index, post in enumerate(data["posts"]):
        if post["slug"] == entry["slug"]:
            data["posts"][index] = entry
            return False
    data["posts"].insert(0, entry)
    return True


# ---------- feed / sitemap ----------


def rfc822(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def write_xml(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    buffer = io.BytesIO()
    ET.ElementTree(root).write(buffer, encoding="utf-8", xml_declaration=True)
    _write_preserving_newlines(path, buffer.getvalue())


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


def rebuild(dry_run: bool = False) -> None:
    data = load_manifest()
    if dry_run:
        print("[dry-run] 将按 posts.json 重新生成 feed.xml 与 sitemap.xml")
        return
    write_xml(build_feed(data), FEED)
    write_xml(build_sitemap(data), SITEMAP)
    print("已重新生成 feed.xml 与 sitemap.xml")


# ---------- 保存 ----------


def build_entry(slug: str, title: str, summary: str, tags: list[str], date: str) -> dict:
    return {
        "slug": slug,
        "title": title,
        "date": date,
        "summary": summary,
        "tags": list(tags),
        "file": f"posts/{slug}.html",
    }


def save_post(
    *,
    slug: str,
    title: str,
    summary: str,
    tags: list[str],
    date: str,
    body: str,
    create_only: bool = False,
) -> dict:
    """校验 → 写文章页 → 更新 posts.json → 重建 feed / sitemap。值为空/非法时抛 ValueError。"""
    data = load_manifest()
    validate_slug(slug)
    if not date.strip():
        raise ValueError("日期不能为空")
    parse_date(date)
    if not title.strip():
        raise ValueError("标题不能为空")

    existing = find_post(data, slug)
    if create_only and existing:
        raise ValueError(f"posts.json 里已有 slug：{slug}")
    if create_only and (POSTS_DIR / f"{slug}.html").exists():
        raise ValueError(f"文件已存在：posts/{slug}.html")

    entry = build_entry(slug, title.strip(), summary.strip(), [tag.strip() for tag in tags if tag.strip()], date)
    write_post(data["site"], entry, body)
    created = upsert_post(data, entry)
    save_manifest(data)
    write_xml(build_feed(data), FEED)
    write_xml(build_sitemap(data), SITEMAP)
    return {
        "slug": slug,
        "file": entry["file"],
        "created": created,
        "rebuilt": ["feed.xml", "sitemap.xml"],
    }
