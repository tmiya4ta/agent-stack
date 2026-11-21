# 操作動画

Codelab (`../codelab/actionability.md`) の手順を、Lab ごとに録った動画。本番サイトの 4 モジュールの構成。
Lab ごとの mp4 と字幕 (`.srt`) を、スライドと 1 本につないだのが `actionability-full.mp4` (下の「1 本にまとめる」)。
動画と画像の `{名前}` は `demo`。操作は `labs/<lab>.js` に残してあり、Lab ごとに撮り直せる。

| ファイル (`out/final/`) | 中身 | 台本 (`labs/`) |
|---|---|---|
| `lab0` | 準備: サインイン、Enhanced UI、ビジネスグループ | `lab0.js` |
| `m1-lab1` | Lab 1-1 Agent Scanner | `m1-lab1.js` |
| `m2-lab1` | Lab 2-1 MCP Bridge (作る → Workshop UI で試す) | `m2-lab1a.js` + `m2-lab1b.js` |
| `m2-lab2` | Lab 2-2 MCP Global Access Control | `m2-lab2.js` |
| `m2-lab3` | Lab 2-3 Orchestration (Alex) + 任意: Broker の構成方法 (ガイドのページ) | `m2-lab3.js` |
| `m3-lab1` | Lab 3-1 Trusted Agent Identity (OBO の設定 → Jamie、Identity) | `m3-lab1.js` |
| `m3-lab2` | Lab 3-2 Agent Visualizer | `m3-lab2.js` |
| `m4-lab1` | Lab 4-1 Semantic Routing (Proxy を作る → アクセスの申請、Workshop UI) | `m4-lab1a.js` + `m4-lab1b.js` |
| `m4-lab2` | Lab 4-2 Model Wallet (Wallet → ポリシー → 429) + 費用の確認 | `m4-lab2a.js` + `m4-lab2b.js` |
| `m4-lab3` | Lab 4-3 Cost Optimization (Tool Mapping、Progressive Disclosure) + Tokens saved | `m4-lab3a.js` + `m4-lab3b.js` |
| `actionability-full` | 全部を 1 本に。字幕はトラックで入れてあり、プレーヤーでオン/オフできる。同じ名前の `.srt` もある | |
| `actionability-full-sub` | 同じものに字幕を焼き込んだ版 (プレーヤーを選ばない) | |

`a` と `b` に分けた Lab は、`edit.py` が 1 本につなぐ。

**Lab 4-2 の後半 (`m4-lab2b`) と Lab 4-3 (`m4-lab3a`、`m4-lab3b`) は、ブース 1 (tmiyashita-10879) で撮った**
(2026-11-13)。録画用の org (tmiyashita-10730) では Agentforce が無効で Optimize All が動かず、Budgets の Used も
0% のままだったため。この 3 本だけ、映る BG 名 (Actionability Workshop1) とユーザー名が他の Lab と違う。
Lab 4-3 は `labs/m4-lab3a-agent.js` (Optimize All の提案を Apply Changes で適用する版)。前の版は `out/final-10730/`。
ブースのアカウントで流すときは `booth.sh` (台本の BG 名、ユーザー名、org の ID を置き換える。ドライバは CRED、WS_BG、PROFILE で起動)。

## 作り方

```console
$ python reset.py <env.json> [--yes]       # 撮り直しの前に、demo の名前で作ったものを消す (表示だけなら --yes なし)
$ HANDSON_ENV=<env.json> node rec-driver.js   # ブラウザを開いたままにするドライバ (127.0.0.1:9334)
$ ./run.sh start m2-lab2                   # 録画を始める (out/profile を使い回す)
$ T=900 ./run.sh < labs/m2-lab2.js         # 台本を流す
$ ./run.sh stop                            # out/m2-lab2.<タブ>.webm と .json (字幕、タブの切り替え、切り取る区間)
$ python process.py <ffmpeg.exe> m2-lab2   # タブをつなぎ、切り取って out/final/m2-lab2.mp4 と .srt を作る
$ ./check_frames.sh <ffmpeg.exe> "kurita|811801467559"   # 2 秒ごとのコマを OCR にかけ、写ってはいけない文字を探す
```

- 台本は最初に `s.lib()` で `labs/common.js` (サインイン、ビジネスグループ、Workshop UI への接続、Broker の選択、
  プロンプトの送信、伏せ字) を読む。`s.step('字幕')` の文がそのまま字幕になるので、社外向けの言葉遣いで書く。
- Anypoint はタブ `a`、Workshop UI はタブ `ui` に置き、`s.tab()` で切り替える。タブごとに録画し、`process.py` が
  切り替えた順につなぐ。Workshop UI はページを読み直すと Anypoint との接続が切れるので、行き来しても切れないようにしている。
- Lab の最初は `s.intro()` の「それではここから、Lab 2-2「…」を行います」。前の Lab の続きの状態 (Workshop UI の接続、
  MCP サーバーへの接続、ペルソナのサインイン) は、切り取る区間 (`s.skipStart` / `s.skipEnd`) で作っておく。
- 失敗した操作は切り取らずに、その Lab を撮り直す (切り取ると画面が飛ぶ)。作成したものは `reset.py` か画面で消してから。
- 切り取るのは、待ち時間とサインイン (`skips`)、5 秒より長く画面が止まっている区間 (字幕を読む時間は残す)。
- 秘密の欄 (AWS のキー、LLM の API キー、client ID / secret) は、入れる前に `s.blur` でぼかす。画面に出る値は
  `s.watchBlur` (AWS のアカウント ID を伏せ字) と `s.watchHex` (32 桁の英数字をぼかす) で、出た瞬間に隠す。
- Workshop UI のラベルは CSS で大文字にしているだけで、元の文字は「Path」「Client ID」のように小文字が混じる。
- ffmpeg は字幕や切り取りのフィルタが入ったフル版を使う (gyan.dev の essentials build)。Playwright 付属のものでは足りない。
- `out/` は git に入れない (ユーザー名や org の URL が写っている)。

## 1 本にまとめる

```console
$ powershell -File slides.ps1 <Workshop-Template.pptx> out/actionability-slides.pptx out/slides   # スライドを作って PNG に
$ python edit.py <ffmpeg.exe> [--all]    # out/final/actionability-full.mp4、-sub.mp4、.srt
```

- テンプレートは表紙、区切り、白、締めの 4 枚。`slides.ps1` が文言 (`slides.json`) を入れて、表紙、全体の説明、事前準備、モジュールごとの区切りと説明、Lab ごとの区切り (「Lab 2-2  名前」と説明)、締めの 21 枚にする。表紙の日付とサブタイトル、講演用のノートは消す。スライドの名前と番号の対応は `out/slides/index.json`。
- `out/edit/` の区切りごとの mp4 は、元のスライドや録画より新しければ作り直さない。`edit.py` のフィルタ (帯やフェード) を変えたときは `--all`。
- 締めの「Thank you」は 1 文字ずつ置いてあり、フォント (Avant Garde Demi SFDC) が無い PC では崩れる。出力のコピーでは Century Gothic の 1 つの文字にし直している。
- 字幕とスライドは社外向けなので、ビジネスの言葉遣いにする。字幕は「です・ます」でそろえて体言止めにしない。IT で普通に使う語にする (デプロイ、ユーザー ID、プロンプト、再接続など。「配備」「身元」「問い」などは使わない)。
- ラボの間は録画を少し縮めて上に帯を作り、モジュールとラボの名前を出しておく (画面の上にかぶせると、最初に押すメニューが隠れる)。

## イベント版 (ブースの 4K モニターで流す)

```console
$ powershell -File slides.ps1 <Workshop-Template.pptx> out/booth/booth-slides.pptx out/booth/slides slides-booth.json 3840
$ python booth.py <ffmpeg.exe> --still   # 場面ごとの静止画 (out/booth/stills/) で、映す範囲と見出しを確かめる
$ python booth.py <ffmpeg.exe>           # out/final/actionability-booth.mp4 (3840x2160、約 5 分)
```

- **2026-11-09 に全部撮り直したため、`booth.json` の秒数は前の録画のもので、今の録画とは合わない。使う前に場面を選び直す。**
- 通りがかりの人が離れて見る前提。ラボの手順は追わず、結果の出る場面だけを `booth.json` に並べる (録画の何秒から何秒、何倍速、どこを映すか、見出し)。
- 録画は紺の背景の上の角丸の枠に入れ、見出しは枠の下に 1 行。映像の上には文字を重ねない。右下に、いまの柱 (Discover〜Cost Control) を出す。
- 最後は Thank you から黒に落として 3 秒止める (ループで流したときに区切りがわかるように)。音と字幕のトラックは無い。
- 映す範囲 (crop) は、Workshop UI の右上と Anypoint の左下のユーザー名、AWS のアカウント ID、エラーの表示が入らないように選んでいる。範囲を変えたら `--still` で確かめる。
