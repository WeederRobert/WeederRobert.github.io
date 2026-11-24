# REQ-004 本地博客文章编辑器（MyBlog/editor）

- 状态：`done`
- 项目：`MyBlog/`
- 提出：2026-11-24
- 关联：[../README.md](../README.md)（本地预览 / 写新文章）、[REQ-001-github-io-blog.md](REQ-001-github-io-blog.md)（无构建静态站）

## 1. 需求

在 `MyBlog/` 下单独开一个模块 `editor/`：一条命令启动本地网页编辑器（只监听本机、启动时生成一次性访问令牌），浏览器里能浏览 / 搜索 / 按标签筛选已有文章，新建文章，编辑标题、日期、摘要、标签与正文 HTML，右侧实时预览站点真实样式；保存时一次写回文章 HTML、更新 `posts.json`、重建 `feed.xml` 与 `sitemap.xml`，并能打开真实页面。

不要：发布（不 push）、删除文章、图片上传、Markdown 转换、第三方依赖或构建链、对外监听、在编辑器里改站点主题与身份。

## 2. 现状与事实

- 文章清单：`posts.json:1` —— `site`（title / description / author / github_user / url）+ `posts[]`（slug / title / date / summary / tags / file）。
- 现有建页与重建逻辑：[scripts/new_post.py](../scripts/new_post.py) —— `SLUG_RE`、`POST_TEMPLATE`、`load_manifest`、`save_manifest`、`build_feed`、`build_sitemap`、`write_xml`、`rebuild`、`add_post`。
- 跨脚本复用：[scripts/set_site.py:16](../scripts/set_site.py) 已有 `from new_post import FEED, ROOT, SITEMAP, build_feed, ...`，证明「共享一份核心」是既有做法。
- 文章页真实结构：[posts/hello-world.html](../posts/hello-world.html) —— `.topbar` 页头、`.post-header`、`.post-body`、`.post-footer`、`.site-footer.page-footer`。
- CSS 事实：[assets/style.css:499](../assets/style.css) `.topbar`、`:560` `.post-header h1`、`:567` `.post-body`、`:627` `.page-footer`；`git grep -n 'site-header' -- assets` 无结果 —— 即 **`new_post.py` 的 `POST_TEMPLATE` 仍是改版前的 `.site-header` 版式与旧品牌「CM233 的记事本」**，今天用它建页会得到无样式页头。本条一并修正。
- 发布范围：[.github/workflows/pages.yml](../.github/workflows/pages.yml) 的 `rsync` 只排除 `.git` / `.github` / `specs` / `scripts` —— 新增 `editor/` 默认会被发布到站点，需加排除。
- 仓库卫生：`git ls-files | Select-String pycache` 显示 `scripts/__pycache__/new_post.cpython-313.pyc` **已被跟踪**，而 `.gitignore` 未忽略 `__pycache__/`。
- 运行时：本机 `python --version` → `3.13.15`；`new_post.py` 已使用 `datetime.UTC`（3.11+），README 里「Python 3.9+」的说法与之不符。

## 3. 验收标准

| # | 可观察结果 | 验证方式 |
| --- | --- | --- |
| AC-1 | `python editor/server.py --no-browser` 可启动，`GET /api/posts` 返回 200，`site` 与 `posts` 数组条目数等于 `posts.json` | `curl http://127.0.0.1:8765/api/posts` + `python -c` 比对条数 |
| AC-2 | `GET /api/posts/hello-world` 返回的 `body` 与 `posts/hello-world.html` 中 `.post-body` 内容一致（去掉公共缩进后） | 同上 curl，与文件逐字比对 |
| AC-3 | 打开 `hello-world` 原样保存后，`posts/hello-world.html` 与 `feed.xml` / `sitemap.xml` 无任何 diff（模板若漂移必须失败） | 保存前后 `git diff --stat` 为空 |
| AC-4 | 新建文章后：`posts/<slug>.html` 存在且含 `.topbar` 与 `.post-body`；`posts.json` 顶部新增条目；`feed.xml` 含该标题；`sitemap.xml` 含完整 URL | `grep` 四个文件 |
| AC-5 | 非法输入被拒且不落盘：slug 含大写/空格、重复 slug、空标题、坏日期 → HTTP 400 | `curl -X POST` 四种非法体，随后 `git status --short` 不变 |
| AC-6 | 只监听本机：socket 绑定 `127.0.0.1`；`Host` 不是 `127.0.0.1` / `localhost` 的请求返回 403 | `Get-NetTCPConnection -LocalPort 8765` + `curl -H "Host: evil.example"` |
| AC-7 | 浏览器里搜索框输入关键词后列表只剩匹配项；点标签 chip 后只显示该标签文章 | 浏览器实测（`readPage` / 截图） |
| AC-8 | 浏览器里改正文，右侧 iframe 预览在 1 秒内更新且使用站点 CSS（页头、标题渐变、代码块样式与线上一致） | 浏览器实测 + 预览 HTML 与保存结果同源（`/api/render`） |
| AC-9 | 既有 CLI 行为不变：`python scripts/new_post.py --rebuild` 不产生文件 diff；`python scripts/set_site.py --user WeederRobert --dry-run` 正常输出 | 两条命令 + `git status` |
| AC-10 | `python -m unittest discover -s scripts -p "test_*.py"` 全绿（含 hello-world 往返、新建落盘、非法 slug） | 测试输出 |
| AC-11 | 发布产物不含编辑器：workflow 的 `rsync` 行含 `--exclude 'editor'` | `Select-String pages.yml` |
| AC-12 | 没有 Cookie 时 `/api/posts` 返回 403；没有 `?key=` 时 `/editor/` 返回 403 说明页 | `curl` / `scripts/test_editor_auth.py` |
| AC-13 | 带正确 `?key=` 打开 `/editor/` 返回 200 且下发 `myblog_editor` Cookie（`HttpOnly; SameSite=Strict`）；页面加载后地址栏不再含 `key` | `curl -D -` 看响应头 + 浏览器实测 `location.search === ''` |
| AC-14 | 写接口三重门槛：缺 Cookie / 缺 `X-Editor: 1` / `Origin` 不是本机页面，任一不满足都 403 且不写文件 | `scripts/test_editor_auth.py` + `git status` |
| AC-15 | 令牌每次启动重新生成：换一个 token 启动后，旧 Cookie 访问 `/api/posts` 返回 403 | `scripts/test_editor_auth.py::test_restart_with_new_token_rejects_old_cookie` |
| AC-16 | 服务只绑定 `127.0.0.1`（`Get-NetTCPConnection` 的 LocalAddress），且伪造 `Host: evil.example` 返回 403 | 命令 + `curl -H "Host: ..."` |

## 4. 影响面

| 类型 | 位置 | 说明 |
| --- | --- | --- |
| 代码 | `scripts/blog_core.py` | 新增共享核心（清单 / 建页 / 解析 / feed / sitemap） |
| 代码 | `scripts/new_post.py` | 改为调用 `blog_core`，模板修正为当前 `.topbar` 版式 |
| 代码 | `scripts/set_site.py` | 导入来源改为 `blog_core` |
| 代码 | `editor/server.py` | 新增：stdlib HTTP + JSON API + 静态文件 |
| 代码 | `editor/index.html` / `editor/editor.css` / `editor/editor.js` | 新增：编辑器 UI |
| 测试 | `scripts/test_blog_core.py` | 新增 stdlib `unittest` |
| 文档 | `README.md` | 新增「本地编辑器」章节、目录树、Python 版本口径 |
| 文档 | `specs/requirements.md`、`specs/changes/` | 登记与留痕 |
| 配置 | `.github/workflows/pages.yml` | `rsync` 排除 `editor` |
| 配置 | `.gitignore` | 忽略 `__pycache__/` 与 `*.pyc`，并取消跟踪已有 pyc |

## 5. 复用基线

可直接复用（禁止重复实现）：

- `scripts/new_post.py` 中的 `SLUG_RE` / `POST_TEMPLATE` / `load_manifest` / `save_manifest` / `parse_date` / `display_date` / `post_url` / `build_feed` / `build_sitemap` / `write_xml` / `rebuild` —— 整体迁进 `scripts/blog_core.py`，`new_post.py` 与 `editor/` 共用同一份。
- `assets/style.css` / `assets/app.js` —— 预览 iframe 直接加载，不另写样式。
- `posts.json` —— 唯一文章清单，编辑器不引入第二个索引文件。

本次新增的可复用件：

- 落点：`scripts/blog_core.py`
- 契约：
  - `load_manifest() -> dict`、`save_manifest(data) -> None`
  - `render_post_page(site, entry, body) -> str`、`parse_post_page(text) -> dict`、`read_post(entry) -> dict`（返回 `drift` 列表标记页面与清单不一致的字段）
  - `save_post(slug, title, summary, tags, date, body, create_only=False) -> dict`：校验 → 写 HTML → 更新清单 → 重建 feed / sitemap
  - `default_body(summary) -> str`、`rebuild(dry_run=False) -> None`
- 调用方：`scripts/new_post.py`、`scripts/set_site.py`、`editor/server.py`、`scripts/test_blog_core.py`
- 为什么不复用现有：现有逻辑全部长在 `new_post.py` 这个 CLI 脚本里（`add_post` 直接 `SystemExit` + `print`），没有可复用的校验/渲染/解析入口，编辑器直接 import 它会把 CLI 的退出行为带进 HTTP 处理器。

## 6. 决策与取舍

| 决策 | 备选方案 | 为什么选这个 |
| --- | --- | --- |
| 本地网页版（stdlib `ThreadingHTTPServer` + 浏览器 UI） | Tkinter 窗口 / 纯 CLI 向导 | 能直接加载站点 CSS 做真实预览；Tkinter 嵌 HTML 需要第三方浏览器组件，违背零依赖；CLI 做不到所见即所得 |
| 正文编辑 HTML 片段（去公共缩进显示，保存时恢复 6 空格） | 自写 Markdown 转换 | 站内既有文章全是 HTML，README 明确「正文是 HTML」；自写转换器会与现有页面格式分叉 |
| 预览由服务端 `/api/render` 用同一 `render_post_page` 生成 | 前端手拼预览 DOM | 预览与保存同一口径，模板改动后预览不会说谎 |
| 抽出 `blog_core.py` | 编辑器内复制一份 feed / sitemap 逻辑 | 复制必然出现两处口径漂移；`set_site.py` 本来就靠 import 复用，说明共享是既有约定 |
| 保存时整页重新渲染 | 只替换 `.post-body` 片段 | 整页渲染才能让模板修正对旧文章生效；用「去 6 空格缩进 → 恢复 6 空格」保证往返零 diff（AC-3） |
| slug 建好后不可改 | 支持改名 | 改名要同步改清单、文件名与外链，风险大；需要时另立 REQ |
| 编辑器写盘接口要求 `X-Editor: 1` 头 + 只监听 `127.0.0.1` + 校验 `Host` | 直接裸公开端口 | 本机其他页面 / DNS rebinding 不得随意写文件 |
| 启动时生成随机 token（`secrets.token_urlsafe`）+ `HttpOnly; SameSite=Strict` Cookie，并用 `hmac.compare_digest` 比较 | 账号密码体系 / 只靠端口不公开 | 需求是「单人本机」：没有数据库、没有多用户，随机 token 就能把「谁启动谁使用」定死；重启即吊销，比持久密码更安全也更好解释。账号体系留给将来真正的远程场景 |
| 写接口再校验同源 `Origin` | 只靠自定义请求头 | 自定义头挡住简单表单 CSRF，但显式校验 Origin 把「跨站 fetch」也一并关掉；两者都便宜的几行代码 |
| 页面加载后 `history.replaceState` 抹掉 `?key=` | 链接一直留在地址栏 | 截图、录屏、浏览器历史都不留凭证；Cookie 已在内存中，不需要 key 二次出现 |

## 7. 不做的事

- 删除文章、重命名 slug、草稿态（不登记 `posts.json` 的中间态）、图片上传与裁剪。
- Markdown 输入、WYSIWYG（`contenteditable`）、语法高亮、自动保存。
- 发布 / push / 调用 GitHub API、任何账号与权限。
- 改站点主题、站点身份（`set_site.py` 负责）、改 CSS / JS。
- 对外监听、鉴权登录、多用户、远程协作。

## 8. 口径与边界

- 正文存储位置：`posts/<slug>.html` 的 `.post-body` 内 HTML；文件内缩进 6 空格，编辑器内按公共缩进去掉显示。
- 事实源：`posts.json` 的 `title` / `date` / `summary` / `tags` 为列表、RSS、sitemap 的事实源；页面里的 `<h1>`、`<meta description>`、`<span class="tag">` 由它们渲染。若页面与清单不一致，`read_post` 返回 `drift`，UI 提示「保存后以表单为准」。
- 日期：存 `YYYY-MM-DD`，页面显示 `YYYY年M月D日`（沿用 `display_date`）。
- 保存即重建 `feed.xml` / `sitemap.xml`；「只重建」仍走 CLI `--rebuild`。
- 未确认项（用户不在线，按 autopilot 默认推进）：形态=网页版、正文=HTML 片段、功能=列表/搜索/标签筛选/新建/编辑/保存/预览、无删除、`editor/` 不发布。若与实际意图不符，先改本 REQ 再改代码。
- 已知限制：预览 iframe 通过 `srcdoc` 加载，正文里的 `<script>` 不会被执行（正文约定是静态 HTML）；预览与线上差异仅限域名与绝对链接。
- 访问控制口径：只绑定 `127.0.0.1` → 每进程随机 `key`（终端打印、不落盘）→ 换 `HttpOnly; SameSite=Strict` Cookie → 写接口再验 `Origin` + `X-Editor` → `Host` 白名单。撤销访问的唯一动作是重启服务。
- 明确不保证：同一台机器上的其他进程 / 其他系统账号可以绕过（它们能直接读文件，也能伪造请求头）；不提供任何公网入口与账号体系。远程使用必须先立新 REQ（反向代理 + 认证 + TLS）。

## 9. 变更记录

| 日期 | 记录 | 结果 |
| --- | --- | --- |
| 2026-11-24 | `changes/20261124-005-local-post-editor.md` | 已验收 |
