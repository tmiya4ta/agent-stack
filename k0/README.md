# k0 の AI のサービス

Agent Fabric と Agent アプリの開発に使う LLM、埋め込み、ベクトル DB を、kind クラスタ k0 で動かす。
定義はここに置き、反映はこのディレクトリから `kubectl --context kind-k0 apply` で行う (theorems-infra のインフラのセッションと合意済み)。

## 名前の規則

公開名は `<何か>.<相手かモデル>.<分類>.theorems.dev`。右から読む。

| 分類 (名前空間) | 意味 |
|---|---|
| `model` (`ai-model`) | モデルを動かすエンジン (llama-server、内蔵 GPU) |
| `emu` (`ai-emu`) | 他社の API の真似。中身は `ai-model` のエンジン |
| `stat` (`ai-stat`) | モデルを使わない統計的な実装 |

Deployment、Service、Secret、`~/.config/<名前>/env` は、公開名のラベルを `-` でつないだ名前にする
(`llm.ornith.model` → `llm-ornith-model`)。k8s の Service の名前にドットは使えないため。

## 一覧

| 公開名 (`.theorems.dev`) | 何か | 後ろ | 状態 |
|---|---|---|---|
| `llm.ornith.model` | llama-server + Ornith 1.5 35B (Q4_K_M)。OpenAI 互換 (`/v1/chat/completions`、`/v1/responses`)。モデル名 `ornith-1.5-35b` | 内蔵 GPU | 動いている。HTTPRoute あり |
| `embed.gte-qwen2.model` | llama-server + gte-Qwen2-1.5B-instruct (q8_0、1536 次元)。`/v1/embeddings`。モデル名 `gte-qwen2-1.5b` | 内蔵 GPU | 動いている。HTTPRoute あり |
| `llm.openai.emu` | OpenAI の LLM の真似 (Responses API と Chat Completions)。ソースは `emu/llm-openai-emu` | `llm.ornith.model` | 動いている。HTTPRoute あり |
| `llm.gemini.emu` | Gemini の真似 (`generateContent`) | `llm.ornith.model` | これから |
| `embed.openai.emu` | OpenAI の埋め込み (`/v1/embeddings`)。ソースは `emu/embed-emu` (FLAVOR=openai) | `embed.gte-qwen2.model` | 動いている。HTTPRoute あり |
| `embed.azure.emu` | Azure OpenAI の埋め込み (`/openai/deployments/<名前>/embeddings`)。同じプログラム (FLAVOR=azure) | `embed.gte-qwen2.model` | 動いている。HTTPRoute あり |
| `embed.ollama.emu` | Ollama の埋め込み (`/api/embed`、`/api/embeddings`、`/api/tags`)。同じプログラム (FLAVOR=ollama) | `embed.gte-qwen2.model` | 動いている。HTTPRoute あり |
| `ai-search.azure.emu` | Azure AI Search の真似 (ベクトル DB) | 自前 (PVC) | これから |
| `llm.tfidf.stat` | 統計的な LLM (agent-harness の方式、mulay で動かす) | なし | これから |
| `embed.hash512.stat` | 統計的な埋め込み (ハッシュ、512 次元、mulay で動かす) | なし | これから |

## 置き方

- **GPU**: device plugin (kube-system の generic-device-plugin、定義は theorems-infra の `cluster/gpu/`) の `squat.ai/dri` を 1 つ要求する。
  Pod の `supplementalGroups: [106]` (ノードの中の renderD128 の gid)。特権も hostPath の `/dev/dri` も使わない。
  k0-worker と k0-worker2 に 4 つずつあり、同じ iGPU (Radeon 780M、メインメモリと共用の約 32GB) を分け合う。
- **モデル**: PVC `ai-model/models` (local-path、k0-worker)。`ai-model/load-models.sh` が `~/models/gguf` から docker cp で入れる。
  エンジンはモデルの PVC のある k0-worker に固定する。
- **API キー**: 全サービスに付ける (Gateway の手前に認証は無く、インターネットから誰でも届く)。
  llama-server は鍵なしでも `/` (Web UI の静的ファイル) と `/health` だけは返す。API は全部 401。
  `./secrets.sh <名前空間> <名前>` が `~/.config/<名前>/env` の `API_KEY` (無ければ作る、0600) から Secret `<名前>-api-key` を作る。
- **公開**: HTTPRoute (`parentRefs: rtf/cluster-gateway`、hostnames は `.dev` だけ。`timeouts` も書く、下の「長い生成」)。3 階層の名前の証明書は Caddy の on-demand TLS
  (配線盤の `/ask` が HTTPRoute にある名前だけを許す)。新しい名前は初回だけ証明書の取得に 40 秒ほどかかる。

## llama-server の注意

- 引数の値は別の引数で渡す。`--model=/models/X_Y.gguf` の形にすると、値の中の `_` まで `-` に変えられてファイル名が壊れる。
- `--attention non-causal` は `llama-embedding` 専用で、llama-server では受け付けない。gte-Qwen2 の non-causal は GGUF の
  `qwen2.attention.causal = false` で決まる (`~/models/gguf` のファイルには入っている)。
- Responses API (`/v1/responses`) は `text.format` の json_schema を無視して文章を返す (2026-10-11、イメージの digest は各 yaml)。
  Chat Completions の `response_format` (json_schema) は効く。broker は Responses API で構造化出力を使うので、`llm.openai.emu` で変換する。
- 埋め込みの値は、同じ文でも直前の要求によって 2 通りに分かれる (コサイン 0.99975 ほどの差。`cache_prompt: false` でも変わらない)。
  Vulkan の計算の順が直前の状態で変わるためと思われる。検索には効かない大きさ。比べるときは完全一致ではなくコサインで見る。

## 長い生成とタイムアウト

共有 Gateway (cloud-provider-kind の Envoy) の既定は 15 秒で 504。インフラが v0.10.0 にパッチを当て、HTTPRoute の
`rules[].timeouts.request` が効くようにした (2026-10-12、theorems-infra の `cluster/cloud-provider-kind/`。0s は無制限)。
AI の HTTPRoute には全部 `timeouts: {request: 900s}` を書く。書かないと 15 秒で切れる。
埋め込みの大きな束も 15 秒を超える (エンジンは 1 本で順に処理し、1 秒に約 1000 トークン。600 件 × 186 トークンで 113 秒)。

## Mule のコネクタから埋め込みを使う

MuleSoft Vectors コネクタ (1.0.0) の埋め込みの接続のうち、ここに向けられるのは 2 つ (jar の中で確かめた)。

| 接続 | 設定 | 呼ばれる所 |
|---|---|---|
| Azure OpenAI | endpoint `https://embed.azure.emu.theorems.dev`、apiKey は `embed-azure-emu` の鍵、deployment と apiVersion は何でもよい | `POST {endpoint}/openai/deployments/{deployment}/embeddings?api-version=..` (ヘッダ `api-key`) |
| Ollama | baseUrl `https://embed.ollama.emu.theorems.dev/k/<embed-ollama-emu の鍵>` | `GET {baseUrl}/api/tags` (接続の確認)、`POST {baseUrl}/api/embeddings` (`{model, prompt}`、1 件ずつ) |

- OpenAI の接続は apiKey しか持たず、行き先が `https://api.openai.com` に固定なので使えない。
- Ollama の接続は base URL しか持たず、鍵のヘッダを付けられない。そこで鍵をパスの前置き `/k/<鍵>` で渡す
  (鍵は `secrets.sh` が英数字だけで作る。base URL の末尾に `/` を付けても通る)。
  鍵が URL に入るので、`embed-emu` は URI をログに出さない (Caddy と Envoy のアクセスログには残りうる)。

## embed-emu の作り (`emu/embed-emu`)

- 1 つのイメージを FLAVOR (openai、azure、ollama) で 3 つの Deployment にする。鍵は Bearer、`api-key` ヘッダ、`/k/<鍵>` のどれでも通る。
- `dimensions` は 1536 のときだけ受け、他は 400 (gte-Qwen2 は次元の切り詰めを前提に訓練されていない)。
- 上流には 128 件 (BATCH) ずつ送り、応答をつなぐ。clay.http のクライアントは応答が 8 MiB を超えると失敗するため
  (1536 次元の float で約 250 件)。clay に上限を変える項目を頼んである (2026-10-12)。1 回で済む要求は本文をそのまま返す。
- Ollama の違い: `truncate` は効かない (8192 トークンを超えると 400)。`GET /` は "Ollama is running" ではなくこのサービスの説明。
- テストは `clay test test` (変換は `embconv.clay`、テストからは symlink で読む)。
- 中身を変えたら VERSION を上げ、yaml の image も上げる (imagePullPolicy が IfNotPresent なので、同じ版の作り直しは Pod に届かない)。
- イメージの PID 1 は tini。Clay のサーバーが PID 1 だと SIGTERM を受けず、Pod の入れ替えで 30 秒待たされる。

## 確かめたこと (2026-10-11)

- `llm-ornith-model`: 鍵なしは 401。生成は 1 秒に約 24 トークン。Chat Completions と Responses API の両方で、ツール呼び出しが正しく返る。
- `embed-gte-qwen2-model`: 前の embeddings-server (元の PyTorch 実装とコサイン 0.9993 以上で一致) と、日本語・英語・長文でコサイン 0.9997 以上。

## 確かめたこと (2026-10-12)

- 公開名 (`https://llm.openai.emu.theorems.dev`、`https://llm.ornith.model.theorems.dev`) に Let's Encrypt の証明書が付き、鍵なしは 401。
- `llm.openai.emu` の公開名で、900 トークン (約 40 秒) の生成が Chat Completions で 200、Responses API のストリーミングで
  `response.completed` まで流れる。
- 埋め込みの 3 つの口: 公開名に証明書が付き、各社の形の 401 を返す。OpenAI (float と base64)、Azure (deployment と `api-key`)、
  Ollama (`/api/embed`、`/k/<鍵>/api/embeddings`) の返すベクトルが、エンジンの値と順序どおりにコサイン 0.9997 以上で合う。
  `embed.openai.emu` に 600 件を一度に送り、113 秒で 600 件 (19.6 MB) が index の順に返る。
