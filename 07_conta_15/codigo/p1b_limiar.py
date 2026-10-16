# -*- coding: utf-8 -*-
import sys
import time
from collections import deque
from math import ceil, log
import numpy as np
import p1_aprender as P
ALFA, DP, K, NBITS = (P.ALFA, P.DP, P.N_ACONT, P.NBITS)
N_GUARDA = int(ceil(DP * DP / ALFA))
LIM_PAGE = log((1.0 - ALFA) / ALFA)
TAXA = P.P_ANUNCIO / K * (1.0 + P.SOZINHO)
P0 = 1.0 - (1.0 - TAXA) ** P.N_VIVAS
NS = (1, 2, 3, 5, 10, 20, 50, 108)

def limiar_pesado(sc, pw, n_bg):
    k = max(1, int(ceil(ALFA * n_bg)))
    frac = (k - 1) / n_bg
    o = np.argsort(sc)[::-1]
    cum = np.cumsum(pw[o])
    i = int(np.searchsorted(cum, frac, side='right'))
    return float(sc[o][min(i, len(o) - 1)])

def limiar_guardado(buf, n):
    if n == 0:
        return np.inf
    k = max(1, int(ceil(ALFA * n)))
    return float(np.partition(buf[:n], n - k)[n - k])

def conta(PAL, f, V, S):
    print('A CONTA DA SEGUNDA FORMULACAO (antes da vida)', flush=True)
    print('  alfa %.5f; a unidade guarda %d somas do costume; o limiar de Page ln((1-alfa)/alfa) = %.2f; p0 = %.4f' % (ALFA, N_GUARDA, LIM_PAGE, P0), flush=True)
    p, _ = P.pesos_da_corrente(f, S)
    qw = V[:, :2].mean(axis=1)
    primeiro, hvida = ({}, {})
    for n in NS:
        hits, fps = (0, 0)
        for k, sk in enumerate(S):
            fundo = p.copy()
            fundo[sk] = 0.0
            fundo /= fundo.sum()
            qbar = fundo @ qw
            N1 = n * P.N_VIVAS * (1.0 + P.SOZINHO)
            a = n * qw[sk] + n * (P.N_VIVAS - 1 + P.SOZINHO * P.N_VIVAS) * qbar
            N0 = n / (P.P_ANUNCIO / K) - N1
            w = P.pesos(a, N0 * qbar, N1, N0)
            sc = (V[:, :2] @ w).ravel()
            thr = limiar_pesado(sc, np.repeat(fundo, 2) / 2.0, min(N0, N_GUARDA))
            st = V[:, 2] @ w
            h = bool(st[sk] > thr)
            hits += h
            fps += int(np.sum(st > thr)) - int(h)
            if h and k not in primeiro:
                primeiro[k] = n
            if n == NS[-1]:
                hvida[k] = float(np.mean(V[sk, :2] @ w > thr))
        print('  previsto depois de %3d anuncios: a fala nunca ouvida acende a propria unidade em %2d de 10; a unidade errada em %d de %d (o criterio da 5.6.1 da %.1f)' % (n, hits, fps, K * (len(PAL) - 1), ALFA * K * (len(PAL) - 1)), flush=True)
    print('  previsto: o anuncio a partir do qual a fala nunca ouvida acende a propria unidade: %s' % ', '.join(('%s %s' % (PAL[S[k]], primeiro.get(k, 'nunca')) for k in range(K))), flush=True)
    for k in P.EXTINTOS:
        h = hvida[k]
        q = 0.005 * h / (0.005 * h + ALFA * (1.0 - P.P_ANUNCIO))
        passo = log((1.0 - P0) / (1.0 - q))
        m = int(ceil(LIM_PAGE / passo))
        print('  previsto para %s: acende em %.0f%% das falas da vida; a chance de acertar quando acende q = %.3f; cada vez sem o acontecimento soma %.2f, e a ligacao se apaga na %da vez dita sem ele' % (PAL[S[k]], 100 * h, q, passo, m), flush=True)
    hm = float(np.mean(list(hvida.values())))
    q = 0.005 * hm / (0.005 * hm + ALFA * (1.0 - P.P_ANUNCIO))
    m = int(ceil(LIM_PAGE / log((1.0 - P0) / (1.0 - q))))
    lf, lt = (ALFA * (1.0 - P.P_ANUNCIO), 0.005 * hm)
    falsos = P.DIA * lt * (lf / (lf + lt)) ** m * K
    print('  previsto: esquecimentos falsos (a ligacao apagada sem ter mudado) no dia, nas 10 unidades: %.1f' % falsos, flush=True)

def vida(PAL, f, V, S):
    rng = np.random.default_rng(P.SEMENTE)
    _, livres = P.pesos_da_corrente(f, S)
    cpl = np.cumsum(f[livres] / f[livres].sum())
    a = np.zeros((K, NBITS))
    b = np.zeros((K, NBITS))
    N1 = np.zeros(K)
    N0 = np.zeros(K)
    buf = np.zeros((K, N_GUARDA))
    nbuf = np.zeros(K, int)
    pos = np.zeros(K, int)
    Fk = np.zeros(K)
    Hk = np.zeros(K)
    C = np.zeros(K)
    falhas = [[] for _ in range(K)]
    viva = deque()
    pend_agora, pend_prox = ([], [])
    n_anun = np.zeros(K, int)
    n_sem = np.zeros(K, int)
    acendeu_em = np.full(K, -1)
    apagou_em = np.full(K, -1)
    esquec = []
    t0 = time.time()
    print('A VIDA', flush=True)
    for t in range(P.DIA):
        metade2 = t >= P.DIA // 2
        k = -1
        if rng.random() < P.P_ANUNCIO:
            k = int(rng.integers(K))
            w = S[k]
            if metade2 and k in P.EXTINTOS:
                n_sem[k] += 1
            else:
                pend_prox.append(k)
                n_anun[k] += 1
        else:
            w = int(livres[min(int(np.searchsorted(cpl, rng.random())), len(livres) - 1)])
        x = V[w, int(rng.integers(2))]
        W = P.pesos(a, b, N1[:, None], N0[:, None])
        s = W @ x
        thr = np.array([limiar_guardado(buf[kk], nbuf[kk]) for kk in range(K)])
        acende = s > thr
        if k >= 0 and acende[k] and (acendeu_em[k] < 0) and (not metade2):
            acendeu_em[k] = n_anun[k]
        viva.append([w, x, np.zeros(K, bool), s.copy(), acende.copy()])
        if len(viva) > P.N_VIVAS:
            w0, x0, visto, s0, ac0 = viva.popleft()
            y = visto.astype(np.float64)
            a += y[:, None] * x0[None, :]
            b += (1.0 - y)[:, None] * x0[None, :]
            N1 += y
            N0 += 1.0 - y
            for kk in range(K):
                if not visto[kk]:
                    buf[kk, pos[kk]] = s0[kk]
                    pos[kk] = (pos[kk] + 1) % N_GUARDA
                    nbuf[kk] = min(nbuf[kk] + 1, N_GUARDA)
                if ac0[kk]:
                    q = (Hk[kk] + P.PRIOR) / (Fk[kk] + 2 * P.PRIOR)
                    Fk[kk] += 1
                    if visto[kk]:
                        Hk[kk] += 1
                        C[kk] = max(0.0, C[kk] + log(P0 / q))
                        if C[kk] == 0.0:
                            falhas[kk] = []
                    else:
                        C[kk] += log((1.0 - P0) / (1.0 - q))
                        falhas[kk].append(x0)
                        if C[kk] >= LIM_PAGE:
                            bits = np.any(np.array(falhas[kk]) > 0, axis=0)
                            a[kk, bits] = (b[kk, bits] + P.PRIOR) * (N1[kk] + 2 * P.PRIOR) / (N0[kk] + 2 * P.PRIOR) - P.PRIOR
                            verdadeiro = metade2 and kk in P.EXTINTOS
                            esquec.append((t, kk, verdadeiro, w0 == S[kk]))
                            if verdadeiro and apagou_em[kk] < 0:
                                apagou_em[kk] = n_sem[kk]
                            C[kk] = 0.0
                            falhas[kk] = []
        ev = set(pend_agora)
        for kk in range(K):
            if rng.random() < P.P_ANUNCIO / K * P.SOZINHO:
                ev.add(kk)
        for kk in ev:
            for item in viva:
                item[2][kk] = True
        pend_agora, pend_prox = (pend_prox, [])
        if (t + 1) % 3600 == 0:
            W = P.pesos(a, b, N1[:, None], N0[:, None])
            st = V[:, 2] @ W.T
            thr = np.array([limiar_guardado(buf[kk], nbuf[kk]) for kk in range(K)])
            hits, fps = ([], 0)
            for kk, sk in enumerate(S):
                hits.append(bool(st[sk, kk] > thr[kk]))
                fps += int(np.sum(st[:, kk] > thr[kk])) - int(hits[-1])
            nv = sum((1 for e in esquec if e[2]))
            print('  %2d h de vida: a fala nunca ouvida acende a propria unidade em %d de 10 (as que param: %s); a unidade errada em %d de %d; esquecimentos: %d verdadeiros e %d falsos' % ((t + 1) * P.PASSO_S / 3600, sum(hits), ''.join(('S' if hits[e] else 'n' for e in P.EXTINTOS)), fps, K * (len(PAL) - 1), nv, len(esquec) - nv), flush=True)
    dt = time.time() - t0
    print('  o anuncio em que cada palavra acendeu a propria unidade antes do acontecimento: %s' % ', '.join(('%s %d' % (PAL[S[kk]], acendeu_em[kk]) for kk in range(K))), flush=True)
    print('  as que pararam de anunciar: %s' % '; '.join(('%s se apagou na %da vez dita sem o acontecimento (%d vezes ditas sem ele)' % (PAL[S[kk]], apagou_em[kk], n_sem[kk]) for kk in P.EXTINTOS)), flush=True)
    falsos = [e for e in esquec if not e[2]]
    print('  esquecimentos falsos: %d (%s)' % (len(falsos), ', '.join(('%s as %.1f h%s' % (PAL[S[e[1]]], e[0] * P.PASSO_S / 3600, '' if e[3] else ' por palavra parecida') for e in falsos[:20]))), flush=True)
    print('  o custo neste roteiro (numpy, sem compilar): %.1f ms por palavra, %.3f s de servidor por segundo de vida' % (dt / P.DIA * 1000.0, dt / P.DIA / P.PASSO_S), flush=True)

def main():
    PAL, f, V, S = P.carregar()
    conta(PAL, f, V, S)
    if '--vida' in sys.argv:
        vida(PAL, f, V, S)
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
