# 02 MCP Bridge: 2 つの API を 1 つの Commerce MCP にする

元のページ: [Lab 2: MCP Bridge](https://develop-actionability.workshops.mulesoft.com/action/mcp-bridge.html) (モジュール 2)

## 目的

Customer REST API と Order REST API の操作を、コードを書かずに 1 つの MCP サーバのツールにまとめ、gateway に配備する。
ラボ 04 の broker が使う Commerce MCP と同じ形。

## 手順

1. BG を**親の workshop BG** に切り替える (自分の子 BG のままだと「No Omni Gateways Available」になる)。
2. **MCP Servers** → **Add MCP Server** → **Create MCP Server**。
3. **APIs (2)** で絞り込み、**Customer REST API** と **Order REST API** を両方選ぶ。ツールは全部チェックのまま → Next。
4. 右上の **Edit** で設定を開き、Save:
   - Server Name: `commerce-mcp-<名前>`
   - Gateway: `attendee-gateway` (sandbox)
   - Version、Path、Environment はそのまま
5. **Create & Deploy**。

## 確かめること (Workshop UI の MCP タブ)

1. **Connect** で Anypoint につなぎ、BG と環境を選ぶ。**Browse my MCP servers** で自分のサーバを選び、**Use this proxy** → **Connect**。
2. **Tools (6)** を上から順に **Run Tool** する。前のツールで作った ID が次のツールに自動で入る。

| # | ツール | 中身 |
|---|---|---|
| 1 | `customer-rest-api_get_customers` | 顧客の一覧 (Alex、Ashley、Jamie と、ワークショップ中に作られたもの) |
| 2 | `customer-rest-api_post_customers` | 顧客を作る。username だけ空なので、一意な値 (自分の名前など) を入れる。ID は CUST-… |
| 3 | `customer-rest-api_get_customers_customerId` | 作った顧客 (飛ばしたら CUST-100001) |
| 4 | `customer-rest-api_put_customers_customerId` | loyaltyTier を Gold、pointsBalance を 500 に |
| 5 | `order-rest-api_createOrder` | Alex の注文 (6 項目すべて必須。見本が入っている) |
| 6 | `order-rest-api_getShippingStatus` | 作った注文 (飛ばしたら ORD-2026-00001) |

右上の Form / JSON で同じ値を 2 通りに見られる。**Show raw MCP response** で MCP の応答をそのまま見られる。

## つまずき

| 症状 | 直し |
|---|---|
| 保存でパスが重なるエラー | Base path を一意にする (`<名前>` を変える) |
| Asset not found / Permission denied | 親の workshop BG にいるか確かめる |
| 顧客を作ると重なりのエラー | username を変える |
| 注文で `{}` や required key not found | 6 項目を消していないか確かめる |
| Connect 後に 0 tools | Server URL の末尾に `/mcp/` を付ける |

## 実施メモ

- サーバの名前:
- 作った顧客と注文の ID:
- 気づいたこと:
