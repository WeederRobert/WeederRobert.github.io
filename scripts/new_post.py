"""新建文章并同步 posts.json / feed.xml / sitemap.xml（仅用标准库）。

用法：
    python scripts/new_post.py --title "标题" --slug my-post --summary "摘要" --tags 随笔,工具
    python scripts/new_post.py --rebuild          # 只按 posts.json 重算 feed / sitemap
    python scripts/new_post.py ... --dry-run      # 只打印将要做的事

逻辑在 `blog_core.py`，与 `editor/` 的保存走同一条路径。
"""

from __future__ import annotations

import argparse
from datetime import datetime

from blog_core import POSTS_DIR, ROOT, default_body, rebuild, save_post


def add_post(title: str, slug: str, summary: str, tags: list[str], date: str, dry_run: bool) -> None:
    target = POSTS_DIR / f"{slug}.html"
    if dry_run:
        print(f"[dry-run] 将新建 {target.relative_to(ROOT)}")
        print(f"[dry-run] 将把 {slug}（{date}）登记到 posts.json")
        print("[dry-run] 将重新生成 feed.xml 与 sitemap.xml")
        return

    try:
        save_post(
            slug=slug,
            title=title,
            summary=summary,
            tags=tags,
            date=date,
            body=default_body(summary),
            create_only=True,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None

    print(f"已新建 {target.relative_to(ROOT)}，并更新 posts.json / feed.xml / sitemap.xml")
    print("下一步：编辑正文（或用 python editor/server.py 打开编辑器），然后 python -m http.server 8000 本地预览")


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
