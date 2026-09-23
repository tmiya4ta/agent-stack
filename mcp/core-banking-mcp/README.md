# core-banking-mcp

Core Banking — an MCP server (Mule 4.11, Java 17, streamable HTTP at `/mcp`) with **fictitious**
customers, accounts, transactions and transaction-monitoring alerts for the
[AML alert investigation](../../networks/aml-investigation/) demo. It also keeps the state of each
investigation conversation and the analyst's decisions.

The data lives in SQLite (`src/main/resources/seed.sql`) and is recreated at every start, so a
restart or redeploy resets the demo.

| Tool | Input | Returns |
|---|---|---|
| `get-alert` | `alertId` (`ALT-0915` or `0915`) | the alert, its account and the customer profile, or `{"found": false}` |
| `list-transactions` | `accountId` | the account's transactions, oldest first |
| `get-case` | `contextId` | the investigation state of a conversation (`step`: `new` / `awaiting_decision` / `decided`) |
| `save-case` | `contextId`, `alertId`, `step`, `recommendation` | saves the state after the memo is drafted |
| `record-decision` | `contextId`, `decision` (`close` / `file_str` / `hold`), `note` | records the analyst's decision, returns a decision ID |

## The three alerts

| Alert | Customer | What it looks like | Expected recommendation |
|---|---|---|---|
| ALT-0901 | 佐伯 美咲, salaried | a large deposit that is the employer's annual bonus, as last year | close |
| ALT-0915 | 黒田 隆, restaurant owner | eight cash deposits just under ¥500,000 in nine days, then ¥3.85M sent to Hong Kong | consider a report |
| ALT-0922 | 森本 翔太, company officer | ¥12M into a 16-day-old account; the news has an arrest of someone with the same name | hold for more checks |

## Build and deploy

No properties are required. The listener port is `${http.port}` (8081 unless set).

```bash
mvn -B package -DskipTests
yc harness deploy <org> <env> core-banking-mcp target=ps:<space>
```
