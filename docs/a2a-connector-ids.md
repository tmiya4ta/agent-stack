# A2A コネクタ（Mule）は contextId / taskId をどう管理しているか

2026-09-23、`mule4-a2a-connector` 1.1.1（A2A 0.3）で作った単独のエージェント
[a2a/address-change-agent](../a2a/address-change-agent/)（住所変更の受付、LLM なし）をローカルの
Mule 4.11.3 で動かし、`/debug/ids`（受信した ID）と `/debug/store`（コネクタのタスク保存先）で確かめた。
コネクタ本体（`ServerAgent`、`TaskHistoryParameterGroup`、`repository/*`）のクラスも読んだ。

## 結論

- **ID はコネクタが決める。** クライアントが `taskId` / `contextId` を送らなければ、フローが呼ばれる前に
  コネクタが新しく採番し、`attributes.taskId` / `attributes.contextId` に入れて渡す
  （メッセージ本体の `message.taskId` / `message.contextId` は空のまま）。
  フローはこの 2 つをそのまま応答の Task（`id` / `contextId`）に使えばよい。
- **同じ `taskId` を送ると同じタスクが続く**（`input-required` → `completed`）。
  **`contextId` だけ送ると、同じ会話の中の新しいタスク**になる。
- **タスクの状態の検査もコネクタがする。** 次のものは、フローが呼ばれる前に JSON-RPC エラーで返る。

| 送ったもの | 結果 |
|---|---|
| 終わったタスク（completed / canceled）に続きを送る | HTTP 400 `-32004 Task has reached terminal state.` |
| 存在しない `taskId` | HTTP 404 `-32001 task not found!` |
| `taskId` だけで `contextId` なし | HTTP 500 `-32602 Task belongs to different context!`（コネクタが新しい contextId を採番し、タスクの contextId と食い違うため） |
| `tasks/get` / `tasks/cancel`（authorization-listener が無いとき） | HTTP 403 `-32005 Authorization listener required for tasks/get` |

- `tasks/get` と `tasks/cancel` は**コネクタが自分で答える**（task-listener のフローは呼ばれない）。
  ただし `<a2a:authorization-listener>` のフローが必要で、そのフローがエラーなく終われば許可になる。
  `tasks/cancel` の後、そのタスクへの送信は `-32004`。

## 保存のしかた（タスク保存先）

`<a2a:server-config>` の `<a2a:history taskHistoryEnabled="true" defaultMaxHistoryLength="20" taskRepositoryObjectStore="…"/>`
（`<a2a:agent-card>` の後に置く）。

| キー | 値 |
|---|---|
| `context-<contextId>` | `{"contextId": …}` だけ（会話が存在することの記録） |
| `task-<taskId>` | `contextId`、`taskState`（最後の状態）、`task`（フローが返した Task）、`history`（user と agent のメッセージを JSON 文字列で）、`historyLength`、`pushNotificationConfigs`、`streamingContext` |

`history` の例（1 つのタスクで 3 往復）: 1 通目の user メッセージには taskId / contextId が無く、
2 通目以降と agent の返事には、コネクタが決めた taskId / contextId が付いている。

### 保存先を指定しないとき（コネクタのクラスから）

- 履歴が無効（`taskHistoryEnabled=false`）で、かつカードの `capabilities.pushNotifications` が false なら、
  **タスクを保存しない**（そのとき `tasks/get` などに答えられない）。
- 保存先を指定しなければ、コネクタが Object Store `_a2a-taskRepository-<設定名>` を作る:
  **persistent（CloudHub なら Object Store v2）、TTL 1 日、`maxEntries = defaultMaxHistoryLength`**。
  最後の点は、「履歴の長さ」の設定が「保存できるエントリ数」を兼ねてしまうので、既定値のままだと
  タスクが多いときに古いものから消えるおそれがある（未検証）。自前の Object Store を渡すほうが安全。

## 作るときの注意

- 1.1.1 は `mule-maven-plugin` 4.9.x が必要。4.7.0 では `org/mule/runtime/http/api/sse/server/SseClient`
  が無くてビルドが落ちる。
- カードは `<a2a:agent-card><a2a:json>…</a2a:json></a2a:agent-card>`（0.4.0-BETA の `<a2a:card>` とは別の書き方）。
- 応答は `<a2a:task-listener><a2a:response><a2a:response>#[vars.taskJson]</a2a:response></a2a:response>` に
  Task の JSON（`kind: "task"`、`id`、`contextId`、`status.state`、`status.message`、`artifacts`）を渡す。
  `status.state` に `input-required` / `completed` / `canceled` などを入れれば、そのままタスクの状態になる。
- agent-network の broker から呼ばれる側としては、**broker は初回に contextId を送らない**ので、
  コネクタが採番した contextId を返せばよい（[broker-context-ownership.md](broker-context-ownership.md)）。
