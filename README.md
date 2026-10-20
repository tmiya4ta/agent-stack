# agent-stack

エージェントまわりの部品 (MCP サーバ、A2A エージェント、Agent Network、LLM・埋め込み・ベクトル検索のサービス) を
1 つのリポジトリで管理する。yc はここを読み、`harness.yaml` のある単位をビルド・publish・デプロイする ([docs/harness.md](docs/harness.md))。

## 構成

| 場所 | 中身 | 動かし方 |
|---|---|---|
| [a2a/](a2a/) | A2A エージェント (Mule) | yc (`harness.yaml`) |
| [mcp/](mcp/) | MCP サーバ (Mule) | yc (`harness.yaml`) |
| [networks/](networks/) | Agent Network (broker) | yc (`harness.yaml`) |
| [sets/](sets/) | 一緒に配備する単位の組 | `yc harness deploy <org> <env> <set>` |
| [max/](max/) | マックス証券 (架空) のデモ。max-core、max-oms (mulay)、DB、Salesforce の承認箱 | [k0/max-rtf](k0/max-rtf/) から RTF (k0) へ |
| [k0/](k0/) | kind クラスタ k0 の定義 (LLM、埋め込み、emu、stat、max の配備) | `kubectl --context kind-k0 apply` |
| [emu/](emu/) | k0 の emu (他社 API の真似) のソース (clay)。LLM と埋め込みの emu、`aisearch-server` (`ai-search.azure.emu`) | 各 `build.sh` (aisearch-server は `image.sh`) でイメージにして k0 へ |
| [docs/](docs/) | 仕様と調べた記録 | — |

## 単位の一覧 (`harness.yaml`)

| 名前 | kind | 使う network |
|---|---|---|
| [address-change-agent](a2a/address-change-agent/) | a2a | (単独。A2A コネクタの調べもの用) |
| [case-history-agent](a2a/case-history-agent/) | a2a | aml-investigation |
| [it-provisioning-agent](a2a/it-provisioning-agent/) | a2a | onboarding-employees |
| [office-concierge-agent](a2a/office-concierge-agent/) | a2a | onboarding-employees |
| [core-banking-mcp](mcp/core-banking-mcp/) | mcp | aml-investigation |
| [employee-db-app](mcp/employee-db-app/) | mcp | onboarding-employees |
| [screening-mcp](mcp/screening-mcp/) | mcp | aml-investigation |
| [onboarding-employees](networks/onboarding-employees/) | network | セット onboarding-demo |
| [aml-investigation](networks/aml-investigation/) | network | セット finance-demo |
| [max-surveillance](networks/max-surveillance/)、[max-operations](networks/max-operations/)、[max-support](networks/max-support/) | network | セット max-demo (MCP は k0 の max-core) |

## 決めごと

- モノレポ。タグはアプリごと (`<名前>/v<版>`)。
- CI は harness.yaml の検証、`mvn verify`、clay のテストだけにする。llama.cpp や Vulkan が要るビルドは手元の PC でやる。
- 大きなバイナリ (GGUF など) は git に入れない。取得元と置き場所だけを書く。
- 秘密はリポジトリに置かない。yc の変数 (`${var:…}`)、`~/.config/<名前>/env`、k8s の Secret から渡す。
- clay で足りないものは回避せず、clay 側に伝える。

## やること

- CI の雛形 (`.github/workflows/`)。
- `api/` の最初の単位。
- 旧 `~/mule/agents/agentic-harness` (Linux の PC、553MB) を消してよいか確かめる。そこから持ってきた chat-server と embeddings-server は
  k0 (`llm.ornith.model`、`embed.gte-qwen2.model`) に置き換わったので消した。中身は git の履歴 (`674fd46`) にある。
