# 变更记录 2026-11-24 #003 修正两条提交信息的中文乱码

- 需求：`../REQ-003-fixed-navbar.md`（仓库可维护性修复，无功能变更）
- 项目：`MyBlog/`
- 范围：提交历史（仅重写信息，代码与线上站点不变）
- 结果：`已验收`

## 问题

`git log` 里出现两条标题为 `feat(ui): ??????? REQ-003` 与 `docs(sdd): ?? REQ-003 ...` 的提交，中文与全角标点全部变成 `?`。

## 原因

这两条提交不是本地 `git commit` 产生的：推送时 `github.com` 的 DNS 被污染，`git push` 无法完成，于是改用 GitHub Git Data API 直接创建 commit。

PowerShell 5.1 的 `Invoke-RestMethod -Body <字符串>` 在 `Content-Type: application/json` 不带 charset 时，按 ASCII 编码发送请求体，非 ASCII 字符被替换为 `?`，GitHub 原样存进了 commit 对象。这也是当时新 commit 的 sha 与本地不一致的原因。

## 处理

1. `git reset --mixed b3d02f9` 回到这两条提交之前（工作区内容不变）。
2. 按内容重新提交两次，消息用 `git commit -F`（UTF-8 无 BOM 文件）：
   - `6f1b696 feat(ui): 顶部固定导航栏 REQ-003`
   - `58ada36 docs(sdd): 收口 REQ-003 导航栏验收与变更记录`
3. `git push --force-with-lease origin main` 覆盖远端（`2129d7f → 58ada36`）。

## 改动文件

无文件内容变更；只重写了两条提交对象，tree 与原来的 `b8877bf` / `2129d7f` 相同。

## 验证

| 操作 | 结果 |
| --- | --- |
| `git log --pretty=format:"%h | %s"` | 四条标题中文正常 |
| `git status -sb` | `## main...origin/main`，无 ahead/behind |
| GitHub API `/commits?per_page=4` | 远端标题与本地一致 |
| 线上站点 | 内容未变（本次不产生页面差异） |

## 可复用结论

- **API 直推必须传字节**：`-Body ([Text.Encoding]::UTF8.GetBytes($json))` + `-ContentType 'application/json; charset=utf-8'`；或确保 JSON 里的非 ASCII 已转义为 `\uXXXX`。
- 提交信息优先用 `git commit -F <utf8-file>`，避免命令行编码差异。
- 重写已推送历史必须用 `--force-with-lease`，并确认没有其他协作者。

## 遗留与限制

无。REQ-003 的功能与线上站点不受影响。
