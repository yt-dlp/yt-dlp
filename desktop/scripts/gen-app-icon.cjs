// Renders assets/icon.svg to the PNG sizes the packager needs.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const svg = fs.readFileSync(path.join(__dirname, '..', 'assets', 'icon.svg'), 'utf8');
  const b = await chromium.launch();
  for (const size of [1024, 512, 256]) {
    const p = await b.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await p.setContent(`<style>html,body{margin:0;background:transparent}svg{width:${size}px;height:${size}px;display:block}</style>${svg}`);
    await p.screenshot({ path: path.join(__dirname, '..', 'assets', size === 1024 ? 'icon.png' : `icon-${size}.png`), omitBackground: true });
    await p.close();
  }
  await b.close();
})();
