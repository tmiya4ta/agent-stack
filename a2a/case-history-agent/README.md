# case-history-agent

Case History Agent — an A2A agent (Mule 4.11, Java 17) that finds past AML investigations similar
to a new alert and reports how they were decided and why. Used by the
[AML alert investigation](../../networks/aml-investigation/) network.

The past cases (all fictitious) are fixed in the system prompt in
`src/main/mule/case-history-agent.xml`; the LLM only picks and explains the similar ones and is
told never to invent a case. It calls an OpenAI-compatible Responses API endpoint.

| Path | What |
|---|---|
| `/` | A2A JSON-RPC endpoint (`message/send`, A2A 0.3) |
| `/.well-known/agent-card.json` | Agent card; its `url` is `${agent.url}` |

## Properties

| Property | Value |
|---|---|
| `agent.url` | This app's externally reachable URL |
| `llm.proxy.host` | Bare host of the OpenAI-compatible endpoint |
| `llm.apiKey` | **Secure.** Sent as `Authorization: Bearer …` |

```bash
mvn -B package -DskipTests
yc harness deploy <org> <env> case-history-agent target=ps:<space>   # fills the three properties
```
