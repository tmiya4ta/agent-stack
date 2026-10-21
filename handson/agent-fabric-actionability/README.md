# Agent Fabric Actionability Workshop

MuleSoft の [Agent Fabric Actionability Workshop](https://develop-actionability.workshops.mulesoft.com/index.html) (develop 版、英語) を
実施した記録と、自分で開くための準備をまとめる。元の手順書のソースは GitHub の
`MuleSoft-SE-Community-emu/actionability-workshop-documentation` (develop ブランチ、非公開)。日本語版 (`/jp`) は公開されていない (2026-10-21)。

## 筋書き

架空のアパレル会社 Vogue Studios が、[Composability Workshop](https://composable-enterprise.workshops.mulesoft.com/index.html) で作った
注文と顧客の API を元に、AI のスタイル相談アプリ **Vogue Premiere** を組み立てる。API には手を入れず、Agent Fabric で
エージェントから使えるようにし、統制し、つなぎ、見えるようにし、費用を抑える。

## ラボ

| # | モジュール | ラボ | 参加者がやること | 手順 |
|---|---|---|---|---|
| 0 | — | 準備 | Anypoint と Workshop UI に入る | [00-prep](tutorial/00-prep.md) |
| 1 | 1. 可視化 | Agent Scanner | Amazon Bedrock のエージェントを Exchange に取り込む | [01](tutorial/01-agent-scanner.md) |
| 2 | 2. AI に行動させる | MCP Bridge | Customer API と Order API を 1 つの Commerce MCP にする | [02](tutorial/02-mcp-bridge.md) |
| 3 | | MCP Global Access Control | 注文のツールをゲートウェイで隠す | [03](tutorial/03-mcp-global-access-control.md) |
| 4 | | Orchestration | 配備済みの broker を UI から使い、経路を見る | [04](tutorial/04-orchestration.md) |
| 5 | 3. 本番に向けた統制 | Trusted Agent Identity | OBO のトークン交換と、他人の注文が見えないことを確かめる | [05](tutorial/05-trusted-agent-identity.md) |
| 6 | | Agent Visualizer | ネットワークの地図 (Titanium があればトレースとログ) | [06](tutorial/06-agent-visualizer.md) |
| 7 | 4. 費用 | Semantic Routing | 問いの意味で行き先のモデルを変える Model Proxy | [07](tutorial/07-semantic-routing.md) |
| 8 | | Model Wallet | JWT の claim ごとの予算 (200 / 401 / 429) | [08](tutorial/08-model-wallet.md) |
| 9 | | MCP Cost Optimization | Tool Mapping と Progressive Disclosure | [09](tutorial/09-mcp-cost-optimization.md) |

参加者が自分で作るのは Scanner、MCP Bridge、ポリシー、Model Proxy、Wallet だけで、broker、エージェント、IdP、Workshop UI は
主催者が先に用意しておく ([hosting.md](hosting.md))。

## クレデンシャル

何が要るかは [credentials.md](credentials.md)。値は同じフォルダの `credentials.local.md` に書く (`.gitignore` で除外。git に入れない)。

## 状態

| | 状態 |
|---|---|
| 手順のまとめ (tutorial/) | 元のページから作った (2026-10-21)。実施メモは未記入 |
| 主催者の準備 (hosting.md) | 必要なものを洗い出しただけ。まだ何も作っていない |
