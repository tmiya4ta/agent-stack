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
| `llm.gemini.emu` | Gemini API の真似 (`generateContent`、`streamGenerateContent`、`countTokens`)。ソースは `emu/llm-gemini-emu` | `llm.ornith.model` | 動いている。HTTPRoute あり |
| `embed.openai.emu` | OpenAI の埋め込み (`/v1/embeddings`)。ソースは `emu/embed-emu` (FLAVOR=openai) | `embed.gte-qwen2.model` | 動いている。HTTPRoute あり |
| `embed.azure.emu` | Azure OpenAI の埋め込み (`/openai/deployments/<名前>/embeddings`)。同じプログラム (FLAVOR=azure) | `embed.gte-qwen2.model` | 動いている。HTTPRoute あり |
| `embed.ollama.emu` | Ollama の埋め込み (`/api/embed`、`/api/embeddings`、`/api/tags`)。同じプログラム (FLAVOR=ollama) | `embed.gte-qwen2.model` | 動いている。HTTPRoute あり |
| `ai-search.azure.emu` | Azure AI Search の真似 (ベクトル DB)。ソースは `aisearch-server` | 自前 (PVC `ai-search-data`) | 動いている。HTTPRoute あり |
| `llm.tfidf.stat` | 統計的な LLM (`/v1/chat/completions`、agent-harness の `stat::agent`)。mulay の `templates/stat-models` (stat.serve=llm) | なし | 動いている。HTTPRoute あり |
| `embed.hash512.stat` | 統計的な埋め込み (512 次元。OpenAI、Azure、Ollama の形)。同じアプリ (stat.serve=embed) | なし | 動いている。HTTPRoute あり |

## 置き方

- **GPU**: device plugin (kube-system の generic-device-plugin、定義は theorems-infra の `cluster/gpu/`) の `squat.ai/dri` を 1 つ要求する。
  Pod の `supplementalGroups: [106]` (ノードの中の renderD128 の gid)。特権も hostPath の `/dev/dri` も使わない。
  k0-worker と k0-worker2 に 4 つずつあり、同じ iGPU (Radeon 780M、メインメモリと共用の約 32GB) を分け合う。
- **モデル**: PVC `ai-model/models` (local-path、k0-worker)。`ai-model/load-models.sh` が `~/models/gguf` から docker cp で入れる。
  エンジンはモデルの PVC のある k0-worker に固定する。
- **API キー**: 全サービスに付ける (Gateway の手前に認証は無く、インターネットから誰でも届く)。
  llama-server は鍵なしでも `/` (Web UI の静的ファイル) と `/health` だけは返す。API は全部 401。
  `./secrets.sh <名前空間> <名前>` が `~/.config/<名前>/env` の `API_KEY` (無ければ作る、0600) から Secret `<名前>-api-key` を作る。
  Secret のキーは `api-key` (鍵そのもの) と `api-key.properties` (`api.key=<鍵>`。Mule のアプリが configuration-properties で読む)。
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

MuleSoft Vectors コネクタ (1.0.0) の埋め込みの接続のうち、ここに向けられるのは 2 つ (jar の中で確かめ、実 Mule 4.11.3 で動かした)。

| 接続 | 設定 | 呼ばれる所 |
|---|---|---|
| Azure OpenAI | endpoint `https://embed.azure.emu.theorems.dev`、apiKey は `embed-azure-emu` の鍵、deployment と apiVersion は何でもよい | `POST {endpoint}/openai/deployments/{deployment}/embeddings?api-version=..` (ヘッダ `api-key`) |
| Ollama | baseUrl `https://embed.ollama.emu.theorems.dev/k/<embed-ollama-emu の鍵>` | `GET {baseUrl}/api/tags` (接続の確認)、`POST {baseUrl}/api/embeddings` (`{model, prompt}`、1 件ずつ) |

- OpenAI の接続は apiKey しか持たず、行き先が `https://api.openai.com` に固定なので使えない。
- 保存先は `ai-search-connection` (url `https://ai-search.azure.emu.theorems.dev`、apiKey は `ai-search-azure-emu` の鍵)。
  アプリの pom で、コネクタの additionalDependencies に `dev.langchain4j:langchain4j-azure-ai-search:1.1.0-beta7` を足す
  (無いと `NoClassDefFoundError: com/azure/core/exception/HttpResponseException`)。
- Ollama の接続は base URL しか持たず、鍵のヘッダを付けられない。そこで鍵をパスの前置き `/k/<鍵>` で渡す
  (鍵は `secrets.sh` が英数字だけで作る。base URL の末尾に `/` を付けても通る)。
  鍵が URL に入るので、`embed-emu` は URI をログに出さない (Caddy と Envoy のアクセスログには残りうる)。

## Agent Network の broker から使う (2026-10-12、T1/Sandbox の aml-investigation-s0 で確かめた)

broker (v2) の LLM の接続を `https://llm.openai.emu.theorems.dev/v1` (platform AzureOpenai、apiKey は llm-openai-emu の鍵) に
向けると、broker は Responses API を非ストリーミングで呼ぶ。毎回 `tools` と `text.format` (json_schema、strict) の両方と
`reasoning.effort: low`、`store: false` を送り、道具を呼んだ後は `{"role":"assistant","content":""}` と前のノードの答え
(assistant) を input に入れてくる。そのままでは llama-server が通らないので、次のように埋めた。

| 起きたこと | llama-server の返事 | 直し |
|---|---|---|
| tools と text.format が両方ある | 400 failed to parse grammar | `llm.openai.emu` が 2 段に分ける (道具だけ → 文の答えならスキーマだけで聞き直す) |
| content が文字列の assistant の項目 | 400 Cannot determine type of 'item' | 空なら外し、中身があれば `type: message` + `output_text` にする |
| 最後が assistant の項目 | 400 Failed to initialize samplers: std::exception | エンジンに `--no-prefill-assistant` (続きを書かない。OpenAI と同じ) |
| 考えると 1 回 10 秒を超える | — | `reasoning.effort` が none / minimal / low なら考えない (`THINK_OFF`)。OpenAI の low とは違う |

- 出口のゲートウェイ ft1 の `upstreamResponseTimeout` が 15 秒で、長い生成 (一覧の表、調査メモ) が 504
  (broker のログに `upstream request timeout`) になった。API インスタンスの `responseTimeout` は LLM の出口には効かない。
  ユーザーの了承を得て ft1 を 300 秒にした (2026-10-12。gatewaymanager の PUT。プラグインが新しく作るゲートウェイは 60 秒)。
- **結論 (2026-10-12)**: 仕組みとしては通る (一覧の会話は COMPLETED)。ただ AML の調査 (道具 3 つ + A2A + 長い構造化出力) は
  3 回中 1 回しか正しく終わらなかった (「見つからない」と誤る、invalid input)。low で考えさせると 1 回が 3 分を超え、JSON の中身も崩れた。
  当面 broker の LLM はデモ用のプロキシ (OpenAI / Gemini) にし、手元の LLM は統計的な口・埋め込み・エージェントの中で使う。
- broker の接続の確認は、空の本文 (`{}`) の `POST /v1/responses` を送り、400 でも合格にする。

## llm-gemini-emu の作り (`emu/llm-gemini-emu`)

- 客: Agent Network の broker の Gemini の接続 (v2。`url` を設定でき、認証は apiKey)。Mule の Inference コネクタ (1.2.0) の
  Gemini の接続は、行き先が `https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent` に固定で、鍵は
  `?key=` (jar の中で確かめた) なので使えない。
- 鍵は `x-goog-api-key`、`?key=`、Bearer のどれでも通る。鍵が無ければ 403 PERMISSION_DENIED、違えば 400 INVALID_ARGUMENT (本物と同じ文言)。
  `?key=` は URL に入るので、プログラムは URI をログに出さない。Caddy のログで伏せる設定はインフラに頼んである (2026-10-12)。
- 変換は `gemconv.clay` (テスト 18 件、`clay test test`)。応答の形 (キーの順も) は、本物の gemini-2.5-flash の応答
  (MuleSoft のデモ用の Gemini プロキシ経由、2026-10-12) に合わせた。
  - 項目名は camelCase と snake_case のどちらでも読む (API は両方を受け、公式の Python SDK は snake_case で送る)。
  - 関数呼び出しの id は無い (本物も無い)。functionResponse は、前の model の番の呼び出しに名前の順で対応させる。
  - `responseSchema` (OpenAPI の部分集合) は JSON Schema にする (type を小文字に、nullable は `[t, "null"]`、propertyOrdering を外す)。
    `responseJsonSchema` と `parametersJsonSchema` はそのまま渡す。
  - ストリーミング (`?alt=sse`) は `data: {..}\r\n\r\n`。最後の文の断片に finishReason と usageMetadata を付ける。
    断片は 1 トークンずつ (本物はもっと大きい)。`?alt=sse` が無いときは、流さずに JSON の配列 1 つで返す。
- 本物との違い:
  - `thinkingBudget` は 0 (考えない、`enable_thinking: false`) かそれ以外 (考える) かだけ。予算の数は守らない。
  - `thoughtsTokenCount` は出さない (llama-server は考えた分を分けない。`candidatesTokenCount` に入る)。
  - `googleSearch` などの組み込みの道具は捨てる。`candidateCount` は 1 だけ。部品は text、functionCall、functionResponse だけ。
  - エンジンは関数呼び出しの前に一言の文を付けることがある (本物は関数呼び出しだけのことが多い)。
- 公式の Python SDK (google-genai 2.29.0) で、流さない呼び出し、ストリーミング、関数の自動呼び出しの往復、スキーマ付きの JSON
  (Pydantic で読める)、考えた内容の部品、countTokens、鍵の誤り (ClientError 400) が通る。
- LOG_BODIES=1 で動かしている (broker が送るものを見るため)。

## stat の作り (`k0/ai-stat`)

- アプリは mulay の `templates/stat-models` (計算は agent-harness の `stat/*.dwl` を symlink で共有)。`ai-stat/build.sh` が
  `mulay build` で 1 つの実行ファイル (DataWeave もネイティブ。JVM は要らない) にし、イメージ `stat-models:<VERSION>` にして k0 に読み込む。
  mulay、templates/stat-models、agent-harness の stat/*.dwl のどれかを変えたら VERSION と yaml の image を上げる。
- 同じイメージを `stat.serve=embed` と `stat.serve=llm` の 2 つの Deployment にする。鍵は Secret の `api-key.properties` を
  `keys.file` で読む (無ければ起動しない。鍵は実行ファイルに入らない)。
- `llm.tfidf.stat` の客は agent-harness (`llm.url=https://llm.tfidf.stat.theorems.dev/v1`、`llm.key`、`llm.model=tfidf`)。
  ツールは agent-harness の `stat/hints.dwl` に手がかりがあるものだけが選ばれる。broker には使えない (Responses API も推論も無い)。
- 確かめたこと (2026-10-12): シナリオ 21 件が実 Mule 4.11.3 と mulay で一致。agent-harness の `llm.url` をここに向けると、
  agent-harness-stat のシナリオの答え 166 件が、内蔵の統計的なモデルのときと全部同じ。100 件の埋め込みは mulay が中央値 0.10 秒、
  実 Mule が 0.20 秒。公開名に証明書が付き、鍵なしは 401。

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
- 実 Mule 4.11.3 + Vectors 1.0.0 の embedding-generate-from-text が、公開名 (HTTPS) に向けた Azure OpenAI の接続 (3 件) と
  Ollama の接続 (`/k/<鍵>`、末尾の `/` ありも) で 1536 次元を返す。同じ文の値は両方で同じ。鍵の誤りは
  `MS-VECTORS:EMBEDDING_OPERATIONS_FAILURE` (文言は 401 の本文を含む)。Mule のログに鍵は出ない。
- `llm.gemini.emu`: 公開名に証明書が付き、鍵なしは 403。`?key=` 付きの `streamGenerateContent?alt=sse` で 781 トークン (30 秒) が流れ、
  最後に finishReason と usageMetadata が来る。
- `ai-search.azure.emu`: smoke_test.py (並行登録を含む) が通る。実 Mule 4.11.3 + Vectors 1.0.0 で、embed.azure.emu で埋め込んで
  store-add (インデックスはコネクタが作る) と query が公開名で通り、英語の問いに正しい文書が最も近い 1 件として返る。
