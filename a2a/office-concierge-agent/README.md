# office-concierge-agent

Office Concierge Agent — an A2A agent (Mule 4.11, Java 17). Issues ID badges for new hires and answers questions about office rules (mock). An employee ID is required to issue a badge.
It replies through an OpenAI-compatible Responses API endpoint.

Used by [networks/onboarding-employees](../../networks/onboarding-employees/), but it is an
ordinary Mule app and is built and deployed on its own.

## Endpoints

| Path | What |
|---|---|
| `/` | A2A JSON-RPC endpoint (`agentPath="/"`) |
| `/.well-known/agent-card.json` | Agent card; its `url` is `${agent.url}` |
| `/doc` | Reference page |

## Properties

Defaults are in `src/main/resources/app.properties`. Pass these at deploy time instead of editing the file:

| Property | Value |
|---|---|
| `agent.url` | This app's externally reachable URL. The broker fetches the card and calls back to it |
| `llm.proxy.host` | Bare host of the OpenAI-compatible endpoint (no scheme, no path) |
| `llm.apiKey` | **Secure.** Sent as `Authorization: Bearer …` |

`llm.proxy.port` / `llm.proxy.protocol` / `llm.proxy.path` / `llm.model` can be overridden the same way.

## Build and deploy

```bash
mvn -B package -DskipTests      # target/office-concierge-agent-app-1.7.8-mule-application.jar

yc deploy file <org> Sandbox <business-group-id> office-concierge-agent-app 1.7.8 \
  target/office-concierge-agent-app-1.7.8-mule-application.jar target=ch2:<cluster> name=office-concierge-agent \
  +agent.url=https://<app-host> +llm.proxy.host=<llm-host> +secure:llm.apiKey=<key>
```

Bump `<version>` in `pom.xml` before re-publishing; Exchange does not accept the same version twice.
After deploying, set the app's URL as `office-concierge-agent{{-suffix}}.url` in the network's `exchange.json`.
