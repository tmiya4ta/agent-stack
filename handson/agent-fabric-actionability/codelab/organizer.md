---
id: agent-fabric-actionability-organizer
summary: Agent Fabric Actionability ワークショップの主催者向けの資料です。事前の準備、参加者とやり取りする情報、当日の進行上の注意をまとめています
categories: MuleSoft
environments: Web
status: Draft
feedback_link:
authors:
---

# Agent Fabric Actionability ワークショップ 主催者向け資料

## この資料について
Duration: 2:00

参加者には手順書 `actionability.docx` (Web 版: https://actionability-codelab-23fgzd.pnwfdv.jpn-e1.cloudhub.io/) をお渡しします。手順書には参加者の操作だけを記載しているため、事前の準備、参加者とやり取りする情報、当日の進行上の注意は本資料にまとめています。

所要時間は約 3 時間です。参加者側の事前のインストールや登録は不要です。

## 事前に用意するもの
Duration: 5:00

| 用意するもの | 内容 | ラボ |
|---|---|---|
| Anypoint の組織 | ワークショップのビジネスグループ (2026-11-20 の環境では `Actionability Workshop A`) と、参加者ごとの子ビジネスグループ (名前はユーザー名)。Enhanced UI、Agent Fabric、Agent Scanner、MCP Bridge、Model Proxy、Model Wallet、Cost Management が使えること | すべて |
| 参加者のユーザー | 1 人 1 つ。ご自身のビジネスグループとワークショップのビジネスグループの両方に権限を付けます | すべて |
| Omni Gateway | `attendee-gateway` (Sandbox)。MCP サーバーと Model Proxy のデプロイ先 | 2-1、4-1 |
| Customer / Order REST API | Exchange の資産と実装。初期データは Alex、Ashley、Jamie と、注文 ORD-2026-00001〜00003 | 2-1、3-1 |
| Vogue Premiere の Broker | Styling / Availability / Loyalty の各エージェントと Commerce MCP (Credential Injection OAuth2 OBO を設定済み) | 2-3、3-1、3-2 |
| ID プロバイダー (Keycloak) | ペルソナ (Alex Chen、Ashley Grover、Jamie Torres、Emily、Thomas など) と、OBO 用のクライアント `commerce-mcp-obo` | 2-3、3-1、4-2 |
| Workshop UI | MCP Client、Multi-Agent Orchestrator、Semantic Routing、Model Wallet のタブ | 2-1 以降 |
| Amazon Bedrock | 検出対象のエージェント 1 つと、参加者に配る読み取り専用の IAM のキー | 1-1 |
| 埋め込みの接続 | Semantic service (2026-11-20 の環境では `semantic-service`。Basic scale) | 4-1 |
| LLM の接続先 | Model Proxy から呼ぶ OpenAI / Azure OpenAI の URL と API Key | 4-1 |
| Model Wallet (任意) | `finance` と `engineering` の Wallet (Emily と Thomas のプリセット用) | 4-2 |
| Agentforce | Lab 4-3 の **Optimize All** に必要です | 4-3 |
| Anypoint Titanium (任意) | Lab 3-2 の Distributed Traces と Log Search に使います | 3-2 |

詳細は `hosting.md` を参照してください。

## 参加者とやり取りする情報
Duration: 5:00

### 事前に参加者にお知らせいただく情報

環境の準備や進め方の調整のため、ワークショップの前に次の点をお知らせいただきます。

| 区分 | 内容 |
|---|---|
| 参加者 | お名前とメールアドレス、ハンズオンに参加する人数 (見学のみの方を除く)、役割 (開発者、アーキテクト、プラットフォームエンジニアなど) |
| MuleSoft のご利用状況 | ご利用の有無 (利用中 / 未利用 / 評価中)、利用中の Anypoint の製品、Agent Fabric をどの程度ご存じか |
| AI エージェントの状況 | 利用状況 (本番 / 試行 / 評価中 / 未着手)、利用中の基盤 (Amazon Bedrock、Google Vertex、Azure AI、OpenAI、Copilot Studio、LangChain など) |
| 目的 | 参加の目的、検討中のユースケース、特に関心のある機能、ワークショップに期待する成果 |

### 当日に参加者にお渡しする情報

| 名前 | 内容 | ラボ |
|---|---|---|
| Anypoint のサインイン | ユーザー名とパスワード | すべて |
| Workshop UI | URL と、サインイン用のユーザー名とパスワード | 2-1 以降 |
| AWS (Bedrock) | Access Key ID と Secret Access Key (リージョン us-east-1) | 1-1 |
| LLM の接続先 | Destination URL と API Key | 4-1 |

お渡しする際に、値はメモ帳などに控え、ほかの方に見せたりチャットに貼り付けたりしないようお伝えください。

## 当日の進行上の注意
Duration: 10:00

### 全体

* 参加者は全員が同じゲートウェイと環境を使います。`{名前}` が重なると保存できないため、名字などの重ならない名前を使うよう案内します。
* Workshop UI のページを再読み込みすると Anypoint との接続が切れます。その場合は **Connect Anypoint** から接続し直します。

### Module 1

* Agent Scanner のスキャンは通常 1 分ほどですが、参加者が多いと時間がかかります。**Scan History** に結果が出ない場合は再読み込みを案内します。
* ガイドにある Action groups と Knowledge bases は、検出対象のエージェントに設定していないため表示されません。

### Module 2

* Lab 2-1 以降はワークショップのビジネスグループで操作します。ご自身のビジネスグループのままだと **No Omni Gateways Available** と表示されます。
* MCP サーバーの Gateway に **agent-network-gw** (共有の Broker 用) を選ぶと、ワークショップ全体の Broker に影響します。必ず **attendee-gateway** を選ぶよう案内します。
* Review の画面の **MCP Response Sanitization** は、作成後のインスタンスでは **MCP Payload Optimization** という名前で表示されます。
* ツール 2 (顧客の作成) の username を空欄にすると顧客が作成されず、ツール 4 で Alex Chen (`CUST-100001`) の会員ランクを書き換えてしまいます。Alex Chen は Lab 2-3 で全員が使うため、username の入力と customerId の確認を強調します。
* Lab 2-2 のポリシーの並べ替えの画面には、Inbound のポリシー 5 つだけが表示されます (ガイドの表にある Outbound の MCP Transcoding 2 つは表示されません)。
* Lab 2-3 で URL を **→** で確定しないままメッセージを送ると **Broker call failed: fetch failed** と表示されます。確定しても解決しない場合は Broker の URL を案内します。
* Workshop UI のセッションの最初のプロンプトは、Broker がツールを使わない一般的な回答 (「No external tools were required…」) を返し、Reasoning Map に経路が出ないことがあります (2026-11-21 の撮影で毎回起きた)。2 回目からは正しく動くので、同じプロンプトをもう一度送るよう案内します。
* Broker が確認の質問を返すことがあります。同じプロンプトをもう一度送信するよう案内します。

### Module 3

* Commerce MCP Server のポリシーは全員で共有しています。確認だけにとどめ、保存しないよう案内します。
* Identity タブで Exchanged token が **Not available yet** と表示された場合は、**Reasoning Map** などに切り替えてから戻ると表示されます。
* Agent Visualizer の既定のフィルターは最上位のビジネスグループと Production のため、最初は何も表示されません。
* Titanium が有効でない組織では、Distributed Traces と Log Search は使えません。手順書では「お使いの場合は」として紹介にとどめています。

### Module 4

* 元のガイドでは Finance のルートは Gemini 2.5 Flash ですが、提供する LLM の接続先が Azure OpenAI のみの場合は Azure OpenAI の GPT-4o Mini にします。同じ Provider のルートを 2 つ設定すると **routes must be uniquely matchable** になるため、Coding は OpenAI、Finance は Azure OpenAI と Provider を分けています。
* Semantic service が Basic scale の場合、トピックごとの発話例は 10 個までです。手順書の発話例は Workshop UI の用意されたプロンプトを中心に選んでいます。
* OpenAI の Provider は Destination URL に `chat/completions` を付けて呼び出すため、`…/openai/v1/` まで入力しないと 404 になります。
* Fallback の既定のモデル GPT 5.2 は、提供する LLM の接続先では使えないため GPT 5 Mini にしています。
* Provider を変更すると、そのルートのモデル、API キー、トピックが消えます。
* 作成後に **Edit Configuration** でトピックの発話例だけを変えると **Save Changes** を押せないことがあります。ほかの項目も一緒に変えると保存できます。
* Model Proxy の **Monitoring**、Cost Management の使用量、Lab 4-3 の **Tokens saved** は、反映まで数十分から翌日までかかることがあります。表示されない場合は、後のラボのあとで確認するよう案内します。Cost Management で **Budget usage is currently unavailable** と表示されても、予算による 429 のブロックは動作します。
* Lab 4-2 の予算は呼び出しの前に判定するため、最後の 1 回で上限を大きく超えることがあります (予行では 281%)。**(verbose)** のプロンプトは **ERROR** (SyntaxError: Unexpected token '<') になりやすいため (2026-11-21 の撮影では毎回)、手順書では案内していません。短いプロンプトを 5 回ほど送れば上限に達します。
* Lab 4-2 でポリシーを変更すると、Semantic Routing タブ (client_id と client_secret で呼び出す) からはその Proxy を呼び出せなくなります (**JWT Token is required.**)。
* Emily と Thomas の Wallet は、主催者が用意している場合に計測されます。
* Lab 4-3 の **Optimize All** は Agentforce が有効でないと動作しません (**Agentforce is not fully enabled**)。その場合は **Current Description** を手動で短くするよう案内します (例 `get_customers_customerId` は `Get customer by ID`、`createOrder` は `Create an order`)。2026-11-20 の環境では動作しました (102 トークン → 78 トークン)。
* Progressive Disclosure を Global Access Control より後ろに置くと、Global Access Control には `invoke_tool` しか見えず、ブロックしたツールを `invoke_tool` 経由で呼び出せてしまいます。必ず MCP Support の直後に置くよう案内します。
* `search_tools` で `customers` を検索した結果は、予行では 4 件、ガイドでは 5 件でした。
* MCP Bridge が作るツールの名前は環境によって変わります。2026-11-20 の環境では `get_customers`、`createOrder` のように API 名の接頭辞が付きません (以前は `order-rest-api_createOrder`)。Lab 2-2 の Value は、Workshop UI に表示される名前をそのまま入れます。

### よくある症状と対処

| 症状 | 対処 |
|---|---|
| MCP サーバーの保存時にパスの重複エラーになる | `{名前}` を重ならないものに変更します |
| Asset not found や Permission denied になる | ビジネスグループがワークショップのものか確認します |
| 顧客の作成で重複エラーになる | username を変更します |
| 注文の作成で `{}` や required key not found が返る | 6 つの項目を消していないか確認します |
| Connect のあとツールが 0 個になる | SERVER URL の末尾に `/mcp/` を付けます |
| Global Access Control が効かず、呼び出すと `{}` が返る | ポリシーの順番を確認し、MCP Support の直後にします |
| Global Access Control がまったく効かない | Value がツール名と一致しているか、Match Type が literal か確認します |
| ツールの一覧が変わらない | Workshop UI で Disconnect → Connect します |
| GOVERNANCE LOG で **— (none engaged)** になる | 入力したユーザー名と Wallet の Claim values が一致しているか確認します |

## 後片付け
Duration: 3:00

* 参加者が作成したもの (Scanner、MCP サーバー、アプリケーション、Model Proxy、Model Wallet) は、手順書の「後片付け」で参加者に削除していただくか、主催者がまとめて削除します。Model Proxy は、アプリケーションとの契約が残っていると削除できません。
* Lab 2-1 で参加者が作成した顧客と注文は、主催者がまとめて削除します。
* Alex Chen などのペルソナのデータが書き換えられていないか、次回の前に確認します。
