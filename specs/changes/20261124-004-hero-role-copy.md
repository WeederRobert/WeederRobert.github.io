# 变更记录 2026-11-24 #004 首页 hero 身份文案调整

- 需求：无（纯文案改动，按 [.github/instructions/sdd.instructions.md](../../../.github/instructions/sdd.instructions.md) 的「例外」处理，不立 spec）
- 项目：`MyBlog/`
- 范围：`index.html` hero 区身份行 1 行文案
- 结果：`已验收`

## 为什么没有 REQ

改动只是换掉首页问候语下方身份行的措辞：没有增删元素、没有改结构、没有动 CSS 与 JS，也没有改变任何可观察行为（页面结构、`posts.json` 清单、`feed.xml` / `sitemap.xml`、部署流程都不受影响）。按 SDD 例外条款，这类无行为变化的纯文案改动只写变更记录、不占 REQ 编号。若以后要把身份信息收进 `posts.json` 统一驱动（会改变数据流），再立 REQ。

## 做了什么

| 位置 | 改前 | 改后 |
| --- | --- | --- |
| hero 身份行（第 71 行） | `🧑‍💻 <strong>全栈练习生</strong> · 工程实践记录者` | `<strong>软件开发工程师</strong> · 软件架构师研习中` |

- 保留 `<p class="role">` 与内部 `<strong>`：`assets/style.css` 的 `.role` / `.role strong` 依赖这两个选择器，去掉会丢字号与强调色。
- 行首的 🧑‍💻 emoji 一并去掉；`.role` 没有固定宽度或强制单行约束，文案变短不影响排版。

## 改动文件

| 文件 | 改动 |
| --- | --- |
| `index.html` | 第 71 行 hero 身份文案 |
| `specs/requirements.md` | 变更记录索引新增本行 |
| `README.md` | 「需求与变更记录」链接从 `specs/REQ-001-github-io-blog.md` 改为 `specs/requirements.md`（登记表才是需求入口） |
| `.github/specs/README.md` | 「项目索引」补 `MyBlog/` 一行（该项目早已有 `specs/`，但索引里漏登记） |

## 验证

| 命令 / 操作 | 实测结果 |
| --- | --- |
| `git diff --stat` | `index.html \| 2 +-`，1 file changed, 1 insertion(+), 1 deletion(-) |
| `git grep -n -E '全栈\|练习生'` | 无匹配，旧文案无残留 |
| `python -m http.server 8123` + `curl -s -o tmp -w "HTTP %{http_code}" http://127.0.0.1:8123/index.html` | `HTTP 200`，6813 bytes |
| 上一步的临时文件按 UTF-8 读取后断言 | `软件开发工程师</strong> · 软件架构师研习中` → 存在；`全栈练习生` → 不存在；`<p class="role">` → 存在 |
| 三个 Markdown 首字节检查 | `0x23`（`#`），均无 BOM |

## 新增 / 改动的可复用件

无。

## 决策与理由

- 不把这段文案抽成 `posts.json` 字段：当前只有一处使用，抽出去只是多一个配置项；项目 `README.md` 的「个性化项」表格已笼统覆盖 `index.html` 的 `.hero` 问候语与简介，按现有约定手改即可。
- 不新增 `specs/REQ-004`：纯文案不占编号，避免以后查到一条没有验收标准的空 spec。
- 顺手把项目 `README.md` 的需求入口从单条 spec 改指登记表：链接指向 `requirements.md` 才能看到全部 REQ 与状态，这是本次留痕的直接配套。

## 遗留与限制

- 线上生效需要 `push` 到 `main`（本次只提交到本地，未推送）。
- `about.html` 正文不涉及身份头衔，无需同步；`posts.json` 的 `site.description` 与本次文案无关，也未改动。

## 后续

无。
