// alternativas.cpp: a vencedora e a referência de 29/09 (copiadas do programa publicado, sem mudança) contra alternativas
// existentes, com o mesmo medidor do programa publicado (blocos alternados de 256 vetores, ciclos pelo rdtsc, a razão de cada
// repetição é a mediana das razões dos blocos, a razão final é a mediana das repetições) e a mesma conferência exaustiva
// (os 8^8 vetores com valores de 0 a 7), mais 10 milhões de vetores int32 sorteados contra o std::sort.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <vector>
#include <x86intrin.h>
#include <immintrin.h>
#define N 8
#include "redes_29-09.inc"
// o std::sort da biblioteca
__attribute__((noinline)) static void padrao_(int32_t *v) { std::sort(v, v + N); }
// a rede bitônica de 8 elementos num registrador de 256 bits (AVX2): 6 níveis, cada um troca, mínimo, máximo e mistura
__attribute__((noinline)) static void avx2_(int32_t *p) {
    __m256i v = _mm256_loadu_si256((const __m256i *)p), t, a, b;
    t = _mm256_shuffle_epi32(v, 0xB1); a = _mm256_min_epi32(v, t); b = _mm256_max_epi32(v, t); v = _mm256_blend_epi32(a, b, 0x66);
    t = _mm256_shuffle_epi32(v, 0x4E); a = _mm256_min_epi32(v, t); b = _mm256_max_epi32(v, t); v = _mm256_blend_epi32(a, b, 0x3C);
    t = _mm256_shuffle_epi32(v, 0xB1); a = _mm256_min_epi32(v, t); b = _mm256_max_epi32(v, t); v = _mm256_blend_epi32(a, b, 0x5A);
    t = _mm256_permute4x64_epi64(v, 0x4E); a = _mm256_min_epi32(v, t); b = _mm256_max_epi32(v, t); v = _mm256_blend_epi32(a, b, 0xF0);
    t = _mm256_shuffle_epi32(v, 0x4E); a = _mm256_min_epi32(v, t); b = _mm256_max_epi32(v, t); v = _mm256_blend_epi32(a, b, 0xCC);
    t = _mm256_shuffle_epi32(v, 0xB1); a = _mm256_min_epi32(v, t); b = _mm256_max_epi32(v, t); v = _mm256_blend_epi32(a, b, 0xAA);
    _mm256_storeu_si256((__m256i *)p, v);
}
// a mesma rede com AVX-512VL: o máximo mascarado faz a mistura (3 instruções por nível)
__attribute__((noinline)) static void avx512_(int32_t *p) {
    __m256i v = _mm256_loadu_si256((const __m256i *)p), t, a;
    t = _mm256_shuffle_epi32(v, 0xB1); a = _mm256_min_epi32(v, t); v = _mm256_mask_max_epi32(a, 0x66, v, t);
    t = _mm256_shuffle_epi32(v, 0x4E); a = _mm256_min_epi32(v, t); v = _mm256_mask_max_epi32(a, 0x3C, v, t);
    t = _mm256_shuffle_epi32(v, 0xB1); a = _mm256_min_epi32(v, t); v = _mm256_mask_max_epi32(a, 0x5A, v, t);
    t = _mm256_permute4x64_epi64(v, 0x4E); a = _mm256_min_epi32(v, t); v = _mm256_mask_max_epi32(a, 0xF0, v, t);
    t = _mm256_shuffle_epi32(v, 0x4E); a = _mm256_min_epi32(v, t); v = _mm256_mask_max_epi32(a, 0xCC, v, t);
    t = _mm256_shuffle_epi32(v, 0xB1); a = _mm256_min_epi32(v, t); v = _mm256_mask_max_epi32(a, 0xAA, v, t);
    _mm256_storeu_si256((__m256i *)p, v);
}
static double agora() { timespec q; clock_gettime(CLOCK_MONOTONIC, &q); return q.tv_sec + q.tv_nsec * 1e-9; }
static uint64_t rs = 88172645463325252ULL;
static inline uint64_t rnd() { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static double mediana(std::vector<double> x) { std::sort(x.begin(), x.end()); return x[x.size() / 2]; }
static double quartil(std::vector<double> x, double q) { std::sort(x.begin(), x.end()); return x[(size_t)(q * (x.size() - 1))]; }
template <void (*F)(int32_t *)> static void passada(const int32_t *dados, int m, uint64_t *soma) {
    int32_t v[N];
    for (int k = 0; k < m; k++) { memcpy(v, dados + (size_t)k * N, sizeof(v)); F(v); *soma += (uint32_t)v[0] * 3u + (uint32_t)v[N - 1] + (uint32_t)v[N / 2]; }
}
template <void (*F)(int32_t *)> static long long conferir() {
    long long total = 1, erros = 0; for (int q = 0; q < N; q++) total *= N;
    int32_t v[N];
    for (long long c = 0; c < total; c++) {
        long long x = c; int cont[N] = {0}, cont2[N] = {0};
        for (int q = 0; q < N; q++) { v[q] = (int32_t)(x % N); x /= N; cont[v[q]]++; }
        F(v); int ok = 1;
        for (int q = 1; q < N; q++) if (v[q - 1] > v[q]) ok = 0;
        for (int q = 0; q < N; q++) { if (v[q] < 0 || v[q] >= N) { ok = 0; break; } cont2[v[q]]++; }
        for (int q = 0; q < N && ok; q++) if (cont[q] != cont2[q]) ok = 0;
        if (!ok) erros++;
    }
    for (int k = 0; k < 10000000; k++) {               // int32 sorteados, inclusive extremos, contra o std::sort
        int32_t w[N];
        for (int q = 0; q < N; q++) { uint64_t r = rnd(); w[q] = (r & 7) == 0 ? (int32_t)(r >> 32 & 1 ? 0x7fffffff : 0x80000000u) : (int32_t)(r >> 32); v[q] = w[q]; }
        F(v); std::sort(w, w + N); if (memcmp(v, w, sizeof(w))) erros++;
    }
    return erros;
}
const int BL = 256, NB = 256, M = BL * NB;
static std::vector<int32_t> dados;
template <void (*F)(int32_t *)> static void medir(const char *nome, int R) {
    uint64_t soma = 0;
    for (int w = 0; w < 3; w++) { passada<F>(dados.data(), M, &soma); passada<refe>(dados.data(), M, &soma); passada<refe2>(dados.data(), M, &soma); }
    std::vector<double> rc, rr, tc, tr;
    for (int r = 0; r < R; r++) {
        std::vector<double> bc, br;
        for (int b = 0; b < NB; b++) {
            const int32_t *d = dados.data() + (size_t)b * BL * N; uint64_t c0, c1, r0, r1, s0, s1; int o = (b + r) % 3;
            if (o == 0) { c0 = __rdtsc(); passada<F>(d, BL, &soma); c1 = __rdtsc(); r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); }
            else if (o == 1) { r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); c0 = __rdtsc(); passada<F>(d, BL, &soma); c1 = __rdtsc(); }
            else { s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); c0 = __rdtsc(); passada<F>(d, BL, &soma); c1 = __rdtsc(); r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); }
            bc.push_back((double)(c1 - c0) / (double)(r1 - r0)); br.push_back((double)(s1 - s0) / (double)(r1 - r0));
            tc.push_back((double)(c1 - c0)); tr.push_back((double)(r1 - r0));
        }
        rc.push_back(mediana(bc)); rr.push_back(mediana(br));
    }
    double razao = mediana(rc);
    printf("{\"rotina\": \"%s\", \"tiques_por_vetor\": %.3f, \"tiques_referencia\": %.3f, \"razao_vs_rede\": %.5f, \"razao_ref_contra_ref\": %.5f, \"ruido\": %.5f, \"soma\": %llu}\n",
           nome, mediana(tc) / BL, mediana(tr) / BL, razao, mediana(rr), (quartil(rc, 0.75) - quartil(rc, 0.25)) / razao, (unsigned long long)(soma & 0xffff));
    fflush(stdout);
}
int main(int argc, char **argv) {
    int R = argc > 1 ? atoi(argv[1]) : 21;
    printf("{\"erros\": {\"vencedora\": %lld, \"referencia\": %lld, \"std_sort\": %lld, \"avx2\": %lld, \"avx512\": %lld}}\n",
           conferir<cand_>(), conferir<refe_>(), conferir<padrao_>(), conferir<avx2_>(), conferir<avx512_>());
    dados.resize((size_t)M * N);
    for (int k = 0; k < M; k++) for (int q = 0; q < N; q++) dados[(size_t)k * N + q] = (k & 1) ? (int32_t)(rnd() % 4) : (int32_t)rnd();
    medir<cand_>("vencedora_29-09", R); medir<padrao_>("std_sort", R); medir<avx2_>("avx2_bitonica", R); medir<avx512_>("avx512_bitonica", R); medir<refe2_>("copia_da_referencia", R);
    return 0;
}
