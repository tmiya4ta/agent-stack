# harness.yaml

Every deployable unit in this repository has a `harness.yaml` at its root. yc reads only this
file to find, build, deploy and wire the unit; it does not infer anything from the directory
layout.

A unit is found by walking the repository for `harness.yaml`. Its `name` is the key other
units use to refer to it and the default deployment name.

## Common fields

```yaml
name: it-provisioning-agent     # unique in the repository
kind: a2a                       # llm | embedding | vector | mcp | a2a | api | network | set
runtime: mule                   # mule | host | agent-network | set
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

The pom `artifactId` must not equal any asset id a network publishes (the `registry` names in
`agent-network.yaml`). Both land in the same Business Group, and Exchange refuses a second
asset with the same id (`CreateExchangeAsset Unexpected error`, 500). Mule apps therefore end
in `-app` (`it-provisioning-agent-app`), while the deployment name stays the harness `name`.

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

## runtime: set

A set is a named selection of units provisioned together — for example everything a finance
demo needs. It lives under `sets/<name>/harness.yaml` and holds no code of its own.

```yaml
name: onboarding-demo
kind: set
runtime: set
units:                        # harness names; a network brings its members along
  - onboarding-employees
defaults:                     # used when the deploy command does not say otherwise
  target: ps:rootps
  gateway: ft1
  profile: onboarding-employees   # yc variables profile
  suffix: ""
use-existing:                 # do not deploy these; find them and use their URLs
  - from: tm:T1/Sandbox       # <yc login profile>:<business group>/<environment>
    units: [employee-db-app]  # omit to use whatever matching unit is found there
```

The Business Group and environment a set is deployed **into** are not part of the set; they
are given on the command line (`yc harness deploy <org> <env> <set>`), so one set can be
provisioned into several environments.

Deploying a set:

1. Expand `units`: every network adds its `members`. A unit reached twice is deployed once.
2. For each `use-existing` entry, log in with its profile and list that environment's
   applications (not agent networks). A unit matches an application whose name is the unit
   name (plus the suffix, if one is given) **or** whose Exchange reference is the unit's pom
   `artifactId`. The match must be running and have a public URL — another Business Group or
   private space cannot be reached over an internal URL.
3. Deploy the remaining non-network units and read their public URLs (known as soon as the
   deployment exists).
4. Fill every network's member tokens with the found or deployed URL plus the member's
   `endpoint`, then build, publish and deploy the networks.

Nothing found by a scan is written back into the repository. URLs are looked up again on
every deploy, so a re-run picks up an application that moved. A `use-existing` unit that is
not found, not running or has no public URL stops the deploy with a list of what is missing;
it is never deployed silently in its place.

The command line can add or replace `use-existing`:
`yc harness deploy T1 Sandbox onboarding-demo use-existing=tm:T1/Sandbox`.

Tearing down a set (`yc harness down <org> <env> <set>`) removes what the set deployed into
that environment — its networks and its own apps — and never touches a `use-existing` unit.

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
