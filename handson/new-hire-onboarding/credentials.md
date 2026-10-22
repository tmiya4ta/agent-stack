# クレデンシャルの一覧

ここには名前と使い道だけを書く。値は環境ごとに `~/.config/handson/new-hire-onboarding/<環境名>/env.json` (git の外) に書き、
`python ../env_page.py` で HTML にする ([hosting.md](hosting.md) の「環境のメモ」)。
参加者のパスワードは `setup/anypoint_setup.py users` が環境のフォルダの `users.json` に書き出す。

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
| Exchange のページ | BG1 の `new-hire-onboarding-handson`。メンバーの 3 つの URL、LLM (Model Proxy) の URL (認証なし)、`openAI.*` の値 (`none`)、コピペする 3 つのファイル |
