# 变更记录 2026-11-23 #002 站点身份统一为 WeederRobert

- 需求：`../REQ-001-github-io-blog.md`
- 项目：`MyBlog/`
- 范围：GitHub 用户名、站点域名、标题、作者，以及新增 `scripts/set_site.py`
- 结果：`已验收`

## 做了什么

- 初版按 `git config --global user.name = CM233` 填了身份；用户确认实际 GitHub 用户名为 `WeederRobert`，全站改回。
- 把身份收敛到 `posts.json` 的 `site.github_user` / `url` / `title` / `author`，新增 `scripts/set_site.py` 一条命令替换并重建元数据。
- `specs/` 视为历史记录，不参与替换。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `scripts/set_site.py` | 新建：`--user` / `--title` / `--author` / `--dry-run`，复用 `new_post` 的 feed / sitemap 生成器 |
| `posts.json` | `github_user=WeederRobert`、`url=https://weederrobert.github.io`、`title`/`author=WeederRobert` |
| `index.html` / `about.html` / `404.html` / `posts/hello-world.html` | 标题、品牌名、页脚 GitHub 链接与作者名 |
| `feed.xml` / `sitemap.xml` / `robots.txt` | 重建，域名换为 `weederrobert.github.io` |
| `README.md` | 改为「一条命令改身份」的说明 |

## 验证

| 命令 / 操作 | 结果 |
| --- | --- |
| `python scripts/set_site.py --user WeederRobert --title "WeederRobert 的记事本" --author WeederRobert` | 更新 5 个文件，重建 3 个元数据文件 |
| `Select-String 'CM233\|cm233'`（站点文件） | 0 命中 |
| `posts.json` 读取 | `title=WeederRobert 的记事本`、`author=WeederRobert`、`github_user=WeederRobert`、`url=https://weederrobert.github.io` |
| `feed.xml` / `sitemap.xml` / `robots.txt` | `link` / `loc` / `Sitemap` 均为 `https://weederrobert.github.io` |
| 4 个 HTML 抽查 | `<title>`、`.brand`、页脚链接、版权作者均为 WeederRobert |

## 新增 / 改动的可复用件

- `scripts/set_site.py`：身份变更的唯一入口；换域名或改标题同样是这一条命令。

## 决策与理由

- 不再手改散落 URL：此前正是因为标题 / 作者 / 链接分散在 5 个 HTML 里才填错，脚本化后错误面收敛到 `posts.json` 一处。

## 遗留与限制

- AC-9 仍未验证（取决于是否已部署）。
- 若希望显示名与 GitHub 用户名不同，用 `--user <handle> --title "<显示名>" --author "<显示名>"` 分开指定。

## 后续

部署后回填 AC-9。
