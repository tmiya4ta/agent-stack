// ラボの台本で使う共通の操作。台本の最初で s.lib() を呼ぶと s に足される。
//   s.login()          Anypoint にサインインし、Enhanced UI を開く (動画からは切り取る)
//   s.bg(name)         左下のビジネスグループを切り替える
//   s.closeAgent()     右の MuleSoft Agent のパネルが出ていたら閉じる
//   s.intro(no, name)  ラボの最初の字幕「それではここから Lab no name を行います」
//   s.uiOpen()         Workshop UI のタブ ('ui') を開き、サインインして Anypoint につなぐ。narrate: false なら切り取る
//   s.mcpConnect(name) Workshop UI の MCP Client で、自分の MCP サーバーにつなぐ
module.exports = (s) => {
  const P = () => s.page;
  const visible = async (loc) => loc.first().isVisible().catch(() => false);

  s.login = async (url = 'https://omni.mulesoft.com/') => {
    s.skipStart();
    await s.tab('a');
    const page = P();
    await page.goto('https://anypoint.mulesoft.com/login/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3000);
    const ok = page.locator('#onetrust-accept-btn-handler'); if (await visible(ok)) { await ok.click({ force: true }); await page.waitForTimeout(800); }
    if (await visible(page.locator('#nameInput'))) {
      await page.fill('#nameInput', s.V['Anypoint/ユーザー名']); await page.fill('#passwordInput', s.V['Anypoint/パスワード']);
      await page.click('button:has-text("Sign in")'); await page.waitForTimeout(8000);
    }
    // 初めてサインインするアカウントでは、Cookie の同意がメールの確認 (Not Now) の上に重なる
    const ok2 = page.locator('#onetrust-accept-btn-handler'); if (await visible(ok2)) { await ok2.click({ force: true }); await page.waitForTimeout(1000); }
    const nn = page.getByText('Not Now'); if (await visible(nn)) await nn.click({ force: true });
    await page.goto(url, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(8000);
    for (const n of ['Skip tour and close dialog']) { const b = page.getByRole('button', { name: n }); if (await visible(b)) await b.click(); }
    const se = page.getByText('Start exploring', { exact: true }); if (await visible(se)) { await se.click(); await page.waitForTimeout(1500); const b = page.getByRole('button', { name: 'Skip tour and close dialog' }); if (await visible(b)) await b.click(); }
    await s.closeAgent();
    await page.waitForTimeout(1000);
    s.skipEnd();
  };

  s.closeAgent = async () => {
    const page = P();
    // Agentforce が有効な org では、パネルに「Close sidebar」がある (全画面にするボタンの隣)
    const cs = page.locator('button[aria-label="Close sidebar"]').filter({ visible: true });
    if (await cs.count()) { await cs.first().click(); await page.waitForTimeout(800); return; }
    const head = page.getByText('MuleSoft Agent', { exact: true });
    if (!(await visible(head))) return;
    const box = await head.first().boundingBox();
    // 見出しと同じ行の右端の × を押す
    const x = page.locator('button').filter({ has: page.locator('svg') });
    for (const b of await x.all()) {
      const bb = await b.boundingBox().catch(() => null);
      if (bb && box && Math.abs(bb.y + bb.height / 2 - (box.y + box.height / 2)) < 14 && bb.x > box.x) { await b.click(); await page.waitForTimeout(800); return; }
    }
  };

  s.bg = async (name, { narrate } = {}) => {
    const page = P();
    if (narrate) await s.step(narrate, 600);
    await s.click(page.getByRole('combobox', { name: 'Business group selector' }));
    await page.waitForTimeout(1000);
    const opt = page.getByRole('option', { name, exact: true });
    await s.click((await opt.count()) ? opt : page.getByText(name, { exact: true }).last());
    await page.waitForTimeout(3500);
    await s.closeAgent();
  };

  // ページに text が出たら、その部分だけを伏せ字にする (SPA の中で画面が変わっても効く。AWS のアカウント ID など)
  s.watchBlur = async (text) => P().evaluate((t) => {
    const mask = '•'.repeat(t.length);
    const hit = () => {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (w.nextNode()) if (w.currentNode.nodeValue.includes(t)) w.currentNode.nodeValue = w.currentNode.nodeValue.split(t).join(mask);
    };
    hit();
    new MutationObserver(hit).observe(document.body, { childList: true, subtree: true, characterData: true });
  }, text);

  // Exchange の下に出る Cookie の帯を、出たらすぐに消す
  s.hideCookieBar = async () => P().evaluate(() => {
    const hit = () => {
      for (const e of document.querySelectorAll('body *')) {
        if (e.children.length < 6 && /^We use cookies/.test((e.innerText || '').trim()) && e.style.display !== 'none') {
          let t = e; while (t.parentElement && t.parentElement !== document.body && t.parentElement.innerText.trim().length < (e.innerText.trim().length + 20)) t = t.parentElement;
          t.style.display = 'none';
        }
      }
    };
    hit();
    new MutationObserver(hit).observe(document.body, { childList: true, subtree: true });
  });

  // 12 桁の数字 (AWS のアカウント ID) を、出たらすぐに伏せ字にする
  s.watchAws = async () => P().evaluate(() => {
    const re = /\d{12}/g;
    const hit = () => {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (w.nextNode()) if (/\d{12}/.test(w.currentNode.nodeValue)) w.currentNode.nodeValue = w.currentNode.nodeValue.replace(re, '••••••••••••');
    };
    hit();
    new MutationObserver(hit).observe(document.body, { childList: true, subtree: true, characterData: true });
  });

  // text を含む行 (一覧の 1 行や 1 項目) を、出たらすぐに見えなくする (削除済みの kurita-wallet の集計など)
  s.watchHide = async (text) => P().evaluate((t) => {
    const hit = () => {
      let best = null;
      for (const e of document.querySelectorAll('body *')) {
        const it = e.innerText || '';
        if (it.includes(t) && /tokens|\d/.test(it) && e.offsetParent && (!best || it.length < best.innerText.length)) best = e;
      }
      if (best && best.style.visibility !== 'hidden') best.style.visibility = 'hidden';
    };
    hit();
    new MutationObserver(hit).observe(document.body, { childList: true, subtree: true, characterData: true });
  }, text);

  // 32 桁の英数字 (client_id / client_secret) を含む文字と入力欄を、出たらすぐにぼかす
  s.watchHex = async () => P().evaluate(() => {
    const re = /[0-9a-fA-F]{32}/;
    const hit = () => {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (w.nextNode()) if (re.test(w.currentNode.nodeValue)) w.currentNode.parentElement.style.filter = 'blur(7px)';
      for (const i of document.querySelectorAll('input, textarea')) if (re.test(i.value)) i.style.filter = 'blur(7px)';
    };
    hit();
    new MutationObserver(hit).observe(document.body, { childList: true, subtree: true, characterData: true });
    setInterval(hit, 150);
  });

  s.intro = async (no, name) => {
    await s.step(`それではここから、Lab ${no}「${name}」を行います`, 3000);
  };

  s.uiOpen = async ({ narrate = false } = {}) => {
    if (!narrate) s.skipStart();
    await s.tab('ui');
    const page = P();
    if (narrate) {
      // 初めて開くところを映すので、前に保存されたサインインを消しておく
      s.skipStart();
      await page.goto('https://actionability-ui.workshops.mulesoft.com/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(2000);
      await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
      await s.ctx.clearCookies({ domain: 'actionability-ui.workshops.mulesoft.com' });
      await page.goto('about:blank'); await page.waitForTimeout(500);
      s.skipEnd();
      await s.step('別のタブで Workshop UI を開き、講師がご案内するユーザー名とパスワードでサインインします', 600);
    }
    await page.goto('https://actionability-ui.workshops.mulesoft.com/', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(4000);
    if (await visible(page.getByRole('button', { name: 'Sign In' }))) {
      const ins = page.locator('input');
      await s.type(ins.nth(0), s.V['Broker/ユーザー名'], { delay: 30 }); await s.type(ins.nth(1), s.V['Broker/パスワード'], { delay: 30 });
      if (narrate) await s.shot('04-ui-signin');
      await s.click(page.getByRole('button', { name: 'Sign In' })); await page.waitForTimeout(4000);
    }
    if (narrate) await s.step('右上の Connect Anypoint を押し、Anypoint のユーザー名とパスワードを入力して接続します', 600);
    await s.click(page.getByRole('button', { name: 'Connect Anypoint' })); await page.waitForTimeout(1200);
    const ins = page.locator('input[data-form-type="other"]');
    await s.type(ins.nth(0), s.V['Anypoint/ユーザー名'], { delay: 30 });
    await s.type(ins.nth(1), s.V['Anypoint/パスワード'], { delay: 20 });
    if (narrate) await s.shot('04-connect-anypoint');
    await s.click(page.getByRole('button', { name: 'Connect', exact: true }).first()); await page.waitForTimeout(5000);
    if (narrate) await s.step(`ビジネスグループに ${s.V.WS}、環境に Sandbox を選択します`, 600);
    const sel = page.locator('select').filter({ visible: true });
    const pick = async (loc, label) => { const b = await loc.boundingBox(); if (b) { await s.move(b.x + b.width / 2, b.y + b.height / 2); await page.waitForTimeout(400); } await loc.selectOption({ label }); await page.waitForTimeout(2500); };
    await pick(sel.nth(0), s.V.WS);
    await pick(sel.nth(1), 'Sandbox');
    if (narrate) await s.shot('04-bg-env');
    await page.mouse.click(700, 600); await page.waitForTimeout(1000);
    if (!narrate) s.skipEnd();
  };

  // Workshop UI のボタンは aria-label か title に名前がある (表示は → など)
  s.uiBtn = (name) => P().locator(`button[aria-label="${name}"], button[title="${name}"]`).filter({ visible: true }).first();

  // Multi-Agent Orchestrator で Broker を選んで URL を確定する
  s.broker = async ({ narrate = true } = {}) => {
    const page = P();
    if (narrate) await s.step('上の欄で vogue_premiere を選択し、横の → をクリックすると、Agent Broker の欄に URL が入ります', 600);
    const sel = page.locator('select').filter({ visible: true }).first();
    const b = await sel.boundingBox(); await s.move(b.x + b.width / 2, b.y + b.height / 2); await page.waitForTimeout(400);
    await sel.selectOption({ label: 'vogue_premiere' }); await page.waitForTimeout(1500);
    await s.click(s.uiBtn('Use this proxy')); await page.waitForTimeout(2500);
    if (narrate) await s.step('右端の → をクリックして、Broker の URL を確定します', 600);
    await s.click(s.uiBtn('Confirm broker URL')); await page.waitForTimeout(2500);
  };

  // 用意されたプロンプトを押して、応答を待つ。押したボタンが戻るまで待ち、次のプロンプトが押せるようになれば成功
  // (確認の質問が返ったときは次が押せないので、案内してから押し直す)。最後のプロンプトは、ボタンが戻れば完了とする
  s.prompt = async (re, { retryNote = 'Broker が確認の質問を返すことがあります。その場合は、同じプロンプトをもう一度クリックします' } = {}) => {
    const page = P();
    const chips = page.locator('button.prompt-chip').filter({ visible: true });
    const names = await chips.evaluateAll(es => es.map(e => e.innerText));
    const idx = names.findIndex(t => re.test(t));
    if (idx < 0) throw new Error('no prompt ' + re);
    for (let i = 0; i < 3; i++) {
      await s.click(chips.nth(idx));
      await page.waitForTimeout(4000);
      s.skipStart();
      for (let k = 0; k < 90 && (await chips.nth(idx).isDisabled()); k++) await page.waitForTimeout(2000);
      await page.waitForTimeout(2500);
      s.skipEnd();
      // 最後のプロンプトは次が無いので、ボタンが戻れば応答が返ったとみなす (他人の注文のように、Reasoning Map が増えない応答もある)
      const ok = idx + 1 < names.length ? !(await chips.nth(idx + 1).isDisabled()) : true;
      if (ok) return;
      if (i < 2) await s.step(retryNote, 3500);
    }
    throw new Error('no answer for ' + re);
  };

  // セッションの最初のプロンプトには経路 (Reasoning Map) が付かないことがある。付くまで送り直す
  s.promptMap = async (re) => {
    const page = P();
    for (let i = 0; i < 3; i++) {
      await s.prompt(re);
      await page.waitForTimeout(2000);
      if (await visible(page.getByText('Showing the active branch only'))) return;
      await s.step('経路が表示されない場合は、同じプロンプトをもう一度クリックします', 2500);
    }
    throw new Error('no reasoning map for ' + re);
  };

  s.mcpConnect = async (name = 'commerce-mcp-demo', { shot } = {}) => {
    const page = P();
    const sel = page.locator('select').filter({ visible: true }).first();
    const b = await sel.boundingBox(); await s.move(b.x + b.width / 2, b.y + b.height / 2); await page.waitForTimeout(400);
    await sel.selectOption({ label: name }); await page.waitForTimeout(1500);
    const use = page.getByRole('button', { name: /Use this proxy/ }); if (await use.count()) await s.click(use);
    if (shot) await s.shot(shot);
    await s.click(page.getByRole('button', { name: /^Connect/ }).last()); await page.waitForTimeout(6000);
  };
};
