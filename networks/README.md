# networks

Reference implementations of MuleSoft **Agent Fabric** agent networks.

Each folder is the root of one Agent Network project — `agent-network.yaml`, `exchange.json`,
`brokers/` and a `harness.yaml`. The Mule apps that make up its members live in
[`../a2a/`](../a2a/) and [`../mcp/`](../mcp/) and are listed under `members` in the
`harness.yaml`, so yc deploys them along with the network.

| Reference | What it shows | Members |
|---|---|---|
| [onboarding-employees](onboarding-employees/) | New employee onboarding. One broker orchestrates 2 A2A agents and 1 MCP server, branching explicitly on full success, partial failure and total failure | `it-provisioning-agent`, `office-concierge-agent`, `employee-db-app` |
| [aml-investigation](aml-investigation/) | First pass of an AML alert investigation (fictitious bank data). The agent gathers and drafts; the analyst decides | `case-history-agent`, `core-banking-mcp`, `screening-mcp` |
| [max-surveillance](max-surveillance/) | Max Securities (fictitious): investigates trade surveillance alerts and asks for approval | MCP on k0 `max-core` ([max/](../max/)) |
| [max-operations](max-operations/) | Max Securities: account opening | MCP on k0 `max-core` |
| [max-support](max-support/) | Max Securities: customer inquiries. Drafts replies from FAQ facts; guarded ones go to the approval inbox | MCP on k0 `max-core` |

The max-* networks have no `members`: their MCP server is `max-core` running on k0 (not deployed
by yc), and its URL comes from a yc variables profile.

---

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
