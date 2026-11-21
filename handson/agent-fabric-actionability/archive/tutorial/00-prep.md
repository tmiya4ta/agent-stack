# 00 準備

元のページ: [Homepage](https://develop-actionability.workshops.mulesoft.com/index.html)

## 用意するもの

- 主催者から受け取るクレデンシャル ([credentials.md](../credentials.md))。値は `credentials.local.md` に書く
- ブラウザ (タブを 2 つ使う: Anypoint と Workshop UI)

## 手順

1. https://anypoint.mulesoft.com/ に主催者のユーザー名とパスワードで入る。
2. URL が omni.mulesoft.com で始まっていなければ、右上の **Switch to Enhanced** で新しい UI にする。
3. 左下の BG の切り替えで、BG が 2 つ見えることを確かめる。
   - 自分の子 BG (ユーザー名と同じ名前): ラボ 01 で使う
   - 親の workshop BG (一覧の 2 番目): ラボ 02 から使う
4. Workshop UI の URL を別のタブで開き、UI のユーザー名とパスワードで入る。ヘッダーの **Connect** で Anypoint につなぎ、BG と環境を選ぶ。

## 名前の付け方

`<名前>` は参加者ごとに一意にする (他の参加者と同じ gateway と環境を使うので、名前が重なると保存できない)。

| 作るもの | 名前 | ラボ |
|---|---|---|
| Scanner | `<名前> Scanner` | 01 |
| MCP サーバ | `commerce-mcp-<名前>` | 02 |
| Model Proxy | `<名前>-proxy` (Base path も同じ) | 07 |
| Exchange のアプリ | `<名前> Application` | 07 |
| Model Wallet | `<名前>-wallet` | 08 |

## 実施メモ

- 日付:
- 使った名前:
- 気づいたこと:
