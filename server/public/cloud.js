/* D20 cloud UI: accounts, cloud save/open, share links.
   Injected by the server into V2/index.html. Depends on window.D20App
   ({collect, load}) exposed by the page. */
(function () {
  'use strict';
  const App = window.D20App;
  if (!App) { console.warn('[d20-cloud] window.D20App missing; cloud UI disabled'); return; }

  let user = null;
  let currentId = null;      // cloud project the session is bound to
  let currentName = '';

  // ---------- api ----------
  async function api(method, url, body) {
    const res = await fetch(url, {
      method,
      credentials: 'same-origin',
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    let json = {};
    try { json = await res.json(); } catch {}
    if (!res.ok) throw new Error(json.error || `Request failed (${res.status})`);
    return json;
  }

  // ---------- styles ----------
  const css = document.createElement('style');
  css.textContent = `
  .d20c-sep{display:inline-block;width:1px;height:22px;background:currentColor;opacity:.25;margin:0 6px;vertical-align:middle}
  .d20c-user{font-size:12px;opacity:.8;margin-left:4px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle;display:inline-block}
  .d20c-overlay{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:100000}
  .d20c-panel{background:#1d1f24;color:#e8e8ea;border:1px solid #3a3d45;border-radius:10px;padding:18px 20px;width:min(460px,calc(100vw - 32px));max-height:80vh;overflow:auto;font:14px/1.4 system-ui,sans-serif;box-shadow:0 10px 40px rgba(0,0,0,.5)}
  .d20c-panel h3{margin:0 0 12px;font-size:16px}
  .d20c-panel input{width:100%;box-sizing:border-box;margin:4px 0 10px;padding:8px;border-radius:6px;border:1px solid #444;background:#111317;color:inherit;font:inherit}
  .d20c-row{display:flex;gap:8px;justify-content:flex-end;margin-top:6px;flex-wrap:wrap}
  .d20c-btn{padding:6px 12px;border-radius:6px;border:1px solid #555;background:#2b2e35;color:inherit;cursor:pointer;font:inherit}
  .d20c-btn.primary{background:#3b6ef5;border-color:#3b6ef5;color:#fff}
  .d20c-btn.danger{border-color:#a33;color:#f88}
  .d20c-err{color:#ff8a8a;min-height:18px;font-size:13px}
  .d20c-link{background:none;border:none;color:#8ab4ff;cursor:pointer;padding:0;font:inherit;text-decoration:underline}
  .d20c-list{list-style:none;margin:0;padding:0}
  .d20c-list li{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #30333a}
  .d20c-list .nm{flex:1;min-width:0}
  .d20c-list .nm b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .d20c-list .nm small{opacity:.6}
  .d20c-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#222;color:#fff;border:1px solid #444;padding:8px 14px;border-radius:8px;z-index:100001;font:13px system-ui,sans-serif;max-width:calc(100vw - 32px)}
  .d20c-banner{background:#2a3350;color:#dfe6ff;padding:6px 12px;font:13px system-ui,sans-serif;text-align:center}
  `;
  document.head.appendChild(css);

  // ---------- small dom helpers ----------
  function el(tag, attrs = {}, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') n.className = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v);
    }
    for (const k of kids) n.append(k);
    return n;
  }
  let toastTimer;
  function toast(msg) {
    document.querySelectorAll('.d20c-toast').forEach(t => t.remove());
    const t = el('div', { class: 'd20c-toast' }, msg);
    document.body.appendChild(t);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.remove(), 3500);
  }
  function modal(title, body) {
    const panel = el('div', { class: 'd20c-panel', role: 'dialog', 'aria-label': title }, el('h3', {}, title), body);
    const ov = el('div', { class: 'd20c-overlay', onclick: e => { if (e.target === ov) close(); } }, panel);
    // Keep typing in the dialog from reaching the sequencer's keyboard shortcuts.
    for (const t of ['keydown', 'keyup', 'keypress']) {
      panel.addEventListener(t, e => { if (e.key !== 'Escape') e.stopPropagation(); });
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    function close() { ov.remove(); document.removeEventListener('keydown', onKey); }
    document.addEventListener('keydown', onKey);
    document.body.appendChild(ov);
    return close;
  }
  const fmtDate = s => new Date(s).toLocaleString();
  const fmtSize = b => b > 1e6 ? (b / 1e6).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1e3)) + ' KB';

  // ---------- toolbar ----------
  const host = document.querySelector('#engineBar .file-ctrl') || document.querySelector('#engineBar') || document.body;
  const btnSave  = el('button', { class: 'file-btn', type: 'button', title: 'Save this project to your cloud account (Shift+click: save as new)' }, 'Save to Cloud');
  const btnOpen  = el('button', { class: 'file-btn', type: 'button', title: 'Open one of your cloud projects' }, 'Open Cloud');
  const btnShare = el('button', { class: 'file-btn', type: 'button', title: 'Get a public link to this cloud project' }, 'Share');
  const btnAcct  = el('button', { class: 'file-btn', type: 'button' }, 'Sign in');
  const who      = el('span', { class: 'd20c-user' });
  host.append(el('span', { class: 'd20c-sep' }), btnSave, btnOpen, btnShare, btnAcct, who);

  function render() {
    btnAcct.textContent = user ? 'Sign out' : 'Sign in';
    who.textContent = user ? user.email : '';
    btnShare.disabled = !user || !currentId;
  }

  // Loading a local file or starting a new project detaches from the cloud copy.
  ['newProjectBtn', 'loadProjectBtn'].forEach(id => {
    const b = document.getElementById(id);
    if (b) b.addEventListener('click', () => { currentId = null; currentName = ''; render(); });
  });

  // ---------- auth ----------
  function authDialog(then) {
    let mode = 'login';
    const email = el('input', { type: 'email', autocomplete: 'email', placeholder: 'you@example.com' });
    const pw = el('input', { type: 'password', autocomplete: 'current-password', placeholder: 'Password (8+ characters)' });
    const err = el('div', { class: 'd20c-err' });
    const submit = el('button', { class: 'd20c-btn primary', type: 'submit' }, 'Sign in');
    const toggle = el('button', { class: 'd20c-link', type: 'button' }, 'Create an account');
    const form = el('form', {}, el('label', {}, 'Email'), email, el('label', {}, 'Password'), pw, err,
      el('div', { class: 'd20c-row' }, toggle, submit));
    const close = modal('Sign in', form);
    const heading = form.parentElement.querySelector('h3');
    toggle.addEventListener('click', () => {
      mode = mode === 'login' ? 'register' : 'login';
      submit.textContent = heading.textContent = mode === 'login' ? 'Sign in' : 'Create account';
      toggle.textContent = mode === 'login' ? 'Create an account' : 'I have an account';
      pw.setAttribute('autocomplete', mode === 'login' ? 'current-password' : 'new-password');
      err.textContent = '';
      email.focus();
    });
    form.addEventListener('submit', async e => {
      e.preventDefault();
      err.textContent = '';
      submit.disabled = true;
      try {
        const r = await api('POST', `/api/auth/${mode}`, { email: email.value, password: pw.value });
        user = r.user;
        render();
        close();
        toast(`Signed in as ${user.email}`);
        if (then) then();
      } catch (x) { err.textContent = x.message; }
      finally { submit.disabled = false; }
    });
    setTimeout(() => email.focus(), 0);
  }

  btnAcct.addEventListener('click', async () => {
    if (!user) return authDialog();
    await api('POST', '/api/auth/logout').catch(() => {});
    user = null; currentId = null; currentName = '';
    render();
    toast('Signed out');
  });

  // ---------- save ----------
  async function save(asNew) {
    if (!user) return authDialog(() => save(asNew));
    const data = App.collect();
    const name = (data && data.name) || currentName || 'Untitled';
    try {
      if (currentId && !asNew) {
        await api('PUT', `/api/projects/${currentId}`, { name, data });
      } else {
        const r = await api('POST', '/api/projects', { name, data });
        currentId = r.id;
      }
      currentName = name;
      render();
      toast(`Saved "${name}" to cloud`);
    } catch (x) { toast(x.message); }
  }
  btnSave.addEventListener('click', e => save(e.shiftKey));

  // ---------- open ----------
  async function openDialog() {
    if (!user) return authDialog(openDialog);
    let list;
    try { list = (await api('GET', '/api/projects')).projects; }
    catch (x) { return toast(x.message); }
    const ul = el('ul', { class: 'd20c-list' });
    const close = modal('Your cloud projects', el('div', {},
      list.length ? ul : el('p', {}, 'No cloud projects yet. Use Save to Cloud first.'),
      el('div', { class: 'd20c-row' }, el('button', { class: 'd20c-btn', type: 'button', onclick: () => close() }, 'Close'))));
    for (const p of list) {
      const li = el('li', {},
        el('div', { class: 'nm' }, el('b', {}, p.name),
          el('small', {}, `${fmtDate(p.updated_at)} · ${fmtSize(p.bytes)}${p.share_slug ? ' · shared' : ''}`)),
        el('button', { class: 'd20c-btn primary', type: 'button', onclick: async () => {
          try {
            const r = await api('GET', `/api/projects/${p.id}`);
            App.load(r.data);
            currentId = r.id; currentName = r.name;
            render(); close();
            toast(`Opened "${r.name}"`);
          } catch (x) { toast(x.message); }
        } }, 'Open'),
        el('button', { class: 'd20c-btn danger', type: 'button', onclick: async (e) => {
          const b = e.currentTarget;
          if (b.dataset.armed !== '1') { b.dataset.armed = '1'; b.textContent = 'Confirm'; return; }
          try {
            await api('DELETE', `/api/projects/${p.id}`);
            li.remove();
            if (currentId === p.id) { currentId = null; render(); }
            toast(`Deleted "${p.name}"`);
          } catch (x) { toast(x.message); }
        } }, 'Delete'));
      ul.append(li);
    }
  }
  btnOpen.addEventListener('click', openDialog);

  // ---------- share ----------
  btnShare.addEventListener('click', async () => {
    if (!user || !currentId) return toast('Save to Cloud first, then share.');
    try {
      const { slug } = await api('POST', `/api/projects/${currentId}/share`);
      const url = `${location.origin}/?s=${encodeURIComponent(slug)}`;
      const input = el('input', { type: 'text', readonly: '' });
      input.value = url;
      const close = modal('Share link', el('div', {},
        el('p', {}, 'Anyone with this link can open a copy of the current cloud save. Later cloud saves update what the link shows.'),
        input,
        el('div', { class: 'd20c-row' },
          el('button', { class: 'd20c-btn danger', type: 'button', onclick: async () => {
            try { await api('DELETE', `/api/projects/${currentId}/share`); close(); toast('Share link disabled'); }
            catch (x) { toast(x.message); }
          } }, 'Disable link'),
          el('button', { class: 'd20c-btn primary', type: 'button', onclick: async () => {
            try { await navigator.clipboard.writeText(url); toast('Link copied'); }
            catch { input.select(); toast('Press Ctrl+C to copy'); }
          } }, 'Copy'),
          el('button', { class: 'd20c-btn', type: 'button', onclick: () => close() }, 'Close'))));
      input.select();
    } catch (x) { toast(x.message); }
  });

  // ---------- shared link on load ----------
  async function loadShared(slug) {
    try {
      const r = await api('GET', `/api/shared/${encodeURIComponent(slug)}`);
      App.load(r.data);
      currentId = null; currentName = '';
      const banner = el('div', { class: 'd20c-banner' },
        `Shared project: ${r.name}. Save to Cloud to keep your own copy.`);
      document.body.prepend(banner);
      history.replaceState(null, '', location.pathname);
    } catch (x) { toast(x.message); }
  }

  // ---------- boot ----------
  (async () => {
    try { user = (await api('GET', '/api/auth/me')).user; } catch {}
    render();
    const slug = new URLSearchParams(location.search).get('s');
    if (slug) loadShared(slug);
  })();
})();
