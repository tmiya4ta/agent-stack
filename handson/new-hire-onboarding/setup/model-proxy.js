// Model Proxy (旧 LLM Proxy) を Enhanced UI (omni.mulesoft.com) で作る。作る API は公開されていないので画面を操作する。
//
//   npm install playwright && npx playwright install chromium     (このフォルダの外で一度)
//   export ANYPOINT_USERNAME=... ANYPOINT_PASSWORD=... LLM_TOKEN=...
//   NODE_PATH=<playwright を入れた node_modules> node model-proxy.js [--dry-run]
//
// --dry-run は 1 ページ目を埋めたところで止め、スクリーンショット model-proxy-dry-run.png を残す。
// 作ったあとは `python anypoint_setup.py proxy-auth-off` で Client ID Enforcement を無効にする。
const { chromium } = require('playwright');

const cfg = {
  bg: process.env.BG || 'BG1',
  gateway: process.env.GATEWAY || 'agent-network-shared-gw',
  name: process.env.PROXY_NAME || 'workshop-llm-proxy',
  basePath: process.env.BASE_PATH || 'llm',
  destination: process.env.LLM_DESTINATION || 'https://llm-proxy.workshops.mulesoft.com/openai/v1/', // 末尾の / が要る
  token: process.env.LLM_TOKEN,
  dryRun: process.argv.includes('--dry-run'),
};

async function rootOrgName() {
  const r = await fetch('https://anypoint.mulesoft.com/accounts/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: process.env.ANYPOINT_USERNAME, password: process.env.ANYPOINT_PASSWORD }),
  });
  const { access_token } = await r.json();
  const me = await (await fetch('https://anypoint.mulesoft.com/accounts/api/me', {
    headers: { Authorization: `Bearer ${access_token}` },
  })).json();
  return me.user.organization.name;
}

(async () => {
  if (!cfg.token && !cfg.dryRun) throw new Error('LLM_TOKEN is required');
  const root = await rootOrgName();
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext({ viewport: { width: 1600, height: 1100 } })).newPage();
  try {
    await page.goto('https://anypoint.mulesoft.com/login/');
    await page.locator('#onetrust-accept-btn-handler').click({ force: true, timeout: 8000 }).catch(() => {});
    await page.fill('input[name="username"]', process.env.ANYPOINT_USERNAME);
    await page.fill('input[name="password"]', process.env.ANYPOINT_PASSWORD);
    await page.keyboard.press('Enter');
    await page.waitForURL(u => !u.toString().includes('/login'), { timeout: 60000 });

    await page.goto('https://omni.mulesoft.com/');
    await page.waitForTimeout(8000);
    // first visit shows a welcome dialog and a tour
    await page.locator('button:has-text("Start exploring")').click({ timeout: 3000 }).catch(() => {});
    await page.keyboard.press('Escape');
    // the BG switcher at the bottom left shows the root org after login
    await page.locator(`text=${root}`).first().click({ timeout: 15000 });
    await page.waitForTimeout(2000);
    await page.locator(`text=${cfg.bg}`).first().click({ timeout: 15000 });
    await page.waitForTimeout(6000);

    await page.locator('nav >> text=Model Proxies').first().click();
    await page.waitForTimeout(6000);
    await page.locator('button:has-text("Add Model Proxy")').first().click();
    await page.waitForTimeout(6000);

    // page 1: Configure Gateway (Format stays OpenAI, Environment stays Sandbox, Port stays 8081)
    await page.fill('input[placeholder*="Billing Triage"]', cfg.name);
    await page.fill('textarea', 'New hire onboarding workshop: brokers call the LLM through this proxy');
    await page.fill('input[placeholder="billing-ai"]', cfg.basePath);
    await page.locator('text=Omni Gateway* >> xpath=following::*[@role="combobox" or self::button or self::select][1]')
      .first().click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(2000);
    await page.locator(`[role=option]:has-text("${cfg.gateway}"), li:has-text("${cfg.gateway}")`).first().click();
    await page.waitForTimeout(2000);
    if (cfg.dryRun) {
      await page.screenshot({ path: 'model-proxy-dry-run.png' });
      console.log('dry run: page 1 filled, stopped before Continue');
      return;
    }
    // Continue creates the Exchange asset (POST omni.mulesoft.com/api/llm-proxies/create). It answers 409 when the
    // asset is left over from an interrupted run, and the form still moves on to page 2.
    await page.locator('button:has-text("Continue"):not([disabled])').click();
    await page.locator('input[placeholder="Route A"]').waitFor({ timeout: 120000 });

    // page 2: Configure Routing Strategy (Model-based, provider OpenAI because the destination takes Bearer)
    await page.fill('input[placeholder="Route A"]', 'workshop-llm');
    await page.fill('input[placeholder*="api.openai.com"], input[value="https://api.openai.com/v1/"]', cfg.destination);
    await page.fill('input[placeholder="Enter OpenAI API key"]', cfg.token);
    // Add Model Proxy creates the API Manager instance (POST omni.mulesoft.com/api/llm-proxies/deploy)
    await page.locator('button:has-text("Add Model Proxy"):not([disabled])').click();
    await page.waitForURL(u => u.toString().includes('/llms/'), { timeout: 180000 });
    console.log(`created model proxy ${cfg.name}: ${page.url()}`);
  } catch (e) {
    await page.screenshot({ path: 'model-proxy-error.png' });
    console.error(`failed (screenshot model-proxy-error.png): ${e.message.split('\n')[0]}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
