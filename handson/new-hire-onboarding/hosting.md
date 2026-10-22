# ハンズオン環境の作り方

主催者が当日までに作っておくもの。参加者は BG1 / Sandbox で onboarding-employees の broker を配備し、
APPBG に置いたメンバーの 3 アプリを URL で呼ぶ。メンバーのアプリは参加者に見せない。
参加者は VS Code (Anypoint Code Builder) で配備する。その手順は別のチュートリアルにあるので、ここには環境の作り方だけを書く。
値 (ログイン、URL、鍵) の名前は [credentials.md](credentials.md) に、値は環境ごとに `~/.config/handson/new-hire-onboarding/<環境名>/env.json` に書く (git の外)。
環境名は `<日付>-<お客さん>` (例 `20261029-acme`)。同じハンズオンを別のお客さんに別の org でやるので、環境ごとにフォルダを分ける。
`python ../env_page.py` が全部の env.json から HTML を作り、デスクトップの「handson 環境」から開ける (下の「環境のメモ」)。
受講者が見るのは BG1 の Exchange の資産 `new-hire-onboarding-handson` (使う URL、クレデンシャル、コピペする 3 つのファイル)。

## Claude に頼むとき

「new-hire-onboarding をセットアップして」と言われたら、**確認を挟まずに**下の「手順」の 1〜8 を順に流し、「確かめる」と「予行」(CLI) まで通して、
結果 (作ったものの ID と URL、受講者のユーザー名とパスワード、Exchange のページの URL) を env.json に書き、`python ../env_page.py` で HTML を作り直してから報告する。
聞いてよいのは、次のどれかが分からないときだけ:

- 管理者のユーザー名とパスワード、LLM の行き先の URL と鍵 (その環境の env.json に無ければ)
- お客さんの名前 (環境名に使う。分からなければ日付だけにして、あとで名前を変える)
- ハンズオンの日付 (ユーザー名の `wsXX_<日付>`) と人数 (既定は ws00 + 受講者 5 人)

「new-hire-onboarding を片付けて」と言われたら、下の「後片付け」を、まず消すものの一覧を出して見せてから `--yes` で流す (消すと戻せないので、ここだけは確認する)。

## 全体

```
root org
  ├─ BG1 (Sandbox)       参加者の場所。チーム workshop に BG1 / Sandbox の全ロール
  │    ├─ Managed Omni Gateway agent-network-shared-gw   broker と API インスタンスの配備先
  │    ├─ Model Proxy workshop-llm-proxy (/llm)           JWT (HS256、全員同じ 1 つ)。行き先は主催者の LLM
  │    └─ 参加者ごとの broker  onboarding-broker-wsXX     (参加者が配備する)
  └─ APPBG (Sandbox)     主催者だけ。チーム workshop は付けない (見えなくする)
       ├─ employee-db-app          (MCP)
       ├─ it-provisioning-agent    (A2A、LLM に直接)
       └─ office-concierge-agent   (A2A、LLM に直接)
```

## 用意するもの

- Anypoint の org の管理者 (MFA なし。`/accounts/login` は MFA に対応しない)。US の org で、Sandbox の vCore が 0.8 以上、Managed Gateway の Small が 1 つ以上
- LLM の行き先: OpenAI 互換の URL と、`Authorization: Bearer` で通る鍵 (workshops の `llm-proxy.workshops.mulesoft.com` の token など)
- 道具: Python 3、Node.js と Playwright (`npm install playwright && npx playwright install chromium` を repo の外で)、`yc`、`anypoint-cli-v4` と agent-fabric プラグイン、Maven と JDK 17
- 事前テスト用のリモートデスクトップ (VS Code での予行)

## 手順

スクリプトは [setup/](setup/) にある。すでにあるもの (同じ名前の BG、Gateway、チーム、ユーザー) は作り直さないので、途中で止まっても頭から流し直せる。

```bash
export ANYPOINT_USERNAME=<管理者> ANYPOINT_PASSWORD=<パスワード>
cd handson/new-hire-onboarding/setup
```

| # | 作るもの | コマンド | かかる時間 |
|---|---|---|---|
| 1 | BG1 と APPBG、vCore (APPBG 0.3、BG1 に残り全部)、BG1 に Managed Gateway Small 1 つ、Gateway `agent-network-shared-gw` (us-east-2、最新の LTS、Small) | `python anypoint_setup.py org` | 1〜2 分 |
| 2 | チーム workshop。`/accounts/api/roles` の全ロールを BG1 / Sandbox に付ける。APPBG には付けない | `python anypoint_setup.py team` | 15 分ほど (50 回ごとに 429 で待つ) |
| 3 | 参加者のユーザー `wsXX_<日付>`。チーム workshop に入れる。パスワードは `--out` (既定は環境のフォルダの `users.json`) に出る | `python anypoint_setup.py users --count 6 --date 20261029 --env 20261029-acme` | 1 分 |
| 4 | メンバーの 3 アプリを APPBG / Sandbox に配備 (下の「メンバーのアプリ」) | `yc harness deploy ...` | 1 つ 3〜5 分 |
| 5 | Model Proxy `workshop-llm-proxy` を BG1 に作る | `LLM_TOKEN=<鍵> NODE_PATH=<node_modules> node model-proxy.js` | 2 分 |
| 6 | Model Proxy の認証を JWT にする。Client ID Enforcement を無効にし、JWT Validation (HS256) を付ける。秘密鍵と受講者用の JWT は環境のフォルダの `llm-jwt.json` に出る (期限は `--jwt-days`、既定 90 日) | `python anypoint_setup.py proxy-jwt --env <環境名>` | 1 分 (反映に 1〜2 分) |
| 7 | 受講者が見る Exchange のページ。BG1 の custom 資産 `new-hire-onboarding-handson` に、使う値と、値を埋めた `exchange.json`、`agent-network.yaml`、`broker1.agent` を載せる | `python anypoint_setup.py page --env <環境名>` | 1 分 |
| 8 | 確かめる (下の「確かめる」と「予行」) | `python anypoint_setup.py show` と curl | 10 分 |

ws00 は主催者の予行用にする (`--count 6` なら ws00 と参加者 5 人)。
メールの既定は `tmiyashita+{name}@salesforce.com` (`--email` で変える)。org のユーザー名は Anypoint 全体で一意なので、日付で分ける。
作ったものの ID と URL は `show` で出るので、env.json に写す。

### メンバーのアプリ

A2A の 2 つは Model Proxy を通さず、LLM に直接向ける。yc の変数プロファイル (`~/.yc/agentnet-vars.json`) に、LLM のホストと鍵を入れておく。

```json
"nho-20261029": {
  "llm-host": "llm-proxy.workshops.mulesoft.com",
  "llm-api-key": "<鍵>",
  "llm-base-url": "https://llm-proxy.workshops.mulesoft.com/openai/v1"
}
```

```bash
yc config credential <profile> <管理者> <パスワード> user    # 1 度だけ。~/.yc/credentials の項目名は username / password
yc login <profile>
for u in employee-db-app it-provisioning-agent office-concierge-agent; do
  yc harness deploy <APPBG の ID> <APPBG の Sandbox の ID> $u target=ch2:cloudhub-us-east-2 profile=nho-20261029
done
```

出てきた URL を env.json に書く。broker の `exchange.json` に入れるのは、A2A は末尾 `/` 付きの URL、employee-db-app は base URL (`/mcp` は付けない)。

### Model Proxy

作る API は公開されていないので、[setup/model-proxy.js](setup/model-proxy.js) が Enhanced UI (omni.mulesoft.com) を操作する。
先に `--dry-run` で 1 ページ目を埋めたところまで動かし、`model-proxy-dry-run.png` で BG1 と Gateway が選べているのを見ておくとよい。

画面で作るときの中身 ([Create](https://docs.mulesoft.com/general/model-proxy-create-model-proxy)、[Policies](https://docs.mulesoft.com/general/model-proxy-policies)):

1. 左下で BG1 を選び、**Model Proxies > Add Model Proxy**
2. Proxy Name `workshop-llm-proxy`、Base Path `llm`、Format は **OpenAI** (後から変えられない)、Environment Sandbox、Omni Gateway `agent-network-shared-gw`、Port 8081
3. Routing は Model-based。Provider は **OpenAI** (行き先が `Authorization: Bearer` を受けるので)。
   Destination URL は `https://llm-proxy.workshops.mulesoft.com/openai/v1/` (末尾の `/` が要る)、API Key は Static で鍵
4. 既定で Client ID Enforcement が付く (ほかに cors、llm-proxy-core、model-based-routing など 8 つ)。
   `proxy-jwt` がこれを無効にし (`PATCH .../apis/<id>/policies/<policyId>` に `{"disabled":true}`。無効にしたポリシーは一覧から消える)、
   同じ order 3 に JWT Validation を付ける: signingMethod hmac、signingKeyLength 256、jwtKeyOrigin text (秘密鍵)、
   jwtOrigin `httpBearerAuthenticationHeader`、skipClientIdValidation true、mandatoryExpClaim true。
   JWT の中身は `sub` と `client_id` が `new-hire-onboarding-handson`、`exp` 付き

1 ページ目の Continue で `POST https://omni.mulesoft.com/api/llm-proxies/create` (Exchange の資産、type llm)、
Add Model Proxy で `.../api/llm-proxies/deploy` (API Manager のインスタンス) が呼ばれる。
途中で止めると資産だけ残る。作り直すと create が 409 になるが、そのまま 2 ページ目に進める。

### 確かめる

```bash
python anypoint_setup.py show        # BG、Gateway の URL、アプリ、API インスタンス

# Model Proxy。JWT 無しは 400 JWT Token is required.、違う JWT は 401 Invalid token.、llm-jwt.json の token なら 200
curl -s <Gateway の URL>/llm/chat/completions -H 'Content-Type: application/json' -H "Authorization: Bearer <JWT>" \
  -d '{"model":"gpt-5-mini","messages":[{"role":"user","content":"say hi"}]}'
```

そのあと ws00 で broker を配備して呼ぶ (下の「予行」)。

## 予行

参加者と同じ権限 (ws00) で、broker の build、publish、deploy、呼び出しまで通るのを見る。VS Code での通しは、事前テスト用のリモートデスクトップで ws01 を使う。

CLI で通すとき:

```bash
cp -r ../onboarding-employees ~/work/ws00-net && cd ~/work/ws00-net
sed -i -e 's/{{-suffix}}/-ws00/g' -e 's/{{_suffix}}/_ws00/g' -e 's/{{business-group-id}}/<BG1 の ID>/g' \
  -e 's#{{it-provisioning-agent-url}}#<URL>/#g' -e 's#{{office-concierge-agent-url}}#<URL>/#g' \
  -e 's#{{employee-db-app-url}}#<URL>#g' -e 's#{{llm-base-url}}#<Gateway の URL>/llm#g' \
  -e 's/{{llm-client-id}}/none/g' -e 's/{{llm-client-secret}}/none/g' -e 's/{{llm-api-key}}/<JWT>/g' \
  exchange.json agent-network.yaml brokers/broker1.agent
A="--username ws00_<日付> --password <パスワード> --organization <BG1 の ID> --environment Sandbox"
anypoint-cli-v4 agent-network project build
anypoint-cli-v4 agent-network project publish $A
anypoint-cli-v4 agent-network project deploy $A -g agent-network-shared-gw \
  --property it-provisioning-agent-ws00.url:<URL>/ --property office-concierge-agent-ws00.url:<URL>/ \
  --property employee-db-server-ws00.url:<URL> --property openai-llm-ws00.url:<Gateway の URL>/llm \
  --property openAI.clientId:none --property openAI.clientSecret:none --property openAI.apiKey:<JWT> < /dev/null
```

変数を全部 `--property` で渡さないと、deploy は入力待ちで止まり、900 秒後に `errorCode: 3018` になる (`yes ''` を流し込んでも進まない)。
`openAI.apiKey` は `llm-jwt.json` の token (broker が `Authorization: Bearer` で送る)。`openAI.clientId` / `clientSecret` は使わないので `none` でよい。broker の呼び方は [onboarding-employees の README](onboarding-employees/README.md) の curl
(`<Gateway の URL>/onboarding-broker-ws00/`、`SendMessage`、`A2A-Version: 1.0`)。全部成功なら `TASK_STATE_COMPLETED` で、社員 ID、PC、入館証が返る。

## 受講者に渡すもの

- 1 人ずつ: ユーザー名 (`wsXX_<日付>`) とパスワード (環境のフォルダの `users.json`)
- 全員に: Exchange のページの URL (`page` が最後に出す。`https://anypoint.mulesoft.com/exchange/<BG1 の ID>/new-hire-onboarding-handson/`)

Exchange のページ (手順 7) に載せるもの:

| ページ | 中身 |
|---|---|
| home | BG1 の名前と ID、Sandbox、Gateway の名前、メンバーの 3 つの URL、Model Proxy の URL、クレデンシャル (`openAI.apiKey` に JWT と期限、`openAI.clientId` / `clientSecret` は `none`)、broker の呼び方 |
| exchange.json、agent-network.yaml、broker1.agent | `onboarding-employees/` のファイルの `{{...}}` を埋めたもの (`{{llm-api-key}}` は JWT)。suffix は `-wsXX` / `_wsXX` のままにして、受講者が自分の番号に置き換える |

全員が BG1 / Sandbox / 同じ Gateway に配備するので、Exchange の assetId、broker の名前、connection (= API インスタンス) の名前がぶつかる。
そのために `wsXX` を自分の番号にしてもらう。`onboarding-employees/` のファイルを直したら `page` を流し直す (同じ資産のページを上書きする)。

## 後片付け

```bash
python anypoint_setup.py teardown --date <日付>          # 消すものの一覧を出すだけ
python anypoint_setup.py teardown --date <日付> --yes    # 消す
```

BG1 と APPBG の Sandbox のアプリ (受講者の broker とメンバーの 3 つ) → API インスタンス (broker の connection と Model Proxy) → Gateway →
ユーザー `wsNN_<日付>` → チーム workshop → BG1 と APPBG、の順に消す。Exchange の資産 (受講者のネットワーク、Model Proxy、ハンズオンのページ) は BG と一緒に消える。
BG は Gateway が消えきるまで消せないので、30 秒おきに試す (最大 10 分)。vCore と Managed Gateway の枠は root に戻る。
yc の変数プロファイル `nho-<日付>` は手で消す。env.json は消さずに `"status": "done"` にして `python ../env_page.py` を流す (一覧の「片付けた環境」に移る)。

## 環境のメモ

このリポジトリは GitHub で公開されている。お客さんの名前、org や BG の ID、URL、クレデンシャルは git に書かず、env.json にだけ書く。

環境ごとの URL とクレデンシャルは `~/.config/handson/new-hire-onboarding/<環境名>/env.json` に置き、[../env_page.py](../env_page.py) で HTML にする。

```bash
python ../env_page.py               # 全部の env.json から HTML を作り直す
python ../env_page.py --shortcut    # 初回だけ。デスクトップに「handson 環境」(~/.config/handson/index.html へのショートカット) を作る
```

env.json は `sections` の下に `{"label", "value"}` を並べる。パスワードや鍵は `"secret": true` (画面では伏せて、「表示」と「コピー」)、URL は `"link": true`。
形は env_page.py の先頭に書いてある。載せるもの: 受講者に渡すもの (Exchange のページ、BG / Environment)、受講者のユーザーとパスワード、管理者、
事前テスト用のリモートデスクトップ、BG と Gateway の ID と URL、メンバーのアプリの URL、LLM (Model Proxy の URL、行き先、鍵)。

## Gateway の名前

Agent Fabric が作る Gateway の名前は、作り方とスペースで決まる
([Get Started](https://docs.mulesoft.com/agent-network/latest/af-get-started)、
[CI/CD](https://docs.mulesoft.com/agent-network/latest/af-build-agent-networks-in-a-ci-cd-environment))。

| 作り方 | 名前 |
|---|---|
| Code Builder の `MuleSoft: Set Up Agent Network Gateways`、shared space | `agent-network-shared-gw` (ingress と egress を 1 つで) |
| 同じコマンド、private space、1 つ | `agent-network-gw` |
| 同じコマンド、private space、分ける | `agent-network-ingress-gw` と `agent-network-egress-gw` |
| `anypoint-cli-v4 agent-network project deploy` で `-g` を付けないとき | `agent-network-gw` を使う |
| Runtime Manager で手で作る | 既定の名前は無い |

BG1 には private space を作らないので `agent-network-shared-gw` にする。VS Code から配備するときもこの Gateway を選ぶ。
バージョンは 1.12.x LTS 以上 (1.10.0 より前は配備が `errorCode: 3004` で失敗する)。サイズは Small (API 50 まで) で足りる。

## 気を付けること

- vCore: root の `reassigned` に、子の BG が無くても使えない分が入っていることがある (2026-10-21 は 0.2)。`org` は 400 の「only N vCores available」を見て BG1 の分を減らす。
- JWT Validation の jwtOrigin を `customExpression` にして `Authorization` と `api-key` の両方から読ませようとしたら、Flex 1.12.9 では
  JWT 無しも偽物も通った (式が効かず、ポリシーが素通しになる)。標準の `httpBearerAuthenticationHeader` にしたら効いた。
- `jwt-validation` の最新 (0.12.0) は Flex 1.12.9 に実装が無く 400。`proxy-jwt` は新しい版から順に試す (1.12.9 では 0.11.1)。
- Gateway を API で作るときは `configuration` (ingress、logging、properties) が要る。`runtimeVersion` は `latest` だと 400 で、版の番号を入れる。shared space の public URL は空で送ると Gateway が付けてくれる。
- チームのロールは、Sandbox の環境スコープ、だめなら BG1 のスコープで付ける。org で使えないロールは 403 で付かない。
  2026-10-21 は環境スコープ 81、BG スコープ 39 が付き、224 が 403 (Organization Administrator、Exchange Administrator、MuleSoft Agent AI User、Application Create / Owner の系統など)。
  それでも ws00 の権限で broker の build、publish、deploy まで通った。
- root にはもとから「Workshop Team」というチームがある (workshops の org の作り)。触らずに別に workshop を作る。
- employee-db-app の DB は SQLite で、全員が同じものを使う。再起動すると消える。
- `deploy` は 900 秒待って `errorCode: 3018` でタイムアウトすることがあるが、配備はできていることが多い。アプリの状態を直接見る。
- `exchange.json` の `version` は publish のたびに上げる。同じ版だと `Skipping...` で何も変わらない。

## 記録

| 回 | org | 状態 |
|---|---|---|
| 2026-10-29 | `anypoint-cbp-1791266292` (US)。ID と URL は `~/.config/handson/new-hire-onboarding/20261029-*/env.json (お客さんの名前は git に書かない)` | 2026-10-21〜22 に 1〜8 を済ませた (BG1 の vCore は 0.5)。ws00 で broker を CLI で配備して全部成功の分岐を確認。Exchange のページは ws00 から見える。teardown は一覧を出すところまで (消すのは未実行) |
