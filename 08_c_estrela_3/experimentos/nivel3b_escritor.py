# -*- coding: utf-8 -*-
import glob
import json
import math
import os
import zipfile
import numpy as np
from experimentos import nivel3b_aprendiz as A
from experimentos import nivel3b_bits as B
from experimentos import nivel3b_fotos as F
from experimentos import nivel3b_meta as M
TROCA, MOVER = (0, 1)
NOMES_DE_TIPO = ('troca_de_bits', 'move_bloco')
JANELA = 8
PROBES = 128
KMAX = 20
GRUPOS = {'global': (0, 8), 'tipo': (8, 10), 'janela': (10, 15), 'unidades_antigas': (15, 21), 'unidades_novas': (21, 27), 'contexto': (27, 36), 'relacao': (36, 45), 'movimento': (45, 48), 'bits_antigos': (48, 68), 'bits_novos': (68, 88), 'fios_antigos': (88, 120), 'fios_novos': (120, 152), 'comportamento_do_pai': (152, 280)}
N_BASE = 48
N_ENTRADA = N_BASE + 2 * KMAX + 64 + PROBES
FRACAO_CEGA = A.FRACAO_CEGA

def tamanhos_de_janela(n):
    w = B.largura(n)
    U = 2 * w
    return sorted({k for k in (1, 2, 3, w, w + 2, U, U + w, 2 * U) if 1 <= k <= min(KMAX, 2 * U)})

class Estado:

    def __init__(self, n, pref, S, f_S, fd_S, vetores, passo=0, comportamento=0):
        self.n = int(n)
        self.w = B.largura(n)
        self.U = 2 * self.w
        self.S = np.asarray(S, np.int64).reshape(-1, 2)
        self.m = len(self.S)
        m = self.m
        self.I, self.J = (self.S[:, 0], self.S[:, 1])
        self.val = self.I << self.w | self.J
        nv, prof = A.niveis(n, pref, [tuple(c) for c in self.S])
        self.nv = np.asarray(nv, float)
        self.prof = float(max(prof, 1))
        self.prev = np.full((m, n), -1, np.int64)
        self.nxt = np.full((m, n), m, np.int64)
        ultimo = np.full(n, -1, np.int64)
        for t in range(m):
            self.prev[t] = ultimo
            ultimo[self.I[t]] = t
            ultimo[self.J[t]] = t
        proximo = np.full(n, m, np.int64)
        for t in range(m - 1, -1, -1):
            self.nxt[t] = proximo
            proximo[self.I[t]] = t
            proximo[self.J[t]] = t
        fd = np.asarray(fd_S, float)
        self.imp = np.maximum(fd - float(f_S), 0.0)
        self.imp_rel = self.imp / max(vetores, 1)
        self.imp_log = np.log1p(self.imp) / 8.0
        self.rank = np.argsort(np.argsort(self.imp, kind='stable'), kind='stable') / max(m - 1, 1)
        idx = np.arange(m)
        self.ultimo_i = (self.nxt[idx, self.I] == m).astype(float)
        self.ultimo_j = (self.nxt[idx, self.J] == m).astype(float)
        self.primeiro_i = (self.prev[idx, self.I] == -1).astype(float)
        self.primeiro_j = (self.prev[idx, self.J] == -1).astype(float)
        self.cnt = np.zeros((n, n), np.int64)
        np.add.at(self.cnt, (self.I, self.J), 1)
        self.f = float(f_S)
        self.comportamento = int(comportamento)
        self.bits = B.codificar(n, [tuple(c) for c in self.S])
        self.g_glob = np.array([n / 32.0, m / 100.0, len(pref) / 100.0, math.log1p(f_S) / 8.0, f_S / max(vetores, 1), math.log10(max(vetores, 1)) / 5.0, passo / 4.0, 1.0 if f_S == 0 else 0.0], np.float32)
        self.phi = np.array([self.comportamento >> p & 1 for p in range(PROBES)], np.float32)

class Pool:

    def __init__(self, tipo, p, k, seq, q2, u0, nu, ni, nj, valido, origem=None):
        self.tipo, self.p, self.k, self.seq, self.q2, self.u0, self.nu = (np.asarray(x, np.int64) for x in (tipo, p, k, seq, q2, u0, nu))
        self.ni, self.nj = (np.asarray(ni, np.int64).reshape(-1, 3), np.asarray(nj, np.int64).reshape(-1, 3))
        self.valido = np.asarray(valido, bool)
        self.origem = np.zeros(len(self.tipo), np.int8) if origem is None else np.asarray(origem, np.int8)

    @property
    def K(self):
        return len(self.tipo)

    def uma(self, i):
        return (int(self.tipo[i]), int(self.p[i]), int(self.k[i]), int(self.seq[i]), int(self.q2[i]))

    def filtrar(self, mascara):
        m = np.asarray(mascara, bool)
        return Pool(self.tipo[m], self.p[m], self.k[m], self.seq[m], self.q2[m], self.u0[m], self.nu[m], self.ni[m], self.nj[m], self.valido[m], self.origem[m])

    @staticmethod
    def vazio():
        return Pool([], [], [], [], [], [], [], np.zeros((0, 3)), np.zeros((0, 3)), [])

    @staticmethod
    def juntar(pools):
        pools = [p for p in pools if p.K]
        if not pools:
            return Pool.vazio()
        return Pool(*(np.concatenate([getattr(p, c) for p in pools]) for c in ('tipo', 'p', 'k', 'seq', 'q2', 'u0', 'nu')), np.concatenate([p.ni for p in pools]), np.concatenate([p.nj for p in pools]), np.concatenate([p.valido for p in pools]), np.concatenate([p.origem for p in pools]))

def _decodificar_trechos(est, p, k, seq):
    n, w, U, m = (est.n, est.w, est.U, est.m)
    FULL = (1 << U) - 1
    pad = np.concatenate([est.val, np.zeros(3, np.int64)])
    u0 = p // U
    o = p % U
    ul = (p + k - 1) // U
    nu = ul - u0 + 1
    seg = pad[np.minimum(u0, m + 2)] << 2 * U | pad[np.minimum(u0 + 1, m + 2)] << U | pad[np.minimum(u0 + 2, m + 2)]
    shift = 3 * U - o - k
    mascara = (np.int64(1) << k) - 1 << shift
    novo = seg & ~mascara | seq << shift
    v = np.stack([novo >> 2 * U & FULL, novo >> U & FULL, novo & FULL], 1)
    afetada = np.arange(3)[None, :] < nu[:, None]
    i = v >> w
    j = v & (1 << w) - 1
    ok_unidade = (i != j) & (i < n) & (j < n)
    lo, hi = (np.minimum(i, j), np.maximum(i, j))
    pos = np.minimum(u0[:, None] + np.arange(3)[None, :], m - 1)
    antigo_i, antigo_j = (est.I[pos], est.J[pos])
    mudou = (afetada & ((lo != antigo_i) | (hi != antigo_j))).any(1)
    valido = (ul < m) & (~afetada | ok_unidade).all(1) & mudou
    lo = np.where(afetada, lo, -1)
    hi = np.where(afetada, hi, -1)
    return (u0, nu, lo, hi, valido)

def amostrar_cego(est, M_, mix, g, janela=JANELA):
    n, m, U = (est.n, est.m, est.U)
    if m < 2:
        return Pool.vazio()
    w = np.asarray(mix, float)
    w = np.array([w[0] + w[1], w[2] + w[3]])
    w = w / w.sum()
    cont = g.multinomial(int(M_), w)
    pools = []
    k1 = int(cont[0])
    if k1:
        ks = np.asarray(tamanhos_de_janela(n))
        k = ks[g.integers(0, len(ks), k1)]
        L = U * m
        p = (g.random(k1) * (L - k + 1)).astype(np.int64)
        seq = (g.random(k1) * (np.int64(1) << k)).astype(np.int64)
        u0, nu, lo, hi, valido = _decodificar_trechos(est, p, k, seq)
        pools.append(Pool(np.full(k1, TROCA), p, k, seq, np.zeros(k1, np.int64), u0, nu, lo, hi, valido))
    k2 = int(cont[1])
    if k2:
        I, J = (est.I, est.J)
        q = g.integers(0, m, k2)
        passo = g.integers(1, janela + 1, k2) * (2 * g.integers(0, 2, k2) - 1)
        longe = g.random(k2) < 0.2
        q2 = np.where(longe, g.integers(0, m, k2), np.clip(q + passo, 0, m - 1))
        ok = q2 != q
        frente = q2 > q
        prox = np.minimum(est.nxt[q, I[q]], est.nxt[q, J[q]])
        ant = np.maximum(est.prev[q, I[q]], est.prev[q, J[q]])
        ok &= np.where(frente, prox <= q2, ant >= q2)
        z = np.zeros(k2, np.int64)
        neg = -np.ones(k2, np.int64)
        pools.append(Pool(np.full(k2, MOVER), q, np.full(k2, U), z, q2, q, np.ones(k2, np.int64), np.stack([I[q], neg, neg], 1), np.stack([J[q], neg, neg], 1), ok))
    P = Pool.juntar(pools)
    return P.filtrar(P.valido)

def aplicar(S, n, tipo, p, k, seq, q2):
    L = [tuple(c) for c in S]
    if tipo == MOVER:
        u = L.pop(p)
        L.insert(q2, u)
        return L
    w = B.largura(n)
    U = 2 * w
    m = len(L)
    u0 = p // U
    ul = (p + k - 1) // U
    if ul >= m:
        return None
    seg = 0
    for t in range(u0, ul + 1):
        seg = seg << U | (L[t][0] << w | L[t][1])
    largura = (ul - u0 + 1) * U
    shift = largura - (p - u0 * U) - k
    mascara = (1 << k) - 1 << shift
    seg = seg & ~mascara | seq << shift
    novos = []
    for t in range(ul - u0, -1, -1):
        v = seg >> t * U & (1 << U) - 1
        i, j = (v >> w, v & (1 << w) - 1)
        if i == j or i >= n or j >= n:
            return None
        novos.append((min(i, j), max(i, j)))
    if novos == L[u0:ul + 1]:
        return None
    L[u0:ul + 1] = novos
    return L

def caracteristicas(est, pool):
    K = pool.K
    n, m, w, U = (est.n, est.m, est.w, est.U)
    if K == 0:
        return np.zeros((0, N_ENTRADA), np.float32)
    tipo, p, k, seq, q2, u0, nu = (pool.tipo, pool.p, pool.k, pool.seq, pool.q2, pool.u0, pool.nu)
    ehm = (tipo == MOVER).astype(np.float64)
    ehp = 1.0 - ehm
    u = np.minimum(u0, m - 1)
    Iq, Jq = (est.I[u], est.J[u])
    G = np.tile(est.g_glob, (K, 1)).astype(np.float64)
    TIPO = np.stack([ehp, ehm], 1)
    o = np.where(tipo == TROCA, p % U, 0)
    JAN = np.stack([k / (2.0 * U), o / U, ((o == 0) & (tipo == TROCA)).astype(float), ((o == w) & (tipo == TROCA)).astype(float), nu / 3.0], 1)
    pos3 = np.minimum(u[:, None] + np.arange(3)[None, :], m - 1)
    afet = (np.arange(3)[None, :] < nu[:, None]).astype(float)
    ANT = np.stack([est.I[pos3] / n * afet, est.J[pos3] / n * afet], 2).reshape(K, 6)
    ni, nj = (np.where(pool.ni >= 0, pool.ni, 0), np.where(pool.nj >= 0, pool.nj, 0))
    NOV = np.stack([ni / n * (pool.ni >= 0) * ehp[:, None], nj / n * (pool.nj >= 0) * ehp[:, None]], 2).reshape(K, 6)
    CTX = np.stack([u / m, est.nv[u] / est.prof, est.imp_rel[u], est.imp_log[u], est.rank[u], est.ultimo_i[u], est.ultimo_j[u], est.primeiro_i[u], est.primeiro_j[u]], 1)
    a0, b0 = (ni[:, 0], nj[:, 0])
    comum = ((a0 == Iq) | (a0 == Jq)).astype(float) + ((b0 == Iq) | (b0 == Jq)).astype(float)
    gpa = np.where(est.prev[u, a0] < 0, u + 1, u - est.prev[u, a0]) / m
    gna = np.where(est.nxt[u, a0] >= m, m - u, est.nxt[u, a0] - u) / m
    gpb = np.where(est.prev[u, b0] < 0, u + 1, u - est.prev[u, b0]) / m
    gnb = np.where(est.nxt[u, b0] >= m, m - u, est.nxt[u, b0] - u) / m
    REL = np.stack([comum / 2.0, np.abs(a0 - Iq) / n, np.abs(b0 - Jq) / n, np.minimum(est.cnt[a0, b0], 3) / 3.0, (est.cnt[n - 1 - b0, n - 1 - a0] > 0).astype(float), gpa, gna, gpb, gnb], 1) * ehp[:, None]
    frente = q2 > p
    prox_toque = np.minimum(est.nxt[u, Iq], est.nxt[u, Jq])
    ant_toque = np.maximum(est.prev[u, Iq], est.prev[u, Jq])
    ate = np.where(frente, prox_toque - u, u - ant_toque) / m
    MOV = np.stack([(q2 - p) / m, ate, (np.abs(q2 - p) > JANELA).astype(float)], 1) * ehm[:, None]
    posb = np.arange(KMAX)[None, :]
    dentro = (posb < k[:, None]) & (tipo == TROCA)[:, None]
    ix = np.minimum(p[:, None] + posb, len(est.bits) - 1)
    BANT = est.bits[ix].astype(np.float64) * dentro
    BNOV = ((seq[:, None] >> np.maximum(k[:, None] - 1 - posb, 0) & 1) * dentro).astype(np.float64)
    FA = np.zeros((K, 32))
    FN = np.zeros((K, 32))
    ar = np.arange(K)
    for t in range(3):
        a_ = afet[:, t] > 0
        FA[ar[a_], est.I[pos3[a_, t]]] = 1.0
        FA[ar[a_], est.J[pos3[a_, t]]] = 1.0
        b_ = a_ & (pool.ni[:, t] >= 0) & (tipo == TROCA)
        FN[ar[b_], pool.ni[b_, t]] = 1.0
        FN[ar[b_], pool.nj[b_, t]] = 1.0
    PHI = np.tile(est.phi, (K, 1)).astype(np.float64)
    X = np.concatenate([G, TIPO, JAN, ANT, NOV, CTX, REL, MOV, BANT, BNOV, FA, FN, PHI], 1)
    assert X.shape[1] == N_ENTRADA, X.shape
    return X.astype(np.float32)

class RedeDupla:

    def __init__(self, entrada=N_ENTRADA, escondidas=(128, 64), saidas=PROBES, semente=0, lr=0.003, l2=0.0, peso_c=0.5):
        g = np.random.default_rng(semente)
        self.esc = tuple((int(x) for x in escondidas))
        self.entrada, self.saidas, self.lr, self.l2, self.peso_c = (int(entrada), int(saidas), float(lr), float(l2), float(peso_c))
        dims = [self.entrada, *self.esc]
        self.W = [g.normal(0, 1.0 / math.sqrt(dims[i]), (dims[i], dims[i + 1])).astype(np.float32) for i in range(len(dims) - 1)]
        self.b = [np.zeros(dims[i + 1], np.float32) for i in range(len(dims) - 1)]
        self.Wf = g.normal(0, 1.0 / math.sqrt(dims[-1]), (dims[-1], 1)).astype(np.float32)
        self.bf = np.zeros(1, np.float32)
        self.Wc = g.normal(0, 0.1 / math.sqrt(dims[-1]), (dims[-1], self.saidas)).astype(np.float32)
        self.bc = np.full(self.saidas, -2.0, np.float32)
        self._zerar_adam()

    def _params(self):
        return self.W + self.b + [self.Wf, self.bf, self.Wc, self.bc]

    def _zerar_adam(self):
        self._m = [np.zeros_like(p) for p in self._params()]
        self._v = [np.zeros_like(p) for p in self._params()]
        self._t = 0

    def _fwd(self, X):
        hs = [np.asarray(X, np.float32)]
        for W, b in zip(self.W, self.b):
            hs.append(np.tanh(hs[-1] @ W + b))
        f = (hs[-1] @ self.Wf + self.bf)[:, 0]
        z = hs[-1] @ self.Wc + self.bc
        return (hs, f, z)

    def _pai(self, X):
        return np.asarray(X, np.float32)[:, self.entrada - self.saidas:]

    def prever_troca(self, X):
        _, _, z = self._fwd(X)
        return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))

    def prever(self, X):
        _, f, z = self._fwd(X)
        q = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        a = self._pai(X)
        return (f, a + (1.0 - 2.0 * a) * q)

    def passo(self, X, yf, Y, w, lr=None):
        lr = self.lr if lr is None else lr
        hs, f, z = self._fwd(X)
        w = np.asarray(w, np.float32)
        sw = max(float(w.sum()), 1e-09)
        q = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        troca = np.abs(np.asarray(Y, np.float32) - self._pai(X))
        ef = (f - yf) * w / sw
        gf = (2.0 * ef)[:, None]
        gz = (q - troca) * w[:, None] / sw * (self.peso_c / self.saidas)
        gh = gf @ self.Wf.T + gz @ self.Wc.T
        gWf, gbf = (hs[-1].T @ gf, gf.sum(0))
        gWc, gbc = (hs[-1].T @ gz, gz.sum(0))
        gW, gb = ([None] * len(self.W), [None] * len(self.b))
        for k in range(len(self.W) - 1, -1, -1):
            gh = gh * (1 - hs[k + 1] ** 2)
            gW[k] = hs[k].T @ gh
            gb[k] = gh.sum(0)
            gh = gh @ self.W[k].T
        grads = gW + gb + [gWf, gbf, gWc, gbc]
        self._t += 1
        for i, (par, gr) in enumerate(zip(self._params(), grads)):
            self._m[i] = 0.9 * self._m[i] + 0.1 * gr
            self._v[i] = 0.999 * self._v[i] + 0.001 * gr ** 2
            mh = self._m[i] / (1 - 0.9 ** self._t)
            vh = self._v[i] / (1 - 0.999 ** self._t)
            par -= (lr * mh / (np.sqrt(vh) + 1e-08)).astype(np.float32)
            if self.l2 and i < len(self.W):
                par -= (lr * self.l2 * par).astype(np.float32)
        eps = 1e-07
        bce = -(troca * np.log(q + eps) + (1 - troca) * np.log(1 - q + eps)).mean(1)
        return (float(((f - yf) ** 2 * w).sum() / sw), float((bce * w).sum() / sw))

    def copiar(self):
        r = RedeDupla(self.entrada, self.esc, self.saidas, 0, self.lr, self.l2, self.peso_c)
        r.W, r.b = ([x.copy() for x in self.W], [x.copy() for x in self.b])
        r.Wf, r.bf, r.Wc, r.bc = (self.Wf.copy(), self.bf.copy(), self.Wc.copy(), self.bc.copy())
        r._zerar_adam()
        return r

    def alargar(self, extra, g):
        k = len(self.W) - 1
        self.W[k] = np.concatenate([self.W[k], g.normal(0, 0.1, (self.W[k].shape[0], extra)).astype(np.float32)], axis=1)
        self.b[k] = np.concatenate([self.b[k], np.zeros(extra, np.float32)])
        self.Wf = np.concatenate([self.Wf, np.zeros((extra, 1), np.float32)], axis=0)
        self.Wc = np.concatenate([self.Wc, np.zeros((extra, self.saidas), np.float32)], axis=0)
        self.esc = self.esc[:-1] + (self.esc[-1] + int(extra),)
        self._zerar_adam()

    def estado(self):
        return {'esc': list(self.esc), 'entrada': self.entrada, 'saidas': self.saidas, 'lr': self.lr, 'l2': self.l2, 'peso_c': self.peso_c, 'W': [x.tolist() for x in self.W], 'b': [x.tolist() for x in self.b], 'Wf': self.Wf.tolist(), 'bf': self.bf.tolist(), 'Wc': self.Wc.tolist(), 'bc': self.bc.tolist()}

    @classmethod
    def de_estado(cls, e):
        r = cls(e['entrada'], e['esc'], e['saidas'], 0, e.get('lr', 0.003), e.get('l2', 0.0), e.get('peso_c', 0.5))
        r.W, r.b = ([np.asarray(x, np.float32) for x in e['W']], [np.asarray(x, np.float32) for x in e['b']])
        r.Wf, r.bf, r.Wc, r.bc = (np.asarray(e[k], np.float32) for k in ('Wf', 'bf', 'Wc', 'bc'))
        r._zerar_adam()
        return r

def bits_dos_comportamentos(lo, hi, P=PROBES):
    lo, hi = (np.asarray(lo, np.uint64), np.asarray(hi, np.uint64))
    sh = np.arange(64, dtype=np.uint64)
    a = (lo[:, None] >> sh[None, :] & np.uint64(1)).astype(np.float32)
    b = (hi[:, None] >> sh[None, :] & np.uint64(1)).astype(np.float32)
    return np.concatenate([a, b], 1)[:, :P]

def dividir(v):
    v = int(v)
    return (v & F.MASCARA64, v >> 64 & F.MASCARA64)

class MemoriaEscritor:

    def __init__(self, teto=150000, semente=0):
        self.teto = int(teto)
        self.g = np.random.default_rng(semente + 303)
        self._cap = 4096
        self._X = np.zeros((self._cap, N_ENTRADA), np.float16)
        self._y = np.zeros(self._cap, np.float32)
        self._lo = np.zeros(self._cap, np.uint64)
        self._hi = np.zeros(self._cap, np.uint64)
        self._foto = np.full(self._cap, -1, np.int64)
        self._ed = np.zeros((self._cap, 6), np.int64)
        self._cego = np.zeros(self._cap, np.int8)
        self._rod = np.zeros(self._cap, np.int32)
        self._peso = np.ones(self._cap, np.float32)
        self._N = 0
        self.vistos = 0
        self.externo = None
    X = property(lambda s: s._X[:s._N])
    y = property(lambda s: s._y[:s._N])
    foto = property(lambda s: s._foto[:s._N])
    ed = property(lambda s: s._ed[:s._N])
    rod = property(lambda s: s._rod[:s._N])
    cego = property(lambda s: s._cego[:s._N])

    def __len__(self):
        return self._N

    def proprios(self):
        return self._N

    def comportamento_do_filho(self, idx=None):
        s = slice(0, self._N) if idx is None else idx
        return bits_dos_comportamentos(self._lo[s], self._hi[s])

    def _crescer(self):
        cap = self._cap * 2
        for nome, pad in (('_X', 0), ('_y', 0), ('_lo', 0), ('_hi', 0), ('_foto', -1), ('_ed', 0), ('_cego', 0), ('_rod', 0), ('_peso', 1)):
            a = getattr(self, nome)
            b = np.full((cap,) + a.shape[1:], pad, a.dtype)
            b[:self._cap] = a
            setattr(self, nome, b)
        self._cap = cap

    def adicionar(self, x, y, comportamento_do_filho, cego=0, rodada=0, foto=-1, edicao=None, informativa=False):
        self.vistos += 1
        peso = 4.0 if y < 0 else 3.0 if informativa else 1.0
        if self._N < self.teto:
            if self._N >= self._cap:
                self._crescer()
            pos = self._N
            self._N += 1
        else:
            pesos = self._peso[:self._N]
            neutras, mudaram, melhoras = (np.flatnonzero(pesos <= 1.0), np.flatnonzero((pesos > 1.0) & (pesos < 4.0)), np.flatnonzero(pesos >= 4.0))
            if peso == 4.0:
                cand = neutras if len(neutras) else mudaram if len(mudaram) else melhoras
            elif peso == 3.0:
                cand = neutras if len(neutras) else mudaram
                if not len(neutras) and self.g.random() > self.teto / self.vistos:
                    return -1
            else:
                if self.g.random() > self.teto / self.vistos:
                    return -1
                cand = mudaram if len(mudaram) + len(melhoras) >= self.teto // 2 and len(mudaram) else neutras
                if not len(cand):
                    cand = mudaram if len(mudaram) else neutras
            if len(cand) == 0:
                return -1
            pos = int(cand[self.g.integers(len(cand))])
        self._X[pos], self._y[pos] = (x, y)
        self._lo[pos], self._hi[pos] = dividir(comportamento_do_filho)
        self._cego[pos], self._rod[pos], self._foto[pos], self._peso[pos] = (int(cego), int(rodada), int(foto), peso)
        self._ed[pos] = 0 if edicao is None else np.asarray(edicao, np.int64)
        return pos

    def lote(self, quantos, g, reservar=0.0):
        N = self._N
        if N == 0:
            return None
        corte = max(1, int(N * (1.0 - reservar)))
        p = self._peso[:corte].astype(np.float64)
        p = p / p.sum()
        k1 = quantos // 2
        idx = np.concatenate([g.choice(corte, k1, p=p), g.integers(0, corte, quantos - k1)])
        return (self._X[idx].astype(np.float32), self._y[idx], bits_dos_comportamentos(self._lo[idx], self._hi[idx]), np.ones(len(idx), np.float32))

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        N = self._N
        np.savez(tmp, X=self._X[:N], y=self._y[:N], lo=self._lo[:N], hi=self._hi[:N], foto=self._foto[:N], ed=self._ed[:N], cego=self._cego[:N], rod=self._rod[:N], peso=self._peso[:N], vistos=np.asarray([self.vistos]), teto=np.asarray([self.teto]))
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, teto=None, semente=0):
        m = cls(teto=teto or 150000, semente=semente)
        if caminho and os.path.exists(caminho):
            try:
                z = np.load(caminho)
                N = len(z['y'])
                if z['X'].shape[1] == N_ENTRADA:
                    while m._cap < N:
                        m._crescer()
                    m._X[:N], m._y[:N], m._lo[:N], m._hi[:N], m._foto[:N], m._ed[:N] = (z['X'], z['y'], z['lo'], z['hi'], z['foto'], z['ed'])
                    m._cego[:N], m._rod[:N], m._peso[:N] = (z['cego'], z['rod'], z['peso'])
                    m._N = N
                    m.vistos = int(z['vistos'][0])
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                pass
        return m

    def importar(self, caminhos, teto=60000):
        Xs, ys, ls, hs = ([], [], [], [])
        for c in caminhos:
            try:
                z = np.load(c)
                if len(z['y']) == 0 or z['X'].shape[1] != N_ENTRADA:
                    continue
                (Xs.append(z['X']), ys.append(z['y']), ls.append(z['lo']), hs.append(z['hi']))
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                continue
        if not Xs:
            self.externo = None
            return 0
        X, y, lo, hi = (np.concatenate(Xs), np.concatenate(ys), np.concatenate(ls), np.concatenate(hs))
        if len(y) > teto:
            ix = self.g.choice(len(y), teto, replace=False)
            X, y, lo, hi = (X[ix], y[ix], lo[ix], hi[ix])
        self.externo = (X, y, lo, hi)
        return len(y)

class Piscinas:

    def __init__(self, teto=400, semente=0):
        self.teto = int(teto)
        self.g = np.random.default_rng(semente + 777)
        self.itens = []
        self.vistas = 0

    def __len__(self):
        return len(self.itens)

    def adicionar(self, X, y, lo, hi, n, seq):
        self.vistas += 1
        it = (np.asarray(X, np.float16).copy(), np.asarray(y, np.float32).copy(), np.asarray(lo, np.uint64).copy(), np.asarray(hi, np.uint64).copy(), int(n), int(seq))
        if len(self.itens) < self.teto:
            self.itens.append(it)
        else:
            j = int(self.g.integers(self.vistas))
            if j < self.teto:
                self.itens[j] = it

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        if self.itens:
            Xc = np.concatenate([it[0] for it in self.itens])
            yc = np.concatenate([it[1] for it in self.itens])
            lo = np.concatenate([it[2] for it in self.itens])
            hi = np.concatenate([it[3] for it in self.itens])
            off = np.cumsum([0] + [len(it[1]) for it in self.itens])
        else:
            Xc, yc, lo, hi, off = (np.zeros((0, N_ENTRADA), np.float16), np.zeros(0, np.float32), np.zeros(0, np.uint64), np.zeros(0, np.uint64), np.zeros(1, int))
        np.savez_compressed(tmp, Xc=Xc, yc=yc, lo=lo, hi=hi, off=off, n=np.array([it[4] for it in self.itens], int), seq=np.array([it[5] for it in self.itens], int), vistas=np.asarray([self.vistas]))
        os.replace(tmp, caminho)

    @staticmethod
    def ler(caminho):
        z = np.load(caminho)
        Xc, yc, lo, hi, off = (z['Xc'], z['yc'], z['lo'], z['hi'], z['off'])
        if Xc.shape[1] != N_ENTRADA:
            return []
        return [(Xc[off[i]:off[i + 1]], yc[off[i]:off[i + 1]], lo[off[i]:off[i + 1]], hi[off[i]:off[i + 1]], int(z['n'][i]), int(z['seq'][i])) for i in range(len(z['n']))]

    @classmethod
    def carregar(cls, caminho, teto=400, semente=0):
        p = cls(teto, semente)
        if caminho and os.path.exists(caminho):
            try:
                p.itens = Piscinas.ler(caminho)[:teto]
                p.vistas = max(len(p.itens), int(np.load(caminho)['vistas'][0]))
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                pass
        return p

def ler_piscinas_externas(pasta, proprio, teto=500, g=None):
    itens = []
    for c in sorted(glob.glob(os.path.join(pasta, 'escritor_piscinas_*.npz'))):
        if c.endswith('.tmp.npz') or os.path.basename(c) == f'escritor_piscinas_{proprio}.npz':
            continue
        try:
            itens.extend(Piscinas.ler(c))
        except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
            continue
    if len(itens) > teto:
        g = g or np.random.default_rng(0)
        itens = [itens[i] for i in g.choice(len(itens), teto, replace=False)]
    return itens

def ler_historia_do_escritor(pasta):
    H = []
    caminho = os.path.join(pasta, 'historia.jsonl') if pasta else None
    if not caminho or not os.path.exists(caminho):
        return H
    for ln in open(caminho, encoding='utf-8'):
        if '"evento": "candidata_escritor"' not in ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if 'params' in e and isinstance(e.get('d_dev'), (int, float)) and (not e.get('pulou')):
            H.append(e)
    return H

class Biblioteca:

    def __init__(self, n, P=PROBES):
        self.n, self.P = (int(n), int(P))
        self.d = {}
        self.total = 0

    @staticmethod
    def banda_de(u, m):
        return min(2, int(3 * u / max(m, 1)))

    def registrar(self, k, o, banda, seq, delta, fix_mask, quebra_mask):
        e = self.d.get((k, o, banda, seq))
        if e is None:
            e = [0, 0, 0.0, np.zeros(self.P, np.int32), np.zeros(self.P, np.int32)]
            self.d[k, o, banda, seq] = e
        e[0] += 1
        e[1] += int(delta < 0)
        e[2] += float(delta)
        if fix_mask:
            e[3] += np.array([fix_mask >> p & 1 for p in range(self.P)], np.int32)
        if quebra_mask:
            e[4] += np.array([quebra_mask >> p & 1 for p in range(self.P)], np.int32)
        self.total += 1

    def tamanho(self):
        return len(self.d)

    def opcoes(self, k, o, banda, alvo_mask=0):
        seqs, pesos = ([], [])
        alvo = np.array([alvo_mask >> p & 1 for p in range(self.P)], np.float64) if alvo_mask else None
        for (kk, oo, bb, seq), (t, mel, soma, fix, qb) in self.d.items():
            if kk != k or oo != o or bb != banda:
                continue
            taxa = (mel + 0.5) / (t + 2.0)
            bonus = 0.0
            if alvo is not None and alvo.sum() > 0:
                bonus = float((fix * alvo).sum() / (t + 2.0) / alvo.sum())
            seqs.append(seq)
            pesos.append(taxa * (1.0 + 4.0 * bonus))
        return (np.asarray(seqs, np.int64), np.asarray(pesos, np.float64))

    def topo(self, quantos=20, minimo=15):
        linhas = []
        for (k, o, banda, seq), (t, mel, soma, fix, qb) in self.d.items():
            if t >= minimo and mel > 0:
                consertadas = [int(p) for p in np.argsort(-fix)[:3] if fix[p] > 0]
                linhas.append({'k': k, 'deslocamento': o, 'regiao': banda, 'sequencia': format(seq, f'0{k}b'), 'tentativas': int(t), 'melhoras': int(mel), 'taxa': round(mel / t, 4), 'delta_medio': round(soma / t, 4), 'sondas_que_mais_conserta': consertadas})
        linhas.sort(key=lambda r: (-r['taxa'], -r['tentativas']))
        return linhas[:quantos]

    def salvar(self, caminho):
        chaves = list(self.d.keys())
        tmp = caminho + '.tmp.npz'
        np.savez_compressed(tmp, chaves=np.array(chaves, np.int64).reshape(-1, 4), tent=np.array([self.d[c][0] for c in chaves], np.int64), mel=np.array([self.d[c][1] for c in chaves], np.int64), soma=np.array([self.d[c][2] for c in chaves], np.float64), fix=np.array([self.d[c][3] for c in chaves], np.int32).reshape(-1, self.P), qb=np.array([self.d[c][4] for c in chaves], np.int32).reshape(-1, self.P), n=np.asarray([self.n]), total=np.asarray([self.total]))
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, n, P=PROBES):
        b = cls(n, P)
        if caminho and os.path.exists(caminho):
            try:
                z = np.load(caminho)
                for i, c in enumerate(z['chaves']):
                    b.d[tuple((int(x) for x in c))] = [int(z['tent'][i]), int(z['mel'][i]), float(z['soma'][i]), z['fix'][i].copy(), z['qb'][i].copy()]
                b.total = int(z['total'][0])
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                pass
        return b

def amostrar_da_biblioteca(est, biblioteca, M_, g, alvo_mask=0):
    n, m, w, U = (est.n, est.m, est.w, est.U)
    if m < 2 or biblioteca is None or biblioteca.tamanho() == 0 or (M_ <= 0):
        return Pool.vazio()
    u = g.integers(0, m, M_)
    opcao = g.integers(0, 3, M_)
    k = np.where(opcao == 0, U, w)
    o = np.where(opcao == 2, w, 0)
    seq = np.zeros(M_, np.int64)
    ok = np.zeros(M_, bool)
    banda = np.minimum(2, 3 * u // max(m, 1))
    for kk, oos in ((U, (0,)), (w, (0, w))):
        for oo in oos:
            for bb in (0, 1, 2):
                sel = np.flatnonzero((k == kk) & (o == oo) & (banda == bb))
                if len(sel) == 0:
                    continue
                seqs, pesos = biblioteca.opcoes(kk, oo, bb, alvo_mask)
                if len(seqs) == 0:
                    continue
                pesos = pesos / pesos.sum()
                seq[sel] = seqs[g.choice(len(seqs), len(sel), p=pesos)]
                ok[sel] = True
    if not ok.any():
        return Pool.vazio()
    p = u * U + o
    u0, nu, lo, hi, valido = _decodificar_trechos(est, p[ok], k[ok], seq[ok])
    P = Pool(np.full(ok.sum(), TROCA), p[ok], k[ok], seq[ok], np.zeros(ok.sum(), np.int64), u0, nu, lo, hi, valido, origem=np.ones(ok.sum(), np.int8))
    return P.filtrar(P.valido)

def duras_do_pai(X, n_duras):
    phi = X[0, N_ENTRADA - PROBES:N_ENTRADA - PROBES + n_duras]
    return int(sum((int(v > 0.5) << i for i, v in enumerate(phi))))

def notas(rede, X, n_duras=0, peso_semantico=0.5):
    X = np.asarray(X, np.float32)
    f, p = rede.prever(X)
    if n_duras > 0 and peso_semantico and len(X):
        esperadas = p[:, :n_duras].sum(1)
        antes = bin(duras_do_pai(X, n_duras)).count('1')
        f = f + peso_semantico * (esperadas - antes) / n_duras
    return f

def escolha_top1(notas_por_piscina, itens):
    return np.array([float(it[1][int(np.argmin(p))]) for p, it in zip(notas_por_piscina, itens)])

def ganho_no_top1(notas_por_piscina, itens):
    esc = escolha_top1(notas_por_piscina, itens)
    med = np.array([float(it[1].mean()) for it in itens])
    melhor = np.array([float(it[1].min()) for it in itens])
    d = esc - med
    cap = (med - esc).sum() / max((med - melhor).sum(), 1e-09)
    return (M.resumo(d), float(cap))

def particoes_de_piscinas(proprias, externas):
    ordem = sorted(proprias, key=lambda it: it[5])
    n = len(ordem)
    return (ordem[n // 2:], ordem[:int(n * 0.3)] + list(externas))

def notas_das_piscinas(rede, itens, n_duras=0):
    return [notas(rede, it[0], n_duras) for it in itens]
BRACOS = {'piscina': 0, 'aprendida': 1, 'cega': 2, 'fria': 3}

class Escritor:

    def __init__(self, n, pref, vetores, sondas=None, semente=0, pool=2048, k_modelo=40, k_cega=12, passos=4, mix=(45, 20, 15, 20), min_memoria=1500, teto_memoria=150000, piscina_m=128, peso_semantico=0.5):
        self.n, self.pref, self.vetores = (int(n), [tuple(c) for c in pref], int(vetores))
        self.sondas = sondas
        self.pool, self.k_modelo, self.k_cega, self.passos, self.mix = (int(pool), int(k_modelo), int(k_cega), int(passos), tuple(mix))
        self.piscina_m = int(piscina_m)
        self.min_memoria = int(min_memoria)
        self.peso_semantico = float(peso_semantico)
        self.g = np.random.default_rng(semente + 4242)
        self.mem = MemoriaEscritor(teto=teto_memoria, semente=semente)
        self.rede = RedeDupla(semente=semente + 11)
        self.piscinas = Piscinas(teto=400, semente=semente)
        self.biblioteca = Biblioteca(n)
        self.fotos = None
        self.edicoes = None
        self.treinos = 0
        self.seq = 0
        self.H = []
        self.meta = M.MetaModelo()
        self.contadores = {'escritas': 0, 'escritas_aprendidas': 0, 'escritas_cegas': 0, 'escritas_frias': 0, 'passos_aceitos': 0, 'edicoes_avaliadas': 0, 'avaliacoes_de_V': 0, 'piscinas_rotuladas': 0, 'unidades_do_modelo_aceitas': 0, 'unidades_cegas_aceitas': 0, 'edicoes_da_biblioteca_avaliadas': 0, 'edicoes_da_biblioteca_aceitas': 0, 'sementes_que_ordenam': 0, 'rodadas_de_selecao': 0, 'trocas_adotadas': 0, 'trocas_recusadas': 0, 'edicoes_que_mudaram_o_comportamento': 0}
        self.vel = {b: [0, 0, 0] for b in ('aprendida', 'cega', 'fria')}
        self._vel_anterior = {b: [0, 0, 0] for b in ('aprendida', 'cega', 'fria')}

    @property
    def n_duras(self):
        return len(self.sondas.duras) if self.sondas is not None else 0

    def _mascara_das_duras(self):
        return self.sondas.mascara_das_duras() if self.sondas is not None else 0

    def _mascara_total(self):
        return (1 << len(self.sondas)) - 1 if self.sondas is not None else 0

    def _avaliar(self, srv, rede):
        if self.sondas is not None:
            return srv.avaliar_f(rede)
        return (srv.avaliar(rede), 0)

    def _duras_falhando(self, comp):
        return bin(int(comp) & self._mascara_das_duras()).count('1')

    def pronto(self):
        return self.treinos > 0 and self.mem.proprios() >= self.min_memoria

    def _foto(self, rede, falhas, comp, origem, pai, gen):
        if self.fotos is None:
            return -1
        ident = self.fotos.adicionar(rede, falhas, len(self.pref) + len(rede), None, origem, pai, gen, comp if self.sondas is not None else None, self.sondas.versao if self.sondas is not None else 0)
        return ident

    def _log_edicao(self, estado_id, tipo, p, k, seq, q2, passo, falhas, comp, braco, gen):
        if self.edicoes is not None:
            self.edicoes.adicionar(estado_id, tipo, p, k, seq, q2, passo, falhas, comp, BRACOS.get(braco, 0), gen)

    def _registrar_padrao(self, est, pool, i, y, comp_pai, comp_filho):
        if int(pool.tipo[i]) != TROCA:
            return
        w, U = (est.w, est.U)
        k, p = (int(pool.k[i]), int(pool.p[i]))
        o = p % U
        if not (k == U and o == 0 or (k == w and o in (0, w))):
            return
        banda = Biblioteca.banda_de(int(pool.u0[i]), est.m)
        fix = int(comp_pai) & ~int(comp_filho) & self._mascara_das_duras()
        quebra = ~int(comp_pai) & int(comp_filho) & self._mascara_total()
        self.biblioteca.registrar(k, o, banda, int(pool.seq[i]), y, fix, quebra)

    def _alinhar(self, srv, S, f, fd):
        Sc = F.canonica(self.n, self.pref, S)
        if Sc == [tuple(c) for c in S]:
            return (Sc, int(f), list(fd), 0)
        f2, fd2 = srv.escanear(Sc)
        return (Sc, int(f2), list(fd2), len(Sc))

    def escrever(self, srv, S0, f0, fd0, braco, g=None, pai_foto=-1, gen=0):
        g = g or self.g
        S, f, fd, aval = self._alinhar(srv, S0, f0, fd0)
        f_conf, comp = self._avaliar(srv, S)
        aval += 1
        aplicaveis = braco == 'aprendida' and self.pronto()
        rotulo = 'aprendida' if aplicaveis else 'cega' if braco == 'cega' else 'fria'
        origem_foto = 'escrita_' + rotulo
        id_estado = self._foto(S, f, comp, 'retirada', pai_foto, gen)
        estados = [{'rede': [tuple(c) for c in S], 'falhas': f, 'comportamento': comp, 'id': id_estado}]
        aceitas = []
        f_molde, duras_molde = (f, self._duras_falhando(comp))
        mask_d = self._mascara_das_duras()
        for passo in range(self.passos):
            est = Estado(self.n, self.pref, S, f, fd, self.vetores, passo, comp)
            if aplicaveis:
                n_bib = self.pool // 2 if self.biblioteca.tamanho() >= 50 else 0
                pool = Pool.juntar([amostrar_cego(est, self.pool - n_bib, self.mix, g), amostrar_da_biblioteca(est, self.biblioteca, n_bib, g, comp & mask_d)])
            else:
                pool = amostrar_cego(est, self.pool, self.mix, g)
            if pool.K == 0:
                break
            X = caracteristicas(est, pool)
            if aplicaveis:
                sc = notas(self.rede, X, self.n_duras, self.peso_semantico)
                k1 = min(self.k_modelo, pool.K)
                topo = np.argpartition(sc, k1 - 1)[:k1] if k1 < pool.K else np.arange(pool.K)
                cand = np.setdiff1d(np.flatnonzero(pool.origem == 0), topo)
                k2 = min(self.k_cega, len(cand))
                cegas = g.choice(cand, k2, replace=False) if k2 else np.zeros(0, int)
                escolhidas = np.concatenate([topo, cegas]).astype(int)
                origens = ['modelo'] * len(topo) + ['cega'] * len(cegas)
            else:
                k = min(self.k_modelo + self.k_cega, pool.K)
                escolhidas = g.choice(pool.K, k, replace=False).astype(int)
                origens = ['cega'] * k
            base = math.log1p(f)
            melhor = None
            avaliadas = 0
            for i, org in zip(escolhidas, origens):
                tipo, p, kk, seq, q2 = pool.uma(int(i))
                filho = aplicar(S, self.n, tipo, p, kk, seq, q2)
                if filho is None:
                    continue
                fc, cc = self._avaliar(srv, filho)
                aval += 1
                avaliadas += 1
                y = math.log1p(fc) - base
                mudou = int(cc) != int(comp)
                self.mem.adicionar(X[i], y, cc, cego=int(org == 'cega'), rodada=gen, foto=id_estado, edicao=(tipo, p, kk, seq, q2, passo), informativa=mudou)
                self._registrar_padrao(est, pool, int(i), y, comp, cc)
                self._log_edicao(id_estado, tipo, p, kk, seq, q2, passo, fc, cc, rotulo, gen)
                self.contadores['edicoes_que_mudaram_o_comportamento'] += int(mudou)
                if pool.origem[i] == 1:
                    self.contadores['edicoes_da_biblioteca_avaliadas'] += 1
                chave = (fc, self._duras_falhando(cc))
                if (fc < f or (fc == f and chave[1] < self._duras_falhando(comp))) and (melhor is None or chave < melhor[0]):
                    melhor = (chave, filho, org, (tipo, p, kk, seq, q2), int(i), cc)
            self.contadores['edicoes_avaliadas'] += avaliadas
            self.vel[rotulo][0] += 1
            self.vel[rotulo][2] += avaliadas
            if melhor is None:
                break
            (fc, _), filho, org, edicao, i_esc, cc = melhor
            self.vel[rotulo][1] += 1
            pai_estado = id_estado
            S = F.canonica(self.n, self.pref, filho)
            f_toda, fd = srv.escanear(S)
            f_conf, comp = self._avaliar(srv, S)
            f = int(f_conf)
            aval += len(S) + 1
            self.vel[rotulo][2] += len(S) + 1
            id_estado = self._foto(S, f, comp, origem_foto, pai_estado, gen)
            estados.append({'rede': [tuple(c) for c in S], 'falhas': f, 'comportamento': comp, 'id': id_estado})
            aceitas.append({'origem': org, 'edicao': edicao, 'nome': NOMES_DE_TIPO[edicao[0]], 'falhas_depois': f, 'da_biblioteca': bool(pool.origem[i_esc] == 1), 'comportamento_depois': int(comp)})
            self.contadores['unidades_do_modelo_aceitas' if org == 'modelo' else 'unidades_cegas_aceitas'] += 1
            self.contadores['edicoes_da_biblioteca_aceitas'] += int(pool.origem[i_esc] == 1)
            if f == 0:
                break
        self.contadores['escritas'] += 1
        self.contadores['escritas_' + {'aprendida': 'aprendidas', 'cega': 'cegas', 'fria': 'frias'}[rotulo]] += 1
        self.contadores['passos_aceitos'] += len(aceitas)
        self.contadores['avaliacoes_de_V'] += aval
        if f == 0:
            self.contadores['sementes_que_ordenam'] += 1
        return {'rede': S, 'falhas': f, 'falhas_do_molde': int(f_molde), 'duras_do_molde': duras_molde, 'duras_da_semente': self._duras_falhando(comp), 'braco': rotulo, 'aceitas': aceitas, 'avaliacoes': aval, 'estados': estados}

    def rotular_piscina(self, srv, S, f, fd, g=None, rodada=0, foto=-1, destino='piscina'):
        g = g or self.g
        S, f, fd, gasto = self._alinhar(srv, S, f, fd)
        f_conf, comp = self._avaliar(srv, S)
        est = Estado(self.n, self.pref, S, f, fd, self.vetores, 0, comp)
        pool = amostrar_cego(est, self.piscina_m, self.mix, g)
        if pool.K < 8:
            return gasto
        X = caracteristicas(est, pool)
        base = math.log1p(f)
        ys = np.zeros(pool.K, np.float32)
        los, his = (np.zeros(pool.K, np.uint64), np.zeros(pool.K, np.uint64))
        comps = []
        for i in range(pool.K):
            tipo, p, kk, seq, q2 = pool.uma(i)
            filho = aplicar(S, self.n, tipo, p, kk, seq, q2)
            fc, cc = self._avaliar(srv, filho)
            ys[i] = math.log1p(fc) - base
            los[i], his[i] = dividir(cc)
            comps.append(cc)
            self._log_edicao(foto, tipo, p, kk, seq, q2, 0, fc, cc, 'piscina', rodada)
            self._registrar_padrao(est, pool, i, float(ys[i]), comp, cc)
        self.seq += 1
        if destino == 'piscina':
            self.piscinas.adicionar(X, ys, los, his, self.n, self.seq)
        else:
            for i in range(pool.K):
                tipo, p, kk, seq, q2 = pool.uma(i)
                self.mem.adicionar(X[i], float(ys[i]), comps[i], cego=1, rodada=rodada, foto=foto, edicao=(tipo, p, kk, seq, q2, 0), informativa=int(comps[i]) != int(comp))
        self.contadores['piscinas_rotuladas'] += 1
        return gasto + pool.K + 1

    def treinar(self, passos=25, lote=256):
        if self.mem.proprios() < 200:
            return
        for _ in range(passos):
            b = self.mem.lote(lote, self.g)
            self.rede.passo(b[0], b[1], b[2], b[3])
        self.treinos += 1

    def curva(self, externas=None):
        dev, ret = particoes_de_piscinas(self.piscinas.itens, externas or [])
        if len(dev) < 10:
            return None
        r_dev, cap_dev = ganho_no_top1(notas_das_piscinas(self.rede, dev, self.n_duras), dev)
        out = {'piscinas_dev': r_dev['K'], 'ganho_dev': round(r_dev['media'], 5), 'erro_padrao_dev': round(r_dev['erro_padrao'], 5) if math.isfinite(r_dev['erro_padrao']) else None, 'captura_dev': round(cap_dev, 4)}
        if len(ret) >= 10:
            r_ret, cap_ret = ganho_no_top1(notas_das_piscinas(self.rede, ret, self.n_duras), ret)
            out.update(piscinas_ret=r_ret['K'], ganho_ret=round(r_ret['media'], 5), captura_ret=round(cap_ret, 4))
        return out

    def significado(self, itens=None, max_piscinas=120):
        itens = itens if itens is not None else self.piscinas.itens[-max_piscinas:]
        if len(itens) < 5 or self.sondas is None:
            return None
        P = len(self.sondas)
        prob_all, pai_all, filho_all = ([], [], [])
        for it in itens:
            X = np.asarray(it[0], np.float32)
            _, p = self.rede.prever(X)
            prob_all.append(p[:, :P])
            pai_all.append(np.tile(X[0, N_ENTRADA - PROBES:N_ENTRADA - PROBES + P], (len(X), 1)))
            filho_all.append(bits_dos_comportamentos(it[2], it[3], P))
        p, pai, filho = (np.concatenate(prob_all), np.concatenate(pai_all), np.concatenate(filho_all))
        eps = 1e-06
        bce = float(-(filho * np.log(p + eps) + (1 - filho) * np.log(1 - p + eps)).mean())
        pc = np.clip(pai, 0.02, 0.98)
        bce_copia = float(-(filho * np.log(pc) + (1 - filho) * np.log(1 - pc)).mean())
        troca = (filho != pai).astype(np.float64)
        taxa = np.clip(troca.mean(0), 0.0001, 1 - 0.0001)
        bce_acaso = float(-(taxa * np.log(taxa) + (1 - taxa) * np.log(1 - taxa)).mean())
        mudou = (filho != pai).reshape(-1)
        escore = np.abs(p - pai).reshape(-1)
        auc = None
        if mudou.any() and (~mudou).any():
            ordem = np.argsort(escore, kind='mergesort')
            rk = np.empty(len(escore))
            rk[ordem] = np.arange(1, len(escore) + 1)
            n1 = int(mudou.sum())
            auc = float((rk[mudou].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(escore) - n1)))
        return {'pares_edicao_sonda': int(len(mudou)), 'mudancas_de_estado': int(mudou.sum()), 'entropia_cruzada_do_modelo': round(bce, 5), 'entropia_cruzada_de_copiar_o_pai': round(bce_copia, 5), 'entropia_cruzada_do_acaso_calibrado': round(bce_acaso, 5), 'auc_de_prever_quais_sondas_mudam': round(auc, 4) if auc is not None else None}

    def rodada_de_selecao(self, externas=None, H_externa=None, minimo_dev=30, minimo_ret=15, max_degraus=6):
        dev, ret = particoes_de_piscinas(self.piscinas.itens, externas or [])
        reg = {'evento': 'candidata_escritor', 'K_dev': len(dev), 'K_ret': len(ret)}
        if len(dev) < minimo_dev or self.mem.proprios() < 300:
            return dict(reg, pulou='poucas piscinas ou pouca memória')
        H = list(self.H) + list(H_externa or [])
        params, cego, nota = self.meta.propor(H, self.g, 1)
        op = params['op']
        atual = self.rede
        if op == 'nova':
            cand = RedeDupla(escondidas=tuple(params['esc'][:2]) or (64,), semente=int(self.g.integers(1 << 30)), lr=params['lr'], l2=params['l2'])
        else:
            cand = atual.copiar()
            cand.lr, cand.l2 = (params['lr'], params.get('l2', 0.0))
            if op in ('alargar', 'degrau'):
                cand.alargar(params.get('extra', 8) or 8, self.g)
        for _ in range(150 if op == 'nova' else 80):
            b = self.mem.lote(256, self.g)
            cand.passo(b[0], b[1], b[2], b[3])
        nd = self.n_duras
        esc_at_dev, esc_no_dev = (escolha_top1(notas_das_piscinas(atual, dev, nd), dev), escolha_top1(notas_das_piscinas(cand, dev, nd), dev))
        d_dev = esc_no_dev - esc_at_dev
        d_ret = escolha_top1(notas_das_piscinas(cand, ret, nd), ret) - escolha_top1(notas_das_piscinas(atual, ret, nd), ret) if ret else np.zeros(0)
        ok_dev, ok_ret = (M.passa_a_porta(d_dev, minimo_dev), M.passa_a_retencao(d_ret, minimo_ret))
        adotou = bool(ok_dev and ok_ret)
        g_antes, cap_antes = ganho_no_top1(notas_das_piscinas(atual, dev, nd), dev)
        g_depois, cap_depois = ganho_no_top1(notas_das_piscinas(cand, dev, nd), dev)
        if adotou:
            self.rede = cand
        rd, rr = (M.resumo(d_dev), M.resumo(d_ret))

        def r6(x):
            return round(x, 6) if math.isfinite(x) else None
        reg.update(params=params, cego=bool(cego), nota_do_meta_modelo=round(nota, 5), arquitetura=list(cand.esc), d_dev=r6(rd['media']), se_dev=r6(rd['erro_padrao']), d_ret=r6(rr['media']), se_ret=r6(rr['erro_padrao']), passa_a_porta=bool(ok_dev), passa_a_retencao=bool(ok_ret), adotou=adotou, ganho_no_top1={'antes': r6(g_antes['media']), 'depois': r6(g_depois['media']), 'captura_antes': round(cap_antes, 4), 'captura_depois': round(cap_depois, 4)})
        self.H.append({'params': params, 'd_dev': reg['d_dev'] if reg['d_dev'] is not None else 0.0})
        self.contadores['rodadas_de_selecao'] += 1
        self.contadores['trocas_adotadas' if adotou else 'trocas_recusadas'] += 1
        return reg

    def velocidade(self):
        out = {}
        for b in self.vel:
            atual, antes = (self.vel[b], self._vel_anterior[b])
            d = [a - c for a, c in zip(atual, antes)]
            out[b] = {'passos': d[0], 'melhoraram': d[1], 'avaliacoes': d[2], 'melhoras_por_mil_avaliacoes': round(1000.0 * d[1] / d[2], 4) if d[2] else None}
            self._vel_anterior[b] = list(atual)
        return out

    def padroes(self, piscinas_max=120):
        y = self.mem.y
        out = {'exemplos_proprios': int(len(y)), 'edicoes_que_melhoraram': int((y < 0).sum()), 'padroes_na_biblioteca': self.biblioteca.tamanho(), 'padroes_de_bits_que_mais_melhoraram': self.biblioteca.topo(20)}
        if self.sondas is not None:
            out['sondas'] = self.sondas.descricao()
        sig = self.significado()
        if sig:
            out['significado_que_o_modelo_sabe_prever'] = sig
        itens = self.piscinas.itens[-piscinas_max:]
        if len(itens) >= 10 and self.pronto():
            base_res, _ = ganho_no_top1(notas_das_piscinas(self.rede, itens, self.n_duras), itens)
            imp = {}
            g = np.random.default_rng(5)
            for nome, (a, b) in GRUPOS.items():
                emb = []
                for it in itens:
                    Xp = np.asarray(it[0], np.float32).copy()
                    Xp[:, a:b] = Xp[g.permutation(len(Xp))][:, a:b]
                    emb.append(notas(self.rede, Xp, self.n_duras, self.peso_semantico))
                r, _ = ganho_no_top1(emb, itens)
                imp[nome] = round(r['media'] - base_res['media'], 5)
            out['importancia_dos_grupos'] = imp
            out['ganho_de_decisao_no_top1_contra_o_sorteio'] = {'media': round(base_res['media'], 5), 'erro_padrao': round(base_res['erro_padrao'], 5) if math.isfinite(base_res['erro_padrao']) else None, 'piscinas': base_res['K']}
        return out

    def salvar(self, pasta, conhecimento=None, rotulo=None):
        os.makedirs(pasta, exist_ok=True)
        self.mem.salvar(os.path.join(pasta, 'escritor_memoria.npz'))
        tmp = os.path.join(pasta, 'escritor_modelo.json.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.rede.estado(), f)
        os.replace(tmp, os.path.join(pasta, 'escritor_modelo.json'))
        self.piscinas.salvar(os.path.join(pasta, 'escritor_piscinas.npz'))
        self.biblioteca.salvar(os.path.join(pasta, 'escritor_biblioteca.npz'))
        with open(os.path.join(pasta, 'escritor_estado.json'), 'w', encoding='utf-8') as f:
            json.dump({'treinos': self.treinos, 'seq': self.seq, 'contadores': self.contadores, 'H': self.H, 'vel': self.vel}, f)
        if conhecimento and rotulo:
            self.mem.salvar(os.path.join(conhecimento, f'escritor_memoria_{rotulo}.npz'))
            self.piscinas.salvar(os.path.join(conhecimento, f'escritor_piscinas_{rotulo}.npz'))

    def carregar(self, pasta, semente=0):
        m = os.path.join(pasta, 'escritor_memoria.npz')
        if not os.path.exists(m):
            return False
        self.mem = MemoriaEscritor.carregar(m, teto=self.mem.teto, semente=semente)
        try:
            self.rede = RedeDupla.de_estado(json.load(open(os.path.join(pasta, 'escritor_modelo.json'), encoding='utf-8')))
        except (OSError, ValueError, KeyError):
            pass
        self.piscinas = Piscinas.carregar(os.path.join(pasta, 'escritor_piscinas.npz'), semente=semente)
        self.biblioteca = Biblioteca.carregar(os.path.join(pasta, 'escritor_biblioteca.npz'), self.n)
        try:
            e = json.load(open(os.path.join(pasta, 'escritor_estado.json'), encoding='utf-8'))
            self.treinos, self.seq, self.H = (int(e.get('treinos', 0)), int(e.get('seq', 0)), list(e.get('H', [])))
            self.contadores.update(e.get('contadores', {}))
            for b, v in e.get('vel', {}).items():
                if b in self.vel:
                    self.vel[b] = list(v)
                    self._vel_anterior[b] = list(v)
        except (OSError, ValueError):
            pass
        return True

    def importar_das_outras(self, conhecimento, rotulo):
        if not conhecimento:
            return 0
        proprio = os.path.join(conhecimento, f'escritor_memoria_{rotulo}.npz')
        outros = [c for c in sorted(glob.glob(os.path.join(conhecimento, 'escritor_memoria_*.npz'))) if c != proprio and (not c.endswith('.tmp.npz'))]
        return self.mem.importar(outros)
