# -*- coding: utf-8 -*-
import io
import json
import time
import numpy as np
PASTA = '/home/iro/bancada/vozes'
VOZES = ['faber', 'cadu', 'dora', 'alex', 'santa']
NBITS = 3472
NS_EM_ORDEM = 4.58
DPRIME = 3.0

def carregar():
    F = json.load(io.open(PASTA + '/fonetica.json', encoding='utf-8'))
    PAL = list(F['palavras'])
    ni = {w: i for i, w in enumerate(PAL)}
    X, C, V, R = ([], [], [], [])
    for arq in ('vozes_piper.npz', 'vozes_kokoro.npz'):
        z = np.load(PASTA + '/' + arq)
        X.append(np.unpackbits(z['vet'], axis=1)[:, :NBITS].astype(np.float64))
        C += [ni[str(w)] for w in z['rot']]
        V += [str(v) for v in z['voz']]
        R += [int(r) for r in z['rep']]
    g = np.load(PASTA + '/vozes_gabriel.npz')
    GX = np.unpackbits(g['vet'], axis=1)[:, :NBITS].astype(np.float64)
    GC = np.array([ni[str(w)] for w in g['rot']])
    return (PAL, np.concatenate(X), np.array(C), np.array(V), np.array(R), GX, GC)

def encolhida(Res):
    n, p = Res.shape
    S = Res.T @ Res / n
    mu = np.trace(S) / p
    S2 = float(np.sum(S * S))
    d2 = (S2 - mu * mu * p) / p
    x4 = float(np.sum(np.sum(Res * Res, axis=1) ** 2))
    b2 = min((x4 - n * S2) / (n * n * p), d2)
    a = b2 / d2
    S *= 1.0 - a
    S[np.diag_indices(p)] += a * mu
    return (S, a)

def medias(X, C):
    ws = np.unique(C)
    return (ws, np.array([X[C == w].mean(axis=0) for w in ws]))

def orelha(X, C):
    ws, M = medias(X, C)
    Res = X - M[np.searchsorted(ws, C)]
    S, a = encolhida(Res)
    d, Q = np.linalg.eigh(S)
    Wb = Q / np.sqrt(d)[None, :]
    g = M.mean(axis=0)
    _, s, Vt = np.linalg.svd((M - g) @ Wb, full_matrices=False)
    k = int(np.sum(s > s[0] * 1e-09))
    return {'g': g, 'P': Wb @ Vt[:k].T, 'lam': s[:k] ** 2 / len(ws), 'a': a, 'k': k}

def dist2(A, B):
    return np.maximum((A * A).sum(1)[:, None] - 2.0 * A @ B.T + (B * B).sum(1)[None, :], 0.0)

def ler(Zm, Cm, Zt, Ct):
    ws, Mz = medias(Zm, Cm)
    pos = np.searchsorted(ws, Ct)
    acerto = float(np.mean(np.argmin(dist2(Zt, Mz), axis=1) == pos))
    sig = float(np.sqrt(np.mean((Zt - Mz[pos]) ** 2)))
    DM = dist2(Mz, Mz)
    np.fill_diagonal(DM, np.inf)
    dp = np.sqrt(DM[np.unique(pos)].min(axis=1)) / sig
    return (acerto, sig, float(np.median(dp)), float(np.mean(dp >= DPRIME)))

def jaccard_v10(Xm, Cm, Xt, Ct, npal):
    inter = Xt @ Xm.T
    J = inter / np.maximum(Xt.sum(1)[:, None] + Xm.sum(1)[None, :] - inter, 1.0)
    N = np.full((len(Ct), npal), -1.0)
    for c in np.unique(Cm):
        N[:, c] = J[:, Cm == c].max(axis=1)
    return float(np.mean(np.argmax(N, axis=1) == Ct))

def main():
    t0 = time.time()
    PAL, X, C, V, R, GX, GC = carregar()
    npal = len(PAL)
    metade_de = np.arange(npal) % 2
    aceso = float(X.sum(1).mean())
    print('A CONTA DA ORELHA · D: a 5.6.1, decidir com tres desvios · Pi: %d falas sinteticas de %d palavras em 5 vozes e %d trechos de Gabriel, pela coclea da V9p (%d bits, %.0f acesos em media)' % (len(C), npal, len(GC), NBITS, aceso), flush=True)
    guardadas = {}

    def orelha_de(vozes, A):
        chave = (tuple(sorted(vozes)), A)
        if chave not in guardadas:
            m = np.isin(V, vozes) & (metade_de[C] == A)
            guardadas[chave] = orelha(X[m], C[m])
        return guardadas[chave]

    def lembrancas(vozes):
        m = np.isin(V, vozes) & (R == 0)
        return (X[m], C[m])

    def teste(voz, B):
        if voz == 'gabriel':
            m = metade_de[GC] == B
            return (GX[m], GC[m])
        m = (V == voz) & (R == 0) & (metade_de[C] == B)
        return (X[m], C[m])

    def avalia(o, dentro, voz, B):
        Xm, Cm = lembrancas(dentro)
        Xt, Ct = teste(voz, B)
        return (ler((Xm - o['g']) @ o['P'], Cm, (Xt - o['g']) @ o['P'], Ct), len(Ct))
    rodada = 0
    for A in (0, 1):
        B = 1 - A
        for alvo in VOZES + ['gabriel']:
            rodada += 1
            dentro = [v for v in VOZES if v != alvo]
            prev = []
            for u in dentro:
                outras = [v for v in dentro if v != u]
                prev.append(avalia(orelha_de(outras, A), outras, u, B)[0])
            prev = np.array(prev)
            o = orelha_de(dentro, A)
            lam = o['lam']
            meia = int(np.searchsorted(np.cumsum(lam), lam.sum() / 2.0)) + 1
            print('  rodada %d: de fora %s; a orelha pelas palavras %s da lista, o teste nas %s' % (rodada, alvo, ('pares', 'impares')[A], ('pares', 'impares')[B]), flush=True)
            print('    a materia: %d direcoes sobre os %d bits (encolhimento %.2f); a razao entre palavras e voz vai de %.2f na primeira a %.4f na ultima, metade dela nas %d primeiras; o preco, %.0f bits acesos x %d direcoes x %.2f ns = %.2f ms por palavra' % (o['k'], NBITS, o['a'], lam[0], lam[-1], meia, aceso, o['k'], NS_EM_ORDEM, aceso * o['k'] * NS_EM_ORDEM * 1e-06), flush=True)
            print("    a previsao da conta (cada voz de dentro de fora por vez, com uma voz a menos): acerto %.1f%% (de %.1f a %.1f), dispersao %.3f, d' mediano %.2f, %.1f%% das palavras com d' >= 3" % (100 * prev[:, 0].mean(), 100 * prev[:, 0].min(), 100 * prev[:, 0].max(), prev[:, 1].mean(), prev[:, 2].mean(), 100 * prev[:, 3].mean()), flush=True)
            r, n = avalia(o, dentro, alvo, B)
            print("    a medida em %s, fora da conta (%d falas): acerto %.1f%%, dispersao %.3f, d' mediano %.2f, %.1f%% com d' >= 3" % (alvo, n, 100 * r[0], r[1], r[2], 100 * r[3]), flush=True)
            Xm, Cm = lembrancas(dentro)
            Xt, Ct = teste(alvo, B)
            cru = ler(Xm, Cm, Xt, Ct)
            print("    sem a orelha, no mesmo teste: pela media dos bits %.1f%% (d' mediano %.2f, %.1f%% com d' >= 3); pelo Jaccard da V10 %.1f%%" % (100 * cru[0], cru[2], 100 * cru[3], 100 * jaccard_v10(Xm, Cm, Xt, Ct, npal)), flush=True)
    print('FIM %.0f s' % (time.time() - t0), flush=True)
if __name__ == '__main__':
    main()
