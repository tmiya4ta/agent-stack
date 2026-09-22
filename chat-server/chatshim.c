/*
 * chatshim.h の実装。llama.cpp で chat 形式の返答を生成する。
 *
 * - 会話はモデルの GGUF に入っている chat template（tokenizer.chat_template）で 1 本のプロンプトにする。
 *   テンプレートが無いモデルでは chatml を使う。
 * - テンプレートが enable_thinking を持つモデル（Qwen3 / Qwen3.5 系。Ornith もそう）は、考える過程を出さないよう
 *   プロンプトの末尾に空の "<think>\n\n</think>\n\n" を付ける（Jinja で enable_thinking=false にしたときと同じ文字列）。
 *   それでも "</think>" が出たら、そこまでを本文から落とす。
 * - 1 要求ごとに KV キャッシュを空にしてから流す（会話の続きを覚えない。OpenAI API と同じく毎回全文が来る）。
 * - llama.cpp の呼び出しはすべて専用の計算スレッド（スタック 64MB）で行う。clay の HTTP ハンドラは
 *   256KB スタックのスレッドで並行に動くので、ハンドラは仕事を 1 件渡して終わるまで待つだけ
 *   （= 生成は 1 件ずつ直列）。embeddings-server の embshim.c と同じ作り。
 */
#include "chatshim.h"

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "llama.h"

enum { JOB_GENERATE = 1, JOB_COUNT = 2 };

struct chat_job {
    int kind;
    const char *msgs;
    int64_t max_tokens;
    int64_t temp_milli;
    char *out;
    int64_t cap;
    int64_t result;
    int done;
};

static struct llama_model *g_model;
static struct llama_context *g_ctx;
static const struct llama_vocab *g_vocab;
static const char *g_tmpl;
static int32_t g_n_ctx;
static int g_no_think; /* テンプレートが enable_thinking を持つ */

static pthread_mutex_t g_submit = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t g_job_ready = PTHREAD_COND_INITIALIZER;
static pthread_cond_t g_job_done = PTHREAD_COND_INITIALIZER;
static struct chat_job *g_pending;

static void log_warn_only(enum ggml_log_level level, const char *text, void *user_data) {
    (void)user_data;
    if (level >= GGML_LOG_LEVEL_WARN) {
        fputs(text, stderr);
    }
}

/* "role\x1Fcontent\x1E..." を llama_chat_message の配列にする。n を返す（呼び出し側が free_msgs する）。 */
static int parse_msgs(const char *msgs, llama_chat_message **out) {
    int cap = 8, n = 0;
    llama_chat_message *arr = malloc(sizeof(*arr) * (size_t)cap);
    const char *p = msgs;
    while (*p) {
        const char *rs = strchr(p, '\x1e');
        const char *end = rs ? rs : p + strlen(p);
        const char *us = memchr(p, '\x1f', (size_t)(end - p));
        if (us) {
            if (n == cap) {
                cap *= 2;
                arr = realloc(arr, sizeof(*arr) * (size_t)cap);
            }
            arr[n].role = strndup(p, (size_t)(us - p));
            arr[n].content = strndup(us + 1, (size_t)(end - us - 1));
            n++;
        }
        p = rs ? rs + 1 : end;
    }
    *out = arr;
    return n;
}

static void free_msgs(llama_chat_message *arr, int n) {
    for (int i = 0; i < n; i++) {
        free((void *)arr[i].role);
        free((void *)arr[i].content);
    }
    free(arr);
}

/* テンプレートを当てたプロンプト（malloc）。失敗なら NULL */
static char *apply_template(const char *msgs) {
    llama_chat_message *arr;
    int n = parse_msgs(msgs, &arr);
    if (n == 0) {
        free(arr);
        return NULL;
    }
    int32_t len = 4096;
    char *buf = malloc((size_t)len);
    int32_t need = llama_chat_apply_template(g_tmpl, arr, (size_t)n, true, buf, len);
    if (need > len) {
        buf = realloc(buf, (size_t)need + 1);
        need = llama_chat_apply_template(g_tmpl, arr, (size_t)n, true, buf, need + 1);
    }
    free_msgs(arr, n);
    if (need < 0) {
        free(buf);
        return NULL;
    }
    buf[need] = '\0';
    if (g_no_think) {
        static const char empty_think[] = "<think>\n\n</think>\n\n";
        buf = realloc(buf, (size_t)need + sizeof(empty_think));
        memcpy(buf + need, empty_think, sizeof(empty_think));
    }
    return buf;
}

/* 本文に "</think>" があれば、そこまで（と直後の空白）を落とす。新しい長さを返す */
static int64_t drop_thinking(char *s, int64_t n) {
    static const char tag[] = "</think>";
    const int64_t tl = (int64_t)sizeof(tag) - 1;
    for (int64_t i = n - tl; i >= 0; i--) {
        if (memcmp(s + i, tag, (size_t)tl) == 0) {
            int64_t j = i + tl;
            while (j < n && (s[j] == '\n' || s[j] == ' ' || s[j] == '\r' || s[j] == '\t')) {
                j++;
            }
            memmove(s, s + j, (size_t)(n - j));
            return n - j;
        }
    }
    return n;
}

/* プロンプトをトークン列にする（malloc、*n に個数）。BOS はテンプレートに無ければ足す。 */
static llama_token *tokenize(const char *prompt, int32_t *n) {
    int32_t len = (int32_t)strlen(prompt);
    int32_t need = -llama_tokenize(g_vocab, prompt, len, NULL, 0, true, true);
    llama_token *toks = malloc(sizeof(llama_token) * (size_t)(need > 0 ? need : 1));
    *n = llama_tokenize(g_vocab, prompt, len, toks, need, true, true);
    return toks;
}

/* 末尾の途中で切れた UTF-8 の文字を落とす */
static int64_t trim_utf8(const char *s, int64_t n) {
    int64_t i = n;
    int back = 0;
    while (i > 0 && back < 4 && ((unsigned char)s[i - 1] & 0xC0) == 0x80) {
        i--;
        back++;
    }
    if (i == 0) {
        return n;
    }
    unsigned char lead = (unsigned char)s[i - 1];
    int want = lead >= 0xF0 ? 4 : lead >= 0xE0 ? 3 : lead >= 0xC0 ? 2 : 1;
    return (want == back + 1) ? n : i - 1;
}

static int64_t run_count(const char *msgs) {
    char *prompt = apply_template(msgs);
    if (prompt == NULL) {
        return -2;
    }
    int32_t n;
    llama_token *toks = tokenize(prompt, &n);
    free(prompt);
    free(toks);
    return n;
}

static int64_t run_generate(const struct chat_job *job) {
    if (job->msgs[0] == '\0') {
        return -1;
    }
    char *prompt = apply_template(job->msgs);
    if (prompt == NULL) {
        return -2;
    }
    int32_t n_prompt;
    llama_token *toks = tokenize(prompt, &n_prompt);
    free(prompt);
    if (n_prompt <= 0 || n_prompt + 1 > g_n_ctx) {
        free(toks);
        return -3;
    }
    int64_t max_new = job->max_tokens;
    if (max_new > g_n_ctx - n_prompt) {
        max_new = g_n_ctx - n_prompt;
    }

    struct llama_sampler *smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
    if (job->temp_milli <= 0) {
        llama_sampler_chain_add(smpl, llama_sampler_init_greedy());
    } else {
        /* top_k 20 / top_p 0.8 は Qwen3 系が考えない生成に勧める値。無いと Ornith は日本語に中国語が混ざる */
        llama_sampler_chain_add(smpl, llama_sampler_init_top_k(20));
        llama_sampler_chain_add(smpl, llama_sampler_init_top_p(0.8f, 1));
        llama_sampler_chain_add(smpl, llama_sampler_init_min_p(0.05f, 1));
        llama_sampler_chain_add(smpl, llama_sampler_init_temp((float)job->temp_milli / 1000.0f));
        llama_sampler_chain_add(smpl, llama_sampler_init_dist((uint32_t)time(NULL)));
    }

    llama_memory_clear(llama_get_memory(g_ctx), true);
    const int64_t head = 16;
    int64_t pos = head;
    int64_t n_gen = 0;
    char finish = 's';
    int64_t result = 0;
    llama_batch batch = llama_batch_get_one(toks, n_prompt);
    llama_token tok;
    for (;;) {
        if (llama_decode(g_ctx, batch) != 0) {
            result = -4;
            break;
        }
        tok = llama_sampler_sample(smpl, g_ctx, -1);
        if (llama_vocab_is_eog(g_vocab, tok)) {
            break;
        }
        char piece[256];
        int m = llama_token_to_piece(g_vocab, tok, piece, sizeof(piece), 0, false);
        if (m < 0) {
            m = 0;
        }
        if (pos + m >= job->cap) {
            finish = 'l';
            break;
        }
        memcpy(job->out + pos, piece, (size_t)m);
        pos += m;
        n_gen++;
        if (n_gen >= max_new) {
            finish = 'l';
            break;
        }
        batch = llama_batch_get_one(&tok, 1);
    }
    llama_sampler_free(smpl);
    free(toks);
    if (result < 0) {
        return result;
    }
    pos = head + trim_utf8(job->out + head, pos - head);
    if (g_no_think) {
        pos = head + drop_thinking(job->out + head, pos - head);
    }
    char h[17];
    snprintf(h, sizeof(h), "%06d %06d %c\n", (int)n_prompt, (int)n_gen, finish);
    memcpy(job->out, h, (size_t)head);
    job->out[pos] = '\0';
    return pos;
}

static void *worker(void *arg) {
    (void)arg;
    for (;;) {
        pthread_mutex_lock(&g_mu);
        while (g_pending == NULL) {
            pthread_cond_wait(&g_job_ready, &g_mu);
        }
        struct chat_job *job = g_pending;
        pthread_mutex_unlock(&g_mu);

        job->result = job->kind == JOB_COUNT ? run_count(job->msgs) : run_generate(job);

        pthread_mutex_lock(&g_mu);
        job->done = 1;
        g_pending = NULL;
        pthread_cond_broadcast(&g_job_done);
        pthread_mutex_unlock(&g_mu);
    }
    return NULL;
}

static int64_t submit(struct chat_job *job) {
    pthread_mutex_lock(&g_submit);
    pthread_mutex_lock(&g_mu);
    g_pending = job;
    pthread_cond_signal(&g_job_ready);
    while (!job->done) {
        pthread_cond_wait(&g_job_done, &g_mu);
    }
    pthread_mutex_unlock(&g_mu);
    pthread_mutex_unlock(&g_submit);
    return job->result;
}

/* llama.cpp が層を載せる先（GPU / IGPU）を stderr に出す */
static void report_devices(int64_t n_gpu_layers) {
    int found = 0;
    if (n_gpu_layers != 0) {
        for (size_t i = 0; i < ggml_backend_dev_count(); i++) {
            ggml_backend_dev_t dev = ggml_backend_dev_get(i);
            enum ggml_backend_dev_type t = ggml_backend_dev_type(dev);
            if (t == GGML_BACKEND_DEVICE_TYPE_GPU || t == GGML_BACKEND_DEVICE_TYPE_IGPU) {
                fprintf(stderr, "chatshim: gpu %s (%s)\n", ggml_backend_dev_name(dev), ggml_backend_dev_description(dev));
                found = 1;
            }
        }
    }
    if (!found) {
        fputs(n_gpu_layers == 0 ? "chatshim: cpu only (CHAT_GPU_LAYERS=0)\n" : "chatshim: no gpu found, cpu only\n", stderr);
    }
}

int64_t chat_load(char *path, int64_t n_ctx, int64_t n_threads, int64_t n_gpu_layers) {
    llama_log_set(log_warn_only, NULL);
    ggml_backend_load_all();
    llama_backend_init();
    report_devices(n_gpu_layers);

    struct llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = (int32_t)n_gpu_layers; /* 負数 = 全層 */
    g_model = llama_model_load_from_file(path, mp);
    if (g_model == NULL) {
        return -1;
    }
    struct llama_context_params cp = llama_context_default_params();
    cp.n_ctx = (uint32_t)n_ctx;
    cp.n_batch = (uint32_t)n_ctx; /* プロンプト全体を 1 回の decode で流す */
    cp.n_threads = (int32_t)n_threads;
    cp.n_threads_batch = (int32_t)n_threads;
    cp.no_perf = true;
    g_ctx = llama_init_from_model(g_model, cp);
    if (g_ctx == NULL) {
        return -2;
    }
    g_vocab = llama_model_get_vocab(g_model);
    g_n_ctx = (int32_t)llama_n_ctx(g_ctx);
    g_tmpl = llama_model_chat_template(g_model, NULL);
    if (g_tmpl == NULL) {
        g_tmpl = "chatml";
        fputs("chatshim: the model has no chat template, using chatml\n", stderr);
    }
    g_no_think = strstr(g_tmpl, "enable_thinking") != NULL;
    if (g_no_think) {
        fputs("chatshim: template has enable_thinking; generating with thinking off\n", stderr);
    }

    pthread_attr_t attr;
    pthread_t th;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, (size_t)64 << 20);
    pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
    if (pthread_create(&th, &attr, worker, NULL) != 0) {
        return -3;
    }
    pthread_attr_destroy(&attr);
    return g_n_ctx;
}

int64_t chat_generate(char *msgs, int64_t max_tokens, int64_t temp_milli, char *out, int64_t cap) {
    struct chat_job job = {JOB_GENERATE, msgs, max_tokens, temp_milli, out, cap, 0, 0};
    return submit(&job);
}

int64_t chat_count_tokens(char *msgs) {
    struct chat_job job = {JOB_COUNT, msgs, 0, 0, NULL, 0, 0, 0};
    return submit(&job);
}
