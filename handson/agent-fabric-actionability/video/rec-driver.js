// Lab ごとの操作動画を録るドライバ。ブラウザを開いたまま、localhost に送った JS を順に実行する。
//
//   HANDSON_ENV=<env.json のパス> node rec-driver.js
//   POST /start?lab=lab1   新しいブラウザ (録画つき) を開く。プロファイルは out/profile を使い回す
//   POST /run              本文の JS を実行する。失敗した区間は bad として記録し、あとで切り取る
//   POST /stop             ブラウザを閉じて out/<lab>.webm と out/<lab>.json (字幕の元と切り取る区間) を書く
//
// JS の中で使えるもの: s.step('字幕'), s.click(loc), s.type(loc, text), s.blur(loc), s.skipStart(), s.skipEnd(), s.V['見出し/項目']
//   s.tab('ui') でタブを切り替える (無ければ開く)。最初のタブは 'a' (Anypoint)。タブごとに録画し、process.py が
//   切り替えた順につなぐ (Workshop UI を別のタブに置いておけば、Anypoint を行き来しても接続が切れない)。
//   JS の中の page は、いま前にあるタブを指す
const { chromium } = require(process.env.PLAYWRIGHT || 'C:/Users/tmiyashita/pw-browser/node_modules/playwright');
const http = require('http'), path = require('path'), fs = require('fs');
const { CURSOR_INIT_SCRIPT } = require('./cursor-script');

const OUT = path.join(__dirname, 'out');
const W = 1440, H = 900;
fs.mkdirSync(OUT, { recursive: true });

const env = JSON.parse(fs.readFileSync(process.env.HANDSON_ENV, 'utf8'));
const V = {};
for (const sec of env.sections) for (const i of sec.items) V[sec.title.split(' ')[0] + '/' + i.label] = i.value;
// CRED=-1 なら、見出しが「Anypoint-1」などの値 (ブース 1) を「Anypoint」として使う。WS_BG はワークショップの BG の名前
const CRED = process.env.CRED || '';
if (CRED) for (const k of Object.keys(V)) { if (k.split('/')[0].endsWith(CRED)) V[k.split('/')[0].slice(0, -CRED.length) + '/' + k.split('/').slice(1).join('/')] = V[k]; }
V.WS = process.env.WS_BG || 'Agent_Actionability_Workshop';
// ANYPOINT_USER で、env.json とは別の Anypoint のユーザーで操作する (パスワードは全員共通)
// LLM の見出しが「Azure OpenAI LLM …」の env.json でも、台本は LLM/token で読む
if (!V['LLM/token'] && V['Azure/token']) V['LLM/token'] = V['Azure/token'];
if (process.env.ANYPOINT_USER) V['Anypoint/ユーザー名'] = process.env.ANYPOINT_USER;
// STEP_FAST=1 なら字幕の間の待ちを短くする (画像だけを撮るとき)
const STEP_MAX = process.env.STEP_FAST ? 300 : Infinity;
// 録画用 (out/profile) とは別のブラウザのプロファイルを使うとき (別のユーザーでサインインする)
const PROFILE = process.env.PROFILE || path.join(OUT, 'profile');

let s = null;

function now() { return (Date.now() - s.t0) / 1000; }

async function start(lab) {
  const raw = path.join(OUT, 'raw-' + lab);
  fs.rmSync(raw, { recursive: true, force: true });
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    headless: true, viewport: { width: W, height: H }, deviceScaleFactor: 1, locale: 'en-US',
    recordVideo: { dir: raw, size: { width: W, height: H } },
    httpCredentials: { username: V['Broker/ユーザー名'], password: V['Broker/パスワード'] },
  });
  await ctx.addInitScript(CURSOR_INIT_SCRIPT);
  for (const p of ctx.pages()) await p.close();
  s = { lab, ctx, raw, t0: Date.now(), marks: [], bad: [], skips: [], V, require, tabs: {}, timeline: [] };
  s.tab = async (name) => {
    if (!s.tabs[name]) { const start = now(); s.tabs[name] = { page: await ctx.newPage(), start }; }
    const p = s.tabs[name].page;
    await p.bringToFront();
    s.page = p;
    s.timeline.push({ sec: now(), tab: name });
    return name;
  };
  await s.tab('a');
  ctx.on('page', p => { s.last = p; });
  // labs/common.js の共通の操作を s に足す (編集したら読み直す)
  s.lib = () => { const p = require.resolve('./labs/common'); delete require.cache[p]; require(p)(s); return 'lib ok'; };

  // 字幕の区切り。説明を読む間があるように、既定で少し止まる
  s.step = async (label, wait = 1200) => { s.marks.push({ sec: now(), label }); console.log(`[${lab} ${now().toFixed(1)}] ${label}`); await s.page.waitForTimeout(Math.min(wait, STEP_MAX)); };
  s.skipStart = () => { s.skips.push({ start: now() }); };
  s.skipEnd = () => { const k = s.skips[s.skips.length - 1]; if (k && k.end === undefined) k.end = now(); };
  s.move = async (x, y) => s.page.mouse.move(x, y, { steps: 25 });
  s.click = async (loc, { before = 450, after = 700 } = {}) => {
    loc = loc.first();
    await loc.scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
    const b = await loc.boundingBox();
    if (b) { await s.move(b.x + b.width / 2, b.y + b.height / 2); await s.page.waitForTimeout(before); }
    await loc.click({ timeout: 10000 });
    await s.page.waitForTimeout(after);
  };
  s.type = async (loc, text, { delay = 45, clear = true } = {}) => {
    await s.click(loc, { after: 200 });
    if (clear) { await s.page.keyboard.press('Control+A'); await s.page.keyboard.press('Delete'); }
    await s.page.keyboard.type(text, { delay });
    await s.page.waitForTimeout(400);
  };
  s.scrollTo = async (loc, block = 'center') => { await loc.first().evaluate((e, b) => e.scrollIntoView({ behavior: 'smooth', block: b }), block); await s.page.waitForTimeout(1500); };
  // 長い文 (発話の一覧など) は貼り付けたように一度に入れる
  s.paste = async (loc, text) => { await s.click(loc, { after: 200 }); await loc.first().fill(text); await s.page.waitForTimeout(600); };
  // 秘密の欄をぼかす (録画に値が映らないように、入力の前に呼ぶ)
  s.blur = async (loc) => loc.first().evaluate(e => { e.style.filter = 'blur(7px)'; });
  s.blurText = async (text) => s.page.evaluate(t => {
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) if (w.currentNode.nodeValue.includes(t)) w.currentNode.parentElement.style.filter = 'blur(7px)';
  }, text);
  // 原稿の画像 (codelab/media の名前) を out/shots に撮る
  s.shot = async (name) => { fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true }); const vis = v => s.page.evaluate(v => { const c = document.getElementById('pw-cursor'); if (c) c.style.visibility = v; }, v).catch(() => {}); await vis('hidden'); await s.page.screenshot({ path: path.join(OUT, 'shots', name + '.png') }); await vis('visible'); };
  s.dbg = async () => s.page.screenshot({ path: path.join(OUT, 'dbg.png') });
  // 新しいタブで開くリンクを、同じタブで開き直す (動画を 1 本に保つため)
  s.sameTab = async (loc) => {
    const [p] = await Promise.all([s.ctx.waitForEvent('page', { timeout: 15000 }).catch(() => null), s.click(loc)]);
    if (p) { await p.waitForLoadState('domcontentloaded').catch(() => {}); await p.waitForTimeout(1500); const u = p.url(); await p.close(); await s.page.goto(u, { waitUntil: 'domcontentloaded' }); }
  };
  s.texts = async (sel = 'button, a, [role=menuitem], [role=tab], [role=option], label, h1, h2, h3') =>
    (await s.page.$$eval(sel, els => els.filter(e => e.offsetParent !== null).map(e => (e.innerText || e.value || '').trim().replace(/\s+/g, ' ')).filter(t => t && t.length < 80))).join(' | ');
  return `started ${lab}`;
}

async function stop() {
  const { ctx, lab, raw } = s;
  const end = now();
  const tabs = {};
  for (const [name, t] of Object.entries(s.tabs)) tabs[name] = { start: t.start, video: t.page.video() };
  await ctx.close();
  for (const [name, t] of Object.entries(tabs)) {
    t.file = `${lab}.${name}.webm`;
    fs.copyFileSync(await t.video.path(), path.join(OUT, t.file));
    delete t.video;
  }
  fs.writeFileSync(path.join(OUT, lab + '.json'), JSON.stringify({ lab, end, tabs, timeline: s.timeline, marks: s.marks, bad: s.bad, skips: s.skips }, null, 1));
  s = null;
  return `stopped ${lab} (${end.toFixed(1)}s)`;
}

http.createServer((req, res) => {
  let body = ''; req.on('data', c => body += c);
  req.on('end', async () => {
    const url = new URL(req.url, 'http://x');
    try {
      let out;
      if (url.pathname === '/start') out = await start(url.searchParams.get('lab'));
      else if (url.pathname === '/stop') out = await stop();
      else {
        const t = now();
        try {
          // page はいま前にあるタブ (s.tab で切り替えても追いかける)
          const page = new Proxy({}, { get: (_, k) => { const v = s.page[k]; return typeof v === 'function' ? v.bind(s.page) : v; } });
          const fn = new Function('s', 'page', 'ctx', `return (async () => { ${body} })()`);
          out = await fn(s, page, s.ctx);
        } catch (e) {
          s.bad.push({ start: t, end: now(), error: String(e).slice(0, 200) });
          throw e;
        }
      }
      res.end(typeof out === 'string' ? out : JSON.stringify(out, null, 1) ?? 'ok');
    } catch (e) { res.statusCode = 500; res.end(String(e && e.stack || e)); }
  });
}).listen(9334, '127.0.0.1', () => console.log('rec driver ready on 9334'));
