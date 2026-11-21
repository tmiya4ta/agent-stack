// Lab 3-2 Agent Visualizer
s.lib();
await s.login();
s.skipStart(); await s.bg(s.V.WS); s.skipEnd();
await s.intro('3-2', 'Agent Visualizer でネットワークを可視化する');
await s.step('Agent Visualizer は、従来の Anypoint Platform の画面にあります。左下の Go to Anypoint Platform をクリックします', 600);
await s.sameTab(page.getByRole('link', { name: 'Go to Anypoint Platform' }).first()); await page.waitForTimeout(6000);
const nn = page.getByText('Not Now'); if (await nn.isVisible().catch(() => false)) await nn.click();
await s.step('上部の Agents & Tools から、Agent Visualizer をクリックします', 600);
await s.click(page.getByText('Agents & Tools').first()); await page.waitForTimeout(1500);
const link = page.locator('a[href*="agentvisualizer"]').filter({ visible: true }).first();
await s.move(...(await link.boundingBox().then(b => [b.x + 40, b.y + b.height / 2]))); await page.waitForTimeout(600);
await page.goto('https://anypoint.mulesoft.com/visualizer/agentvisualizer/', { waitUntil: 'domcontentloaded' });
s.skipStart(); await page.getByRole('button', { name: 'Toggle filters panel' }).waitFor({ timeout: 60000 });
for (let i = 0; i < 40 && (await page.locator('.canvas-loading-spinner').count()); i++) await page.waitForTimeout(1500);
// 前の設定が残っていたら、既定の Production に戻しておく (切り取る)
const sb = page.getByRole('radio', { name: 'Sandbox environment' });
await page.getByRole('button', { name: 'Toggle filters panel' }).click(); await page.waitForTimeout(1500);
if (await sb.isChecked()) {
  await page.getByText('Production environment', { exact: true }).click(); await page.waitForTimeout(500);
  await page.getByRole('button', { name: 'Apply Filters' }).click(); await page.waitForTimeout(2000);
  for (let i = 0; i < 40 && (await page.locator('.canvas-loading-spinner').count()); i++) await page.waitForTimeout(1500);
} else await page.getByRole('button', { name: 'Close filters panel' }).click();
await page.waitForTimeout(3000); s.skipEnd();
await s.shot('08-visualizer');
await s.step(`右上のフィルターを開き、Business Groups で ${s.V.WS}、Environment で Sandbox environment を選択して、Apply Filters をクリックします`, 600);
const tg = page.getByRole('button', { name: 'Toggle filters panel' });
if ((await tg.getAttribute('aria-expanded')) !== 'true') await s.click(tg); else { const b = await tg.boundingBox(); await s.move(b.x + 10, b.y + 10); }
await page.waitForTimeout(2000);
const ws = page.getByLabel(s.V.WS);
if (!(await ws.isChecked())) await s.click(page.getByText(s.V.WS, { exact: true }).last()); else { const b = await ws.boundingBox(); await s.move(b.x + 6, b.y + 6); await page.waitForTimeout(600); }
await s.click(page.getByText('Sandbox environment', { exact: true })); await page.waitForTimeout(800);
await s.shot('08-filters-set');
await s.click(page.getByRole('button', { name: 'Apply Filters' })); await page.waitForTimeout(2000);
for (let i = 0; i < 40 && (await page.locator('.canvas-loading-spinner').count()); i++) await page.waitForTimeout(1500);
await page.waitForTimeout(1500);
if (await page.getByRole('button', { name: 'Close filters panel' }).isVisible().catch(() => false)) await s.click(page.getByRole('button', { name: 'Close filters panel' }));
await s.click(page.getByRole('button', { name: 'Fit View' })); await page.waitForTimeout(2000);
await s.shot('08-graph-full');
await s.step('Vogue Premiere の Broker を中心に、Styling、Availability、Loyalty の各エージェントと Commerce MCP Server が表示されます', 4500);
await s.step('Lab 2-1 で作成した commerce-mcp-demo も表示されています。ノードはエージェントと MCP サーバー、線はそのつながりを表します', 4500);
await s.step('Availability Agent のノードをクリックすると、詳細のカードが表示されます', 600);
await s.click(page.getByText('Availability Agent', { exact: true }).first()); await page.waitForTimeout(3500);
await s.shot('08-node-details');
await s.step('プラットフォーム、プロトコル (A2A)、ビジネスグループ、環境、適用されているポリシーを確認できます', 4500);
const perf = page.getByText('Performance and Health', { exact: true }).first();
if (await perf.count()) await s.scrollTo(perf, 'start');
await s.step('過去 24 時間のリクエストの数と失敗の割合、メトリクス、トレース、ログへのリンクも表示されます', 4500);
await s.click(page.getByRole('button', { name: 'close Inspector' })).catch(() => {});
await page.waitForTimeout(1000); await s.click(page.getByRole('button', { name: 'Fit View' })); await page.waitForTimeout(1500);
await s.step('右上の虫めがねでは名前や種類からノードを検索でき、フィルターではビジネスグループ、環境、期間で表示を絞り込めます', 600);
const q = page.locator('input[type=search]').first();
const qb = await q.boundingBox(); await s.move(qb.x + 60, qb.y + qb.height / 2); await page.waitForTimeout(2500);
const fb = await page.getByRole('button', { name: 'Toggle filters panel' }).boundingBox(); await s.move(fb.x + 10, fb.y + 10); await page.waitForTimeout(2500);
await s.step('大きなネットワークでも、見たい範囲に絞り込んで、エージェントとツールのつながりを把握できます', 4000);
return 'ok';
