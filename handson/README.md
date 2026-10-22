# handson

Hands-on material, laid out like [../demos/](../demos/): one folder per hands-on, named after
its set, holding the set (`harness.yaml`), the agent network and its member Mule apps. A hands-on
that follows someone else's workshop holds the tutorial and credentials list instead. The
requirements and conventions in [../demos/README.md](../demos/README.md) apply here too.

| Hands-on (= set) | What it builds |
|---|---|
| [new-hire-onboarding](new-hire-onboarding/) | New employee onboarding. The [onboarding-employees](new-hire-onboarding/onboarding-employees/) broker orchestrates 2 A2A agents and 1 MCP server, branching explicitly on full success, partial failure and total failure. [hosting.md](new-hire-onboarding/hosting.md) and [setup/](new-hire-onboarding/setup/) build the hands-on environment (BGs, gateway, team, users, Model Proxy) |
| [agent-fabric-actionability](agent-fabric-actionability/) | MuleSoft's Agent Fabric Actionability Workshop (Vogue Premiere): Agent Scanner, MCP Bridge, MCP policies, a broker with OBO, Model Proxy and Model Wallet. Tutorial in Japanese, credentials list, and what a host has to prepare. No `harness.yaml` yet |

Per-environment URLs and credentials stay outside git, in `~/.config/handson/<hands-on>/<env>/env.json`; [env_page.py](env_page.py) turns them into one HTML page per environment plus an index (`--shortcut` puts a link to it on the Windows desktop).

```bash
yc harness deploy <org> <env> new-hire-onboarding [suffix=<s>] [use-existing=<profile>:<bg>/<env>]
yc harness down   <org> <env> new-hire-onboarding [suffix=<s>]
```
