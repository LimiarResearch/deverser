"""Ferramenta declarada do executor (emenda 3 do motor, 29/09/2026): o medidor das rotinas curtas de ordenação.

O candidato passa só uma descrição estruturada: n, a lista de comparadores (pares de posições), a variante de cada troca e se os valores
ficam em registradores. Esta ferramenta gera o C++ a partir disso (o candidato nunca manda código para o compilador), compila com o g++
declarado por caminho e sha256 (FERRAMENTA_GXX e FERRAMENTA_GXX_SHA256), confere V e mede o tempo no mesmo processo que as referências:
- V exaustivo: todos os n^n vetores com valores de 0 a n-1 (cobrem todas as ordens com empate); o erro é a fração que sai fora de ordem;
- o tempo: a mediana de R passadas alternadas sobre 16.384 vetores fixos (metade com valores de 32 bits, metade com muitos empates),
  contra a rede de referência (a melhor rede conhecida, com a troca mais simples) e contra o std::sort do libstdc++;
- o ruído: a dispersão (p75 - p25) / mediana das passadas da referência, que decide o que é distinguível.
"""
import hashlib
import json
import os
import subprocess
import tempfile

VARIANTES = {
    "ternario": "{{ int32_t a = {A}, b = {B}; {A} = a < b ? a : b; {B} = a < b ? b : a; }}",
    "minmax": "{{ int32_t a = {A}, b = {B}; {A} = std::min(a, b); {B} = std::max(a, b); }}",
    "mascara": "{{ int32_t a = {A}, b = {B}; int32_t d = (a ^ b) & -(int32_t)(b < a); {A} = a ^ d; {B} = b ^ d; }}",
}
MOLDE = r'''#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <vector>
#include <x86intrin.h>
#include <immintrin.h>
#include <climits>
#define N __N__
__attribute__((noinline)) static void cand_(int32_t *v) { __CAND__ }
static inline void cand(int32_t *v) { cand_(v); }
__attribute__((noinline)) static void refe_(int32_t *v) { __REFE__ }
static inline void refe(int32_t *v) { refe_(v); }
__attribute__((noinline)) static void refe2_(int32_t *v) { __REFE__ }
__attribute__((noinline)) static void refs_(int32_t *v) { __REFS__ }
static inline void refs(int32_t *v) { refs_(v); }
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
    std::vector<double> rc, rr, rs2, tcand, tref, tsimd, tpad;
    for (int r = 0; r < R; r++) {
        std::vector<double> bc, br, bs;
        for (int b = 0; b < NB; b++) {
            const int32_t *d = dados.data() + (size_t)b * BL * N;
            uint64_t c0, c1, r0, r1, s0, s1;
            int o = (b + r) % 3;
            if (o == 0) { c0 = __rdtsc(); passada<cand>(d, BL, &soma); c1 = __rdtsc(); r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); }
            else if (o == 1) { r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); c0 = __rdtsc(); passada<cand>(d, BL, &soma); c1 = __rdtsc(); }
            else { s0 = __rdtsc(); passada<refe2>(d, BL, &soma); s1 = __rdtsc(); c0 = __rdtsc(); passada<cand>(d, BL, &soma); c1 = __rdtsc(); r0 = __rdtsc(); passada<refe>(d, BL, &soma); r1 = __rdtsc(); }
            uint64_t q0 = __rdtsc(); passada<refs>(d, BL, &soma); uint64_t q1 = __rdtsc();
            bs.push_back((double)(c1 - c0) / (double)(q1 - q0));
            tsimd.push_back((double)(q1 - q0));
            bc.push_back((double)(c1 - c0) / (double)(r1 - r0));
            br.push_back((double)(s1 - s0) / (double)(r1 - r0));
            tcand.push_back((double)(c1 - c0)); tref.push_back((double)(r1 - r0));
        }
        rc.push_back(mediana(bc)); rr.push_back(mediana(br)); rs2.push_back(mediana(bs));
        if (r % 5 == 0) tpad.push_back(passada<padrao>(dados.data(), BL * 16, &soma) / (BL * 16));
    }
    double razao = mediana(rc), piso = mediana(rr), razao_simd = mediana(rs2);
    /* contra a referência mais rápida: a maior das duas razões */
    double melhor = razao < razao_simd ? razao_simd : razao;
    std::vector<double> &rm = razao < razao_simd ? rs2 : rc;
    double ruido = (quartil(rm, 0.75) - quartil(rm, 0.25)) / melhor;
    printf("{\"erro_de_ordenacao\": %.9f, \"vetores_conferidos\": %lld, \"ciclos_por_vetor\": %.3f, \"ciclos_referencia\": %.3f, \"ns_std_sort\": %.3f, "
           "\"razao_vs_rede\": %.5f, \"razao_vs_simd\": %.5f, \"razao_vs_melhor\": %.5f, \"ciclos_simd\": %.3f, \"razao_ref_contra_ref\": %.5f, \"ruido\": %.5f, \"soma\": %llu}\n",
           (double)erros / total, total, mediana(tcand) / BL, mediana(tref) / BL, mediana(tpad) * 1e9, razao, razao_simd, melhor, mediana(tsimd) / BL, piso, ruido, (unsigned long long)(soma & 0xffff));
    return 0;
}
'''


def _niveis(n, comps):
    ultimo, niveis = [0] * n, []
    for i, j in comps:
        nv = max(ultimo[i], ultimo[j]) + 1
        ultimo[i] = ultimo[j] = nv
        while len(niveis) < nv:
            niveis.append([])
        niveis[nv - 1].append((i, j))
    return niveis


def _simd(n, comps, imediato):
    """A rede em AVX2: os 8 valores num registrador de 256 bits; cada nível é uma permutação, um mínimo, um máximo e uma mistura. Com
    imediato, o nível que só troca dentro de cada metade de 128 bits usa o embaralhamento com constante, e a mistura usa a constante."""
    if n > 8:
        raise ValueError("o SIMD de 256 bits cabe até 8 elementos")
    # carga e gravação direto da memória (a versão de 29/09 02h30 montava um vetor temporário e travava o repasse gravação-leitura: 4x mais lenta)
    if n == 8:
        L = ["__m256i x = _mm256_loadu_si256((const __m256i *)v), p, lo, hi;"]
    else:
        m = ", ".join("-1" if q < n else "0" for q in range(8))
        L = [f"const __m256i m = _mm256_setr_epi32({m});",
             "__m256i x = _mm256_blendv_epi8(_mm256_set1_epi32(INT_MAX), _mm256_maskload_epi32(v, m), m), p, lo, hi;"]
    for nivel in _niveis(n, comps):
        perm, alto = list(range(8)), [0] * 8
        for i, j in nivel:
            perm[i], perm[j], alto[j] = j, i, 1
        dentro = all(perm[k] // 4 == k // 4 for k in range(8)) and all(perm[k + 4] - 4 == perm[k] for k in range(4))
        if imediato and dentro:
            L.append(f"p = _mm256_shuffle_epi32(x, {sum((perm[k] & 3) << (2 * k) for k in range(4))});")
        else:
            L.append("p = _mm256_permutevar8x32_epi32(x, _mm256_setr_epi32(" + ", ".join(map(str, perm)) + "));")
        L.append("lo = _mm256_min_epi32(x, p); hi = _mm256_max_epi32(x, p);")
        if imediato:
            L.append(f"x = _mm256_blend_epi32(lo, hi, {sum(b << k for k, b in enumerate(alto))});")
        else:
            L.append("x = _mm256_blendv_epi8(lo, hi, _mm256_setr_epi32(" + ", ".join("-1" if b else "0" for b in alto) + "));")
    L.append("_mm256_storeu_si256((__m256i *)v, x);" if n == 8 else "_mm256_maskstore_epi32(v, m, x);")
    return " ".join(L)


def _gxx():
    caminho, esperado = os.environ.get("FERRAMENTA_GXX"), os.environ.get("FERRAMENTA_GXX_SHA256")
    if not caminho or not esperado:
        raise RuntimeError("ferramenta não declarada: FERRAMENTA_GXX e FERRAMENTA_GXX_SHA256")
    with open(caminho, "rb") as f:
        visto = hashlib.sha256(f.read()).hexdigest()
    if visto != esperado:
        raise RuntimeError(f"o compilador mudou depois da declaração: sha256 {visto[:12]} contra {esperado[:12]}")
    return caminho


def disponivel():
    try:
        _gxx()
        return True
    except (RuntimeError, OSError):
        return False


def _corpo(n, comps, variante, registradores):
    if variante in ("simd", "simd_imediato"):
        return _simd(n, comps, variante == "simd_imediato")
    X = (lambda q: f"x{q}") if registradores else (lambda q: f"v[{q}]")
    linhas = []
    if registradores:
        linhas.append(" ".join(f"int32_t x{q} = v[{q}];" for q in range(n)))
    for i, j in comps:
        linhas.append(VARIANTES[variante].format(A=X(i), B=X(j)))
    if registradores:
        linhas.append(" ".join(f"v[{q}] = x{q};" for q in range(n)))
    return " ".join(linhas)


def normalizar(n, comparadores):
    out = []
    for c in comparadores:
        i, j = int(c[0]), int(c[1])
        if not (0 <= i < n and 0 <= j < n) or i == j:
            continue
        out.append((min(i, j), max(i, j)))
    return out[:96]


def medir(n, comparadores, variante, registradores, referencia, repeticoes=21):
    n = int(n)
    if not 2 <= n <= 10 or variante not in (*VARIANTES, "simd", "simd_imediato"):
        raise ValueError("n ou variante fora da ferramenta")
    comps, ref = normalizar(n, comparadores), normalizar(n, referencia)
    src = (MOLDE.replace("__N__", str(n)).replace("__CAND__", _corpo(n, comps, variante, bool(registradores)))
           .replace("__REFE__", _corpo(n, ref, "ternario", True)).replace("__REFS__", _simd(n, ref, False)))
    h = hashlib.sha256(src.encode()).hexdigest()[:24]
    pasta = os.path.join(tempfile.gettempdir(), f"ordenacao_{os.getuid() if hasattr(os, 'getuid') else 0}")
    os.makedirs(pasta, exist_ok=True)
    binario = os.path.join(pasta, h)
    if not os.path.exists(binario):
        fonte = binario + ".cpp"
        with open(fonte, "w") as f:
            f.write(src)
        r = subprocess.run([_gxx(), "-O2", "-march=native", "-std=c++17", "-falign-functions=64", "-falign-loops=64", fonte, "-o", binario + ".tmp"], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("a compilação falhou: " + r.stderr[-400:])
        os.replace(binario + ".tmp", binario)
    out = subprocess.run([binario, str(int(repeticoes))], capture_output=True, text=True, timeout=600)
    res = json.loads(out.stdout)
    res.update(comparadores=len(comps), fonte_sha256=h)
    return res
