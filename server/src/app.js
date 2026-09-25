// Express app shared by the local/Docker server (SQLite) and the Lambda handler (DynamoDB + S3).
// All storage goes through an async `store` (see store/sqlite.js, store/aws.js).
import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { COOKIE, hashPassword, verifyPassword, makeSessions, parseCookies, rateLimit } from './auth.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function createApp({
  store,
  secret,
  prod = false,
  maxProjects = 200,
  maxBodyBytes = 10 * 1024 * 1024,
  kitDir = null,          // instrument-library folder, for /api/kits
  staticRoot = null,      // repo root; when set, the app also serves the frontend
  cloudDir = null,        // server/public (cloud.js)
}) {
  const sessions = makeSessions(secret);
  const app = express();
  app.set('trust proxy', true);
  app.disable('x-powered-by');

  app.use((req, res, next) => {
    res.set({
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'X-Frame-Options': 'SAMEORIGIN',
    });
    next();
  });
  app.use(express.json({ limit: maxBodyBytes }));

  const wrap = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

  // ---------- session helpers ----------
  function setSession(res, uid) {
    res.cookie(COOKIE, sessions.issue(uid), {
      httpOnly: true, sameSite: 'lax', secure: prod, maxAge: sessions.maxAgeMs, path: '/',
    });
  }
  async function currentUser(req) {
    const uid = sessions.read(parseCookies(req.headers.cookie)[COOKIE]);
    return uid ? store.getUser(uid) : null;
  }
  const requireUser = wrap(async (req, res, next) => {
    const user = await currentUser(req);
    if (!user) return res.status(401).json({ error: 'Not signed in.' });
    req.user = user;
    next();
  });

  // ---------- validation ----------
  function validProject(body) {
    const data = body && body.data;
    if (!data || typeof data !== 'object' || data.format !== 'd20-synth-project') {
      return 'Body must include data with format "d20-synth-project".';
    }
    return null;
  }
  function projectName(body) {
    const n = String((body && body.name) || (body && body.data && body.data.name) || 'Untitled').trim();
    return n.slice(0, 120) || 'Untitled';
  }

  // ---------- auth ----------
  const authLimit = rateLimit({ windowMs: 15 * 60e3, max: 30 });

  app.post('/api/auth/register', authLimit, wrap(async (req, res) => {
    const email = String(req.body?.email || '').trim().toLowerCase();
    const password = String(req.body?.password || '');
    if (!EMAIL_RE.test(email) || email.length > 254) return res.status(400).json({ error: 'Enter a valid email.' });
    if (password.length < 8 || password.length > 256) return res.status(400).json({ error: 'Password must be 8 to 256 characters.' });
    const user = await store.createUser(email, hashPassword(password));
    if (!user) return res.status(409).json({ error: 'That email is already registered.' });
    setSession(res, user.id);
    res.status(201).json({ user });
  }));

  app.post('/api/auth/login', authLimit, wrap(async (req, res) => {
    const email = String(req.body?.email || '').trim().toLowerCase();
    const auth = await store.getAuthByEmail(email);
    if (!auth || !verifyPassword(String(req.body?.password || ''), auth.pw_hash)) {
      return res.status(401).json({ error: 'Wrong email or password.' });
    }
    setSession(res, auth.id);
    res.json({ user: await store.getUser(auth.id) });
  }));

  app.post('/api/auth/logout', (req, res) => {
    res.clearCookie(COOKIE, { path: '/', httpOnly: true, sameSite: 'lax', secure: prod });
    res.json({ ok: true });
  });

  app.get('/api/auth/me', wrap(async (req, res) => res.json({ user: await currentUser(req) })));

  // ---------- projects ----------
  app.get('/api/projects', requireUser, wrap(async (req, res) => {
    res.json({ projects: await store.listProjects(req.user.id) });
  }));

  app.post('/api/projects', requireUser, wrap(async (req, res) => {
    const err = validProject(req.body);
    if (err) return res.status(400).json({ error: err });
    if ((await store.listProjects(req.user.id)).length >= maxProjects) {
      return res.status(403).json({ error: `Project limit (${maxProjects}) reached.` });
    }
    const id = await store.createProject(req.user.id, projectName(req.body), JSON.stringify(req.body.data));
    res.status(201).json({ id });
  }));

  app.get('/api/projects/:id', requireUser, wrap(async (req, res) => {
    const row = await store.getProject(req.user.id, req.params.id);
    if (!row) return res.status(404).json({ error: 'Not found.' });
    res.json({ id: row.id, name: row.name, share_slug: row.share_slug, updated_at: row.updated_at, data: JSON.parse(row.data) });
  }));

  app.put('/api/projects/:id', requireUser, wrap(async (req, res) => {
    const err = validProject(req.body);
    if (err) return res.status(400).json({ error: err });
    const ok = await store.updateProject(req.user.id, req.params.id, projectName(req.body), JSON.stringify(req.body.data));
    if (!ok) return res.status(404).json({ error: 'Not found.' });
    res.json({ ok: true });
  }));

  app.delete('/api/projects/:id', requireUser, wrap(async (req, res) => {
    if (!(await store.deleteProject(req.user.id, req.params.id))) return res.status(404).json({ error: 'Not found.' });
    res.json({ ok: true });
  }));

  app.post('/api/projects/:id/share', requireUser, wrap(async (req, res) => {
    const slug = await store.setShare(req.user.id, req.params.id);
    if (!slug) return res.status(404).json({ error: 'Not found.' });
    res.json({ slug });
  }));

  app.delete('/api/projects/:id/share', requireUser, wrap(async (req, res) => {
    if (!(await store.clearShare(req.user.id, req.params.id))) return res.status(404).json({ error: 'Not found.' });
    res.json({ ok: true });
  }));

  app.get('/api/shared/:slug', wrap(async (req, res) => {
    const row = await store.getShared(String(req.params.slug));
    if (!row) return res.status(404).json({ error: 'Share link not found.' });
    res.json({ name: row.name, updated_at: row.updated_at, data: JSON.parse(row.data) });
  }));

  // ---------- kits ----------
  app.get('/api/kits', (req, res) => {
    let files = [];
    try { files = kitDir ? fs.readdirSync(kitDir).filter(f => f.endsWith('.json')) : []; } catch {}
    const kits = files.map(f => {
      try { return { file: f, name: JSON.parse(fs.readFileSync(path.join(kitDir, f), 'utf8')).name || f }; }
      catch { return { file: f, name: f }; }
    });
    res.json({ kits });
  });

  const health = (req, res) => res.json({ ok: true });
  app.get('/healthz', health);
  app.get('/api/healthz', health);
  app.use('/api', (req, res) => res.status(404).json({ error: 'Unknown API route.' }));

  // ---------- frontend (local/Docker only; on AWS the site is served from S3) ----------
  if (staticRoot) {
    const indexFile = path.join(staticRoot, 'V2', 'index.html');
    let cache = null;
    const indexHtml = () => {
      if (cache && prod) return cache;
      return (cache = injectCloudScript(fs.readFileSync(indexFile, 'utf8')));
    };
    app.get(['/', '/index.html'], (req, res) => res.type('html').set('Cache-Control', 'no-cache').send(indexHtml()));
    if (cloudDir) app.use('/cloud', express.static(cloudDir, { maxAge: prod ? '1h' : 0 }));
    app.use('/instrument-library', express.static(path.join(staticRoot, 'V2', 'instrument-library')));
    app.use('/workbench', express.static(path.join(staticRoot, 'browser')));
  }

  app.use((err, req, res, next) => {
    if (err.type === 'entity.too.large') {
      return res.status(413).json({ error: `Project too large (${Math.round(maxBodyBytes / 1048576)} MB max).` });
    }
    if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'Invalid JSON.' });
    console.error(err);
    res.status(500).json({ error: 'Server error.' });
  });

  return app;
}

export const CLOUD_SCRIPT_TAG = '<script src="/cloud/cloud.js" defer></script>';
export function injectCloudScript(html) {
  return html.includes('</body>') ? html.replace('</body>', `${CLOUD_SCRIPT_TAG}\n</body>`) : html + CLOUD_SCRIPT_TAG;
}
