# screening-mcp

Screening — an MCP server (Mule 4.11, Java 17, streamable HTTP at `/mcp`) with **fictitious**
watch lists (sanctions, foreign PEPs, the bank's own list of counterparties to watch) and news
articles, for the [AML alert investigation](../../networks/aml-investigation/) demo.

Names are compared after dropping spaces, case, 株式会社 and anything in parentheses. A partial
match is reported as `"match": "partial"` together with whether the birth date matches, so a
namesake can be told from a real hit — the same judgement an analyst makes with a real
screening system.

| Tool | Input | Returns |
|---|---|---|
| `screen-name` | `name`, optional `birthDate` | list hits with `match` (exact / partial) and `birthDateMatch` |
| `search-news` | `name` | articles that mention the name |

The data lives in SQLite (`src/main/resources/seed.sql`) and is recreated at every start.

```bash
mvn -B package -DskipTests
yc harness deploy <org> <env> screening-mcp target=ps:<space>
```
