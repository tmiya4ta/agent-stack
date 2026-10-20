# agent-stack

エージェントまわりの部品 (MCP サーバ、A2A エージェント、Agent Network、LLM・埋め込み・ベクトル検索のサービス) を
1 つのリポジトリで管理する。yc はここを読み、`harness.yaml` のある単位をビルド・publish・デプロイする ([docs/harness.md](docs/harness.md))。

## 構成

```
agent-stack/
├── demos/       デモごとに、セット・Agent Network・メンバーの Mule アプリを 1 か所に
│   ├── onboarding/   新入社員の受け入れ (セット onboarding-demo)
│   ├── finance/      AML アラートの調査 (セット finance-demo)
│   └── max/          マックス証券 (架空。セット max-demo、max-core / max-oms と k0 への配備)
├── ai/          k0 で動く AI のサービス。ソースと k8s の yaml を同じフォルダに
│   ├── model/        real (本物のモデル)、emu (他社の API の真似)、stat (統計的な実装)
│   └── vector/       emu (Azure AI Search の真似)
├── labs/        どのデモにも属さない調べもの
└── docs/        仕様と調べた記録
```

| 場所 | 動かし方 |
|---|---|
| [demos/](demos/) | `yc harness deploy <org> <env> <セット>`。max-core / max-oms は [demos/max/deploy](demos/max/deploy/) から RTF (k0) へ |
| [ai/](ai/) | 各 `build.sh` (aisearch-server は `image.sh`) でイメージにし、`kubectl --context kind-k0 apply` |
| [labs/](labs/) | yc (`harness.yaml`) |

フォルダの名前は、中の単位の harness の `name` (k0 のものはプログラムの名前) と同じにする。

## 単位の一覧 (`harness.yaml`)

| 名前 | kind | 場所 |
|---|---|---|
| onboarding-demo | set | [demos/onboarding](demos/onboarding/) |
| ├ [onboarding-employees](demos/onboarding/onboarding-employees/) | network | |
| ├ [it-provisioning-agent](demos/onboarding/it-provisioning-agent/)、[office-concierge-agent](demos/onboarding/office-concierge-agent/) | a2a | |
| └ [employee-db-app](demos/onboarding/employee-db-app/) | mcp | |
| finance-demo | set | [demos/finance](demos/finance/) |
| ├ [aml-investigation](demos/finance/aml-investigation/) | network | |
| ├ [case-history-agent](demos/finance/case-history-agent/) | a2a | |
| └ [core-banking-mcp](demos/finance/core-banking-mcp/)、[screening-mcp](demos/finance/screening-mcp/) | mcp | |
| max-demo | set | [demos/max](demos/max/) |
| └ [max-surveillance](demos/max/max-surveillance/)、[max-operations](demos/max/max-operations/)、[max-support](demos/max/max-support/) | network | MCP は k0 の max-core |
| [address-change-agent](labs/address-change-agent/) | a2a | 単独。A2A コネクタの調べもの用 |

## 決めごと

- モノレポ。タグはアプリごと (`<名前>/v<版>`)。
- CI は harness.yaml の検証、`mvn verify`、clay のテストだけにする。llama.cpp や Vulkan が要るビルドは手元の PC でやる。
- 大きなバイナリ (GGUF など) は git に入れない。取得元と置き場所だけを書く。
- 秘密はリポジトリに置かない。yc の変数 (`${var:…}`)、`~/.config/<名前>/env`、k8s の Secret から渡す。
- clay で足りないものは回避せず、clay 側に伝える。

## やること

- CI の雛形 (`.github/workflows/`)。
- API (kind: api) の最初の単位。
- 旧 `~/mule/agents/agentic-harness` (Linux の PC、553MB) を消してよいか確かめる。そこから持ってきた chat-server と embeddings-server は
  k0 (`llm.ornith.model`、`embed.gte-qwen2.model`) に置き換わったので消した。中身は git の履歴 (`674fd46`) にある。
