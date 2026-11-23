# REQ-003 顶部固定导航栏

- 状态：`done`（AC-1~AC-8 本地与线上均验证；见 `changes/20261124-002-fixed-navbar.md`）
- 项目：`MyBlog/`
- 提出：2026-11-24
- 关联：[REQ-002](REQ-002-homepage-redesign.md)（版式基线）

## 1. 需求

所有页面顶部增加一条**固定（滚动时始终可见）**的导航栏，包含站点名、页面入口与主题切换；首页目前没有页头，文章页只有一个随页面滚走的简易页头，需要统一。

不要：二级菜单、移动端抽屉、滚动阴影动画、任何第三方组件。

## 2. 现状与事实

- `index.html` 无页头；`about.html` / `404.html` / `posts/hello-world.html` 使用 `.site-header`（`max-width: 760px`，随页面滚出视野）。
- 主题按钮在首页位于 `.actions` 内，在文章页位于 `.site-header` 内 —— 位置不一致。
- 侧栏 `.side` 使用 `position: sticky; top: 2rem`，新增顶部栏后需让位，否则会贴在栏下沿被遮挡。

## 3. 验收标准

| # | 可观察结果 | 验证方式 | 结果 |
| --- | --- | --- | --- |
| AC-1 | 滚动 600px 后导航栏仍在视口顶部（`rect.top === 0`） | 浏览器 | ✅ 首页/文章页均 0 |
| AC-2 | 导航包含 文章 / 关于 / RSS / GitHub 与主题按钮；当前页高亮 | 浏览器 + DOM | ✅ 各页仅一项 `aria-current` |
| AC-3 | 四页导航结构一致，子目录页面链接前缀正确 | 静态检查 | ✅ 文章页为 `../` |
| AC-4 | 首屏标题不被导航遮挡 | 浏览器 | ✅ `h1.top≈100.8 > 56.8` |
| AC-5 | 375px 无横向滚动 | 浏览器 | ✅ `scrollWidth=clientWidth=360` |
| AC-6 | 主题按钮仍可切换并持久化 | 浏览器 | ✅ 单按钮，`localStorage=dark` |
| AC-7 | 无第三方请求、0 死链、无 BOM | 脚本 | ✅ `errors: none` |
| AC-8 | 半透明 + 模糊在深浅色下可读 | 截图 | ✅ 两种主题均正常 |

## 4. 影响面

| 类型 | 位置 | 说明 |
| --- | --- | --- |
| 代码 | `index.html` / `about.html` / `404.html` / `posts/hello-world.html` | 插入统一 `.topbar`，移除旧 `.site-header` |
| 代码 | `assets/style.css` | 新增 `.topbar` / `.nav`，删除 `.site-header` / `.site-nav`，调整 `.side` 粘连偏移 |
| 代码 | `assets/app.js` | 不改（`[data-theme-toggle]` 选择器与位置无关） |
| 文档 | `README.md` | 目录说明补一句导航栏 |
| 文档 | `specs/` | 本 spec 与变更记录 |

## 5. 复用基线

- 复用：`.theme-toggle` 组件、`--border` / `--chip` / `--muted` / `--fg` 变量、`blog-theme` 存储键、`[data-theme-toggle]` 契约。
- 新增可复用件：`.topbar` / `.topbar-inner` / `.nav` 结构与样式，四个页面共用同一份标记。

## 6. 决策与取舍

| 决策 | 备选方案 | 为什么选这个 |
| --- | --- | --- |
| `position: sticky` | `position: fixed` | sticky 仍在文档流内，无需给内容补 `padding-top`，也不会在移动端键盘弹出时错位 |
| 导航放在 `<body>` 顶层、内层限宽 | 直接放进 `.shell` | sticky 需要滚动容器是视口；放 shell 内只能粘在 shell 顶部 |
| 半透明 + `backdrop-filter` | 纯色不透明 | 滚动时保留内容层次，符合现有卡片质感；旧浏览器降级为不透明纯色 |
| 首页移除 `.actions` 里的重复入口 | 两处都保留 | 导航已提供入口，重复会让首屏噪音变大 |
| 导航项用纯文本 + `aria-current` | 图标按钮 | 文字更明确，且不引入图标库 |

## 7. 不做的事

- 移动端汉堡菜单 / 抽屉（当前只有 4 个入口，直接横排即可）。
- 滚动时隐藏导航、进度条、锚点目录。

## 8. 口径与边界

- 导航高度通过 `--topbar-h: 56px` 统一控制；`.side` 的 `top` 依赖它，改高度只需改一处。
- `backdrop-filter` 不可用时退化为 `var(--bg)` 级别的半透明底色，不影响可读性。

## 9. 变更记录

| 日期 | 记录 | 结果 |
| --- | --- | --- |
| 2026-11-24 | [20261124-002](changes/20261124-002-fixed-navbar.md) | 已验收（本地 + 线上；推送经 API，本地待重置） |
