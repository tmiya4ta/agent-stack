# aml-investigation

A MuleSoft **Agent Network** that does the first pass of an anti-money-laundering (AML) alert
investigation. The agent gathers and drafts; **the analyst decides**.

Transaction monitoring raises alerts, most of which turn out to be harmless, and an analyst
spends most of the time on each one collecting the customer profile, the transactions, screening
and news results and similar past cases before writing a memo. This network does the collecting
and the draft, recommends one of three outcomes, and waits. The analyst's reply in the same
conversation is recorded as the decision — by a deterministic executor, with no LLM between the
reply and the record.

- Format: `agentNetwork: 2.0.0` (v2) + AgentScript (`# @dialect: AGENTFABRIC=1.1`)
- Members, each built and deployed on its own (all data fictitious):
  - [mcp/core-banking-mcp](../../mcp/core-banking-mcp/) — alerts, customers, transactions; investigation state and decisions
  - [mcp/screening-mcp](../../mcp/screening-mcp/) — watch-list screening and news search
  - [a2a/case-history-agent](../../a2a/case-history-agent/) — similar past cases and how they were decided
- Provision everything at once with the [finance-demo](../../sets/finance-demo/) set

## The conversation

```
any     analyst: "アラート一覧を見せて"  (or any message without an alert ID)
        broker:  📋 table of alerts with status and customer, then "send the ID to investigate"
turn 1  analyst: "アラート ALT-0915 を調べてください"
        broker:  🔎 調査メモ（下書き）— alert, customer profile, notable transactions (table),
                 screening and news, similar past cases, sources that could not be reached,
                 recommendation, and "reply with クローズ / 届出検討 / 保留 and your reason"
turn 2  analyst: "届出検討。基準額を避けた分割入金で、送金先も要注意リストに一致"   (same contextId)
        broker:  ✅ アラート ALT-0915 の判断「届出検討」を記録しました。理由: …
```

| Alert | What the draft should say |
|---|---|
| ALT-0901 | The deposit is the employer's annual bonus, as last year → クローズ |
| ALT-0915 | Structured cash deposits, then money to a Hong Kong company on the bank's own watch list → 届出検討 |
| ALT-0922 | A namesake was arrested, but age and address differ; the source of ¥12M still needs papers → 保留 |

## The broker graph

```
trigger
 └→ subagent classify         get-case(contextId): new / awaiting_decision / decided
     └→ router mainRouter
          ├ investigate     → orchestrator investigate  get-alert (profile + transactions),
          │                      │                      check-parties (watch lists + news), case history (A2A)
          │                      └→ router foundRouter
          │                           ├ not found → echo alertNotFound (FAILED)
          │                           └ found     → executor saveCase (save-case, no LLM)
          │                                          → generator draftMemo → echo memoArtifact → echo memoStatus
          ├ list_alerts     → subagent listAlerts (list-alerts) → echo alertList   (no alert ID: list, never ask)
          ├ decide          → executor recordDecision (record-decision) → echo decisionRecorded
          ├ ask_decision    → echo askDecision
          └ already_decided → echo alreadyDecided
```

Design notes, expanded in the header of `brokers/aml_broker.agent`:

- A turn cannot pause and resume, so each turn ends `COMPLETED` and the analyst answers in the
  same conversation. Progress is kept in the Core Banking MCP under the `contextId`.
- Nodes that call tools are told never to address the human; a question from an orchestrator
  ends the task early. Every question to the human is its own `echo`.
- A source that fails is listed under 「確認できなかった材料」 instead of silently disappearing.

## Measured (T1 / Sandbox, gpt-5-mini, 2026-09-23)

| | Time | Recommendation |
|---|---|---|
| ALT-0901 turn 1 | 47 s | クローズ |
| ALT-0915 turn 1 | 41 s | 届出検討 |
| ALT-0922 turn 1 | 47–72 s | 保留（追加確認） |
| decision turn | 10–12 s | recorded with a decision ID |

### Pitfalls met on the way

- **Every tool call is an LLM round trip.** The first version called seven tools one by one and
  the gateway answered 504. The backends now return bundles (`get-alert` includes the
  transactions, `check-parties` screens several names), state is saved by an executor, and the
  LLM runs with `reasoning_effort: "LOW"` (the enum is upper case).
- **Keep the orchestrator's structured output short.** Asking it to copy every transaction made
  the turn fail with `An internal error occurred while processing your request.`
- **A tool whose input schema nests objects in an array fails the broker's tool validation**
  (`A tool service failed validation.`, within a second, on every node). `check-parties` takes an
  array of strings instead. The broker checks the tools when it starts, so restart it after a
  member gains a tool.
- **Connection keys and registry names are per environment, not per network.** A second
  `openai_connection` fails with 409; everything here is prefixed `aml_`.
- **Examples in a prompt become facts.** An example of "usual activity" in the orchestrator's
  instructions showed up in a memo for a customer who has no such history.

## Deploying

```bash
yc harness deploy <org> <env> finance-demo              # the three members, then the network
yc harness down   <org> <env> finance-demo              # remove what the set deployed
```

The LLM endpoint and key come from the yc variables profile (`llm-base-url`, `llm-api-key`).
Member URLs are filled in from the deployed apps. See [docs/harness.md](../../docs/harness.md).

Call the broker with A2A 1.0 (`SendMessage`, header `A2A-Version: 1.0`); for the second turn put
the first turn's `contextId` into `message.contextId`.
