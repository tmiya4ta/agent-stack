/*
 * clay から呼ぶ llama.cpp の薄い層（宣言だけ。実装は embshim.c）。
 *
 * clay の defextern は Int (= int64_t) と Str (= char*) しか渡せないので、
 * llama.cpp の構造体はすべて embshim.c の中に閉じ込めて、ここには素の型だけを出す。
 * このヘッダは llama.h を含まない: clay のビルドは build.sh の EXTRA_CFLAGS で
 * `-include embshim.h` として読み込み、llama.cpp の include パスを要らなくしている。
 */
#ifndef EMBSHIM_H
#define EMBSHIM_H

#include <stdint.h>

/*
 * モデルを読み込み、計算用スレッドを起動する。成功なら埋め込み次元数、失敗なら負数。
 * n_gpu_layers は GPU に載せる層数（負数 = 全層、0 = CPU のみ）。
 */
int64_t emb_load(char *path, int64_t n_ctx, int64_t n_threads, int64_t n_gpu_layers);

/* トークン数（末尾の EOS を含む）。上限を超えていても正しい数を返す。 */
int64_t emb_count_tokens(char *text);

/*
 * text の埋め込みの先頭 dims 次元を L2 正規化し、float32 リトルエンディアンで out に書く
 * （out は dims * 4 バイト以上）。戻り値はトークン数、失敗なら負数
 * （-1: 長すぎる、-2: 空、-3: llama_decode 失敗、-4: 埋め込みが取れない）。
 */
int64_t emb_embed(char *text, int64_t dims, char *out);

/* float32 配列（n 個）を JSON の数値配列 "[a,b,...]" にして out に書く。書いたバイト数、cap 不足なら -1。 */
int64_t emb_format_json(char *f32, int64_t n, char *out, int64_t cap);

#endif
