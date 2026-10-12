%dw 2.0
// 注文をその日の終値で約定させる (max-oms と、max-core の試験用の代わりで共用する)。乱数も時刻も使わない。
// orders: [{customer_id, code, side, qty, channel}]、closes: {code: close}
// 並びは (顧客、銘柄、売買) で決め、約定の ID は T + yyMMdd + 3 桁の連番、注文の ID は O + yyMMdd + 5 桁の連番。
// 返す要素は MQ に送る約定の形: {tradeId, orderId, customerId, code, side, qty, price, tradeDate, channel}

fun ymd(day: String): String = (day replace "-" with "")[2 to 7]

fun fills(day: String, orders: Array, closes: Object): Array =
    (orders orderBy ($.customer_id ++ "|" ++ $.code ++ "|" ++ $.side)) map ((o, i) -> {
        tradeId: "T" ++ ymd(day) ++ ((i + 1) as String {format: "000"}),
        orderId: "O" ++ ymd(day) ++ ((i + 1) as String {format: "00000"}),
        customerId: o.customer_id, code: o.code, side: o.side, qty: o.qty,
        price: closes[o.code], tradeDate: day, channel: o.channel default "ネット"
    })
