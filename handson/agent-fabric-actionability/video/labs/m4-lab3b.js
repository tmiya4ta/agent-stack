// Lab 4-3 Cost Optimization (後半: Tokens saved を確認する)。m4-lab3a のあとにつなぐ。集計が反映されてから録る (撮影時は翌日)
s.lib();
await s.login('https://omni.mulesoft.com/cost-management?tab=optimizations&scope=mcp-servers');
s.skipStart(); await s.bg(s.V.WS); await page.goto('https://omni.mulesoft.com/cost-management?tab=optimizations&scope=mcp-servers', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(8000); await s.closeAgent(); await s.watchHide('kurita'); s.skipEnd();
await s.step('Anypoint の Cost Management の Optimizations で、MCP Servers を選択します', 600);
await s.click(page.getByRole('button', { name: 'MCP Servers', exact: true }).or(page.getByRole('tab', { name: 'MCP Servers', exact: true })).last()); await page.waitForTimeout(6000);
const row = page.locator('main tr').filter({ hasText: 'commerce-mcp-demo' });
const b = await row.boundingBox(); await s.move(b.x + b.width * 0.55, b.y + b.height / 2);
const t = (await row.innerText()).replace(/\s+/g, ' ');
const m = t.match(/([\d.]+K?) tokens ([\d.]+K?) tokens (\d+)%/);
if (!m) throw new Error('row: ' + t);
await s.shot('12-tokens-saved');
await s.step(`commerce-mcp-demo の Tokens Saved に、削減されたトークン数 (${m[1]} トークン中 ${m[2]} トークン、${m[3]}%) が表示されます`, 5000);
await s.move(b.x + b.width * 0.85, b.y + b.height / 2);
await s.step('Optimizations には、適用した最適化の数 (3/5) が表示されます', 3500);
await s.step('Tool Mapping と Progressive Disclosure で、MCP のツールの定義が消費するトークンを削減できました', 4500);
return t;
