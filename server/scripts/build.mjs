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
