# MyBlog

无构建的静态个人博客，托管在 GitHub Pages。只有 HTML / CSS / JavaScript 和一份 `posts.json`。

**线上地址：<https://weederrobert.github.io/>**

- 站点入口：[index.html](index.html)
- 文章目录：[posts/](posts/)
- 文章清单：[posts.json](posts.json)（首页、RSS、sitemap 的唯一事实源）
- 需求与变更记录：[specs/requirements.md](specs/requirements.md)（登记表 + 每条 REQ 的 spec 与 `specs/changes/`）

## 目录

```
MyBlog/
├── index.html / about.html / 404.html
├── assets/            # style.css + app.js（主题与文章列表）
├── posts/             # 文章页
├── posts.json         # 站点信息 + 文章清单
├── feed.xml / sitemap.xml / robots.txt
├── .nojekyll          # 关闭 Pages 的 Jekyll 处理
├── start-editor.sh    # 起编辑器的 bash 脚本（不发布）
├── editor/            # 本地文章编辑器（不发布）
├── scripts/           # blog_core.py + new_post.py / set_site.py（不发布）
├── .github/workflows/pages.yml
└── specs/             # 需求规范与变更记录（不发布）
```

所有页面共用 `.topbar` 顶部固定导航（`position: sticky`，高度由 `--topbar-h` 控制，侧栏粘连偏移也随之计算）。

## 本地预览

首页用 `fetch` 读 `posts.json`，直接双击 HTML 会被浏览器的同源策略拦截，需要起一个静态服务：

```powershell
cd d:\Workspace\Projects\MyBlog
python -m http.server 8000
# 打开 http://localhost:8000
```

## 本地编辑器

`editor/` 是只用标准库的本地网页编辑器：左栏文章列表（可搜索、按标签筛选），右栏改标题 / 日期 / 摘要 / 标签 / 正文，下方按站点真实样式实时预览；保存会一次写回文章 HTML、更新 `posts.json`、重建 `feed.xml` 与 `sitemap.xml`。

```powershell
cd d:\Workspace\Projects\MyBlog
python editor/server.py                     # 终端会打印一次性链接 http://127.0.0.1:8765/editor/?key=…
python editor/server.py --port 8800 --no-browser
```

Git Bash / WSL / Linux / macOS 下用等价脚本（会先查 Python 版本与端口占用）：

```bash
./start-editor.sh                 # 默认 8765
./start-editor.sh --port 8800     # 换端口
MYBLOG_EDITOR_PORT=8800 ./start-editor.sh
```

脚本只做三件事：找 `python3`/`python` 并确认 ≥ 3.11、检查端口是否被占用、`exec python -u editor/server.py "$@"`；
其余行为（随机 key、浏览器、访问控制）都在 `editor/server.py` 里，不在脚本里重复。

- 正文是 HTML 片段（`<p>` / `<h2>` / `<ul>` / `<pre><code>` / `<blockquote>`）。文件里正文缩进 6 空格，编辑器内按公共缩进去掉显示，保存时恢复，所以「打开再保存」不产生 diff。
- 预览与保存调用同一个渲染函数（`scripts/blog_core.py` 的 `render_post_page`），预览就是保存后的样子。
- slug 建好之后不可改；删除文章、发布、图片上传都不在编辑器范围内。

### 访问控制（谁能打开）

编辑器会**自己写盘**，所以按「单人本机工具」设计：启动时生成一次性 `key`，只有拿到这个链接的人能用。

| 手段 | 挡住什么 | 挡不住什么 |
| --- | --- | --- |
| 只绑定 `127.0.0.1` | 同一局域网 / 外网的其他设备直接连不上，不需要防火墙配合 | 同一台电脑上的其他进程、其他 Windows 账号 |
| 启动时随机 `key`（`secrets.token_urlsafe`），只在终端打印、不落盘 | 不知道 key 打不开页面、调不到任何 `/api/*`；服务重启后旧链接与旧 Cookie 立即失效 | 你主动把链接发出去，或终端输出被录屏 / 记日志 |
| 校验通过后下发 `HttpOnly; SameSite=Strict` 会话 Cookie，页面加载后立刻从地址栏抹掉 `?key=` | 第三方站点带不上你的凭证；截图 / 历史记录里不留 key | 同一个浏览器里你自己装的恶意扩展 |
| 写接口要求同源 `Origin` + `X-Editor: 1` | 别的网页借你的浏览器发 POST 改文章（CSRF） | 本机进程直接用 curl 伪造请求头 |
| `Host` 只接受 `127.0.0.1` / `localhost` | DNS rebinding：把恶意域名解析到 `127.0.0.1` 再绕过同源 | — |

结论：**它保证「局域网/外网的人进不来、别的网页改不了你的文章、旧链接过期即失效」，不保证「同机其他程序读不到你的草稿」** —— 那需要操作系统账号 / 文件权限或真正的账号体系。

- 撤销访问：重启服务（key 重新生成）；或清掉浏览器里的 `myblog_editor` Cookie。
- 不要把它暴露到公网：没有登录、没有限速、写盘无二次确认。要远程用，得另做「反向代理 + 认证 + TLS」的方案（另一个 REQ），而不是把端口开出去。

## 写新文章

用上面的 [本地编辑器](#本地编辑器)，或者走命令行：

```powershell
python scripts/new_post.py --title "标题" --slug my-post --summary "一句话摘要" --tags 随笔,工具
```

一条命令做四件事：新建 `posts/my-post.html` 骨架 → 在 `posts.json` 顶部登记 → 重新生成 `feed.xml` 与 `sitemap.xml`。
然后编辑 `posts/my-post.html` 里 `<div class="post-body">` 的正文。

只改了摘要或日期、想重算 feed 与 sitemap：

```powershell
python scripts/new_post.py --rebuild
```

想先看清会改什么：

```powershell
python scripts/new_post.py --title ... --slug ... --dry-run
```

手动方式（不用脚本）：复制 `posts/hello-world.html`，改标题与日期，再同步 `posts.json`、`feed.xml`、`sitemap.xml`。
脚本依赖 Python 3.11+（用到 `datetime.UTC`）与标准库，不需要 `uv` 或任何第三方包；编辑器也一样。

## 部署

1. GitHub 新建仓库 `<你的用户名>.github.io`（要用根域名就必须叫这个名字）。
2. 把本目录推到该仓库的 `main` 分支。
3. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**。
4. 之后每次 push 到 `main`，[.github/workflows/pages.yml](.github/workflows/pages.yml) 自动发布；首次进度看仓库 Actions 页。

发布内容是仓库里除 `.git` / `.github` / `specs` / `scripts` / `editor` / `start-editor.sh` 之外的文件（见 workflow 里的 `rsync` 行），所以规格、脚本与本地编辑器不会出现在站点上。

## 改成你自己的信息

站点身份用一条命令统一改（用户名 / 标题 / 作者，并重建 feed、sitemap、robots）：

```powershell
python scripts/set_site.py --user WeederRobert --title "WeederRobert 的记事本" --author WeederRobert
```

它会替换 `posts.json` 的 `site.*`、所有页面的页脚 GitHub 链接与站点标题、以及本 README，然后重建 `feed.xml` / `sitemap.xml` / `robots.txt`。
`specs/` 视为历史记录，不参与替换。

其余个性化项：

| 文件 | 位置 | 当前值 |
| --- | --- | --- |
| `posts.json` | `site.title` / `description` / `author` / `url` | WeederRobert / … / `https://weederrobert.github.io` |
| `index.html` | `<title>`、`meta description`、`.hero` 问候语与简介、`.chips` 标签、`.timeline` 时间线、`.doing` 在做的事 | |
| `about.html` | 正文 | |
| 各页面页脚 | GitHub 链接 | `https://github.com/WeederRobert` |
| `feed.xml` / `sitemap.xml` | 域名 | 改完 `posts.json` 的 `site.url` 后跑 `--rebuild` |
| `robots.txt` | `Sitemap:` 域名 | 手动改 |

## 设计来源

首页版式参考 [xxynet/HomePage](https://github.com/xxynet/HomePage)（其 README 说明改自 ZYYO homepage）。

该仓库**没有 LICENSE 文件**，因此本项目**未复用其任何代码、图片或音效**：只参考了「左栏个人卡（标识 / 标签 / 时间线）+ 右栏问候与卡片区块」这一通用版式，HTML / CSS / JS 与视觉素材均为本仓库原创（头像为文字缩写 + CSS 渐变）。相关决策见 [specs/REQ-002-homepage-redesign.md](specs/REQ-002-homepage-redesign.md)。

## 设计取舍

- **无构建**：十年后拉下来就能改，不依赖 Node / Ruby 版本。
- **`posts.json` 单一清单**：首页、RSS、sitemap 不会各说各话。
- **相对路径**：以后改成项目页（`/<repo>/`）也不用改链接。
- **无第三方脚本**：没有统计、没有 CDN，断网可用；主题靠 CSS 变量 + `localStorage`。
