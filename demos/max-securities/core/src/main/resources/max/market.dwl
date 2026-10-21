%dw 2.0
// 仮想の市場の 1 日を作る。乱数は使わず、日付と銘柄・顧客の MD5 から作る (同じ日なら何度でも同じ結果。実 DW と mulay で同じ)。
// 値動き: 前の日の終値に ±1.2% ほどの揺れ。前の営業日に公表があった銘柄は、その値動き (price_move_pct) を足す。
// 普段の売買: 顧客ごとに 1 日 8% の確からしさで、これまでに売買した銘柄の 1 つを、年収の 1〜4% ほど売買する (買 7 割)。
import MD5 from dw::Crypto
import fromHex from dw::core::Numbers

// key から 0 以上 1 未満の数
fun u(key: String): Number = fromHex(MD5(key as Binary {encoding: "UTF-8"})[0 to 7]) / 4294967296

// d の次の営業日 (土日を飛ばす。祝日は扱わない)
fun nextBusinessDay(d: Date): Date = do {
    var n = d + |P1D|
    ---
    if (n.dayOfWeek == 6) n + |P2D| else if (n.dayOfWeek == 7) n + |P1D| else n
}

fun round1(x: Number): Number = round(x * 10) / 10

// その日の終値。prev: [{code, close}] (前の営業日)、jumps: {code: price_move_pct}
fun dayPrices(day: String, prev: Array, jumps: Object): Array =
    prev orderBy $.code map ((p) -> do {
        var r = (u("max|price|" ++ day ++ "|" ++ p.code) - 0.5) * 0.024
        var j = (jumps[p.code] default 0) / 100
        var c = round1(p.close * (1 + r) * (1 + j))
        ---
        {code: p.code, trade_date: day,
         close: if (c < 50) 50 else c,
         volume: floor((80000 + u("max|volume|" ++ day ++ "|" ++ p.code) * 520000) * (if (jumps[p.code]?) 3 else 1))}
    })

// その日の普段の売買。customers: [{customer_id, annual_income}]、favorites: {customer_id: [code]}、closes: {code: close}
fun backgroundTrades(day: String, customers: Array, favorites: Object, closes: Object): Array =
    flatten(customers orderBy $.customer_id map ((c) -> do {
        var key = "max|trade|" ++ day ++ "|" ++ c.customer_id
        var codes = (favorites[c.customer_id] default []) orderBy $
        ---
        if (isEmpty(codes) or u(key) >= 0.08) []
        else do {
            var code = codes[floor(u(key ++ "|code") * sizeOf(codes))]
            var price = closes[code]
            var budget = c.annual_income * (0.01 + u(key ++ "|budget") * 0.03)
            var lots = floor(budget / price / 100)
            ---
            [{customer_id: c.customer_id, code: code,
              side: if (u(key ++ "|side") < 0.7) "買" else "売",
              qty: (if (lots < 1) 1 else lots) * 100, price: price, trade_date: day,
              channel: ["ネット", "ネット", "ネット", "対面", "コールセンター"][floor(u(key ++ "|channel") * 5)]}]
        }
    }))
