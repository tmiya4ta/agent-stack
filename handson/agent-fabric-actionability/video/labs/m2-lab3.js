// Lab 2-3 Orchestration (+ 任意: Broker の構成方法)
s.lib();
await s.login();
await s.uiOpen();
s.skipStart(); await s.mcpConnect(); s.skipEnd();
await s.intro('2-3', 'Orchestration で複数のエージェントを連携させる');
await s.step('Workshop UI の上部の Multi-Agent Orchestrator タブを開きます', 600);
await s.click(page.getByRole('button', { name: 'Multi-Agent Orchestrator' })); await page.waitForTimeout(3500);
await s.step('MCP Client タブは 1 つの MCP サーバーに直接つなぎました。このタブは Broker につなぎ、Broker がネットワークのエージェントとツールを使い分けます', 4500);
await s.broker();
await s.shot('06-broker-selected');
await s.step('右の Sign in to Vogue Premiere で Alex Chen を選択し、サインインします', 600);
await s.click(page.getByRole('button', { name: /Alex Chen/ }).first()); await page.waitForTimeout(800);
await s.shot('06-persona-signin');
await s.click(page.getByRole('button', { name: 'Sign In as Alex Chen' })); await page.waitForTimeout(6000);
await s.step('実際の ID プロバイダーへのサインインです。発行されたトークンがリクエストのたびに Broker に送られ、Broker はこの顧客に代わって動作します', 4500);
await s.click(s.uiBtn('Zoom out')); await page.waitForTimeout(800); await s.click(s.uiBtn('Zoom out')); await page.waitForTimeout(1200);
await s.step('左はエージェントのネットワークの図、中央の Orchestration は Broker の処理の過程、右は用意されたプロンプトとチャットです', 4500);

await s.step('右上の SUGGESTED PROMPTS にあるプロンプトを、上から順にクリックします。1 つ目は、ディナーに着ていく服の相談です', 600);
await s.promptMap(/dinner in Napa/);
await s.shot('06-p1-chat');
await s.step('Styling Agent が服を提案しました。左の図では、使われたエージェントと MCP サーバーが強調表示されます', 4000);
await s.step('中央の Reasoning Map には、Broker が経由したノードが上から順に表示されます', 3000);
await s.step('顧客の情報の取得、意図の分類、振り分けの共通の処理のあと、分類した意図 (styling) の分岐だけを実行しています', 4500);
await s.step('ノードをクリックすると、その処理の説明が表示されます', 600);
await s.click(page.getByText('Classify Intent', { exact: true }).first()); await page.waitForTimeout(3500);
await s.shot('06-p1-reasoning-map');
await s.step('STEP は AI を使わない決まった処理、LLM は言語モデルによる推論、A2A はエージェント、MCP はツールの呼び出しです', 4500);

await s.step('2 つ目のプロンプトをクリックして、4 つの商品に自分のサイズの在庫があるかを確認します', 600);
await s.prompt(/available in my size/);
await s.step('Availability Agent が在庫を確認しました。Broker はサインインで顧客を把握しているので、サイズを伝える必要はありません', 4500);
await s.step('Trace タブには、Broker 自身が出力した生の記録 (意図、ユーザー、経路、呼び出した接続先) が表示されます', 600);
await s.click(page.getByRole('button', { name: 'Trace' })); await page.waitForTimeout(3500);
await page.mouse.move(840, 500); await page.mouse.wheel(0, 300); await page.waitForTimeout(2500);
await s.shot('06-p2-trace');
await s.click(page.getByRole('button', { name: 'Reasoning Map' })); await page.waitForTimeout(1500);

await s.step('3 つ目のプロンプトをクリックして、会員の特典を確認します', 600);
await s.prompt(/loyalty perks/);
await s.step('Loyalty Agent が、会員ランクに応じた特典を回答しました', 3500);

await s.step('4 つ目のプロンプトをクリックして、コーディネート一式を注文します', 600);
await s.prompt(/Place the order/);
await s.shot('06-p4-chat');
await s.step('Commerce MCP のツールで注文が作成されました。図では Commerce MCP のノードが強調表示されます', 4500);
await s.step('1 つの会話の中で、Broker が専門のエージェントと MCP サーバーを使い分けていることがわかります', 4000);

// 任意: Broker の構成方法 (ガイドのページ)
await s.step('任意: Broker がどのように構成されているかを、ワークショップのガイドで確認します', 600);
await s.tab('guide');
await page.goto('https://actionability.workshops.mulesoft.com/action/orchestration.html', { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(4000);
const ok = page.locator('#onetrust-accept-btn-handler'); if (await ok.isVisible().catch(() => false)) { await ok.click({ force: true }); await page.waitForTimeout(800); }
const h = (t) => page.locator('h2, h3').filter({ hasText: t }).first();
const sum = (t) => page.locator('summary').filter({ hasText: t }).first();
await s.scrollTo(h('Optional: How the Broker Is Built'), 'start');
await s.step('Broker は、利用者のリクエストを受け、使うエージェントとツールを判断し、応答をまとめる役割を担います', 4000);
await s.step('Vogue Premiere の Broker は、Anypoint Code Builder で、Create、Configure、Publish、Deploy の 4 つの段階で作成されています', 4500);
await s.scrollTo(h('1. Create'), 'start');
await s.step('1. Create: Agent Network のプロジェクトを作成すると、agent-network.yaml、exchange.json、.agent のひな形ができます', 600);
await s.click(sum('Creating an agent network project')); await page.waitForTimeout(1500); await s.scrollTo(sum('Creating an agent network project'), 'start'); await page.waitForTimeout(3000);
await s.scrollTo(h('2. Configure'), 'start');
await s.step('2. Configure: agent-network.yaml に Broker の名前と連携させる相手を、.agent に振り分けのルールと推論の指示を記述します', 600);
await s.click(sum('Configuring the broker')); await page.waitForTimeout(1500); await s.scrollTo(sum('Configuring the broker'), 'start'); await page.waitForTimeout(3500);
await s.scrollTo(h('3. Publish'), 'start');
await s.step('3. Publish: Broker と、参照するエージェントと MCP サーバーを、Exchange の資産として公開します', 4000);
await s.scrollTo(h('4. Deploy'), 'start');
await s.step('4. Deploy: 環境、ゲートウェイ、エージェントの URL や API キーなどの変数を指定してデプロイします。Lab 2-3 の Broker もこの手順で作成されています', 5500);
await s.scrollTo(h('Conclusion'), 'start');
await s.step('ご自身で作成する場合は、Agent Fabric のドキュメントを参照してください', 3000);
return 'ok';
