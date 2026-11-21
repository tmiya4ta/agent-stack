# 08 Model Wallet: 身元ごとに LLM の費用の上限を決める

元のページ: [Lab 2: Model Wallet](https://develop-actionability.workshops.mulesoft.com/cost/model-wallet.html) (モジュール 4)

## 目的

ラボ 07 の proxy の前に Model Wallet を置き、(1) 身元 (JWT の claim) が合う呼び手だけを通し、(2) その費用を予算で数えて、
上限を超えたら止める。結果は 3 通り: 通る (200)、許されない (401)、予算切れ (429)。

## 考え方

- **通すか** (access) と **誰の予算で払うか** (metering) は別。どちらも JWT の claim (例 `cost_center=finance`) で決まる。
  ラボ 07 の Client ID Enforcement は JWT Validation に替わる。
- 払う wallet の選び方: claim が合う wallet のうち、priority が一番高いもの。同じなら wallet-id で決める。
- このワークショップでは参加者全員が同じ claim (`cost_center=attendee`) なので、全員の wallet が候補になる。
  **Equalize priorities** で priority をそろえ、自分の wallet-id で選ぶ。

## 手順 1: wallet を作る

**Model Proxies > Model Wallets** → **+ New Model Wallet**:

| 項目 | 値 |
|---|---|
| Name | `<名前>-wallet` |
| Description | 空 |
| Environment | Sandbox |
| Claim key | `cost_center` |
| Claim values | `attendee` |

**+ Add budget** を 2 つ:

| Provider | Model | Period | Metric | 上限 |
|---|---|---|---|---|
| openai | GPT-5 Mini | Daily | Tokens | 5000 |
| gemini | Gemini 2.5 Flash | Daily | Spend | 5 (USD) |

→ **Create Model Wallet**。

## 手順 2: ポリシーを UI から替える (Workshop UI の Model Wallet タブ)

1. **Model Proxy Policy Configuration** で `<名前>-proxy` を選び **Use this proxy** → **Configure policies**。
2. 下見に出る変更 (Client ID Enforcement を外す、JWT Validation を足す、LLM Proxy Core を JWT の claim に向ける) を見て **Confirm & apply**。
   ゲートウェイに届くまで 1 分ほど待つ。

## 手順 3: priority をそろえる

**Equalize priorities** → 下見を見て **Confirm & apply**。誰かが新しい wallet を作るとそろえ直しになるので、そのときは押し直す (何度押してもよい)。

## 手順 4: 試す

1. Model Proxy Endpoint を **Use this proxy** か Consumer Endpoint で入れる。
2. ペルソナ **Attendee** を選び、wallet-id に自分の wallet の id (Anypoint の wallet のページの **Client ID**) を入れて送る。
3. **Governance log** で、選ばれた wallet、wallet-id、動いたモデル、トークン数を見る。選ばれた wallet が自分のものでなければ、手順 3 をやり直す。
4. ペルソナを替えて試す:

| ペルソナ | wallet-id | claim | 結果 |
|---|---|---|---|
| Attendee (自分) | `<名前>-wallet` | attendee | 200 |
| Emily (Finance) | finance-team | finance | 200 |
| Thomas (Engineering) | engineering-team | engineering | 200 |
| Alex (Marketing) | — | marketing | 401 (合う wallet が無い) |

- 予算切れを見る: Thomas で Finance の問い (Gemini に行く) を続けると、engineering-team の Gemini の予算 (1 日 2,000 トークン) が尽きて 429。
- 自分の wallet でも: Attendee で Coding か General の **(verbose)** の問いを続けると、OpenAI の 5,000 トークンが尽きて 429。

## 手順 5: 費用を見る

- Model Proxy の **Monitoring** → **Top client applications by tokens** に Attendee、Thomas、Emily が並ぶ (JWT で身元ごとに数える)。
- 左のメニューの **Cost management**: Budgets、Tokens (金額は数セントなのでトークンの方が分かりやすい)、期間を選ぶ。
  wallet ごとの上限と使った量。棒にカーソルを当てると詳細。

## 実施メモ

- wallet の id:
- 429 になるまでの回数:
- 気づいたこと:
