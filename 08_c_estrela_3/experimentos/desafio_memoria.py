# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
from comum_vida import _desempacotar
from experimentos import desafio_oraculo as OR
ANTIGO = 5000
RECENTE = 256
COPIAS_TOLERADAS = 16
POR_TAREFA = 8
CORRELACAO = 0.98
FOLGA_DO_LIMIAR = 0.001
MIN_CELULAS = 5
TRANSICAO = 200

def montar_sondas_de_memoria(f, antigo=ANTIGO, por_tarefa=POR_TAREFA, semente=0):
    x, y, _ = OR.ler_vida(f)
    OR.zerar_registro(f)
    av = f['_avaliacao'].abrir()
    tarefa = np.asarray(av['tarefa'])
    pos = list(av['sondas_em'])
    refut = {int(k): int(v) for k, v in av['refutada_desde'].items()}
    tarefas = sorted(set(np.asarray(av['tarefa_sonda']).tolist()))
    N = len(y)
    idx = np.arange(N)
    fora = np.zeros(N, bool)
    s = 0
    for _tipo, _t, n in av['segmentos']:
        fora[s:s + min(TRANSICAO, n)] = True
        s += n
    X, T, Y, I = ([], [], [], [])
    for j, p in enumerate(pos):
        xs, ts, ys, ii = ([], [], [], [])
        for t in tarefas:
            ok = (tarefa == t) & (idx <= p - antigo) & ~fora
            r = refut.get(int(t))
            if r is not None and p >= r:
                ok &= idx >= r
            eleg = np.flatnonzero(ok)
            if len(eleg) < por_tarefa:
                continue
            g = np.random.default_rng([int(semente), j, int(t)])
            esc = g.choice(eleg, por_tarefa, replace=False)
            xs.append(x[esc])
            ts += [int(t)] * por_tarefa
            ys.append(y[esc])
            ii.append(esc)
        if xs:
            X_, T_, Y_, I_ = (np.concatenate(xs), np.asarray(ts, np.int64), np.concatenate(ys), np.concatenate(ii))
            emb = np.random.default_rng([int(semente), j, 999983]).permutation(len(T_))
            X.append(X_[emb])
            T.append(T_[emb])
            Y.append(Y_[emb])
            I.append(I_[emb])
        else:
            X.append(np.zeros((0, x.shape[1]), np.float32))
            T.append(np.zeros(0, np.int64))
            Y.append(np.zeros(0, np.int64))
            I.append(np.zeros(0, np.int64))
    return {'X': X, 'tarefa': T, 'y': Y, 'i': I}

def acerto_de_memoria(f, pred, sondas_mem):
    av = f['_avaliacao'].abrir()
    tarefas = sorted(set(np.asarray(av['tarefa_sonda']).tolist()))
    M = np.full((len(sondas_mem['y']), len(tarefas)), np.nan, np.float32)
    for j, (t_j, y_j) in enumerate(zip(sondas_mem['tarefa'], sondas_mem['y'])):
        if len(y_j) == 0:
            continue
        p = np.asarray(pred[j])
        for c, t in enumerate(tarefas):
            m = t_j == t
            if m.any():
                M[j, c] = float(np.mean(p[m] == y_j[m]))
    return M

def lacuna_de_memoria(A, M, min_celulas=MIN_CELULAS):
    por_tarefa = []
    for c in range(A.shape[1]):
        m = np.isfinite(M[:, c]) & np.isfinite(A[:, c])
        if int(m.sum()) >= min_celulas:
            por_tarefa.append(float(np.mean(M[m, c] - A[m, c])))
    if not por_tarefa:
        return float('nan')
    return max(0.0, float(np.mean(por_tarefa)))

def simular_memoria(entrada, saida, sondas_mem, memoriza=0.0, semente=1, copias=0.0, cresce=0.0):
    saida['memoria'], saida['copias'], saida['tamanho_logico'] = ([], [], [])
    for k, f in enumerate(entrada['fluxos']):
        av = f['_avaliacao'].abrir()
        tarefas = sorted(set(np.asarray(av['tarefa_sonda']).tolist()))
        A = OR.acerto_por_sonda(f, saida['respostas'][k])
        g = np.random.default_rng(31000 + 1000 * int(semente) + k)
        mem = []
        for j in range(len(sondas_mem[k]['y'])):
            t_j, y_j = (sondas_mem[k]['tarefa'][j], sondas_mem[k]['y'][j])
            resp = np.zeros(len(y_j), np.int8)
            for c, t in enumerate(tarefas):
                m = t_j == t
                if m.any():
                    p = min(1.0, float(A[j, c]) + float(memoriza))
                    certo = g.random(int(m.sum())) < p
                    errado = (y_j[m] + g.integers(1, OR.CLASSES, int(m.sum()))) % OR.CLASSES
                    resp[m] = np.where(certo, y_j[m], errado)
            mem.append(resp)
        n_int = len(av['interromper_em'])
        saida['memoria'].append(mem)
        saida['copias'].append([float(copias)] * n_int)
        saida['tamanho_logico'].append([int(4000 * (1.0 + float(cresce) * i)) for i in range(n_int)])
    return saida

def tensores_do_estado(b):
    try:
        o = _desempacotar(b)
    except Exception:
        raw = np.frombuffer(bytes(b), np.uint8)
        out = [raw]
        if len(raw) >= 4:
            out.append(np.frombuffer(bytes(b)[:len(raw) // 4 * 4], np.float32))
        return (out, False)
    out = []

    def anda(v):
        if isinstance(v, np.ndarray):
            out.append(v)
        elif isinstance(v, dict):
            for w in v.values():
                anda(w)
        elif isinstance(v, (list, tuple)):
            for w in v:
                anda(w)
    anda(o)
    return (out, True)

def tamanho_logico(b):
    t, _ = tensores_do_estado(b)
    return int(sum((a.nbytes for a in t)))

def _janelas(tensores, d, max_janelas=20000, semente=0):
    W = []
    for a in tensores:
        a = np.asarray(a)
        if a.size < d or a.dtype.kind not in 'fiu':
            continue
        v = a.astype(np.float32, copy=False)
        if v.ndim >= 2 and d <= v.shape[-1] <= 4 * d:
            linhas = v.reshape(-1, v.shape[-1])
            for off in range(0, linhas.shape[1] - d + 1):
                W.append(linhas[:, off:off + d])
        else:
            f = v.reshape(-1)
            n = len(f) - d + 1
            if n <= 0:
                continue
            ini = np.arange(n)
            if n > max_janelas:
                ini = np.sort(np.random.default_rng(semente).choice(n, max_janelas, replace=False))
            W.append(f[ini[:, None] + np.arange(d)[None, :]])
    if not W:
        return np.zeros((0, d), np.float32)
    W = np.concatenate(W).astype(np.float32)
    if len(W) > max_janelas:
        W = W[np.random.default_rng(semente).choice(len(W), max_janelas, replace=False)]
    return W

def _normalizar_linhas(M):
    M = M - M.mean(1, keepdims=True)
    n = np.linalg.norm(M, axis=1, keepdims=True)
    return (M / np.maximum(n, 1e-12), n[:, 0])

def copias_no_estado(tensores, X_velhos, correlacao=CORRELACAO, max_comparacoes=40000000.0, semente=0):
    X_velhos = np.asarray(X_velhos, np.float32)
    if len(X_velhos) == 0:
        return (0.0, 0, 1.0)
    d = X_velhos.shape[1]
    W = _janelas(tensores, d, semente=semente)
    if len(W) == 0:
        return (0.0, 0, 1.0)
    Wn, nw = _normalizar_linhas(W)
    vivas = nw > 1e-06
    Wn = Wn[vivas]
    if len(Wn) == 0:
        return (0.0, 0, 1.0)
    n_in = int(min(len(X_velhos), max(256, max_comparacoes / max(len(Wn), 1))))
    if n_in < len(X_velhos):
        sel = np.random.default_rng(semente + 1).choice(len(X_velhos), n_in, replace=False)
        Xv = X_velhos[sel]
    else:
        Xv = X_velhos
    Xn, nx = _normalizar_linhas(Xv)
    Xn = Xn[nx > 1e-06]
    if len(Xn) == 0:
        return (0.0, 0, 1.0)
    achou = np.zeros(len(Wn), bool)

    def _bloco_antigo(i):
        w = Wn[i:i + 256]
        melhor = np.full(len(w), -2.0, np.float32)
        for k in range(0, len(Xn), 2048):
            np.maximum(melhor, (w @ Xn[k:k + 2048].T).max(1), out=melhor)
        achou[i:i + 256] = melhor >= correlacao
    rapido = None
    try:
        from experimentos import copias_c
        rapido = copias_c.max_corr(Wn, Xn)
    except Exception:
        rapido = None
    if rapido is None:
        for i in range(0, len(Wn), 256):
            _bloco_antigo(i)
    else:
        achou[:] = rapido >= correlacao
        perto = np.abs(rapido - correlacao) <= FOLGA_DO_LIMIAR
        for i in sorted({int(j) // 256 * 256 for j in np.flatnonzero(perto)}):
            _bloco_antigo(i)
    cobertura = len(Xv) / len(X_velhos)
    n = int(achou.sum())
    return (float(n / cobertura), n, float(cobertura))

def _aprender_trecho(aprendiz, xs, ys):
    if hasattr(aprendiz, 'aprender_varios'):
        aprendiz.aprender_varios(np.stack(xs), np.asarray(ys, np.int64))
    else:
        for x, y in zip(xs, ys):
            aprendiz.aprender(x, y)

def rodar_com_memoria(entrada, fabrica, restaurar, sondas_mem=None, varrer_estado=True):
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': [], 'memoria': [], 'copias': [], 'tamanho_logico': [], 'flops': []}
    d, c = (entrada['d_entrada'], entrada['classes'])
    for k, f in enumerate(entrada['fluxos']):
        a = fabrica(d, c, np.random.default_rng(100 + k))
        sombra = None
        ler, resp, etq, bts, fiel, mem, cop, tam, flo = (f['abrir'](), [], [], [], [], [], [], [], [])
        vistos, nv, j = (np.zeros((1024, d), np.float32), 0, 0)
        sm = None if sondas_mem is None else sondas_mem[k]
        pendente, acabou = (None, False)
        while True:
            if pendente is not None:
                ev, pendente = (pendente, None)
            elif acabou:
                break
            else:
                ev = ler()
            if ev is None:
                break
            if ev[0] == 'treino':
                xs, ys = ([ev[1]], [ev[2]])
                while True:
                    nx = ler()
                    if nx is None:
                        acabou = True
                        break
                    if nx[0] == 'treino':
                        xs.append(nx[1])
                        ys.append(nx[2])
                        continue
                    pendente = nx
                    break
                if varrer_estado:
                    if nv + len(xs) > len(vistos):
                        vistos = np.concatenate([vistos, np.zeros((max(len(vistos), len(xs)), d), np.float32)])
                    vistos[nv:nv + len(xs)] = np.stack(xs)
                    nv += len(xs)
                _aprender_trecho(a, xs, ys)
                if sombra is not None:
                    _aprender_trecho(sombra, xs, ys)
            elif ev[0] == 'sonda':
                p, e = a.prever(ev[1])
                if sombra is not None:
                    ps, es = sombra.prever(ev[1])
                    fiel.append(bool(np.array_equal(np.asarray(p), np.asarray(ps)) and np.array_equal(np.asarray(e), np.asarray(es))))
                    sombra = None
                resp.append(np.asarray(p, np.int8))
                etq.append(np.asarray(e, np.int8))
                if sm is not None:
                    Xm = sm['X'][j]
                    if len(Xm):
                        pm, _ = a.prever(Xm.copy())
                        mem.append(np.asarray(pm, np.int8))
                    else:
                        mem.append(np.zeros(0, np.int8))
                j += 1
            else:
                b = a.estado()
                bts.append(len(b))
                fl = getattr(a, 'flops_por_interacao', None)
                if fl is not None and fl() is not None:
                    flo.append(float(fl()))
                if varrer_estado:
                    tensores, _conhecido = tensores_do_estado(b)
                    tam.append(int(sum((t.nbytes for t in tensores))))
                    if nv > RECENTE:
                        cop.append(copias_no_estado(tensores, vistos[:nv - RECENTE], semente=nv)[0])
                    else:
                        cop.append(0.0)
                sombra = a
                a = restaurar(b, d, c)
        out['respostas'].append(resp)
        out['etiquetas'].append(etq)
        out['bytes_por_interrupcao'].append(bts)
        out['restauracao_fiel'].append(fiel)
        out['memoria'].append(mem)
        out['copias'].append(cop)
        out['tamanho_logico'].append(tam)
        out['flops'].append(flo)
        if hasattr(a, 'diagnostico'):
            out['diagnostico'].append(a.diagnostico())
    return out
