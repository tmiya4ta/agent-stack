# 01 Agent Scanner: 外のエージェントを Exchange に取り込む

元のページ: [Lab 1: Agent Scanner](https://develop-actionability.workshops.mulesoft.com/register/agent-scanner.html) (モジュール 1)

## 目的

Amazon Bedrock で動いているエージェントを Agent Scanner で見つけ、Exchange の資産にする。自分で作っていないエージェントの
モデル、指示 (プロンプト)、つなぎ方が Anypoint の中で読めるようになる。

## 手順

1. 左下の BG の切り替えで、**自分の子 BG** を選ぶ。
2. 左のメニューの **Agents** → **Add Agent** → **Connect to Provider** → **Amazon** → Continue。
3. 接続を入れて **Test Connection** (緑で Connection successful になる) → Continue。
   - Platform: Amazon Bedrock
   - AWS Access Key ID / Secret Access Key: 主催者のもの
   - Region: US East (N. Virginia) us-east-1
4. Scanner を設定して **Connect**: 名前 `<名前> Scanner`、説明は空、頻度 every 24 hours、時刻は既定。
5. **Providers** → 自分の Scanner → **Run Discovery Scan**。
6. 終わったら (1 分ほど。画面の更新が要ることがある) スキャンの詳細を開き、**Services Added** の追加されたエージェント
   (例 `agent-quick-start-jqsb7`) を開く。

## 確かめること

エージェントのページの上から順に:

| 節 | 中身 |
|---|---|
| Documentation | 作成・更新の日時、版、AWS のアカウント ID、Provider URL |
| Agent card | Agent ID、URL とリージョン、プロトコルと版、機能 (ストリーミングあり、プッシュ通知なし) |
| Agent configuration | 基盤モデル (Claude 3.5 Haiku の推論プロファイル)、状態、エイリアス、ARN。Bedrock 固有の項目 |
| Action groups / Knowledge bases | どちらも無し |
| System instructions | エージェントのプロンプトそのもの (Vogue Premiere の Loyalty Agent) |

Scanner は提供元ごとのメタデータを読んで、合う項目を自動で出す (設定は要らない)。

## 実施メモ

- 取り込まれたエージェントの名前:
- 気づいたこと:
