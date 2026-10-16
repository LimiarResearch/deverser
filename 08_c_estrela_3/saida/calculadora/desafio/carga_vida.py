# -*- coding: utf-8 -*-
import numpy as np
D_ENTRADA, CLASSES, OCULTA_PROF = (20, 4, 16)
BASE, PARES = (12, ((0, 1), (2, 3), (4, 5)))
REFUTADAS = (6, 7, 8)
FLUXOS, SONDA_A_CADA, TESTE, INTERROMPER_A_CADA, COMPOSTA_N = (2, 1000, 48, 8000, 150)
D_CONTEXTO, CONTEXTO_ESC, CONTEXTO_RUIDO = (4, 2.0, 0.5)

def _prof(r, mu=None):
    esc = r.uniform(0.8, 1.6)
    return {'W1': r.normal(0, esc, (D_ENTRADA, OCULTA_PROF)), 'b1': r.normal(0, 0.3, OCULTA_PROF), 'W2': r.normal(0, 1.0, (OCULTA_PROF, CLASSES)), 'b2': r.normal(0, 0.7, CLASSES), 'mu': r.normal(0, 0.8, D_ENTRADA) if mu is None else mu}

def _rot(p, x):
    return np.argmax(np.tanh(x @ p['W1'] + p['b1']) @ p['W2'] + p['b2'], axis=1)

def _x(p, r, n):
    return (r.normal(0, 1, (n, D_ENTRADA)) + p['mu']).astype(np.float32)

def _fresco(x, y, xt, yt, semente, oculta=64, lr=0.05):
    r = np.random.default_rng(semente)
    W1 = r.normal(0, 1 / np.sqrt(x.shape[1]), (x.shape[1], oculta)).astype(np.float32)
    b1 = np.zeros(oculta, np.float32)
    W2 = r.normal(0, 1 / np.sqrt(oculta), (oculta, CLASSES)).astype(np.float32)
    b2 = np.zeros(CLASSES, np.float32)
    for i in range(len(x)):
        h = np.maximum(0, x[i] @ W1 + b1)
        z = h @ W2 + b2
        p = np.exp(z - z.max())
        p /= p.sum()
        g = p.copy()
        g[y[i]] -= 1
        gh = W2 @ g * (h > 0)
        W2 -= lr * np.outer(h, g)
        b2 -= lr * g
        W1 -= lr * np.outer(x[i], gh)
        b1 -= lr * gh
    return float(np.mean(np.argmax(np.maximum(0, xt @ W1 + b1) @ W2 + b2, axis=1) == yt))

def _leitor(eventos, registro):
    pos = {'i': 0}
    registro['aberturas'] += 1

    def proximo():
        i = pos['i']
        if i >= len(eventos):
            if i == len(eventos):
                pos['i'] += 1
                registro['completos'] += 1
            return None
        pos['i'] = i + 1
        ev = eventos[i]
        if ev[0] == 'treino':
            return ('treino', ev[1].copy(), int(ev[2]))
        if ev[0] == 'sonda':
            return ('sonda', ev[1].copy())
        return ('interromper',)
    return proximo

def _vida(semente):
    r = np.random.default_rng(semente)
    profs = []
    for t in range(BASE):
        par = next((a for a, b in PARES if b == t), None)
        profs.append(_prof(r, mu=profs[par]['mu'] if par is not None else None))
    nova = _prof(r)
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
            x = _x(profs[a], r, n)
            y = (_rot(profs[a], x) + _rot(profs[b], x)) % CLASSES
            ident = ('composta', t)
        elif tipo == 'nova':
            x = _x(nova, r, n)
            y = _rot(nova, x)
            ident = ('nova', 0)
        else:
            x = _x(profs[t], r, n)
            y = _rot(profs[t], x)
            if tipo == 'refutada' or t in refutada_desde:
                y = (y + 1) % CLASSES
            ident = ('base', t)
        if tipo == 'refutada':
            refutada_desde[t] = sum((len(v) for v in ys))
        cid = np.full(n, num(ident))
        trans = int(r.integers(0, 200)) if anterior is not None and tipo != 'composta' else 0
        if trans and anterior[0] == 'base':
            ta = anterior[1]
            xa = _x(profs[ta], r, trans)
            ya = _rot(profs[ta], xa)
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
        Xs.append(_x(profs[t], r, TESTE))
        ts += [t] * TESTE
    for c, (a, b) in enumerate(PARES):
        Xs.append(_x(profs[a], r, TESTE))
        ts += [BASE + 1 + c] * TESTE
    Xs.append(_x(nova, r, TESTE))
    ts += [BASE] * TESTE
    X_sonda, ts = (np.concatenate(Xs), np.array(ts))
    y_regra = np.zeros(len(ts), np.int64)
    for t in range(BASE):
        y_regra[ts == t] = _rot(profs[t], X_sonda[ts == t])
    for c, (a, b) in enumerate(PARES):
        m = ts == BASE + 1 + c
        y_regra[m] = (_rot(profs[a], X_sonda[m]) + _rot(profs[b], X_sonda[m])) % CLASSES
    y_regra[ts == BASE] = _rot(nova, X_sonda[ts == BASE])
    dist = []
    for c, (a, b) in enumerate(PARES):
        g = [a, b, BASE + 1 + c]
        m = np.isin(ts, g)
        cx = CTX[ts[m]] + rc.normal(0, CONTEXTO_RUIDO, (int(m.sum()), D_CONTEXTO))
        pred = np.array(g)[np.argmin(((cx[:, None, :] - CTX[g][None]) ** 2).sum(2), 1)]
        Xc = _x(profs[a], rc, 4000)
        ya, yb = (_rot(profs[a], Xc), _rot(profs[b], Xc))
        M = np.stack([(ya == k).astype(int) + (yb == k) + ((ya + yb) % CLASSES == k) for k in range(CLASSES)], 1).max(1)
        dist.append({'grupo': g, 'separacao_por_contexto': float(np.mean(pred == ts[m])), 'teto_sem_contexto': float(M.mean() / 3)})
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
    ref_nova = float(np.mean([_fresco(x[mn], y[mn], X_sonda[ts == BASE], y_regra[ts == BASE], semente + 11 * j) for j in range(3)]))
    ref_comp = {}
    for c in range(len(PARES)):
        mc = tarefa == BASE + 1 + c
        ref_comp[BASE + 1 + c] = float(np.mean([_fresco(x[mc], y[mc], X_sonda[ts == BASE + 1 + c], y_regra[ts == BASE + 1 + c], semente + 13 * j) for j in range(3)]))
    registro = {'aberturas': 0, 'completos': 0}
    aval = {'tarefa_sonda': ts, 'verdade': np.array(verdade, np.int64), 'sondas_em': sondas_em, 'interromper_em': interr_em, 'tarefa': tarefa, 'inicio': ini, 'majoritaria': maj, 'refutada_desde': refutada_desde, 'ref_nova': ref_nova, 'ref_composta': ref_comp, 'segmentos': tipo_da, 'registro': registro, 'base': BASE, 'compostas': [BASE + 1 + c for c in range(len(PARES))], 'distinguibilidade': dist}
    return {'abrir': lambda: _leitor(eventos, registro), '_avaliacao': aval}

class _Cofre:

    def __init__(self, dados):
        self.__dict__['_dados'] = dados
        self.__dict__['lido'] = False

    def __getitem__(self, k):
        self.__dict__['lido'] = True
        return self.__dict__['_dados'][k]

    def __getattr__(self, k):
        self.__dict__['lido'] = True
        raise AttributeError(k)

    def abrir(self):
        return self.__dict__['_dados']

def gerar_carga(semente):
    fluxos = [_vida(1000 * semente + k) for k in range(FLUXOS)]
    for f in fluxos:
        f['_avaliacao'] = _Cofre(f['_avaliacao'])
    return {'fluxos': fluxos, 'classes': CLASSES, 'd_entrada': D_ENTRADA + D_CONTEXTO, 'orcamento_bytes': 65536}
