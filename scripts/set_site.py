"""统一修改站点身份：GitHub 用户名、标题、作者，并同步 feed / sitemap / robots。

用法：
    python scripts/set_site.py --user CM233
    python scripts/set_site.py --user someone --title "某人的博客" --author someone
    python scripts/set_site.py --user CM233 --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

from new_post import FEED, ROOT, SITEMAP, build_feed, build_sitemap, load_manifest, save_manifest, write_xml

ROBOTS = ROOT / "robots.txt"
README = ROOT / "README.md"


def iter_targets() -> list[Path]:
    """站点页面与 README；specs/ 是历史记录，不参与替换。"""
    pages = [path for path in ROOT.rglob("*.html") if "specs" not in path.parts]
    if README.exists():
        pages.append(README)
    return pages


def replace_all(old: str, new: str) -> list[Path]:
    if not old or old == new:
        return []
    changed = []
    for path in iter_targets():
        text = path.read_text(encoding="utf-8")
        if old not in text:
            continue
        path.write_bytes(text.replace(old, new).encode("utf-8"))
        changed.append(path.relative_to(ROOT))
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="改站点身份并同步 feed / sitemap / robots")
    parser.add_argument("--user", required=True, help="GitHub 用户名（只填用户名本身）")
    parser.add_argument("--title", help="站点标题，默认沿用当前值")
    parser.add_argument("--author", help="作者名，默认沿用当前值")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要做的改动")
    args = parser.parse_args(argv)

    user = args.user.strip().lstrip("@")
    if not user or any(ch in user for ch in "/ \t"):
        raise SystemExit("用户名不合法：只填 GitHub 用户名本身")

    data = load_manifest()
    site = data["site"]
    old_user = site.get("github_user") or user
    old_profile = f"https://github.com/{old_user}"
    new_profile = f"https://github.com/{user}"
    old_url = site["url"]
    new_url = f"https://{user.lower()}.github.io"
    old_title = site["title"]
    new_title = args.title.strip() if args.title else old_title
    old_author = site["author"]
    new_author = args.author.strip() if args.author else old_author

    if args.dry_run:
        print(f"[dry-run] profile: {old_profile} -> {new_profile}")
        print(f"[dry-run] url: {old_url} -> {new_url}")
        print(f"[dry-run] title: {old_title} -> {new_title}")
        print(f"[dry-run] author: {old_author} -> {new_author}")
        return 0

    touched: list[str] = []
    for old, new in (
        (old_profile, new_profile),
        (old_url, new_url),
        (old_title, new_title),
        (old_author, new_author),
    ):
        touched += [str(path) for path in replace_all(old, new)]

    site["github_user"] = user
    site["url"] = new_url
    site["title"] = new_title
    site["author"] = new_author
    save_manifest(data)

    write_xml(build_feed(data), FEED)
    write_xml(build_sitemap(data), SITEMAP)
    ROBOTS.write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {new_url}/sitemap.xml\n",
        encoding="utf-8",
    )

    unique = sorted(set(touched))
    print(f"已更新 {len(unique)} 个文件：")
    for name in unique:
        print(f"  - {name}")
    print(f"站点地址：{new_url}")
    print("已重建 feed.xml / sitemap.xml / robots.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
