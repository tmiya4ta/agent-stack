# クレデンシャルの一覧

ここには名前と使い道だけを書く。値は `credentials.local.md` (git に入らない) に、同じ見出しで書く。

## 参加者が主催者から受け取るもの

| 名前 | 中身 | 使うラボ |
|---|---|---|
| Anypoint のログイン | ユーザー名とパスワード。参加者ごとの子の BG (ユーザー名と同じ名前) が付く | すべて |
| Workshop UI | URL と、UI のログイン (ユーザー名とパスワード) | 02〜05、07、08 |
| AWS (Bedrock) | Access Key ID と Secret Access Key。リージョンは us-east-1 | 01 |
| OpenAI の行き先 | Destination URL (末尾の `/` が要る) と API Key | 07 |
| Gemini の行き先 | Destination URL (末尾の `/` が要る) と API Key | 07 |

## 参加者がラボの中で作るもの

| 名前 | 中身 | 作るラボ | 使うラボ |
|---|---|---|---|
| Model Proxy の client | Exchange の Request access で出る client_id と client_secret (アプリ名 `<名前> Application`) | 07 | 07 |
| Model Wallet の id | 自分の wallet (`<名前>-wallet`) のページの Client ID | 08 | 08 |

## ペルソナ (Workshop UI のログイン。IdP は Keycloak)

UI の中でペルソナを選んで入る。パスワードを手で入れるかどうかは未確認。

| ペルソナ | 使うラボ | 何を見るか |
|---|---|---|
| Alex Chen | 04 | 既定のペルソナ。スタイル相談から注文まで |
| Ashley Grover | 04、05 | ORD-2026-00002 の持ち主 |
| Jamie Torres | 05 | 自分の ORD-2026-00003 は見え、ORD-2026-00002 は見えない |
| Attendee | 08 | `cost_center=attendee`。自分の wallet に付く |
| Emily (Finance) | 08 | `cost_center=finance` → wallet `finance-team` |
| Thomas (Engineering) | 08 | `cost_center=engineering` → wallet `engineering-team` (Gemini は 1 日 2,000 トークン) |
| Alex (Marketing) | 08 | `cost_center=marketing`。合う wallet が無く 401 |

## 主催者が持つもの (参加者には配らない)

自分で開くときに要る。詳しくは [hosting.md](hosting.md)。

| 名前 | 使い道 |
|---|---|
| Anypoint の org の管理者 | BG、ユーザー、Gateway、配備 |
| broker の LLM の鍵 (OpenAI) | Vogue Premiere broker の配備の変数 |
| Keycloak の管理者 | レルム、ペルソナ、クライアント |
| OBO のクライアント `commerce-mcp-obo` | Client ID と Client Secret。Commerce MCP の OBO ポリシーに入れる |
| AWS のアカウント | Bedrock のエージェントと、参加者に配る IAM のキー |
