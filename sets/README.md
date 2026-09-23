# sets

Named selections of units provisioned together with one command. Each folder holds only a
`harness.yaml`; see [docs/harness.md](../docs/harness.md#runtime-set).

| Set | What it brings up |
|---|---|
| [onboarding-demo](onboarding-demo/) | The employee onboarding network and its three member apps |

```bash
yc harness deploy <org> <env> onboarding-demo [suffix=<s>] [use-existing=<profile>:<bg>/<env>]
yc harness down   <org> <env> onboarding-demo [suffix=<s>]
```
