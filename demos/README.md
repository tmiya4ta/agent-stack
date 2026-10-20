# demos

One folder per demo. Each holds the demo's set (`harness.yaml` at the folder root), its MuleSoft
**Agent Fabric** agent networks and the Mule apps that make up their members, so everything a
demo needs is in one place. Folders are named after the harness `name` of the unit inside.

| Demo | Set | What it brings up |
|---|---|---|
| [onboarding](onboarding/) | `onboarding-demo` | New employee onboarding. The [onboarding-employees](onboarding/onboarding-employees/) broker orchestrates 2 A2A agents and 1 MCP server, branching explicitly on full success, partial failure and total failure |
| [finance](finance/) | `finance-demo` | First pass of an AML alert investigation (fictitious bank data). The [aml-investigation](finance/aml-investigation/) network, two MCP servers and one A2A agent. The agent gathers and drafts; the analyst decides |
| [max](max/) | `max-demo` | Max Securities (fictitious): the surveillance, operations and support networks. `max-core` / `max-oms` run on k0 under mulay and are deployed separately ([max/deploy](max/deploy/)) |

```bash
yc harness deploy <org> <env> onboarding-demo [suffix=<s>] [use-existing=<profile>:<bg>/<env>]
yc harness down   <org> <env> onboarding-demo [suffix=<s>]
```

A network brings its `members` (listed in its `harness.yaml`) along. The max-* networks have no
`members`: their MCP server is `max-core` on k0, and its URL comes from a yc variables profile.
See [docs/harness.md](../docs/harness.md).

## Requirements

- An Anypoint Platform Business Group with Agent Fabric enabled
- A Managed Flex Gateway on **1.12.x LTS or newer**
- `anypoint-cli-v4` with the `agent-network` plugin

## Conventions

- `{{...}}` tokens are placeholders and must be replaced before building. Nothing here builds
  as checked in.
- `{{-suffix}}` and `{{_suffix}}` carry their own separator, so deleting them yields the plain
  single-deployment names. Replace them with `-myid` / `_myid` to run several instances side by
  side in one Business Group.
- Credentials never live in the repository. Pass them as secure deployment properties.
