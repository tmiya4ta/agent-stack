# address-change-agent

Address Change Intake Agent — a standalone A2A agent (Mule 4, Java 17, **A2A connector 1.1.1**,
no LLM) that takes a bank customer's change of address. It asks for whatever is missing (task
state `input-required`) until it has the account number, the new address and the moving date,
then issues a receipt number (`completed`). `キャンセル` cancels the task.

It exists to observe how the A2A connector assigns and stores `contextId` / `taskId`; what was
found is in [docs/a2a-connector-ids.md](../../docs/a2a-connector-ids.md).

| Path | What |
|---|---|
| `/` | A2A JSON-RPC (`message/send`, `tasks/get`, `tasks/cancel`; A2A 0.3) |
| `/.well-known/agent-card.json` | Agent card |
| `GET /debug/ids` | Each call: the ids the listener received (attributes and message) and the ids / state returned |
| `GET /debug/store` | The connector's own task repository, key by key |

```
you:   住所変更をお願いします                              → input-required (new taskId, new contextId)
you:   口座は 1002-0002 です             (same taskId)      → input-required
you:   東京都板橋区大山町1-2-3、10月1日  (same taskId)      → completed, receipt ADR-…
```

Connector 1.1.1 needs `mule-maven-plugin` 4.9.x (4.7.0 fails with a missing `SseClient` class).
The task repository is set with `<a2a:history taskRepositoryObjectStore=…>` after
`<a2a:agent-card>`; `tasks/get` and `tasks/cancel` need an `<a2a:authorization-listener>` flow.

```bash
yc harness deploy <org> <env> address-change-agent target=ps:<space>
```
