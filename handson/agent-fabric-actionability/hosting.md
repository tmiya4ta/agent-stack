# 自分で開くときに用意するもの

元の手順書から読み取れる、主催者が先に用意しておくもの。元の環境の作り方 (broker のソースなど) は公開されていないので、
ここにあるのは「参加者の画面から見える形」に合わせた必要なものの一覧。作ったものはこの表の「agent-stack での当て」の欄に書いていく。

## 全体

```
参加者のブラウザ
  ├─ Anypoint (omni.mulesoft.com)    親の workshop BG / 参加者ごとの子 BG、Sandbox、Omni Gateway attendee-gateway
  └─ Workshop UI                      MCP | Multi-Agent Orchestrator | Semantic Routing | Model Wallet のタブ
        │ ペルソナでログイン (Keycloak)
        ▼
  Vogue Premiere broker (Agent Network)
        ├─ A2A: Styling Agent、Availability Agent、Loyalty Agent
        └─ MCP: Commerce MCP (Customer + Order。outbound に OBO) ── Customer REST API / Order REST API
  Amazon Bedrock: Loyalty Agent (Agent Scanner で取り込む相手)
  Model Proxy の行き先: OpenAI (GPT-5 Mini)、Gemini (2.5 Flash)、意味検索のサービス
```

## 一覧

| 部品 | 要る形 (手順書から) | 使うラボ | agent-stack での当て | 状態 |
|---|---|---|---|---|
| Anypoint の org | 親の workshop BG (BG の一覧の 2 番目) と、参加者ごとの子 BG (名前はユーザー名)。Enhanced UI、Agent Fabric、Agent Scanner、MCP Bridge、Model Proxy、Model Wallet、Cost management が使えること | すべて | — | 未 |
| 参加者のユーザー | 1 人 1 つ。子 BG と親の BG の両方に権限 | すべて | `anypoint-user-admin` のスキル (CSV で一括作成) | 未 |
| Omni Gateway | `attendee-gateway` (Sandbox、親の BG)。MCP Bridge と Model Proxy の配備先 | 02、07 | — | 未 |
| Customer REST API | Exchange の資産と実装。`GET/POST /customers`、`GET/PUT /customers/{customerId}`。初期データは Alex、Ashley、Jamie (CUST-100001 ..)。username は一意。ID は `CUST-…` を自動で振る | 02 | Mule で作る (未) | 未 |
| Order REST API | Exchange の資産と実装。`createOrder` (customerId、cartId、paymentMethodId、customerName、status、customerAddress が必須)、`getShippingStatus`。注文 ORD-2026-00001〜00003 (00002 は Ashley、00003 は Jamie)。ID は `ORD-…` | 02、05 | Mule で作る (未) | 未 |
| Commerce MCP (主催者の分) | broker が呼ぶもの。Customer と Order のツール、`get_customer_profile`。outbound に Credential Injection OAuth2 OBO (RFC 8693、audience `commerce-mcp-obo`、scope `openid`、token endpoint は Keycloak)。検索はトークンの `sub` で絞る | 04、05 | — | 未 |
| A2A のエージェント 3 つ | Styling (服の提案)、Availability (サイズの在庫)、Loyalty (会員の特典) | 04 | Mule の A2A (`demos/` の作りと同じ) | 未 |
| Vogue Premiere broker | Agent Network。受け取る → 顧客の取得 → 意図の分類 → 振り分け、の後に意図ごとの枝 (styling、availability、loyalty、order)。broker の LLM は OpenAI | 04、05、06 | `agent-network.yaml` + `.agent` (`handson/new-hire-onboarding` と同じ形) | 未 |
| Keycloak | ペルソナ (Alex Chen、Ashley Grover、Jamie Torres、Attendee、Emily、Thomas、Alex (Marketing))、クライアント `vogue-ui` (UI) と `commerce-mcp-obo` (機密。token exchange を許す)。コストのラボのペルソナには `cost_center` の claim | 04、05、08 | — | 未 |
| Workshop UI | Anypoint に「Connect」して BG と環境を選ぶ。MCP のテスト (ツールの一覧、フォーム、生の応答)、broker のチャット (ネットワーク図、Reasoning Map、Trace、Identity)、Semantic Routing のテスト、Model Wallet のポリシーの一括設定 (Configure policies、Equalize priorities) | 02〜05、07、08 | — (一番大きい。作るかどうかから決める) | 未 |
| Amazon Bedrock | エージェント 1 つ (Vogue Premiere Loyalty Agent の人格、Claude 3.5 Haiku の推論プロファイル、action group と knowledge base は無し)。参加者に配る IAM のキー (読み取りだけ) | 01 | — | 未 |
| LLM の行き先 | Model Proxy から呼ぶ OpenAI 互換と Gemini の URL と鍵。意味検索のサービス (`<semantic-service>`、埋め込みの鍵は要らない) | 07、08 | `ai/model/emu` の `llm.openai.emu`、`llm.gemini.emu`、`embed-emu` が使えるかもしれない (本物のモデル名 GPT-5 Mini / Gemini 2.5 Flash で選ぶので要確認) | 未 |
| 主催者の Model Wallet | `finance-team` (claim finance) と `engineering-team` (claim engineering、Gemini は 1 日 2,000 トークン) | 08 | — | 未 |
| Titanium | 任意。Distributed Traces と Log Search | 06 | — | 未 |

## 手順書の中の食い違い (開くときに直す)

- MCP Bridge で作るサーバの名前が、ラボ 02 では `commerce-mcp-<名前>`、ラボ 09 では `commerce-mcp-bridge-<イニシャル>`。
- ツールの名前が、ラボ 02・03 では `customer-rest-api_get_customers_customerId` や `order-rest-api_createOrder`、ラボ 09 では
  `get_customers_customerid` や `post_orders`。ツール名は Bridge の設定で決まるので、実際の名前に合わせる。
- 各ページの見出しの番号 (MCP Bridge が「Lab 2」、Global Access Control が「Lab 1」) が、モジュールの並びと合っていない。
