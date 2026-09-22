# 引き継ぎ: agentic-harness → agent-stack（2026-09-23）

このファイルは引っ越し直後の作業メモ。下の「やること」が終わったら消すか docs/ に移す。

## ここは何か

エージェントまわりの部品（LLM サーバ、埋め込み、ベクトル検索、MCP サーバ、A2A エージェント、API、Agent Network）を
1 つのリポジトリで管理する場所。GitHub（tmiya4ta/agent-stack の予定）に置き、そこから取ってビルド・publish・デプロイする。
いずれ yc（~/projects/yc）から一気通貫でできるようにする。

## 引っ越しで何をしたか

- ~/mule/agentic-harness から `aisearch-server/` `chat-server/` `embeddings-server/` をそのままコピーした（build/ と build-llama/ も含む）。
  **.git はコピーしていない**。旧リポジトリの唯一のコミット ee4b623 に、削除した Mule 版 embedding-harness の 17MB の .bin が入っていたので、
  履歴は作り直す（まだ一度も push していない）。
- `embedding-harness`（Mule 版の埋め込みエミュレーター）は削除した（ユーザー了承済み）。
- 旧 ~/mule/agentic-harness はまだ残してある。embeddings-server の README / server.clay / smoke_test.py に未コミットの変更があったが、
  それもコピー済み。こちらで問題なければ旧ディレクトリは消してよい（ユーザーに確認してから）。
- 動いている systemd --user サービス（chat-server / embeddings-server / aisearch-server）は `~/.local/lib/<name>/` の実行ファイルと
  `~/.config/<name>/env` を使っていて、ソースの場所には依存していない。引っ越しで止まったりはしない。
- Claude のメモリは `~/.claude/projects/-home-myst-mule-agent-stack/memory/` にコピー済み（目的のメモは agent-stack-purpose.md に更新）。

## 合意した設計

### ディレクトリ: 1 段目は kind（何をするか）

kind は Agent Network の接続種別（`llm://` `mcp://` `a2a://`）にそろえる。network が参照する部品を yc が名前で解決できるようにするため。

```
agent-stack/
├── README.md                 # カタログ（harness.yaml から自動生成）
├── llm/chat-server/          # host: clay + llama.cpp（Ornith 1.5 35B、:8898）
├── embedding/embeddings-server/  # host: clay + llama.cpp（gte-Qwen2-1.5B、:8896）
├── vector/aisearch-server/   # host: clay（Azure AI Search エミュ、:8897）
├── mcp/  a2a/  api/          # これから（主に Mule）
├── networks/                 # tmiya4ta/agent-networks を統合（agent-network.yaml / .agent）
├── shared/
│   ├── llama/                # llama.cpp の静的ビルド（chat と embeddings で共用）
│   ├── mule-parent/          # 共通 parent pom、DataWeave モジュール
│   └── clay/                 # 共通 clay ライブラリ
└── .github/workflows/
```

### 動かし方は各アプリの `harness.yaml` に書く

yc はディレクトリ構造を推測せず、これだけを読む。runtime は `mule`（CH2 / RTF）か `host`（clay 実行ファイル + systemd --user）。

```yaml
name: embeddings-server
kind: embedding            # llm | embedding | vector | mcp | a2a | api | network
runtime: host              # host | mule
interface: openai-embeddings/v1
version: 0.3.0
build: ./build.sh
test: ./smoke_test.py
deploy:
  host:
    unit: embeddings-server.service
    install: ./install.sh
    env: ~/.config/embeddings-server/env   # 秘密は外。パスだけ書く
expose:
  url: https://embeddings.theorems.io
  relay: /emb/                             # CloudHub リレー経由のパス
requires: [shared/llama]
```

Mule の場合は `deploy.mule: {target: ch2|rtf, env: Sandbox, properties: config/sandbox.yaml}`、`exchange: {publish: true}`
（groupId は pom / exchange.json から読む）。

### その他の決めごと

- モノレポ、タグはアプリごと（`embeddings-server/v0.3.0`）。yc は tag の zip を取れば特定版をビルドできる
  （yc の repos.clay は今ブランチの zip を `~/.yc/repos/<name>/` に展開している。これを流用）。
- CI は harness.yaml の検証、`mvn verify`、clay のテストだけ。llama.cpp / Vulkan が要るビルドはこの PC の yc でやる。
- 大きなバイナリは git に入れない（Git LFS か Release アセット）。GGUF は harness.yaml に取得元と置き場所だけ書く。
- 秘密はリポジトリに置かない。

## やること（順番に）

1. ~~git init して最初のコミットを作る~~ **済**。
2. **kind 別に移す**: `llm/chat-server`、`embedding/embeddings-server`、`vector/aisearch-server`。
   移したら各 build.sh / install.sh / README の相対パスを直す。特に
   **chat-server/build.sh の既定 `LLAMA_BUILD=$HERE/../embeddings-server/build-llama`** は壊れるので、
   `shared/llama/`（build スクリプト + ビルド成果物は ignore）に出して両方から使う。
   移した後に 3 つとも build.sh が通ることを確認する（サービスの入れ替えはユーザーに聞いてから）。
3. **各アプリに harness.yaml を付ける**（上の形。ポート・公開名・env の場所は各 README にある）。
4. ~~networks/ に tmiya4ta/agent-networks を統合~~ **済（2026-09-23）**。中身だけを履歴なしでコピーした（旧リポジトリは削除する）。残り: yc の repos.clay の `default-url`（`https://github.com/tmiya4ta/agent-networks`）と
   config.clay の言及を agent-stack の `networks/` に向け替える（yc リポジトリ側の作業）。旧 GitHub リポジトリはユーザーが削除する。
   2026-09-23: onboarding-employees のメンバー Mule アプリ 3 つを `a2a/it-provisioning-agent`、`a2a/office-concierge-agent`、
   `mcp/employee-db-app` に出した（各 README に yc deploy file での単体デプロイ手順、harness.yaml 付き）。
   network フォルダの `apps/` はそれらへのシンボリックリンク。network のビルドは exchange.json / agent-network.yaml / brokers しか
   梱包しないので影響しない。
5. ~~GitHub に push~~ **済（2026-09-23、git@github-tmiya4ta:tmiya4ta/agent-stack.git の main）**。CI の雛形はまだ。
6. **yc に `harness list / build / publish / deploy` を足す**（まず runtime: host から）。これは yc リポジトリ側の作業。

## 参考

- 各アプリの README に構成図・エンドポイント・ビルドの注意（clay の版、RPATH、-DCLAY_SERVER=threaded など）がある。
- clay で足りないものは回避せず clay 側に伝える方針（メモリ build-on-this-pc-with-clay）。
