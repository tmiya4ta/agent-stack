# agent-stack

エージェントまわりの部品 (MCP サーバ、A2A エージェント、Agent Network、LLM・埋め込み・ベクトル検索のサービス) を
1 つのリポジトリで管理する。yc はここを読み、`harness.yaml` のある単位をビルド・publish・デプロイする ([docs/harness.md](docs/harness.md))。

## 構成

```
agent-stack/
├── demos/       見せるためのデモ。セット・Agent Network・メンバーの Mule アプリを 1 か所に
│   ├── suspicious-transaction-review/   銀行の疑わしい取引のアラート調査 (AML = マネーロンダリング対策)
│   └── max-securities/                  マックス証券 (架空のネット証券)。売買審査・口座開設・問い合わせ
├── handson/     ハンズオン (作りはデモと同じ)
│   └── new-hire-onboarding/             新入社員の受け入れ
├── ai/          k0 で動く AI のサービス。ソースと k8s の yaml を同じフォルダに
│   ├── model/        real (本物のモデル)、emu (他社の API の真似)、stat (統計的な実装)
│   └── vector/       emu (Azure AI Search の真似)
├── labs/        どこにも属さない調べもの
└── docs/        仕様と調べた記録
```

| 場所 | 動かし方 |
|---|---|
| [demos/](demos/)、[handson/](handson/) | `yc harness deploy <org> <env> <セット>`。セットの名前はフォルダの名前と同じ。max-core / max-oms は [demos/max-securities/deploy](demos/max-securities/deploy/) から RTF (k0) へ |
| [ai/](ai/) | 各 `build.sh` (aisearch-server は `image.sh`) でイメージにし、`kubectl --context kind-k0 apply` |
| [labs/](labs/) | yc (`harness.yaml`) |

デモとハンズオンのフォルダの名前は、セットの名前と同じにする。その中のフォルダは、中の単位の harness の `name`
(k0 のものはプログラムの名前) と同じにする。単位の名前は配備の名前にもなるので、配備したあとは変えない
(`yc harness down` で消せなくなる)。

## 単位の一覧 (`harness.yaml`)

| 名前 | kind | 中身 |
|---|---|---|
| [suspicious-transaction-review](demos/suspicious-transaction-review/) | set | 疑わしい取引のアラート調査のデモ |
| ├ [aml-investigation](demos/suspicious-transaction-review/aml-investigation/) | network | アラートの一次調査。材料を集めて下書きし、判断は担当者 |
| ├ [case-history-agent](demos/suspicious-transaction-review/case-history-agent/) | a2a | 似た過去の調査と、その結論を探す |
| ├ [core-banking-mcp](demos/suspicious-transaction-review/core-banking-mcp/) | mcp | 顧客・口座・取引・アラート (架空) |
| └ [screening-mcp](demos/suspicious-transaction-review/screening-mcp/) | mcp | 制裁リストなどの照合とニュース検索 (架空) |
| [max-securities](demos/max-securities/) | set | マックス証券のデモ |
| └ [max-surveillance](demos/max-securities/max-surveillance/)、[max-operations](demos/max-securities/max-operations/)、[max-support](demos/max-securities/max-support/) | network | 売買審査、口座開設、問い合わせ。MCP は k0 の max-core |
| [new-hire-onboarding](handson/new-hire-onboarding/) | set | 新入社員の受け入れのハンズオン |
| ├ [onboarding-employees](handson/new-hire-onboarding/onboarding-employees/) | network | 3 つの業務システムをまとめて呼ぶ broker |
| ├ [it-provisioning-agent](handson/new-hire-onboarding/it-provisioning-agent/)、[office-concierge-agent](handson/new-hire-onboarding/office-concierge-agent/) | a2a | PC の貸し出し、入館証と社内の決まり |
| └ [employee-db-app](handson/new-hire-onboarding/employee-db-app/) | mcp | 社員の登録 |
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
