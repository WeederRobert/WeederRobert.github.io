# 变更记录 2026-11-24 #005 本地博客文章编辑器（`editor/`）

- 需求：[`../REQ-004-local-post-editor.md`](../REQ-004-local-post-editor.md)
- 项目：`MyBlog/`
- 范围：新增 `editor/` 模块；抽出 `scripts/blog_core.py` 共享层；修正 `new_post.py` 过期模板；编辑器访问控制
- 结果：`已验收`

## 做了什么

1. **抽出共享核心** `scripts/blog_core.py`：清单读写、`SLUG_RE`、文章页渲染 / 解析、feed / sitemap 构建与写盘。
   `new_post.py`、`set_site.py`、`editor/server.py`、测试都指向它，不再各自维护一份。
2. **修掉过期模板**：`new_post.py` 原来的 `POST_TEMPLATE` 还是改版前 `.site-header` + 「CM233 的记事本」，
   而 `assets/style.css` 里只剩 `.topbar`。新模板按 `posts/hello-world.html` 的现行结构渲染，品牌与标题来自 `posts.json`。
3. **新增编辑器** `editor/`：`server.py`（stdlib `ThreadingHTTPServer` + JSON API）、`index.html` / `editor.css` / `editor.js`。
   左栏列表 + 搜索 + 标签筛选，右栏字段表单 + HTML 片段工具栏 + 实时预览，`Ctrl+S` 保存。
4. **访问控制**：
   - 只绑定 `127.0.0.1`，不提供 `--host`；
   - 每次启动 `secrets.token_urlsafe(24)` 生成 key，只打印到终端、不落盘；
   - `GET /editor/?key=…` 校验通过后下发 `HttpOnly; SameSite=Strict` 会话 Cookie，前端 `history.replaceState` 抹掉地址栏里的 key；
   - 其余所有 GET（含静态文件）要求 Cookie；写接口再加 `Origin` 同源 + `X-Editor: 1`；
   - `Host` 只接受 `127.0.0.1` / `localhost`，防 DNS rebinding；
   - 未授权请求返回 403：页面请求给一页中文说明，API 给 JSON。
5. **仓库卫生**：`.gitignore` 增加 `__pycache__/`、`*.pyc`，并 `git rm --cached` 掉误提交的 `scripts/__pycache__/new_post.cpython-313.pyc`。
6. **发布范围**：workflow 的 `rsync` 增加 `--exclude 'editor'`，编辑器源码不上线。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `scripts/blog_core.py` | 新增：清单 / 渲染 / 解析 / feed / sitemap 共享核心 |
| `scripts/new_post.py` | 改为调用 `blog_core`，模板换成现行 `.topbar` 版式，CLI 参数与提示保持一致 |
| `scripts/set_site.py` | 改为 `from blog_core import ...` |
| `scripts/test_blog_core.py` | 新增：往返、落盘、非法输入、CRLF 保持 |
| `scripts/test_editor_auth.py` | 新增：令牌 / Cookie / Origin / Host / 重启吊销 |
| `editor/server.py` | 新增：HTTP 服务、JSON API、访问控制、静态文件 |
| `editor/index.html` / `editor.css` / `editor.js` | 新增：编辑器 UI |
| `.github/workflows/pages.yml` | `rsync` 排除 `editor` |
| `.gitignore` | 忽略 Python 缓存 |
| `README.md` | 新增「本地编辑器」与「访问控制」章节、目录树、Python 版本改成 3.11+ |
| `specs/requirements.md` | 登记 REQ-004 |
| `specs/REQ-004-local-post-editor.md` | 新增本需求规范 |

## 验证

| 命令 / 操作 | 实测结果 |
| --- | --- |
| `python -m unittest discover -s scripts -p "test_*.py"` | `Ran 9 tests in 1.064s` / `OK`（blog_core 4 个 + 编辑器鉴权 5 个） |
| `python scripts/new_post.py --rebuild` | 输出「已重新生成 feed.xml 与 sitemap.xml」，随后 `git status` 无 feed / sitemap 差异（核心逻辑与旧实现等价） |
| `python scripts/set_site.py --user WeederRobert --dry-run` | 正常输出 4 行 dry-run，退出码 0 |
| API 冒烟（临时脚本，用后已删） | `GET /api/posts` 200 / 1 篇；`GET /api/posts/hello-world` `drift=[]`；`POST /api/render` 含 `header.topbar`；保存既有文章后页面字节完全一致 |
| 非法输入 | slug 非法、URL 与 body slug 不一致、标题为空、日期为空、日期非法 → 全部 `400`，文章文件字节不变 |
| 鉴权（curl） | 无 Cookie `/api/posts` → `403`；`/editor/` 无 key → `403`；`?key=wrong` → `403`；正确 key → `200` + `Set-Cookie: myblog_editor=…; Path=/; HttpOnly; SameSite=Strict`；带 Cookie → `200`；`Host: evil.example` → `403`；POST 缺 `X-Editor` → `403`；`Origin: http://evil.example` → `403` |
| 监听地址 | `Get-NetTCPConnection -LocalPort 8765` → `LocalAddress 127.0.0.1` |
| 浏览器（1280×960 窗口） | 列表 2 篇；搜索「为什么」→ 1 篇；点「静态站」chip → 1 篇；改正文 1.2s 内 iframe 出现新标题与段落，页头 / 标题 / 代码块样式来自 `assets/style.css` |
| 浏览器新建 | 「新建」填标题/slug/摘要/标签/正文 → `Ctrl+S` 提示「已新建 posts/ui-smoke.html，重建 feed.xml / sitemap.xml」，列表变 3 篇、标签 chip 多出「工具」、保存后 slug 锁定（验证后已删） |
| 浏览器保存既有文章 | 载入 hello-world 直接 `Ctrl+S`：提示「已保存 posts/hello-world.html」，`git status` 无该文件 / `posts.json` / feed / sitemap 差异；标签保持 `["站点","静态站"]` |
| `Select-String pages.yml "exclude 'editor'"` | 命中第 30 行 |

## 新增 / 改动的可复用件

- `scripts/blog_core.py`
  - `load_manifest()` / `save_manifest(data)`
  - `render_post_page(site, entry, body) -> str`、`parse_post_page(text) -> dict`、`read_post(entry) -> dict`（带 `drift`）
  - `save_post(slug, title, summary, tags, date, body, create_only=False) -> dict`
  - `default_body(summary)`、`rebuild(dry_run=False)`、`build_feed` / `build_sitemap` / `write_xml`
  - 调用方：`scripts/new_post.py`、`scripts/set_site.py`、`editor/server.py`、两个测试文件
- `editor/server.py`：`create_server(port, token)` / `make_handler(token)`，供鉴权测试直接起服务

## 决策与理由

- **抽 `blog_core.py` 而不是让编辑器 import `new_post.py`**：`new_post.py` 的 `add_post` 直接 `SystemExit` + `print`，是 CLI 形状；编辑器要的是可返回错误值的函数。抽出来后 `set_site.py` 的既有复用也一并落到同一层。
- **正文仍是 HTML**：站内既有文章与 README 都明确「正文是 HTML」，自写 Markdown 转换会让存量文章与新文章两种格式并存。
- **保存整页重渲染**：这样才能把模板修正作用到旧文章；用「去掉 6 空格公共缩进 ↔ 保存时恢复」保证往返零 diff，实测 hello-world 字节一致。
- **偏离 spec 的三处修正**（已回写到 REQ-004 的验收标准）：
  1. 保存路径不再对日期做「静默回落今天」，改为严格校验 → `400`；回落只用于预览 `/api/render`；
  2. 写文件保留原文件行尾风格（Windows 工作区 CRLF 时不再整文件变 LF），否则「打开即保存」会产生全文件 diff；
  3. 标签输入统一用逗号往返（列表展示仍用 `·`），避免「站点 · 静态站」被当成单个标签写回。

## 遗留与限制

- 未做：删除文章、slug 改名、图片上传、草稿态、自动保存、发布 / push。
- 访问控制只针对「其他设备 / 其他网页」；同一台机器上的其他进程或系统账号仍可直接读写仓库文件，这属于操作系统权限范畴。
- 本次只提交到本地，未推送；线上生效需要 `git push` 后由 Actions 发布。

## 后续

需要远程写作时另立 REQ：反向代理 + 账号认证 + TLS，而不是把当前服务直接开出去。
