(() => {
  const $ = (selector) => document.querySelector(selector);
  const fields = {
    title: $('[data-field="title"]'),
    slug: $('[data-field="slug"]'),
    date: $('[data-field="date"]'),
    tags: $('[data-field="tags"]'),
    summary: $('[data-field="summary"]'),
    body: $('[data-field="body"]'),
  };
  const list = $('[data-list]');
  const chips = $('[data-chips]');
  const status = $('[data-status]');
  const siteLabel = $('[data-site]');
  const pageLink = $('[data-page-link]');
  const split = $('[data-split]');
  const preview = $('[data-preview]');
  const toastBox = $('[data-toast]');

  const state = {
    site: null,
    posts: [],
    tags: [],
    current: null,
    dirty: false,
    keyword: '',
    tag: '',
    previewOn: true,
  };
  let previewTimer = 0;
  let toastTimer = 0;

  const SNIPPETS = {
    p: { before: '<p>', after: '</p>', sample: '段落文字' },
    h2: { before: '<h2>', after: '</h2>', sample: '小标题' },
    ul: { before: '<ul>\n  <li>', after: '</li>\n</ul>', sample: '第一项' },
    pre: { before: '<pre><code>', after: '</code></pre>', sample: 'npm run build' },
    quote: { before: '<blockquote>', after: '</blockquote>', sample: '引用一句话' },
    link: { before: '<a href="https://', after: '">链接文字</a>', sample: 'example.com' },
    img: { before: '<img src="../assets/', after: '" alt="">', sample: 'photo.png' },
  };

  async function api(path, { method = 'GET', body } = {}) {
    const headers = { 'X-Editor': '1' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch(path, { method, headers, body });
    const type = response.headers.get('Content-Type') || '';
    const data = type.includes('application/json') ? await response.json() : await response.text();
    if (response.status === 403) {
      throw new Error('访问令牌失效或缺失，请回终端用带 ?key= 的新链接打开（重启服务后旧链接会失效）');
    }
    if (!response.ok) throw new Error((data && data.error) || `HTTP ${response.status}`);
    return data;
  }

  function toast(message, isError = false) {
    toastBox.textContent = message;
    toastBox.classList.toggle('error', isError);
    toastBox.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toastBox.hidden = true;
    }, isError ? 6000 : 3200);
  }

  function markDirty() {
    state.dirty = true;
    status.textContent = '未保存';
    status.classList.add('dirty');
  }

  function markClean(label = '已保存') {
    state.dirty = false;
    status.textContent = label;
    status.classList.remove('dirty');
  }

  function tagText(tags) {
    return (tags || []).join(' · ');
  }

  function renderChips() {
    chips.textContent = '';
    const make = (label, value) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chip' + (state.tag === value ? ' active' : '');
      button.textContent = label;
      button.addEventListener('click', () => {
        state.tag = state.tag === value ? '' : value;
        renderChips();
        renderList();
      });
      chips.append(button);
    };
    make('全部', '');
    state.tags.forEach((tag) => make(tag, tag));
  }

  function renderList() {
    const keyword = state.keyword.trim().toLowerCase();
    const visible = state.posts.filter((post) => {
      const tagOk = !state.tag || (post.tags || []).includes(state.tag);
      const haystack = [post.title, post.summary, post.slug, (post.tags || []).join(' ')]
        .join(' ')
        .toLowerCase();
      return tagOk && (!keyword || haystack.includes(keyword));
    });

    list.textContent = '';
    if (visible.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'empty';
      empty.textContent = state.posts.length ? '没有匹配的文章' : '还没有文章';
      list.append(empty);
      return;
    }

    visible.forEach((post) => {
      const item = document.createElement('li');
      item.className = 'item' + (state.current === post.slug ? ' active' : '');

      const title = document.createElement('span');
      title.className = 'item-title';
      title.textContent = post.title;

      const meta = document.createElement('span');
      meta.className = 'item-meta';
      const time = document.createElement('time');
      time.textContent = post.date;
      const tags = document.createElement('span');
      tags.className = 'item-tags';
      tags.textContent = tagText(post.tags);
      meta.append(time, tags);

      item.append(title, meta);
      item.addEventListener('click', () => openPost(post.slug));
      list.append(item);
    });
  }

  function fillForm(data, { creating }) {
    fields.title.value = data.title || '';
    fields.slug.value = data.slug || '';
    fields.date.value = data.date || '';
    fields.tags.value = (data.tags || []).join(', ');
    fields.summary.value = data.summary || '';
    fields.body.value = data.body || '';
    fields.slug.readOnly = !creating;
    state.current = creating ? null : data.slug;
    pageLink.hidden = creating || !data.slug;
    pageLink.href = creating || !data.slug ? '#' : `/posts/${data.slug}.html`;
    renderList();
    schedulePreview();
  }

  function collect() {
    return {
      slug: fields.slug.value.trim(),
      title: fields.title.value,
      date: fields.date.value,
      tags: fields.tags.value
        .split(/[,，、]/)
        .map((tag) => tag.trim())
        .filter(Boolean),
      summary: fields.summary.value,
      body: fields.body.value,
    };
  }

  async function loadPosts() {
    const data = await api('/api/posts');
    state.site = data.site;
    state.posts = data.posts;
    state.tags = data.tags;
    siteLabel.textContent = `${data.site.title} · ${data.posts.length} 篇`;
    renderChips();
    renderList();
  }

  async function openPost(slug) {
    if (state.current === slug) return;
    if (state.dirty && !window.confirm('当前修改还没保存，切换会丢掉。继续？')) return;
    try {
      const data = await api(`/api/posts/${encodeURIComponent(slug)}`);
      fillForm(data, { creating: false });
      markClean('已载入');
      if (data.drift.length) {
        toast(`页面与 posts.json 不一致：${data.drift.join('、')}；保存后以表单为准`, true);
      }
    } catch (error) {
      toast(`打开失败：${error.message}`, true);
    }
  }

  function newPost() {
    if (state.dirty && !window.confirm('当前修改还没保存，新建会丢掉。继续？')) return;
    const today = new Date();
    const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(
      today.getDate(),
    ).padStart(2, '0')}`;
    fillForm({ title: '', slug: '', date: iso, tags: [], summary: '', body: '<p></p>' }, { creating: true });
    markClean('新文章');
    fields.title.focus();
    toast('填标题与 slug 后保存；slug 建好后不可改');
  }

  async function save() {
    const payload = collect();
    if (!payload.title.trim()) {
      toast('标题不能为空', true);
      fields.title.focus();
      return;
    }
    if (!payload.slug) {
      toast('slug 不能为空（小写字母、数字、连字符）', true);
      fields.slug.focus();
      return;
    }
    try {
      const result = await api(`/api/posts/${encodeURIComponent(payload.slug)}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      markClean('已保存');
      fields.slug.readOnly = true;
      state.current = result.slug;
      pageLink.hidden = false;
      pageLink.href = result.url;
      await loadPosts();
      renderList();
      toast(`${result.created ? '已新建' : '已保存'} ${result.file}，重建 ${result.rebuilt.join(' / ')}`);
    } catch (error) {
      toast(`保存失败：${error.message}`, true);
    }
  }

  async function updatePreview() {
    if (!state.previewOn) return;
    try {
      const data = await api('/api/render', { method: 'POST', body: JSON.stringify(collect()) });
      preview.srcdoc = data.html;
    } catch (error) {
      preview.srcdoc = `<!doctype html><meta charset="utf-8"><p style="font:14px system-ui;color:#c0392b;padding:16px">预览失败：${error.message}</p>`;
    }
  }

  function schedulePreview() {
    window.clearTimeout(previewTimer);
    previewTimer = window.setTimeout(updatePreview, 220);
  }

  function insertSnippet(kind) {
    const snippet = SNIPPETS[kind];
    if (!snippet) return;
    const area = fields.body;
    const { selectionStart: start, selectionEnd: end, value } = area;
    const selected = value.slice(start, end) || snippet.sample;
    const text = snippet.before + selected + snippet.after;
    area.value = value.slice(0, start) + text + value.slice(end);
    const caret = start + snippet.before.length;
    area.focus();
    area.setSelectionRange(caret, caret + selected.length);
    area.dispatchEvent(new Event('input', { bubbles: true }));
  }

  document.querySelectorAll('[data-insert]').forEach((button) => {
    button.addEventListener('click', () => insertSnippet(button.dataset.insert));
  });

  Object.values(fields).forEach((input) => {
    input.addEventListener('input', () => {
      markDirty();
      schedulePreview();
    });
  });

  $('[data-search]').addEventListener('input', (event) => {
    state.keyword = event.target.value;
    renderList();
  });

  $('[data-new]').addEventListener('click', newPost);
  $('[data-save]').addEventListener('click', save);

  $('[data-toggle-preview]').addEventListener('click', (event) => {
    state.previewOn = !state.previewOn;
    event.currentTarget.setAttribute('aria-pressed', String(state.previewOn));
    split.classList.toggle('preview-off', !state.previewOn);
    if (state.previewOn) schedulePreview();
  });

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      save();
    }
  });

  window.addEventListener('beforeunload', (event) => {
    if (!state.dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });

  // 令牌只用来换 Cookie，换完就从地址栏与历史里抹掉，避免截图 / 分享链接泄露。
  if (window.location.search.includes('key=')) {
    window.history.replaceState(null, '', window.location.pathname);
  }

  loadPosts()
    .then(() => {
      if (state.posts.length) return openPost(state.posts[0].slug);
      newPost();
      return null;
    })
    .catch((error) => toast(`加载失败：${error.message}`, true));
})();
