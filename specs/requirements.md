# MyBlog 需求汇总

- 项目根目录：[../](../)
- 长期文档：[README.md](../README.md)
- SDD 规则：[.github/specs/README.md](../../.github/specs/README.md)
- 模板：[spec](../../.github/specs/_template/spec.md) · [change](../../.github/specs/_template/change.md)

> 这是本项目的**需求单一入口**：新需求先在这里登记，再展开成同目录的 `REQ-<NNN>-<slug>.md`；每次实现后更新状态并在 `changes/` 留记录。

## 状态总览

| 状态 | 数量 |
| --- | --- |
| draft | 0 |
| approved | 1 |
| in-progress | 1 |
| done | 0 |

## 需求登记表

| ID | 标题 | 状态 | 提出 | 验收 | Spec | 变更记录 |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-001 | 搭建 GitHub Pages 个人博客 | in-progress | 2026-11-23 | AC-1~AC-8 通过；AC-9 待开启 Pages | [REQ-001-github-io-blog.md](REQ-001-github-io-blog.md) | [001](changes/20261123-001-github-io-blog.md) · [002](changes/20261123-002-site-identity.md) |
| REQ-002 | 首页改版：仿 xxynet/HomePage 版式 | approved | 2026-11-24 | AC-1~AC-8 | [REQ-002-homepage-redesign.md](REQ-002-homepage-redesign.md) | 待实现 |

## 按主题汇总

### 站点与发布

- `REQ-001`：无构建静态站 + `posts.json` 单一清单 + GitHub Actions 发布，先跑通「写一篇 → 首页可见 → 推送即上线」。

## 变更记录索引

| 日期 | 记录 | 需求 | 结果 |
| --- | --- | --- | --- |
| 2026-11-23 | [20261123-001](changes/20261123-001-github-io-blog.md) | REQ-001 | 部分完成（AC-1~AC-8） |
| 2026-11-23 | [20261123-002](changes/20261123-002-site-identity.md) | REQ-001 | 已验收 |
