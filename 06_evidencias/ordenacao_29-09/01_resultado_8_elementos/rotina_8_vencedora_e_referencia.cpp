#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <vector>
#include <x86intrin.h>
#define N 8
__attribute__((noinline)) static void cand_(int32_t *v) { { int32_t a = v[4], b = v[6]; v[4] = a < b ? a : b; v[6] = a < b ? b : a; } { int32_t a = v[5], b = v[7]; v[5] = a < b ? a : b; v[7] = a < b ? b : a; } { int32_t a = v[1], b = v[3]; v[1] = a < b ? a : b; v[3] = a < b ? b : a; } { int32_t a = v[0], b = v[2]; v[0] = a < b ? a : b; v[2] = a < b ? b : a; } { int32_t a = v[2], b = v[6]; v[2] = a < b ? a : b; v[6] = a < b ? b : a; } { int32_t a = v[1], b = v[5]; v[1] = a < b ? a : b; v[5] = a < b ? b : a; } { int32_t a = v[3], b = v[7]; v[3] = a < b ? a : b; v[7] = a < b ? b : a; } { int32_t a = v[0], b = v[4]; v[0] = a < b ? a : b; v[4] = a < b ? b : a; } { int32_t a = v[6], b = v[7]; v[6] = a < b ? a : b; v[7] = a < b ? b : a; } { int32_t a = v[0], b = v[1]; v[0] = a < b ? a : b; v[1] = a < b ? b : a; } { int32_t a = v[4], b = v[5]; v[4] = a < b ? a : b; v[5] = a < b ? b : a; } { int32_t a = v[2], b = v[3]; v[2] = a < b ? a : b; v[3] = a < b ? b : a; } { int32_t a = v[3], b = v[5]; v[3] = a < b ? a : b; v[5] = a < b ? b : a; } { int32_t a = v[2], b = v[4]; v[2] = a < b ? a : b; v[4] = a < b ? b : a; } { int32_t a = v[3], b = v[6]; v[3] = a < b ? a : b; v[6] = a < b ? b : a; } { int32_t a = v[1], b = v[4]; v[1] = a < b ? a : b; v[4] = a < b ? b : a; } { int32_t a = v[3], b = v[4]; v[3] = a < b ? a : b; v[4] = a < b ? b : a; } { int32_t a = v[1], b = v[2]; v[1] = a < b ? a : b; v[2] = a < b ? b : a; } { int32_t a = v[5], b = v[6]; v[5] = a < b ? a : b; v[6] = a < b ? b : a; } }
static inline void cand(int32_t *v) { cand_(v); }
__attribute__((noinline)) static void refe_(int32_t *v) { int32_t x0 = v[0]; int32_t x1 = v[1]; int32_t x2 = v[2]; int32_t x3 = v[3]; int32_t x4 = v[4]; int32_t x5 = v[5]; int32_t x6 = v[6]; int32_t x7 = v[7]; { int32_t a = x0, b = x2; x0 = a < b ? a : b; x2 = a < b ? b : a; } { int32_t a = x1, b = x3; x1 = a < b ? a : b; x3 = a < b ? b : a; } { int32_t a = x4, b = x6; x4 = a < b ? a : b; x6 = a < b ? b : a; } { int32_t a = x5, b = x7; x5 = a < b ? a : b; x7 = a < b ? b : a; } { int32_t a = x0, b = x4; x0 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x1, b = x5; x1 = a < b ? a : b; x5 = a < b ? b : a; } { int32_t a = x2, b = x6; x2 = a < b ? a : b; x6 = a < b ? b : a; } { int32_t a = x3, b = x7; x3 = a < b ? a : b; x7 = a < b ? b : a; } { int32_t a = x0, b = x1; x0 = a < b ? a : b; x1 = a < b ? b : a; } { int32_t a = x2, b = x3; x2 = a < b ? a : b; x3 = a < b ? b : a; } { int32_t a = x4, b = x5; x4 = a < b ? a : b; x5 = a < b ? b : a; } { int32_t a = x6, b = x7; x6 = a < b ? a : b; x7 = a < b ? b : a; } { int32_t a = x2, b = x4; x2 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x3, b = x5; x3 = a < b ? a : b; x5 = a < b ? b : a; } { int32_t a = x1, b = x4; x1 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x3, b = x6; x3 = a < b ? a : b; x6 = a < b ? b : a; } { int32_t a = x1, b = x2; x1 = a < b ? a : b; x2 = a < b ? b : a; } { int32_t a = x3, b = x4; x3 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x5, b = x6; x5 = a < b ? a : b; x6 = a < b ? b : a; } v[0] = x0; v[1] = x1; v[2] = x2; v[3] = x3; v[4] = x4; v[5] = x5; v[6] = x6; v[7] = x7; }
static inline void refe(int32_t *v) { refe_(v); }
__attribute__((noinline)) static void refe2_(int32_t *v) { int32_t x0 = v[0]; int32_t x1 = v[1]; int32_t x2 = v[2]; int32_t x3 = v[3]; int32_t x4 = v[4]; int32_t x5 = v[5]; int32_t x6 = v[6]; int32_t x7 = v[7]; { int32_t a = x0, b = x2; x0 = a < b ? a : b; x2 = a < b ? b : a; } { int32_t a = x1, b = x3; x1 = a < b ? a : b; x3 = a < b ? b : a; } { int32_t a = x4, b = x6; x4 = a < b ? a : b; x6 = a < b ? b : a; } { int32_t a = x5, b = x7; x5 = a < b ? a : b; x7 = a < b ? b : a; } { int32_t a = x0, b = x4; x0 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x1, b = x5; x1 = a < b ? a : b; x5 = a < b ? b : a; } { int32_t a = x2, b = x6; x2 = a < b ? a : b; x6 = a < b ? b : a; } { int32_t a = x3, b = x7; x3 = a < b ? a : b; x7 = a < b ? b : a; } { int32_t a = x0, b = x1; x0 = a < b ? a : b; x1 = a < b ? b : a; } { int32_t a = x2, b = x3; x2 = a < b ? a : b; x3 = a < b ? b : a; } { int32_t a = x4, b = x5; x4 = a < b ? a : b; x5 = a < b ? b : a; } { int32_t a = x6, b = x7; x6 = a < b ? a : b; x7 = a < b ? b : a; } { int32_t a = x2, b = x4; x2 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x3, b = x5; x3 = a < b ? a : b; x5 = a < b ? b : a; } { int32_t a = x1, b = x4; x1 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x3, b = x6; x3 = a < b ? a : b; x6 = a < b ? b : a; } { int32_t a = x1, b = x2; x1 = a < b ? a : b; x2 = a < b ? b : a; } { int32_t a = x3, b = x4; x3 = a < b ? a : b; x4 = a < b ? b : a; } { int32_t a = x5, b = x6; x5 = a < b ? a : b; x6 = a < b ? b : a; } v[0] = x0; v[1] = x1; v[2] = x2; v[3] = x3; v[4] = x4; v[5] = x5; v[6] = x6; v[7] = x7; }
static inline void refe2(int32_t *v) { refe2_(v); }
static inline void padrao(int32_t *v) { std::sort(v, v + N); }
static double agora() { timespec q; clock_gettime(CLOCK_MONOTONIC, &q); return q.tv_sec + q.tv_nsec * 1e-9; }
static uint64_t rs = 88172645463325252ULL;
static inline uint64_t rnd() { rs ^= rs << 13; rs ^= rs >> 7; rs ^= rs << 17; return rs; }
static double mediana(std::vector<double> x) { std::sort(x.begin(), x.end()); return x[x.size() / 2]; }
static double quartil(std::vector<double> x, double q) { std::sort(x.begin(), x.end()); return x[(size_t)(q * (x.size() - 1))]; }
template <void (*F)(int32_t *)> static double passada(const int32_t *dados, int m, uint64_t *soma) {
    int32_t v[N];
    double t0 = agora();
    for (int k = 0; k < m; k++) {
        memcpy(v, dados + (size_t)k * N, sizeof(v));
        F(v);
        *soma += (uint32_t)v[0] * 3u + (uint32_t)v[N - 1] + (uint32_t)v[N / 2];
    }
    return agora() - t0;
}
int main(int argc, char **argv) {
    int R = argc > 1 ? atoi(argv[1]) : 21;
    /* V: todos os n^n vetores com valores 0..n-1 */
    long long total = 1, erros = 0;
    for (int q = 0; q < N; q++) total *= N;
    int32_t v[N];
    for (long long c = 0; c < total; c++) {
        long long x = c;
        for (int q = 0; q < N; q++) { v[q] = (int32_t)(x % N); x /= N; }
        int cont[N] = {0};
        for (int q = 0; q < N; q++) cont[v[q]]++;
        cand(v);
        int ok = 1;
        for (int q = 1; q < N; q++) if (v[q - 1] > v[q]) ok = 0;
        int cont2[N] = {0};
        for (int q = 0; q < N; q++) { if (v[q] < 0 || v[q] >= N) { ok = 0; break; } cont2[v[q]]++; }
        for (int q = 0; q < N && ok; q++) if (cont[q] != cont2[q]) ok = 0;
        if (!ok) erros++;
    }
    /* o tempo, em ciclos, em blocos alternados: em cada repetição, cada bloco de 256 vetores passa pelo candidato, pela referência e por
       uma cópia idêntica da referência, em ordem que gira; a razão de cada repetição é a mediana das razões dos blocos. A razão da
       referência contra a cópia dela mesma mede o que o meio distorce sozinho (alinhamento, cache, vizinhos) e é o piso do distinguível. */
    const int BL = 256, NB = 256, M = BL * NB;
    std::vector<int32_t> dados((size_t)M * N);
    for (int k = 0; k < M; k++) for (int q = 0; q < N; q++)
        dados[(size_t)k * N + q] = (k & 1) ? (int32_t)(rnd() % 4) : (int32_t)rnd();
    uint64_t soma = 0;
    for (int w = 0; w < 3; w++) { passada<cand>(dados.data(), M, &soma); passada<refe>(dados.data(), M, &soma); passada<refe2>(dados.data(), M, &soma); }
    std::vector<double> rc, rr, tcand, tref, tpad;
    for (int r = 0; r < R; r++) {
        std::vector<double> bc, br;
        for (int b = 0; b < NB; b++) {
            const int32_t *d = dados.data() + (size_t)b * BL * N;
            uint64_t c0, c1, r0, r1, s0, s1;
            int o = (b + r) % 3;
            if (o == 0) { c0 = __rdtsc(); passada<cand>(d, BL, &soma); c1 = __rdtsc(); r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); }
            else if (o == 1) { r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); c0 = __rdtsc(); passada<cand>(d, BL, &soma); c1 = __rdtsc(); }
            else { s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); c0 = __rdtsc(); passada<cand>(d, BL, &soma); c1 = __rdtsc(); r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); }
            bc.push_back((double)(c1 - c0) / (double)(r1 - r0));
            br.push_back((double)(s1 - s0) / (double)(r1 - r0));
            tcand.push_back((double)(c1 - c0)); tref.push_back((double)(r1 - r0));
        }
        rc.push_back(mediana(bc)); rr.push_back(mediana(br));
        if (r % 5 == 0) tpad.push_back(passada<padrao>(dados.data(), BL * 16, &soma) / (BL * 16));
    }
    double razao = mediana(rc), piso = mediana(rr);
    double ruido = (quartil(rc, 0.75) - quartil(rc, 0.25)) / razao;
    printf("{\"erro_de_ordenacao\": %.9f, \"vetores_conferidos\": %lld, \"ciclos_por_vetor\": %.3f, \"ciclos_referencia\": %.3f, \"ns_std_sort\": %.3f, "
           "\"razao_vs_rede\": %.5f, \"razao_ref_contra_ref\": %.5f, \"ruido\": %.5f, \"soma\": %llu}\n",
           (double)erros / total, total, mediana(tcand) / BL, mediana(tref) / BL, mediana(tpad) * 1e9, razao, piso, ruido, (unsigned long long)(soma & 0xffff));
    return 0;
}
