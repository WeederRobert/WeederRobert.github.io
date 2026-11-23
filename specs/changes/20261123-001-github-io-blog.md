# 变更记录 2026-11-23 #001 搭建 GitHub Pages 个人博客

- 需求：`../REQ-001-github-io-blog.md`
- 项目：`MyBlog/`
- 范围：无构建静态站（4 个页面 + 主题 + 文章清单）+ Pages 发布流水线
- 结果：`部分完成`（AC-1~AC-8 通过；AC-9 待用户开启 Pages）

## 做了什么

- 4 个页面：首页（文章列表）、关于、404、示例文章；无构建、无第三方脚本。
- 主题：CSS 变量 + `<head>` 内联预设（避免闪白）+ `localStorage` 记忆；切换按钮同步 `aria-label`。
- 文章清单：`posts.json` 为唯一事实源，`assets/app.js` 的 `renderPosts()` 渲染首页。
- 生成器：`scripts/new_post.py` 一次写「文章页骨架 + `posts.json` + `feed.xml` + `sitemap.xml`」，仅用标准库。
- 发布：GitHub Actions `upload-pages-artifact` + `deploy-pages`，用 `rsync` 排除 `.git/.github/specs/scripts`。
- 元数据：`.nojekyll`、`robots.txt`、RSS、sitemap。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `index.html` / `about.html` / `404.html` / `posts/hello-world.html` | 新建页面 |
| `assets/style.css` | 新建：主题变量、卡片、正文排版、响应式 |
| `assets/app.js` | 新建：主题切换、`escapeHtml` / `formatDate` / `renderPosts`、年份填充 |
| `posts.json` | 新建：站点配置 + 文章清单 |
| `scripts/new_post.py` | 新建：文章生成器与 RSS / sitemap 生成 |
| `feed.xml` / `sitemap.xml` / `robots.txt` / `.nojekyll` | 新建 |
| `.github/workflows/pages.yml` | 新建：组装 `_site` 并发布 Pages |
| `README.md` | 新建：结构、写作流程、部署步骤、个性化说明 |

## 验证

| 命令 / 操作 | 结果 |
| --- | --- |
| `python -m http.server 8000` + `Invoke-WebRequest` | `/` 200（1996 bytes）；`posts.json` 1 条；`posts/hello-world.html` 200；`feed.xml` 200；`style.css` 200；`app.js` 200 |
| 静态校验脚本 | `ALL OK`；`posts=1 html=4`；无 BOM；站内链接全部可解析；`script/link` 无 http(s) 外链 |
| 浏览器实测（首页） | 标题、简介、1 张文章卡片（2026年11月23日 + 2 个标签） |
| 浏览器实测（文章页） | 标题 / 日期 / 5 个小节 / 引用块 / 返回链接齐全 |
| 主题切换 | 初始 dark → 点击后 light，`localStorage='light'`，`aria-label` 变「切换到深色模式」；刷新后保持 light |
| 375px 视口 | `scrollWidth=375`、`clientWidth=375`、`body.scrollWidth=375`（无横向滚动） |
| 生成器自检（临时副本） | 新增 tmp-test 后 `posts=2`、feed 2 item（新稿在前）、sitemap 4 URL、UTF-8 无 BOM、占位符全部替换 |

## 新增 / 改动的可复用件

- `assets/app.js`：`escapeHtml` / `formatDate` / `renderPosts` / 主题初始化，任何页面可复用。
- `scripts/new_post.py`：`build_feed` / `build_sitemap` / `add_post` / `--rebuild`，`set_site.py` 直接复用。

## 决策与理由

- 偏离 spec：无。
- 实施中发现身份信息（标题 / 作者 / 链接）会散落多处，因此在 #002 追加 `set_site.py` 收敛。

## 遗留与限制

- AC-9 需用户创建 `<username>.github.io` 仓库、推 `main`、在 Settings → Pages 选 GitHub Actions。
- 无评论 / 搜索 / 分页（spec 明确不做）。

## 后续

用户完成 Pages 设置后回填 AC-9，需求状态转 `done`。
