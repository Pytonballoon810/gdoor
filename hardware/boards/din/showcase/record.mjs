// Renders the showcase to showcase.mp4 (full quality) and showcase.gif (for
// the README). Each frame is rendered at an exact time through ?capture, so
// the result does not depend on how fast the machine is.
//
//   npm install
//   npm run record                  (Edge on Windows; set BROWSER for another
//                                    Chromium-based browser)
import { createServer } from 'node:http';
import { readFile, mkdir, rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { extname, join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';
import ffmpeg from 'ffmpeg-static';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');           // hardware/boards/din: the page loads ../enclosure
const FRAMES = join(HERE, 'frames');
const W = 1280, H = 720, FPS = 30;
const BROWSER = process.env.BROWSER ?? 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.glb': 'model/gltf-binary', '.stl': 'model/stl', '.png': 'image/png', '.json': 'application/json' };
const server = createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = resolve(ROOT, '.' + (path.endsWith('/') ? path + 'index.html' : path));
  if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' }).end(body);
  } catch { res.writeHead(404).end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const url = `http://127.0.0.1:${server.address().port}/showcase/?capture`;

await rm(FRAMES, { recursive: true, force: true });
await mkdir(FRAMES);
const browser = await puppeteer.launch({
  executablePath: BROWSER, headless: true,
  args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', `--window-size=${W},${H}`],
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
page.on('pageerror', e => console.error('page:', e.message));
await page.goto(url, { waitUntil: 'networkidle0', timeout: 120000 });
await page.waitForFunction('window.__showcaseReady === true', { timeout: 120000 });
const duration = await page.evaluate('__showcase.DURATION');
const n = Math.round(duration * FPS);
for (let i = 0; i < n; i++) {
  await page.evaluate(t => __showcase.renderAt(t), i / FPS);
  await page.screenshot({ path: join(FRAMES, `f${String(i).padStart(5, '0')}.png`) });
  if (i % 150 === 0) console.log(`frame ${i} / ${n}`);
}
await browser.close();
server.close();

const run = args => {
  const r = spawnSync(ffmpeg, ['-y', '-loglevel', 'error', ...args], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error('ffmpeg failed: ' + args.join(' '));
};
const input = ['-framerate', String(FPS), '-i', join(FRAMES, 'f%05d.png')];
run([...input, '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-pix_fmt', 'yuv420p',
  '-movflags', '+faststart', join(HERE, 'showcase.mp4')]);
run([...input, '-vf', 'fps=8,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle',
  join(HERE, 'showcase.gif')]);
await rm(FRAMES, { recursive: true, force: true });
console.log('wrote showcase.mp4 and showcase.gif');
