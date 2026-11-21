// 準備: サインイン、Enhanced UI、ビジネスグループ
s.lib();
s.skipStart();
await ctx.clearCookies();
await page.goto('https://anypoint.mulesoft.com/login/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(4000);
const ok = page.locator('#onetrust-accept-btn-handler'); if (await ok.isVisible().catch(() => false)) { await ok.click({ force: true }); await page.waitForTimeout(800); }
s.skipEnd();
await s.step('はじめに、講師がご案内するユーザー名とパスワードで、Anypoint Platform にサインインします', 1500);
await s.type(page.locator('#nameInput'), s.V['Anypoint/ユーザー名']);
await s.type(page.locator('#passwordInput'), s.V['Anypoint/パスワード'], { delay: 30 });
await s.shot('01-login');
await s.click(page.getByRole('button', { name: 'Sign in' }));
await page.waitForTimeout(9000);
const nn = page.getByText('Not Now'); if (await nn.isVisible().catch(() => false)) { await s.step('メールアドレスの確認が表示された場合は、Not Now で閉じてかまいません', 1500); await s.click(nn); await page.waitForTimeout(3000); }
await s.step('ホーム画面の右上にある Switch to enhanced をクリックして、新しい画面 (Enhanced UI) を開きます', 2000);
await s.shot('01-switch-to-enhanced');
await s.sameTab(page.getByText('Switch to enhanced').first());
await page.waitForTimeout(8000);
const se = page.getByText('Start exploring', { exact: true });
if (await se.isVisible().catch(() => false)) {
  await s.step('初めて開くと、ウェルカム画面が表示されます。閉じてかまいません', 2500);
  await s.click(se); await page.waitForTimeout(2000);
}
const skip = page.getByRole('button', { name: 'Skip tour and close dialog' });
if (await skip.isVisible().catch(() => false)) { await s.click(skip); await page.waitForTimeout(1500); }
if (await page.getByText('MuleSoft Agent', { exact: true }).isVisible().catch(() => false)) {
  await s.step('右側に MuleSoft Agent のパネルが表示された場合も、閉じてかまいません', 2000);
  await s.closeAgent();
}
await s.step('Enhanced UI のホーム画面です。左のメニューから各機能を開きます', 2500);
await s.shot('01-omni-home');
for (const n of ['Agents', 'MCP Servers', 'Model Proxies', 'Cost Management', 'Providers']) {
  const l = page.getByRole('link', { name: n }).first(); const b = await l.boundingBox(); if (b) { await s.move(b.x + 40, b.y + b.height / 2); await page.waitForTimeout(500); }
}
await s.step(`左下のビジネスグループの切り替えを開くと、ご自身のユーザー名のものと、ワークショップ用の ${s.V.WS} が表示されます`, 1000);
await s.click(page.getByRole('combobox', { name: 'Business group selector' }));
await page.waitForTimeout(4000);
await s.shot('01-bg-switcher');
await page.keyboard.press('Escape'); await page.waitForTimeout(1500);
await s.step('これで準備は完了です', 2500);
return 'ok';
