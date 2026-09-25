// Password hashing (scrypt) and stateless signed session cookies (HMAC-SHA256).
import crypto from 'node:crypto';

const SCRYPT = { N: 16384, r: 8, p: 1, keylen: 64 };
export const COOKIE = 'd20_session';
const SESSION_DAYS = 30;

export function hashPassword(pw) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(pw, salt, SCRYPT.keylen, SCRYPT);
  return `scrypt$${salt.toString('base64')}$${hash.toString('base64')}`;
}

export function verifyPassword(pw, stored) {
  const [alg, saltB64, hashB64] = String(stored).split('$');
  if (alg !== 'scrypt') return false;
  const expected = Buffer.from(hashB64, 'base64');
  const actual = crypto.scryptSync(pw, Buffer.from(saltB64, 'base64'), expected.length, SCRYPT);
  return crypto.timingSafeEqual(actual, expected);
}

export function makeSessions(secret) {
  const sign = (payload) =>
    crypto.createHmac('sha256', secret).update(payload).digest('base64url');

  function issue(userId) {
    const payload = Buffer.from(JSON.stringify({
      uid: userId,
      exp: Date.now() + SESSION_DAYS * 864e5,
    })).toString('base64url');
    return `${payload}.${sign(payload)}`;
  }

  function read(token) {
    if (!token || typeof token !== 'string') return null;
    const [payload, sig] = token.split('.');
    if (!payload || !sig) return null;
    const good = Buffer.from(sign(payload));
    const got = Buffer.from(sig);
    if (good.length !== got.length || !crypto.timingSafeEqual(good, got)) return null;
    try {
      const data = JSON.parse(Buffer.from(payload, 'base64url').toString());
      return data.exp > Date.now() ? data.uid : null;
    } catch { return null; }
  }

  return { issue, read, maxAgeMs: SESSION_DAYS * 864e5 };
}

export function parseCookies(header) {
  const out = {};
  for (const part of String(header || '').split(';')) {
    const i = part.indexOf('=');
    if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

// Minimal in-memory fixed-window limiter for auth endpoints (single-instance deploy).
export function rateLimit({ windowMs, max }) {
  const hits = new Map();
  setInterval(() => hits.clear(), windowMs).unref();
  return (req, res, next) => {
    const key = req.ip;
    const n = (hits.get(key) || 0) + 1;
    hits.set(key, n);
    if (n > max) return res.status(429).json({ error: 'Too many attempts, try again later.' });
    next();
  };
}
