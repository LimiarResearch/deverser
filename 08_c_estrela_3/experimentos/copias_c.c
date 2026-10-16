#include <stdint.h>
#include <string.h>

typedef float v8 __attribute__((vector_size(32)));
typedef int32_t v8i __attribute__((vector_size(32)));

static inline v8 carrega(const float *p) { v8 v; memcpy(&v, p, sizeof v); return v; }
static inline v8 vmax(v8 a, v8 b) { const v8i m = a > b; return (v8)((m & (v8i)a) | (~m & (v8i)b)); }
static inline float hmax(v8 a) { float m = a[0]; for (int i = 1; i < 8; i++) m = a[i] > m ? a[i] : m; return m; }

void max_corr(const float *W, int m, const float *Xt, int n, int d, float *melhor) {
    for (int i = 0; i < m; i++) melhor[i] = -2.0f;
    int BLOCO = (32768 / (4 * (d > 0 ? d : 1))) & ~15;
    if (BLOCO < 16) BLOCO = 16;
    if (BLOCO > 512) BLOCO = 512;
    static float xb[8192 + 16];
    for (int k0 = 0; k0 < n; k0 += BLOCO) {
        const int nb = (n - k0) < BLOCO ? (n - k0) : BLOCO;
        for (int j = 0; j < d; j++) memcpy(xb + (int64_t)j * BLOCO, Xt + (int64_t)j * n + k0, sizeof(float) * nb);
        const int nb16 = nb & ~15;
        int i = 0;
        for (; i + 4 <= m; i += 4) {
            const float *w0 = W + (int64_t)i * d, *w1 = w0 + d, *w2 = w1 + d, *w3 = w2 + d;
            v8 m0 = {-2, -2, -2, -2, -2, -2, -2, -2}, m1 = m0, m2 = m0, m3 = m0;
            for (int k = 0; k < nb16; k += 16) {
                v8 a0 = {0}, b0 = {0}, a1 = {0}, b1 = {0}, a2 = {0}, b2 = {0}, a3 = {0}, b3 = {0};
                for (int j = 0; j < d; j++) {
                    const float *x = xb + (int64_t)j * BLOCO + k;
                    const v8 xa = carrega(x), xb = carrega(x + 8);
                    const float c0 = w0[j], c1 = w1[j], c2 = w2[j], c3 = w3[j];
                    a0 += c0 * xa; b0 += c0 * xb; a1 += c1 * xa; b1 += c1 * xb;
                    a2 += c2 * xa; b2 += c2 * xb; a3 += c3 * xa; b3 += c3 * xb;
                }
                m0 = vmax(m0, vmax(a0, b0)); m1 = vmax(m1, vmax(a1, b1)); m2 = vmax(m2, vmax(a2, b2)); m3 = vmax(m3, vmax(a3, b3));
            }
            float x0 = hmax(m0), x1 = hmax(m1), x2 = hmax(m2), x3 = hmax(m3);
            for (int k = nb16; k < nb; k++) {
                float s0 = 0, s1 = 0, s2 = 0, s3 = 0;
                for (int j = 0; j < d; j++) { const float v = xb[(int64_t)j * BLOCO + k]; s0 += w0[j] * v; s1 += w1[j] * v; s2 += w2[j] * v; s3 += w3[j] * v; }
                x0 = s0 > x0 ? s0 : x0; x1 = s1 > x1 ? s1 : x1; x2 = s2 > x2 ? s2 : x2; x3 = s3 > x3 ? s3 : x3;
            }
            if (x0 > melhor[i]) melhor[i] = x0;
            if (x1 > melhor[i + 1]) melhor[i + 1] = x1;
            if (x2 > melhor[i + 2]) melhor[i + 2] = x2;
            if (x3 > melhor[i + 3]) melhor[i + 3] = x3;
        }
        for (; i < m; i++) {
            const float *w = W + (int64_t)i * d;
            float mx = melhor[i];
            for (int k = 0; k < nb; k++) {
                float s = 0;
                for (int j = 0; j < d; j++) s += w[j] * xb[(int64_t)j * BLOCO + k];
                mx = s > mx ? s : mx;
            }
            melhor[i] = mx;
        }
    }
}
