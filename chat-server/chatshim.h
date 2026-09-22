/*
 * clay から呼ぶ llama.cpp の文章生成の薄い層（宣言だけ。実装は chatshim.c）。
 *
 * clay の defextern は Int (= int64_t) と Str (= char*) しか渡せないので、llama.cpp の構造体は
 * chatshim.c に閉じ込め、ここには素の型だけを出す。このヘッダは llama.h を含まない
 * （clay のビルドには build.sh が `-include chatshim.h` で読ませる）。
 */
#ifndef CHATSHIM_H
#define CHATSHIM_H

#include <stdint.h>

/*
 * モデルを読み込み、計算用スレッドを起動する。成功なら n_ctx、失敗なら負数。
 * n_gpu_layers は GPU に載せる層数（負数 = 全層、0 = CPU のみ）。
 */
int64_t chat_load(char *path, int64_t n_ctx, int64_t n_threads, int64_t n_gpu_layers);

/*
 * 会話 msgs に続く assistant の返答を生成して out に書く（cap バイトまで）。
 * msgs は「role \x1F content」を \x1E で区切って並べたもの。
 * out の先頭 16 バイトは固定長の見出し "PPPPPP CCCCCC S\n"
 * （P = プロンプトのトークン数、C = 生成したトークン数、S = 終わり方。s は stop、l は length）、
 * その後ろが UTF-8 の本文。temp_milli は温度の 1000 倍（0 なら常に最も確からしいトークン）。
 * 戻り値は out に書いたバイト数（見出しを含む）。失敗なら負数
 * （-1: msgs が空、-2: テンプレートを当てられない、-3: プロンプトが n_ctx に収まらない、-4: llama_decode 失敗）。
 */
int64_t chat_generate(char *msgs, int64_t max_tokens, int64_t temp_milli, char *out, int64_t cap);

/* msgs をテンプレートに当てたときのトークン数（生成はしない）。失敗なら負数。 */
int64_t chat_count_tokens(char *msgs);

#endif
