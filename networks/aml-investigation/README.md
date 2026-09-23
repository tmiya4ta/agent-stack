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
          ├ investigate     → orchestrator investigate  get-alert, list-transactions, screen-name,
          │                      │                      search-news, case history (A2A), save-case
          │                      └→ router foundRouter
          │                           ├ not found → echo alertNotFound (FAILED)
          │                           └ found     → generator draftMemo → echo memoArtifact → echo memoStatus
          ├ ask_alert       → echo askAlert
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

## Deploying

```bash
yc harness deploy <org> <env> finance-demo              # the three members, then the network
yc harness down   <org> <env> finance-demo              # remove what the set deployed
```

The LLM endpoint and key come from the yc variables profile (`llm-base-url`, `llm-api-key`).
Member URLs are filled in from the deployed apps. See [docs/harness.md](../../docs/harness.md).

Call the broker with A2A 1.0 (`SendMessage`, header `A2A-Version: 1.0`); for the second turn put
the first turn's `contextId` into `message.contextId`.
