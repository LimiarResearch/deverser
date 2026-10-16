# -*- coding: utf-8 -*-
import copy
import json
import math
import numpy as np
try:
    from .comum_vida import _desempacotar, _empacotar, _etiquetas_por_confianca, _rodar
except ImportError:
    from comum_vida import _desempacotar, _empacotar, _etiquetas_por_confianca, _rodar

def _f(pad, lo, hi, esc='lin'):
    return {'pad': pad, 't': 'f', 'lo': lo, 'hi': hi, 'esc': esc}

def _i(pad, lo, hi, esc='lin'):
    return {'pad': pad, 't': 'i', 'lo': lo, 'hi': hi, 'esc': esc}

def _c(pad, *opcoes):
    return {'pad': pad, 't': 'c', 'op': list(opcoes)}
TECIDO = {'ativacao': _c('relu', 'relu', 'tanh'), 'ativas0': _f(1.0, 0.25, 1.0), 'porta_entrada': _f(0.0, 0.0, 1.0), 'densidade': _f(1.0, 0.3, 1.0), 'semente': _i(0, 0, 9999)}
LARGURA = (8, 128)
OPS = {'sgd': {'lr': _f(0.05, 0.005, 0.3, 'log'), 'wd': _f(0.0, 0.0, 0.001), 'lote': _c(4, 1, 2, 4, 8, 16), 'clip': _f(10.0, 0.5, 50.0, 'log')}, 'utilidade': {'eta': _f(0.01, 0.001, 0.1, 'log'), 'tipo': _c('contrib', 'contrib', 'grad2', 'mix')}, 'fisher': {'beta': _f(0.02, 0.001, 0.1, 'log')}, 'ancora': {'gatilho': _c('mudanca', 'mudanca', 'cada'), 'cada': _i(2000, 100, 20000, 'log'), 'acumula': _f(1.0, 0.0, 1.0)}, 'penalidade': {'lam': _f(1.0, 0.01, 100.0, 'log'), 'usa_fisher': _c(1, 1, 0)}, 'repeticao': {'R': _i(128, 16, 1024, 'log'), 'precisao': _c('f32', 'f32', 'f16', 'i8'), 'q': _f(1.0, 0.25, 4.0, 'log'), 'insercao': _c('reservatorio', 'reservatorio', 'surpresa', 'balanceado'), 'amostragem': _c('uniforme', 'uniforme', 'perda')}, 'mudanca': {'rapida': _f(0.1, 0.02, 0.3, 'log'), 'lenta': _f(0.005, 0.001, 0.02, 'log'), 'limiar': _f(0.15, 0.02, 0.5, 'log'), 'folga': _i(200, 50, 2000, 'log')}, 'porta': {'m_min': _f(0.1, 0.0, 0.5), 'm_max': _f(1.5, 1.0, 5.0), 'c_u': _f(-1.5, -3.0, 3.0), 'c_a': _f(0.0, -3.0, 3.0), 'c_s': _f(1.0, -3.0, 3.0), 'vies': _f(0.5, -3.0, 3.0), 'k': _f(3.0, 1.0, 8.0), 'cada': _c(20, 5, 20, 50), 'idade_ref': _i(1000, 100, 5000, 'log')}, 'reinit': {'rho': _f(0.0001, 1e-05, 0.01, 'log'), 'maturidade': _i(100, 50, 5000, 'log'), 'cada': _c(1, 1, 5, 20), 'criterio': _c('utilidade', 'utilidade', 'aleatorio', 'idade')}, 'alocar': {'crescer': _c(1, 0, 1, 2, 4, 8), 'liberar': _f(0.0, 0.0, 0.2)}, 'podar': {'alvo': _f(0.3, 0.0, 0.8), 'cada': _i(1000, 200, 5000, 'log')}, 'perturbar': {'shrink': _f(0.9995, 0.99, 1.0), 'sigma': _f(0.001, 0.0, 0.01), 'cada': _i(10, 1, 100, 'log')}, 'lento': {'tau': _f(0.01, 0.001, 0.2, 'log'), 'mistura': _f(0.5, 0.0, 1.0)}}
ORDEM = ['sgd', 'repeticao', 'mudanca', 'utilidade', 'fisher', 'ancora', 'penalidade', 'porta', 'reinit', 'podar', 'perturbar', 'alocar', 'lento']

def _ajusta(spec, v):
    if spec['t'] == 'c':
        return v if v in spec['op'] else spec['pad']
    try:
        v = float(v)
    except (TypeError, ValueError):
        v = float(spec['pad'])
    v = min(max(v, spec['lo']), spec['hi'])
    return int(round(v)) if spec['t'] == 'i' else float(v)

def _padrao(nome):
    return {'op': nome, **{k: s['pad'] for k, s in OPS[nome].items()}}

def normalizar(prog):
    p = prog or {}
    T = dict(p.get('tecido') or {})
    cam = [int(min(max(int(h), LARGURA[0]), LARGURA[1])) for h in T.get('camadas') or [32]][:3] or [32]
    tec = {'camadas': cam}
    for k, spec in TECIDO.items():
        tec[k] = _ajusta(spec, T.get(k, spec['pad']))
    ops = {}
    for o in p.get('regra') or []:
        nome = o.get('op')
        if nome in OPS and nome not in ops:
            ops[nome] = {'op': nome, **{k: _ajusta(spec, o.get(k, spec['pad'])) for k, spec in OPS[nome].items()}}
    if 'sgd' not in ops:
        ops['sgd'] = _padrao('sgd')
    exige = []
    if 'penalidade' in ops:
        exige.append('ancora')
        if ops['penalidade']['usa_fisher'] == 1:
            exige.append('fisher')
    if 'fisher' in ops:
        exige.append('ancora')
    if 'ancora' in ops or 'ancora' in exige:
        if 'ancora' in ops and ops['ancora']['gatilho'] == 'mudanca':
            exige.append('mudanca')
        elif 'ancora' not in ops:
            ops['ancora'] = _padrao('ancora')
            if ops['ancora']['gatilho'] == 'mudanca':
                exige.append('mudanca')
    if 'porta' in ops or ('reinit' in ops and ops['reinit']['criterio'] == 'utilidade') or ('alocar' in ops and ops['alocar']['liberar'] > 0):
        exige.append('utilidade')
    if 'alocar' in ops and ops['alocar']['crescer'] > 0:
        exige.append('mudanca')
    for n in exige:
        if n not in ops:
            ops[n] = _padrao(n)
    return {'tecido': tec, 'regra': [ops[n] for n in ORDEM if n in ops]}

def canonico(prog):

    def arred(o):
        if isinstance(o, float):
            return float(f'{o:.4g}')
        if isinstance(o, dict):
            return {k: arred(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [arred(v) for v in o]
        return o
    return json.dumps(arred(normalizar(prog)), sort_keys=True)

def descrever(prog):
    p = normalizar(prog)
    t = p['tecido']
    partes = [f"{'-'.join((str(h) for h in t['camadas']))} {t['ativacao']}" + (f" ativas {t['ativas0']:.2f}" if t['ativas0'] < 1 else '') + (f" porta {t['porta_entrada']:.2f}" if t['porta_entrada'] > 0 else '') + (f" dens {t['densidade']:.2f}" if t['densidade'] < 1 else '')]
    for o in p['regra']:
        partes.append(o['op'] + '(' + ','.join((f'{k}={v:.3g}' if isinstance(v, float) else f'{k}={v}' for k, v in o.items() if k != 'op')) + ')')
    return ' + '.join(partes)

def _sorteia(spec, rng):
    if spec['t'] == 'c':
        return spec['op'][int(rng.integers(len(spec['op'])))]
    lo, hi = (spec['lo'], spec['hi'])
    v = math.exp(rng.uniform(math.log(lo), math.log(hi))) if spec.get('esc') == 'log' else rng.uniform(lo, hi)
    return int(round(v)) if spec['t'] == 'i' else float(v)

def _perturba(spec, v, rng, forca):
    if spec['t'] == 'c':
        return spec['op'][int(rng.integers(len(spec['op'])))] if rng.random() < 0.6 else v
    lo, hi = (spec['lo'], spec['hi'])
    if spec.get('esc') == 'log':
        nv = math.exp(min(max(math.log(max(float(v), lo)) + rng.normal(0, 0.5 * forca), math.log(lo)), math.log(hi)))
    else:
        nv = min(max(float(v) + rng.normal(0, 0.2 * forca * (hi - lo)), lo), hi)
    return int(round(nv)) if spec['t'] == 'i' else float(nv)

def _sorteia_op(nome, rng):
    return {'op': nome, **{k: _sorteia(s, rng) for k, s in OPS[nome].items()}}

def sortear(rng):
    tec = {'camadas': [int(rng.integers(LARGURA[0], 97)) for _ in range(int(rng.integers(1, 4)))]}
    tec.update({k: _sorteia(s, rng) for k, s in TECIDO.items()})
    nomes = [n for n in OPS if n != 'sgd']
    esc = [nomes[i] for i in rng.permutation(len(nomes))[:int(rng.integers(1, 5))]]
    return normalizar({'tecido': tec, 'regra': [_sorteia_op('sgd', rng)] + [_sorteia_op(n, rng) for n in esc]})

def mutar(prog, rng, forca=1.0):
    q = normalizar(prog)
    tec, regra = (dict(q['tecido']), {o['op']: dict(o) for o in q['regra']})
    x = rng.random()
    if x < 0.12:
        livres = [n for n in OPS if n not in regra]
        if livres:
            n = livres[int(rng.integers(len(livres)))]
            regra[n] = _sorteia_op(n, rng)
    elif x < 0.22:
        saiveis = [n for n in regra if n != 'sgd']
        if saiveis:
            del regra[saiveis[int(rng.integers(len(saiveis)))]]
    elif x < 0.34:
        cam = list(tec['camadas'])
        k = int(rng.integers(4))
        if k == 0:
            i = int(rng.integers(len(cam)))
            cam[i] = int(round(min(max(cam[i] * math.exp(rng.normal(0, 0.4 * forca)), LARGURA[0]), LARGURA[1])))
        elif k == 1:
            if len(cam) < 3 and (rng.random() < 0.5 or len(cam) == 1):
                cam.append(int(rng.integers(LARGURA[0], 65)))
            elif len(cam) > 1:
                cam.pop()
        else:
            campo = list(TECIDO)[int(rng.integers(len(TECIDO)))]
            tec[campo] = _perturba(TECIDO[campo], tec[campo], rng, forca)
        tec['camadas'] = cam
    else:
        for _ in range(1 + int(rng.integers(3))):
            n = list(regra)[int(rng.integers(len(regra)))]
            k = list(OPS[n])[int(rng.integers(len(OPS[n])))]
            regra[n][k] = _perturba(OPS[n][k], regra[n][k], rng, forca)
    return normalizar({'tecido': tec, 'regra': list(regra.values())})

def cruzar(a, b, rng):
    a, b = (normalizar(a), normalizar(b))
    tec = {k: a['tecido'][k] if rng.random() < 0.5 else b['tecido'][k] for k in a['tecido']}
    ra, rb = ({o['op']: o for o in a['regra']}, {o['op']: o for o in b['regra']})
    regra = []
    for n in ORDEM:
        if n in ra and n in rb:
            regra.append({k: ra[n][k] if rng.random() < 0.5 else rb[n][k] for k in ra[n]})
        elif (n in ra or n in rb) and (n == 'sgd' or rng.random() < 0.5):
            regra.append(dict(ra.get(n) or rb.get(n)))
    return normalizar({'tecido': tec, 'regra': regra})

class _P:
    ESCALA_I8 = 8.0

    def __init__(s, d, c, r, prog, restaurando=False):
        s.d, s.c, s.r = (d, c, r)
        s.p = normalizar(prog)
        s.o = {o['op']: o for o in s.p['regra']}
        T = s.p['tecido']
        s.hs, s.L = (list(T['camadas']), len(T['camadas']))
        s.tanh, s.sg = (T['ativacao'] == 'tanh', float(T['porta_entrada']))
        s.B = int(s.o['sgd']['lote'])
        s.rep = s.o.get('repeticao')
        s.Bcap = int(s.rep['R']) if s.rep else 0
        L, tam = (s.L, [d] + s.hs + [c])
        g = np.random.default_rng(10007 + int(T['semente']))
        s.G = (g.normal(0, 1, (d, s.hs[0])) * (2.0 / np.sqrt(d))).astype(np.float32)
        s.gb = g.normal(0, 1, s.hs[0]).astype(np.float32)
        dens = float(T['densidade'])
        s.conn = [(g.random((tam[i], tam[i + 1])) < dens).astype(np.float32) if dens < 0.999 else None for i in range(L)] + [None]
        if restaurando:
            return
        s.mask = [(np.arange(h) < max(1, int(round(float(T['ativas0']) * h)))).astype(np.float32) for h in s.hs]
        s._pesos_novos()
        s.age = [np.zeros(h, np.float32) for h in s.hs]
        s.util = [np.zeros(h, np.float32) for h in s.hs]
        s.mult = [np.ones(h, np.float32) for h in s.hs]
        s.pmask = [np.ones(s.P[i].shape, bool) for i in range(L)] if 'podar' in s.o else None
        zero = lambda: [np.zeros_like(w) for w in s.P]
        s.F = zero() if 'fisher' in s.o else None
        s.Fa = zero() if 'fisher' in s.o and 'ancora' in s.o else None
        s.A = None
        s.S = [w.copy() for w in s.P] if 'lento' in s.o else None
        if s.rep:
            dt = {'f32': np.float32, 'f16': np.float16, 'i8': np.int8}[s.rep['precisao']]
            s.BX, s.BY, s.Bl = (np.zeros((s.Bcap, d), dt), np.zeros(s.Bcap, np.int8), np.zeros(s.Bcap, np.float16))
        else:
            s.BX = s.BY = s.Bl = None
        s.Bn = s.Bvistos = 0
        s.t = s.u = 0
        s.LX, s.LY, s.nl = (np.zeros((s.B, d), np.float32), np.zeros(s.B, np.int64), 0)
        s.pr = s.pl = None
        s.folga_rest, s.lref, s.surp = (0, 0.7, 0.0)
        s.acc = [0.0] * L
        s.diag = {'reinicializadas': 0, 'ancoras': 0, 'mudancas': 0, 'cresceu': 0, 'liberou': 0, 'podado': 0.0, 'atualizacoes': 0}

    def _pesos_novos(s):
        L, tam = (s.L, [s.d] + s.hs + [s.c])
        s.P = [s.r.normal(0, 1 / np.sqrt(tam[i]), (tam[i], tam[i + 1])).astype(np.float32) for i in range(L + 1)] + [np.zeros(tam[i + 1], np.float32) for i in range(L + 1)]
        for i in range(L):
            if s.conn[i] is not None:
                s.P[i] *= s.conn[i]
        for l in range(L):
            s._silenciar(l, np.flatnonzero(s.mask[l] == 0))

    def _divergiu(s):
        s._pesos_novos()
        s.age = [np.zeros(h, np.float32) for h in s.hs]
        s.util = [np.zeros(h, np.float32) for h in s.hs]
        s.mult = [np.ones(h, np.float32) for h in s.hs]
        if s.pmask is not None:
            s.pmask = [np.ones(s.P[i].shape, bool) for i in range(s.L)]
        if s.F is not None:
            s.F = [np.zeros_like(w) for w in s.P]
            s.Fa = [np.zeros_like(w) for w in s.P] if s.Fa is not None else None
        s.A = None
        if s.S is not None:
            s.S = [w.copy() for w in s.P]
        s.pr = s.pl = None
        s.diag['divergiu'] = s.diag.get('divergiu', 0) + 1

    def _a(s, z):
        return np.tanh(z) if s.tanh else np.maximum(z, 0)

    def _da(s, z, h):
        return 1.0 - h * h if s.tanh else (z > 0).astype(np.float32)

    def _fwd(s, X, P=None):
        P, L = (P or s.P, s.L)
        H, Hs, Zs, fac = (X, [], [], [])
        for l in range(L):
            z = H @ P[l] + P[L + 1 + l]
            a = s._a(z)
            f = 1.0
            if l == 0 and s.sg > 0:
                f = 1.0 - s.sg + s.sg / (1.0 + np.exp(-(X @ s.G + s.gb)))
            h = (a * f * s.mask[l]).astype(np.float32)
            Zs.append((z, a))
            Hs.append(h)
            fac.append(f)
            H = h
        return (Hs, Zs, fac, H @ P[L] + P[2 * L + 1])

    def _grad(s, X, Y):
        L, B = (s.L, len(Y))
        Hs, Zs, fac, Z = s._fwd(X)
        E = np.exp(Z - Z.max(1, keepdims=True))
        Pr = E / E.sum(1, keepdims=True)
        perda = -np.log(Pr[np.arange(B), Y] + 1e-09)
        dZ = Pr.copy()
        dZ[np.arange(B), Y] -= 1
        dZ /= B
        G = [None] * (2 * (L + 1))
        G[L], G[2 * L + 1] = (Hs[-1].T @ dZ, dZ.sum(0))
        dH, dzs = (dZ @ s.P[L].T, [None] * L)
        for l in range(L - 1, -1, -1):
            z, a = Zs[l]
            dz = dH * s.mask[l] * fac[l] * s._da(z, a)
            entrada = Hs[l - 1] if l > 0 else X
            G[l], G[L + 1 + l] = (entrada.T @ dz, dz.sum(0))
            dzs[l] = dz * B
            dH = dz @ s.P[l].T
        return (G, perda, Pr, Hs, dzs)

    def _silenciar(s, l, idx):
        if len(idx) == 0:
            return
        s.P[l][:, idx] = 0
        s.P[s.L + 1 + l][idx] = 0
        s.P[l + 1][idx, :] = 0

    def _renascer(s, l, idx):
        if len(idx) == 0:
            return
        L, fan = (s.L, s.P[l].shape[0])
        w = s.r.normal(0, 1 / np.sqrt(fan), (fan, len(idx))).astype(np.float32)
        if s.conn[l] is not None:
            w *= s.conn[l][:, idx]
        s.P[l][:, idx] = w
        s.P[L + 1 + l][idx] = 0
        s.P[l + 1][idx, :] = 0
        s.age[l][idx] = 0
        ativa = s.mask[l] > 0
        s.util[l][idx] = float(s.util[l][ativa].mean()) if ativa.any() else 0.0
        if s.pmask is not None:
            s.pmask[l][:, idx] = True
            if l + 1 < L:
                s.pmask[l + 1][idx, :] = True
        for lst in (s.F, s.Fa):
            if lst is not None:
                lst[l][:, idx] = 0
                lst[L + 1 + l][idx] = 0
                lst[l + 1][idx, :] = 0
        if s.A is not None:
            s.A[l][:, idx] = s.P[l][:, idx]
            s.A[L + 1 + l][idx] = 0
            s.A[l + 1][idx, :] = 0

    def _guarda(s, x):
        p = s.rep['precisao']
        if p == 'i8':
            return np.clip(np.round(x / s.ESCALA_I8 * 127), -127, 127).astype(np.int8)
        return x.astype(np.float16 if p == 'f16' else np.float32)

    def _le(s, idx):
        x = s.BX[idx]
        return x.astype(np.float32) * (s.ESCALA_I8 / 127) if s.rep['precisao'] == 'i8' else x.astype(np.float32)

    def _amostrar(s, k):
        n = s.Bn
        if s.rep['amostragem'] == 'perda':
            p = s.Bl[:n].astype(np.float64) + 0.05
            return s.r.choice(n, size=k, p=p / p.sum())
        return s.r.integers(0, n, k)

    def _inserir(s, x, y, perda):
        R, pol = (s.Bcap, s.rep['insercao'])
        s.Bvistos += 1
        if s.Bn < R:
            pos, s.Bn = (s.Bn, s.Bn + 1)
        elif pol == 'reservatorio':
            pos = int(s.r.integers(0, s.Bvistos))
            if pos >= R:
                return
        elif pol == 'surpresa':
            if s.r.random() > min(1.0, perda / (2.0 * max(s.lref, 0.001))):
                return
            pos = int(np.argmin(s.Bl[:R]))
        else:
            cnt = np.bincount(s.BY[:R].astype(np.int64), minlength=s.c)
            cheia = int(np.argmax(cnt))
            if y == cheia and s.r.random() < 0.5:
                return
            pos = int(s.r.choice(np.flatnonzero(s.BY[:R] == cheia)))
        s.BX[pos], s.BY[pos], s.Bl[pos] = (s._guarda(x), y, perda)

    def aprender(s, x, y):
        s.t += 1
        s.LX[s.nl], s.LY[s.nl] = (x, y)
        s.nl += 1
        if s.nl >= s.B:
            X, Y = (s.LX[:s.nl].copy(), s.LY[:s.nl].copy())
            s.nl = 0
            s._atualizar(X, Y)

    def _atualizar(s, X, Y):
        o, L, B = (s.o, s.L, len(Y))
        s.u += 1
        s.diag['atualizacoes'] += 1
        Xa, Ya, idx = (X, Y, None)
        if s.rep and s.Bn > 0:
            idx = s._amostrar(max(1, int(round(s.rep['q'] * B))))
            Xa, Ya = (np.concatenate([X, s._le(idx)]), np.concatenate([Y, s.BY[idx].astype(np.int64)]))
        with np.errstate(all='ignore'):
            G, perda, Pr, Hs, dzs = s._grad(Xa, Ya)
        if not (np.isfinite(perda).all() and all((np.isfinite(g).all() for g in G))):
            s._divergiu()
            return
        if idx is not None:
            s.Bl[idx] = perda[B:].astype(np.float16)
        lr = o['sgd']['lr']
        if s.F is not None:
            beta, n = (o['fisher']['beta'], float(len(Ya)))
            for i in range(len(G)):
                s.F[i] += beta * ((G[i] * n) ** 2 - s.F[i])
        if 'penalidade' in o and s.A is not None:
            lam, usa = (o['penalidade']['lam'], o['penalidade']['usa_fisher'] == 1 and s.Fa is not None)
            for i in range(len(G)):
                coef = np.minimum(lam * (s.Fa[i] if usa else 1.0), 0.9 / lr)
                G[i] = G[i] + coef * (s.P[i] - s.A[i])
        wd = o['sgd']['wd']
        if wd > 0:
            for i in range(L + 1):
                G[i] = G[i] + wd * s.P[i]
        gn = float(np.sqrt(sum((float((g * g).sum()) for g in G))))
        if gn > o['sgd']['clip']:
            G = [g * (o['sgd']['clip'] / gn) for g in G]
        for l in range(L):
            G[l] = G[l] * s.mult[l][None, :]
            G[L + 1 + l] = G[L + 1 + l] * s.mult[l]
            if s.conn[l] is not None:
                G[l] = G[l] * s.conn[l]
        for i in range(len(G)):
            s.P[i] -= (lr * G[i]).astype(np.float32)
        if s.pmask is not None:
            for l in range(L):
                s.P[l] *= s.pmask[l]
        for l in range(L):
            s.age[l] += s.mask[l]
        if 'utilidade' in o:
            eta, tipo = (o['utilidade']['eta'], o['utilidade']['tipo'])
            for l in range(L):
                ativa = s.mask[l] > 0
                contrib = np.abs(Hs[l]).mean(0) * np.abs(s.P[l + 1]).sum(1)
                g2 = (dzs[l] ** 2).mean(0)
                if tipo == 'contrib':
                    f = contrib
                elif tipo == 'grad2':
                    f = g2
                else:
                    f = contrib / (contrib[ativa].mean() + 1e-09) + g2 / (g2[ativa].mean() + 1e-09) if ativa.any() else contrib
                s.util[l] += eta * (f - s.util[l]) * s.mask[l]
        mudou = False
        pn = float(perda[:B].mean())
        s.lref += 0.01 * (pn - s.lref)
        if 'mudanca' in o:
            m = o['mudanca']
            if s.pr is None:
                s.pr = s.pl = pn
            s.pr += m['rapida'] * (pn - s.pr)
            s.pl += m['lenta'] * (pn - s.pl)
            s.folga_rest = max(0, s.folga_rest - 1)
            sinal = s.pr - s.pl
            s.surp = float(min(max(sinal / max(m['limiar'], 1e-06), 0.0), 3.0) / 3.0)
            if sinal > m['limiar'] and s.folga_rest == 0 and (s.u > 20):
                mudou, s.folga_rest = (True, int(m['folga']))
                s.diag['mudancas'] += 1
        if 'ancora' in o:
            a = o['ancora']
            if a['gatilho'] == 'mudanca' and mudou or (a['gatilho'] == 'cada' and s.u % int(a['cada']) == 0):
                if s.Fa is not None:
                    s.Fa = [a['acumula'] * fa + f for fa, f in zip(s.Fa, s.F)]
                s.A = [w.copy() for w in s.P]
                s.diag['ancoras'] += 1
        if 'porta' in o and s.u % int(o['porta']['cada']) == 0:
            s._porta()
        if 'reinit' in o:
            s._reinit()
        if 'podar' in o:
            s._podar()
        if 'perturbar' in o and s.u % int(o['perturbar']['cada']) == 0:
            for l in range(L):
                ruido = s.r.normal(0, 1, s.P[l].shape).astype(np.float32)
                s.P[l] = (o['perturbar']['shrink'] * s.P[l] + o['perturbar']['sigma'] * ruido * s.mask[l][None, :]).astype(np.float32)
                if s.conn[l] is not None:
                    s.P[l] *= s.conn[l]
                if s.pmask is not None:
                    s.P[l] *= s.pmask[l]
        if 'alocar' in o:
            s._alocar(mudou)
        if s.S is not None:
            tau = o['lento']['tau']
            for i in range(len(s.P)):
                s.S[i] += tau * (s.P[i] - s.S[i])
        if s.rep:
            for j in range(B):
                s._inserir(X[j], int(Y[j]), float(perda[j]))

    def _porta(s):
        g = s.o['porta']
        for l in range(s.L):
            ativa = s.mask[l] > 0
            n = int(ativa.sum())
            if n == 0:
                continue
            rank = np.zeros(len(ativa), np.float32)
            if n > 1:
                rank[ativa] = np.argsort(np.argsort(s.util[l][ativa], kind='stable'), kind='stable') / (n - 1.0)
            idade = np.minimum(s.age[l] / float(g['idade_ref']), 1.0)
            z = g['c_u'] * rank + g['c_a'] * idade + g['c_s'] * s.surp + g['vies']
            m = g['m_min'] + (g['m_max'] - g['m_min']) / (1.0 + np.exp(-g['k'] * z))
            s.mult[l] = np.where(ativa, m, 1.0).astype(np.float32)

    def _reinit(s):
        o = s.o['reinit']
        if s.u % int(o['cada']) != 0:
            return
        for l in range(s.L):
            elig = np.flatnonzero((s.mask[l] > 0) & (s.age[l] > o['maturidade']))
            if len(elig) == 0:
                continue
            s.acc[l] += o['rho'] * len(elig) * int(o['cada'])
            n = int(s.acc[l])
            if n < 1:
                continue
            s.acc[l] -= n
            n = min(n, len(elig))
            if o['criterio'] == 'utilidade':
                pick = elig[np.argsort(s.util[l][elig], kind='stable')[:n]]
            elif o['criterio'] == 'idade':
                pick = elig[np.argsort(-s.age[l][elig], kind='stable')[:n]]
            else:
                pick = s.r.choice(elig, n, replace=False)
            s._renascer(l, pick)
            s.diag['reinicializadas'] += len(pick)

    def _podar(s):
        o = s.o['podar']
        if s.u % int(o['cada']) != 0 or o['alvo'] <= 0:
            return
        alvo = o['alvo'] * min(1.0, s.u / (4.0 * o['cada']))
        for l in range(s.L):
            k = int(alvo * s.P[l].size)
            if k <= 0:
                continue
            lim = np.partition(np.abs(s.P[l]).ravel(), k - 1)[k - 1]
            s.pmask[l] &= np.abs(s.P[l]) > lim
            s.P[l] *= s.pmask[l]
        s.diag['podado'] = float(np.mean([1.0 - s.pmask[l].mean() for l in range(s.L)]))

    def _alocar(s, mudou):
        o = s.o['alocar']
        for l in range(s.L):
            if mudou and o['crescer'] > 0:
                livres = np.flatnonzero(s.mask[l] == 0)[:int(o['crescer'])]
                if len(livres):
                    s.mask[l][livres] = 1
                    s._renascer(l, livres)
                    s.diag['cresceu'] += len(livres)
            if o['liberar'] > 0 and s.u % 100 == 0:
                ativas = np.flatnonzero(s.mask[l] > 0)
                if len(ativas) > 2:
                    lim = o['liberar'] * float(s.util[l][ativas].mean())
                    sai = ativas[(s.util[l][ativas] < lim) & (s.age[l][ativas] > 200)][:len(ativas) - 2]
                    if len(sai):
                        s.mask[l][sai] = 0
                        s._silenciar(l, sai)
                        s.diag['liberou'] += len(sai)

    def prever(s, X):
        X = np.asarray(X, np.float32)
        with np.errstate(all='ignore'):
            Z = s._fwd(X)[3]
            if s.S is not None:
                mix = s.o['lento']['mistura']
                Z = (1.0 - mix) * Z + mix * s._fwd(X, s.S)[3]
            E = np.exp(Z - Z.max(1, keepdims=True))
            return (np.argmax(Z, 1), _etiquetas_por_confianca(E / E.sum(1, keepdims=True)))

    def diagnostico(s):
        d = dict(s.diag)
        d['unidades_ativas'] = [int(m.sum()) for m in s.mask]
        d['exemplos_guardados'] = int(s.Bn)
        return d

    def estado(s):
        emp = lambda lst: None if lst is None else [np.asarray(a) for a in lst]
        pm = None if s.pmask is None else [{'bits': np.packbits(m.ravel()), 'forma': list(m.shape)} for m in s.pmask]
        return _empacotar({'p': s.p, 'P': s.P, 'mask': s.mask, 'age': s.age, 'util': s.util, 'mult': s.mult, 'pmask': pm, 'F': emp(s.F), 'Fa': emp(s.Fa), 'A': emp(s.A), 'S': emp(s.S), 'buf': None if not s.rep else {'X': s.BX, 'Y': s.BY, 'l': s.Bl}, 'Bn': s.Bn, 'Bv': s.Bvistos, 'sc': [s.t, s.u, s.nl, s.pr, s.pl, s.folga_rest, s.lref, s.surp, s.acc], 'lote': [s.LX[:s.nl].copy(), s.LY[:s.nl].copy()], 'diag': s.diag, 'rng': s.r.bit_generator.state})

    @staticmethod
    def restaurar(b, d, c):
        o = _desempacotar(b)
        a = _P(d, c, np.random.default_rng(0), o['p'], restaurando=True)
        a.P, a.mask, a.age, a.util, a.mult = (o['P'], o['mask'], o['age'], o['util'], o['mult'])
        a.pmask = None if o['pmask'] is None else [np.unpackbits(m['bits'])[:int(np.prod(m['forma']))].reshape(m['forma']).astype(bool) for m in o['pmask']]
        a.F, a.Fa, a.A, a.S = (o['F'], o['Fa'], o['A'], o['S'])
        if a.rep:
            a.BX, a.BY, a.Bl = (o['buf']['X'], o['buf']['Y'], o['buf']['l'])
        else:
            a.BX = a.BY = a.Bl = None
        a.Bn, a.Bvistos = (int(o['Bn']), int(o['Bv']))
        a.t, a.u, a.nl, a.pr, a.pl, a.folga_rest, a.lref, a.surp, a.acc = o['sc']
        a.LX, a.LY = (np.zeros((a.B, d), np.float32), np.zeros(a.B, np.int64))
        a.LX[:a.nl], a.LY[:a.nl] = (o['lote'][0], o['lote'][1])
        a.diag = o['diag']
        a.r.bit_generator.state = o['rng']
        return a

def executar_l2(entrada, programa):
    p = normalizar(programa)
    return _rodar(entrada, lambda d, c, r: _P(d, c, r, p), _P.restaurar)

def _prog(tecido, *regra):
    return normalizar({'tecido': tecido, 'regra': list(regra)})

def referencias(largura=64):
    t = {'camadas': [largura], 'ativacao': 'relu'}
    sgd = {'op': 'sgd', 'lr': 0.05, 'wd': 0.0, 'lote': 4}
    return {'sgd': _prog(t, sgd), 'ewc': _prog(t, sgd, {'op': 'mudanca', 'rapida': 0.1, 'lenta': 0.005, 'limiar': 0.15, 'folga': 200}, {'op': 'fisher', 'beta': 0.02}, {'op': 'ancora', 'gatilho': 'mudanca', 'acumula': 1.0}, {'op': 'penalidade', 'lam': 2.0, 'usa_fisher': 1}), 'replay': _prog(t, sgd, {'op': 'repeticao', 'R': 256, 'precisao': 'f32', 'q': 1.0, 'insercao': 'reservatorio', 'amostragem': 'uniforme'}), 'cbp': _prog(t, sgd, {'op': 'utilidade', 'eta': 0.01, 'tipo': 'contrib'}, {'op': 'reinit', 'rho': 0.0001, 'maturidade': 100, 'cada': 1, 'criterio': 'utilidade'}), 'sp': _prog(t, sgd, {'op': 'perturbar', 'shrink': 0.9995, 'sigma': 0.001, 'cada': 10})}
