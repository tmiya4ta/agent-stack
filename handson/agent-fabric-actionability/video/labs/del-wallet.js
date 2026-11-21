// 流し直しの前の片付け: ワークショップの BG の demo-wallet を消す (録画しない)
s.lib(); await s.login(); await s.bg(s.V.WS);
await page.goto('https://omni.mulesoft.com/model-wallets', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(7000); await s.closeAgent();
if (!(await page.getByText('demo-wallet').first().isVisible().catch(() => false))) return 'none';
await page.getByText('demo-wallet').first().click(); await page.waitForTimeout(5000);
await page.locator('button, a').filter({ hasText: /^\s*Delete\s*$/ }).first().click(); await page.waitForTimeout(1500);
await page.getByRole('dialog').locator('button').filter({ hasText: /^\s*Delete\s*$/ }).click(); await page.waitForTimeout(4000);
return 'deleted';
