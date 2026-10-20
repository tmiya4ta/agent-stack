%dw 2.0
// 売買審査の点数付け (インサイダー取引の疑い)。規則と点は max/README.md の表。同じ入力なら同じ結果 (乱数も時刻も使わない)。
//
// alerts(days, trades, registry, anns): 公表 (値動き 3% 以上) ごとに、値動きの向きに合う売買を公表の前 5 営業日に
//   した顧客を拾い、点を付ける。30 点以上を返す (公表日時、顧客の順)。
//   days     営業日 ["yyyy-MM-dd", ..] (古い順)
//   trades   [{customer_id, code, side, qty, price, trade_date}] (trade_date は "yyyy-MM-dd")
//   registry [{customer_id, code, relation}] (内部者の登録)
//   anns     [{announcement_id, code, published_at ("yyyy-MM-dd HH:mm"), kind, title, price_move_pct}]
// 返す要素: {customer_id, code, announcement_id, score, reasons: [{rule, points, detail}]}

var THRESHOLD = 30

fun dayIndex(days: Array<String>, d: String): Number =
    ((days map ((x, i) -> if (x == d) i else -1)) filter ($ >= 0))[0] default -1

fun amountOf(ts: Array): Number = sum(ts map ($.qty * $.price)) default 0

fun yen(n: Number): String = (round(n) as String {format: "#,##0"}) ++ " 円"

fun usual(avg: Number, ratio: Number): String =
    "直前 60 営業日の 1 回の平均 (" ++ yen(avg) ++ ") の " ++ ((round(ratio * 10) / 10) as String) ++ " 倍"

fun forCustomer(days: Array<String>, trades: Array, registry: Array, a: Object, side: String, after: Array<String>, ts: Array, c: String) = do {
    var amt = amountOf(ts)
    var first = min(ts map $.trade_date)
    var fi = dayIndex(days, first)
    var lo = days[if (fi - 60 < 0) 0 else fi - 60]
    var prior = trades filter ((t) -> t.customer_id == c and t.trade_date >= lo and t.trade_date < first)
    var avg = if (isEmpty(prior)) 0 else amountOf(prior) / sizeOf(prior)
    var ratio = if (avg == 0) 0 else amt / avg
    var firstTime = isEmpty(trades filter ((t) -> t.customer_id == c and t.code == a.code and t.trade_date < first))
    var rel = (registry filter ((r) -> r.customer_id == c and r.code == a.code))[0].relation default null
    var opposite = trades filter ((t) -> t.customer_id == c and t.code == a.code and t.side != side and (after contains t.trade_date))
    var reasons = [
        {rule: "公表前の売買", points: 30,
         detail: "公表 (" ++ a.published_at ++ " " ++ a.kind ++ "、翌日 " ++ (a.price_move_pct as String) ++ "%) の前 5 営業日に "
                 ++ (sizeOf(ts) as String) ++ " 回、計 " ++ yen(amt) ++ " の" ++ side},
        if (firstTime) {rule: "初めての銘柄", points: 20, detail: "この銘柄を売買したのは初めて"} else null,
        if (avg == 0) {rule: "普段との差", points: 25, detail: "直前 60 営業日に売買が無い"}
        else if (ratio >= 5) {rule: "普段との差", points: 25, detail: usual(avg, ratio)}
        else if (ratio >= 2) {rule: "普段との差", points: 10, detail: usual(avg, ratio)}
        else null,
        if (rel != null) {rule: "内部者の登録", points: 25, detail: "登録あり: " ++ (rel as String)} else null,
        if (not isEmpty(opposite)) {rule: "公表後の反対売買", points: 10, detail: "公表後 5 営業日以内に " ++ (if (side == "買") "売" else "買") ++ " (" ++ (opposite[0].trade_date as String) ++ ")"} else null
    ] filter ($ != null)
    ---
    {customer_id: c, code: a.code, announcement_id: a.announcement_id,
     score: min([100, sum(reasons map $.points)]), reasons: reasons}
}

fun forAnnouncement(days: Array<String>, trades: Array, registry: Array, a: Object): Array = do {
    var i = dayIndex(days, a.published_at[0 to 9])
    var win = if (i < 0) [] else days[(if (i - 4 < 0) 0 else i - 4) to i]
    var last = sizeOf(days) - 1
    var after = if (i < 0 or i >= last) [] else days[(i + 1) to (if (i + 5 > last) last else i + 5)]
    var side = if (a.price_move_pct > 0) "買" else "売"
    var hits = trades filter ((t) -> t.code == a.code and t.side == side and (win contains t.trade_date))
    var groups = hits groupBy $.customer_id
    ---
    ((keysOf(groups) map ($ as String)) orderBy $) map ((c) -> forCustomer(days, trades, registry, a, side, after, groups[c], c))
}

fun alerts(days: Array<String>, trades: Array, registry: Array, anns: Array): Array =
    flatten((anns filter (abs($.price_move_pct) >= 3)) orderBy $.published_at map ((a) -> forAnnouncement(days, trades, registry, a)))
        filter ($.score >= THRESHOLD)
