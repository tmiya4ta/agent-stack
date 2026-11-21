// Lab 2-1 MCP Bridge (後半: Workshop UI でツールを試す)。前半の m2-lab1a のあとにつなぐ
s.lib();
await s.login('https://omni.mulesoft.com/mcp-servers/commerce-mcp-demo');
s.skipStart(); await s.bg(s.V.WS); await page.goto('https://omni.mulesoft.com/mcp-servers/commerce-mcp-demo', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(7000); await s.closeAgent(); s.skipEnd();
await s.step('作成した MCP サーバーのツールを、Workshop UI から実行してみます', 2500);
await s.uiOpen({ narrate: true });
await s.step('MCP Client タブの BROWSE MY MCP SERVERS で commerce-mcp-demo を選択し、Use this proxy をクリックして、Connect をクリックします', 600);
await s.mcpConnect('commerce-mcp-demo', { shot: '04-pick-mcp' });
await s.shot('04-mcp-connected');
await s.step('左に TOOLS (6) と表示されれば、接続できています。上から順にツールを実行します', 3500);
const tool = (n) => page.getByText(n, { exact: true }).first();
const run = async () => { await s.click(page.getByRole('button', { name: /Run Tool/ })); await page.waitForTimeout(6000); };
const field = (name) => page.locator('input').filter({ visible: true }).and(page.locator(`xpath=//*[normalize-space(text())="${name}" or normalize-space(text())="${name}*"]/following::input[1]`));

await s.step('1. get_customers を選択し、Run Tool をクリックします。顧客の一覧が返ります', 600);
await s.click(tool('get_customers')); await page.waitForTimeout(1500);
await run(); await page.waitForTimeout(2500);
await s.shot('04-tool-1-result');

await s.step('2. post_customers で顧客を作成します。username には、ほかと重複しない値を入力します (ここでは demo-ws2)', 600);
await s.click(tool('post_customers')); await page.waitForTimeout(1500);
await s.type(field('username').first(), 'demo-ws2');
await s.shot('04-tool-2-form-filled');
await run();
const body = await page.innerText('body');
const cid = (body.match(/CUST-\d+/g) || []).filter(x => x !== 'CUST-100001').pop();
if (!cid) throw new Error('customer not created');
await s.step(`顧客が作成され、ID (${cid}) が採番されました`, 3000);

await s.step('3. get_customers_customerId には、いま作成した顧客の ID が自動で入っています。Run Tool をクリックします', 600);
await s.click(tool('get_customers_customerId')); await page.waitForTimeout(1500);
if (!(await page.locator('input').evaluateAll(es => es.map(e => e.value))).includes(cid)) throw new Error('customerId not carried over (3)');
await run(); await page.waitForTimeout(1500);

await s.step('4. put_customers_customerId で、作成した顧客の会員ランクを Gold、ポイントを 500 に更新します', 600);
await s.click(tool('put_customers_customerId')); await page.waitForTimeout(1500);
const v4 = await page.locator('input').evaluateAll(es => es.map(e => e.value));
if (!v4.includes(cid) || v4.includes('CUST-100001')) throw new Error('customerId not carried over (4): ' + v4.join(','));
await run(); await page.waitForTimeout(1500);

await s.step('5. createOrder で、見本の値のまま Alex の注文を作成します (2 つ目の API のツールです)', 600);
await s.click(tool('createOrder')); await page.waitForTimeout(1500);
await run(); await page.waitForTimeout(1500);

await s.step('6. getShippingStatus で、作成した注文の配送状況を取得します', 600);
await s.click(tool('getShippingStatus')); await page.waitForTimeout(1500);
await run(); await page.waitForTimeout(2000);
await s.shot('04-tool-6-result');
await s.step('2 つの REST API を、コーディングなしで 1 つの MCP サーバーにまとめ、エージェントが使えるツールにできました', 4000);
return cid;
