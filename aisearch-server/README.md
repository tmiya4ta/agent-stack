# aisearch-server

Azure AI Search の REST API（のうちベクトル検索まわり）を真似るエミュレーター。
MuleSoft の Semantic Cache Config で Vector database provider に「Azure AI Search」を選んだときの
接続先にする想定。clay で書き、このマシンで動かす（embeddings-server と同じ置き方）。

```
クライアント ─ https://aisearch.theorems.io ─ theorems-edge (Caddy, TLS 終端)
                                                  ▼
                 (api-key)→ 172.23.0.1:8897  aisearch-server（clay の HTTP サーバ、systemd --user）
                                              │ 状態 = 1 つの atom（インデックスと文書）
                                              └ 状態を変えた要求を ~/.local/share/aisearch-server/log/<連番>.json に書き、起動時に再生
```

- `https://aisearch.theorems.io` で公開（2026-09-22）。サーバ自体は 172.23.0.1（kind bridge）にだけ bind
- LAN 内からは `aisearch.theorems.io` を直接開けない（ヘアピン NAT が効かない）。`--resolve aisearch.theorems.io:443:192.168.11.6`
  を付けるか、このマシンから `http://172.23.0.1:8897` を叩く
- clay 0.42.0 以降が要る（`http/header` とスレッド安全な atom は 0.41.0、chunked の要求本文は 0.42.0。
  ゲートウェイ越しの要求は chunked で届く）。インストール済みの `clay` だけでビルドできる（`build.sh`）

## 使い方

```bash
KEY=$(grep ^AIS_API_KEYS= ~/.config/aisearch-server/env | cut -d= -f2)
curl -s "https://aisearch.theorems.io/indexes?api-version=2024-07-01" -H "api-key: $KEY"
```

Anypoint の Semantic Cache Config なら、Vector database provider は Azure AI Search、
Host は `https://aisearch.theorems.io`（リレーの URL は不可。下の「実際に来たもの」参照）、
API Key は上の `$KEY`、Index name は `semantic-cache`（既定のまま）。
Embedding の手順は embeddings-server（`https://embeddings.theorems.io/v1/embeddings`、`text-embedding-ada-002`）。

## 想定している使われ方

Semantic Cache は文字列のベクトル化を自分で行い（Config の Embedding 手順。embeddings-server を向ける）、
このエミュにはベクトルそのものを渡すはず。つまりエミュ側に埋め込みモデルは要らない。

```
POST /indexes/semantic-cache/docs/search   {"vectorQueries":[{"kind":"vector","vector":[...],"fields":"..","k":1}]}
POST /indexes/semantic-cache/docs/index    {"value":[{"@search.action":"upload","id":"..", "<ベクトル欄>":[...], ...}]}
GET/PUT /indexes/semantic-cache            インデックスの確認・作成
```

実際に来たもの（2026-09-22、Flex Gateway 1.13.4 の semantic-caching-policy-openai-azure-ai-search 1.0.4、api-version 2025-09-01）:

- インデックスは自動では作られない。Anypoint が Config 保存時に出す `vectordb-semantic-cache-setup-*.sh setup` で作る
  （欄: id, proxyId, text, topic, provider, model, userId, clientId, expiresAt(Int64), createdAt, hitCount, input_format, contentVector）
- 検索: `vectorQueries: [{kind: vector, fields: contentVector, k: 5}]` + `select` + `filter: input_format eq 'openai'`
- 登録: `docs/index` に `{@search.action, id, contentVector, text, expiresAt, input_format}`（応答本文は Object Store 側）
- **ポリシーは設定した URL のパスを捨てる**ので、Config の Host はパス無しの `https://aisearch.theorems.io` にする
  （リレー `…/aisearch` だと `/indexes/..` がリレー直下に来て別サブドメイン扱いになる）
- 要求本文は chunked で届く（clay 0.42.0 から受けられる）

## エンドポイント

| メソッド | パス | 内容 |
|---|---|---|
| GET | `/servicestats` | 件数・容量 |
| GET / POST | `/indexes` | 一覧（`$select=name` 可）/ 作成（既にあれば 409） |
| GET / PUT / DELETE | `/indexes/{n}` | 定義 / 作成（201）・更新（200）/ 削除（204） |
| GET | `/indexes/{n}/stats` | documentCount・storageSize・vectorIndexSize |
| POST | `/indexes/{n}/docs/index` | upload / merge / mergeOrUpload / delete のバッチ（一部失敗は 207） |
| POST | `/indexes/{n}/docs/search` | 検索（下記） |
| GET | `/indexes/{n}/docs` | 検索（`search` `$filter` `$select` `$top` `$skip` `$count`） |
| GET | `/indexes/{n}/docs/$count` | 件数（text/plain） |
| GET | `/indexes/{n}/docs/{key}` | 1 件（`$select` 可） |

- `/indexes('n')`・`/docs('key')` の OData 形式のパス、`docs/search.index`・`docs/search.post.search` の別名も受ける
- `api-version` は受け取るが見ない（どの版でも同じ形で答える）
- エラーは Azure と同じ `{"error":{"code":"..","message":".."}}`

## 検索の中身

- `$filter`: `eq ne gt ge lt le`、`and or not`、括弧、`search.in(field, 'a,b'[, '区切り'])`、真偽値の欄、
  `a/b` のパス、`'..'`（`''` はエスケープ）・数・`true/false/null`・日時（文字列として比較）。
  コレクションの `any/all` は未対応
- ベクトル: 常に総当たり（exhaustive KNN）。`hnsw` 指定でも近似しないので結果は同じか、より正確
- `@search.score`:
  - cosine は Azure の公式定義どおり `1 / (1 + (1 − cos))`（範囲 0.333〜1.0）。Semantic Cache のしきい値がこの値と比べられる前提
  - euclidean は `1 / (1 + 距離)`、dotProduct は内積そのもの（どちらも Azure と一致するか未検証）
- `threshold`: `{"kind":"vectorSimilarity"}` は cos（euclidean なら距離）、`{"kind":"searchScore"}` は `@search.score` で足切り
- ベクトル問い合わせが複数、またはベクトル + 文字列のときは RRF（`Σ weight / (60 + 順位)`）
- 文字列検索（`search` が `*` 以外）は語の出現回数を数える簡易版（BM25 ではない。日本語は部分一致）
- `k` の既定は 50、`top` の既定は 50

## ビルドと運用

```bash
./build.sh        # テスト（test/*.clay）を回してから build/aisearch-server を作る
./install.sh      # ~/.local/lib/aisearch-server/ に置いて systemd --user で（再）起動。初回は api-key を作る
API_KEY=$KEY python3 smoke_test.py http://172.23.0.1:8897                  # HTTP のスモークテスト
API_KEY=$KEY python3 smoke_test.py http://172.23.0.1:8897 --concurrency    # 並行登録で更新が消えないかも見る
systemctl --user status aisearch-server
journalctl --user -u aisearch-server -f     # 1 要求 1 行。本文は要約（キー名、ベクトルは長さ、vectorQueries の kind/fields/k、filter）
```

環境変数（`~/.config/aisearch-server/env`）: `AIS_API_KEYS`（カンマ区切り。空なら認証しない）
`AIS_HOST`（既定 172.23.0.1）`AIS_PORT`（既定 8897）`AIS_SERVICE`（エラー文に出るサービス名、既定 aisearch）
`AIS_DATA`（既定 ~/.local/share/aisearch-server）。

- 認証は `api-key` ヘッダ（無い・違うときは 403）。`GET /health` だけは認証なし
- 永続化: 状態を変えた要求（インデックスの作成・更新・削除、docs/index）を 1 件 1 ファイルで残し、
  起動時に連番の順に流し直す。連番は swap! の中で決めるので、並行に書いても再生の順は確定した順になる。
  ログは消さないので増え続ける（全部消せば空から始まる: `systemctl --user stop aisearch-server && rm ~/.local/share/aisearch-server/log/*.json`）
- 1536 次元・1000 件で、検索（k=1）12ms、1 件登録 1ms、100 件まとめて 90ms 程度（Ryzen 7 255）

## 構成

```
ais/web.clay      URI・クエリの分解、Azure 形式の応答、Dyn の小道具
ais/odata.clay    $filter の構文解析と評価
ais/schema.clay   インデックス定義の検証（キー欄、ベクトル欄の次元・プロファイル・metric）
ais/docs.clay     文書のバッチ（upload / merge / mergeOrUpload / delete）
ais/search.clay   検索（フィルタ → ベクトル・文字列の順位 → RRF → skip/top/select）
ais/engine.clay   ルーティング。(handle 状態 method uri body) → Values(新しい状態, 応答, 変わったか)
ais/server.clay   HTTP サーバ（認証、atom、永続化、要求ログ）
test/             engine まわりの単体・結合テスト（HTTP を通さない）
smoke_test.py     HTTP のスモークテスト（標準ライブラリのみ）
build.sh / install.sh / aisearch-server.service
```

clay 側の制約でこう書いているところ（clay エージェントに報告済み。直ったら素直な形に戻す）:

- 順位リストはレコードでなく「Vec(Str) + Map」を多値で受け渡す（レコードの欄に Vec(Float) を置けない、
  Values にも Vec にもレコードを入れられない）
- swap! に渡すクロージャの中身は名前付きの関数に出す（クロージャの中で多値の分割代入ができない）
- ファイルへの追記が無いので、永続化のログは 1 件 1 ファイル
