// Lab 4-2 Model Wallet (後半: 費用を確認する)。m4-lab2a のあとにつなぐ。集計が反映されてから録る (撮影時は翌日)
// Budgets の一覧の Used は 0% のままだった (判定の 429 は動いている) ので、TOP MODEL WALLETS のトークン数を見せる
s.lib();
await s.login();
s.skipStart(); await s.bg(s.V.WS); await page.goto('https://omni.mulesoft.com/llms/demo-proxy', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(7000); await s.closeAgent(); await s.watchHide('kurita'); s.skipEnd();
await s.step('費用を確認します。Model Proxy の demo-proxy のページで、Monitoring タブを開きます', 600);
await s.click(page.getByRole('tab', { name: 'Monitoring' }).or(page.getByRole('button', { name: 'Monitoring', exact: true })).first()); await page.waitForTimeout(9000);
await s.shot('10-proxy-monitoring');
await s.step('総トークン数と、入力と出力のトークン数が表示されます。Model Proxy を経由する呼び出しは、すべて計測されています', 5000);
const top = page.getByText('Top Client Applications by Tokens').first();
await s.scrollTo(top, 'center');
await s.shot('11-proxy-monitoring-identity');
await s.step('Top Client Applications by Tokens には、呼び出し元ごとのトークン数が表示されます。JWT の ID (demo) と、Lab 4-1 のアプリケーション (demo Application) が分けて計測されています', 6000);
await s.step('左のメニューの Cost Management を開き、Budgets と Tokens を選択します', 600);
await s.click(page.getByRole('link', { name: 'Cost Management' }).first()); await page.waitForTimeout(3000);
await s.watchHide('kurita');
await page.waitForTimeout(6000);
await s.click(page.getByRole('button', { name: 'Tokens', exact: true }).or(page.getByRole('tab', { name: 'Tokens', exact: true })).first()); await page.waitForTimeout(3000);
const tw = page.getByText('TOP MODEL WALLETS', { exact: false }).first();
const b = await tw.boundingBox(); if (b) await s.move(b.x + 60, b.y + 40);
await s.shot('11-cost-management');
await s.step('管理されているトークンの合計と、プロバイダーごと、Wallet ごと (TOP MODEL WALLETS) のトークン数が表示されます', 5000);
const row = page.locator('main tr').filter({ hasText: 'demo-wallet' }).first();
const rb = await row.boundingBox(); if (rb) await s.move(rb.x + rb.width * 0.5, rb.y + rb.height / 2);
const rt = rb ? (await row.innerText()).replace(/\s+/g, ' ') : '';
const pct = rt.match(/(\d+)%/);
if (/At Limit/.test(rt)) {
  await s.step(`下の一覧には、Wallet ごとの上限と使用量が表示されます。demo-wallet は 1 日 5K トークンの上限に対して ${pct[1]}% を使い、At Limit になっています`, 5500);
  await s.step('予算は呼び出しの前に判定するため、最後の 1 回で上限を超えることがあります', 4000);
} else {
  await s.step('下の一覧には、Wallet ごとのモデルと上限 (demo-wallet は 1 日 5K トークン) が表示されます', 4500);
}
await s.step('ワークショップの規模では金額は数セント程度のため、トークン数で確認するほうが変化をつかみやすくなります', 4000);
return 'ok';
