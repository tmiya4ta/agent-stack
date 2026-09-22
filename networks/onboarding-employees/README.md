# onboarding-employees

A MuleSoft **Agent Network** reference built around onboarding a new employee.

A single broker orchestrates three back-office systems (employee database, IT assets, office
administration) and branches explicitly on **full success / partial failure / total failure**.
The point of the example is the last part: when something goes wrong halfway through, the caller
is told what was left half-done rather than getting a bare success.

- Format: `agentNetwork: 2.0.0` (v2) + AgentScript (`# @dialect: AGENTFABRIC=1.0`)
- Members: 2 A2A agents, 1 MCP server, 1 LLM provider
- The Mule implementations of all three members live elsewhere in this repository, each built
  and deployed on its own:
  - [a2a/it-provisioning-agent](../../a2a/it-provisioning-agent/) — A2A agent. Orders and repairs loaner laptops (mock)
  - [a2a/office-concierge-agent](../../a2a/office-concierge-agent/) — A2A agent. Issues ID badges, answers office questions (mock)
  - [mcp/employee-db-app](../../mcp/employee-db-app/) — MCP server. Registers employees in SQLite and issues employee IDs

---

## Layout

```
onboarding-employees/
├── agent-network.yaml        Network definition (registry / context / brokers)
├── exchange.json             Exchange descriptor and variables (where URLs and credentials go)
├── brokers/
│   └── broker1.agent         The broker graph, in AgentScript
└── apps/                     Symlinks to the member apps (not part of the network build)
    ├── employee-db-app/          -> ../../../mcp/employee-db-app
    ├── it-provisioning-agent/    -> ../../../a2a/it-provisioning-agent
    └── office-concierge-agent/   -> ../../../a2a/office-concierge-agent
```

---

## The broker graph

```
trigger
 └→ subagent  intake          Extract and validate name / email from the request (LLM only, no actions)
     └→ router intakeRouter
          ├ incomplete → echo rejectIncompleteRequest    TASK_STATE_FAILED, naming the missing fields
          └ complete   → orchestrator onboard            register → provision laptop → issue badge
               └→ router resultRouter
                    ├ all succeeded   → generator successReport → echo successArtifact → echo successStatus
                    ├ partial failure → generator partialReport → echo partialArtifact → echo partialStatus
                    └ all failed      → generator failureReport → echo failureStatus (TASK_STATE_FAILED)
```

Design notes, expanded in the header comment of `brokers/broker1.agent`:

- AgentScript has no exception mechanism, so failures are recorded in the orchestrator's
  structured output and routed deterministically by a router.
- **Partial success is its own path.** It is the most error-prone case in practice, and silently
  treating it as success leaves unprovisioned laptops and unissued badges unattended.
- Report generation is delegated to a generator (one LLM call) so the orchestrator only orchestrates.
- The employee ID is also returned as a machine-readable artifact for downstream systems.

### Constraints found by lint

- A router `when` cannot compare against a boolean literal. Use string comparisons.
- `TASK_STATE_INPUT_REQUIRED` is not accepted as a terminal state. Missing information is
  returned as `TASK_STATE_FAILED`, naming the fields that were missing.
- `@variables` must be declared up front and are not used here; each branch has its own response node.

---

## Placeholders

**This project does not build as checked in.** Every `{{...}}` token must be replaced first.

| Placeholder | Replace with |
|---|---|
| `{{-suffix}}` | A hyphen plus your identifier (e.g. `-acme01`), or **nothing** for a single deployment |
| `{{_suffix}}` | The same identifier with an underscore (e.g. `_acme01`), or **nothing** |
| `{{business-group-id}}` | The ID of the Business Group you deploy into |
| `{{it-provisioning-agent-url}}` etc. | Each member app's endpoint, **scheme included** — the descriptor variable behind it is a `.url`, so `https://…` is part of the value, not assumed |
| `{{llm-base-url}}` | The OpenAI-compatible base URL, scheme and version path included (e.g. `https://host/openai/v1`) |
| `{{llm-client-id}}`, `{{llm-client-secret}}`, `{{llm-api-key}}` | Its credentials |

The two suffix tokens carry their own separator, so deleting them leaves ordinary names
(`onboarding-network`, `it_provisioning_connection`). There are two of them because registry and
broker names are hyphen-separated while `context.connections` keys are underscore-separated.

Single deployment, plain names:

```bash
sed -i -e 's/{{-suffix}}//g' -e 's/{{_suffix}}//g' exchange.json agent-network.yaml brokers/broker1.agent
```

Several deployments side by side in one Business Group:

```bash
sed -i -e 's/{{-suffix}}/-acme01/g' -e 's/{{_suffix}}/_acme01/g' exchange.json agent-network.yaml brokers/broker1.agent
```

The suffix appears in all seven places that must not collide when two instances share a Business
Group, an environment and a Flex Gateway: the Exchange `assetId`, the three `registry` sections,
the broker key, the `context.connections` keys, and the `target` strings in the AgentScript.
Replacing the two tokens covers all of them.

---

## Deploying

1. **Deploy the three member apps first**, each by the steps in its own README. The network
   only references them by URL. Pass `agent.url` (this app's externally reachable URL),
   `llm.proxy.host` and `llm.apiKey` as deployment properties (`llm.apiKey` as secure)
   rather than editing `app.properties`. Each app serves its own reference page at `/doc`.

   `app.properties` wants a bare **host** in `llm.proxy.host` (Mule's HTTP requester takes host,
   port and protocol separately), while the network's variables are whole **URLs**. That is why
   the two carry different placeholder names.

2. **Fill in `exchange.json`** with the Business Group ID, the three member URLs and the LLM
   endpoint. Every one of those variables is a `.url`, so the value includes the scheme — nothing
   prepends `https://` for you. The employee DB URL is a base URL; the `/mcp` path is appended by
   the `transport` setting in `agent-network.yaml`.

3. **Build, publish, deploy.**

   ```bash
   export ANYPOINT_USERNAME='...' ANYPOINT_PASSWORD='...'
   export ANYPOINT_ORG='...' ANYPOINT_ENV='Sandbox'

   anypoint-cli-v4 agent-network project build
   anypoint-cli-v4 agent-network project publish
   anypoint-cli-v4 agent-network project deploy -g '<gateway-name>'
   ```

   Increment `version` in `exchange.json` before every publish. Publishing the same version again
   is skipped with `already exists in exchange. Skipping...`, which looks like success but changes
   nothing. Deleting the asset and republishing the same version does not help either; the version
   has to go up.

   `deploy` waits up to 900 seconds for the app to reach RUNNING and can time out with
   `errorCode: 3018` even though the deployment is fine. Check the app state directly before
   treating it as a failure.

4. **Call the broker.** Its URL is the gateway host plus the `brokers:` key as the path — after
   substitution, `https://GATEWAY_HOST/onboarding-broker/` or `.../onboarding-broker-acme01/`.
   The trailing slash is required.

   ```bash
   curl -s "$BROKER" \
     -H 'Content-Type: application/json' \
     -H 'A2A-Version: 1.0' \
     -d '{
       "jsonrpc": "2.0",
       "id": "1",
       "method": "SendMessage",
       "params": {
         "message": {
           "role": "ROLE_USER",
           "parts": [{"text": "Please start onboarding for new employee Taro Tanaka (tanaka.taro@example.com)"}],
           "messageId": "11111111-1111-1111-1111-111111111111"
         }
       }
     }'
   ```

   The method is `SendMessage` in PascalCase and the `A2A-Version: 1.0` header is mandatory.
   Sending the A2A 0.3 `message/send` returns `-32601 Method not found`; omitting the header
   returns `-32009 Unsupported A2A version`.

### Requirements

- An Anypoint Platform Business Group with Agent Fabric enabled
- A Managed Flex Gateway on **1.12.x LTS or newer** — below 1.10.0 the required policies have no
  implementation and deployment fails with `errorCode: 3004`
- `anypoint-cli-v4` with the `agent-network` plugin
- Maven 3.9+ and JDK 17, to build the member apps

---

## Credentials

`openAI.*` in `exchange.json` and `llm.apiKey` in `a2a/*/src/main/resources/app.properties` are
placeholders. **Do not commit real values.** Pass them as secure deployment properties instead.
