# demos

Demos to show. One folder per demo, named after its set. Each holds the set (`harness.yaml` at
the folder root), its MuleSoft **Agent Fabric** agent networks and the Mule apps that make up
their members, so everything a demo needs is in one place. Inside, folders are named after the
harness `name` of the unit they hold. Hands-on material lives in [../handson/](../handson/).

| Demo (= set) | What it shows |
|---|---|
| [suspicious-transaction-review](suspicious-transaction-review/) | A bank's anti-money-laundering (AML) review of suspicious-transaction alerts (fictitious bank data). The [aml-investigation](suspicious-transaction-review/aml-investigation/) network, two MCP servers and one A2A agent. The agent gathers and drafts; the analyst decides |
| [max-securities](max-securities/) | Max Securities, a fictitious online brokerage: trade surveillance, account opening and customer inquiries, with staff only giving the final approval. `max-core` / `max-oms` run on k0 under mulay and are deployed separately ([max-securities/deploy](max-securities/deploy/)) |

```bash
yc harness deploy <org> <env> suspicious-transaction-review [suffix=<s>] [use-existing=<profile>:<bg>/<env>]
yc harness down   <org> <env> suspicious-transaction-review [suffix=<s>]
```

A network brings its `members` (listed in its `harness.yaml`) along. The max-* networks have no
`members`: their MCP server is `max-core` on k0, and its URL comes from a yc variables profile.
See [docs/harness.md](../docs/harness.md).

## Requirements

- An Anypoint Platform Business Group with Agent Fabric enabled
- A Managed Flex Gateway on **1.12.x LTS or newer**
- `anypoint-cli-v4` with the `agent-network` plugin

## Conventions

These apply to [../handson/](../handson/) as well.

- `{{...}}` tokens are placeholders and must be replaced before building. Nothing here builds
  as checked in.
- `{{-suffix}}` and `{{_suffix}}` carry their own separator, so deleting them yields the plain
  single-deployment names. Replace them with `-myid` / `_myid` to run several instances side by
  side in one Business Group.
- Credentials never live in the repository. Pass them as secure deployment properties.
