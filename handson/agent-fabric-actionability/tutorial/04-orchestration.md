# 04 Orchestration: broker を使って経路を見る

元のページ: [Orchestration](https://develop-actionability.workshops.mulesoft.com/action/orchestration.html) (モジュール 2)

## 目的

配備済みの Vogue Premiere Styling Concierge (broker) を Workshop UI から使い、1 つの問いが複数のエージェントと MCP を
どう通るかを見る。broker は作らない (作り方は最後に読むだけ)。

## 手順

1. Workshop UI に入り、**Connect** で Anypoint につなぎ、workshop BG と sandbox を選ぶ。
2. 上の **Multi-Agent Orchestrator** タブ → Agent Broker URL の欄で broker を選び **Use this proxy**。
3. ペルソナで入る (まず **Alex Chen**)。IdP への本当のログインで、そのトークンが毎回 broker に届く。
4. 画面の見方: ネットワーク図 (使われたノードが光る)、おすすめの問い、チャット、Orchestration の欄 (Reasoning Map、Trace、Identity)。
5. おすすめの問いを上から順に押す (答えが返ってから次へ)。自己紹介は要らない (ログインで broker が誰かを知っている)。

| ペルソナ | 問い | 使われるもの |
|---|---|---|
| Alex Chen | I have a dinner in Napa next Saturday. What should I wear? | Styling Agent、Commerce MCP (顧客の情報) |
| | Can you check if all 4 products are available in my size? | Availability Agent |
| | Show me my loyalty perks | Loyalty Agent |
| | Place the order for the whole outfit. | Commerce MCP (注文) |
| Ashley Grover | I'm going to a weekend brunch. Can you recommend an outfit? | Styling Agent |
| | Can you check if all 4 products are available in my size? | Availability Agent |
| | Great, please place the order for all four items. | Commerce MCP |

## 確かめること

- **Reasoning Map**: 共通の幹 (受け取る → 顧客の情報 → 意図の分類 → 振り分け) の後に、意図に合う枝が 1 本だけ走る。
  ノードの印は STEP (AI なし)、LLM、A2A、MCP。History で前の問いに戻れる。
- **Trace**: broker が出した生の記録。Intent、Identity、通ったノード (LLM の印付き)、呼んだ接続、broker との生の要求と応答 (A2A)。

## つまずき

- broker が確認の質問を返してくる: よくある。同じ問いを送り直す。

## 読むだけ: broker の作り方 (Anypoint Code Builder)

1. Create: **MuleSoft: Create an Agent Network Project**。`agent-network.yaml`、`exchange.json`、`brokers/<名前>.agent` ができる。
2. Configure: `agent-network.yaml` に broker と、つなぐエージェント・MCP。`.agent` に振り分けと指示。
3. Publish: **MuleSoft: Publish Agent Network Assets**。broker と参照先が Exchange の資産になる。
4. Deploy: **MuleSoft: Deploy Agent Network**。環境、ingress / egress の gateway、`exchange.json` の変数 (URL と OpenAI の鍵) を入れる。

agent-stack の [new-hire-onboarding](../../new-hire-onboarding/) も同じ形 (yc で配備する)。

## 実施メモ

- broker の名前:
- 気づいたこと:
