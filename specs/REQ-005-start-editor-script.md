# REQ-005 编辑器启动脚本（bash）

- 状态：`in-progress`
- 项目：`MyBlog/`
- 提出：2026-11-24
- 关联：[REQ-004-local-post-editor.md](REQ-004-local-post-editor.md)（编辑器本体）

## 1. 需求

要一个只干一件事的 bash 启动器：在仓库里执行 `./start-editor.sh` 就能起编辑器，不必记目录、端口和环境差异；命令行参数原样交给 `editor/server.py`。

不要：装依赖、后台常驻 / 守护进程、自动 git 提交、跨平台桌面快捷方式、在脚本里重复实现启动逻辑。

## 2. 现状与事实

- 现有入口：`editor/server.py` 的 `argparse` 支持 `--port`（默认 8765）与 `--no-browser`；启动时打印带 `?key=` 的链接（[editor/server.py](../editor/server.py) 的 `main`）。
- 端口占用：`ThreadingHTTPServer` 绑定失败抛 `OSError`，`main` 已捕获并提示换端口、退出码 1。
- 依赖：`scripts/blog_core.py` 使用 `datetime.UTC` → 需要 Python 3.11+；本机 `python --version` 为 `3.13.15`。
- 本机没有 bash：`Get-Command bash` 无结果，`C:\Program Files\Git\usr\bin\bash.exe` 等路径均不存在，`wsl -l -q` 退出码 1（无发行版）→ 本次无法在本机实跑 `bash start-editor.sh`，只能在静态层面验证。
- 行尾陷阱：`git config core.autocrlf` = `true`，工作区 `.sh` 默认会被写成 CRLF，Git Bash / WSL 执行时报 `bad interpreter ^M` → 需要 `.gitattributes` 强制 LF。

## 3. 验收标准

| # | 可观察结果 | 验证方式 |
| --- | --- | --- |
| AC-1 | `bash start-editor.sh --help` 输出 `editor/server.py` 的帮助（`usage: server.py ...`），退出码 0 | 装有 bash 的环境执行 |
| AC-2 | 默认运行时终端立刻出现带 `?key=` 的链接（不被 stdout 缓冲吞掉），`Ctrl+C` 后端口释放 | 同上 + `Get-NetTCPConnection` |
| AC-3 | 端口被占用时打印中文提示（含换端口建议），退出码非 0，且不会起第二个实例 | `start-editor.sh` + 脚本内嵌端口探针实测 |
| AC-4 | `--port 8800 --no-browser` 原样生效 | 同上 |
| AC-5 | 无 `python3` / `python` 或版本 < 3.11 时给出明确错误 | 代码审阅 + 版本判断片段实测 |
| AC-6 | 从任意工作目录执行都能定位仓库根（向上找 `posts.json`） | 代码审阅（脚本内 `while` 循环） |
| AC-7 | 文件为 LF、无 BOM；工作区即使 `core.autocrlf=true` 也保持 LF | 字节检查 + `.gitattributes` 的 `*.sh text eol=lf` |
| AC-8 | 不发布到站点：`rsync` 排除 `start-editor.sh` | `Select-String pages.yml` |

## 4. 影响面

| 类型 | 位置 | 说明 |
| --- | --- | --- |
| 代码 | `start-editor.sh` | 新增 bash 启动器 |
| 配置 | `.gitattributes` | 新增：`*.sh text eol=lf` |
| 配置 | `.github/workflows/pages.yml` | `rsync` 增加 `--exclude 'start-editor.sh'` |
| 文档 | `README.md` | 「本地编辑器」补脚本用法与目录树 |
| 文档 | `specs/requirements.md`、`specs/changes/` | 登记与留痕 |

## 5. 复用基线

- 复用 `editor/server.py` 的 CLI 与全部运行时行为（令牌、浏览器、访问控制），脚本只做「找解释器 → 端口预检 → `exec`」，不复制任何启动逻辑。
- 复用 Python 做端口探测：Git Bash / WSL / macOS 不保证有 `ss`、`lsof`、`netstat`，但一定有 Python。

本次新增的可复用件：

- 落点：`start-editor.sh`
- 契约：`./start-editor.sh [--port N | --port=N] [--no-browser] [其他 server.py 参数]`；退出码 0 = 正常退出，1 = 前置检查失败或端口被占；端口优先级 `--port` > `MYBLOG_EDITOR_PORT` > `8765`。

## 6. 决策与取舍

| 决策 | 备选方案 | 为什么选这个 |
| --- | --- | --- |
| 脚本只做前置检查 + `exec python -u` | 在脚本里重写服务启动 | 服务端已负责端口、令牌、浏览器；两处实现必然漂移 |
| 端口预检用 Python `socket.bind` | `ss` / `netstat` / `lsof` | 这些工具在三种目标环境上不齐；Python 是硬依赖 |
| `exec` + `-u` | `python &` 放后台 | 前台进程让 `Ctrl+C` 直接停服务；`-u` 保证链接立即打印（此前实测有缓冲导致看不到 key） |
| 脚本自己向上找 `posts.json` | 硬编码 `cd /d/Workspace/...` | 换机器 / 换路径 / 脚本挪到 `editor/` 下都不失效 |
| root 级 `start-editor.sh` + workflow 排除 | 放进 `editor/` 里自动被排除 | 根目录更容易记；排除只是一行 `rsync`，文档里已写清「不发布」 |
| 加 `.gitattributes` 锁 LF | 只在本地转一次 LF | `core.autocrlf=true` 会让下次 checkout 又变 CRLF；仓库级规则才是可持续的 |

## 7. 不做的事

- 后台常驻 / 守护进程 / 开机自启（令牌常驻反而扩大暴露面）。
- 自动 `git commit` / `push`、自动建文章。
- 依赖安装（`pip` / `uv` / `brew`），以及为 Windows 生成 `.cmd` / `.ps1` 包装（PowerShell 直接调 `python editor/server.py` 即可）。

## 8. 口径与边界

- 端口优先级：`--port=N` / `--port N` > `MYBLOG_EDITOR_PORT` > `8765`；非数字端口不预检，交给 `server.py` 报错。
- 端口探测方式：在 `127.0.0.1` 上 `bind` 再 `close`；占用即认为「已有实例或别的程序在监听」。
- 已知限制：本次开发机没有 bash，AC-1 / AC-2 / AC-4 需要在 Git Bash、WSL、Linux 或 macOS 上执行验证；本机给出等价入口 `python editor/server.py`。

## 9. 变更记录

| 日期 | 记录 | 结果 |
| --- | --- | --- |
| 2026-11-24 | `changes/20261124-006-start-editor-script.md` | 部分完成（静态验证通过；bash 实跑待在装有 bash 的环境补） |
