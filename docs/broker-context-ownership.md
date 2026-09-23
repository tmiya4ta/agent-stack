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
- パーティションは broker ごとに 3 つ。

| パーティション | キー | 中身 |
|---|---|---|
| `<broker>-task-store` | タスク ID | `task_id` / `context_id` / `user_id` / `timestamp` / `payload_json`（A2A のタスク本体） |
| `<broker>-graph-state-store` | タスク ID | 実行状態（今のノード、ノードごとの実行記録、グラフ定義） |
| `<broker>-tool-context-store` | `<contextId>:<下流の接続名>-client` | 下流の A2A エージェントが返した contextId とタスクの状態 |

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
- **`agent-network project deploy`（yc の network デプロイも同様）を再実行すると、手で足した
  ingress ポリシーは消える。** 再デプロイのたびに `jwt-validation` と `userIdExpression` を
  貼り直す必要がある。
- broker から下流（MCP / A2A）への contextId は下流が採番し、利用者とは結び付かない
  （`tool-context-store` に別に保存される）。
