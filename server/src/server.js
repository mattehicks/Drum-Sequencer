// Local / Docker entrypoint: Express + SQLite, also serves the frontend.
import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createApp } from './app.js';
import { sqliteStore } from './store/sqlite.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(process.env.APP_ROOT || path.join(here, '..', '..'));
const PORT = Number(process.env.PORT || 8080);
const DB_FILE = process.env.DB_FILE || path.join(here, '..', 'data', 'd20.db');
const PROD = process.env.NODE_ENV === 'production';

let secret = process.env.SESSION_SECRET;
if (!secret) {
  if (PROD) { console.error('SESSION_SECRET is required in production'); process.exit(1); }
  secret = crypto.randomBytes(32).toString('hex');
  console.warn('SESSION_SECRET not set; using a random dev secret (sessions reset on restart).');
}

const app = createApp({
  store: sqliteStore(DB_FILE),
  secret,
  prod: PROD,
  maxProjects: Number(process.env.MAX_PROJECTS_PER_USER || 200),
  kitDir: path.join(APP_ROOT, 'V2', 'instrument-library'),
  staticRoot: APP_ROOT,
  cloudDir: path.join(here, '..', 'public'),
});

app.listen(PORT, () => console.log(`D20 server on :${PORT} (root ${APP_ROOT})`));
