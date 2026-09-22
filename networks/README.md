# networks

Reference implementations of MuleSoft **Agent Fabric** agent networks.

Each folder is the root of one Agent Network project — `agent-network.yaml`, `exchange.json` and
`brokers/` — together with the Mule apps that make up its members, so each reference can be
deployed on its own.

| Reference | What it shows |
|---|---|
| [onboarding-employees](onboarding-employees/) | New employee onboarding. One broker orchestrates 2 A2A agents and 1 MCP server, branching explicitly on full success, partial failure and total failure |

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
