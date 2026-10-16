# -*- coding: utf-8 -*-
import json
import math
import os
import zipfile
import numpy as np
FRACAO_CEGA = 0.25
CLIP_PESO = 5.0
N_CARACTERISTICAS = 20

def niveis(n, prefixo, rede):
    ultimo = [0] * n
    for i, j in prefixo:
        ultimo[i] = ultimo[j] = max(ultimo[i], ultimo[j]) + 1
    nv = []
    for i, j in rede:
        t = max(ultimo[i], ultimo[j]) + 1
        ultimo[i] = ultimo[j] = t
        nv.append(t)
    return (nv, max(ultimo))

def caracteristicas(n, prefixo, rede, f_del, vetores):
    m = len(rede)
    f = np.asarray(f_del, float)
    nv, prof = niveis(n, prefixo, rede)
    ordem = np.argsort(np.argsort(f, kind='stable'), kind='stable')
    fmin, fmax, fmedia = (float(f.min()), float(f.max()), float(f.mean()))
    ultimo_do_fio = {}
    for p, (i, j) in enumerate(rede):
        ultimo_do_fio[i] = p
        ultimo_do_fio[j] = p
    depois = np.zeros(m)
    for p, (i, j) in enumerate(rede):
        depois[p] = sum((1 for q in range(p + 1, m) if rede[q][0] in (i, j) or rede[q][1] in (i, j)))
    X = np.zeros((m, N_CARACTERISTICAS), np.float32)
    for p, (i, j) in enumerate(rede):
        X[p] = [f[p] / vetores, math.log1p(f[p]) / 8.0, ordem[p] / max(m - 1, 1), (f[p] - fmin) / (fmax - fmin + 1e-09), 1.0 if f[p] == fmin else 0.0, p / max(m - 1, 1), nv[p] / max(prof, 1), i / max(n - 1, 1), j / max(n - 1, 1), (j - i) / max(n - 1, 1), depois[p] / max(m, 1), 1.0 if ultimo_do_fio[i] == p else 0.0, 1.0 if ultimo_do_fio[j] == p else 0.0, n / 32.0, m / 100.0, prof / 20.0, math.log10(max(vetores, 1)) / 5.0, fmin / vetores, (fmedia - fmin) / vetores, len(prefixo) / 100.0]
    return X

class _Foto:

    def __init__(self, mem, reservar=0.0):
        ext = mem.externo
        self.n_proprio = len(mem.y)
        self.X, self.y, self.w, self.sup = (mem.X, mem.y, mem.w, mem.sup)
        if ext is not None and len(ext[1]):
            self.X, self.y = (np.concatenate([mem.X, ext[0]]), np.concatenate([mem.y, ext[1]]))
            self.w, self.sup = (np.concatenate([mem.w, ext[2]]), np.concatenate([mem.sup, ext[3]]))
        n = len(self.y)
        corte = int(self.n_proprio * (1.0 - reservar))
        self.reserva = np.arange(corte, self.n_proprio) if reservar > 0 else np.zeros(0, int)
        antigos = np.arange(0, int(self.n_proprio * 0.25))
        externos = np.arange(self.n_proprio, n)
        self.retencao = np.concatenate([antigos, externos]).astype(int)
        self.treino = np.concatenate([np.arange(0, corte), externos]).astype(int)
        self.consertos = self.treino[self.y[self.treino] == 0]
        s = self.sup[self.treino].astype(np.float64) + 0.1
        self.p_sup = s / s.sum() if len(s) else s

    def __len__(self):
        return len(self.y)

    def lote(self, quantos, g):
        if len(self.treino) == 0:
            return None
        k1 = min(len(self.consertos), quantos // 4)
        i1 = g.choice(self.consertos, k1, replace=False) if k1 else np.zeros(0, int)
        resto = quantos - k1
        k2 = resto // 2
        i2 = self.treino[g.choice(len(self.treino), k2, p=self.p_sup)] if k2 else np.zeros(0, int)
        i3 = self.treino[g.integers(0, len(self.treino), resto - k2)]
        idx = np.concatenate([i1, i2, i3]).astype(int)
        return (self.X[idx], self.y[idx], self.w[idx])

class Memoria:

    def __init__(self, teto=60000, semente=0, d=N_CARACTERISTICAS):
        self.teto = int(teto)
        self.d = int(d)
        self.g = np.random.default_rng(semente + 101)
        self.X = np.zeros((0, self.d), np.float32)
        self.y = np.zeros(0, np.float32)
        self.w = np.zeros(0, np.float32)
        self.prop = np.zeros(0, np.float32)
        self.cego = np.zeros(0, np.int8)
        self.n = np.zeros(0, np.int16)
        self.rod = np.zeros(0, np.int32)
        self.sup = np.zeros(0, np.float32)
        self.vistos = 0
        self.externo = None

    def __len__(self):
        return len(self.y) + (0 if self.externo is None else len(self.externo[1]))

    def proprios(self):
        return len(self.y)

    def adicionar(self, x, y, propensao, cego, n, rodada, m_opcoes, sup=1.0):
        peso = float(np.clip(1.0 / max(m_opcoes, 1) / max(propensao, 1e-09), 1.0 / CLIP_PESO, CLIP_PESO))
        self.vistos += 1
        if len(self.y) < self.teto:
            pos = len(self.y)
            for nome, val in (('X', x[None]), ('y', [y]), ('w', [peso]), ('prop', [propensao]), ('cego', [cego]), ('n', [n]), ('rod', [rodada]), ('sup', [sup])):
                arr = getattr(self, nome)
                setattr(self, nome, np.concatenate([arr, np.asarray(val, arr.dtype)]))
            return pos
        if y > 0:
            cand = np.flatnonzero(self.y > 0)
        elif (self.y == 0).sum() < self.teto // 2:
            cand = np.flatnonzero(self.y > 0)
        else:
            cand = np.flatnonzero(self.y == 0)
        if len(cand) == 0:
            return -1
        if self.g.random() > self.teto / self.vistos and y > 0:
            return -1
        pos = int(cand[self.g.integers(len(cand))])
        self.X[pos], self.y[pos], self.w[pos], self.prop[pos], self.cego[pos], self.n[pos], self.rod[pos], self.sup[pos] = (x, y, peso, propensao, cego, n, rodada, sup)
        return pos

    def instantaneo(self, reservar=0.0):
        return _Foto(self, reservar)

    def lote(self, quantos, g):
        if len(self) == 0:
            return None
        return self.instantaneo().lote(quantos, g)

    def importar(self, caminhos):
        Xs, ys, ws, ss = ([], [], [], [])
        for c in caminhos:
            try:
                z = np.load(c)
                if len(z['y']) == 0:
                    continue
                Xs.append(z['X'])
                ys.append(z['y'])
                ws.append(z['w'])
                ss.append(z['sup'] if 'sup' in z.files else np.ones(len(z['y']), np.float32))
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                continue
        if not Xs:
            self.externo = None
            return 0
        self.externo = (np.concatenate(Xs), np.concatenate(ys), np.concatenate(ws), np.concatenate(ss))
        return len(self.externo[1])

    def salvar(self, caminho):
        tmp = caminho + '.tmp.npz'
        np.savez_compressed(tmp, X=self.X, y=self.y, w=self.w, prop=self.prop, cego=self.cego, n=self.n, rod=self.rod, sup=self.sup, vistos=np.asarray([self.vistos]), teto=np.asarray([self.teto]))
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, teto=None, semente=0, d=N_CARACTERISTICAS):
        m = cls(teto=teto or 60000, semente=semente, d=d)
        if os.path.exists(caminho):
            z = np.load(caminho)
            m.X, m.y, m.w, m.prop, m.cego, m.n, m.rod = (z[k] for k in ('X', 'y', 'w', 'prop', 'cego', 'n', 'rod'))
            m.sup = z['sup'] if 'sup' in z.files else np.ones(len(m.y), np.float32)
            m.vistos = int(z['vistos'][0])
            m.teto = int(teto or z['teto'][0])
        return m

class Rede:

    def __init__(self, entrada, escondidas, semente, lr=0.01, l2=0.0):
        g = np.random.default_rng(semente)
        self.esc = tuple((int(x) for x in escondidas))
        self.lr, self.l2 = (float(lr), float(l2))
        dims = [entrada, *self.esc, 1]
        self.W = [g.normal(0, 1.0 / math.sqrt(dims[i]), (dims[i], dims[i + 1])).astype(np.float64) for i in range(len(dims) - 1)]
        self.b = [np.zeros(dims[i + 1]) for i in range(len(dims) - 1)]
        self._zerar_adam()

    def _zerar_adam(self):
        self._m = [np.zeros_like(w) for w in self.W] + [np.zeros_like(b) for b in self.b]
        self._v = [np.zeros_like(w) for w in self.W] + [np.zeros_like(b) for b in self.b]
        self._t = 0

    def prever(self, X):
        h = np.asarray(X, np.float64)
        for W, b in zip(self.W[:-1], self.b[:-1]):
            h = np.tanh(h @ W + b)
        return (h @ self.W[-1] + self.b[-1])[:, 0]

    def passo(self, X, y, w, lr=None):
        lr = self.lr if lr is None else lr
        X = np.asarray(X, np.float64)
        hs = [X]
        for W, b in zip(self.W[:-1], self.b[:-1]):
            hs.append(np.tanh(hs[-1] @ W + b))
        p = (hs[-1] @ self.W[-1] + self.b[-1])[:, 0]
        err = (p - y) * w
        g = err[:, None] / max(w.sum(), 1e-09)
        gW, gb = ([None] * len(self.W), [None] * len(self.b))
        for k in range(len(self.W) - 1, -1, -1):
            gW[k] = hs[k].T @ g
            gb[k] = g.sum(0)
            if k > 0:
                g = g @ self.W[k].T * (1 - hs[k] ** 2)
        grads = gW + gb
        self._t += 1
        params = self.W + self.b
        for i, (par, gr) in enumerate(zip(params, grads)):
            self._m[i] = 0.9 * self._m[i] + 0.1 * gr
            self._v[i] = 0.999 * self._v[i] + 0.001 * gr ** 2
            mh = self._m[i] / (1 - 0.9 ** self._t)
            vh = self._v[i] / (1 - 0.999 ** self._t)
            par -= lr * mh / (np.sqrt(vh) + 1e-08)
            if self.l2 and i < len(self.W):
                par -= lr * self.l2 * par
        return float((err * (p - y)).sum() / max(w.sum(), 1e-09))

    def copiar(self):
        r = Rede(self.W[0].shape[0], self.esc, 0, self.lr, self.l2)
        r.W = [w.copy() for w in self.W]
        r.b = [b.copy() for b in self.b]
        r._zerar_adam()
        return r

    def alargar(self, extra, g):
        k = len(self.W) - 2
        self.W[k] = np.concatenate([self.W[k], g.normal(0, 0.1, (self.W[k].shape[0], extra))], axis=1)
        self.b[k] = np.concatenate([self.b[k], np.zeros(extra)])
        self.W[k + 1] = np.concatenate([self.W[k + 1], np.zeros((extra, self.W[k + 1].shape[1]))], axis=0)
        self.esc = self.esc[:-1] + (self.esc[-1] + int(extra),)
        self._zerar_adam()

    def estado(self):
        return {'esc': list(self.esc), 'lr': self.lr, 'l2': self.l2, 'W': [w.tolist() for w in self.W], 'b': [b.tolist() for b in self.b]}

    @classmethod
    def de_estado(cls, e, entrada):
        r = cls(entrada, e['esc'], 0, e.get('lr', 0.01), e.get('l2', 0.0))
        r.W = [np.asarray(w) for w in e['W']]
        r.b = [np.asarray(b) for b in e['b']]
        r._zerar_adam()
        return r
ARQUITETURAS = ((16,), (32,), (32, 16), (64,), (64, 32))

class Conjunto:

    def __init__(self, memoria, membros=5, semente=0, entrada=N_CARACTERISTICAS):
        self.mem = memoria
        self.g = np.random.default_rng(semente + 7)
        self.entrada = entrada
        self.redes = [Rede(entrada, ARQUITETURAS[k % len(ARQUITETURAS)], semente * 100 + k) for k in range(membros)]
        self.degraus = []
        self.trocas = []
        self.passos = 0

    def prever_com(self, X, redes=None, degraus=None):
        redes = self.redes if redes is None else redes
        degraus = self.degraus if degraus is None else degraus
        P = np.stack([r.prever(X) for r in redes])
        mu, sd = (P.mean(0), P.std(0))
        X = np.asarray(X, np.float64)
        for d in degraus:
            mu = mu + d.prever(np.concatenate([X, mu[:, None], sd[:, None]], axis=1))
        return (mu, sd)

    def prever(self, X):
        return self.prever_com(X)

    def novo_degrau(self, escondidas, semente, lr=0.01, l2=0.0):
        d = Rede(self.entrada + 2, escondidas, semente, lr, l2)
        d.W[-1][:] = 0.0
        d.b[-1][:] = 0.0
        return d

    def treinar(self, passos=20, lote=256, lr=None):
        if len(self.mem) < 32:
            return
        foto = self.mem.instantaneo()
        for _ in range(passos):
            for r in self.redes:
                X, y, w = foto.lote(lote, self.g)
                r.passo(X, y, w, lr)
        self.passos += passos

    def atualizar_surpresas(self, quantos=2000):
        n = len(self.mem.y)
        if n == 0:
            return
        idx = self.g.integers(0, n, min(quantos, n))
        mu, _ = self.prever(self.mem.X[idx])
        self.mem.sup[idx] = np.abs(mu - self.mem.y[idx]).astype(np.float32)

    def erro(self, rede, X, y, w):
        p = rede.prever(X)
        return float((w * (p - y) ** 2).sum() / max(w.sum(), 1e-09))

    @staticmethod
    def porta_de_retencao(e_reserva_nova, e_reserva_atual, e_retencao_nova, e_retencao_atual, tolerancia=1.05):
        if not e_reserva_nova < e_reserva_atual:
            return (False, 'reserva')
        if not e_retencao_nova <= tolerancia * e_retencao_atual:
            return (False, 'retenção')
        return (True, '')

    def trocar_de_rede(self, candidatos=2, passos=150, lote=256, lr=0.01):
        foto = self.mem.instantaneo(reservar=0.2)
        n = len(foto)
        if n < 400 or len(foto.reserva) < 50 or len(foto.retencao) < 50:
            return None
        Xv, yv, wv = (foto.X[foto.reserva], foto.y[foto.reserva], foto.w[foto.reserva])
        Xr, yr, wr = (foto.X[foto.retencao], foto.y[foto.retencao], foto.w[foto.retencao])
        atuais = [self.erro(r, Xv, yv, wv) for r in self.redes]
        pior = int(np.argmax(atuais))
        ret_pior = self.erro(self.redes[pior], Xr, yr, wr)
        regs = []
        melhor, melhor_erro = (None, None)
        for c in range(candidatos):
            arq = ARQUITETURAS[int(self.g.integers(len(ARQUITETURAS)))]
            nova = Rede(self.entrada, arq, int(self.g.integers(1 << 30)))
            idx = foto.treino[self.g.integers(0, len(foto.treino), min(len(foto.treino), 2048))]
            mu, _ = self.prever(foto.X[idx])
            um = np.ones(len(idx))
            for _ in range(passos):
                j = self.g.integers(0, len(idx), lote)
                nova.passo(foto.X[idx][j], mu[j], um[j], lr)
            for _ in range(passos):
                X, y, w = foto.lote(lote, self.g)
                nova.passo(X, y, w, lr)
            e_res, e_ret = (self.erro(nova, Xv, yv, wv), self.erro(nova, Xr, yr, wr))
            entra, motivo = self.porta_de_retencao(e_res, atuais[pior], e_ret, ret_pior)
            regs.append({'arquitetura': list(arq), 'erro_na_reserva': round(e_res, 6), 'erro_na_retencao': round(e_ret, 6), 'passa_a_porta': entra, 'recusa': motivo})
            if entra and (melhor_erro is None or e_res < melhor_erro):
                melhor, melhor_erro = (nova, e_res)
        adotou = melhor is not None
        if adotou:
            self.redes[pior] = melhor
        reg = {'passos': self.passos, 'membro_substituido': pior, 'erro_do_pior_na_reserva': round(atuais[pior], 6), 'erro_do_pior_na_retencao': round(ret_pior, 6), 'candidatas': regs, 'adotou': adotou, 'exemplos': {'proprios': foto.n_proprio, 'externos': n - foto.n_proprio, 'reserva': len(foto.reserva), 'retencao': len(foto.retencao)}}
        self.trocas.append(reg)
        return reg

    def salvar(self, caminho):
        tmp = caminho + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'redes': [r.estado() for r in self.redes], 'degraus': [d.estado() for d in self.degraus], 'trocas': self.trocas, 'passos': self.passos}, f)
        os.replace(tmp, caminho)

    @classmethod
    def carregar(cls, caminho, memoria, semente=0):
        c = cls(memoria, membros=0, semente=semente)
        with open(caminho, encoding='utf-8') as f:
            e = json.load(f)
        c.redes = [Rede.de_estado(x, c.entrada) for x in e['redes']]
        c.degraus = [Rede.de_estado(x, c.entrada + 2) for x in e.get('degraus', [])]
        c.trocas, c.passos = (e.get('trocas', []), e.get('passos', 0))
        return c

def softmax_de_menor(notas, tau):
    z = -(np.asarray(notas, float) - np.min(notas)) / max(tau, 1e-06)
    e = np.exp(z - z.max())
    return e / e.sum()

def escolher(g, notas, tau=0.5, fracao_cega=FRACAO_CEGA):
    m = len(notas)
    p_guiada = softmax_de_menor(notas, tau)
    p = fracao_cega / m + (1 - fracao_cega) * p_guiada
    if g.random() < fracao_cega:
        i = int(g.integers(m))
        return (i, float(p[i]), True)
    i = int(g.choice(m, p=p_guiada))
    return (i, float(p[i]), False)
