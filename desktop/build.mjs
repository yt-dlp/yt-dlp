// Bundles the three parts of the app: main process, preload script, window.
import { build, context } from 'esbuild';
import { cpSync, mkdirSync, rmSync } from 'node:fs';

const watch = process.argv.includes('--watch');
const common = { bundle: true, sourcemap: true, logLevel: 'info', target: 'es2022', minify: !watch };

const targets = [
  { ...common, entryPoints: ['src/main/main.ts'], outfile: 'dist/main/main.js', platform: 'node', format: 'cjs', external: ['electron', 'electron-updater'] },
  { ...common, entryPoints: ['src/preload/preload.ts'], outfile: 'dist/preload/preload.js', platform: 'node', format: 'cjs', external: ['electron'] },
  {
    ...common, entryPoints: ['src/renderer/app.tsx'], outdir: 'dist/renderer', platform: 'browser', format: 'iife',
    jsx: 'automatic', jsxImportSource: 'preact', assetNames: 'fonts/[name]', loader: { '.woff2': 'file', '.woff': 'file' },
  },
];

rmSync('dist', { recursive: true, force: true });
mkdirSync('dist/renderer', { recursive: true });
cpSync('src/renderer/index.html', 'dist/renderer/index.html');

if (watch) {
  for (const t of targets) await (await context(t)).watch();
} else {
  await Promise.all(targets.map((t) => build(t)));
}
