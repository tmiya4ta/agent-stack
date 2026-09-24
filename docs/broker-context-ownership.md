# Agent Network の broker は contextId と利用者 ID をどう管理しているか

2026-09-23、T1 / Sandbox（private space rootps、Managed Flex Gateway ft1）で、
`networks/aml-investigation` の broker（Agent Network v2）を使って確かめた記録。

## 結論

- broker（agent graph の実行環境）は、**`contextId` と利用者 ID を 1 つの ID に合成しない**。
  タスク 1 件ごとの記録に `context_id` と `user_id` を**別々のフィールド**として持つ。
- `user_id` は、`user-context-propagation` ポリシーの `userIdExpression` で取り出した値の
  **SHA-256 ハッシュ（16 進 64 桁）**。JWT の `sub` を指定した場合、`sha256("hanako")` がそのまま入る。
- 身元が解決できないとき（認証ポリシーが無い、または順序が逆）は `user_id = "__default__"`。
- 別の利用者が他人の `contextId` で続きを送ると、**0 秒で `TASK_STATE_FAILED`
  「The operation is not permitted.」**。グラフは動かない。拒否された試行も、
  その `contextId` のもとに**送った側の `user_id` で FAILED のタスクとして記録される**。

## JWT のクレームを指定するポリシー

| ポリシー | 役割 | クレームの指定 |
|---|---|---|
| `user-context-propagation` 1.0.0 | 認証結果から利用者 ID を取り出し、上流に渡す。**持ち主を決めるのはこれ** | `userIdExpression`（DataWeave 式。既定 `#[authentication.clientId]`） |
| `jwt-validation` 0.11.1 | JWT を検証し、認証結果（Authentication）を作る | `validateCustomClaim`・`validateAudClaim`（検証）、`claimsToHeaders`（ヘッダへの受け渡し）。持ち主は決めない |

- JWT のクレームを使うときの式は **`#[authentication.properties.claims.sub]`**（`claims.` が入る）。
  ポリシー定義の説明文にある例 `#[authentication.properties.sub]` では解決できない（以前の実測）。
- 順序は **認証ポリシー → `user-context-propagation`**。公式ドキュメントも
  「逆にすると ID が空になり、タスクは持ち主なしで作られる」としている。
- Flex Gateway に付けられた `jwt-validation` は 0.11.1（実装アセットを分けない形、`impl` 指定なし）。
  `skipClientIdValidation: true` にすると契約（クライアントアプリ）が要らない。

## 実測の手順

1. broker の API インスタンス（デプロイ時に `a-two-a-v1-agent-card` / `tracing` /
   `header-injection` / `user-context-propagation` が自動で付く）に、
   `jwt-validation` 0.11.1 を order 4 で追加し、`user-context-propagation` を order 5 に下げて
   `userIdExpression` を `#[authentication.properties.claims.sub]` に変えた。
2. HS256（共有秘密鍵）の JWT を `sub=hanako` と `sub=taro` の 2 人分、手元で発行した。
3. A2A 1.0（`SendMessage`、`A2A-Version: 1.0`）で次を送った。

| 送信 | 結果 |
|---|---|
| JWT なし | HTTP 400 `JWT Token is required.`（0.3 秒） |
| hanako が新しい会話（contextId `8c21b213…` が採番される） | COMPLETED（16 秒） |
| taro が hanako の `8c21b213…` で続きを送る | **FAILED「The operation is not permitted.」（0 秒）** |
| hanako が自分の `8c21b213…` で続きを送る | COMPLETED（15 秒） |
| taro が新しい会話 | COMPLETED（12 秒） |

4. broker の Object Store を読み、タスクの記録を確かめた（下記）。

## broker の保存先（Object Store v2）

- ストア: `<network アプリのデプロイ ID>-Object-Store`。network アプリと同じリージョン
  （rootps なら `object-store-ap-northeast-1`）。Object Store v2 の API で読める
  （`read:store` を持つ Connected App）。
- パーティションは broker ごとに 6 つ。ただし `context-conversation-store` と 2 つの索引は、
  **身元のわかる利用者（`user_id` が `__default__` 以外）のタスクが初めてできたときに作られる**。
  9-23 09:37（JWT を付ける前）に一覧したときは 3 つだけだった。JWT を付けた後も、
  `__default__` のタスク（11:44 のものなど）は会話・索引のどちらにも入らない。
  値はどれも `{"task_id", "context_id", "user_id", "timestamp", "payload_json"}` の形の JSON 文字列で、
  使わない欄は null（インデックスの 2 つだけは ID の配列）。

| パーティション | キー | 値 |
|---|---|---|
| `<broker>-task-store` | taskId | `task_id` / `context_id` / `user_id`（= `x-ms-user-id`）/ `timestamp` / `payload_json`（A2A 1.0 の Task 本体。`status.state`、応答メッセージ、`history`） |
| `<broker>-graph-state-store` | taskId | `task_id` と `timestamp` だけが入り、`payload_json` に実行状態（`execution.runtime` の今のノード、ノードごとの実行、変数、メッセージ、グラフ定義全体、`execution_history`、`turn_count`、`status`）。`context_id` / `user_id` は null |
| `<broker>-context-conversation-store` | `conversation:<contextId>` | `context_id` / `user_id` と、`payload_json` = `{"v":1,"messages":[{role, content, task_id}…]}`（会話の全発言。user の文と、各ノードの構造化出力） |
| `<broker>-task-store-ctx-index` | contextId | その会話の taskId の配列（持ち主のタスクだけ。他人の拒否された試行は入らない） |
| `<broker>-task-store-user-index` | `user_id`（ハッシュ） | その利用者の taskId の配列（拒否された試行も、送った側の分として入る） |
| `<broker>-tool-context-store` | `<contextId>:<接続名>-client` | `payload_json` = 下流 A2A の `{"context_id", "task_id", "task_state"}` |

上の実測のタスク記録（`task-store`、抜粋）:

```
timestamp                 context_id  user_id (= sha256(sub))   state
2026-09-23T09:49:29.299Z  8c21b213…   eb4950984bcc…  (hanako)   COMPLETED
2026-09-23T09:49:29.634Z  8c21b213…   8ff52c91ed7d…  (taro)     FAILED     ← 拒否された試行
2026-09-23T09:49:44.444Z  8c21b213…   eb4950984bcc…  (hanako)   COMPLETED
2026-09-23T09:49:56.889Z  71017d67…   8ff52c91ed7d…  (taro)     COMPLETED
認証を付ける前のタスク                             __default__
```

## 見えていないこと・注意

- 持ち主の照合そのもの（同じ `context_id` のタスクの `user_id` と比べていると考えられる）は、
  実行環境のソースが非公開なので**推測**。記録の形と振る舞いは上のとおり。
- 以前の実測（別のデモ）では、`user-context-propagation` を外している間に作られた会話は、
  あとで戻しても誰でも続きを送れた。`__default__` で保存されるためと考えられる。
- **手で足した ingress ポリシーは、network を再デプロイすると消える。** 代わりに
  agent-network.yaml の `brokers.<id>.interfaces.a2a.policies.inbound` に書けば毎回付く
  （`networks/aml-investigation/agent-network.yaml` がその形。公式プラグイン 1.3.0 と、
  2026-09-23 以降の yc の両方で確認）。
- broker から下流（MCP / A2A）への contextId は下流が採番し、利用者とは結び付かない
  （`tool-context-store` に別に保存される。次の節）。

## user-context-propagation が上流に送るもの（2026-09-24 実測）

受け取ったヘッダをそのまま返すだけの Mule アプリを上流にして、Flex Gateway（ft1）に
`jwt-validation`（order 1）→ `user-context-propagation`（order 2、`#[authentication.properties.claims.sub]`）
を付けて呼んだ。

| リクエスト | 上流が受け取った `x-ms-user-id` |
|---|---|
| hanako の JWT | `eb4950984bcc…`（= `sha256("hanako")`。生の `hanako` ではない） |
| hanako の JWT ＋ 自分で `x-ms-user-id: taro` | `eb4950984bcc…`（**クライアントの値は上書き**） |
| taro の JWT ＋ 自分で `x-ms-user-id: <hanako のハッシュ>` | `8ff52c91ed7d…`（= `sha256("taro")`。**なりすませない**） |
| `sub` の無い JWT（式が解決しない） | **ヘッダなし** |
| `sub` の無い JWT ＋ 自分で `x-ms-user-id: taro-spoof` | **ヘッダなし（クライアントの値を消す）** |
| JWT なし | `jwt-validation` が 400 で止める（上流に届かない） |
| **`user-context-propagation` を外して** hanako の JWT ＋ `x-ms-user-id: taro-spoof` | **`taro-spoof` がそのまま届く** |

- このポリシーがすることは、**ヘッダ `x-ms-user-id` に「式の値の SHA-256（16 進 64 桁）」を入れる**こと。
  クライアントが送った同名のヘッダは、上書きするか（値があるとき）消す（値が無いとき）。
  ほかのヘッダは足さない（`authorization` はそのまま上流に届く）。
- broker の `task-store` の `user_id` はこのヘッダの値と同じ。broker はハッシュし直さずにこの値を使っている。
- ポリシーを外すと、クライアントが送った `x-ms-user-id` が素通りする。broker がそのとき
  このヘッダを信じるかは未確認（ポリシーが無い間は `__default__` だった以前の実測は、ヘッダを送っていない）。
  **broker の前から `user-context-propagation` を外さない**こと。
- ポリシーの実装（Exchange の `user-context-propagation-flex` の WASM。ソースは配布されていないが
  Rust の関数名が残っている）も読んだ。処理は **リクエストの入口の 1 か所だけ**
  （`user_context_propagation_policy::request_filter`、応答側のフィルタは無い）で、順に
  1. 前のポリシーが残した認証結果（Authentication）を読む（読むだけで書き換えない）
  2. `userIdExpression` を評価する
  3. 結果が空でない文字列なら、SHA-256 を 1 回かけて小文字の 16 進にし、`set_header("x-ms-user-id", …)`
     （同名のヘッダがあれば置き換え）
  4. 評価に失敗した・空文字・文字列でないときは、ログ（`User ID expression evaluation failed` など）を出して
     `remove_header("x-ms-user-id")`

  このほかに、プロパティ（`set_property`）・本文・ほかのヘッダ・外部呼び出しには触れていない。
  つまり**このポリシーが上流に渡すものは `x-ms-user-id` ヘッダだけ**。
- 付け替えの直後は、ゲートウェイの複製ごとに反映の時差があり、数十秒ほど古い設定の応答が混じった。

## taskId でも同じ照合がかかる（2026-09-24 実測）

`task-store` のキーは taskId だが、**taskId を知っているだけでは他人のタスクを読めない**。
hanako が作ったタスク（taskId `0c2a3f63…`）を taro の JWT で `GetTask`（A2A 1.0、`{"id": "<taskId>"}`。
`taskId` という名前のパラメータは無く `-32602 Invalid params` になる）した:

| 呼び出し | 結果 |
|---|---|
| taro が hanako の taskId を `GetTask` | `-32603 "The operation is not permitted."`（データ不返却） |
| hanako が自分の taskId を `GetTask` | 成功。`status` と `history` が返る |

Object Store のキーが taskId であることと、taskId を知っている人が読めることは別で、
broker は `GetTask` でも「タスクの `user_id` と呼び出し元の `user_id` が一致するか」を照合している。
contextId 経由の会話乗っ取り防止と同じ仕組みが、taskId 経由の読み取りにも一貫してかかっている。

## broker → 下流 A2A エージェントの contextId / taskId

同じ日に、下流の `case-history-agent` に受信した ID を記録させ（`GET /debug/a2a-log`）、
1 つの broker 会話（contextId `cb8beda1…`）の中で 3 回呼ばせて確かめた。
下流はタスク形式（`kind: "task"`、毎回新しい taskId）で返す。

| 回 | broker → 下流 | 下流 → broker |
|---|---|---|
| 1（調査） | `contextId` なし、`referenceTaskIds` なし（message のキーは kind / messageId / parts / role だけ） | contextId `3f74ceca…`（下流が採番）、taskId `c6d6c03b…` |
| 2（追加質問） | contextId `3f74ceca…`、`referenceTaskIds: ["c6d6c03b…"]`（1 回目の taskId） | 同じ contextId、taskId `c59fe266…` |
| 3（追加質問） | contextId `3f74ceca…`、`referenceTaskIds: ["c59fe266…"]`（2 回目の taskId） | 同じ contextId、taskId `6a493503…` |

- broker は下流への **contextId を自分で採番しない。初回は送らず**、下流が返した値を以後送り続ける。
- `taskId` は送らない。代わりに **`referenceTaskIds` に直前の taskId を 1 つだけ**入れる。
- 対応表は `<broker>-tool-context-store` のキー `<broker 側 contextId>:<接続名>-client` に 1 件だけあり、
  値は `{"context_id": <下流の contextId>, "task_id": <直前の下流 taskId>, "task_state": ...}`。
  3 回目の後は `task_id = 6a493503…`（最新）に上書きされていた。
- 記録は A2A の接続だけ。MCP の接続には無い。
- 下流が contextId を返さないと鎖は切れる（以前の HITL デモで実測）。下流が
  **メッセージ形式で返すと taskId が無い**ので、`task_id` は空文字で保存される
  （修正前の case-history-agent で確認）。その場合に次の `referenceTaskIds` がどうなるかは未確認。
- 下流 A2A エージェントを書くときは、**受け取った contextId があれば使い、無ければ採番して返す**。
  以前の agent-stack の A2A アプリは日付ごとの固定値を返していたため、別の利用者・別の会話が
  下流では同じ会話になっていた（2026-09-23 修正）。
