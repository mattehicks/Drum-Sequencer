// SQLite store (local dev + Docker) on Node's built-in node:sqlite.
import { DatabaseSync } from 'node:sqlite';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export function sqliteStore(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new DatabaseSync(file);
  db.exec(`
    PRAGMA journal_mode = WAL;
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS users (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
      pw_hash     TEXT NOT NULL,
      created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    CREATE TABLE IF NOT EXISTS projects (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      name        TEXT NOT NULL,
      data        TEXT NOT NULL,
      share_slug  TEXT UNIQUE,
      created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id, updated_at DESC);
  `);

  const q = {
    userByEmail: db.prepare('SELECT id, pw_hash FROM users WHERE email = ?'),
    userById:    db.prepare('SELECT id, email, created_at FROM users WHERE id = ?'),
    insertUser:  db.prepare('INSERT INTO users (email, pw_hash) VALUES (?, ?)'),
    list:   db.prepare(`SELECT id, name, share_slug, created_at, updated_at, length(data) AS bytes
                        FROM projects WHERE user_id = ? ORDER BY updated_at DESC`),
    get:    db.prepare('SELECT * FROM projects WHERE id = ? AND user_id = ?'),
    insert: db.prepare('INSERT INTO projects (user_id, name, data) VALUES (?, ?, ?)'),
    update: db.prepare(`UPDATE projects SET name = ?, data = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                        WHERE id = ? AND user_id = ?`),
    del:    db.prepare('DELETE FROM projects WHERE id = ? AND user_id = ?'),
    share:  db.prepare('UPDATE projects SET share_slug = ? WHERE id = ? AND user_id = ?'),
    slug:   db.prepare('SELECT name, data, updated_at FROM projects WHERE share_slug = ?'),
  };
  const pid = (id) => Number(id) || 0;

  return {
    async createUser(email, pwHash) {
      if (q.userByEmail.get(email)) return null;
      const { lastInsertRowid } = q.insertUser.run(email, pwHash);
      return q.userById.get(lastInsertRowid);
    },
    async getAuthByEmail(email) { return q.userByEmail.get(email) || null; },
    async getUser(id) { return q.userById.get(Number(id)) || null; },
    async listProjects(uid) { return q.list.all(uid); },
    async createProject(uid, name, data) { return Number(q.insert.run(uid, name, data).lastInsertRowid); },
    async getProject(uid, id) { return q.get.get(pid(id), uid) || null; },
    async updateProject(uid, id, name, data) { return q.update.run(name, data, pid(id), uid).changes > 0; },
    async deleteProject(uid, id) { return q.del.run(pid(id), uid).changes > 0; },
    async setShare(uid, id) {
      const row = q.get.get(pid(id), uid);
      if (!row) return null;
      const slug = row.share_slug || crypto.randomBytes(9).toString('base64url');
      q.share.run(slug, row.id, uid);
      return slug;
    },
    async clearShare(uid, id) { return q.share.run(null, pid(id), uid).changes > 0; },
    async getShared(slug) { return q.slug.get(slug) || null; },
  };
}
