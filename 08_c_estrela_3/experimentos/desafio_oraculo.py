# -*- coding: utf-8 -*-
import os
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
CLASSES = 4
ACASO = 1.0 / CLASSES
DEN_MINIMO = 0.1
JANELA_APRENDE = 1000
JANELA_REVISA = 3000

def ler_vida(f):
    ler = f['abrir']()
    xs, ys, sonda = ([], [], None)
    while True:
        ev = ler()
        if ev is None:
            break
        if ev[0] == 'treino':
            xs.append(ev[1])
            ys.append(ev[2])
        elif ev[0] == 'sonda' and sonda is None:
            sonda = ev[1]
    return (np.asarray(xs, np.float32), np.asarray(ys, np.int64), np.asarray(sonda, np.float32))

def zerar_registro(f):
    reg = f['_avaliacao'].abrir()['registro']
    reg['aberturas'], reg['completos'] = (0, 0)

class _Mlp:

    def __init__(self, d, c, largura, semente):
        g = np.random.default_rng(semente)
        self.P = [g.normal(0, np.sqrt(2.0 / d), (d, largura)).astype(np.float32), np.zeros(largura, np.float32), g.normal(0, np.sqrt(2.0 / largura), (largura, largura)).astype(np.float32), np.zeros(largura, np.float32), g.normal(0, np.sqrt(1.0 / largura), (largura, c)).astype(np.float32), np.zeros(c, np.float32)]
        self.m = [np.zeros(p.shape, np.float64) for p in self.P]
        self.v = [np.zeros(p.shape, np.float64) for p in self.P]
        self.t = 0

    def _fwd(self, X):
        W1, b1, W2, b2, W3, b3 = self.P
        h1 = np.maximum(0, X @ W1 + b1)
        h2 = np.maximum(0, h1 @ W2 + b2)
        return (h1, h2, h2 @ W3 + b3)

    def prever(self, X):
        return np.argmax(self._fwd(X)[2], 1)

    def probs(self, X):
        Z = self._fwd(X)[2]
        E = np.exp(Z - Z.max(1, keepdims=True))
        return E / E.sum(1, keepdims=True)

    def passo(self, X, Y, lr, wd=0.0):
        W1, b1, W2, b2, W3, b3 = self.P
        h1, h2, Z = self._fwd(X)
        E = np.exp(Z - Z.max(1, keepdims=True))
        Pr = E / E.sum(1, keepdims=True)
        dZ = Pr
        dZ[np.arange(len(Y)), Y] -= 1
        dZ /= len(Y)
        g3, gb3 = (h2.T @ dZ, dZ.sum(0))
        d2 = dZ @ W3.T * (h2 > 0)
        g2, gb2 = (h1.T @ d2, d2.sum(0))
        d1 = d2 @ W2.T * (h1 > 0)
        g1, gb1 = (X.T @ d1, d1.sum(0))
        if wd:
            g1, g2, g3 = (g1 + wd * W1, g2 + wd * W2, g3 + wd * W3)
        self.t += 1
        for i, (p, gr) in enumerate(zip(self.P, [g1, gb1, g2, gb2, g3, gb3])):
            gr = gr.astype(np.float64)
            self.m[i] = 0.9 * self.m[i] + 0.1 * gr
            self.v[i] = 0.999 * self.v[i] + 0.001 * gr * gr
            p -= (lr * (self.m[i] / (1 - 0.9 ** self.t)) / (np.sqrt(self.v[i] / (1 - 0.999 ** self.t)) + 1e-08)).astype(np.float32)
            p[np.abs(p) < 1e-20] = 0.0

def oraculo_da_vida(f, largura=128, epocas=8, epocas_inicio=40, lote=256, lr=0.003, wd=0.003, conjunto=3, semente=0, verboso=False):
    av = f['_avaliacao'].abrir()
    x, y, Xs = ler_vida(f)
    zerar_registro(f)
    ts, V, pos = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(av['sondas_em']))
    tarefa = np.asarray(av['tarefa'])
    inicio, refut = ({int(k): int(v) for k, v in av['inicio'].items()}, {int(k): int(v) for k, v in av['refutada_desde'].items()})
    tarefas = sorted(set(ts.tolist()))
    col = {t: i for i, t in enumerate(tarefas)}
    mu, sd = (x.mean(0), x.std(0) + 1e-06)
    xn, Xsn = ((x - mu) / sd, (Xs - mu) / sd)
    d = x.shape[1]
    redes = [_Mlp(d, CLASSES, largura, 1000 + 97 * semente + 13 * e) for e in range(conjunto)]
    gs = [np.random.default_rng(2000 + 97 * semente + 13 * e) for e in range(conjunto)]
    O = np.full((len(pos), len(tarefas)), np.nan, np.float32)
    treino_acerto = np.zeros(len(pos), np.float32)
    idx = np.arange(len(y))
    t0 = time.time()
    for j, p in enumerate(pos):
        util = idx <= p
        for t, r in refut.items():
            if p >= r:
                util &= ~((tarefa == t) & (idx < r))
        ii = np.flatnonzero(util)
        n_ep = epocas_inicio if j == 0 else epocas
        for net, g in zip(redes, gs):
            for _ in range(n_ep):
                ordem = g.permutation(ii)
                for k in range(0, len(ordem), lote):
                    b = ordem[k:k + lote]
                    net.passo(xn[b], y[b], lr, wd)
        pred = np.argmax(sum((net.probs(Xsn) for net in redes)), 1)
        for t in tarefas:
            if inicio.get(int(t), 10 ** 12) <= p:
                m = ts == t
                O[j, col[t]] = float(np.mean(pred[m] == V[j][m]))
        amostra = ii[gs[0].permutation(len(ii))[:2000]]
        treino_acerto[j] = float(np.mean(np.argmax(sum((net.probs(xn[amostra]) for net in redes)), 1) == y[amostra]))
        if verboso:
            print(f'  sonda {j + 1}/{len(pos)} ({len(ii)} exemplos) {round(time.time() - t0, 1)} s', flush=True)
    return {'O': O, 'tarefas': np.asarray(tarefas), 'pos': np.asarray(pos), 'treino_acerto': treino_acerto}

def oraculo_das_vidas(entrada, arquivo=None, variante=0, **kw):
    n = len(entrada['fluxos'])
    if arquivo and os.path.exists(arquivo):
        z = np.load(arquivo)
        if int(z['n_vidas'][0]) == n:
            out = [{'O': z[f'O{k}'], 'tarefas': z[f'tarefas{k}'], 'pos': z[f'pos{k}'], 'treino_acerto': z[f'treino{k}']} for k in range(n)]
            for f, o in zip(entrada['fluxos'], out):
                o['G'] = grupos_da_vida(f, o)
            return out
    out = [oraculo_da_vida(f, semente=k + 50 * int(variante), **kw) for k, f in enumerate(entrada['fluxos'])]
    for f, o in zip(entrada['fluxos'], out):
        o['G'] = grupos_da_vida(f, o)
    if arquivo:
        guardar_vidas(arquivo, out)
    return out

def acerto_por_sonda(f, resp):
    av = f['_avaliacao'].abrir()
    ts, V = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']))
    R = np.asarray(resp)
    tarefas = sorted(set(ts.tolist()))
    return np.array([[float(np.mean(R[j][ts == t] == V[j][ts == t])) for t in tarefas] for j in range(len(R))], np.float32)

def grupos_da_vida(f, orac):
    av = f['_avaliacao'].abrir()
    tarefa = np.asarray(av['tarefa'])
    refut = {int(k): int(v) for k, v in av['refutada_desde'].items()}
    pos, tarefas = (list(orac['pos']), list(orac['tarefas']))
    G = np.zeros((len(pos), len(tarefas)), np.int8)
    for j, p in enumerate(pos):
        for c, t in enumerate(tarefas):
            visto = np.flatnonzero(tarefa[:p + 1] == t)
            idade = p - int(visto[-1]) if len(visto) else 10 ** 9
            r = refut.get(int(t))
            if r is not None and 0 <= p - r < JANELA_REVISA:
                G[j, c] = 2
            elif idade <= JANELA_APRENDE:
                G[j, c] = 1
    return G

def _delta(O, A, den, mascara, min_celulas):
    n = int(mascara.sum())
    if n < min_celulas:
        return None
    return max(0.0, float((O[mascara] - A[mascara]).mean() / den[mascara].mean()))

def deficit(A, orac, G, min_celulas=3):
    O = orac['O']
    den = O - ACASO
    ok = np.isfinite(O) & (den > DEN_MINIMO)
    tot, por_grupo = ([], {0: [], 1: [], 2: []})
    for c in range(O.shape[1]):
        d = _delta(O[:, c], A[:, c], den[:, c], ok[:, c], min_celulas)
        if d is not None:
            tot.append(d)
        for gk in (0, 1, 2):
            dg = _delta(O[:, c], A[:, c], den[:, c], ok[:, c] & (G[:, c] == gk), min_celulas)
            if dg is not None:
                por_grupo[gk].append(dg)

    def media(v):
        return float(np.mean(v)) if v else float('nan')
    acima = float(np.mean(A[ok] > O[ok])) if ok.any() else float('nan')
    return [media(tot), media(por_grupo[0]), media(por_grupo[1]), media(por_grupo[2]), acima, int(ok.sum())]

def lacuna_ao_teto(A, orac):
    O = orac['O']
    ok = np.isfinite(O)
    if not ok.any():
        return float('nan')
    return float(np.mean((1.0 - A[ok]) / (1.0 - ACASO)))

def variacao_entre_recomecos(orac1, orac2):
    out = []
    for o1, o2 in zip(orac1, orac2):
        a = deficit(o2['O'], o1, o1['G'])[:4]
        b = deficit(o1['O'], o2, o2['G'])[:4]
        out.append([max(x, y) if np.isfinite(x) and np.isfinite(y) else x if np.isfinite(x) else y if np.isfinite(y) else 0.0 for x, y in zip(a, b)])
    return np.asarray(out, np.float64)

def deficits_por_tarefa(A, orac, base=12, min_celulas=3):
    O = orac['O']
    den = O - ACASO
    ok = np.isfinite(O) & (den > DEN_MINIMO)
    out = {}
    for c, t in enumerate(list(orac['tarefas'])):
        if int(t) < base:
            d = _delta(O[:, c], A[:, c], den[:, c], ok[:, c], min_celulas)
            if d is not None:
                out[int(t)] = d
    return out

def simular_do_oraculo(entrada, oraculos, fator=1.0, esquece=0.0, semente=1):
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': []}
    for k, (f, orac) in enumerate(zip(entrada['fluxos'], oraculos)):
        av = f['_avaliacao'].abrir()
        ts, V, tarefas = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(orac['tarefas']))
        G = orac['G'] if 'G' in orac else grupos_da_vida(f, orac)
        r = np.random.default_rng(1000 * int(semente) + k)
        resp, etq = ([], [])
        for j in range(len(V)):
            R = np.zeros(len(ts), np.int8)
            for c, t in enumerate(tarefas):
                m = ts == t
                o = orac['O'][j, c]
                p = ACASO if not np.isfinite(o) else ACASO + fator * (o - ACASO)
                if esquece > 0 and G[j, c] == 0:
                    p = ACASO + (p - ACASO) * (1.0 - esquece)
                certo = r.random(int(m.sum())) < p
                errado = (V[j][m] + r.integers(1, CLASSES, int(m.sum()))) % CLASSES
                R[m] = np.where(certo, V[j][m], errado)
            resp.append(R)
            etq.append(np.zeros(len(ts), np.int8))
        out['respostas'].append(resp)
        out['etiquetas'].append(etq)
        out['bytes_por_interrupcao'].append([1000] * len(av['interromper_em']))
        out['restauracao_fiel'].append([True] * len(av['interromper_em']))
    return out

def guardar_vidas(arquivo, out):
    n = len(out)
    tmp = arquivo + '.tmp.npz'
    np.savez_compressed(tmp, n_vidas=np.asarray([n]), **{f'O{k}': o['O'] for k, o in enumerate(out)}, **{f'tarefas{k}': o['tarefas'] for k, o in enumerate(out)}, **{f'pos{k}': o['pos'] for k, o in enumerate(out)}, **{f'treino{k}': o['treino_acerto'] for k, o in enumerate(out)})
    os.replace(tmp, arquivo)

def calcular_em_paralelo(semente, variante, arquivo, processos=4):
    import subprocess
    dono = os.path.abspath(__file__)
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    n = 4
    filhos, parciais = ([], [])
    for k in range(n):
        parcial = f'{arquivo}.vida{k}.npz'
        parciais.append(parcial)
        filhos.append(subprocess.Popen([sys.executable, '-B', dono, '--semente', str(semente), '--variante', str(variante), '--vida', str(k), '--parcial', parcial], env=env))
        while sum((1 for c in filhos if c.poll() is None)) >= processos:
            time.sleep(0.5)
    for c in filhos:
        c.wait()
        if c.returncode != 0:
            raise RuntimeError('um processo do oráculo falhou')
    out = []
    for parcial in parciais:
        z = np.load(parcial)
        out.append({'O': z['O'], 'tarefas': z['tarefas'], 'pos': z['pos'], 'treino_acerto': z['treino']})
        os.remove(parcial)
    guardar_vidas(arquivo, out)
if __name__ == '__main__':
    import argparse
    sys.path.insert(0, RAIZ)
    from experimentos import desafio_v as DV
    ap = argparse.ArgumentParser()
    ap.add_argument('--semente', type=int, default=1)
    ap.add_argument('--variante', type=int, default=0)
    ap.add_argument('--vida', type=int, default=None, help='só esta vida (usado pelo cálculo em paralelo)')
    ap.add_argument('--parcial', default=None)
    ap.add_argument('--processos', type=int, default=4)
    ap.add_argument('--saida', default=None)
    a = ap.parse_args()
    if a.vida is not None:
        ent = DV.gerar_vidas(a.semente)
        o = oraculo_da_vida(ent['fluxos'][a.vida], semente=a.vida + 50 * a.variante)
        np.savez_compressed(a.parcial, O=o['O'], tarefas=o['tarefas'], pos=o['pos'], treino=o['treino_acerto'])
        sys.exit(0)
    arq = a.saida or DV.caminho_do_oraculo(a.semente, a.variante)
    t0 = time.time()
    calcular_em_paralelo(a.semente, a.variante, arq, a.processos)
    print('oráculo calculado em', round(time.time() - t0, 1), 's ->', arq)
    ent = DV.gerar_vidas(a.semente)
    o = oraculo_das_vidas(ent, arq)
    for k, oo in enumerate(o):
        fim = oo['O'][-1]
        print(f'vida {k}: acerto final do recomeço por tarefa', np.round(fim, 2).tolist(), '| acerto de treino no fim', round(float(oo['treino_acerto'][-1]), 3))
