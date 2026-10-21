# 06 Agent Visualizer: ネットワークの地図

元のページ: [Agent Visualizer](https://develop-actionability.workshops.mulesoft.com/govern/agent-visualizer.html) (モジュール 3)

## 目的

エージェント、MCP サーバ、broker、LLM のつながりを 1 枚の図で見る。Titanium が有効なら、1 件の要求の通り道 (トレース) と、
全部の部品のログもまとめて見る。

## 手順

1. Visualizer を開く。ノード (エージェントと MCP)、辺 (宣言したつながりと、実際の呼び出し)、詳細のカードが出る。
2. **Availability Agent** のノードを選び、詳細 (資産の情報、メトリクス、ログとトレース) を見る。
3. Exchange に載せた外のエージェントと MCP (ラボ 01 の Bedrock のものなど) も並んで出ることを確かめる。
4. 虫めがねで、名前、種類、プラットフォーム、タグで探す。
5. フィルタで BG、環境、期間を絞る。

## 任意: Titanium (主催者が有効にしたときだけ)

**Runtimes → Monitoring** の中にある。

- **Traces**: 環境を確かめ、期間を 1 hour にして、**Vogue Premiere Agent Broker** を開く。broker の推論、エージェントの呼び出し、
  MCP のツールの呼び出しが、それぞれの時間付きで並ぶ (OpenTelemetry)。
- **Log Search**: 期間を 1 hour にして、broker、MCP、エージェントのログをまとめて探す。broker のログには
  `LLM selected tool`、`Tool Input`、`Executed tool` / `Output was` が出る。

## 実施メモ

- Titanium は使えたか:
- 気づいたこと:
