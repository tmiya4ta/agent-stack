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
| `llm.ornith.model` | llama-server + Ornith 1.5 35B (Q4_K_M)。OpenAI 互換 (`/v1/chat/completions`、`/v1/responses`)。モデル名 `ornith-1.5-35b` | 内蔵 GPU | 動いている (公開はまだ) |
| `embed.gte-qwen2.model` | llama-server + gte-Qwen2-1.5B-instruct (q8_0、1536 次元)。`/v1/embeddings`。モデル名 `gte-qwen2-1.5b` | 内蔵 GPU | 動いている (公開はまだ) |
| `llm.openai.emu` | OpenAI の LLM の真似 (Responses API と Chat Completions) | `llm.ornith.model` | これから |
| `llm.gemini.emu` | Gemini の真似 (`generateContent`) | `llm.ornith.model` | これから |
| `embed.openai.emu` | OpenAI の埋め込み (`/v1/embeddings`) | `embed.gte-qwen2.model` | これから |
| `embed.ollama.emu` | Ollama の埋め込み (`/api/embeddings`、`/api/embed`) | `embed.gte-qwen2.model` | これから |
| `embed.azure.emu` | Azure OpenAI の埋め込み | `embed.gte-qwen2.model` | 要るときに |
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
  `./secrets.sh <名前空間> <名前>` が `~/.config/<名前>/env` の `API_KEY` (無ければ作る、0600) から Secret `<名前>-api-key` を作る。
- **公開**: HTTPRoute (`parentRefs: rtf/cluster-gateway`、hostnames は `.dev` だけ)。3 階層の名前の証明書は Caddy の on-demand TLS
  (配線盤の `/ask` が HTTPRoute にある名前だけを許す)。新しい名前は初回だけ証明書の取得に 40 秒ほどかかる。

## llama-server の注意

- 引数の値は別の引数で渡す。`--model=/models/X_Y.gguf` の形にすると、値の中の `_` まで `-` に変えられてファイル名が壊れる。
- `--attention non-causal` は `llama-embedding` 専用で、llama-server では受け付けない。gte-Qwen2 の non-causal は GGUF の
  `qwen2.attention.causal = false` で決まる (`~/models/gguf` のファイルには入っている)。
- Responses API (`/v1/responses`) は `text.format` の json_schema を無視して文章を返す (2026-10-11、イメージの digest は各 yaml)。
  Chat Completions の `response_format` (json_schema) は効く。broker は Responses API で構造化出力を使うので、`llm.openai.emu` で変換する。

## 確かめたこと (2026-10-11)

- `llm-ornith-model`: 鍵なしは 401。生成は 1 秒に約 24 トークン。Chat Completions と Responses API の両方で、ツール呼び出しが正しく返る。
- `embed-gte-qwen2-model`: 前の embeddings-server (元の PyTorch 実装とコサイン 0.9993 以上で一致) と、日本語・英語・長文でコサイン 0.9997 以上。
