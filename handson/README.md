# handson

Hands-on material, laid out like [../demos/](../demos/): one folder per hands-on, named after
its set, holding the set (`harness.yaml`), the agent network and its member Mule apps. The
requirements and conventions in [../demos/README.md](../demos/README.md) apply here too.

| Hands-on (= set) | What it builds |
|---|---|
| [new-hire-onboarding](new-hire-onboarding/) | New employee onboarding. The [onboarding-employees](new-hire-onboarding/onboarding-employees/) broker orchestrates 2 A2A agents and 1 MCP server, branching explicitly on full success, partial failure and total failure |

```bash
yc harness deploy <org> <env> new-hire-onboarding [suffix=<s>] [use-existing=<profile>:<bg>/<env>]
yc harness down   <org> <env> new-hire-onboarding [suffix=<s>]
```
