#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace {

constexpr float CL = 1000.0f;
constexpr float EPSF = 1.0e-6f;
constexpr float PASSO_MAX = 0.5f;
constexpr float PESO_MAX = 20.0f;
constexpr float TAXA_ENTRADA = 0.001f;
constexpr int MATURIDADE = 16;
constexpr int K_NOS = 8;
constexpr int N_OPS = 32;
constexpr int N_SECOES = 16;

enum Op { ADD = 0, SUB, MUL, DIV, MAX, MIN, NEG, ABS, SQ, SQRT, TANH, RELU, SIG, THR, SIGN, EXP, LOG, INV, AVG, K, MULK, ADDK, GT, ABSDIFF, MEAN0, MEAN1, CLIP1, EMA, SHRK, HYP, SEL, ID };
constexpr int ARIDADE[N_OPS] = {2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 0, 1, 1, 2, 2, 1, 1, 1, 2, 1, 2, 2, 1};

enum Secao { S_RETRO = 0, S_W_OCULTA, S_W_SAIDA, S_S1, S_S2, S_S3, S_U1, S_U2, S_REINIT, S_ATIVA, S_LIBERA, S_G1, S_G2, S_POL1, S_POL2, S_POL3 };

constexpr int N_IN_DA_SECAO[N_SECOES] = {13, 23, 23, 23, 23, 23, 14, 14, 14, 14, 14, 11, 11, 9, 9, 9};

enum Cls { CS = 0, CROW = 1, CCOL = 2, CRS = 3, CFULL = 4 };

static inline float clampf(float x, float lo, float hi) { return x < lo ? lo : (x > hi ? hi : x); }

static inline float vexp(float x) {
    x = x < -87.0f ? -87.0f : (x > 88.0f ? 88.0f : x);
    float fx = std::floor(x * 1.44269504088896341f + 0.5f);
    float r = x - fx * 0.693359375f;
    r = r - fx * (-2.12194440e-4f);
    float y = 1.9875691500E-4f;
    y = y * r + 1.3981999507E-3f;
    y = y * r + 8.3334519073E-3f;
    y = y * r + 4.1665795894E-2f;
    y = y * r + 1.6666665459E-1f;
    y = y * r + 5.0000001201E-1f;
    y = y * r * r + r + 1.0f;
    int32_t n = (int32_t)fx + 127;
    uint32_t u = (uint32_t)n << 23;
    float s;
    std::memcpy(&s, &u, 4);
    return y * s;
}

static inline float vlogp(float x) {
    uint32_t u;
    std::memcpy(&u, &x, 4);
    int32_t e = (int32_t)((u >> 23) & 0xff) - 126;
    u = (u & 0x807fffffu) | 0x3f000000u;
    float m;
    std::memcpy(&m, &u, 4);
    float fe;
    bool baixo = m < 0.707106781186547524f;
    m = baixo ? (m + m - 1.0f) : (m - 1.0f);
    fe = (float)(baixo ? e - 1 : e);
    float z = m * m;
    float y = 7.0376836292E-2f;
    y = y * m + -1.1514610310E-1f;
    y = y * m + 1.1676998740E-1f;
    y = y * m + -1.2420140846E-1f;
    y = y * m + 1.4249322787E-1f;
    y = y * m + -1.6668057665E-1f;
    y = y * m + 2.0000714765E-1f;
    y = y * m + -2.4999993993E-1f;
    y = y * m + 3.3333331174E-1f;
    y = y * m * z;
    y += -2.12194440e-4f * fe;
    y += -0.5f * z;
    m = m + y;
    m += 0.693359375f * fe;
    return m;
}

static inline float vlog1p_abs(float a) {
    float x = std::fabs(a);
    float s = x - x * x * 0.5f + x * x * x * 0.33333333f;
    return x < 1.0e-3f ? s : vlogp(1.0f + x);
}

static inline float vtanh(float x) {
    float ax = std::fabs(x);
    float x2 = x * x;
    float p = x * (1.0f + x2 * (-0.33333333f + x2 * (0.13333334f + x2 * (-0.05396825f + x2 * 0.02186949f))));
    float e = vexp(-2.0f * std::min(ax, 9.0f));
    float t = (1.0f - e) / (1.0f + e);
    t = x < 0 ? -t : t;
    return ax < 0.25f ? p : t;
}

static inline float vsig(float a) { return 1.0f / (1.0f + vexp(-clampf(a, -30.0f, 30.0f))); }

struct NoC {
    int idx, op, a, b;
    float c1, c2, c3;
};

template <int OP>
static inline float aplica(float a, float b, float c1, float c2, float c3) {
    if constexpr (OP == ADD) return a + b;
    else if constexpr (OP == SUB) return a - b;
    else if constexpr (OP == MUL) return clampf(a * b, -CL, CL);
    else if constexpr (OP == DIV) return clampf(a / (std::fabs(b) + EPSF), -CL, CL);
    else if constexpr (OP == MAX) return (a > b || a != a) ? a : b;
    else if constexpr (OP == MIN) return (a < b || a != a) ? a : b;
    else if constexpr (OP == NEG) return -a;
    else if constexpr (OP == ABS) return std::fabs(a);
    else if constexpr (OP == SQ) return clampf(a * a, -CL, CL);
    else if constexpr (OP == SQRT) return std::sqrt(std::fabs(a));
    else if constexpr (OP == TANH) return vtanh(a);
    else if constexpr (OP == RELU) return (a > 0.0f || a != a) ? a : 0.0f;
    else if constexpr (OP == SIG) return vsig(a);
    else if constexpr (OP == THR) return a > 0.0f ? 1.0f : 0.0f;
    else if constexpr (OP == SIGN) return a > 0.0f ? 1.0f : (a < 0.0f ? -1.0f : a);
    else if constexpr (OP == EXP) return clampf(vexp((a < 8.0f || a != a) ? a : 8.0f), -CL, CL);
    else if constexpr (OP == LOG) return vlog1p_abs(a);
    else if constexpr (OP == INV) return clampf(1.0f / (std::fabs(a) + EPSF), -CL, CL);
    else if constexpr (OP == AVG) return 0.5f * (a + b);
    else if constexpr (OP == K) return c1;
    else if constexpr (OP == MULK) return clampf(a * c1, -CL, CL);
    else if constexpr (OP == ADDK) return a + c1;
    else if constexpr (OP == GT) return a > b ? 1.0f : 0.0f;
    else if constexpr (OP == ABSDIFF) return std::fabs(a - b);
    else if constexpr (OP == CLIP1) return clampf(a, -1.0f, 1.0f);
    else if constexpr (OP == EMA) return a + c2 * (b - a);
    else if constexpr (OP == SHRK) return a * c3;
    else if constexpr (OP == HYP) return std::sqrt(a * a + b * b);
    else if constexpr (OP == SEL) return a > 0.0f ? a : b;
    else return a;
}

using Ker = void (*)(float* __restrict, const float*, const float*, int, float, float, float);

template <int OP, bool AV, bool BV>
static void kern(float* __restrict o, const float* a, const float* b, int n, float c1, float c2, float c3) {
    const float a0 = a[0], b0 = b[0];
    for (int i = 0; i < n; i++) {
        float x = AV ? a[i] : a0;
        float y = BV ? b[i] : b0;
        o[i] = aplica<OP>(x, y, c1, c2, c3);
    }
}

#define KER4(OP) {kern<OP, false, false>, kern<OP, false, true>, kern<OP, true, false>, kern<OP, true, true>}
static const Ker KER[N_OPS][4] = {KER4(0),  KER4(1),  KER4(2),  KER4(3),  KER4(4),  KER4(5),  KER4(6),  KER4(7),  KER4(8),  KER4(9),  KER4(10), KER4(11), KER4(12), KER4(13), KER4(14), KER4(15),
                                  KER4(16), KER4(17), KER4(18), KER4(19), KER4(20), KER4(21), KER4(22), KER4(23), KER4(24), KER4(25), KER4(26), KER4(27), KER4(28), KER4(29), KER4(30), KER4(31)};

struct PlanoC {
    int presente = 0, n_in = 0, n = 0;
    NoC nos[K_NOS];
    uint32_t lidas = 0;
};

struct Reg {
    int cls = CS;
    const float* p = nullptr;
};

struct Trab {
    std::vector<float> buf[K_NOS];
    float rs[K_NOS];
    int ncls[K_NOS];
    std::vector<float> acc;
};

static inline int combina(int a, int b) {
    if (a == CS) return b;
    if (b == CS) return a;
    if (a == b) return a;
    if ((a == CCOL && b == CRS) || (a == CRS && b == CCOL)) return CRS;
    return CFULL;
}

struct OpdP {
    const float* p;
    bool vec;
};

static void avalia_secao(const PlanoC& pl, const Reg* env, int R, int C, float* dst, Trab& T) {
    const int n_in = pl.n_in;
    int cls_no[K_NOS] = {0};
    bool reduz_linhas[K_NOS] = {false};

    for (int t = 0; t < pl.n; t++) {
        const NoC& no = pl.nos[t];
        const int i = no.idx;
        const int ar = ARIDADE[no.op];
        const int ca = ar >= 1 ? (no.a < n_in ? env[no.a].cls : cls_no[no.a - n_in]) : CS;
        const int cb = ar >= 2 ? (no.b < n_in ? env[no.b].cls : cls_no[no.b - n_in]) : CS;
        int c;
        if (ar == 0) c = CS;
        else if (no.op == MEAN0) {
            if (ca == CFULL) { c = CROW; reduz_linhas[i] = true; }
            else if (ca == CRS) { c = CS; reduz_linhas[i] = true; }
            else c = (ca == CCOL) ? CS : ca;
        } else if (no.op == MEAN1) {
            c = (ca == CS || ca == CROW) ? CS : (ca == CCOL ? CCOL : CRS);
        } else if (ar == 1) c = ca;
        else c = combina(ca, cb);
        cls_no[i] = c;
        T.ncls[i] = c;
        const size_t tam = c == CS ? 1 : (c == CCOL ? (size_t)R : (size_t)C);
        if (c != CRS && T.buf[i].size() < tam) T.buf[i].resize(tam);
    }

    auto opd = [&](int j, int linha, bool fase_a) -> OpdP {
        if (j < n_in) {
            const Reg& r = env[j];
            switch (r.cls) {
                case CS: return {r.p, false};
                case CROW: return {r.p, true};
                case CCOL: return fase_a ? OpdP{r.p, true} : OpdP{r.p + linha, false};
                default: return {r.p + (size_t)linha * C, true};
            }
        }
        const int k = j - n_in;
        switch (T.ncls[k]) {
            case CS: return {T.buf[k].data(), false};
            case CROW: return {T.buf[k].data(), true};
            case CCOL: return fase_a ? OpdP{T.buf[k].data(), true} : OpdP{T.buf[k].data() + linha, false};
            case CRS: return {&T.rs[k], false};
            default: return {T.buf[k].data(), true};
        }
    };

    auto linha_dos_nos = [&](int ate, int linha) {
        for (int t = 0; t < pl.n; t++) {
            const NoC& no = pl.nos[t];
            const int i = no.idx;
            if (i >= ate) break;
            const int c = cls_no[i];
            if (c != CFULL && c != CRS) continue;
            if (no.op == MEAN1) {
                const int ca = no.a < n_in ? env[no.a].cls : cls_no[no.a - n_in];
                OpdP a = opd(no.a, linha, false);
                if (ca == CRS) { T.rs[i] = a.p[0]; continue; }
                double soma = 0.0;
                for (int j = 0; j < C; j++) soma += a.p[j];
                T.rs[i] = (float)(soma / C);
                continue;
            }
            const int ar = ARIDADE[no.op];
            OpdP a = ar >= 1 ? opd(no.a, linha, false) : OpdP{T.buf[i].data(), false};
            OpdP b = ar >= 2 ? opd(no.b, linha, false) : a;
            if (c == CRS) {
                float o;
                KER[no.op][0](&o, a.p, b.p, 1, no.c1, no.c2, no.c3);
                T.rs[i] = o;
            } else {
                KER[no.op][(a.vec ? 2 : 0) + (b.vec ? 1 : 0)](T.buf[i].data(), a.p, b.p, C, no.c1, no.c2, no.c3);
            }
        }
    };

    for (int t = 0; t < pl.n; t++) {
        const NoC& no = pl.nos[t];
        const int i = no.idx;
        const int c = cls_no[i];
        if (c == CFULL || c == CRS) continue;
        const int ar = ARIDADE[no.op];
        if (reduz_linhas[i]) {
            const int ca = no.a < n_in ? env[no.a].cls : cls_no[no.a - n_in];
            const int ate = no.a < n_in ? 0 : (no.a - n_in + 1);
            if (ca == CFULL) {
                std::vector<double> soma(C, 0.0);
                for (int r = 0; r < R; r++) {
                    linha_dos_nos(ate, r);
                    OpdP a = opd(no.a, r, false);
                    for (int j = 0; j < C; j++) soma[j] += a.p[j];
                }
                for (int j = 0; j < C; j++) T.buf[i][j] = (float)(soma[j] / R);
            } else {
                double soma = 0.0;
                for (int r = 0; r < R; r++) {
                    linha_dos_nos(ate, r);
                    soma += opd(no.a, r, false).p[0];
                }
                T.buf[i][0] = (float)(soma / R);
            }
            continue;
        }
        if (no.op == MEAN0 || no.op == MEAN1) {
            const int ca = no.a < n_in ? env[no.a].cls : cls_no[no.a - n_in];
            OpdP a = opd(no.a, 0, true);
            if (no.op == MEAN0) {
                if (ca == CS) T.buf[i][0] = a.p[0];
                else if (ca == CROW) for (int j = 0; j < C; j++) T.buf[i][j] = a.p[j];
                else { double soma = 0.0; for (int r = 0; r < R; r++) soma += a.p[r]; T.buf[i][0] = (float)(soma / R); }
            } else {
                if (ca == CS) T.buf[i][0] = a.p[0];
                else if (ca == CROW) { double soma = 0.0; for (int j = 0; j < C; j++) soma += a.p[j]; T.buf[i][0] = (float)(soma / C); }
                else for (int r = 0; r < R; r++) T.buf[i][r] = a.p[r];
            }
            continue;
        }
        const int n = c == CS ? 1 : (c == CCOL ? R : C);
        OpdP a = ar >= 1 ? opd(no.a, 0, true) : OpdP{T.buf[i].data(), false};
        OpdP b = ar >= 2 ? opd(no.b, 0, true) : a;
        KER[no.op][(a.vec ? 2 : 0) + (b.vec ? 1 : 0)](T.buf[i].data(), a.p, b.p, n, no.c1, no.c2, no.c3);
    }

    const int iout = K_NOS - 1;
    const int co = cls_no[iout];
    auto finito = [](float v) { return std::isnan(v) ? 0.0f : (std::isinf(v) ? (v > 0 ? CL : -CL) : v); };
    if (co != CFULL && co != CRS) {
        const float* s = T.buf[iout].data();
        for (int r = 0; r < R; r++)
            for (int j = 0; j < C; j++) dst[(size_t)r * C + j] = finito(co == CS ? s[0] : (co == CROW ? s[j] : s[r]));
        return;
    }
    for (int r = 0; r < R; r++) {
        linha_dos_nos(K_NOS, r);
        float* d = dst + (size_t)r * C;
        if (co == CRS) { const float v = finito(T.rs[iout]); for (int j = 0; j < C; j++) d[j] = v; }
        else { const float* s = T.buf[iout].data(); for (int j = 0; j < C; j++) d[j] = finito(s[j]); }
    }
}

struct Rng {
    uint64_t* s;
    static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
    inline uint64_t next() {
        uint64_t r = rotl(s[0] + s[3], 23) + s[0];
        uint64_t t = s[1] << 17;
        s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
        return r;
    }
    inline float uniforme() { return (float)(next() >> 40) * (1.0f / 16777216.0f); }
    inline float normal() {
        uint64_t a = next(), b = next(), c = next();
        uint32_t t = 0;
        for (int k = 0; k < 4; k++) t += (uint32_t)((a >> (16 * k)) & 0xffff) + (uint32_t)((b >> (16 * k)) & 0xffff) + (uint32_t)((c >> (16 * k)) & 0xffff);
        return (float)t * (1.0f / 65536.0f) - 6.0f;
    }
};

struct Ser {
    int d = 0, c = 0, nl = 0, nm = 0, B = 0, cada = 1, pol_padrao = 0;
    int h[3] = {0, 0, 0}, act[3] = {0, 0, 0}, dims[5] = {0, 0, 0, 0, 0};
    int rotulos[3] = {0, 0, 0};
    int init_S[3] = {0, 0, 0}, init_U[2] = {0, 0};
    float escala_init = 1.0f;
    bool S_viva[3] = {false, false, false}, U_viva[2] = {false, false}, G_viva[2] = {false, false};
    bool tem_guarda = false, usa_xi = false;
    uint32_t lidas_peso = 0;
    PlanoC plano[N_SECOES];

    float* W[4] = {};
    uint8_t* conn[4] = {};
    float* mask[3] = {};
    float* age[4] = {};
    float* S[3][4] = {};
    float* U[2][4] = {};
    float* G = nullptr;
    float* mu = nullptr;
    float* var = nullptr;
    float* bx = nullptr;
    float* by = nullptr;
    int32_t* nbuf = nullptr;
    int64_t* cnt = nullptr;
    double pert_eps = 0.0;
    uint64_t pert_semente = 0;
    Rng rng{nullptr};

    Trab trab;
    std::vector<float> apre[4], sl[3], al[3], msg[4], z, p;
    std::vector<float> eP, eQ, eP2, eQ2, epre, epost, eerr, epre2, epost2, eerr2, exi, tmp, tmpS[3], novoW[4];
    std::vector<float> enorm, conf, perda;

    int ultimo_Bn = 0;

    int n_in_m(int m) const { return dims[m]; }
    int n_out_m(int m) const { return dims[m + 1]; }

    static inline float ativa(int tipo, float s) {
        if (tipo == 0) return s > 0.0f ? s : 0.0f;
        if (tipo == 1) return vtanh(s);
        if (tipo == 2) return s / (1.0f + std::fabs(s));
        return s > 0.0f ? s : 0.1f * s;
    }

    void frente(const float* X, int Bn) {
        for (int m = 0; m <= nl; m++) apre[m].assign((size_t)Bn * (dims[m] + 1), 1.0f);
        for (int b = 0; b < Bn; b++) std::memcpy(&apre[0][(size_t)b * (d + 1)], X + (size_t)b * d, sizeof(float) * d);
        for (int l = 0; l < nl; l++) {
            const int ni = dims[l] + 1, no = dims[l + 1];
            sl[l].assign((size_t)Bn * no, 0.0f);
            al[l].assign((size_t)Bn * no, 0.0f);
            for (int b = 0; b < Bn; b++) {
                float* sr = &sl[l][(size_t)b * no];
                const float* ar = &apre[l][(size_t)b * ni];
                for (int k = 0; k < ni; k++) {
                    const float a = ar[k];
                    const float* wr = W[l] + (size_t)k * no;
                    for (int j = 0; j < no; j++) sr[j] += a * wr[j];
                }
                float* ao = &al[l][(size_t)b * no];
                float* ap = &apre[l + 1][(size_t)b * (no + 1)];
                for (int j = 0; j < no; j++) { ao[j] = ativa(act[l], sr[j]) * mask[l][j]; ap[j] = ao[j]; }
            }
        }
        const int ni = dims[nl] + 1, no = c;
        z.assign((size_t)Bn * no, 0.0f);
        for (int b = 0; b < Bn; b++) {
            float* zr = &z[(size_t)b * no];
            const float* ar = &apre[nl][(size_t)b * ni];
            for (int k = 0; k < ni; k++) {
                const float a = ar[k];
                const float* wr = W[nl] + (size_t)k * no;
                for (int j = 0; j < no; j++) zr[j] += a * wr[j];
            }
        }
    }

    void softmax(int Bn) {
        p.assign((size_t)Bn * c, 0.0f);
        for (int b = 0; b < Bn; b++) {
            const float* zr = &z[(size_t)b * c];
            float mx = zr[0];
            for (int j = 1; j < c; j++) mx = std::max(mx, zr[j]);
            float soma = 0.0f;
            float* pr = &p[(size_t)b * c];
            for (int j = 0; j < c; j++) { pr[j] = std::exp(zr[j] - mx); soma += pr[j]; }
            for (int j = 0; j < c; j++) pr[j] /= soma;
        }
    }

    void passo(const float* X, const float* Tg, int Bn) {
        frente(X, Bn);
        softmax(Bn);
        const float fBn = (float)Bn;
        std::vector<float>& e_out = msg[nl];
        e_out.assign((size_t)Bn * c, 0.0f);
        perda.assign(Bn, 0.0f); conf.assign(Bn, 0.0f); enorm.assign(Bn, 0.0f);
        float acertos = 0.0f;
        for (int b = 0; b < Bn; b++) {
            const float* pr = &p[(size_t)b * c];
            const float* tg = Tg + (size_t)b * c;
            float* er = &e_out[(size_t)b * c];
            float mx = pr[0], en = 0.0f, perda_b = 0.0f;
            int am = 0;
            for (int j = 0; j < c; j++) {
                er[j] = tg[j] - pr[j];
                en += std::fabs(er[j]);
                if (pr[j] > mx) { mx = pr[j]; am = j; }
                if (tg[j] != 0.0f) perda_b += tg[j] * std::log(std::max(pr[j], 1.0e-9f));
            }
            perda[b] = -perda_b;
            conf[b] = mx;
            enorm[b] = en / (float)c;
            acertos += tg[am];
        }
        const float acerto = acertos / fBn;
        const float t_n = (float)(std::log1p((double)cnt[0]) / 12.0);
        const float g1 = G_viva[0] ? G[0] : 0.0f, g2 = G_viva[1] ? G[1] : 0.0f;
        const float zero = 0.0f, um = 1.0f;

        for (int l = nl - 1; l >= 0; l--) {
            const int no = dims[l + 1];
            msg[l].assign((size_t)Bn * no, 0.0f);
            if (!plano[S_RETRO].presente) continue;
            std::vector<float>& Tm = tmp;
            Tm.assign((size_t)Bn * no, 0.0f);
            const int nout_up = dims[l + 2];
            for (int b = 0; b < Bn; b++) {
                const float* mu_ = &msg[l + 1][(size_t)b * nout_up];
                for (int i = 0; i < no; i++) {
                    const float* wr = W[l + 1] + (size_t)i * nout_up;
                    float s = 0.0f;
                    for (int j = 0; j < nout_up; j++) s += mu_[j] * wr[j];
                    Tm[(size_t)b * no + i] = s;
                }
            }
            Reg env[13];
            env[0] = {CS, &zero}; env[1] = {CS, &um}; env[2] = {CFULL, Tm.data()}; env[3] = {CFULL, sl[l].data()}; env[4] = {CFULL, al[l].data()};
            env[5] = U_viva[0] ? Reg{CROW, U[0][l]} : Reg{CS, &zero};
            env[6] = U_viva[1] ? Reg{CROW, U[1][l]} : Reg{CS, &zero};
            env[7] = {CS, &g1}; env[8] = {CS, &g2}; env[9] = {CS, &t_n};
            env[10] = {CCOL, perda.data()}; env[11] = {CCOL, conf.data()}; env[12] = {CCOL, enorm.data()};
            std::vector<float>& out = tmpS[0];
            out.resize((size_t)Bn * no);
            avalia_secao(plano[S_RETRO], env, Bn, no, out.data(), trab);
            for (int b = 0; b < Bn; b++)
                for (int j = 0; j < no; j++) msg[l][(size_t)b * no + j] = out[(size_t)b * no + j] * mask[l][j];
        }

        for (int m = 0; m < nm; m++) novoW[m].assign((size_t)(dims[m] + 1) * dims[m + 1], 0.0f);
        std::vector<float> novaS[3][4];
        for (int m = 0; m < nm; m++) {
            const int ni = dims[m] + 1, no = dims[m + 1];
            const float* a_pre = apre[m].data();
            const float* a_pos = m < nl ? al[m].data() : p.data();
            const float* m_pos = msg[m].data();
            const size_t tam = (size_t)ni * no;
            const uint32_t L_ = lidas_peso;
            auto ler = [&](int bit) { return (L_ >> bit) & 1u; };
            auto produto_externo = [&](std::vector<float>& dst, const float* A, const float* Bm, bool quad) {
                dst.assign(tam, 0.0f);
                for (int b = 0; b < Bn; b++)
                    for (int k = 0; k < ni; k++) {
                        const float a = quad ? A[(size_t)b * ni + k] * A[(size_t)b * ni + k] : A[(size_t)b * ni + k];
                        float* dr = &dst[(size_t)k * no];
                        const float* br = Bm + (size_t)b * no;
                        if (quad) for (int j = 0; j < no; j++) dr[j] += a * (br[j] * br[j]);
                        else for (int j = 0; j < no; j++) dr[j] += a * br[j];
                    }
                for (size_t q = 0; q < tam; q++) dst[q] /= fBn;
            };
            if (ler(3)) produto_externo(eP, a_pre, m_pos, false);
            if (ler(4)) produto_externo(eQ, a_pre, a_pos, false);
            if (ler(5)) produto_externo(eP2, a_pre, m_pos, true);
            if (ler(6)) produto_externo(eQ2, a_pre, a_pos, true);
            auto media_col = [&](std::vector<float>& dst, const float* A, int n, bool quad) {
                dst.assign(n, 0.0f);
                for (int j = 0; j < n; j++) {
                    double s = 0.0;
                    for (int b = 0; b < Bn; b++) { float v = A[(size_t)b * n + j]; s += quad ? v * v : v; }
                    dst[j] = (float)(s / Bn);
                }
            };
            if (ler(7)) media_col(epre, a_pre, ni, false);
            if (ler(8)) media_col(epost, a_pos, no, false);
            if (ler(9)) media_col(eerr, m_pos, no, false);
            if (ler(10)) media_col(epre2, a_pre, ni, true);
            if (ler(11)) media_col(epost2, a_pos, no, true);
            if (ler(12)) media_col(eerr2, m_pos, no, true);
            if (usa_xi) {
                exi.resize(tam);
                for (size_t q = 0; q < tam; q++) exi[q] = rng.normal();
            }
            const float prof = (float)m / (float)std::max(nm - 1, 1);
            Reg env[23];
            env[0] = {CS, &zero}; env[1] = {CS, &um}; env[2] = {CFULL, W[m]};
            env[3] = ler(3) ? Reg{CFULL, eP.data()} : Reg{CS, &zero};
            env[4] = ler(4) ? Reg{CFULL, eQ.data()} : Reg{CS, &zero};
            env[5] = ler(5) ? Reg{CFULL, eP2.data()} : Reg{CS, &zero};
            env[6] = ler(6) ? Reg{CFULL, eQ2.data()} : Reg{CS, &zero};
            env[7] = ler(7) ? Reg{CCOL, epre.data()} : Reg{CS, &zero};
            env[8] = ler(8) ? Reg{CROW, epost.data()} : Reg{CS, &zero};
            env[9] = ler(9) ? Reg{CROW, eerr.data()} : Reg{CS, &zero};
            env[10] = ler(10) ? Reg{CCOL, epre2.data()} : Reg{CS, &zero};
            env[11] = ler(11) ? Reg{CROW, epost2.data()} : Reg{CS, &zero};
            env[12] = ler(12) ? Reg{CROW, eerr2.data()} : Reg{CS, &zero};
            for (int k = 0; k < 3; k++) env[13 + k] = S_viva[k] ? Reg{CFULL, S[k][m]} : Reg{CS, &zero};
            for (int k = 0; k < 2; k++) env[16 + k] = U_viva[k] ? Reg{CROW, U[k][m]} : Reg{CS, &zero};
            env[18] = {CS, &g1}; env[19] = {CS, &g2}; env[20] = {CS, &t_n};
            env[21] = usa_xi ? Reg{CFULL, exi.data()} : Reg{CS, &zero};
            env[22] = {CS, &prof};
            const PlanoC& regra = plano[m == nm - 1 ? S_W_SAIDA : S_W_OCULTA];
            float* Wn = novoW[m].data();
            if (regra.presente) {
                tmp.resize(tam);
                avalia_secao(regra, env, ni, no, tmp.data(), trab);
                for (int k = 0; k < ni; k++)
                    for (int j = 0; j < no; j++) {
                        const size_t q = (size_t)k * no + j;
                        float dw = clampf(tmp[q], -PASSO_MAX, PASSO_MAX);
                        if (m < nl) dw = dw * mask[m][j];
                        Wn[q] = clampf(W[m][q] + dw, -PESO_MAX, PESO_MAX) * (float)conn[m][q];
                    }
            } else {
                std::memcpy(Wn, W[m], sizeof(float) * tam);
            }
            for (int k = 0; k < 3; k++) {
                if (!S_viva[k]) continue;
                novaS[k][m].resize(tam);
                avalia_secao(plano[S_S1 + k], env, ni, no, novaS[k][m].data(), trab);
                for (size_t q = 0; q < tam; q++) novaS[k][m][q] = clampf(novaS[k][m][q], -CL, CL);
            }
        }
        for (int m = 0; m < nm; m++) std::memcpy(W[m], novoW[m].data(), sizeof(float) * novoW[m].size());
        if (pert_eps > 0.0) {
            const uint64_t t = (uint64_t)cnt[0];
            for (int m = 0; m < nm; m++) {
                const size_t n = novoW[m].size();
                for (size_t q = 0; q < n; q++) {
                    uint64_t z = pert_semente ^ (t * 0x9E3779B97F4A7C15ULL) ^ ((uint64_t)(m + 1) * 0xBF58476D1CE4E5B9ULL) ^ ((uint64_t)q * 0x94D049BB133111EBULL);
                    z ^= z >> 30; z *= 0xBF58476D1CE4E5B9ULL; z ^= z >> 27; z *= 0x94D049BB133111EBULL; z ^= z >> 31;
                    const double u = (double)(z >> 40) / 16777216.0 * 2.0 - 1.0;
                    const float f = (float)(1.0 + pert_eps * u);
                    W[m][q] = W[m][q] * f;
                }
            }
        }
        for (int k = 0; k < 3; k++)
            if (S_viva[k]) for (int m = 0; m < nm; m++) std::memcpy(S[k][m], novaS[k][m].data(), sizeof(float) * novaS[k][m].size());

        ultimo_Bn = Bn;
        if (U_viva[0] || U_viva[1] || tem_guarda) unidades(Bn, t_n, g1, g2);

        if (G_viva[0] || G_viva[1]) {
            double wn = 0.0;
            for (int m = 0; m < nm; m++) {
                double s = 0.0;
                const size_t tam = (size_t)(dims[m] + 1) * dims[m + 1];
                for (size_t q = 0; q < tam; q++) s += std::fabs(W[m][q]);
                wn += s / (double)tam;
            }
            const float wnorm = (float)(wn / nm);
            double at = 0.0;
            for (int l = 0; l < nl; l++) { double s = 0.0; for (int j = 0; j < h[l]; j++) s += mask[l][j]; at += s / h[l]; }
            const float ativas = (float)(at / nl);
            double sp = 0.0, sc = 0.0, se = 0.0;
            for (int b = 0; b < Bn; b++) { sp += perda[b]; sc += conf[b]; se += enorm[b]; }
            const float fp = (float)(sp / Bn), fc = (float)(sc / Bn), fe = (float)(se / Bn);
            Reg envg[11];
            envg[0] = {CS, &zero}; envg[1] = {CS, &um}; envg[2] = {CS, &fp}; envg[3] = {CS, &acerto}; envg[4] = {CS, &fe}; envg[5] = {CS, &fc}; envg[6] = {CS, &g1}; envg[7] = {CS, &g2};
            envg[8] = {CS, &t_n}; envg[9] = {CS, &wnorm}; envg[10] = {CS, &ativas};
            for (int k = 0; k < 2; k++) {
                if (!G_viva[k]) continue;
                float o = 0.0f;
                avalia_secao(plano[S_G1 + k], envg, 1, 1, &o, trab);
                G[k] = clampf(o, -CL, CL);
            }
        }
        for (int m = 0; m < nm; m++) for (int j = 0; j < dims[m + 1]; j++) age[m][j] += 1.0f;
        cnt[0] += 1;
        cnt[1] += 1;
        if (tem_guarda && cnt[0] % cada == 0) acoes(t_n, g1, g2);
    }

    void estatisticas(int l, int Bn, std::vector<float>& post, std::vector<float>& post2, std::vector<float>& err, std::vector<float>& err2, std::vector<float>& inn, std::vector<float>& outn) {
        const int no = dims[l + 1];
        const float* a_pos = l < nl ? al[l].data() : p.data();
        const float* m_pos = msg[l].data();
        post.assign(no, 0.0f); post2.assign(no, 0.0f); err.assign(no, 0.0f); err2.assign(no, 0.0f); inn.assign(no, 0.0f); outn.assign(no, 0.0f);
        for (int j = 0; j < no; j++) {
            double s1 = 0, s2 = 0, s3 = 0, s4 = 0;
            for (int b = 0; b < Bn; b++) {
                const float a = a_pos[(size_t)b * no + j], e = m_pos[(size_t)b * no + j];
                s1 += a; s2 += (double)a * a; s3 += e; s4 += (double)e * e;
            }
            post[j] = (float)(s1 / Bn); post2[j] = (float)(s2 / Bn); err[j] = (float)(s3 / Bn); err2[j] = (float)(s4 / Bn);
            double si = 0;
            const int ni = dims[l];
            for (int k = 0; k < ni; k++) si += std::fabs(W[l][(size_t)k * no + j]);
            inn[j] = (float)(si / std::max(ni, 1));
        }
        if (l < nl) {
            const int nout_up = dims[l + 2];
            for (int i = 0; i < no; i++) {
                double s = 0;
                for (int j = 0; j < nout_up; j++) s += std::fabs(W[l + 1][(size_t)i * nout_up + j]);
                outn[i] = (float)(s / nout_up);
            }
        }
    }

    void unidades(int Bn, float t_n, float g1, float g2) {

        const float zero = 0.0f, um = 1.0f;
        std::vector<float> post, post2, err, err2, inn, outn, idade, saida;
        for (int k = 0; k < 2; k++) {
            if (!U_viva[k]) continue;
            for (int l = 0; l < nm; l++) {
                estatisticas(l, Bn, post, post2, err, err2, inn, outn);
                const int no = dims[l + 1];
                idade.assign(no, 0.0f);
                for (int j = 0; j < no; j++) idade[j] = (float)(std::log1p((double)age[l][j]) / 12.0);
                Reg env[14];
                env[0] = {CS, &zero}; env[1] = {CS, &um}; env[2] = {CROW, post.data()}; env[3] = {CROW, post2.data()}; env[4] = {CROW, err.data()}; env[5] = {CROW, err2.data()};
                env[6] = {CROW, inn.data()}; env[7] = {CROW, outn.data()};
                env[8] = U_viva[0] ? Reg{CROW, U[0][l]} : Reg{CS, &zero};
                env[9] = U_viva[1] ? Reg{CROW, U[1][l]} : Reg{CS, &zero};
                env[10] = {CROW, idade.data()}; env[11] = {CS, &g1}; env[12] = {CS, &g2}; env[13] = {CS, &t_n};
                saida.assign(no, 0.0f);
                avalia_secao(plano[S_U1 + k], env, 1, no, saida.data(), trab);
                for (int j = 0; j < no; j++) U[k][l][j] = clampf(saida[j], -CL, CL);
            }
        }
    }

    float uniforme_inicial(int tipo, int  ) {
        if (tipo == 0) return 0.0f;
        if (tipo == 1) return 1.0f;
        if (tipo == 2) return 0.5f;
        return rng.uniforme();
    }

    void zerar_unidade(int l, const std::vector<char>& sel) {
        const int ni = dims[l] + 1, no = dims[l + 1];
        for (int k = 0; k < ni; k++) for (int j = 0; j < no; j++) if (sel[j]) W[l][(size_t)k * no + j] = 0.0f;
        if (l + 1 < nm) {
            const int nn = dims[l + 2];
            for (int i = 0; i < no; i++) if (sel[i]) for (int j = 0; j < nn; j++) W[l + 1][(size_t)i * nn + j] = 0.0f;
        }
    }

    float ini_S(int tipo, int m, size_t q) {
        if (tipo == 0) return 0.0f;
        if (tipo == 1) return 1.0f;
        if (tipo == 2) return W[m][q];
        return rng.normal() * 0.1f * (float)conn[m][q];
    }

    void renascer(int l, const std::vector<char>& sel) {
        const int ni = dims[l] + 1, no = dims[l + 1];
        double fan_s = 0;
        for (int j = 0; j < no; j++) { double s = 0; for (int k = 0; k < ni - 1; k++) s += conn[l][(size_t)k * no + j]; fan_s += s; }
        const float fan = std::max(1.0f, (float)(fan_s / no));
        const float sd = escala_init / std::sqrt(fan);
        for (int j = 0; j < no; j++) {
            if (!sel[j]) continue;
            for (int k = 0; k < ni - 1; k++) W[l][(size_t)k * no + j] = rng.normal() * sd * (float)conn[l][(size_t)k * no + j];
            W[l][(size_t)(ni - 1) * no + j] = 0.0f;
        }
        if (l + 1 < nm) {
            const int nn = dims[l + 2];
            for (int i = 0; i < no; i++) if (sel[i]) for (int j = 0; j < nn; j++) W[l + 1][(size_t)i * nn + j] = 0.0f;
        }
        for (int k = 0; k < 3; k++) {
            if (!S_viva[k]) continue;
            for (int j = 0; j < no; j++) if (sel[j]) for (int r = 0; r < ni; r++) S[k][l][(size_t)r * no + j] = ini_S(init_S[k], l, (size_t)r * no + j);
            if (l + 1 < nm) {
                const int nn = dims[l + 2];
                for (int i = 0; i < no; i++) if (sel[i]) for (int j = 0; j < nn; j++) S[k][l + 1][(size_t)i * nn + j] = ini_S(init_S[k], l + 1, (size_t)i * nn + j);
            }
        }
        for (int k = 0; k < 2; k++) {
            if (!U_viva[k]) continue;
            for (int j = 0; j < no; j++) if (sel[j]) U[k][l][j] = uniforme_inicial(init_U[k], no);
        }
        for (int j = 0; j < no; j++) if (sel[j]) age[l][j] = 0.0f;
    }

    void acoes(float t_n, float g1, float g2) {
        const float zero = 0.0f, um = 1.0f;
        std::vector<float> post, post2, err, err2, inn, outn, idade, saida;
        const int Bn = ultimo_Bn;
        for (int l = 0; l < nl; l++) {
            estatisticas(l, Bn, post, post2, err, err2, inn, outn);
            const int n = h[l];
            idade.assign(n, 0.0f);
            for (int j = 0; j < n; j++) idade[j] = (float)(std::log1p((double)age[l][j]) / 12.0);
            Reg env[14];
            env[0] = {CS, &zero}; env[1] = {CS, &um}; env[2] = {CROW, post.data()}; env[3] = {CROW, post2.data()}; env[4] = {CROW, err.data()}; env[5] = {CROW, err2.data()};
            env[6] = {CROW, inn.data()}; env[7] = {CROW, outn.data()};
            env[8] = U_viva[0] ? Reg{CROW, U[0][l]} : Reg{CS, &zero};
            env[9] = U_viva[1] ? Reg{CROW, U[1][l]} : Reg{CS, &zero};
            env[10] = {CROW, idade.data()}; env[11] = {CS, &g1}; env[12] = {CS, &g2}; env[13] = {CS, &t_n};
            saida.assign(n, 0.0f);
            std::vector<char> ativa_(n), sai(n), sel(n);
            for (int j = 0; j < n; j++) ativa_[j] = mask[l][j] > 0.0f;
            if (plano[S_LIBERA].presente) {
                avalia_secao(plano[S_LIBERA], env, 1, n, saida.data(), trab);
                int n_ativas = 0, n_sai = 0;
                for (int j = 0; j < n; j++) { sai[j] = (saida[j] > 0.0f) && ativa_[j]; n_ativas += ativa_[j]; n_sai += sai[j]; }
                if (n_ativas - n_sai < 4) {
                    const int limite = std::max(0, n_ativas - 4);
                    int conta = 0;
                    for (int j = 0; j < n; j++) { if (sai[j] && conta < limite) { conta++; } else sai[j] = 0; }
                    n_sai = conta;
                }
                if (n_sai > 0) {
                    zerar_unidade(l, sai);
                    for (int j = 0; j < n; j++) if (sai[j]) mask[l][j] = 0.0f;
                    cnt[4] += n_sai;
                    for (int j = 0; j < n; j++) ativa_[j] = mask[l][j] > 0.0f;
                }
            }
            if (plano[S_REINIT].presente) {
                avalia_secao(plano[S_REINIT], env, 1, n, saida.data(), trab);
                int q = 0;
                for (int j = 0; j < n; j++) { sel[j] = (saida[j] > 0.0f) && ativa_[j] && (age[l][j] >= (float)MATURIDADE); q += sel[j]; }
                if (q) { renascer(l, sel); cnt[2] += q; }
            }
            if (plano[S_ATIVA].presente) {
                avalia_secao(plano[S_ATIVA], env, 1, n, saida.data(), trab);
                int q = 0;
                for (int j = 0; j < n; j++) { sel[j] = (saida[j] > 0.0f) && !ativa_[j]; q += sel[j]; }
                if (q) {
                    for (int j = 0; j < n; j++) if (sel[j]) mask[l][j] = 1.0f;
                    renascer(l, sel);
                    cnt[3] += q;
                }
            }
        }
    }

    void aprender_um(const float* x, const float* alvo) {
        for (int j = 0; j < d; j++) {
            mu[j] += TAXA_ENTRADA * (x[j] - mu[j]);
            var[j] += TAXA_ENTRADA * ((x[j] - mu[j]) * (x[j] - mu[j]) - var[j]);
        }
        std::memcpy(bx + (size_t)nbuf[0] * d, x, sizeof(float) * d);
        std::memcpy(by + (size_t)nbuf[0] * c, alvo, sizeof(float) * c);
        nbuf[0] += 1;
        if (nbuf[0] >= B) {
            passo(bx, by, nbuf[0]);
            nbuf[0] = 0;
        }
        cnt[5] += 1;
    }

    void prever(const float* X, int Bn, int64_t* classes, int8_t* etiquetas) {
        frente(X, Bn);
        softmax(Bn);
        std::vector<float> confv(Bn), margv(Bn), entv(Bn), novv(Bn);
        for (int b = 0; b < Bn; b++) {
            const float* pr = &p[(size_t)b * c];
            const float* zr = &z[(size_t)b * c];
            int am = 0;
            float m1 = -1.0f, m2 = -1.0f;
            double e = 0.0;
            for (int j = 0; j < c; j++) {
                if (zr[j] > zr[am]) am = j;
                if (pr[j] > m1) { m2 = m1; m1 = pr[j]; } else if (pr[j] > m2) m2 = pr[j];
                e += pr[j] * std::log(std::max(pr[j], 1.0e-9f));
            }
            classes[b] = am;
            confv[b] = m1;
            margv[b] = m1 - m2;
            entv[b] = (float)(-e / std::log((double)c));
            double z2 = 0;
            const float* xr = X + (size_t)b * d;
            for (int j = 0; j < d; j++) { const float df = xr[j] - mu[j]; z2 += (double)(df * df) / (double)(var[j] + 1.0e-6f); }
            novv[b] = (float)(std::log1p(z2 / d) / 3.0);
        }
        const float zero = 0.0f, um = 1.0f;
        const float t_n = (float)(std::log1p((double)cnt[0]) / 12.0);
        const float g1 = G_viva[0] ? G[0] : 0.0f, g2 = G_viva[1] ? G[1] : 0.0f;
        for (int b = 0; b < Bn; b++) etiquetas[b] = (int8_t)pol_padrao;
        std::vector<char> decidido(Bn, 0);
        std::vector<float> saida(Bn);
        for (int k = 0; k < 3; k++) {
            if (!plano[S_POL1 + k].presente) continue;
            Reg env[9];
            env[0] = {CS, &zero}; env[1] = {CS, &um}; env[2] = {CCOL, confv.data()}; env[3] = {CCOL, margv.data()}; env[4] = {CCOL, entv.data()}; env[5] = {CCOL, novv.data()};
            env[6] = {CS, &g1}; env[7] = {CS, &g2}; env[8] = {CS, &t_n};
            avalia_secao(plano[S_POL1 + k], env, Bn, 1, saida.data(), trab);
            for (int b = 0; b < Bn; b++) {
                const bool cond = saida[b] > 0.0f;
                if (cond && !decidido[b]) etiquetas[b] = (int8_t)rotulos[k];
                decidido[b] = decidido[b] || cond;
            }
        }
    }
};

}

extern "C" {

void* ser_criar(const int32_t* ih, const double* dh, const int32_t* prog, const double* pc) {
    Ser* s = new Ser();
    int q = 0;
    s->d = ih[q++]; s->c = ih[q++]; s->nl = ih[q++]; s->B = ih[q++]; s->cada = ih[q++]; s->pol_padrao = ih[q++];
    for (int i = 0; i < 3; i++) s->rotulos[i] = ih[q++];
    for (int i = 0; i < 3; i++) s->act[i] = ih[q++];
    for (int i = 0; i < 3; i++) s->h[i] = ih[q++];
    for (int i = 0; i < 3; i++) s->init_S[i] = ih[q++];
    for (int i = 0; i < 2; i++) s->init_U[i] = ih[q++];
    for (int i = 0; i < 3; i++) s->S_viva[i] = ih[q++] != 0;
    for (int i = 0; i < 2; i++) s->U_viva[i] = ih[q++] != 0;
    for (int i = 0; i < 2; i++) s->G_viva[i] = ih[q++] != 0;
    s->tem_guarda = ih[q++] != 0;
    s->usa_xi = ih[q++] != 0;
    s->lidas_peso = (uint32_t)ih[q++];
    s->escala_init = (float)dh[0];
    s->nm = s->nl + 1;
    s->dims[0] = s->d;
    for (int i = 0; i < s->nl; i++) s->dims[i + 1] = s->h[i];
    s->dims[s->nl + 1] = s->c;
    int pp = 0, cc = 0;
    for (int i = 0; i < N_SECOES; i++) {
        PlanoC& pl = s->plano[i];
        pl.presente = prog[pp++];
        pl.n = prog[pp++];
        pl.lidas = (uint32_t)prog[pp++];
        pl.n_in = N_IN_DA_SECAO[i];
        for (int t = 0; t < pl.n; t++) {
            NoC& no = pl.nos[t];
            no.idx = prog[pp++]; no.op = prog[pp++]; no.a = prog[pp++]; no.b = prog[pp++];
            const double cd = pc[cc++];
            no.c1 = (float)cd;
            no.c2 = (float)std::min(cd, 1.0);
            no.c3 = (float)(1.0 - std::min(cd, 1.0));
        }
    }
    return s;
}

void ser_liberar(void* ctx) { delete (Ser*)ctx; }

void ser_perturbar(void* ctx, double eps, uint64_t semente) { ((Ser*)ctx)->pert_eps = eps; ((Ser*)ctx)->pert_semente = semente; }

void ser_ligar(void* ctx, const uint64_t* pW, const uint64_t* pconn, const uint64_t* pmask, const uint64_t* page, const uint64_t* pS, const uint64_t* pU, float* G, float* mu, float* var, float* bx,
               float* by, int32_t* nbuf, int64_t* cnt, uint64_t* rng) {
    Ser* s = (Ser*)ctx;
    for (int m = 0; m < s->nm; m++) {
        s->W[m] = (float*)pW[m]; s->conn[m] = (uint8_t*)pconn[m]; s->age[m] = (float*)page[m];
        for (int k = 0; k < 3; k++) s->S[k][m] = (float*)pS[k * 4 + m];
        for (int k = 0; k < 2; k++) s->U[k][m] = (float*)pU[k * 4 + m];
    }
    for (int l = 0; l < s->nl; l++) s->mask[l] = (float*)pmask[l];
    s->G = G; s->mu = mu; s->var = var; s->bx = bx; s->by = by; s->nbuf = nbuf; s->cnt = cnt; s->rng.s = rng;
}

void ser_aprender(void* ctx, const float* X, const float* T, int n) {
    Ser* s = (Ser*)ctx;
    for (int i = 0; i < n; i++) s->aprender_um(X + (size_t)i * s->d, T + (size_t)i * s->c);
}

void ser_prever(void* ctx, const float* X, int n, int64_t* classes, int8_t* etiquetas) { ((Ser*)ctx)->prever(X, n, classes, etiquetas); }

int ser_episodio(void* ctx, int lado, int inicio, const int32_t* alvos, int n_alvos, int rot, int tmax, const double* ctxv, int d_ctx, const double* ruido, const double* explora,
                 const int32_t* sorteio, double eps, float* X_out, int32_t* acoes_out, int32_t* sucesso_out) {
    Ser* s = (Ser*)ctx;
    static const int MOV[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
    const int d = lado * lado + 1 + d_ctx;
    int pos = inicio, fase = 0, n = 0;
    *sucesso_out = 0;
    for (int t = 0; t < tmax; t++) {
        float* x = X_out + (size_t)n * d;
        for (int j = 0; j < d; j++) x[j] = 0.0f;
        x[pos] = 1.0f;
        x[lado * lado] = (float)fase;
        for (int j = 0; j < d_ctx; j++) x[lado * lado + 1 + j] = (float)(ctxv[j] + ruido[(size_t)t * d_ctx + j]);
        int64_t cls = 0;
        int8_t etq = 0;
        s->prever(x, 1, &cls, &etq);
        int a = (int)cls;
        if (explora[t] < eps) a = sorteio[t];
        acoes_out[n] = a;
        n++;
        const int m = (((a - rot) % 4) + 4) % 4;
        const int r = pos / lado, c = pos % lado, r2 = r + MOV[m][0], c2 = c + MOV[m][1];
        if (r2 >= 0 && r2 < lado && c2 >= 0 && c2 < lado) pos = r2 * lado + c2;
        if (pos == alvos[fase]) {
            if (fase + 1 < n_alvos) fase++;
            else { *sucesso_out = 1; break; }
        }
    }
    return n;
}

void ser_secao_teste(const int32_t* prog, const double* pc, int tipo, const int32_t* cls, const float* const* ptrs, int R, int C, float* dst) {
    PlanoC pl;
    pl.presente = 1;
    int pp = 0, cc = 0;
    pl.n = prog[pp++];
    pl.n_in = N_IN_DA_SECAO[tipo];
    for (int t = 0; t < pl.n; t++) {
        NoC& no = pl.nos[t];
        no.idx = prog[pp++]; no.op = prog[pp++]; no.a = prog[pp++]; no.b = prog[pp++];
        const double cd = pc[cc++];
        no.c1 = (float)cd; no.c2 = (float)std::min(cd, 1.0); no.c3 = (float)(1.0 - std::min(cd, 1.0));
    }
    std::vector<Reg> env(pl.n_in);
    for (int i = 0; i < pl.n_in; i++) env[i] = {cls[i], ptrs[i]};
    Trab T;
    avalia_secao(pl, env.data(), R, C, dst, T);
}

}
