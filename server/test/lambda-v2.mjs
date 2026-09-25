// Drives the Express app through serverless-http with API Gateway HTTP API (v2) events,
// using the SQLite store, to check body parsing and Set-Cookie <-> cookies[] mapping.
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import serverless from 'serverless-http';
import { createApp } from '../src/app.js';
import { sqliteStore } from '../src/store/sqlite.js';

const app = createApp({
  store: sqliteStore(path.join(os.tmpdir(), `d20-v2-${Date.now()}.db`)),
  secret: 'x'.repeat(32), prod: true,
});
const h = serverless(app);

function ev(method, rawPath, { body, cookies } = {}) {
  return {
    version: '2.0', routeKey: '$default', rawPath, rawQueryString: '',
    cookies,
    headers: { host: 'studio.example.com', 'content-type': 'application/json', 'x-forwarded-for': '198.51.100.7, 203.0.113.1' },
    requestContext: { http: { method, path: rawPath, sourceIp: '203.0.113.1', protocol: 'HTTP/1.1' }, stage: '$default' },
    body: body ? JSON.stringify(body) : undefined,
    isBase64Encoded: false,
  };
}

let r = await h(ev('POST', '/api/auth/register', { body: { email: 'v2@example.com', password: 'longenough1' } }), {});
assert.equal(r.statusCode, 201, r.body);
const cookie = (r.cookies || [])[0] || (r.multiValueHeaders?.['set-cookie'] || [])[0] || r.headers?.['set-cookie'];
assert.ok(cookie && cookie.startsWith('d20_session='), 'session cookie returned: ' + JSON.stringify(r));
assert.ok(/Secure/i.test(cookie) && /HttpOnly/i.test(cookie), 'cookie flags');
console.log('ok   register returns Set-Cookie via', r.cookies ? 'cookies[]' : 'headers');

const c = cookie.split(';')[0];
r = await h(ev('GET', '/api/auth/me', { cookies: [c] }), {});
assert.equal(JSON.parse(r.body).user.email, 'v2@example.com');
console.log('ok   cookies[] on request authenticates');

r = await h(ev('POST', '/api/projects', { cookies: [c], body: { data: { format: 'd20-synth-project', name: 'v2', voices: [] } } }), {});
assert.equal(r.statusCode, 201, r.body);
console.log('ok   JSON body parsed');

r = await h(ev('GET', '/api/nope'), {});
assert.equal(r.statusCode, 404);
console.log('ok   unknown route 404\n\nall v2 adapter checks passed');
