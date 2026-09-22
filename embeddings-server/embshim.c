/*
 * embshim.h の実装。llama.cpp で gte-Qwen2 系の埋め込みを計算する。
 *
 * - gte-Qwen2 は「双方向アテンション + 末尾トークン(EOS)の隠れ状態」を文ベクトルにする。
 *   causal のまま計算すると別物になるので NON_CAUSAL を明示する。
 * - llama.cpp の呼び出しはすべて専用の計算スレッド（スタック 64MB）で行う。
 *   clay の HTTP ハンドラは 256KB スタックのスレッドで並行に動くので、そこから直接
 *   llama.cpp を呼ぶとスタック不足と同時アクセスの両方が起き得る。
 *   ハンドラは仕事を 1 件渡して終わるまで待つだけ（= 計算は 1 件ずつ直列）。
 * - GPU（Vulkan）があれば層を載せる。見つからなければ llama.cpp が CPU で計算する。
 *   どちらになったかは起動時に stderr（journal）に 1 行出す。
 */
#include "embshim.h"

#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "llama.h"

enum { JOB_COUNT = 1, JOB_EMBED = 2 };

struct emb_job {
    int kind;
    const char *text;
    int64_t dims;
    char *out;
    int64_t result;
    int done;
};

static struct llama_model *g_model;
static struct llama_context *g_ctx;
static const struct llama_vocab *g_vocab;
static struct llama_batch g_batch;
static llama_token *g_tokens;
static int32_t g_n_embd;
static int32_t g_n_ctx;

static pthread_mutex_t g_submit = PTHREAD_MUTEX_INITIALIZER; /* 依頼側を 1 人ずつにする */
static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t g_job_ready = PTHREAD_COND_INITIALIZER;
static pthread_cond_t g_job_done = PTHREAD_COND_INITIALIZER;
static struct emb_job *g_pending;

static void log_warn_only(enum ggml_log_level level, const char *text, void *user_data) {
    (void)user_data;
    if (level >= GGML_LOG_LEVEL_WARN) {
        fputs(text, stderr);
    }
}

/* 末尾に EOS を足したトークン列（GGUF の add_eos_token に従う）。足りなければ -(必要数) が返る。 */
static int32_t tokenize(const char *text) {
    return llama_tokenize(g_vocab, text, (int32_t)strlen(text), g_tokens, g_n_ctx, true, true);
}

static int64_t run_count(const char *text) {
    int32_t n = tokenize(text);
    return n < 0 ? -(int64_t)n : (int64_t)n;
}

static int64_t run_embed(const char *text, int64_t dims, char *out) {
    int32_t n = tokenize(text);
    if (n < 0) {
        return -1;
    }
    if (n == 0) {
        return -2;
    }
    g_batch.n_tokens = n;
    for (int32_t i = 0; i < n; i++) {
        g_batch.token[i] = g_tokens[i];
        g_batch.pos[i] = i;
        g_batch.n_seq_id[i] = 1;
        g_batch.seq_id[i][0] = 0;
        g_batch.logits[i] = 1; /* 双方向の埋め込みでは全トークンを出力扱いにする（llama.cpp の要求） */
    }
    llama_memory_clear(llama_get_memory(g_ctx), true);
    if (llama_decode(g_ctx, g_batch) != 0) {
        return -3;
    }
    const float *e = llama_get_embeddings_seq(g_ctx, 0);
    if (e == NULL) {
        return -4;
    }
    int64_t d = dims < g_n_embd ? dims : g_n_embd;
    double norm = 0.0;
    for (int64_t i = 0; i < d; i++) {
        norm += (double)e[i] * e[i];
    }
    norm = sqrt(norm);
    for (int64_t i = 0; i < d; i++) {
        float v = norm > 0 ? (float)(e[i] / norm) : 0.0f;
        memcpy(out + i * 4, &v, 4); /* x86-64 はリトルエンディアン */
    }
    return n;
}

static void *worker(void *arg) {
    (void)arg;
    for (;;) {
        pthread_mutex_lock(&g_mu);
        while (g_pending == NULL) {
            pthread_cond_wait(&g_job_ready, &g_mu);
        }
        struct emb_job *job = g_pending;
        pthread_mutex_unlock(&g_mu);

        job->result = job->kind == JOB_COUNT ? run_count(job->text) : run_embed(job->text, job->dims, job->out);

        pthread_mutex_lock(&g_mu);
        job->done = 1;
        g_pending = NULL;
        pthread_cond_broadcast(&g_job_done);
        pthread_mutex_unlock(&g_mu);
    }
    return NULL;
}

static int64_t submit(struct emb_job *job) {
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

/* llama.cpp が層を載せる先（GPU / IGPU）を stderr に出す。 */
static void report_devices(int64_t n_gpu_layers) {
    int found = 0;
    if (n_gpu_layers != 0) {
        for (size_t i = 0; i < ggml_backend_dev_count(); i++) {
            ggml_backend_dev_t dev = ggml_backend_dev_get(i);
            enum ggml_backend_dev_type t = ggml_backend_dev_type(dev);
            if (t == GGML_BACKEND_DEVICE_TYPE_GPU || t == GGML_BACKEND_DEVICE_TYPE_IGPU) {
                fprintf(stderr, "embshim: gpu %s (%s)\n", ggml_backend_dev_name(dev), ggml_backend_dev_description(dev));
                found = 1;
            }
        }
    }
    if (!found) {
        fputs(n_gpu_layers == 0 ? "embshim: cpu only (EMB_GPU_LAYERS=0)\n" : "embshim: no gpu found, cpu only\n", stderr);
    }
}

int64_t emb_load(char *path, int64_t n_ctx, int64_t n_threads, int64_t n_gpu_layers) {
    llama_log_set(log_warn_only, NULL);
    ggml_backend_load_all();
    llama_backend_init();
    report_devices(n_gpu_layers);

    struct llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = (int32_t)n_gpu_layers;  /* 負数 = 全層 */
    g_model = llama_model_load_from_file(path, mp);
    if (g_model == NULL) {
        return -1;
    }

    struct llama_context_params cp = llama_context_default_params();
    cp.n_ctx = (uint32_t)n_ctx;
    cp.n_batch = (uint32_t)n_ctx;  /* 双方向アテンションでは 1 入力を 1 ubatch に収める必要がある */
    cp.n_ubatch = (uint32_t)n_ctx;
    cp.n_seq_max = 1;
    cp.n_threads = (int32_t)n_threads;
    cp.n_threads_batch = (int32_t)n_threads;
    cp.embeddings = true;
    cp.pooling_type = LLAMA_POOLING_TYPE_LAST;
    cp.attention_type = LLAMA_ATTENTION_TYPE_NON_CAUSAL;
    cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_AUTO;
    g_ctx = llama_init_from_model(g_model, cp);
    if (g_ctx == NULL) {
        return -2;
    }

    g_vocab = llama_model_get_vocab(g_model);
    g_n_embd = llama_model_n_embd(g_model);
    g_n_ctx = (int32_t)n_ctx;
    g_tokens = (llama_token *)malloc(sizeof(llama_token) * (size_t)n_ctx);
    g_batch = llama_batch_init((int32_t)n_ctx, 0, 1);

    pthread_attr_t attr;
    pthread_t th;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, (size_t)64 << 20);
    pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
    if (pthread_create(&th, &attr, worker, NULL) != 0) {
        return -3;
    }
    pthread_attr_destroy(&attr);
    return g_n_embd;
}

int64_t emb_count_tokens(char *text) {
    struct emb_job job = {JOB_COUNT, text, 0, NULL, 0, 0};
    return submit(&job);
}

int64_t emb_embed(char *text, int64_t dims, char *out) {
    struct emb_job job = {JOB_EMBED, text, dims, out, 0, 0};
    return submit(&job);
}

int64_t emb_format_json(char *f32, int64_t n, char *out, int64_t cap) {
    int64_t pos = 0;
    if (cap < 2) {
        return -1;
    }
    out[pos++] = '[';
    for (int64_t i = 0; i < n; i++) {
        float v;
        memcpy(&v, f32 + i * 4, 4);
        int w = snprintf(out + pos, (size_t)(cap - pos), i == 0 ? "%.9g" : ",%.9g", (double)v);
        if (w < 0 || pos + w >= cap) {
            return -1;
        }
        pos += w;
    }
    if (pos + 1 >= cap) {
        return -1;
    }
    out[pos++] = ']';
    out[pos] = '\0';
    return pos;
}
