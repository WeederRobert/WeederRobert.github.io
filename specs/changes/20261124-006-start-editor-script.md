# 变更记录 2026-11-24 #006 编辑器启动脚本（bash）

- 需求：[`../REQ-005-start-editor-script.md`](../REQ-005-start-editor-script.md)
- 项目：`MyBlog/`
- 范围：新增 `start-editor.sh`；补 `.gitattributes` 锁 LF；发布排除脚本
- 结果：`部分完成`（静态验证全通过；bash 实跑待在装有 bash 的环境补 AC-1 / AC-2 / AC-4）

## 做了什么

1. 新增 `start-editor.sh`（bash 3.2+ 兼容写法）：
   - 从脚本位置向上找到含 `posts.json` 的仓库根，与当前工作目录无关；
   - 依次找 `python3`、`python`，并断言版本 ≥ 3.11（`datetime.UTC` 需要）；
   - 用 Python `socket.bind` 在 `127.0.0.1:<port>` 上做端口预检，占用时给中文提示并退出 1；
   - 端口优先级 `--port=N` / `--port N` > `MYBLOG_EDITOR_PORT` > `8765`；
   - `exec "$PY" -u editor/server.py "$@"`：`-u` 防止 stdout 缓冲吞掉带 `?key=` 的链接，`exec` 让 `Ctrl+C` 直接终止服务。
2. 新增 `.gitattributes`：`*.sh text eol=lf`。本机 `core.autocrlf=true`，没有这条规则时下次 checkout 会把脚本写成 CRLF，Git Bash / WSL 直接报 `bad interpreter ^M`。
3. workflow 的 `rsync` 增加 `--exclude 'start-editor.sh'`，脚本不随站点发布。
4. `README.md`「本地编辑器」补脚本用法与端口优先级，目录树与发布排除清单同步。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `start-editor.sh` | 新增 bash 启动器 |
| `.gitattributes` | 新增：`*.sh text eol=lf` |
| `.github/workflows/pages.yml` | `rsync` 排除 `start-editor.sh` |
| `README.md` | 脚本用法、目录树、发布排除清单 |
| `specs/requirements.md` / `specs/REQ-005-start-editor-script.md` | 登记与规范 |

## 验证

本机没有 bash（`Get-Command bash` 无结果；`C:\Program Files\Git\usr\bin\bash.exe` 等路径均不存在；`wsl -l -q` 退出码 1 表示无发行版），
因此 `bash -n` 与整脚本实跑都做不了，下面是实际能测的部分：

| 命令 / 操作 | 实测结果 |
| --- | --- |
| 字节检查 `start-editor.sh` | `bytes=2591 bom=False cr=0 lf=82`（纯 LF、无 BOM） |
| 字节检查 `.gitattributes` | `bytes=165 bom=False cr=0 lf=3` |
| 抽出脚本内嵌的端口探针，`python probe.py 8765` | `exit=1`（此时编辑器正在 8765 监听，判定为占用） |
| `python probe.py 8766` | `exit=0`（空闲端口可 bind） |
| 版本判断片段 `python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'` | `exit=0`（本机 3.13.15） |
| `Select-String pages.yml "exclude 'start-editor.sh'"` | 命中第 31 行 |
| 人工审阅 | `die()` 定义在仓库根查找之前；`for` 循环用 `${#ARGS[@]}`，`exec` 用 `"${ARGS[@]+"${ARGS[@]}"}"` 兜住空数组（bash 3.2 + `set -u` 的已知坑） |

未验证（需要在 Git Bash / WSL / Linux / macOS 上执行一次）：

| 待补 | 命令 |
| --- | --- |
| AC-1 | `bash start-editor.sh --help` |
| AC-2 | `bash start-editor.sh` → 看链接 → `Ctrl+C` → `Get-NetTCPConnection -LocalPort 8765` 为空 |
| AC-4 | `bash start-editor.sh --port 8800 --no-browser` |

## 新增 / 改动的可复用件

- `start-editor.sh`：`./start-editor.sh [--port N|--port=N] [--no-browser] [server.py 其他参数]`；
  端口优先级 `--port` > `MYBLOG_EDITOR_PORT` > `8765`；退出码 1 = 前置检查失败或端口被占。
- 内嵌的 `port_free()`：可在其他脚本里复制这段「Python socket 预检」，避免依赖 `ss` / `lsof` / `netstat`。

## 决策与理由

- **脚本不碰启动逻辑**：令牌、访问控制、浏览器打开都在 `editor/server.py` 里；脚本只做前置检查，避免两处口径漂移（此前已因模板 / 标签分隔符各踩过一次）。
- **端口预检用 Python**：Git Bash、WSL、macOS 上 `ss`/`lsof`/`netstat` 不齐，Python 是硬依赖。
- **根目录放脚本 + workflow 排除**：根目录最好记；排除一行即可，文档已写明「不发布」。
- **`.gitattributes` 而不是本地转一次 LF**：`core.autocrlf=true` 会在下次 checkout 时把 CRLF 写回工作区，仓库级规则才可持续。

## 遗留与限制

- 本机无 bash，AC-1 / AC-2 / AC-4 未实跑，REQ-005 保持 `in-progress`；补测通过后把状态改成 `done`。
- 本机当下可用等价入口：`python editor/server.py`（已在 REQ-004 中验收）；PowerShell 下也可用 `Get-NetTCPConnection ... | ForEach-Object { Stop-Process -Id $_ }` 停服务。
- 不做后台常驻、自动提交、依赖安装。

## 后续

在装了 Git Bash（或任意 Linux/macOS）的机器上跑那三条命令，把输出补进本记录，再把 REQ-005 状态与本表结果改成 `done` / `已验收`。
