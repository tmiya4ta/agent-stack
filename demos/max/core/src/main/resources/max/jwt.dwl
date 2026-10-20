%dw 2.0
// JWT (HS256) を作る・確かめる。Agent Network の broker の jwt-validation (hmac、鍵は文字列) に合わせる。
// 実 DW 4.11.3 と mulay と Python の hmac で、同じ入力から同じ文字列になることを確かめてある (2026-10-12)。
import toBase64, fromBase64 from dw::core::Binaries
import HMACBinary from dw::Crypto

fun b64url(b: Binary): String = ((toBase64(b) replace /=+$/ with "") replace /\+/ with "-") replace /\//  with "_"

fun part(o: Object): String = b64url(write(o, "application/json", {indent: false}) as Binary {encoding: "UTF-8"})

fun sign(signing: String, secret: String): String =
    b64url(HMACBinary(secret as Binary {encoding: "UTF-8"}, signing as Binary {encoding: "UTF-8"}, "HmacSHA256"))

// claims に署名した JWT
fun hs256(claims: Object, secret: String): String = do {
    var signing = part({alg: "HS256", typ: "JWT"}) ++ "." ++ part(claims)
    ---
    signing ++ "." ++ sign(signing, secret)
}

// 署名が合うか (形が JWT でなければ false)
fun valid(token: String, secret: String): Boolean = do {
    var ps = token splitBy "."
    ---
    if (sizeOf(ps) != 3) false else sign(ps[0] ++ "." ++ ps[1], secret) == ps[2]
}

// sub に、いまから ttl 秒の JWT
fun token(sub: String, ttl: Number, secret: String): String = do {
    var t = now() as Number {unit: "seconds"}
    ---
    hs256({sub: sub, iat: t, exp: t + ttl}, secret)
}

// JWT の claims (署名は確かめない。形が違えば {})
fun claims(token: String): Object = do {
    var ps = token splitBy "."
    var body = if (sizeOf(ps) == 3) (ps[1] replace /-/ with "+") replace /_/ with "/" else ""
    var padded = body ++ dw::core::Strings::repeat("=", (4 - (sizeOf(body) mod 4)) mod 4)
    ---
    if (body == "") {} else read(fromBase64(padded) as String {encoding: "UTF-8"}, "application/json") as Object
}
