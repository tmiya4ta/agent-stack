// Lab 4-2 Model Wallet (前半: Wallet を作り、予算を超えるまで)。Workshop UI は Lab 4-1 の続き (サインイン済み)
s.lib();
await s.login();
s.skipStart(); await s.bg(s.V.WS); s.skipEnd();
await s.uiOpen();
s.skipStart(); await s.tab('a'); s.skipEnd();
await s.intro('4-2', 'Model Wallet でユーザーごとに予算を管理する');
await s.step('Model Wallet は、呼び出し元の ID (JWT のクレーム) ごとに、LLM のトークンの消費を予算に照らして計測します', 4000);
await s.step('左のメニューの Model Proxies の下の Model Wallets を開き、右上の New Model Wallet をクリックします', 600);
await s.click(page.getByRole('link', { name: 'Model Proxies' }).first()); await page.waitForTimeout(3000);
await s.click(page.getByRole('link', { name: 'Model Wallets' }).first()); await page.waitForTimeout(3000);
await s.shot('11-wallets');
await s.click(page.getByRole('button', { name: /New Model Wallet/ }).or(page.getByRole('link', { name: /New Model Wallet/ })).first()); await page.waitForTimeout(4000);
await s.step('Name を demo-wallet にします。Environment は Sandbox のままです', 600);
await s.type(page.locator('#new-wallet-name'), 'demo-wallet');
await s.step('Claim key は cost_center、Claim values はご自身のユーザー名 (ここでは demo) です。あとで Workshop UI に入力する値と同じにします', 600);
await s.type(page.getByRole('textbox', { name: 'Claim key' }), 'cost_center');
await s.type(page.getByRole('textbox', { name: 'Claim values (comma-separated)' }), 'demo');
await page.waitForTimeout(1000);
await s.shot('11-wallet-claims');
await s.step('Add Budget で予算を追加します。Provider は OpenAI、Model は GPT 5 Mini、期間は Daily、単位は Tokens、上限は 5000 です', 600);
await s.click(page.getByRole('button', { name: 'Add Budget' })); await page.waitForTimeout(2000);
const d = page.getByRole('dialog');
await s.click(page.locator('#budget-provider')); await page.waitForTimeout(1000);
await s.click(page.getByRole('option', { name: 'OpenAI', exact: true })); await page.waitForTimeout(1000);
await s.click(page.locator('#budget-model')); await page.waitForTimeout(1000);
await s.click(page.getByRole('option', { name: 'GPT 5 Mini', exact: true })); await page.waitForTimeout(800);
await s.click(d.getByText('Daily', { exact: true })); await s.click(d.getByText('Tokens', { exact: true })); await page.waitForTimeout(800);
await s.click(d.locator('#budget-limit')); await d.locator('#budget-limit').fill('5000'); await page.waitForTimeout(1500);
await s.shot('11-budget-filled');
await s.click(d.getByRole('button', { name: 'Add Budget' })); await page.waitForTimeout(2000);
await s.step('上限を 5,000 トークンと小さくしているのは、試しているうちに上限に達し、超過したときの動作を確認できるようにするためです', 4000);
await s.step('Create Model Wallet をクリックします', 600);
await s.click(page.getByRole('button', { name: 'Create Model Wallet' })); await page.waitForTimeout(6000);
await s.step('Model Wallet が作成されました', 3000);
await s.shot('11-wallet-created');

await s.step('次に、Proxy のポリシーを変更します。Workshop UI のタブに戻り、Model Wallet タブを開きます', 600);
await s.tab('ui'); await page.waitForTimeout(1000);
await s.click(page.getByRole('button', { name: 'Model Wallet' })); await page.waitForTimeout(3000);
await s.step('MODEL PROXY POLICY CONFIGURATION で Lab 4-1 の demo-proxy を選択し、Use this proxy をクリックします', 600);
const sel = page.locator('select').filter({ visible: true }).first();
const sb = await sel.boundingBox(); await s.move(sb.x + sb.width / 2, sb.y + sb.height / 2); await page.waitForTimeout(400);
await sel.selectOption({ label: 'demo-proxy' }); await page.waitForTimeout(1500);
await s.click(page.getByRole('button', { name: /Use this proxy/ }).filter({ visible: true }).first()); await page.waitForTimeout(2500);
await s.step('Configure policies をクリックすると、変更内容が表示されます。Client ID Enforcement を外して JWT Validation を追加し、LLM Proxy Core が JWT のクレームを読むように変更します', 600);
await s.click(page.getByRole('button', { name: /Configure policies/ }).filter({ visible: true }).first()); await page.waitForTimeout(5000);
await s.shot('11-configure-preview');
await s.step('Confirm & apply をクリックします。ゲートウェイに反映されるまで 1 分ほど待ちます', 600);
await s.click(page.getByRole('button', { name: /Confirm & apply/ }).filter({ visible: true }).first());
s.skipStart(); await page.waitForTimeout(80000); s.skipEnd();
await s.step('ポリシーが変更されました。Workshop UI がスクリプトで Anypoint の API を呼び出して変更しています', 3500);
const inp = (ph) => page.locator(`xpath=//label[normalize-space(.)="${ph}"]/following::input[1]`).filter({ visible: true }).first();
await s.step('MODEL PROXY ENDPOINT に demo-proxy が入っていることを確認し、PATH を /chat/completions にします', 600);
const pathIn = page.locator('input[placeholder="/v1/chat/completions"]').filter({ visible: true }).first();
await s.type(pathIn, '/chat/completions');
await s.step('IDENTITY は Me (enter username) のまま、USERNAME に Wallet の Claim values と同じ demo を入力します', 600);
await s.type(page.locator('input[placeholder^="e.g. your name"]').filter({ visible: true }).first(), 'demo');
await page.waitForTimeout(1500);
const wsel = (n) => page.locator('select').filter({ visible: true }).nth(n);
const send = async () => {
  const before = (await page.innerText('body')).length;
  await s.click(page.getByRole('button', { name: 'Send', exact: true }).filter({ visible: true }).first());
  s.skipStart();
  for (let i = 0; i < 60; i++) { await page.waitForTimeout(1500); if (await page.getByRole('button', { name: 'Send', exact: true }).filter({ visible: true }).first().isEnabled() && (await page.innerText('body')).length > before + 50) break; }
  await page.waitForTimeout(2500);
  s.skipEnd();
};
await s.step('下の CODING から用意されたプロンプトを選択し、Send をクリックします', 600);
// 0: PROXY, 1: IDENTITY, 2: CODING, 3: FINANCE, 4: GENERAL, 5: JAILBREAK
await wsel(2).selectOption({ index: 1 }); await page.waitForTimeout(1200);
await send();
const log1 = await page.innerText('body');
if (!/demo-wallet/.test(log1)) throw new Error('wallet not engaged');
await s.shot('11-wallet-me');
await s.step('右の GOVERNANCE LOG に、ユーザー名、cost center、計測された Wallet (demo-wallet)、モデル、トークン数が表示されます', 5000);
await s.step('任意: (verbose) のプロンプトを何回か送信すると、1 日 5,000 トークンの予算を使い切ります', 600);
let blocked = false;
for (let i = 0; i < 8 && !blocked; i++) {
  await wsel(4).selectOption({ label: (await wsel(4).locator('option').allInnerTexts()).find(t => /verbose/.test(t)) }); await page.waitForTimeout(800);
  await send();
  blocked = /429/.test(await page.innerText('body'));
}
if (!blocked) throw new Error('budget not exceeded');
await s.shot('11-wallet-429');
await s.step('予算を使い切ると、次の呼び出しは 429 (budget exceeded) で停止します。予算は呼び出しの前に判定するため、最後の 1 回で上限を超えることがあります', 6000);

return 'ok';
