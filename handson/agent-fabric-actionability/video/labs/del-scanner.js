// 録画の前の片付け: ご自身の BG の demo Scanner を消す (録画しない)
s.lib(); await s.login(); await s.bg(s.V['Anypoint/ユーザー名']);
await page.goto('https://omni.mulesoft.com/providers', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(6000);
if (!(await page.getByText('demo Scanner').first().isVisible().catch(() => false))) return 'none';
await page.getByText('demo Scanner').first().click(); await page.waitForTimeout(5000);
await page.getByText('Settings', { exact: true }).first().click(); await page.waitForTimeout(2500);
await page.getByRole('button', { name: 'Delete Scanner' }).click(); await page.waitForTimeout(1500);
await page.getByRole('dialog').getByRole('button', { name: 'Delete Scanner' }).click(); await page.waitForTimeout(4000);
return 'deleted';
