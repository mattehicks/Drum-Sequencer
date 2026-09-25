// D20 Synth Workbench server: static frontend + accounts + cloud projects + share links.
import express from 'express';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openDb } from './db.js';
import { COOKIE, hashPassword, verifyPassword, makeSessions, parseCookies, rateLimit } from './auth.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(process.env.APP_ROOT || path.join(here, '..', '..'));
const PORT = Number(process.env.PORT || 8080);
const DB_FILE = process.env.DB_FILE || path.join(here, '..', 'data', 'd20.db');
const PROD = process.env.NODE_ENV === 'production';
const MAX_PROJECTS = Number(process.env.MAX_PROJECTS_PER_USER || 200);

let SECRET = process.env.SESSION_SECRET;
if (!SECRET) {
  if (PROD) { console.error('SESSION_SECRET is required in production'); process.exit(1); }
  SECRET = crypto.randomBytes(32).toString('hex');
  console.warn('SESSION_SECRET not set; using a random dev secret (sessions reset on restart).');
}

const { q } = openDb(DB_FILE);
const sessions = makeSessions(SECRET);
const app = express();
app.set('trust proxy', 1); // behind Caddy
app.disable('x-powered-by');

app.use((req, res, next) => {
  res.set({
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'X-Frame-Options': 'SAMEORIGIN',
  });
  next();
});
app.use(express.json({ limit: '10mb' }));

// ---------- session helpers ----------
function setSession(res, uid) {
  res.cookie(COOKIE, sessions.issue(uid), {
    httpOnly: true, sameSite: 'lax', secure: PROD, maxAge: sessions.maxAgeMs, path: '/',
  });
}
function currentUser(req) {
  const uid = sessions.read(parseCookies(req.headers.cookie)[COOKIE]);
  return uid ? q.userById.get(uid) : null;
}
function requireUser(req, res, next) {
  const user = currentUser(req);
  if (!user) return res.status(401).json({ error: 'Not signed in.' });
  req.user = user;
  next();
}

// ---------- validation ----------
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
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

app.post('/api/auth/register', authLimit, (req, res) => {
  const email = String(req.body?.email || '').trim().toLowerCase();
  const password = String(req.body?.password || '');
  if (!EMAIL_RE.test(email)) return res.status(400).json({ error: 'Enter a valid email.' });
  if (password.length < 8) return res.status(400).json({ error: 'Password must be at least 8 characters.' });
  if (q.userByEmail.get(email)) return res.status(409).json({ error: 'That email is already registered.' });
  const { lastInsertRowid } = q.insertUser.run(email, hashPassword(password));
  setSession(res, Number(lastInsertRowid));
  res.status(201).json({ user: q.userById.get(lastInsertRowid) });
});

app.post('/api/auth/login', authLimit, (req, res) => {
  const email = String(req.body?.email || '').trim().toLowerCase();
  const row = q.userByEmail.get(email);
  if (!row || !verifyPassword(String(req.body?.password || ''), row.pw_hash)) {
    return res.status(401).json({ error: 'Wrong email or password.' });
  }
  setSession(res, row.id);
  res.json({ user: q.userById.get(row.id) });
});

app.post('/api/auth/logout', (req, res) => {
  res.clearCookie(COOKIE, { path: '/' });
  res.json({ ok: true });
});

app.get('/api/auth/me', (req, res) => res.json({ user: currentUser(req) }));

// ---------- projects ----------
app.get('/api/projects', requireUser, (req, res) => {
  res.json({ projects: q.listProjects.all(req.user.id) });
});

app.post('/api/projects', requireUser, (req, res) => {
  const err = validProject(req.body);
  if (err) return res.status(400).json({ error: err });
  if (q.listProjects.all(req.user.id).length >= MAX_PROJECTS) {
    return res.status(403).json({ error: `Project limit (${MAX_PROJECTS}) reached.` });
  }
  const { lastInsertRowid } = q.insertProject.run(req.user.id, projectName(req.body), JSON.stringify(req.body.data));
  res.status(201).json({ id: Number(lastInsertRowid) });
});

app.get('/api/projects/:id', requireUser, (req, res) => {
  const row = q.getProject.get(Number(req.params.id), req.user.id);
  if (!row) return res.status(404).json({ error: 'Not found.' });
  res.json({ id: row.id, name: row.name, share_slug: row.share_slug, updated_at: row.updated_at, data: JSON.parse(row.data) });
});

app.put('/api/projects/:id', requireUser, (req, res) => {
  const err = validProject(req.body);
  if (err) return res.status(400).json({ error: err });
  const r = q.updateProject.run(projectName(req.body), JSON.stringify(req.body.data), Number(req.params.id), req.user.id);
  if (!r.changes) return res.status(404).json({ error: 'Not found.' });
  res.json({ ok: true });
});

app.delete('/api/projects/:id', requireUser, (req, res) => {
  const r = q.deleteProject.run(Number(req.params.id), req.user.id);
  if (!r.changes) return res.status(404).json({ error: 'Not found.' });
  res.json({ ok: true });
});

app.post('/api/projects/:id/share', requireUser, (req, res) => {
  const row = q.getProject.get(Number(req.params.id), req.user.id);
  if (!row) return res.status(404).json({ error: 'Not found.' });
  const slug = row.share_slug || crypto.randomBytes(9).toString('base64url');
  q.setShare.run(slug, row.id, req.user.id);
  res.json({ slug });
});

app.delete('/api/projects/:id/share', requireUser, (req, res) => {
  const r = q.setShare.run(null, Number(req.params.id), req.user.id);
  if (!r.changes) return res.status(404).json({ error: 'Not found.' });
  res.json({ ok: true });
});

app.get('/api/shared/:slug', (req, res) => {
  const row = q.bySlug.get(String(req.params.slug));
  if (!row) return res.status(404).json({ error: 'Share link not found.' });
  res.json({ name: row.name, updated_at: row.updated_at, data: JSON.parse(row.data) });
});

// ---------- kits ----------
const KIT_DIR = path.join(APP_ROOT, 'V2', 'instrument-library');
app.get('/api/kits', (req, res) => {
  let files = [];
  try { files = fs.readdirSync(KIT_DIR).filter(f => f.endsWith('.json')); } catch {}
  const kits = files.map(f => {
    try { return { file: f, name: JSON.parse(fs.readFileSync(path.join(KIT_DIR, f), 'utf8')).name || f }; }
    catch { return { file: f, name: f }; }
  });
  res.json({ kits });
});

app.get('/healthz', (req, res) => res.json({ ok: true }));
app.use('/api', (req, res) => res.status(404).json({ error: 'Unknown API route.' }));

// ---------- frontend ----------
const INDEX_FILE = path.join(APP_ROOT, 'V2', 'index.html');
const INJECT = '<script src="/cloud/cloud.js" defer></script>';
let indexCache = null;
function indexHtml() {
  if (indexCache && PROD) return indexCache;
  const html = fs.readFileSync(INDEX_FILE, 'utf8');
  indexCache = html.includes('</body>') ? html.replace('</body>', `${INJECT}\n</body>`) : html + INJECT;
  return indexCache;
}

app.get(['/', '/index.html'], (req, res) => {
  res.type('html').set('Cache-Control', 'no-cache').send(indexHtml());
});
app.use('/cloud', express.static(path.join(here, '..', 'public'), { maxAge: PROD ? '1h' : 0 }));
app.use('/instrument-library', express.static(KIT_DIR));
app.use('/workbench', express.static(path.join(APP_ROOT, 'browser')));

app.use((err, req, res, next) => {
  if (err.type === 'entity.too.large') return res.status(413).json({ error: 'Project too large (10 MB max).' });
  if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'Invalid JSON.' });
  console.error(err);
  res.status(500).json({ error: 'Server error.' });
});

app.listen(PORT, () => console.log(`D20 server on :${PORT} (root ${APP_ROOT})`));
