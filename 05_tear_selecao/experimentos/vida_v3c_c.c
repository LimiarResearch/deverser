/* A vida da versão 3 completa em C (03/10/2026): a mesma vida de `vida_v3c.viver`, com a mesma ordem de testes (antes, treino com a prova silenciosa, depois nas treinadas, depois
   nas retidas, depois em todas; o e5; o reteste) e a mesma conta das fases e das que não pararam. O plano de cada vida vem pronto do Python. A prova de que é a mesma vida, bit a
   bit, está em `testes/test_vida_v3c.py`.

   A velocidade (a meta declarada: 1 milhão de medidas por minuto), três coisas EXATAS:
     os registradores   os 16 num inteiro de 16 bits; o ponteiro da memória é uma rotação (o bit t do ponteiro é o registrador a + t)
     o laço sem fim     se a máquina volta a um estado (instrução, registradores, memória) por onde já passou, ela nunca para: a fase acaba ali, como "não parou", e os
                        registradores do fim (a porta r12, lida depois de aprender) saem andando o resto do ciclo módulo o período (Brent: memória O(1))
     a fase lembrada    a fase é uma função pura dos registradores de entrada e do conteúdo da memória (o hash de Zobrist, atualizado a cada bit que muda): uma fase que já
                        rodou com a mesma entrada e a mesma memória, sem mudar a memória, devolve o mesmo resultado, em qualquer vida da medida */
#include <stdint.h>
#include <string.h>

#define M_BITS 512
#define MAX_P 256
#define MAX_E 8

typedef struct { uint8_t op, d, a, b; uint16_t md, ma, mb; int32_t alvo; } Ins;

static Ins g_prog[MAX_P];
static int g_n = 0;
static int g_teto = 256;
/* (03/10, a medida paralela) o estado de uma vida que corre: o hash de Zobrist da memória e a conta das fases; um por vida, para que as 16 vidas de uma medida corram juntas */
typedef struct { uint64_t hash; long fases, nao; } Ctx;
static Ctx g_cx0;
static uint64_t g_z[M_BITS];
static int g_z_pronto = 0;
static int g_memo = 1;
/* (04/10, decisão tomada depois de medida a parede do e3, a rosa a 20 milhões) o índice direto: LEIAJ (10) e ESCREVAJ (11) leem e escrevem mem[8 b + (r[a], r[a+1], r[a+2])],
   uma janela de 3 registradores e uma tabela escolhida pelo b (16 tabelas de 8), sem o degrau nem a fase no endereço. Desligado por padrão: as operações 10 a 15 valem NADA, como antes. */
static int g_janela = 0;
/* (04/10, recomendação da revisão de planejamento, aprovada) o índice generalizado, com VIDA_JANELA=2: LEIAG (12) e ESCREVAG (13) leem e escrevem mem[jan(a) | jan(b) << 3], o endereço de 6 bits
   feito de duas janelas de 3 registradores, cada uma a partir de qualquer registrador (a entrada e o degrau juntos, ou uma janela corrida de 6, ou o que a busca achar). */
void janela(int nivel) { g_janela = nivel < 0 ? 0 : (nivel > 2 ? 2 : nivel); }
static inline int op_max(void) { return g_janela == 2 ? 13 : (g_janela ? 11 : 9); }
static inline int jan(uint16_t r, int a) { return ((r >> a) & 1) | (((r >> ((a + 1) & 15)) & 1) << 1) | (((r >> ((a + 2) & 15)) & 1) << 2); }
static int g_brent = 1;                 /* (depuração) o atalho do laço sem fim ligado */
void brent(int sim) { g_brent = sim; }

static uint64_t _mix(uint64_t x) { x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return x; }

static void _zobrist(void) {
    if (g_z_pronto) return;
    for (int i = 0; i < M_BITS; i++) g_z[i] = _mix(0x9E3779B97F4A7C15ULL * (uint64_t)(i + 1));
    g_z_pronto = 1;
}

/* ---- a lembrança: uma tabela por medida, chave = hash da memória misturado com a entrada da fase */
#define LEM_BITS 15
#define LEM_N (1 << LEM_BITS)
/* a entrada lembrada em duas palavras: w1 = (geração, saída, parou, porta) e w0 = chave ^ w1. Os fios leem e escrevem sem trava; uma leitura que pegou metade de uma escrita
   falha na conferência (w0 ^ w1 != chave) e vale como não lembrada: a fase roda de novo e dá o mesmo resultado. A lembrança só poupa tempo; o resultado é sempre o mesmo. */
typedef struct { uint64_t w0, w1; } Lem;
static Lem g_lem[LEM_N];
static uint32_t g_geracao = 1;

static inline uint16_t rot(uint16_t r, int a) { return (uint16_t)(((r >> a) | (r << (16 - a))) & 0xFFFF); }
static inline int ptr(uint16_t r, int a) { return a ? (rot(r, a) & 0x1FF) : (r & 0x1FF); }

/* uma fase a partir dos registradores `r0`; devolve 1 se parou; os registradores do fim em *rf */
static int rodar(Ctx *cx, uint8_t *mem, uint16_t r0, uint16_t *rf) {
    uint16_t r = r0;
    int pc = 0, passos = 0, n = g_n, teto = g_teto;
    /* Brent: o estado guardado e o tamanho da janela */
    int s_pc = 0; uint16_t s_r = r; uint64_t s_h = cx->hash; int pot = 1, lam = 0;
    while (pc < n && passos < teto) {
        const Ins *I = &g_prog[pc];
        passos++;
        switch (I->op) {
            case 0: pc++; break;
            case 7: pc = (r & I->ma) ? pc + 1 : I->alvo; break;
            case 1: r = (r & I->ma) ? (r | I->md) : (r & ~I->md); pc++; break;
            case 2: r = (r & I->ma) ? (r & ~I->md) : (r | I->md); pc++; break;
            case 3: r = ((r & I->ma) && (r & I->mb)) ? (r | I->md) : (r & ~I->md); pc++; break;
            case 4: r = ((r & I->ma) || (r & I->mb)) ? (r | I->md) : (r & ~I->md); pc++; break;
            case 5: r = ((!(r & I->ma)) != (!(r & I->mb))) ? (r | I->md) : (r & ~I->md); pc++; break;
            case 6: r = ((r & I->ma) && (r & I->mb)) ? (r & ~I->md) : (r | I->md); pc++; break;
            case 8: r = mem[ptr(r, I->a)] ? (r | I->md) : (r & ~I->md); pc++; break;
            case 9: { int q = ptr(r, I->a); uint8_t v = (r & I->md) ? 1 : 0; if (mem[q] != v) { mem[q] = v; cx->hash ^= g_z[q]; } pc++; } break;
            case 10: r = mem[8 * I->b + jan(r, I->a)] ? (r | I->md) : (r & ~I->md); pc++; break;
            case 11: { int q = 8 * I->b + jan(r, I->a); uint8_t v = (r & I->md) ? 1 : 0; if (mem[q] != v) { mem[q] = v; cx->hash ^= g_z[q]; } pc++; } break;
            case 12: r = mem[jan(r, I->a) | (jan(r, I->b) << 3)] ? (r | I->md) : (r & ~I->md); pc++; break;
            case 13: { int q = jan(r, I->a) | (jan(r, I->b) << 3); uint8_t v = (r & I->md) ? 1 : 0; if (mem[q] != v) { mem[q] = v; cx->hash ^= g_z[q]; } pc++; } break;
            default: pc++; break;
        }
        if (pc >= n) break;
        /* o laço sem fim: o mesmo estado (instrução, registradores, memória) de novo */
        if (g_brent && pc == s_pc && r == s_r && cx->hash == s_h) {
            int resto = (teto - passos) % (lam + 1);           /* o estado de agora é o de `lam + 1` passos atrás: o período divide lam + 1, e andar o resto dá os registradores do teto */
            for (int t = 0; t < resto; t++) {
                const Ins *J = &g_prog[pc];
                switch (J->op) {
                    case 0: pc++; break;
                    case 7: pc = (r & J->ma) ? pc + 1 : J->alvo; break;
                    case 1: r = (r & J->ma) ? (r | J->md) : (r & ~J->md); pc++; break;
                    case 2: r = (r & J->ma) ? (r & ~J->md) : (r | J->md); pc++; break;
                    case 3: r = ((r & J->ma) && (r & J->mb)) ? (r | J->md) : (r & ~J->md); pc++; break;
                    case 4: r = ((r & J->ma) || (r & J->mb)) ? (r | J->md) : (r & ~J->md); pc++; break;
                    case 5: r = ((!(r & J->ma)) != (!(r & J->mb))) ? (r | J->md) : (r & ~J->md); pc++; break;
                    case 6: r = ((r & J->ma) && (r & J->mb)) ? (r & ~J->md) : (r | J->md); pc++; break;
                    case 8: r = mem[ptr(r, J->a)] ? (r | J->md) : (r & ~J->md); pc++; break;
                    /* (04/10, a sonda achou) a escrita TEM de rodar aqui: o ciclo pode escrever um bit e apagá-lo depois; no fim de um ciclo inteiro a memória volta, mas o
                       teto pode cair no meio dele, e a fase seguinte lê a memória do meio */
                    case 9: { int q = ptr(r, J->a); uint8_t v = (r & J->md) ? 1 : 0; if (mem[q] != v) { mem[q] = v; cx->hash ^= g_z[q]; } pc++; } break;
                    case 10: r = mem[8 * J->b + jan(r, J->a)] ? (r | J->md) : (r & ~J->md); pc++; break;
                    case 11: { int q = 8 * J->b + jan(r, J->a); uint8_t v = (r & J->md) ? 1 : 0; if (mem[q] != v) { mem[q] = v; cx->hash ^= g_z[q]; } pc++; } break;
                    case 12: r = mem[jan(r, J->a) | (jan(r, J->b) << 3)] ? (r | J->md) : (r & ~J->md); pc++; break;
                    case 13: { int q = jan(r, J->a) | (jan(r, J->b) << 3); uint8_t v = (r & J->md) ? 1 : 0; if (mem[q] != v) { mem[q] = v; cx->hash ^= g_z[q]; } pc++; } break;
                    default: pc++; break;
                }
            }
            *rf = r;
            cx->fases++; cx->nao++;
            return 0;
        }
        if (++lam == pot) { s_pc = pc; s_r = r; s_h = cx->hash; pot <<= 1; lam = 0; }
    }
    *rf = r;
    cx->fases++;
    if (pc < n) { cx->nao++; return 0; }
    return 1;
}

static uint16_t entrada(const uint8_t *x, int n_in, int k, int aprender, const uint8_t *certa, int n_out) {
    uint16_t r = 0;
    for (int j = 0; j < n_in; j++) if (x[j]) r |= (uint16_t)(1u << j);
    r |= (uint16_t)((k & 7) << 4);
    if (aprender) { r |= (1u << 7); for (int t = 0; t < n_out; t++) if (certa[t]) r |= (uint16_t)(1u << (8 + t)); }
    return r;
}

/* uma fase, lembrada: devolve se parou; a saída (bits 15, 14, 13) e a porta r12 */
static int fase(Ctx *cx, uint8_t *mem, uint16_t r0, uint8_t *saida, uint8_t *porta) {
    Lem *l = 0;
    uint64_t chave = 0;
    if (g_memo) {
        chave = _mix(cx->hash ^ ((uint64_t)r0 * 0x9E3779B97F4A7C15ULL) ^ 0x5bd1e995ULL);
        l = &g_lem[chave & (LEM_N - 1)];
        uint64_t w0 = __atomic_load_n(&l->w0, __ATOMIC_RELAXED), w1 = __atomic_load_n(&l->w1, __ATOMIC_RELAXED);
        if ((w0 ^ w1) == chave && (uint32_t)(w1 >> 32) == g_geracao) {
            int parou = (int)((w1 >> 8) & 1);
            uint16_t sai = (uint16_t)(w1 >> 16);
            cx->fases++;
            if (!parou) cx->nao++;
            saida[0] = (sai >> 15) & 1; saida[1] = (sai >> 14) & 1; saida[2] = (sai >> 13) & 1;
            if (porta) *porta = (uint8_t)(w1 & 1);
            return parou;
        }
    }
    uint64_t h0 = cx->hash;
    uint16_t rf;
    int parou = rodar(cx, mem, r0, &rf);
    saida[0] = (rf >> 15) & 1; saida[1] = (rf >> 14) & 1; saida[2] = (rf >> 13) & 1;
    if (porta) *porta = (rf >> 12) & 1;
    if (l && cx->hash == h0) {
        uint64_t w1 = ((uint64_t)g_geracao << 32) | ((uint64_t)rf << 16) | ((uint64_t)(parou ? 1 : 0) << 8) | (uint64_t)((rf >> 12) & 1);
        __atomic_store_n(&l->w1, w1, __ATOMIC_RELAXED);
        __atomic_store_n(&l->w0, chave ^ w1, __ATOMIC_RELAXED);
    }
    return parou;
}

static int responder(Ctx *cx, uint8_t *mem, const uint8_t *x, int n_in, int k, const uint8_t *y, int n_out, uint8_t *resp) {
    uint8_t s[3];
    int parou = fase(cx, mem, entrada(x, n_in, k, 0, 0, n_out), s, 0);
    int ok = parou;
    for (int t = 0; t < n_out; t++) {
        if (resp) resp[t] = parou ? s[t] : 255;
        if (!parou || s[t] != y[t]) ok = 0;
    }
    return ok;
}

static int testar(Ctx *cx, uint8_t *mem, const uint8_t *X, const uint8_t *Y, int n_in, int n_out, int k, const int32_t *idx, int m, uint8_t *resps) {
    int ac = 0;
    for (int i = 0; i < m; i++) {
        int s = idx[i];
        ac += responder(cx, mem, X + s * n_in, n_in, k, Y + s * n_out, n_out, resps ? resps + i * n_out : 0);
    }
    return ac;
}

static int parados(const uint8_t *Y, const uint8_t *resps, int m, int n_out) {
    for (int j = 0; j < n_out; j++) {
        int yvaria = 0, rparada = 1;
        for (int s = 1; s < m; s++) {
            if (Y[s * n_out + j] != Y[j]) yvaria = 1;
            if (resps[s * n_out + j] != resps[j]) rparada = 0;
        }
        if (yvaria && rparada) return 1;
    }
    return 0;
}

static int decodificar(const uint8_t *bits_prog, int p, int bsalto) {
    if (p > MAX_P) return -1;
    for (int i = 0; i < p; i++) {
        const uint8_t *x = bits_prog + 16 * i;
        int f[4];
        for (int c = 0; c < 4; c++) f[c] = (x[4 * c] << 3) | (x[4 * c + 1] << 2) | (x[4 * c + 2] << 1) | x[4 * c + 3];
        int op = f[0] <= op_max() ? f[0] : 0, usa = op >= 1 && op <= op_max(), b = 0;
        if (op == 7 && bsalto > 0) b = f[3] & ((1 << bsalto) - 1);
        else if ((op >= 3 && op <= 6) || op >= 10) b = f[3];
        int d = usa ? f[1] : 0, a = usa ? f[2] : 0;
        Ins *I = &g_prog[i];
        I->op = (uint8_t)op; I->d = (uint8_t)d; I->a = (uint8_t)a; I->b = (uint8_t)b;
        I->md = (uint16_t)(1u << d); I->ma = (uint16_t)(1u << a); I->mb = (uint16_t)(1u << b);
        I->alvo = d + 16 * (b & 7);
    }
    g_n = p;
    return 0;
}

/* uma vida, com o programa já decodificado; o resto como antes (cab de 15 inteiros por etapa) */
static int vida_dec(Ctx *cx, int teto, int ne, const int32_t *cab, const uint8_t *X, const uint8_t *Y, const int32_t *idx, int reteste, int32_t *out) {
    if (ne > MAX_E) return -1;
    (void)teto;                                                 /* o teto é posto por quem chama, antes das vidas correrem */
    cx->fases = 0; cx->nao = 0;
    uint8_t mem[M_BITS], copia[M_BITS], resps[64 * 3];
    memset(mem, 0, sizeof mem);
    cx->hash = 0;
    for (int e = 0; e < ne; e++) {
        const int32_t *c = cab + 15 * e;
        int k = c[0], so_teste = c[1], com_prova = c[2], n_in = c[3], n_out = c[4], n_todas = c[5];
        const uint8_t *Xe = X + c[6], *Ye = Y + c[7];
        const int32_t *trein = idx + c[9], *ret = idx + c[11], *seq = idx + c[13], *todas = idx + c[14];
        int n_trein = c[8], n_ret = c[10], n_seq = c[12];
        int32_t *o = out + 9 * e;
        if (!so_teste) {
            o[0] = testar(cx, mem, Xe, Ye, n_in, n_out, k, todas, n_todas, 0);
            int erros = 0, pediu = 0, passou = -1;
            for (int s = 0; s < n_seq; s++) {
                int si = seq[s];
                erros += !responder(cx, mem, Xe + si * n_in, n_in, k, Ye + si * n_out, n_out, 0);
                uint8_t sai[3], porta = 0;
                fase(cx, mem, entrada(Xe + si * n_in, n_in, k, 1, Ye + si * n_out, n_out), sai, &porta);
                if (com_prova && porta == 1 && !pediu) {
                    pediu = 1;
                    memcpy(copia, mem, M_BITS);
                    uint64_t h = cx->hash;
                    passou = testar(cx, mem, Xe, Ye, n_in, n_out, k, trein, n_trein, 0) == n_trein;
                    memcpy(mem, copia, M_BITS);
                    cx->hash = h;                                         /* a memória e o hash voltam juntos */
                }
            }
            o[1] = erros; o[2] = pediu; o[3] = passou;
            o[4] = testar(cx, mem, Xe, Ye, n_in, n_out, k, trein, n_trein, 0);
            o[5] = n_ret ? testar(cx, mem, Xe, Ye, n_in, n_out, k, ret, n_ret, 0) : 0;
        } else {
            o[0] = o[1] = o[2] = 0; o[3] = -1; o[4] = o[5] = 0;
        }
        o[6] = testar(cx, mem, Xe, Ye, n_in, n_out, k, todas, n_todas, resps);
        uint8_t Yt[64 * 3];
        for (int i = 0; i < n_todas; i++) for (int t = 0; t < n_out; t++) Yt[i * n_out + t] = Ye[todas[i] * n_out + t];
        o[7] = parados(Yt, resps, n_todas, n_out);
        o[8] = 0;
    }
    if (reteste) {
        for (int e = 0; e < ne; e++) {
            const int32_t *c = cab + 15 * e;
            out[9 * e + 8] = testar(cx, mem, X + c[6], Y + c[7], c[3], c[4], c[0], idx + c[14], c[5], 0);
        }
    }
    out[9 * ne] = (int32_t)cx->fases;
    out[9 * ne + 1] = (int32_t)cx->nao;
    return 0;
}

int vida(const uint8_t *bits_prog, int p, int bsalto, int teto, int ne, const int32_t *cab, const uint8_t *X, const uint8_t *Y, const int32_t *idx, int reteste, int32_t *out) {
    _zobrist();
    if (decodificar(bits_prog, p, bsalto) != 0) return -1;
    g_geracao++;
    g_teto = teto;
    return vida_dec(&g_cx0, teto, ne, cab, X, Y, idx, reteste, out);
}

/* As vidas de uma medida numa chamada (a lembrança vale entre as vidas da mesma medida: o mesmo programa, a mesma memória, a mesma entrada, o mesmo resultado). */
int medida(const uint8_t *bits_prog, int p, int bsalto, int teto, int n_vidas, void **planos, const int32_t *nes, const int32_t *retestes, int32_t *out) {
    _zobrist();
    if (decodificar(bits_prog, p, bsalto) != 0) return -1;
    g_geracao++;
    g_teto = teto;
    int pos = 0;
    for (int v = 0; v < n_vidas; v++) {
        int r = vida_dec(&g_cx0, teto, nes[v], (const int32_t *)planos[4 * v], (const uint8_t *)planos[4 * v + 1], (const uint8_t *)planos[4 * v + 2],
                         (const int32_t *)planos[4 * v + 3], retestes[v], out + pos);
        if (r != 0) return r;
        pos += 9 * nes[v] + 2;
    }
    return 0;
}

void lembrar(int sim) { g_memo = sim; }

/* ======================================================================= a versão 3c.1 inteira em C: as vidas geradas pela semente (splitmix64, a mesma ordem de sorteios
   de `vida_v3c1.plano`), as 16 vidas, as contas das cláusulas (as mesmas operações de ponto flutuante do Python: frações, médias sequenciais, metade a média e metade a pior vida)
   e a distância (o arredondamento ao par, como o `round` do Python). */
#include <math.h>

static const int N_ENT[6] = {1, 3, 3, 4, 4, 3};
static int g_funcoes_h[256], g_n_funcoes = 0;

static void _funcoes_h(void) {
    if (g_n_funcoes) return;
    for (int t = 0; t < 256; t++) {
        int todas = 1;
        for (int j = 0; j < 3 && todas; j++) {
            int igual = 1;
            for (int x = 0; x < 8; x++) if (((t >> x) & 1) != ((t >> (x ^ (1 << j))) & 1)) { igual = 0; break; }
            if (igual) todas = 0;
        }
        if (todas) g_funcoes_h[g_n_funcoes++] = t;
    }
}

typedef struct { uint64_t x; } Sm;
static uint64_t sm_prox(Sm *s) {
    s->x += 0x9E3779B97F4A7C15ULL;
    uint64_t z = s->x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static void sm_perm(Sm *s, int n, int *p) {
    for (int i = 0; i < n; i++) p[i] = i;
    for (int i = n - 1; i > 0; i--) { int j = (int)(sm_prox(s) % (uint64_t)(i + 1)); int t = p[i]; p[i] = p[j]; p[j] = t; }
}

uint64_t semente_do_programa(const uint8_t *bits, int p) {
    uint64_t h = 0x6A09E667F3BCC908ULL;
    for (int i = 0; i < p; i++) {
        const uint8_t *x = bits + 16 * i;
        int f[4];
        for (int c = 0; c < 4; c++) f[c] = (x[4 * c] << 3) | (x[4 * c + 1] << 2) | (x[4 * c + 2] << 1) | x[4 * c + 3];
        int op = f[0] <= op_max() ? f[0] : 0, usa = op >= 1 && op <= op_max(), b = 0;
        if (op == 7) b = f[3] & 7; else if ((op >= 3 && op <= 6) || op >= 10) b = f[3];
        uint64_t w = ((uint64_t)op << 12) | ((uint64_t)(usa ? f[1] : 0) << 8) | ((uint64_t)(usa ? f[2] : 0) << 4) | (uint64_t)b;
        Sm s = {h ^ (w + ((uint64_t)i << 16))};
        h = sm_prox(&s);
    }
    return h;
}

static int _gg(int gn, int x) { return x ^ gn; }
static int _hh(int t, int a, int b, int c) { return (t >> (a + 2 * b + 4 * c)) & 1; }
/* (05/10, a família de D; congelada antes de qualquer corrida) g_familia = 0: o leito de sempre. 1, "espelho": o e2 com as saídas na ordem invertida; o e3 com as janelas
   trocadas e os argumentos de h invertidos; o e4 com g no meio da janela; o e5 h(g, g, g). 2, "deslocada": a 2ª janela do e3 dá a volta; o e4 com g por fora de h; o e5 h(x0, x1, g(x2)).
   As primitivas (g de 1 bit, h de 3 bits que depende das três), o número de entradas de cada degrau e as cláusulas são os mesmos. */
static int g_familia = 0;
void familia(int f) { g_familia = f; }
/* (05/10, a família sorteada) g_familia = 3: a gramática vem de uma tabela de expressões pós-fixas (experimentos/familia_sorteada.py), a MESMA que o Python lê: por degrau e
   saída, o tamanho e os símbolos (0 a 3: x0 a x3; 4: g do topo; 5: h(a, b, c), com c no topo). Entregue por `familia_tabela` (6 x 3 x 16 bytes). */
static uint8_t g_tab_fam[6][3][16];
static const int N_SAI_FAM[6] = {1, 1, 3, 2, 2, 1};
void familia_tabela(const uint8_t *b) { memcpy(g_tab_fam, b, sizeof(g_tab_fam)); }
static int avaliar_fam(const uint8_t *e, const uint8_t *x, int gn, int t) {
    int st[16], n = 0, L = e[0];
    for (int i = 1; i <= L; i++) {
        int s = e[i];
        if (s < 4) st[n++] = x[s];
        else if (s == 4) st[n - 1] = _gg(gn, st[n - 1]);
        else { int c = st[--n], b = st[--n], a = st[--n]; st[n++] = _hh(t, a, b, c); }
    }
    return st[0];
}
static int alvo_c(int k, const uint8_t *x, int gn, int t, uint8_t *y) {
    if (g_familia == 3) { for (int j = 0; j < N_SAI_FAM[k]; j++) y[j] = (uint8_t)avaliar_fam(g_tab_fam[k][j], x, gn, t); return N_SAI_FAM[k]; }
    if (g_familia == 1) switch (k) {
        case 0: y[0] = (uint8_t)_gg(gn, x[0]); return 1;
        case 1: y[0] = (uint8_t)_hh(t, x[0], x[1], x[2]); return 1;
        case 2: y[0] = (uint8_t)_gg(gn, x[2]); y[1] = (uint8_t)_gg(gn, x[1]); y[2] = (uint8_t)_gg(gn, x[0]); return 3;
        case 3: y[0] = (uint8_t)_hh(t, x[3], x[2], x[1]); y[1] = (uint8_t)_hh(t, x[2], x[1], x[0]); return 2;
        case 4: y[0] = (uint8_t)_hh(t, x[0], _gg(gn, x[1]), x[2]); y[1] = (uint8_t)_hh(t, x[1], _gg(gn, x[2]), x[3]); return 2;
        default: y[0] = (uint8_t)_hh(t, _gg(gn, x[0]), _gg(gn, x[1]), _gg(gn, x[2])); return 1;
    }
    if (g_familia == 2) switch (k) {
        case 0: y[0] = (uint8_t)_gg(gn, x[0]); return 1;
        case 1: y[0] = (uint8_t)_hh(t, x[0], x[1], x[2]); return 1;
        case 2: y[0] = (uint8_t)_gg(gn, x[0]); y[1] = (uint8_t)_gg(gn, x[1]); y[2] = (uint8_t)_gg(gn, x[2]); return 3;
        case 3: y[0] = (uint8_t)_hh(t, x[0], x[1], x[2]); y[1] = (uint8_t)_hh(t, x[2], x[3], x[0]); return 2;
        case 4: y[0] = (uint8_t)_gg(gn, _hh(t, x[0], x[1], x[2])); y[1] = (uint8_t)_gg(gn, _hh(t, x[1], x[2], x[3])); return 2;
        default: y[0] = (uint8_t)_hh(t, x[0], x[1], _gg(gn, x[2])); return 1;
    }
    switch (k) {
        case 0: y[0] = (uint8_t)_gg(gn, x[0]); return 1;
        case 1: y[0] = (uint8_t)_hh(t, x[0], x[1], x[2]); return 1;
        case 2: y[0] = (uint8_t)_gg(gn, x[0]); y[1] = (uint8_t)_gg(gn, x[1]); y[2] = (uint8_t)_gg(gn, x[2]); return 3;
        case 3: y[0] = (uint8_t)_hh(t, x[0], x[1], x[2]); y[1] = (uint8_t)_hh(t, x[1], x[2], x[3]); return 2;
        case 4: y[0] = (uint8_t)_hh(t, _gg(gn, x[0]), x[1], x[2]); y[1] = (uint8_t)_hh(t, _gg(gn, x[1]), x[2], x[3]); return 2;
        default: y[0] = (uint8_t)_gg(gn, _hh(t, x[0], x[1], x[2])); return 1;
    }
}

typedef struct { int gn, t, gn2, t2; int ntodas[6], ntr[6], nrt[6], tr[6][16], rt[6][16], nseq[6], seq[6][128]; } Plano;

static void plano_c(uint64_t semente, int i, Plano *P) {
    Sm r = {semente ^ (0xA0761D6478BD642FULL * (uint64_t)(i + 1))};
    for (int k = 0; k < 6; k++) {
        int n = 1 << N_ENT[k];
        P->ntodas[k] = n;
        if (k == 0 || k == 1) { P->ntr[k] = n; P->nrt[k] = 0; for (int j = 0; j < n; j++) P->tr[k][j] = j; }
        else if (k == 5) { P->ntr[k] = 0; P->nrt[k] = n; for (int j = 0; j < n; j++) P->rt[k][j] = j; }
        else {
            int p[16], meio = n / 2, a[16], b[16];
            sm_perm(&r, n, p);
            for (int j = 0; j < meio; j++) a[j] = p[j];
            for (int j = meio; j < n; j++) b[j - meio] = p[j];
            for (int u = 0; u < meio; u++) for (int v = u + 1; v < meio; v++) if (a[v] < a[u]) { int t = a[u]; a[u] = a[v]; a[v] = t; }
            for (int u = 0; u < n - meio; u++) for (int v = u + 1; v < n - meio; v++) if (b[v] < b[u]) { int t = b[u]; b[u] = b[v]; b[v] = t; }
            P->ntr[k] = meio; P->nrt[k] = n - meio;
            for (int j = 0; j < meio; j++) P->tr[k][j] = a[j];
            for (int j = 0; j < n - meio; j++) P->rt[k][j] = b[j];
        }
    }
    P->gn = i % 2; P->gn2 = 1 - P->gn;
    P->t = g_funcoes_h[sm_prox(&r) % (uint64_t)g_n_funcoes];
    for (;;) {
        int t2 = g_funcoes_h[sm_prox(&r) % (uint64_t)g_n_funcoes];
        if (__builtin_popcount((unsigned)(P->t ^ t2)) < 2) continue;
        int muda = 0;
        for (int j = 0; j < P->ntr[4] && !muda; j++) {
            int s = P->tr[4][j];
            uint8_t x[4], y1[3], y2[3];
            for (int q = 0; q < 4; q++) x[q] = (uint8_t)((s >> q) & 1);
            alvo_c(4, x, P->gn2, t2, y2); alvo_c(4, x, P->gn, P->t, y1);
            if (y1[0] != y2[0] || y1[1] != y2[1]) muda = 1;
        }
        if (muda) { P->t2 = t2; break; }
    }
    for (int k = 0; k < 5; k++) {
        int n = P->ntr[k], pos = 0, p[16];
        for (int rr = 0; rr < 8; rr++) { sm_perm(&r, n, p); for (int j = 0; j < n; j++) P->seq[k][pos++] = P->tr[k][p[j]]; }
        P->nseq[k] = pos;
    }
}

/* monta o cab, X, Y e idx de uma vida (tipo 0 vida, 1 c2, 2 c4, 3 c5), no formato de `vida_dec` */
static int montar_c(const Plano *P, int tipo, int32_t *cab, uint8_t *X, uint8_t *Y, int32_t *idx, int *reteste) {
    int ks[6], so[6], prova[6], troc[6], ne = 0;
    if (tipo == 0) { for (int k = 0; k < 5; k++) { ks[ne] = k; so[ne] = 0; prova[ne] = 1; troc[ne] = 0; ne++; } ks[ne] = 5; so[ne] = 1; prova[ne] = 0; troc[ne] = 0; ne++; *reteste = 1; }
    else if (tipo == 1) { for (int k = 0; k < 3; k++) { ks[ne] = k; so[ne] = 0; prova[ne] = 0; troc[ne] = (k < 2); ne++; } *reteste = 0; }
    else if (tipo == 2) { for (int k = 0; k < 5; k++) { ks[ne] = k; so[ne] = 0; prova[ne] = 0; troc[ne] = (k < 4); ne++; } *reteste = 0; }
    else { for (int k = 0; k < 2; k++) { ks[ne] = k; so[ne] = 0; prova[ne] = 0; troc[ne] = 1; ne++; } ks[ne] = 5; so[ne] = 1; prova[ne] = 0; troc[ne] = 1; ne++; *reteste = 0; }
    int nx = 0, ny = 0, ni = 0;
    for (int e = 0; e < ne; e++) {
        int k = ks[e], n_in = N_ENT[k], n = P->ntodas[k];
        int gn = troc[e] ? P->gn2 : P->gn, t = troc[e] ? P->t2 : P->t;
        int dX = nx, dY = ny, n_out = 0;
        for (int s = 0; s < n; s++) {
            uint8_t x[4], y[3];
            for (int q = 0; q < n_in; q++) x[q] = (uint8_t)((s >> q) & 1);
            n_out = alvo_c(k, x, gn, t, y);
            for (int q = 0; q < n_in; q++) X[nx++] = x[q];
            for (int q = 0; q < n_out; q++) Y[ny++] = y[q];
        }
        int d_tr = ni; for (int j = 0; j < P->ntr[k]; j++) idx[ni++] = P->tr[k][j];
        int d_rt = ni; for (int j = 0; j < P->nrt[k]; j++) idx[ni++] = P->rt[k][j];
        int d_sq = ni, nsq = so[e] ? 0 : P->nseq[k]; for (int j = 0; j < nsq; j++) idx[ni++] = P->seq[k][j];
        int d_td = ni; for (int j = 0; j < n; j++) idx[ni++] = j;
        int32_t *c = cab + 15 * e;
        c[0] = k; c[1] = so[e]; c[2] = prova[e]; c[3] = n_in; c[4] = n_out; c[5] = n; c[6] = dX; c[7] = dY;
        c[8] = so[e] ? 0 : P->ntr[k]; c[9] = d_tr; c[10] = so[e] ? 0 : P->nrt[k]; c[11] = d_rt; c[12] = nsq; c[13] = d_sq; c[14] = d_td;
    }
    return ne;
}

/* as cláusulas de uma vida (as contas de `vida_v3c.valores_de_uma_vida`) a partir das saídas das 4 vidas (vida, c2, c4, c5) */
static void valores_vida(int32_t *o[4], int32_t *cab[4], const int ne[4], double *val) {
    double parados = 0;
    for (int e = 0; e < 6; e++) parados += o[0][9 * e + 7];
    val[0] = parados / 6.0;
    for (int k = 0; k < 5; k++) val[1 + k] = 1.0 - (double)o[0][9 * k + 4] / (double)cab[0][15 * k + 8];
    double s = 0.0;
    for (int e = 0; e < 6; e++) s += 1.0 - (double)o[0][9 * e + 8] / (double)cab[0][15 * e + 5];
    val[6] = s / 6.0;
    for (int q = 0; q < 2; q++) {
        int k = q == 0 ? 2 : 4, cv = q == 0 ? 1 : 2;
        int e_vida = o[0][9 * k + 1], e_ctrl = o[cv][9 * k + 1];
        double ganho = (double)(e_ctrl - e_vida) / (double)(e_ctrl > 1 ? e_ctrl : 1);
        double falta = (0.25 - ganho > 0.0 ? 0.25 - ganho : 0.0) / 0.25;
        for (int e = 0; e < ne[cv]; e++) { double f = 1.0 - (double)o[cv][9 * e + 4] / (double)cab[cv][15 * e + 8]; if (f > falta) falta = f; }
        val[7 + q] = falta;
    }
    int sem = 0, pedidos = 0, falhas = 0;
    for (int k = 0; k < 5; k++) { if (!o[0][9 * k + 2]) sem++; else { pedidos++; if (o[0][9 * k + 3] != 1) falhas++; } }
    val[9] = (double)sem / 5.0;
    val[10] = pedidos ? (double)falhas / (double)pedidos : 0.0;
    s = 0.0;
    for (int k = 2; k <= 4; k++) s += 1.0 - (double)o[0][9 * k + 5] / (double)cab[0][15 * k + 10];
    val[11] = s / 3.0;
    val[12] = 1.0 - (double)o[0][9 * 5 + 6] / (double)cab[0][15 * 5 + 5];
    val[13] = 1.0 - (double)o[3][9 * 2 + 6] / (double)cab[3][15 * 2 + 5];
    long fases = 0, nao = 0;
    for (int v = 0; v < 4; v++) { fases += o[v][9 * ne[v]]; nao += o[v][9 * ne[v] + 1]; }
    val[14] = (double)nao / (double)(fases > 1 ? fases : 1);
}

/* a soma de `sum()` do Python (3.12 em diante) para números de ponto flutuante: a soma compensada de Neumaier, começando de 0 */
typedef struct { double f, c; } SomaPy;
static void soma_py(SomaPy *s, double x) {
    double t = s->f + x;
    if (fabs(s->f) >= fabs(x)) s->c += (s->f - t) + x; else s->c += (x - t) + s->f;
    s->f = t;
}
static double soma_py_fim(const SomaPy *s) { return (s->c != 0.0 && isfinite(s->c)) ? s->f + s->c : s->f; }

/* A medida da v3c.1: as 4 vidas da semente (a do programa se `usar_semente` = 0), os 15 valores (metade a média, metade a pior), a distância e o resumo (por vida: os erros
   de treino do e0 ao e4 e o acerto nas retidas do e2, e3 e e4, em %, arredondado ao par). */
/* (04/10, a régua v3c.2) a soma antes da razão: a subida no e2 e no e4 sai dos erros de treino somados nas 4 vidas. Desligada por padrão (a régua 4 como era). */
static int g_v32 = 0;
void regua_v32(int sim) { g_v32 = sim ? 1 : 0; }
static int g_fios = 1;
void fios(int n) { g_fios = n < 1 ? 1 : (n > 32 ? 32 : n); }

/* (03/10, a régua 4; o Fable: "toda V que o programa pode influenciar é jogada, e toda V que a busca pode reter é decorada") as vidas de um programa saem do COMPORTAMENTO
   dele e de um SAL: a sonda é a vida inteira de um plano fixo (a semente SONDA, a vida 0), e a assinatura é o hash das contas dela, degrau a degrau (a mesma `out` de `vida_dec`):
   duas variantes com o mesmo comportamento (uma instrução morta diferente) recebem as mesmas vidas, e o dado só rola quando o comportamento muda. O sal é posto por quem mede
   (a ilha: o número da época, que muda a cada 10 mil medidas). A referência é `vida_v3c1.sonda` e `vida_v3c1.semente_das_vidas`. */
#define SONDA 0x50DA5EED1234ABCDULL
static uint64_t g_sal = 0;
static int g_sonda_ligada = 1;                /* (depuração, 04/10) 0 = as vidas pelo hash dos bits, só para medir o custo da sonda numa cópia; as corridas a deixam ligada */
void sonda_ligada(int sim) { g_sonda_ligada = sim ? 1 : 0; }
void sal_c(uint64_t sal) { g_sal = sal; }
uint64_t sal_atual(void) { return g_sal; }
static uint64_t semente_vidas(uint64_t sig, uint64_t sal) { Sm r = {sig ^ (0x9E3779B97F4A7C15ULL * (sal + 1))}; return sm_prox(&r); }
static uint64_t sonda_dec(int teto) {
    static int32_t cab[15 * 8], idx[2048], out[9 * 8 + 2];
    static uint8_t X[512], Y[512];
    static Ctx cx;
    Plano P;
    int ret;
    plano_c(SONDA, 0, &P);
    int ne = montar_c(&P, 0, cab, X, Y, idx, &ret);
    vida_dec(&cx, teto, ne, cab, X, Y, idx, ret, out);
    uint64_t h = 0xC0FFEE0DDBA11ULL;
    for (int j = 0; j < 9 * ne + 2; j++) { Sm r = {h ^ ((uint64_t)(uint32_t)out[j] + ((uint64_t)j << 32))}; h = sm_prox(&r); }
    return h;
}
/* as contas da vida da sonda (para conferir com `vida_v3c1.contas_da_sonda`); devolve quantas */
int sonda_contas(const uint8_t *bits, int p, int bsalto, int teto, int32_t *dest) {
    static int32_t cab[15 * 8], idx[2048], out[9 * 8 + 2];
    static uint8_t X[512], Y[512];
    static Ctx cx;
    _zobrist(); _funcoes_h();
    if (decodificar(bits, p, bsalto) != 0) return -1;
    g_geracao++;
    g_teto = teto;
    Plano P;
    int ret;
    plano_c(SONDA, 0, &P);
    int ne = montar_c(&P, 0, cab, X, Y, idx, &ret);
    vida_dec(&cx, teto, ne, cab, X, Y, idx, ret, out);
    for (int j = 0; j < 9 * ne + 2; j++) dest[j] = out[j];
    return 9 * ne + 2;
}
uint64_t sonda_c(const uint8_t *bits, int p, int bsalto, int teto) {
    _zobrist(); _funcoes_h();
    if (decodificar(bits, p, bsalto) != 0) return 0;
    g_geracao++;
    g_teto = teto;
    return sonda_dec(teto);
}

int julgar_c1(const uint8_t *bits, int p, int bsalto, int teto, uint64_t semente, int usar_semente, double *valores, int32_t *resumo, int32_t *dist) {
    _zobrist(); _funcoes_h();
    if (decodificar(bits, p, bsalto) != 0) return -1;
    g_geracao++;
    g_teto = teto;
    uint64_t s = usar_semente ? semente : (g_sonda_ligada ? semente_vidas(sonda_dec(teto), g_sal) : semente_vidas(semente_do_programa(bits, p), g_sal));   /* (régua 4) a busca: o comportamento e o sal; o banco e o desenvolvimento: a semente dada */
    /* (03/10, a medida paralela; o requisito: ganhar velocidade sem perder nada da qualidade da seleção) as 16 vidas (4 vidas x vida, c2, c4, c5) são independentes: montadas
       aqui, corridas juntas em `g_fios` fios (as 4 vidas inteiras primeiro, que são as mais longas), e as contas das cláusulas depois, em série e na mesma ordem: o mesmo
       resultado, bit a bit, com 1 fio ou com muitos (testes/test_vida_v3c1.py). */
    static int32_t cab[16][15 * 8], idx[16][2048], out[16][9 * 8 + 2];
    static uint8_t X[16][512], Y[16][512];
    static Ctx cx[16];
    static const int ordem[16] = {0, 4, 8, 12, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15};
    int ne[16], ret[16], rr[16];
    double pv[4][15];
    for (int i = 0; i < 4; i++) {
        Plano P;
        plano_c(s, i, &P);
        for (int tipo = 0; tipo < 4; tipo++) { int j = 4 * i + tipo; ne[j] = montar_c(&P, tipo, cab[j], X[j], Y[j], idx[j], &ret[j]); }
    }
    #pragma omp parallel for schedule(dynamic, 1) num_threads(g_fios) if (g_fios > 1)
    for (int q = 0; q < 16; q++) { int j = ordem[q]; rr[j] = vida_dec(&cx[j], teto, ne[j], cab[j], X[j], Y[j], idx[j], ret[j], out[j]); }
    for (int j = 0; j < 16; j++) if (rr[j] != 0) return rr[j];
    for (int i = 0; i < 4; i++) {
        int32_t *op[4], *cp[4];
        for (int tipo = 0; tipo < 4; tipo++) { op[tipo] = out[4 * i + tipo]; cp[tipo] = cab[4 * i + tipo]; }
        valores_vida(op, cp, &ne[4 * i], pv[i]);
        for (int k = 0; k < 5; k++) resumo[8 * i + k] = out[4 * i][9 * k + 1];
        for (int k = 2; k <= 4; k++) resumo[8 * i + 3 + k] = (int32_t)rint(100.0 * ((double)out[4 * i][9 * k + 5] / (double)cab[4 * i][15 * k + 10]));
        /* (03/10, o Fable: "a seleção vê as partes" do c8) os dois componentes da subida ao e4, por vida: os erros de treino no e4 na vida e no controle c4, e quantos dos
           degraus de baixo (e0 a e3) o controle domina */
        int dom = 0;
        for (int e = 0; e < 4; e++) if (out[4 * i + 2][9 * e + 4] == cab[4 * i + 2][15 * e + 8]) dom++;
        resumo[32 + 4 * i + 0] = out[4 * i][9 * 4 + 1];
        resumo[32 + 4 * i + 1] = out[4 * i + 2][9 * 4 + 1];
        resumo[32 + 4 * i + 2] = dom;
        resumo[32 + 4 * i + 3] = 0;
    }
    double v32[2] = {0.0, 0.0};
    if (g_v32) for (int q = 0; q < 2; q++) {
        int k = q == 0 ? 2 : 4, cv = q == 0 ? 1 : 2;
        long ev = 0, ec = 0;
        for (int i = 0; i < 4; i++) { ev += out[4 * i][9 * k + 1]; ec += out[4 * i + cv][9 * k + 1]; }
        double ganho = (double)(ec - ev) / (double)(ec > 1 ? ec : 1);
        double falta = (0.25 - ganho > 0.0 ? 0.25 - ganho : 0.0) / 0.25;
        for (int i = 0; i < 4; i++) {
            int j = 4 * i + cv;
            for (int e = 0; e < ne[j]; e++) { double f = 1.0 - (double)out[j][9 * e + 4] / (double)cab[j][15 * e + 8]; if (f > falta) falta = f; }
        }
        v32[q] = falta;
    }
    SomaPy soma = {0.0, 0.0};
    for (int c = 0; c < 15; c++) {
        SomaPy m = {0.0, 0.0};
        double mx = pv[0][c];
        for (int i = 0; i < 4; i++) { soma_py(&m, pv[i][c]); if (pv[i][c] > mx) mx = pv[i][c]; }
        valores[c] = 0.5 * (soma_py_fim(&m) / 4.0) + 0.5 * mx;
        if (g_v32 && (c == 7 || c == 8)) valores[c] = v32[c - 7];
        double v = valores[c] > 0.0 ? valores[c] : 0.0;
        soma_py(&soma, v < 1.0 ? v : 1.0);
    }
    *dist = (int32_t)rint(1000.0 * soma_py_fim(&soma));
    return 0;
}

/* ======================================================================= a ilha em C (03/10/2026; a meta declarada: 1 milhão de medidas por minuto): a evolução regularizada
   inteira (Real et al. 2019, a mesma de `bancada_c2.condicoes.evolucao`: população de 64, torneio de 8, o filho entra e o mais velho sai, a mutação de campos ou de 1 a 3 bits
   ativos, a forma canônica, as fotos repetidas não custam medida) sobre a v3c.1, com a CONFIRMAÇÃO do Fable: o vencedor de um torneio só vira pai depois de medido de novo em
   vidas novas (a semente do programa mais um), e vale a pior das duas; recorde só de programa confirmado. O sorteador é o do C (xoshiro256**): o caminho não repete o do Python. */
#include <stdlib.h>

#define PI_P 128
#define POP_MAX 256

typedef struct { uint8_t f[PI_P][4]; int32_t d; uint8_t conf; uint64_t chave; float v[15]; int16_t tag; uint8_t logado; int32_t dpai; } Indiv;   /* (04/10, a revisão) tag: a ação que gerou o indivíduo (-1: nenhuma), dpai: a distância do pai no nascimento */   /* conf: 0, 1 (uma semente nova: molde), 2 (duas: recorde e migrante) */

static Indiv g_pop[POP_MAX];
static int g_npop = 0, g_cab = 0, g_tam_pop = 64, g_torneio = 8;
static uint64_t g_rng[4];
static long g_medidas = 0;                    /* medidas de V (as confirmações contam) */
static int32_t g_melhor = 1 << 30;
static Indiv g_melhor_ind;
static int g_teto_ilha = 256;
static int g_lexicase = 0;                    /* (03/10) a seleção: 0 = torneio pela distância, 1 = lexicase com tolerância pelas 15 cláusulas */
static int g_tag_med = -1; static long g_custo[32];   /* (04/10, a revisão) a quem cada medida é atribuída: a ação que gerou o indivíduo medido */
static long g_remedidas = 0;                  /* no lexicase, as medidas repetidas só para ter os 15 valores de um programa já medido (não contam como medida de V) */
/* (03/10, a régua 4) o sal muda a cada SAL_P medidas (a época do sal = medidas / SAL_P), e a população é medida de novo a cada troca: a sorte de uma variante dura uma época.
   O desenvolvimento: 10 sementes próprias (2001 a 2010) que decidem molde, recorde e migrante; o banco (1001 a 1010) só declara, a busca nunca o lê. */
#define SAL_P 10000
static long g_epoca = -1;
static int32_t g_ref = 1 << 30;               /* a pior de três do recordista, medida de novo na época do sal de agora: a barra para um candidato a recorde */
static const uint64_t DEV[10] = {2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010};
static uint64_t dev_semente(int nivel) { long e = g_epoca < 0 ? 0 : g_epoca; return DEV[(e + (nivel == 1 ? 0 : 5)) % 10]; }   /* o nível 1 e o nível 2 usam duas sementes do desenvolvimento, que giram com a época */

/* a tabela das medidas: chave -> d (bits 31 e 30: o nível de confirmação) */
static uint64_t *g_tk = 0;
static int32_t *g_tv = 0;
static size_t g_tcap = 0, g_tn = 0;

static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t xo(void) {
    uint64_t r = rotl(g_rng[1] * 5, 7) * 9, t = g_rng[1] << 17;
    g_rng[2] ^= g_rng[0]; g_rng[3] ^= g_rng[1]; g_rng[1] ^= g_rng[2]; g_rng[0] ^= g_rng[3]; g_rng[2] ^= t; g_rng[3] = rotl(g_rng[3], 45);
    return r;
}
static inline uint64_t xo_abaixo(uint64_t n) { return xo() % n; }
static inline double xo_unif(void) { return (xo() >> 11) * (1.0 / 9007199254740992.0); }

#define TAB_TETO ((size_t)24 << 20)                                  /* 24 M posições: 288 MB por ilha */
static void tabela_criar(size_t cap) {
    free(g_tk); free(g_tv);
    g_tk = (uint64_t *)calloc(cap, sizeof(uint64_t)); g_tv = (int32_t *)calloc(cap, sizeof(int32_t)); g_tcap = cap; g_tn = 0;
}
static size_t tabela_pos(uint64_t k) {
    size_t i = (size_t)(_mix(k) % g_tcap);
    while (g_tk[i] != 0 && g_tk[i] != k) i = (i + 1) % g_tcap;
    return i;
}
static int tabela_ler(uint64_t k, int32_t *v) { if (k == 0) k = 1; size_t i = tabela_pos(k); if (g_tk[i] == 0) return 0; *v = g_tv[i]; return 1; }
static void tabela_por(uint64_t k, int32_t v) {
    if (k == 0) k = 1;
    if ((g_tn + 1) * 10 > g_tcap * 7 && g_tcap * 3 / 2 + 1 > TAB_TETO) {   /* no teto: esquece as medidas guardadas (ela só poupa medir de novo) em vez de crescer */
        memset(g_tk, 0, g_tcap * sizeof(uint64_t)); g_tn = 0;
    } else if ((g_tn + 1) * 10 > g_tcap * 7) {
        uint64_t *ok = g_tk; int32_t *ov = g_tv; size_t oc = g_tcap;
        g_tk = (uint64_t *)calloc(oc * 3 / 2 + 1, sizeof(uint64_t)); g_tv = (int32_t *)calloc(oc * 3 / 2 + 1, sizeof(int32_t)); g_tcap = oc * 3 / 2 + 1; g_tn = 0;
        for (size_t j = 0; j < oc; j++) if (ok[j]) { size_t q = tabela_pos(ok[j]); g_tk[q] = ok[j]; g_tv[q] = ov[j]; g_tn++; }
        free(ok); free(ov);
    }
    size_t i = tabela_pos(k);
    if (g_tk[i] == 0) { g_tk[i] = k; g_tn++; }
    g_tv[i] = v;
}

static void canon(uint8_t f[PI_P][4]) {
    for (int i = 0; i < PI_P; i++) {
        int op = f[i][0] <= op_max() ? f[i][0] : 0, usa = op >= 1 && op <= op_max();
        f[i][0] = (uint8_t)op;
        if (!usa) { f[i][1] = 0; f[i][2] = 0; }
        if (op == 7) f[i][3] &= 7; else if (!((op >= 3 && op <= 6) || op >= 10)) f[i][3] = 0;
    }
}
static void para_bits(const uint8_t f[PI_P][4], uint8_t *bits) {
    for (int i = 0; i < PI_P; i++) for (int c = 0; c < 4; c++) for (int t = 0; t < 4; t++) bits[16 * i + 4 * c + t] = (uint8_t)((f[i][c] >> (3 - t)) & 1);
}
static void de_bits(const uint8_t *bits, uint8_t f[PI_P][4]) {
    for (int i = 0; i < PI_P; i++) for (int c = 0; c < 4; c++) { int v = 0; for (int t = 0; t < 4; t++) v = (v << 1) | bits[16 * i + 4 * c + t]; f[i][c] = (uint8_t)v; }
}

/* os campos ativos (instrução i, papel c) e os bits ativos (instrução, papel, bit 0 = o mais significativo) da forma canônica */
static int campos_ativos(const uint8_t f[PI_P][4], int *lista) {
    int n = 0;
    for (int i = 0; i < PI_P; i++) {
        int op = f[i][0];
        lista[n++] = 4 * i;
        if (op >= 1 && op <= op_max()) { lista[n++] = 4 * i + 1; lista[n++] = 4 * i + 2; }
        if ((op >= 3 && op <= 6) || op == 7 || op >= 10) lista[n++] = 4 * i + 3;
    }
    return n;
}
static int bits_ativos(const uint8_t f[PI_P][4], int *lista) {
    int n = 0;
    for (int i = 0; i < PI_P; i++) {
        int op = f[i][0];
        for (int t = 0; t < 4; t++) lista[n++] = (4 * i + 0) * 4 + t;
        if (op >= 1 && op <= op_max()) { for (int t = 0; t < 4; t++) lista[n++] = (4 * i + 1) * 4 + t; for (int t = 0; t < 4; t++) lista[n++] = (4 * i + 2) * 4 + t; }
        if ((op >= 3 && op <= 6) || op >= 10) for (int t = 0; t < 4; t++) lista[n++] = (4 * i + 3) * 4 + t;
        else if (op == 7) for (int t = 1; t < 4; t++) lista[n++] = (4 * i + 3) * 4 + t;   /* os 3 bits baixos de b */
    }
    return n;
}

/* (04/10, a linha independente: a mente do leito) a proteção de posições: a mutação só mexe nas instruções com g_masc[i] = 1. Com tudo 1 (o padrão), as listas são as mesmas
   e a ilha anda exatamente como antes. */
static uint8_t g_masc[PI_P]; static int g_masc_on = 0;
void ilha_mascara(const uint8_t *m) { if (!m) { g_masc_on = 0; return; } g_masc_on = 1; for (int i = 0; i < PI_P; i++) g_masc[i] = m[i] ? 1 : 0; }
static int filtrar(int *lista, int n, int por) { if (!g_masc_on) return n; int k = 0; for (int j = 0; j < n; j++) if (g_masc[lista[j] / por]) lista[k++] = lista[j]; return k; }
/* a mutação de `_mutar`: meio a meio, reescreve 1 ou 2 campos ativos ao acaso, ou vira 1 a 3 bits ativos; canônica; tem de diferir do pai (até 8 tentativas) */
static int mutar(const uint8_t pai[PI_P][4], uint8_t filho[PI_P][4]) {
    static int lista[PI_P * 16];
    for (int tent = 0; tent < 8; tent++) {
        memcpy(filho, pai, PI_P * 4);
        if (xo_unif() < 0.5) {                                    /* o operador de campos, como o do Python: até 8 tentativas por dentro antes de desistir */
            int n = filtrar(lista, campos_ativos(pai, lista), 4);
            if (n == 0) continue;
            for (int dentro = 0; dentro < 8; dentro++) {
                memcpy(filho, pai, PI_P * 4);
                int k = 1 + (int)(2.0 * xo_unif());
                if (k > n) k = n;
                for (int j = 0; j < k; j++) { int q = j + (int)xo_abaixo((uint64_t)(n - j)); int t = lista[j]; lista[j] = lista[q]; lista[q] = t; }
                for (int j = 0; j < k; j++) filho[lista[j] / 4][lista[j] % 4] = (uint8_t)xo_abaixo(16);
                canon(filho);
                if (memcmp(filho, pai, PI_P * 4) != 0) return 1;
            }
            continue;
        } else {
            int n = filtrar(lista, bits_ativos(pai, lista), 16), k = 1 + (int)xo_abaixo(3);
            if (n == 0) continue;
            if (k > n) k = n;
            for (int j = 0; j < k; j++) { int q = j + (int)xo_abaixo((uint64_t)(n - j)); int t = lista[j]; lista[j] = lista[q]; lista[q] = t; }
            for (int j = 0; j < k; j++) { int campo = lista[j] / 4, t = lista[j] % 4; filho[campo / 4][campo % 4] ^= (uint8_t)(1 << (3 - t)); }
        }
        canon(filho);
        if (memcmp(filho, pai, PI_P * 4) != 0) return 1;
    }
    return 0;
}

static uint8_t g_bits_tmp[PI_P * 16];
/* (04/10, a linha independente) a régua da BUSCA graduada: com g_grad ligado, a distância que a ilha usa para selecionar é a soma de peso[c] x min(max(v[c], 0), teto[c]),
   em vez do corte em 1 de D. Os recordes que o Python grava continuam com os valores verdadeiros (regua4_c1 chama julgar_c1, que não muda). Desligado: nada muda. */
static int g_grad = 0; static double g_grad_teto[15], g_grad_peso[15];
void regua_graduada(int ligar, const double *teto, const double *peso) { g_grad = ligar; for (int c = 0; c < 15; c++) { g_grad_teto[c] = teto ? teto[c] : 1.0; g_grad_peso[c] = peso ? peso[c] : 1.0; } }
/* uma medida de V; com `v`, os 15 valores; `conta` = 0 para as medidas repetidas do lexicase */
static int32_t medir_v(const uint8_t f[PI_P][4], uint64_t semente, int usar, float *v, int conta) {
    double val[15]; int32_t res[48], dist;
    para_bits(f, g_bits_tmp);
    if (julgar_c1(g_bits_tmp, PI_P, 3, g_teto_ilha, semente, usar, val, res, &dist) != 0) { if (v) for (int c = 0; c < 15; c++) v[c] = 1e9f; return 1 << 30; }
    if (conta) { g_medidas++; if (g_tag_med >= 0 && g_tag_med < 32) g_custo[g_tag_med]++; } else g_remedidas++;
    if (v) for (int c = 0; c < 15; c++) v[c] = (float)val[c];
    if (g_grad) { double t = 0.0; for (int c = 0; c < 15; c++) { double x = val[c] > 0.0 ? val[c] : 0.0; if (x > g_grad_teto[c]) x = g_grad_teto[c]; t += g_grad_peso[c] * x; } dist = (int32_t)rint(1000.0 * t); }
    return dist;
}
static int32_t medir(const uint8_t f[PI_P][4], uint64_t semente, int usar) { return medir_v(f, semente, usar, 0, 1); }
/* os 15 valores de um programa no nível de confirmação dele (por cláusula, a pior das sementes medidas), sem contar como medida */
static void valores_no_nivel(Indiv *I) {
    float w[15];
    medir_v(I->f, 0, 0, I->v, 0);
    for (int q = 1; q <= I->conf; q++) { medir_v(I->f, dev_semente(q), 1, w, 0); for (int c = 0; c < 15; c++) if (w[c] > I->v[c]) I->v[c] = w[c]; }
}
/* a média no desenvolvimento, em décimos (a soma das 10 distâncias): o número que decide o recorde e que a linha cheia do gráfico mostra */
/* (04/10, o recorde com margem) também o erro-padrão da média das 10 distâncias, em décimos (10 x desvio-padrão amostral / raiz de 10) */
static int32_t dev_media(const uint8_t f[PI_P][4], double *ep_dec) {
    int32_t soma = 0, ds[10];
    for (int j = 0; j < 10; j++) { int32_t d = medir(f, DEV[j], 1); if (d >= (1 << 30)) { if (ep_dec) *ep_dec = 0; return 1 << 30; } ds[j] = d; soma += d; }
    if (ep_dec) {
        double m = soma / 10.0, q = 0;
        for (int j = 0; j < 10; j++) q += (ds[j] - m) * (ds[j] - m);
        *ep_dec = 10.0 * sqrt(q / 9.0) / sqrt(10.0);
    }
    return soma;
}
static uint64_t chave_t(uint64_t ch) { return ch ^ (0xD1B54A32D192ED03ULL * (uint64_t)(g_epoca + 2)); }   /* a tabela das medidas vale por época do sal */

static uint64_t chave_de(const uint8_t f[PI_P][4]) { para_bits(f, g_bits_tmp); uint64_t k = semente_do_programa(g_bits_tmp, PI_P); return k ? k : 1; }

/* os recordes da época (só de confirmados) */
#define REC_MAX 4096
static long g_rec_n[REC_MAX], g_rec_ep[REC_MAX]; static int32_t g_rec_d[REC_MAX], g_rec_d3[REC_MAX]; static double g_rec_ep_dec[REC_MAX]; static uint8_t g_rec_bits[REC_MAX][PI_P * 16]; static int g_nrec = 0;
/* (régua 4) o candidato confirmado no nível 2 que passa da barra (a pior de três do recordista nesta época) é medido no desenvolvimento inteiro; vira recorde se a média
   melhorar. `g_melhor` está em décimos da média do desenvolvimento. */
static void talvez_recorde_(const Indiv *I);
static void talvez_recorde(const Indiv *I) { int tm = g_tag_med; g_tag_med = I->tag; talvez_recorde_(I); g_tag_med = tm; }
static void talvez_recorde_(const Indiv *I) {
    if (I->conf >= 2 && I->d < g_ref) {
        double epd;
        int32_t dm = dev_media(I->f, &epd);
        if ((double)dm + epd < (double)g_melhor) {                    /* (04/10, aprovado) só vira recorde quem melhora a média por mais que o erro-padrão dela */
            g_melhor = dm; g_melhor_ind = *I; g_ref = I->d;
            if (g_nrec < REC_MAX) { g_rec_n[g_nrec] = g_medidas; g_rec_d[g_nrec] = dm; g_rec_d3[g_nrec] = I->d; g_rec_ep[g_nrec] = g_epoca; g_rec_ep_dec[g_nrec] = epd; para_bits(I->f, g_rec_bits[g_nrec]); g_nrec++; }
        }
    }
}

/* (03/10, o Fable) a confirmação em dois níveis: o nível 1 (a semente do programa mais um) basta para o molde, que é frequente; o nível 2 (mais um, a semente mais dois:
   vale a pior das três) é o de recorde e de migrante, que são raros e decidem a história da corrida */
/* (04/10, a revisão: o aprendiz de encomendas) o crédito honesto e de graça: quando um indivíduo com ação marcada é confirmado pela primeira vez (venceu um torneio e foi medido
   numa vida nova do desenvolvimento; vale a pior das duas), o evento (ação, distância confirmada, distância do pai no nascimento) vai a um registro. Não muda nada na ilha. */
#define EV_CAP (1 << 16)
static int g_tag = -1; static int32_t g_dpai = 0;
static int g_ev_n = 0; static int16_t g_ev_tag[EV_CAP]; static int32_t g_ev_d[EV_CAP], g_ev_dpai[EV_CAP]; static uint64_t g_ev_chave[EV_CAP];
static long g_nasc[32];
static void subir_nivel_(Indiv *I);
static void subir_nivel(Indiv *I) { int tm = g_tag_med; g_tag_med = I->tag; subir_nivel_(I); g_tag_med = tm; }
static void subir_nivel_(Indiv *I) {
    float w[15];
    int32_t d2 = medir_v(I->f, dev_semente(I->conf + 1), 1, g_lexicase ? w : 0, 1);
    if (d2 > I->d) I->d = d2;
    if (g_lexicase) for (int c = 0; c < 15; c++) if (w[c] > I->v[c]) I->v[c] = w[c];
    I->conf++;
    if (I->conf == 1 && I->tag >= 0 && !I->logado) { if (g_ev_n < EV_CAP) { g_ev_tag[g_ev_n] = I->tag; g_ev_d[g_ev_n] = I->d; g_ev_dpai[g_ev_n] = I->dpai; g_ev_chave[g_ev_n] = I->chave; g_ev_n++; } I->logado = 1; }
    tabela_por(chave_t(I->chave), (int32_t)((uint32_t)I->d | ((uint32_t)I->conf << 30)));
}
static void confirmar_forte(Indiv *I) {
    while (I->conf < 2) subir_nivel(I);
    talvez_recorde(I);
}
static void confirmar(Indiv *I) {
    if (I->conf) return;
    subir_nivel(I);
    if (I->d < g_ref) confirmar_forte(I);                         /* candidato a recorde: a pior de três, e depois o desenvolvimento inteiro */
}

static void entrar(const Indiv *I) {
    if (g_npop < g_tam_pop) g_pop[g_npop++] = *I;
    else { g_pop[g_cab] = *I; g_cab = (g_cab + 1) % g_tam_pop; }
}

void ilha_iniciar(uint64_t semente, int tam_pop, int torneio, int teto) {
    _zobrist(); _funcoes_h();
    Sm s = {semente};
    for (int i = 0; i < 4; i++) g_rng[i] = sm_prox(&s);
    g_tam_pop = tam_pop < POP_MAX ? tam_pop : POP_MAX; g_torneio = torneio; g_teto_ilha = teto;
    g_npop = 0; g_cab = 0; g_medidas = 0; g_melhor = 1 << 30; g_nrec = 0; g_remedidas = 0; g_epoca = -1; g_ref = 1 << 30; g_sal = 0; g_ev_n = 0; g_tag = -1; g_tag_med = -1; for (int i = 0; i < 32; i++) { g_nasc[i] = 0; g_custo[i] = 0; }
    tabela_criar(1 << 16);
}

/* (04/10) o registro dos filhos para o aprendiz do leito: com a capacidade 0 (o padrão), nada é gravado e a ilha anda exatamente como antes (nenhum sorteio a mais) */
static int g_log_cap = 0, g_log_n = 0;
static uint8_t *g_log_pai = 0, *g_log_filho = 0;
static int32_t *g_log_dp = 0, *g_log_df = 0;
static int32_t g_ultimo_d = 0;
static int g_ultimo_v_ok = 0;
static float g_ultimo_vv[15];
static float *g_log_vp = 0, *g_log_vf = 0;                      /* os 15 valores do pai e do filho (-1: desconhecidos) */
static void registrar_filho(const uint8_t pai[PI_P][4], const float *vp, const uint8_t filho[PI_P][4], int32_t dp, int32_t df) {
    if (g_log_n >= g_log_cap) return;
    memcpy(g_log_pai + (size_t)g_log_n * PI_P * 4, pai, PI_P * 4); memcpy(g_log_filho + (size_t)g_log_n * PI_P * 4, filho, PI_P * 4);
    memcpy(g_log_vp + (size_t)g_log_n * 15, vp, 15 * sizeof(float));
    if (g_ultimo_v_ok) memcpy(g_log_vf + (size_t)g_log_n * 15, g_ultimo_vv, 15 * sizeof(float)); else for (int c = 0; c < 15; c++) g_log_vf[(size_t)g_log_n * 15 + c] = -1.0f;
    g_log_dp[g_log_n] = dp; g_log_df[g_log_n] = df; g_log_n++;
}

/* um indivíduo novo (sorteado, filho ou migrante) */
static void novo(uint8_t f[PI_P][4], int32_t d_conhecida, int conf_conhecido) {
    Indiv I;
    int fresco = 0;
    I.tag = (int16_t)g_tag; I.dpai = g_dpai; I.logado = 0;
    if (g_tag >= 0 && g_tag < 32) g_nasc[g_tag]++;
    memcpy(I.f, f, PI_P * 4);
    I.chave = chave_de(I.f);
    int32_t v;
    if (d_conhecida >= 0) {
        I.d = d_conhecida; I.conf = (uint8_t)conf_conhecido; tabela_por(chave_t(I.chave), (int32_t)((uint32_t)I.d | ((uint32_t)I.conf << 30)));
        if (g_lexicase) valores_no_nivel(&I);
    } else if (tabela_ler(chave_t(I.chave), &v)) {
        I.d = v & 0x3FFFFFFF; I.conf = (uint8_t)(((uint32_t)v) >> 30);
        if (g_lexicase) valores_no_nivel(&I);
    } else { g_tag_med = g_tag; I.d = medir_v(I.f, 0, 0, (g_lexicase || g_log_cap) ? I.v : 0, 1); g_tag_med = -1; I.conf = 0; tabela_por(chave_t(I.chave), I.d); fresco = 1; }
    if (!fresco && !g_lexicase) for (int c = 0; c < 15; c++) I.v[c] = -1.0f;      /* (04/10) os valores por cláusula de quem não foi medido agora: desconhecidos (a ilha de torneio nunca os lê) */
    g_ultimo_v_ok = fresco && g_log_cap;
    memcpy(g_ultimo_vv, I.v, sizeof(g_ultimo_vv));
    g_ultimo_d = I.d;
    entrar(&I);
    talvez_recorde(&I);                                           /* um migrante (confirmado no nível 2) melhor que o melhor da ilha vira recorde dela */
}

static int torneio_vencedor(void) {
    int idx[64], k = g_torneio < g_npop ? g_torneio : g_npop, n = 0;
    while (n < k) { int c = (int)xo_abaixo((uint64_t)g_npop), rep = 0; for (int j = 0; j < n; j++) if (idx[j] == c) rep = 1; if (!rep) idx[n++] = c; }
    int v = idx[0]; double dv = xo_unif();
    for (int j = 1; j < k; j++) { double dj = xo_unif(); if (g_pop[idx[j]].d < g_pop[v].d || (g_pop[idx[j]].d == g_pop[v].d && dj < dv)) { v = idx[j]; dv = dj; } }
    return v;
}

/* (03/10, o Fable: o lexicase como rota nova) o lexicase com tolerância (La Cava et al. 2016) sobre as 15 cláusulas: as cláusulas numa ordem sorteada; a cada uma, ficam os
   que estão a até uma tolerância do melhor dela (a tolerância é o desvio absoluto mediano da cláusula na população); no fim, um dos que sobraram, ao acaso */
static int cmp_f(const void *a, const void *b) { float x = *(const float *)a, y = *(const float *)b; return (x > y) - (x < y); }
static int lexicase_vencedor(void) {
    static int cand[POP_MAX], ordem[15];
    float eps[15], col[POP_MAX];
    for (int c = 0; c < 15; c++) {
        for (int i = 0; i < g_npop; i++) col[i] = g_pop[i].v[c];
        qsort(col, (size_t)g_npop, sizeof(float), cmp_f);
        float med = col[g_npop / 2];
        for (int i = 0; i < g_npop; i++) col[i] = fabsf(g_pop[i].v[c] - med);
        qsort(col, (size_t)g_npop, sizeof(float), cmp_f);
        eps[c] = col[g_npop / 2];
    }
    for (int c = 0; c < 15; c++) ordem[c] = c;
    for (int c = 14; c > 0; c--) { int j = (int)xo_abaixo((uint64_t)(c + 1)); int t = ordem[c]; ordem[c] = ordem[j]; ordem[j] = t; }
    int n = g_npop;
    for (int i = 0; i < n; i++) cand[i] = i;
    for (int q = 0; q < 15 && n > 1; q++) {
        int c = ordem[q];
        float m = g_pop[cand[0]].v[c];
        for (int i = 1; i < n; i++) if (g_pop[cand[i]].v[c] < m) m = g_pop[cand[i]].v[c];
        int k = 0;
        for (int i = 0; i < n; i++) if (g_pop[cand[i]].v[c] <= m + eps[c]) cand[k++] = cand[i];
        n = k;
    }
    return cand[xo_abaixo((uint64_t)n)];
}

/* (régua 4) a troca do sal: a época nova, a população medida de novo com o sal novo (a confirmação recomeça), e a barra do recorde: a pior de três do recordista nesta época */
static void trocar_sal(void) {
    g_epoca = g_medidas / SAL_P;
    g_sal = (uint64_t)g_epoca;
    for (int i = 0; i < g_npop; i++) {
        Indiv *I = &g_pop[i];
        I->d = medir_v(I->f, 0, 0, (g_lexicase || g_log_cap) ? I->v : 0, 1); I->conf = 0;
        tabela_por(chave_t(I->chave), I->d);
    }
    if (g_melhor < (1 << 30)) {
        Indiv R = g_melhor_ind; R.tag = -1;
        R.d = medir(R.f, 0, 0); R.conf = 0;
        while (R.conf < 2) subir_nivel(&R);
        g_ref = R.d;
    } else g_ref = 1 << 30;
}

/* anda até `alvo` medidas (ou até cumprir D); devolve quantos recordes a época teve (lidos por ilha_recorde) */
int ilha_andar(long alvo) {
    g_nrec = 0;
    static uint8_t f[PI_P][4];
    if (g_epoca < 0) { g_epoca = g_medidas / SAL_P; g_sal = (uint64_t)g_epoca; }
    while (g_npop < g_tam_pop) {                                  /* a população de partida, sorteada e canônica */
        for (int i = 0; i < PI_P; i++) for (int c = 0; c < 4; c++) f[i][c] = (uint8_t)xo_abaixo(16);
        canon(f);
        novo(f, -1, 0);
    }
    while (g_medidas < alvo && g_melhor != 0) {
        int v;
        if (g_medidas / SAL_P != g_epoca) trocar_sal();
        for (;;) { v = g_lexicase ? lexicase_vencedor() : torneio_vencedor(); if (g_pop[v].conf) break; confirmar(&g_pop[v]); }
        if (!mutar(g_pop[v].f, f)) continue;
        if (g_log_cap) {
            static uint8_t pai[PI_P][4]; static float vp[15]; int32_t dp = g_pop[v].d;
            memcpy(pai, g_pop[v].f, PI_P * 4); memcpy(vp, g_pop[v].v, sizeof(vp));
            g_tag = 31; g_dpai = dp; novo(f, -1, 0); g_tag = -1;
            registrar_filho(pai, vp, f, dp, g_ultimo_d);
        } else { g_tag = 31; g_dpai = g_pop[v].d; novo(f, -1, 0); g_tag = -1; }
    }
    return g_nrec;
}

long ilha_n(void) { return g_medidas; }
int32_t ilha_melhor(uint8_t *bits) { if (g_melhor < (1 << 30)) para_bits(g_melhor_ind.f, bits); return g_melhor; }
void ilha_recorde(int i, long *n, int32_t *d, uint8_t *bits) { *n = g_rec_n[i]; *d = g_rec_d[i]; memcpy(bits, g_rec_bits[i], PI_P * 16); }
int ilha_tamanho(void) { return g_npop; }
void ilha_indiv(int i, uint8_t *bits, int32_t *d, int32_t *conf) { para_bits(g_pop[i].f, bits); *d = g_pop[i].d; *conf = g_pop[i].conf; }
void ilha_inserir(const uint8_t *bits, int32_t d, int32_t conf) { static uint8_t ff[PI_P][4]; de_bits(bits, ff); canon(ff); novo(ff, d, conf); }
void ilha_confirmar_todos(int k) { for (int i = 0; i < g_npop && i < k; i++) confirmar(&g_pop[i]); }
void ilha_estado(uint64_t *rng, long *n, int32_t *melhor, int32_t *cab) { for (int i = 0; i < 4; i++) rng[i] = g_rng[i]; *n = g_medidas; *melhor = g_melhor; *cab = g_cab; }
void ilha_restaurar(const uint64_t *rng, long n, int32_t melhor, const uint8_t *melhor_bits, int32_t cab) {
    for (int i = 0; i < 4; i++) g_rng[i] = rng[i];
    g_medidas = n; g_melhor = melhor; g_cab = cab;
    g_epoca = g_medidas / SAL_P - 1;                              /* a retomada troca o sal logo na primeira volta: a população herdada é medida de novo */
    if (melhor < (1 << 30)) { de_bits(melhor_bits, g_melhor_ind.f); g_melhor_ind.d = melhor; g_melhor_ind.conf = 2; g_melhor_ind.chave = chave_de(g_melhor_ind.f); g_melhor_ind.tag = -1; g_melhor_ind.logado = 1; }
}
/* (03/10) a régua nova na retomada: o melhor herdado medido no desenvolvimento inteiro; devolve a média em décimos, que passa a ser o melhor da ilha */
int32_t ilha_recalibrar(void) {
    if (g_melhor >= (1 << 30)) return g_melhor;
    g_melhor_ind.chave = chave_de(g_melhor_ind.f);
    g_melhor = dev_media(g_melhor_ind.f, 0);
    return g_melhor;
}
void ilha_recorde_mais(int i, long *epoca, int32_t *d3, double *ep_dec) { *epoca = g_rec_ep[i]; *d3 = g_rec_d3[i]; *ep_dec = g_rec_ep_dec[i]; }
long ilha_epoca(void) { return g_epoca; }
void ilha_selecao(int lexicase) { g_lexicase = lexicase ? 1 : 0; }
long ilha_remedidas(void) { return g_remedidas; }
void ilha_confirmar_forte(int i) { if (i >= 0 && i < g_npop) confirmar_forte(&g_pop[i]); }
void ilha_esvaziar(void) { g_npop = 0; g_cab = 0; }
void ilha_confirmar(int i) { if (i >= 0 && i < g_npop) confirmar(&g_pop[i]); }
void ilha_sortear(int k) { static uint8_t f[PI_P][4]; for (int j = 0; j < k; j++) { for (int i = 0; i < PI_P; i++) for (int c = 0; c < 4; c++) f[i][c] = (uint8_t)xo_abaixo(16); canon(f); novo(f, -1, 0); } }
int ilha_cabeca(void) { return g_cab; }

/* ======================================================================= (04/10/2026) o que o aprendiz do leito usa (o teste decidido: relançar uma corrida igual com o aprendiz e
   ver se a descida é mais rápida). Nada disto é chamado pela ilha sozinha: com o registro desligado, a s17 de antes e a ilha de agora andam igual (conferido em testes/test_leito_aprendiz.py). */
void ilha_registro(int cap) {
    free(g_log_pai); free(g_log_filho); free(g_log_dp); free(g_log_df); free(g_log_vp); free(g_log_vf);
    g_log_cap = cap > 0 ? cap : 0; g_log_n = 0;
    g_log_pai = g_log_cap ? (uint8_t *)malloc((size_t)g_log_cap * PI_P * 4) : 0; g_log_filho = g_log_cap ? (uint8_t *)malloc((size_t)g_log_cap * PI_P * 4) : 0;
    g_log_dp = g_log_cap ? (int32_t *)malloc(sizeof(int32_t) * g_log_cap) : 0; g_log_df = g_log_cap ? (int32_t *)malloc(sizeof(int32_t) * g_log_cap) : 0;
    g_log_vp = g_log_cap ? (float *)malloc(sizeof(float) * 15 * g_log_cap) : 0; g_log_vf = g_log_cap ? (float *)malloc(sizeof(float) * 15 * g_log_cap) : 0;
}
int ilha_registro_n(void) { return g_log_n; }
/* copia os filhos registrados (campos: n x PI_P x 4) e esvazia o registro */
void ilha_registro_ler(uint8_t *pais, uint8_t *filhos, int32_t *dp, int32_t *df, float *vp, float *vf) {
    memcpy(pais, g_log_pai, (size_t)g_log_n * PI_P * 4); memcpy(filhos, g_log_filho, (size_t)g_log_n * PI_P * 4);
    memcpy(vp, g_log_vp, sizeof(float) * 15 * g_log_n); memcpy(vf, g_log_vf, sizeof(float) * 15 * g_log_n);
    memcpy(dp, g_log_dp, sizeof(int32_t) * g_log_n); memcpy(df, g_log_df, sizeof(int32_t) * g_log_n);
    g_log_n = 0;
}
/* um pai como a ilha escolhe (o torneio ou o lexicase, confirmado antes de servir): o índice na população */
int ilha_pai(void) {
    int v;
    if (g_epoca < 0) { g_epoca = g_medidas / SAL_P; g_sal = (uint64_t)g_epoca; }
    if (g_medidas / SAL_P != g_epoca) trocar_sal();
    for (;;) { v = g_lexicase ? lexicase_vencedor() : torneio_vencedor(); if (g_pop[v].conf) break; confirmar(&g_pop[v]); }
    return v;
}
void ilha_campos(int i, uint8_t *campos, int32_t *d, float *v) { memcpy(campos, g_pop[i].f, PI_P * 4); *d = g_pop[i].d; memcpy(v, g_pop[i].v, sizeof(float) * 15); }
/* `k` filhos candidatos do indivíduo i pela MESMA mutação da ilha (o sorteador da ilha); devolve quantos saíram */
int ilha_candidatos(int i, int k, uint8_t *saida) {
    static uint8_t pai[PI_P][4], f[PI_P][4];
    memcpy(pai, g_pop[i].f, PI_P * 4);
    int n = 0;
    for (int j = 0; j < k; j++) { if (!mutar(pai, f)) continue; memcpy(saida + (size_t)n * PI_P * 4, f, PI_P * 4); n++; }
    return n;
}
/* o filho escolhido entra como os da ilha (medido, ou lido da tabela; o mais velho sai; pode virar recorde): devolve a distância dele */
int32_t ilha_inserir_campos(const uint8_t *campos, float *v) { static uint8_t f[PI_P][4]; memcpy(f, campos, PI_P * 4); canon(f); novo(f, -1, 0);
    if (g_ultimo_v_ok) memcpy(v, g_ultimo_vv, sizeof(float) * 15); else for (int c = 0; c < 15; c++) v[c] = -1.0f;
    return g_ultimo_d; }
/* a MESMA mutação da ilha sobre campos quaisquer (uma composição do aprendiz): 1 se saiu um filho legal e diferente */
int ilha_mutar_campos(const uint8_t *pai, uint8_t *filho) { static uint8_t a[PI_P][4], b[PI_P][4]; memcpy(a, pai, PI_P * 4); int ok = mutar(a, b); memcpy(filho, b, PI_P * 4); return ok; }
/* a forma canônica de campos quaisquer */
void ilha_canon(uint8_t *campos) { static uint8_t a[PI_P][4]; memcpy(a, campos, PI_P * 4); canon(a); memcpy(campos, a, PI_P * 4); }
int ilha_nrec(void) { return g_nrec; }
void ilha_recordes_zerar(void) { g_nrec = 0; }

/* (04/10, a revisão) o aprendiz de encomendas: marcar a ação do próximo indivíduo, ler os eventos de confirmação e os nascimentos por ação (31 = a mutação da própria ilha) */
void ilha_tag(int tag, int32_t dpai) { g_tag = tag; g_dpai = dpai; }
int ilha_eventos_n(void) { return g_ev_n; }
void ilha_eventos_ler(int32_t *tag, int32_t *d, int32_t *dpai) { for (int i = 0; i < g_ev_n; i++) { tag[i] = g_ev_tag[i]; d[i] = g_ev_d[i]; dpai[i] = g_ev_dpai[i]; } g_ev_n = 0; }
void ilha_nasc(int64_t *out) { for (int i = 0; i < 32; i++) out[i] = g_nasc[i]; }
void ilha_custo(int64_t *out) { for (int i = 0; i < 32; i++) out[i] = g_custo[i]; }
/* (a biblioteca de receitas) os mesmos eventos com a chave do indivíduo confirmado (o hash dos bits canônicos) */
void ilha_eventos_ler2(int32_t *tag, int32_t *d, int32_t *dpai, uint64_t *chave) { for (int i = 0; i < g_ev_n; i++) { tag[i] = g_ev_tag[i]; d[i] = g_ev_d[i]; dpai[i] = g_ev_dpai[i]; chave[i] = g_ev_chave[i]; } g_ev_n = 0; }
