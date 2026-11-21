# Agent Fabric Actionability Workshop

MuleSoft の [Agent Fabric Actionability Workshop](https://actionability.workshops.mulesoft.com/index.html) (英語) を
実施した記録と、自分で開くための準備をまとめる。

> [!NOTE]
> これまでの手順書と動画は、develop 版 ([develop-actionability](https://develop-actionability.workshops.mulesoft.com/index.html)、
> 5 モジュール・11 ラボ) を元に作っていた。本番のサイトは 4 モジュール (Gain Visibility / Enable AI Actions / Govern AI Agents /
> Align AI Costs) なので、本番に合わせて作り直した (2026-11-06)。それまでのものは [archive/](archive/) に置いた。
> develop 版は 2026-11-06 の時点でも 5 モジュールのまま。元の手順書のソースは GitHub の
`MuleSoft-SE-Community-emu/actionability-workshop-documentation` (develop ブランチ、非公開)。日本語版 (`/jp`) は公開されていない (2026-10-21)。

## 筋書き

架空のアパレル会社 Vogue Studios が、[Composability Workshop](https://composable-enterprise.workshops.mulesoft.com/index.html) で作った
注文と顧客の API を元に、AI のスタイル相談アプリ **Vogue Premiere** を組み立てる。API には手を入れず、Agent Fabric で
エージェントから使えるようにし、統制し、つなぎ、見えるようにし、費用を抑える。

## ラボ

| # | モジュール | ラボ | 参加者がやること | 手順 |
|---|---|---|---|---|
| 0 | — | 準備 | Anypoint と Workshop UI に入る | [00-prep](archive/tutorial/00-prep.md) |
| 1 | 1. 可視化 | Agent Scanner | Amazon Bedrock のエージェントを Exchange に取り込む | [01](archive/tutorial/01-agent-scanner.md) |
| 2 | 2. AI に行動させる | MCP Bridge | Customer API と Order API を 1 つの Commerce MCP にする | [02](archive/tutorial/02-mcp-bridge.md) |
| 3 | | MCP Global Access Control | 注文のツールをゲートウェイで隠す | [03](archive/tutorial/03-mcp-global-access-control.md) |
| 4 | | Orchestration | 配備済みの broker を UI から使い、経路を見る | [04](archive/tutorial/04-orchestration.md) |
| 5 | 3. 本番に向けた統制 | Trusted Agent Identity | OBO のトークン交換と、他人の注文が見えないことを確かめる | [05](archive/tutorial/05-trusted-agent-identity.md) |
| 6 | | Agent Visualizer | ネットワークの地図 (Titanium があればトレースとログ) | [06](archive/tutorial/06-agent-visualizer.md) |
| 7 | 4. 費用 | Semantic Routing | 問いの意味で行き先のモデルを変える Model Proxy | [07](archive/tutorial/07-semantic-routing.md) |
| 8 | | Model Wallet | JWT の claim ごとの予算 (200 / 401 / 429) | [08](archive/tutorial/08-model-wallet.md) |
| 9 | | MCP Cost Optimization | Tool Mapping と Progressive Disclosure | [09](archive/tutorial/09-mcp-cost-optimization.md) |

参加者が自分で作るのは Scanner、MCP Bridge、ポリシー、Model Proxy、Wallet だけで、broker、エージェント、IdP、Workshop UI は
主催者が先に用意しておく ([hosting.md](hosting.md))。

## Codelab

`codelab/actionability.md` が原稿、`actionability.docx` が [codelab-generator](https://github.com/tmiya4ta/codelab-generator) で作った DOCX。
画像は `video/labs/` の台本の `s.shot` で撮ったスクショ (`video/out/shots/`) から `build_media.py` で作る (秘密の欄は撮る時点でぼかしてある。枠を付ける)。
画像だけを撮り直すときは、ドライバを `ANYPOINT_USER=<ユーザー名> WS_BG=<ワークショップの BG> STEP_FAST=1` で起動して Lab の台本を順に流す (下の video/README の手順)。

```console
$ cd codelab
$ python build_media.py                  # 画像は ../video/out/shots/ から
$ node ~/demos/codelab-generator/dist/codelab.js actionability.md -o actionability.docx
```

`actionability.md` はお客様に渡す手順書で、参加者の操作だけを書く (簡潔に。ネガティブなことや主催者向けの説明は書かない)。
事前の準備、参加者とやり取りする情報、当日の進行上の注意 (予行で分かったこと) は `organizer.md` / `.docx` (主催者向け。Web には載せない)。

Web で読める版は `codelab-site/` の Mule アプリが配信する (T1 / Sandbox、`rootps`、アプリ名 `actionability-codelab`。
https://actionability-codelab-23fgzd.pnwfdv.jpn-e1.cloudhub.io/)。`build.sh` が同じ原稿から codelab-generator の HTML 出力
(`-f html`) で `src/main/resources/web/` を作り、`<http:load-static-resource>` がそれを返す。原稿を直したら作り直して version を上げる。

```console
$ ./codelab-site/build.sh && (cd codelab-site && mvn -B clean package -DskipTests)
$ yc deploy file T1 Sandbox <T1 の org ID> actionability-codelab-app <version> codelab-site/target/actionability-codelab-app-<version>-mule-application.jar target=ps:rootps name=actionability-codelab
```

元の手順書から変えたところ:

- Semantic Routing: Finance の行き先を Gemini 2.5 Flash から Azure OpenAI の GPT-4o Mini にした (配られる LLM が Azure OpenAI だけ。
  同じ Provider のルートは 2 本置けない)。OpenAI のルートの Destination URL は `…/openai/v1/` まで付ける。Basic scale は 1 話題 10 発話までなので、
  発話は Workshop UI の用意された問い 8 つ + 2 つにした
- Model Wallet: Gemini の予算は省いた (Proxy が Gemini を使わない)。Cost Optimization: Optimize All が動かないときは説明を手で短くする
- 本番サイトの 4 モジュールの構成で書いた。社外向けなので「です・ます」のビジネスの言葉遣いにしている。
  develop 版にあった Lab 4-2 (Runtime Manager のログと API Manager の Key Metrics) は本番にないので外し、Titanium の節 (任意) にした

## クレデンシャル

何が要るかは [credentials.md](credentials.md)。値は同じフォルダの `credentials.local.md` に書く (`.gitignore` で除外。git に入れない)。

## 状態

| | 状態 |
|---|---|
| 手順のまとめ (archive/tutorial/) | 元のページから作った (2026-10-21)。本番と同じ 4 モジュールの並び。実施メモは未記入 |
| Codelab (codelab/) | 本番の 4 モジュールの構成の日本語の手順書 `actionability.md` / `.docx` (2026-11-06)。画像は 2026-11-21 に新しい環境 (`tmiyashita095102-10951`、BG `Actionability Workshop A`) で撮り直した。ツール名は `createOrder` など接頭辞なし |
| 動画 (video/) | 録画を本番の構成のラボに切り直したもの、ハンズオン用の通しの動画、イベント版 (Module 1 と MCP Bridge まで)。`out/` は git に入れない |
| archive/ | develop 版の構成で作った手順書 (codelab/、tutorial/) と動画 (video/。元の録画もここ) |
| 主催者の準備 (hosting.md) | 必要なものを洗い出しただけ。まだ何も作っていない |
