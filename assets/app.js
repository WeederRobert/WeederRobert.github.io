(() => {
  const THEME_KEY = 'blog-theme';
  const root = document.documentElement;

  const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ESCAPES[ch]);

  const formatDate = (iso) => {
    const date = new Date(`${iso}T00:00:00`);
    if (Number.isNaN(date.getTime())) return iso;
    return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(date);
  };

  function setTheme(theme) {
    root.dataset.theme = theme;
    const button = document.querySelector('[data-theme-toggle]');
    if (!button) return;
    const label = theme === 'dark' ? '切换到浅色模式' : '切换到深色模式';
    button.setAttribute('aria-label', label);
    button.title = label;
    button.textContent = theme === 'dark' ? '☀' : '☾';
  }

  function initTheme() {
    let saved = null;
    try {
      saved = localStorage.getItem(THEME_KEY);
    } catch (error) {
      saved = null;
    }
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(saved || (prefersDark ? 'dark' : 'light'));

    const button = document.querySelector('[data-theme-toggle]');
    if (!button) return;
    button.addEventListener('click', () => {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch (error) {
        // 隐私模式写不进去时，仍然切换当前会话
      }
      setTheme(next);
    });
  }

  function renderPosts(list, posts) {
    const sorted = [...posts].sort((a, b) => String(b.date).localeCompare(String(a.date)));
    list.innerHTML = sorted
      .map((post) => {
        const tags = (post.tags || [])
          .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
          .join('');
        return `
          <li class="post-card">
            <a href="${escapeHtml(post.file)}">
              <h3 class="post-title">${escapeHtml(post.title)}</h3>
              <p class="post-summary">${escapeHtml(post.summary)}</p>
            </a>
            <p class="post-meta"><time datetime="${escapeHtml(post.date)}">${formatDate(post.date)}</time>${tags}</p>
          </li>`;
      })
      .join('');
  }

  function updateStats(posts) {
    const count = document.querySelector('[data-article-count]');
    if (count) count.textContent = String(posts.length);
    const latest = document.querySelector('[data-last-updated]');
    if (latest) {
      const dates = posts.map((post) => post.date).filter(Boolean).sort();
      latest.textContent = dates.length ? formatDate(dates[dates.length - 1]) : '—';
    }
  }

  async function initPostList() {
    const list = document.querySelector('[data-post-list]');
    if (!list) return;
    try {
      const response = await fetch('posts.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.posts) || data.posts.length === 0) {
        throw new Error('posts.json 里没有文章');
      }
      renderPosts(list, data.posts);
      updateStats(data.posts);
    } catch (error) {
      list.innerHTML = `<li class="empty">文章列表加载失败：${escapeHtml(error.message)}<br>本地预览请先运行 <code>python -m http.server 8000</code>，再访问 http://localhost:8000；直接双击 HTML 会被浏览器拦截 fetch。</li>`;
    } finally {
      list.removeAttribute('aria-busy');
    }
  }

  function initLocalTime() {
    const clock = document.querySelector('[data-local-time]');
    const zone = document.querySelector('[data-timezone]');
    if (!clock && !zone) return;

    const timeFmt = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });
    let zoneName = '';
    try {
      zoneName = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    } catch (error) {
      zoneName = '';
    }
    if (zone) zone.textContent = zoneName || '本地时间';

    const tick = () => {
      if (clock) clock.textContent = timeFmt.format(new Date());
    };
    tick();
    window.setInterval(tick, 30000);
  }

  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initPostList();
    initLocalTime();
    document.querySelectorAll('[data-year]').forEach((node) => {
      node.textContent = String(new Date().getFullYear());
    });
  });
})();
