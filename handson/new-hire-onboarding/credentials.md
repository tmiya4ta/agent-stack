# クレデンシャルの一覧

ここには名前と使い道だけを書く。値は `credentials.local.md` (git に入らない) に、同じ見出しで書く。
参加者のパスワードは `setup/anypoint_setup.py users` が `credentials.local.json` (git に入らない) に書き出す。

## 主催者が持つもの (参加者には配らない)

| 名前 | 使い道 |
|---|---|
| Anypoint の管理者 | BG、vCore、Gateway、チーム、ユーザー、APPBG への配備 |
| 事前テスト用のリモートデスクトップ | Guacamole の URL とログイン。VS Code での予行に使う |
| LLM の行き先 | LLM Proxy の Target URL と鍵。APPBG の A2A の 2 つの `llm.proxy.host` と `llm.apiKey` にも使う (直接向ける) |
| メンバーのアプリの URL | APPBG に配備した 3 つの public endpoint。broker の `exchange.json` に入れる |

## 参加者が主催者から受け取るもの

| 名前 | 中身 |
|---|---|
| Anypoint のログイン | ユーザー名 (`wsXX_<日付>`) とパスワード。BG1 / Sandbox |
| suffix | `wsXX` |
| メンバーのアプリの URL | 上と同じ 3 つ |
| LLM Proxy | URL (認証なし) |
