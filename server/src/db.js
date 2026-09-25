// SQLite storage via Node's built-in node:sqlite (Node >= 22.13, no native build step).
import { DatabaseSync } from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';

export function openDb(file) {
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
    userByEmail:   db.prepare('SELECT * FROM users WHERE email = ?'),
    userById:      db.prepare('SELECT id, email, created_at FROM users WHERE id = ?'),
    insertUser:    db.prepare('INSERT INTO users (email, pw_hash) VALUES (?, ?)'),

    listProjects:  db.prepare(`SELECT id, name, share_slug, created_at, updated_at, length(data) AS bytes
                               FROM projects WHERE user_id = ? ORDER BY updated_at DESC`),
    getProject:    db.prepare('SELECT * FROM projects WHERE id = ? AND user_id = ?'),
    insertProject: db.prepare('INSERT INTO projects (user_id, name, data) VALUES (?, ?, ?)'),
    updateProject: db.prepare(`UPDATE projects SET name = ?, data = ?,
                               updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                               WHERE id = ? AND user_id = ?`),
    deleteProject: db.prepare('DELETE FROM projects WHERE id = ? AND user_id = ?'),
    setShare:      db.prepare('UPDATE projects SET share_slug = ? WHERE id = ? AND user_id = ?'),
    bySlug:        db.prepare('SELECT name, data, updated_at FROM projects WHERE share_slug = ?'),
  };

  return { db, q };
}
