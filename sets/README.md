# sets

Named selections of units provisioned together with one command. Each folder holds only a
`harness.yaml`; see [docs/harness.md](../docs/harness.md#runtime-set).

| Set | What it brings up |
|---|---|
| [onboarding-demo](onboarding-demo/) | The employee onboarding network and its three member apps |
| [finance-demo](finance-demo/) | AML alert investigation: the network, two MCP servers and one A2A agent (fictitious bank data) |
| [max-demo](max-demo/) | Max Securities (fictitious): the surveillance, operations and support networks. `max-core` / `max-oms` are deployed separately to k0 ([k0/max-rtf](../k0/max-rtf/)) |

```bash
yc harness deploy <org> <env> onboarding-demo [suffix=<s>] [use-existing=<profile>:<bg>/<env>]
yc harness down   <org> <env> onboarding-demo [suffix=<s>]
```
