# -*- coding: utf-8 -*-
import math
import os
import sys
import numpy as np
from experimentos import l_ser_lang as L
DES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
from comum_vida import _desempacotar, _empacotar
CL = L.CL
EPS = L.EPS
MATURIDADE = 16
PASSO_MAX = 0.5
PESO_MAX = 20.0
TAXA_ENTRADA = 0.001

def _prender(x):
    return np.clip(x, -CL, CL)
PERTURBACAO = {'eps': 0.0, 'semente': 0}
_K_T, _K_M, _K_Q = (np.uint64(11400714819323198485), np.uint64(13787848793156543929), np.uint64(10723151780598845931))

def definir_perturbacao(eps=0.0, semente=0):
    eps = float(eps)
    if eps:
        assert eps > 0 and math.frexp(eps)[0] == 0.5, 'eps tem de ser uma potência de 2 (para o fator ser exato nos dois motores)'
    PERTURBACAO['eps'], PERTURBACAO['semente'] = (eps, int(semente) & (1 << 64) - 1)

def fatores_de_perturbacao(semente, t, m, n, eps):
    with np.errstate(over='ignore'):
        q = np.arange(n, dtype=np.uint64)
        z = np.uint64(semente) ^ np.uint64(t) * _K_T ^ np.uint64(m + 1) * _K_M ^ q * _K_Q
        z = z ^ z >> np.uint64(30)
        z = z * _K_M
        z = z ^ z >> np.uint64(27)
        z = z * _K_Q
        z = z ^ z >> np.uint64(31)
    u = (z >> np.uint64(40)).astype(np.float64) / 16777216.0 * 2.0 - 1.0
    return (1.0 + eps * u).astype(np.float32)

def _f32(x):
    return np.asarray(x, np.float32)

def _op_add(a, b, c):
    return a + b

def _op_sub(a, b, c):
    return a - b

def _op_mul(a, b, c):
    return _prender(a * b)

def _op_div(a, b, c):
    return _prender(a / (np.abs(b) + EPS))

def _op_max(a, b, c):
    return np.maximum(a, b)

def _op_min(a, b, c):
    return np.minimum(a, b)

def _op_neg(a, b, c):
    return -a

def _op_abs(a, b, c):
    return np.abs(a)

def _op_sq(a, b, c):
    return _prender(a * a)

def _op_sqrt(a, b, c):
    return np.sqrt(np.abs(a))

def _op_tanh(a, b, c):
    return np.tanh(a)

def _op_relu(a, b, c):
    return np.maximum(a, 0.0)

def _op_sig(a, b, c):
    return 1.0 / (1.0 + np.exp(-np.clip(a, -30.0, 30.0)))

def _op_thr(a, b, c):
    return (a > 0).astype(np.float32)

def _op_sign(a, b, c):
    return np.sign(a)

def _op_exp(a, b, c):
    return _prender(np.exp(np.minimum(a, 8.0)))

def _op_log(a, b, c):
    return np.log1p(np.abs(a))

def _op_inv(a, b, c):
    return _prender(1.0 / (np.abs(a) + EPS))

def _op_avg(a, b, c):
    return 0.5 * (a + b)

def _op_k(a, b, c):
    return np.float32(c)

def _op_mulk(a, b, c):
    return _prender(a * np.float32(c))

def _op_addk(a, b, c):
    return a + np.float32(c)

def _op_gt(a, b, c):
    return (a > b).astype(np.float32)

def _op_absdiff(a, b, c):
    return np.abs(a - b)

def _op_mean0(a, b, c):
    return a.mean(axis=0, keepdims=True) if np.ndim(a) >= 2 else a

def _op_mean1(a, b, c):
    return a.mean(axis=-1, keepdims=True) if np.ndim(a) >= 2 else a

def _op_clip1(a, b, c):
    return np.clip(a, -1.0, 1.0)

def _op_ema(a, b, c):
    return a + np.float32(min(c, 1.0)) * (b - a)

def _op_shrk(a, b, c):
    return a * np.float32(1.0 - min(c, 1.0))

def _op_hyp(a, b, c):
    return np.sqrt(a * a + b * b)

def _op_sel(a, b, c):
    return np.where(a > 0, a, b)

def _op_id(a, b, c):
    return a
_FUNCOES = [_op_add, _op_sub, _op_mul, _op_div, _op_max, _op_min, _op_neg, _op_abs, _op_sq, _op_sqrt, _op_tanh, _op_relu, _op_sig, _op_thr, _op_sign, _op_exp, _op_log, _op_inv, _op_avg, _op_k, _op_mulk, _op_addk, _op_gt, _op_absdiff, _op_mean0, _op_mean1, _op_clip1, _op_ema, _op_shrk, _op_hyp, _op_sel, _op_id]
assert len(_FUNCOES) == L.N_OPS
_VALOR_DE_C = [L.valor_da_constante(q) for q in range(L.NIVEIS)]

class Plano:
    __slots__ = ('tipo', 'nos', 'n_in', 'lidas')

    def __init__(self, nos, tipo):
        self.tipo = tipo
        self.n_in = L.N_ENTRADAS[tipo]
        vivos, lidas = L._nos_vivos(nos, tipo)
        self.lidas = lidas
        self.nos = [(i, _FUNCOES[nos[i].op], nos[i].a, nos[i].b, _VALOR_DE_C[nos[i].c]) for i in sorted(vivos)]

    def rodar(self, env):
        n_in = self.n_in
        reg = list(env) + [None] * L.K_NOS
        for i, f, a, b, c in self.nos:
            va = reg[a]
            vb = reg[b]
            r = f(va, vb, c)
            reg[n_in + i] = r
        out = reg[n_in + L.K_NOS - 1]
        return np.nan_to_num(np.asarray(out, np.float32), copy=False, nan=0.0, posinf=CL, neginf=-CL)

def _ativacao(nome, s):
    if nome == 'relu':
        return np.maximum(s, 0.0)
    if nome == 'tanh':
        return np.tanh(s)
    if nome == 'softsign':
        return s / (1.0 + np.abs(s))
    return np.where(s > 0, s, 0.1 * s)

def _softmax(z):
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)

class AprendizSer:

    def __init__(self, d, c, r, prog, restaurando=False):
        self.d, self.c, self.prog = (int(d), int(c), prog)
        T = prog.tecido
        self.T = T
        self.nl = int(T['n_camadas'])
        self.h = [int(T['larguras'][i]) for i in range(self.nl)]
        self.B = int(T['lote'])
        self.cada = int(T['cada'])
        self.dims = [self.d] + self.h + [self.c]
        self.nm = self.nl + 1
        self.planos = {n: Plano(prog.secoes[n], L.TIPO_DA_SECAO[n]) if prog.secoes[n] is not None else None for n in L.NOMES_DAS_SECOES}
        self.rotulos = {n: int(prog.rotulos.get(n, 0)) for n in ('POL1', 'POL2', 'POL3')}
        self._descobrir_o_que_e_lido()
        self.diag = {'passos': 0, 'renascidas': 0, 'ativadas': 0, 'liberadas': 0, 'aprendizados': 0}
        if restaurando:
            return
        seed = (int(r.integers(0, 2 ** 31 - 1)), int(T['semente']))
        self.r = np.random.default_rng(seed)
        self._iniciar()

    def _descobrir_o_que_e_lido(self):
        pl = self.planos
        lidas_peso = set()
        for n in ('W_OCULTA', 'W_SAIDA', 'S1', 'S2', 'S3'):
            if pl[n] is not None:
                lidas_peso |= pl[n].lidas
        self.lidas_peso = lidas_peso
        lidas_unid = set()
        for n in ('U1', 'U2', 'REINIT', 'ATIVA', 'LIBERA'):
            if pl[n] is not None:
                lidas_unid |= pl[n].lidas
        self.lidas_unid = lidas_unid
        self.usa_xi = 'xi' in lidas_peso
        self.S_vivas = [k for k in (1, 2, 3) if pl[f'S{k}'] is not None]
        self.U_vivas = [k for k in (1, 2) if pl[f'U{k}'] is not None]
        self.G_vivas = [k for k in (1, 2) if pl[f'G{k}'] is not None]
        self.tem_guarda = any((pl[n] is not None for n in ('REINIT', 'ATIVA', 'LIBERA')))

    def _iniciar(self):
        T, r = (self.T, self.r)
        self.W, self.conn = ([], [])
        for m in range(self.nm):
            n_in, n_out = (self.dims[m], self.dims[m + 1])
            conn = np.ones((n_in + 1, n_out), bool)
            if m == 0:
                k = max(1, int(round(float(T['porta_entrada']) * n_in)))
                ligadas = np.sort(r.choice(n_in, k, replace=False))
                conn[:n_in] = False
                conn[ligadas] = True
            elif m < self.nm - 1:
                conn[:n_in] = r.random((n_in, n_out)) < float(T['densidade'])
            fan = max(1.0, float(conn[:-1].sum(axis=0).mean()))
            W = r.normal(0.0, float(T['escala_init']) / math.sqrt(fan), (n_in + 1, n_out)).astype(np.float32)
            W[-1] = 0.0
            W *= conn
            self.W.append(W)
            self.conn.append(conn)
        self.mask = []
        for l in range(self.nl):
            k = max(4, int(round(float(T['ativas0']) * self.h[l])))
            k = min(k, self.h[l])
            m_ = np.zeros(self.h[l], np.float32)
            m_[:k] = 1.0
            self.mask.append(m_)
        self.age = [np.zeros(self.dims[l + 1], np.float32) for l in range(self.nm)]
        self.S = {k: [self._init_S(T[f'init_S{k}'], m) for m in range(self.nm)] for k in self.S_vivas}
        self.U = {k: [self._init_U(T[f'init_U{k}'], self.dims[l + 1]) for l in range(self.nm)] for k in self.U_vivas}
        self.G = {k: np.float32(1.0 if T[f'init_G{k}'] == 'um' else 0.0) for k in self.G_vivas}
        self.t = 0
        self.mu = np.zeros(self.d, np.float32)
        self.var = np.ones(self.d, np.float32)
        self.bx, self.by = ([], [])

    def _init_S(self, tipo, m):
        W = self.W[m]
        if tipo == 'zeros':
            return np.zeros_like(W)
        if tipo == 'uns':
            return np.ones_like(W)
        if tipo == 'copia_de_w':
            return W.copy()
        return self.r.normal(0.0, 0.1, W.shape).astype(np.float32) * self.conn[m]

    def _init_U(self, tipo, n):
        if tipo == 'zeros':
            return np.zeros((1, n), np.float32)
        if tipo == 'uns':
            return np.ones((1, n), np.float32)
        if tipo == 'meio':
            return np.full((1, n), 0.5, np.float32)
        return self.r.random((1, n)).astype(np.float32)

    def _frente(self, X):
        X = np.asarray(X, np.float32)
        Bn = X.shape[0]
        um = np.ones((Bn, 1), np.float32)
        apre = [np.concatenate([X, um], 1)]
        s_l, a_l = ([], [])
        for l in range(self.nl):
            s = apre[-1] @ self.W[l]
            a = _ativacao(self.T['ativ'][l], s) * self.mask[l]
            s_l.append(s)
            a_l.append(a)
            apre.append(np.concatenate([a, um], 1))
        z = apre[-1] @ self.W[self.nl]
        return (apre, s_l, a_l, z)

    def _alvo(self, y):
        if np.ndim(y) == 0:
            t = np.zeros(self.c, np.float32)
            t[int(y)] = 1.0
            return t
        return np.asarray(y, np.float32).reshape(self.c)

    def aprender(self, x, y):
        x = np.asarray(x, np.float32)
        self.mu += np.float32(TAXA_ENTRADA) * (x - self.mu)
        self.var += np.float32(TAXA_ENTRADA) * ((x - self.mu) ** 2 - self.var)
        self.bx.append(x)
        self.by.append(self._alvo(y))
        if len(self.bx) >= self.B:
            with np.errstate(all='ignore'):
                self._passo(np.stack(self.bx), np.stack(self.by))
            self.bx, self.by = ([], [])
        self.diag['aprendizados'] += 1

    def _passo(self, X, T):
        pl = self.planos
        Bn = X.shape[0]
        apre, s_l, a_l, z = self._frente(X)
        p = _softmax(z)
        e_out = T - p
        perda_ex = -(T * np.log(np.maximum(p, 1e-09))).sum(axis=1, keepdims=True).astype(np.float32)
        conf_ex = p.max(axis=1, keepdims=True)
        enorm_ex = np.abs(e_out).mean(axis=1, keepdims=True)
        acerto = float(T[np.arange(Bn), p.argmax(1)].mean())
        t_n = np.float32(math.log1p(self.t) / 12.0)
        g1 = self.G.get(1, np.float32(0.0))
        g2 = self.G.get(2, np.float32(0.0))
        msgs = [None] * self.nm
        msgs[self.nl] = e_out.astype(np.float32)
        for l in range(self.nl - 1, -1, -1):
            if pl['RETRO'] is None:
                msgs[l] = np.zeros((Bn, self.h[l]), np.float32)
                continue
            Tm = msgs[l + 1] @ self.W[l + 1][:-1].T
            u1 = self.U[1][l] if 1 in self.U else np.float32(0.0)
            u2 = self.U[2][l] if 2 in self.U else np.float32(0.0)
            env = [np.float32(0.0), np.float32(1.0), Tm, s_l[l], a_l[l], u1, u2, g1, g2, t_n, perda_ex, conf_ex, enorm_ex]
            msgs[l] = (np.broadcast_to(pl['RETRO'].rodar(env), (Bn, self.h[l])) * self.mask[l]).astype(np.float32)
        novos_W, novas_S = ([], {k: [] for k in self.S_vivas})
        lidas = self.lidas_peso
        for m in range(self.nm):
            a_pre = apre[m]
            a_pos = a_l[m] if m < self.nl else p
            m_pos = msgs[m]
            e = {}
            if 'P' in lidas:
                e['P'] = a_pre.T @ m_pos / Bn
            if 'Q' in lidas:
                e['Q'] = a_pre.T @ a_pos / Bn
            if 'P2' in lidas:
                e['P2'] = (a_pre * a_pre).T @ (m_pos * m_pos) / Bn
            if 'Q2' in lidas:
                e['Q2'] = (a_pre * a_pre).T @ (a_pos * a_pos) / Bn
            if 'pre' in lidas:
                e['pre'] = a_pre.mean(axis=0)[:, None]
            if 'post' in lidas:
                e['post'] = a_pos.mean(axis=0)[None, :]
            if 'err' in lidas:
                e['err'] = m_pos.mean(axis=0)[None, :]
            if 'pre2' in lidas:
                e['pre2'] = (a_pre * a_pre).mean(axis=0)[:, None]
            if 'post2' in lidas:
                e['post2'] = (a_pos * a_pos).mean(axis=0)[None, :]
            if 'err2' in lidas:
                e['err2'] = (m_pos * m_pos).mean(axis=0)[None, :]
            if self.usa_xi:
                e['xi'] = self.r.standard_normal(self.W[m].shape).astype(np.float32)
            z0, z1 = (np.float32(0.0), np.float32(1.0))
            names = L.ENTRADAS['peso']
            env = [z0, z1, self.W[m], e.get('P', z0), e.get('Q', z0), e.get('P2', z0), e.get('Q2', z0), e.get('pre', z0), e.get('post', z0), e.get('err', z0), e.get('pre2', z0), e.get('post2', z0), e.get('err2', z0), self.S[1][m] if 1 in self.S else z0, self.S[2][m] if 2 in self.S else z0, self.S[3][m] if 3 in self.S else z0, self.U[1][m] if 1 in self.U else z0, self.U[2][m] if 2 in self.U else z0, g1, g2, t_n, e.get('xi', z0), np.float32(m / max(self.nm - 1, 1))]
            assert len(env) == len(names)
            regra = pl['W_SAIDA'] if m == self.nm - 1 else pl['W_OCULTA']
            if regra is not None:
                dw = np.clip(np.broadcast_to(regra.rodar(env), self.W[m].shape), -PASSO_MAX, PASSO_MAX)
                if m < self.nl:
                    dw = dw * self.mask[m][None, :]
                W_novo = np.clip(self.W[m] + dw, -PESO_MAX, PESO_MAX) * self.conn[m]
            else:
                W_novo = self.W[m]
            novos_W.append(W_novo.astype(np.float32))
            for k in self.S_vivas:
                s_out = np.clip(np.broadcast_to(pl[f'S{k}'].rodar(env), self.W[m].shape), -CL, CL)
                novas_S[k].append(np.ascontiguousarray(s_out, dtype=np.float32))
        self.W = novos_W
        if PERTURBACAO['eps'] > 0.0:
            self.W = [(w * fatores_de_perturbacao(PERTURBACAO['semente'], self.t, m, w.size, PERTURBACAO['eps']).reshape(w.shape)).astype(np.float32) for m, w in enumerate(self.W)]
        for k in self.S_vivas:
            self.S[k] = novas_S[k]
        if self.U_vivas or self.tem_guarda:
            self._unidades(apre, a_l, p, msgs, t_n, g1, g2)
        if self.G_vivas:
            wnorm = np.float32(np.mean([np.abs(w).mean() for w in self.W]))
            ativas = np.float32(np.mean([m_.mean() for m_ in self.mask]))
            envg = [np.float32(0.0), np.float32(1.0), np.float32(perda_ex.mean()), np.float32(acerto), np.float32(enorm_ex.mean()), np.float32(conf_ex.mean()), g1, g2, t_n, wnorm, ativas]
            for k in self.G_vivas:
                self.G[k] = np.float32(np.clip(float(pl[f'G{k}'].rodar(envg).reshape(-1)[0]), -CL, CL))
        self.age = [a + 1.0 for a in self.age]
        self.t += 1
        self.diag['passos'] += 1
        if self.tem_guarda and self.t % self.cada == 0:
            self._acoes(t_n, g1, g2)

    def _estatisticas_de_unidade(self, l, apre, a_l, p, msgs):
        a_pos = a_l[l] if l < self.nl else p
        m_pos = msgs[l]
        post = a_pos.mean(axis=0)[None, :]
        post2 = (a_pos * a_pos).mean(axis=0)[None, :]
        err = m_pos.mean(axis=0)[None, :]
        err2 = (m_pos * m_pos).mean(axis=0)[None, :]
        inn = np.abs(self.W[l][:-1]).mean(axis=0)[None, :]
        outn = np.abs(self.W[l + 1][:-1]).mean(axis=1)[None, :] if l < self.nl else np.zeros((1, self.dims[l + 1]), np.float32)
        return (post, post2, err, err2, inn, outn)

    def _unidades(self, apre, a_l, p, msgs, t_n, g1, g2):
        for k in self.U_vivas:
            novas = []
            for l in range(self.nm):
                post, post2, err, err2, inn, outn = self._estatisticas_de_unidade(l, apre, a_l, p, msgs)
                u1 = self.U[1][l] if 1 in self.U else np.float32(0.0)
                u2 = self.U[2][l] if 2 in self.U else np.float32(0.0)
                idade = (np.log1p(self.age[l]) / 12.0)[None, :].astype(np.float32)
                env = [np.float32(0.0), np.float32(1.0), post, post2, err, err2, inn, outn, u1, u2, idade, g1, g2, t_n]
                novas.append(np.clip(np.broadcast_to(self.planos[f'U{k}'].rodar(env), (1, self.dims[l + 1])), -CL, CL).astype(np.float32))
            self.U[k] = novas
        self._ultimo = (apre, a_l, p, msgs)

    def _acoes(self, t_n, g1, g2):
        pl = self.planos
        apre, a_l, p, msgs = getattr(self, '_ultimo', (None, None, None, None))
        if apre is None:
            return
        for l in range(self.nl):
            post, post2, err, err2, inn, outn = self._estatisticas_de_unidade(l, apre, a_l, p, msgs)
            u1 = self.U[1][l] if 1 in self.U else np.float32(0.0)
            u2 = self.U[2][l] if 2 in self.U else np.float32(0.0)
            idade = (np.log1p(self.age[l]) / 12.0)[None, :].astype(np.float32)
            env = [np.float32(0.0), np.float32(1.0), post, post2, err, err2, inn, outn, u1, u2, idade, g1, g2, t_n]
            n = self.h[l]
            ativa = self.mask[l] > 0
            if pl['LIBERA'] is not None:
                g = np.broadcast_to(pl['LIBERA'].rodar(env), (1, n))[0] > 0
                sai = g & ativa
                if ativa.sum() - sai.sum() < 4:
                    idx = np.flatnonzero(sai)
                    sai[:] = False
                    sai[idx[:max(0, int(ativa.sum()) - 4)]] = True
                if sai.any():
                    self._zerar_unidade(l, sai)
                    self.mask[l][sai] = 0.0
                    self.diag['liberadas'] += int(sai.sum())
                    ativa = self.mask[l] > 0
            if pl['REINIT'] is not None:
                g = np.broadcast_to(pl['REINIT'].rodar(env), (1, n))[0] > 0
                renasce = g & ativa & (self.age[l] >= MATURIDADE)
                if renasce.any():
                    self._renascer(l, renasce)
                    self.diag['renascidas'] += int(renasce.sum())
            if pl['ATIVA'] is not None:
                g = np.broadcast_to(pl['ATIVA'].rodar(env), (1, n))[0] > 0
                entra = g & ~ativa
                if entra.any():
                    self.mask[l][entra] = 1.0
                    self._renascer(l, entra)
                    self.diag['ativadas'] += int(entra.sum())

    def _zerar_unidade(self, l, sel):
        self.W[l][:, sel] = 0.0
        if l + 1 < self.nm:
            self.W[l + 1][:-1][sel, :] = 0.0

    def _renascer(self, l, sel):
        n_in = self.dims[l]
        fan = max(1.0, float(self.conn[l][:-1].sum(axis=0).mean()))
        novos = self.r.normal(0.0, float(self.T['escala_init']) / math.sqrt(fan), (n_in + 1, int(sel.sum()))).astype(np.float32)
        novos[-1] = 0.0
        self.W[l][:, sel] = novos * self.conn[l][:, sel]
        if l + 1 < self.nm:
            self.W[l + 1][:-1][sel, :] = 0.0
        for k in self.S_vivas:
            self.S[k][l][:, sel] = self._init_S(self.T[f'init_S{k}'], l)[:, sel]
            if l + 1 < self.nm:
                self.S[k][l + 1][:-1][sel, :] = self._init_S(self.T[f'init_S{k}'], l + 1)[:-1][sel, :]
        for k in self.U_vivas:
            self.U[k][l][:, sel] = self._init_U(self.T[f'init_U{k}'], self.dims[l + 1])[:, sel]
        self.age[l][sel] = 0.0

    def prever(self, X):
        with np.errstate(all='ignore'):
            return self._prever(X)

    def _prever(self, X):
        X = np.asarray(X, np.float32)
        apre, s_l, a_l, z = self._frente(X)
        p = _softmax(z)
        classes = np.argmax(z, axis=1)
        pl = self.planos
        Bn = X.shape[0]
        ordenado = np.sort(p, axis=1)
        conf = ordenado[:, -1:]
        marg = ordenado[:, -1:] - ordenado[:, -2:-1]
        ent = (-(p * np.log(np.maximum(p, 1e-09))).sum(axis=1, keepdims=True) / math.log(self.c)).astype(np.float32)
        z2 = ((X - self.mu) ** 2 / (self.var + 1e-06)).mean(axis=1, keepdims=True)
        nov = (np.log1p(z2) / 3.0).astype(np.float32)
        t_n = np.float32(math.log1p(self.t) / 12.0)
        g1 = self.G.get(1, np.float32(0.0))
        g2 = self.G.get(2, np.float32(0.0))
        env = [np.float32(0.0), np.float32(1.0), conf.astype(np.float32), marg.astype(np.float32), ent, nov, g1, g2, t_n]
        etiquetas = np.full(Bn, int(self.T['pol_padrao']), np.int8)
        decidido = np.zeros(Bn, bool)
        for nome in ('POL1', 'POL2', 'POL3'):
            if pl[nome] is None:
                continue
            cond = np.broadcast_to(pl[nome].rodar(env), (Bn, 1))[:, 0] > 0
            novo = cond & ~decidido
            etiquetas[novo] = self.rotulos[nome]
            decidido |= cond
        return (classes.astype(np.int64), etiquetas)

    def flops_por_interacao(self):
        dims = [self.d] + [int(m.sum()) for m in self.mask] + [self.c]
        B = max(int(self.B), 1)
        pl = self.planos
        nos = lambda n: 0 if pl[n] is None else len(pl[n].nos)
        total = sum((2 * (dims[m] + 1) * dims[m + 1] for m in range(self.nm)))
        termos = len(self.lidas_peso & {'P', 'Q', 'P2', 'Q2'})
        if pl['RETRO'] is not None:
            for l in range(self.nl):
                total += 2 * dims[l + 2] * dims[l + 1] + nos('RETRO') * dims[l + 1] / B
        for m in range(self.nm):
            el = (dims[m] + 1) * dims[m + 1]
            regra = 'W_SAIDA' if m == self.nm - 1 else 'W_OCULTA'
            total += 2 * termos * el
            total += el * (nos(regra) + sum((nos(f'S{k}') for k in (1, 2, 3)))) / B
        n_unid = sum(dims[1:])
        total += n_unid * (nos('U1') + nos('U2')) / B + (nos('G1') + nos('G2')) / B
        if self.tem_guarda:
            total += n_unid * (nos('REINIT') + nos('ATIVA') + nos('LIBERA')) / (B * max(int(self.cada), 1))
        return float(total)

    def diagnostico(self):
        d = dict(self.diag)
        d['unidades_ativas'] = [int(m.sum()) for m in self.mask]
        d['exemplos_guardados'] = len(self.bx)
        return d

    def estado(self):
        from experimentos import l_ser_lang as LL
        bits = LL.codificar_programa(self.prog)
        return _empacotar({'bits': np.packbits(bits), 'W': self.W, 'conn': [np.packbits(c.astype(np.uint8)) for c in self.conn], 'formas': [list(c.shape) for c in self.conn], 'mask': self.mask, 'age': self.age, 'S': {str(k): v for k, v in self.S.items()}, 'U': {str(k): v for k, v in self.U.items()}, 'G': {str(k): float(v) for k, v in self.G.items()}, 't': self.t, 'mu': self.mu, 'var': self.var, 'bx': np.stack(self.bx) if self.bx else np.zeros((0, self.d), np.float32), 'by': np.stack(self.by) if self.by else np.zeros((0, self.c), np.float32), 'diag': self.diag, 'rng': self.r.bit_generator.state})

    @staticmethod
    def restaurar(b, d, c):
        o = _desempacotar(b)
        prog = L.decodificar_bits(np.unpackbits(o['bits'])[:L.N_BITS])
        a = AprendizSer(d, c, None, prog, restaurando=True)
        a.r = np.random.default_rng(0)
        a.r.bit_generator.state = o['rng']
        a.W = [np.asarray(w, np.float32) for w in o['W']]
        a.conn = [np.unpackbits(cn)[:int(np.prod(f))].reshape(f).astype(bool) for cn, f in zip(o['conn'], o['formas'])]
        a.mask = [np.asarray(m, np.float32) for m in o['mask']]
        a.age = [np.asarray(x, np.float32) for x in o['age']]
        a.S = {int(k): [np.asarray(x, np.float32) for x in v] for k, v in o['S'].items()}
        a.U = {int(k): [np.asarray(x, np.float32) for x in v] for k, v in o['U'].items()}
        a.G = {int(k): np.float32(v) for k, v in o['G'].items()}
        a.t = int(o['t'])
        a.mu, a.var = (np.asarray(o['mu'], np.float32), np.asarray(o['var'], np.float32))
        a.bx = [x for x in np.asarray(o['bx'], np.float32)]
        a.by = [x for x in np.asarray(o['by'], np.float32).reshape(-1, c)]
        a.diag = dict(o['diag'])
        return a

def fabricar(bits):
    prog = L.decodificar_bits(bits)
    return (lambda d, c, r: AprendizSer(d, c, r, prog), lambda b, d, c: AprendizSer.restaurar(b, d, c))
