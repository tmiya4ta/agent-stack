# employee-db-app

Employee DB — an MCP server (Mule 4.11, Java 17, streamable HTTP). Registers an employee from a
name and an email address in SQLite and returns the issued employee ID.

Used by [networks/onboarding-employees](../../networks/onboarding-employees/), but it is an
ordinary Mule app and is built and deployed on its own.

## Endpoints and tools

| Path | What |
|---|---|
| `/mcp` | MCP streamable HTTP endpoint |
| `POST /employee`, `GET /employee` | The same table over plain HTTP |
| `/doc` | Reference page |

| Tool | Input |
|---|---|
| `register-employee` | `name`, `email` (both required) |

The table lives in a local SQLite file (`products.db`) and is recreated at startup, so the data
does not survive a restart or a redeploy. It is a demo backend, not a store.

## Build and deploy

No properties are required.

```bash
mvn -B package -DskipTests      # target/employee-db-app-1.0.6-mule-application.jar

yc deploy file <org> Sandbox <business-group-id> employee-db-app 1.0.6 \
  target/employee-db-app-1.0.6-mule-application.jar target=ch2:<cluster>
```

Bump `<version>` in `pom.xml` before re-publishing; Exchange does not accept the same version twice.
After deploying, set the app's base URL (without `/mcp`) as `employee-db-server{{-suffix}}.url`
in the network's `exchange.json`.
