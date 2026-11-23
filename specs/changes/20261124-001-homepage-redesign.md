# 变更记录 2026-11-24 #001 首页改版为个人主页版式并上线

- 需求：`../REQ-002-homepage-redesign.md`（同时关闭 REQ-001 的 AC-9）
- 项目：`MyBlog/`
- 范围：首页重写、样式系统重写、JS 增量、首次发布到 GitHub Pages
- 结果：`已验收`

## 做了什么

- 首页由「页头 + 文章列表」改为两栏个人主页：左栏标识 / 现在 / 标签 / 时间线，右栏问候语、入口按钮、站点概况、文章卡片、站点卡片、在做的事。
- `assets/style.css` 重写为设计变量 + 组件（`card` / `chips` / `timeline` / `post-card` / `link-card` / `doing`），保留文章页样式并新增 `page-footer` 限宽修饰类。
- `assets/app.js` 增加 `[data-local-time]` / `[data-timezone]` 与文章数、最近更新统计；保留 `escapeHtml` / `formatDate` / `renderPosts` / 主题逻辑。
- `about.html` / `404.html` / `posts/hello-world.html` 页脚加 `page-footer`，避免新样式下页脚铺满全宽。
- 版式参考 xxynet/HomePage，但**未复用其代码、图片或音效**（该仓库无 LICENSE）。
- 首次发布：创建 `WeederRobert/WeederRobert.github.io` 并推送 `main`；Pages 由 legacy 切到 workflow，workflow 为 `configure-pages` 增加 `enablement: true`。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `index.html` | 重写为两栏个人主页 |
| `assets/style.css` | 重写设计系统与响应式 |
| `assets/app.js` | 新增本地时间、站点统计；文章卡片结构改为 `h3.post-title` |
| `about.html` / `404.html` / `posts/hello-world.html` | 页脚加 `page-footer` |
| `.github/workflows/pages.yml` | 增加 `actions/configure-pages@v5`（`enablement: true`） |
| `.gitignore` | 新建：忽略 `_site/` 与系统文件 |
| `README.md` | 新增「设计来源」、首页个性化位置、线上地址 |

## 验证

| 命令 / 操作 | 结果 |
| --- | --- |
| 本地 1280px | 网格 `300px 792px`；`scrollWidth = clientWidth = 1265`；卡片 1 张；统计 1 篇 |
| 本地 375px | 单列 `328px`；`scrollWidth = clientWidth = 360`；无横向滚动 |
| 主题切换 | light → dark，`localStorage` 为 `dark`，刷新保持；图标与 `aria-label` 同步 |
| 静态校验脚本 | `errors: none`（无 BOM、站内链接全通、`script/link/img` 无 http(s) 引用） |
| GitHub Actions | `Deploy to GitHub Pages` = completed / success |
| 线上探测 | `/` 200、`/posts.json` 200、`/assets/style.css` 200（10834 B）、`/posts/hello-world.html` 200、`/feed.xml` 200、`/sitemap.xml` 200 |
| 发布边界 | `/specs/requirements.md` 404、`/scripts/new_post.py` 404（rsync 排除生效） |
| 线上浏览器 | 标题 `WeederRobert`；2.5s 内渲染 1 张卡片；控制台 0 错误；`Asia/Shanghai` 本地时间正常 |

## 新增 / 改动的可复用件

- 组件样式：`.card` / `.chips` / `.timeline` / `.link-card` / `.doing` / `.stats`，about 页可直接复用。
- `assets/app.js`：`updateStats()`（文章数 / 最近更新）、`initLocalTime()`（本地时间 + 时区）。

## 决策与理由

- 参考仓库没有 LICENSE：只参考「左栏个人卡 + 右栏卡片」的通用版式，HTML/CSS/JS 与素材全部原创，头像用文字缩写 + 渐变。
- 保持无构建：与 REQ-001 的「免工具链、可审计」一致，不引入 Vue/Vite。
- Pages 由 legacy 切 workflow：让 workflow 的 `rsync` 排除规则生效，`specs/`、`scripts/` 不对外。

## 遗留与限制

- 只有 1 篇示例文章；标签、时间线、在做的事为静态内容，需手工维护。
- 无评论、搜索、分页（spec 明确不做）。

## 后续

写第二篇：`python scripts/new_post.py --title ... --slug ... --summary ...`，推送后自动发布。
