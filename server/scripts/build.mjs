// Builds the AWS deploy artifacts into <repo>/build:
//   build/site    static frontend for S3 (index.html with cloud.js injected, kits, workbench)
//   build/lambda  bundled API handler (index.mjs) + instrument-library for /api/kits
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { injectCloudScript } from '../src/app.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const out = path.join(root, 'build');
const site = path.join(out, 'site');
const lambdaDir = path.join(out, 'lambda');

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(site, { recursive: true });
fs.mkdirSync(lambdaDir, { recursive: true });

// ---- site ----
const html = fs.readFileSync(path.join(root, 'V2', 'index.html'), 'utf8');
if (!html.includes('window.D20App')) throw new Error('V2/index.html is missing the window.D20App hook');
fs.writeFileSync(path.join(site, 'index.html'), injectCloudScript(html));
fs.cpSync(path.join(root, 'V2', 'instrument-library'), path.join(site, 'instrument-library'), { recursive: true });
fs.cpSync(path.join(root, 'browser'), path.join(site, 'workbench'), { recursive: true });
fs.cpSync(path.join(here, '..', 'public'), path.join(site, 'cloud'), { recursive: true });

// S3 serves text/html without a charset, so every page must declare UTF-8 itself
// (within the first 1024 bytes), or browsers decode it as Windows-1252.
function ensureCharset(file) {
  const src = fs.readFileSync(file, 'utf8');
  if (/<meta[^>]+charset\s*=/i.test(src.slice(0, 1024))) return false;
  const tag = '<meta charset="utf-8">';
  const m = src.slice(0, 1024).match(/<head(\s[^>]*)?>/i);   // not <header>
  fs.writeFileSync(file, m ? src.replace(m[0], `${m[0]}\n${tag}`) : `${tag}\n${src}`);
  const out = fs.readFileSync(file, 'utf8');
  if (!/<meta charset="utf-8">/.test(out.slice(0, 1024))) throw new Error(`charset not in first 1024 bytes of ${file}`);
  return true;
}
const htmlFiles = fs.readdirSync(site, { recursive: true }).filter(f => f.endsWith('.html')).map(f => path.join(site, f));
const fixed = htmlFiles.filter(ensureCharset);
console.log(`charset added to ${fixed.length}/${htmlFiles.length} html files`);

// favicon.ico (browsers request it unconditionally; a missing S3 key returns 403).
// 32x32 PNG in an ICO container: accent-orange rounded square matching the D20 badge.
{
  const S = 32, R = 7, px = Buffer.alloc(S * (S * 4 + 1));
  for (let y = 0; y < S; y++) {
    px[y * (S * 4 + 1)] = 0; // filter: none
    for (let x = 0; x < S; x++) {
      const dx = Math.max(R - x, x - (S - 1 - R), 0), dy = Math.max(R - y, y - (S - 1 - R), 0);
      const inside = dx * dx + dy * dy <= R * R;
      const o = y * (S * 4 + 1) + 1 + x * 4;
      px[o] = 0xff; px[o + 1] = 0x8a; px[o + 2] = 0x3d; px[o + 3] = inside ? 255 : 0;
    }
  }
  const zlib = await import('node:zlib');
  const crcT = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (b) => { let c = 0xffffffff; for (const v of b) c = crcT[(c ^ v) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const c = Buffer.alloc(4); c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(S, 0); ihdr.writeUInt32BE(S, 4); ihdr[8] = 8; ihdr[9] = 6;
  const png = Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(px)), chunk('IEND', Buffer.alloc(0))]);
  const ico = Buffer.alloc(22);
  ico.writeUInt16LE(0, 0); ico.writeUInt16LE(1, 2); ico.writeUInt16LE(1, 4);
  ico[6] = S; ico[7] = S; ico.writeUInt16LE(1, 10); ico.writeUInt16LE(32, 12);
  ico.writeUInt32LE(png.length, 14); ico.writeUInt32LE(22, 18);
  fs.writeFileSync(path.join(site, 'favicon.ico'), Buffer.concat([ico, png]));
}

// ---- lambda ----
await build({
  entryPoints: [path.join(here, '..', 'src', 'lambda.js')],
  outfile: path.join(lambdaDir, 'index.mjs'),
  bundle: true,
  platform: 'node',
  target: 'node22',
  format: 'esm',
  minify: true,
  sourcemap: false,
  legalComments: 'none',
  // CJS deps (express) call require(); give the ESM bundle a real one.
  banner: { js: "import { createRequire as __cr } from 'module'; const require = __cr(import.meta.url);" },
});
fs.cpSync(path.join(root, 'V2', 'instrument-library'), path.join(lambdaDir, 'instrument-library'), { recursive: true });

const size = (d) => fs.readdirSync(d, { recursive: true, withFileTypes: true })
  .filter(e => e.isFile()).reduce((n, e) => n + fs.statSync(path.join(e.parentPath ?? e.path, e.name)).size, 0);
console.log(`site   ${(size(site) / 1024).toFixed(0)} KB -> ${path.relative(root, site)}`);
console.log(`lambda ${(size(lambdaDir) / 1024).toFixed(0)} KB -> ${path.relative(root, lambdaDir)}`);
