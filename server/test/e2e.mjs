// End-to-end API check against a running server. Usage: BASE=http://localhost:8099 node test/e2e.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.env.BASE || 'http://localhost:8080';
const here = path.dirname(fileURLToPath(import.meta.url));
const kit = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'V2', 'instrument-library', 'kit-808-classic.json'), 'utf8'));

let cookie = '';
async function call(method, url, body, expect) {
  const res = await fetch(BASE + url, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(cookie ? { Cookie: cookie } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const set = res.headers.get('set-cookie');
  if (set) cookie = set.split(';')[0];
  const json = await res.json().catch(() => ({}));
  if (expect) assert.equal(res.status, expect, `${method} ${url} -> ${res.status} ${JSON.stringify(json)}`);
  return json;
}

const email = `t${Date.now()}@example.com`;
const pass = (m) => console.log('ok  ', m);

const html = await (await fetch(BASE + '/')).text();
assert.ok(html.includes('/cloud/cloud.js'), 'index injects cloud.js');
assert.ok(html.includes('window.D20App'), 'index exposes D20App hook');
pass('index served with cloud hook + script');

assert.equal((await fetch(BASE + '/cloud/cloud.js')).status, 200); pass('cloud.js served');
assert.equal((await fetch(BASE + '/instrument-library/kit-808-classic.json')).status, 200); pass('kit static');
assert.ok((await call('GET', '/api/kits', null, 200)).kits.length >= 8); pass('kits list');

await call('GET', '/api/projects', null, 401); pass('projects require auth');
await call('POST', '/api/auth/register', { email, password: 'short' }, 400); pass('short password rejected');
await call('POST', '/api/auth/register', { email, password: 'hunter2hunter2' }, 201); pass('register');
assert.equal((await call('GET', '/api/auth/me', null, 200)).user.email, email); pass('me');
await call('POST', '/api/auth/register', { email, password: 'hunter2hunter2' }, 409); pass('duplicate email rejected');

await call('POST', '/api/projects', { data: { format: 'wrong' } }, 400); pass('bad format rejected');
const data = { ...kit, name: 'E2E Beat' };
const { id } = await call('POST', '/api/projects', { data }, 201); pass('create project');
assert.equal((await call('GET', '/api/projects', null, 200)).projects[0].name, 'E2E Beat'); pass('list');
await call('PUT', `/api/projects/${id}`, { data: { ...data, name: 'E2E Beat v2' } }, 200); pass('update');
const got = await call('GET', `/api/projects/${id}`, null, 200);
assert.equal(got.name, 'E2E Beat v2'); assert.equal(got.data.voices.length, kit.voices.length); pass('get round-trips data');

const { slug } = await call('POST', `/api/projects/${id}/share`, null, 200); pass('share');
const saved = cookie;
cookie = '';
assert.equal((await call('GET', `/api/shared/${slug}`, null, 200)).name, 'E2E Beat v2'); pass('public shared read');
await call('GET', `/api/projects/${id}`, null, 401); pass('anon cannot read private');

// second user cannot touch first user's project
await call('POST', '/api/auth/register', { email: 'x' + email, password: 'hunter2hunter2' }, 201);
await call('GET', `/api/projects/${id}`, null, 404);
await call('DELETE', `/api/projects/${id}`, null, 404); pass('cross-user isolation');

cookie = saved;
await call('DELETE', `/api/projects/${id}/share`, null, 200);
cookie = ''; await call('GET', `/api/shared/${slug}`, null, 404); cookie = saved; pass('unshare');
await call('DELETE', `/api/projects/${id}`, null, 200); pass('delete');
await call('POST', '/api/auth/logout', null, 200);
cookie = '';
await call('POST', '/api/auth/login', { email, password: 'wrongwrong' }, 401); pass('bad login rejected');
await call('POST', '/api/auth/login', { email, password: 'hunter2hunter2' }, 200); pass('login');

console.log('\nall checks passed');
