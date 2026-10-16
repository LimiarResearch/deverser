# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
import carga_vida as CV
CLASSES = CV.CLASSES

class MundoDeSequencias:
    nome = 'sequencias'
    d_base = CV.D_ENTRADA
    base = CV.BASE
    pares = CV.PARES
    refutadas = CV.REFUTADAS

    @staticmethod
    def perfil(r, compartilhado=None):
        return CV._prof(r, mu=compartilhado)

    @staticmethod
    def compartilhar(perfil):
        return perfil['mu']

    @staticmethod
    def amostrar(perfil, r, n):
        return CV._x(perfil, r, n)

    @staticmethod
    def rotular(perfil, x):
        return CV._rot(perfil, x)

class MundoDeLinguagem:
    nome = 'linguagem'
    ALFABETO = 6
    JANELA = 8
    DISTANCIAS = (1, 2, 3, 4, 5, 6)
    base = CV.BASE
    pares = CV.PARES
    refutadas = CV.REFUTADAS

    @property
    def d_base(self):
        return self.ALFABETO * self.JANELA

    def perfil(self, r, compartilhado=None):
        A, W = (self.ALFABETO, self.JANELA)
        if compartilhado is None:
            dial = r.dirichlet(np.full(A, 0.7), size=W)
        else:
            dial = compartilhado
        delta = int(r.choice(self.DISTANCIAS))
        i = int(r.integers(0, W - delta))
        return {'dial': dial, 'i': i, 'j': i + delta, 'T1': r.integers(0, CLASSES, A), 'T2': r.integers(0, CLASSES, A)}

    @staticmethod
    def compartilhar(perfil):
        return perfil['dial']

    def amostrar(self, perfil, r, n):
        A, W = (self.ALFABETO, self.JANELA)
        acum = np.cumsum(perfil['dial'], axis=1)
        u = r.random((n, W))
        simbolos = (u[:, :, None] > acum[None, :, :-1]).sum(axis=2)
        x = np.zeros((n, W, A), np.float32)
        x[np.arange(n)[:, None], np.arange(W)[None, :], simbolos] = 1.0
        return x.reshape(n, W * A)

    def simbolos(self, x):
        return np.asarray(x).reshape(len(x), self.JANELA, self.ALFABETO).argmax(axis=2)

    def rotular(self, perfil, x):
        s = self.simbolos(x)
        return (perfil['T1'][s[:, perfil['i']]] + perfil['T2'][s[:, perfil['j']]]) % CLASSES

class MundoDeSequenciasFundo(MundoDeSequencias):
    nome = 'sequencias_fundo'
    base = 16
    pares = ((0, 1), (2, 3), (4, 5), (6, 7))
    refutadas = (8, 9, 10)

    @staticmethod
    def perfil(r, compartilhado=None):
        esc = r.uniform(0.8, 1.6)
        D, H = (CV.D_ENTRADA, CV.OCULTA_PROF)
        return {'W1': r.normal(0, esc, (D, H)), 'b1': r.normal(0, 0.3, H), 'Wm': r.normal(0, 1.5 / np.sqrt(H), (H, H)), 'bm': r.normal(0, 0.3, H), 'W2': r.normal(0, 1.0, (H, CLASSES)), 'b2': r.normal(0, 0.7, CLASSES), 'mu': r.normal(0, 0.8, D) if compartilhado is None else compartilhado}

    @staticmethod
    def rotular(perfil, x):
        h = np.tanh(x @ perfil['W1'] + perfil['b1'])
        h = np.tanh(h @ perfil['Wm'] + perfil['bm'])
        return np.argmax(h @ perfil['W2'] + perfil['b2'], axis=1)

class MundoDeLinguagemTres(MundoDeLinguagem):
    nome = 'linguagem_tres'
    ALFABETO = 8

    def perfil(self, r, compartilhado=None):
        A, W = (self.ALFABETO, self.JANELA)
        dial = r.dirichlet(np.full(A, 0.7), size=W) if compartilhado is None else compartilhado
        pos = sorted((int(p) for p in r.choice(W, 3, replace=False)))
        return {'dial': dial, 'pos': pos, 'T1': r.integers(0, CLASSES, A), 'T2': r.integers(0, CLASSES, A), 'T3': r.integers(0, CLASSES, A)}

    def rotular(self, perfil, x):
        s = self.simbolos(x)
        i, j, k = perfil['pos']
        return (perfil['T1'][s[:, i]] + perfil['T2'][s[:, j]] + perfil['T3'][s[:, k]]) % CLASSES
D_CONTEXTO, CONTEXTO_ESC, CONTEXTO_RUIDO = (CV.D_CONTEXTO, CV.CONTEXTO_ESC, CV.CONTEXTO_RUIDO)
SONDA_A_CADA, TESTE, INTERROMPER_A_CADA, COMPOSTA_N = (CV.SONDA_A_CADA, CV.TESTE, CV.INTERROMPER_A_CADA, CV.COMPOSTA_N)

def gerar_vida(mundo, semente):
    M = mundo
    BASE, PARES, REFUTADAS = (M.base, M.pares, M.refutadas)
    r = np.random.default_rng(semente)
    profs = []
    for t in range(BASE):
        par = next((a for a, b in PARES if b == t), None)
        profs.append(M.perfil(r, M.compartilhar(profs[par]) if par is not None else None))
    nova = M.perfil(r)
    rc = np.random.default_rng(semente + 7777)
    CTX = rc.normal(0, CONTEXTO_ESC, (BASE + 1 + len(PARES), D_CONTEXTO))
    num = lambda v: BASE + 1 + v[1] if v[0] == 'composta' else BASE if v[0] == 'nova' else v[1]
    ordem = []
    for _ in range(6):
        ordem += list(r.permutation(BASE))
    vistas, ordem2, comp_feitas, ref_feitas = ({}, [], set(), set())
    for k, t in enumerate(ordem):
        ordem2.append(('base', int(t)))
        vistas[int(t)] = vistas.get(int(t), 0) + 1
        for c, (a, b) in enumerate(PARES):
            if c not in comp_feitas and vistas.get(a, 0) >= 2 and (vistas.get(b, 0) >= 2) and (r.random() < 0.5):
                ordem2.append(('composta', c))
                comp_feitas.add(c)
        if k > len(ordem) // 2:
            for t2 in REFUTADAS:
                if t2 not in ref_feitas and r.random() < 0.08:
                    ordem2.append(('refutada', t2))
                    ref_feitas.add(t2)
    ordem2 += [('composta', c) for c in range(len(PARES)) if c not in comp_feitas]
    ordem2 += [('refutada', t) for t in REFUTADAS if t not in ref_feitas]
    ordem2.append(('nova', BASE))
    xs, ys, rotulo_da, tipo_da, cids = ([], [], [], [], [])
    refutada_desde = {}
    anterior = None
    for tipo, t in ordem2:
        n = COMPOSTA_N if tipo == 'composta' else int(r.integers(300, 900))
        if tipo == 'composta':
            a, b = PARES[t]
            x = M.amostrar(profs[a], r, n)
            y = (M.rotular(profs[a], x) + M.rotular(profs[b], x)) % CLASSES
            ident = ('composta', t)
        elif tipo == 'nova':
            x = M.amostrar(nova, r, n)
            y = M.rotular(nova, x)
            ident = ('nova', 0)
        else:
            x = M.amostrar(profs[t], r, n)
            y = M.rotular(profs[t], x)
            if tipo == 'refutada' or t in refutada_desde:
                y = (y + 1) % CLASSES
            ident = ('base', t)
        if tipo == 'refutada':
            refutada_desde[t] = sum((len(v) for v in ys))
        cid = np.full(n, num(ident))
        trans = int(r.integers(0, 200)) if anterior is not None and tipo != 'composta' else 0
        if trans and anterior[0] == 'base':
            ta = anterior[1]
            xa = M.amostrar(profs[ta], r, trans)
            ya = M.rotular(profs[ta], xa)
            if ta in refutada_desde:
                ya = (ya + 1) % CLASSES
            velho = r.random(trans) < np.linspace(1, 0, trans)
            x[:trans][velho], y[:trans][velho] = (xa[velho], ya[velho])
            cid[:trans][velho] = num(anterior)
        xs.append(x)
        ys.append(y.astype(np.int64))
        cids.append(cid)
        rotulo_da += [ident] * n
        tipo_da.append((tipo, t, n))
        anterior = ident
    x, y = (np.concatenate(xs), np.concatenate(ys))
    N = len(y)
    cid = np.concatenate(cids)
    x = np.hstack([x, CTX[cid] + rc.normal(0, CONTEXTO_RUIDO, (N, D_CONTEXTO))]).astype(np.float32)
    Xs, ts = ([], [])
    for t in range(BASE):
        Xs.append(M.amostrar(profs[t], r, TESTE))
        ts += [t] * TESTE
    for c, (a, b) in enumerate(PARES):
        Xs.append(M.amostrar(profs[a], r, TESTE))
        ts += [BASE + 1 + c] * TESTE
    Xs.append(M.amostrar(nova, r, TESTE))
    ts += [BASE] * TESTE
    X_sonda, ts = (np.concatenate(Xs), np.array(ts))
    y_regra = np.zeros(len(ts), np.int64)
    for t in range(BASE):
        y_regra[ts == t] = M.rotular(profs[t], X_sonda[ts == t])
    for c, (a, b) in enumerate(PARES):
        m = ts == BASE + 1 + c
        y_regra[m] = (M.rotular(profs[a], X_sonda[m]) + M.rotular(profs[b], X_sonda[m])) % CLASSES
    y_regra[ts == BASE] = M.rotular(nova, X_sonda[ts == BASE])
    dist = []
    for c, (a, b) in enumerate(PARES):
        g = [a, b, BASE + 1 + c]
        m = np.isin(ts, g)
        cx = CTX[ts[m]] + rc.normal(0, CONTEXTO_RUIDO, (int(m.sum()), D_CONTEXTO))
        pred = np.array(g)[np.argmin(((cx[:, None, :] - CTX[g][None]) ** 2).sum(2), 1)]
        Xc = M.amostrar(profs[a], rc, 4000)
        ya, yb = (M.rotular(profs[a], Xc), M.rotular(profs[b], Xc))
        Mx = np.stack([(ya == k).astype(int) + (yb == k) + ((ya + yb) % CLASSES == k) for k in range(CLASSES)], 1).max(1)
        dist.append({'grupo': g, 'separacao_por_contexto': float(np.mean(pred == ts[m])), 'teto_sem_contexto': float(Mx.mean() / 3)})
    X_sonda = np.hstack([X_sonda, CTX[ts] + rc.normal(0, CONTEXTO_RUIDO, (len(ts), D_CONTEXTO))]).astype(np.float32)
    emb = r.permutation(len(ts))
    X_sonda, ts, y_regra = (X_sonda[emb], ts[emb], y_regra[emb])
    eventos, sondas_em, verdade, interr_em = ([], [], [], [])
    for i in range(N):
        eventos.append(('treino', x[i], int(y[i])))
        if (i + 1) % INTERROMPER_A_CADA == 0 and i + 1 < N:
            eventos.append(('interromper',))
            interr_em.append(i)
        if (i + 1) % SONDA_A_CADA == 0 or i == N - 1:
            eventos.append(('sonda', X_sonda))
            sondas_em.append(i)
            v = y_regra.copy()
            for t, desde in refutada_desde.items():
                if i >= desde:
                    v[ts == t] = (v[ts == t] + 1) % CLASSES
            verdade.append(v)
    tarefa = np.array([BASE + 1 + v[1] if v[0] == 'composta' else BASE if v[0] == 'nova' else v[1] for v in rotulo_da])
    ini = {int(t): int(np.flatnonzero(tarefa == t)[0]) for t in np.unique(tarefa)}
    maj = {int(t): float(np.bincount(y_regra[ts == t], minlength=CLASSES).max() / TESTE) for t in np.unique(ts)}
    mn = tarefa == BASE
    ref_nova = float(np.mean([CV._fresco(x[mn], y[mn], X_sonda[ts == BASE], y_regra[ts == BASE], semente + 11 * j) for j in range(3)]))
    ref_comp = {}
    for c in range(len(PARES)):
        mc = tarefa == BASE + 1 + c
        ref_comp[BASE + 1 + c] = float(np.mean([CV._fresco(x[mc], y[mc], X_sonda[ts == BASE + 1 + c], y_regra[ts == BASE + 1 + c], semente + 13 * j) for j in range(3)]))
    registro = {'aberturas': 0, 'completos': 0}
    aval = {'tarefa_sonda': ts, 'verdade': np.array(verdade, np.int64), 'sondas_em': sondas_em, 'interromper_em': interr_em, 'tarefa': tarefa, 'inicio': ini, 'majoritaria': maj, 'refutada_desde': refutada_desde, 'ref_nova': ref_nova, 'ref_composta': ref_comp, 'segmentos': tipo_da, 'registro': registro, 'base': BASE, 'compostas': [BASE + 1 + c for c in range(len(PARES))], 'distinguibilidade': dist}
    return {'abrir': lambda: CV._leitor(eventos, registro), '_avaliacao': aval}

def gerar_carga(mundo, semente, fluxos=2):
    vidas = [gerar_vida(mundo, 1000 * semente + k) for k in range(fluxos)]
    for v in vidas:
        v['_avaliacao'] = CV._Cofre(v['_avaliacao'])
    return {'fluxos': vidas, 'classes': CLASSES, 'd_entrada': mundo.d_base + D_CONTEXTO, 'orcamento_bytes': 65536}
