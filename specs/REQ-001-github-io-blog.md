# REQ-001 搭建 GitHub Pages 个人博客

- 状态：`done`（AC-1~AC-9 全部通过；线上 <https://weederrobert.github.io/>）
- 项目：`MyBlog/`
- 提出：2026-11-23
- 关联：[README.md](../README.md)

## 1. 需求

在空目录 `MyBlog/` 里搭一个可发布到 GitHub Pages 的个人博客：能写文章、首页能列出文章、长期好维护。

不要：CMS 后台、评论、站内搜索、多语言、分页。

## 2. 现状与事实

- `MyBlog/` 为空目录（0 个文件），无历史约定可继承。
- 工作区无 Node / Ruby 前端工具链；Python 可用，规范要求 Windows 下不额外装工具链。
- 用户确认 GitHub 用户名为 `WeederRobert`（`git config user.name` 亦为该值；初次按 git 全局 `CM233` 填错，已修正，见 `20261123-002`）。

## 3. 验收标准

| # | 可观察结果 | 验证方式 |
| --- | --- | --- |
| AC-1 | 首页显示站点标题、简介，以及按日期倒序的文章卡片 | 本地 HTTP 预览 |
| AC-2 | 点卡片进入 `posts/hello-world.html`，标题 / 日期 / 正文 / 返回链接齐全 | 浏览器实测 |
| AC-3 | `posts.json` 能被 `JSON.parse` 解析，条数与首页卡片一致 | `python -c` 校验 |
| AC-4 | 站内相对链接 0 死链 | 脚本扫描 |
| AC-5 | 无第三方 JS / CSS 依赖，断网也能打开 | 检查 HTML 引用 |
| AC-6 | 深 / 浅色跟随系统；手动切换后刷新仍保持 | 浏览器实测 |
| AC-7 | 375px 宽无横向滚动（`scrollWidth === clientWidth`） | 浏览器实测 |
| AC-8 | `feed.xml` / `sitemap.xml` 是合法 XML，且包含全部文章 | XML 解析校验 |
| AC-9 | 推送 `main` 后 Actions 发布成功，站点首页 200 | 用户开启 Pages 后实测（外部步骤） |

## 4. 影响面

| 类型 | 位置 | 说明 |
| --- | --- | --- |
| 代码 | `index.html` / `about.html` / `404.html` / `posts/hello-world.html` | 4 个页面，无构建 |
| 代码 | `assets/style.css` / `assets/app.js` | 主题与文章列表渲染 |
| 数据 | `posts.json` | 文章清单（唯一事实源） |
| 数据 | `feed.xml` / `sitemap.xml` / `robots.txt` / `.nojekyll` | 站点元数据 |
| 工具 | `scripts/new_post.py` | 新建文章 + 同步清单 / RSS / sitemap（仅 stdlib） |
| 工具 | `scripts/set_site.py` | 一条命令改用户名 / 标题 / 作者并重建 feed、sitemap、robots |
| CI | `.github/workflows/pages.yml` | 发布到 GitHub Pages |
| 文档 | `README.md` | 结构、写作流程、部署步骤、占位清单 |
| 文档 | `specs/` | 需求登记、本 spec、变更记录 |

## 5. 复用基线

- 复用：系统字体栈；CSS 变量统一主题；`posts.json` 作为唯一文章清单；Python `pathlib` + `json` + `xml.etree` 生成 RSS / sitemap。
- 本次新增的可复用件：
  - `assets/app.js`：主题切换 + 从 `posts.json` 渲染文章列表，其他页面可直接复用同一套逻辑。
  - `scripts/new_post.py`: `new_post()` 一次完成「文章页 + 清单 + RSS + sitemap」四处更新，避免手工漏改。
  - `scripts/set_site.py`: 复用 `new_post` 的 feed / sitemap 生成器，把身份信息收敛成一处可替换的配置。

## 6. 决策与取舍

| 决策 | 备选方案 | 为什么选这个 |
| --- | --- | --- |
| 纯静态 HTML / CSS / JS，免构建 | Jekyll / Astro / Hugo | Windows 免装工具链；Pages 直接托管；源码可读可审计。代价：文章清单靠生成器维护 |
| `posts.json` 作唯一清单，前端 `fetch` 渲染 | 写死在 `index.html` | 单一事实源，生成器与页面共用；代价：本地预览需起 HTTP 服务（README 已写明） |
| GitHub Actions 发布 | Pages 传统「分支直出」 | 发布过程可审计、可控；代价：需要一次性在仓库设置里选 GitHub Actions |
| 页面用相对路径 | 根路径 `/assets/...` | 兼容以后改成项目页（`/<repo>/` 子路径） |
| 文章正文写 HTML，生成器给骨架 | 前端渲染 Markdown | 零依赖、无首屏闪白、SEO 友好；写作时只改正文段落 |

## 7. 不做的事

- 评论、搜索、分页、多语言、CMS、图片自动压缩、构建产物缓存。
- 不引入 npm / Ruby / 任何前端框架或 CDN。

## 8. 口径与边界

- GitHub 用户名已确认为 `WeederRobert`：`posts.json` 的 `site.github_user` 是唯一配置源，改身份一律跑 `scripts/set_site.py`，不要手改散落的 URL。
- 仓库要命名为 `<username>.github.io` 才得到根域名；改成项目仓库也能用，但 URL 带子路径（相对路径已兼容）。
- AC-9 已关闭：仓库 `WeederRobert/WeederRobert.github.io` 已创建，Pages 采用 `build_type=workflow`，`Deploy to GitHub Pages` 成功，首页 200。
- 文章日期统一 `YYYY-MM-DD`（UTC 日期，不带时间，避免时区歧义）。

## 9. 变更记录

| 日期 | 记录 | 结果 |
| --- | --- | --- |
| 2026-11-23 | [20261123-001](changes/20261123-001-github-io-blog.md) | 已验收（AC-1~AC-8 本地实测；AC-9 待用户开启 Pages） |
| 2026-11-23 | [20261123-002](changes/20261123-002-site-identity.md) | 已验收（身份统一为 WeederRobert，AC-9 状态不变） |
| 2026-11-24 | [20261124-001](changes/20261124-001-homepage-redesign.md) | AC-9 通过：线上 <https://weederrobert.github.io/> 返回 200 |
