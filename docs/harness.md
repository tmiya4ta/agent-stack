# harness.yaml

Every deployable unit in this repository has a `harness.yaml` at its root. yc reads only this
file to find, build, deploy and wire the unit; it does not infer anything from the directory
layout.

A unit is found by walking the repository for `harness.yaml`. Its `name` is the key other
units use to refer to it and the default deployment name.

## Common fields

```yaml
name: it-provisioning-agent     # unique in the repository
kind: a2a                       # llm | embedding | vector | mcp | a2a | api | network
runtime: mule                   # mule | host | agent-network
version: 1.7.8                  # informational; for mule the pom <version> wins
```

## runtime: mule

```yaml
build: mvn -B package -DskipTests
artifact: target/*-mule-application.jar   # glob, relative to the unit
endpoint: /                  # path appended to the app's public URL to get the URL
                             # other units should call (A2A: "/", MCP: "" since the
                             # network appends /mcp itself)
deploy:
  mule:
    target: ch2              # default target kind; the actual target is chosen at deploy time
    properties:              # application properties, set on every deploy
      agent.url: ${self.url}
      llm.proxy.host: ${var:llm-host}
    secure:                  # secure application properties
      llm.apiKey: ${var:llm-api-key}
```

The Exchange coordinates come from `pom.xml` (`artifactId`, `version`); the groupId is the
Business Group being deployed into, not the pom's placeholder `com.mycompany`.

## runtime: agent-network

```yaml
name: onboarding-employees
kind: network
runtime: agent-network
members:                     # {{token}} in exchange.json -> the unit whose URL fills it
  it-provisioning-agent-url: it-provisioning-agent
  office-concierge-agent-url: office-concierge-agent
  employee-db-app-url: employee-db-app
```

The project itself (`exchange.json`, `agent-network.yaml`, `brokers/`) sits next to this file.
Tokens not listed under `members` (`{{llm-base-url}}`, `{{llm-api-key}}`, …) come from a yc
variables profile. `{{business-group-id}}` is the Business Group deployed into, and
`{{-suffix}}` / `{{_suffix}}` are the deployment suffix (empty for a plain deployment).

## runtime: host

A clay executable run as a `systemd --user` unit on this PC.

```yaml
build: ./build.sh
test: ./smoke_test.py
deploy:
  host:
    unit: embeddings-server.service
    install: ./install.sh
    env: ~/.config/embeddings-server/env    # secrets live there; only the path is recorded
expose:
  url: https://embeddings.theorems.io
```

## Value references

| Form | Resolves to |
|---|---|
| `${self.url}` | This unit's own public URL once deployed (no trailing slash) |
| `${unit:<name>.url}` | Another unit's URL, including its `endpoint` |
| `${var:<name>}` | A value from the chosen yc variables profile |
| anything else | Used literally |

A reference that cannot be resolved stops the deploy; it is never sent as an empty string.

Secrets are never written into this repository — only `${var:…}` references to them.
