# -*- coding: utf-8 -*-
import io
import json
import sys
import time
from collections import deque
from math import erf, sqrt
import numpy as np
PASTA = '/home/iro/bancada/vozes'
NBITS = 3472
DP = 3.0
ALFA = 0.5 * (1.0 - erf(DP / sqrt(2.0)))
N_VIVAS = 3
JANELA = int(round(4 * DP * DP))
PRIOR = 0.5
PASSO_S = 2.0
N_ACONT = 10
P_ANUNCIO = 0.05
SOZINHO = 0.1
DIA = 43200
SEMENTE = 20260926
EXTINTOS = (0, 1)
NS = (1, 2, 3, 5, 10, 20, 50, 108)
MS = (1, 2, 5, 10, 20, 50, 108)
NS_UNIDADE, QUADRO_S, NUCLEOS, TETO = (1.447e-08, 0.0116, 6, 0.42)

def carregar():
    F = json.load(io.open(PASTA + '/fonetica.json', encoding='utf-8'))
    PAL = list(F['palavras'])
    fq = F['freq_cartilha']
    z = np.load(PASTA + '/vozes_piper.npz')
    m = np.array([str(v) == 'faber' for v in z['voz']])
    X = np.unpackbits(z['vet'][m], axis=1)[:, :NBITS].astype(np.float64)
    ni = {w: i for i, w in enumerate(PAL)}
    V = np.zeros((len(PAL), 3, NBITS))
    for x, r, c in zip(X, z['rep'][m], z['rot'][m]):
        V[ni[str(c)], int(r)] = x
    f = np.array([max(float(fq.get(w, 0)), 1.0) for w in PAL])
    ordem = sorted(range(len(PAL)), key=lambda i: -f[i])
    S = [i for i in ordem if len(PAL[i]) >= 4][:N_ACONT]
    return (PAL, f, V, S)

def pesos(a, b, N1, N0):
    p1 = (a + PRIOR) / (N1 + 2 * PRIOR)
    q1 = (b + PRIOR) / (N0 + 2 * PRIOR)
    return np.log(p1 / q1) - np.log((1.0 - p1) / (1.0 - q1))

def pesos_da_corrente(f, S):
    nw = len(f)
    livres = np.array([i for i in range(nw) if i not in S])
    p = np.zeros(nw)
    p[livres] = (1.0 - P_ANUNCIO) * f[livres] / f[livres].sum()
    for s in S:
        p[s] = P_ANUNCIO / N_ACONT
    return (p, livres)

def medir(w, V, fundo, sk):
    sc = V[:, :2] @ w
    mu = float((fundo[:, None] * sc).sum() / 2.0)
    m2 = float((fundo[:, None] * sc * sc).sum() / 2.0)
    sig = sqrt(max(m2 - mu * mu, 1e-12))
    st = V[:, 2] @ w
    lim = mu + DP * sig
    fp = int(np.sum(st > lim)) - int(st[sk] > lim)
    return (bool(st[sk] > lim), fp, (st[sk] - mu) / sig)

def conta(PAL, f, V, S):
    print('A CONTA (antes da vida)', flush=True)
    teto = NUCLEOS * TETO * QUADRO_S / NS_UNIDADE
    print('  o orcamento: %d nucleos x %.2f x %.1f ms / %.2f ns = %.2f milhoes de unidades de 1.024 entradas decididas a cada quadro' % (NUCLEOS, TETO, QUADRO_S * 1000.0, NS_UNIDADE * 1000000000.0, teto / 1000000.0), flush=True)
    p, _ = pesos_da_corrente(f, S)
    taxa = P_ANUNCIO / N_ACONT * (1.0 + SOZINHO)
    p0 = 1.0 - (1.0 - taxa) ** N_VIVAS
    print('  alfa (a 5.6.1) = %.5f; a janela da media = %d palavras; a chance de um acontecimento cair por acaso na vida de uma palavra, p0 = %.4f' % (ALFA, JANELA, p0), flush=True)
    print('  as palavras que anunciam: %s' % ', '.join((PAL[s] for s in S)), flush=True)
    qw = V[:, :2].mean(axis=1)
    primeiro = {}
    for n in NS:
        hits, fps, dps = (0, 0, [])
        for k, sk in enumerate(S):
            fundo = p.copy()
            fundo[sk] = 0.0
            fundo /= fundo.sum()
            qbar = fundo @ qw
            N1 = n * N_VIVAS * (1.0 + SOZINHO)
            a = n * qw[sk] + n * (N_VIVAS - 1 + SOZINHO * N_VIVAS) * qbar
            N0 = n / (P_ANUNCIO / N_ACONT) - N1
            b = N0 * qbar
            h, fp, dp = medir(pesos(a, b, N1, N0), V, fundo, sk)
            hits += h
            fps += fp
            dps.append(dp)
            if h and k not in primeiro:
                primeiro[k] = n
        print("  previsto depois de %3d anuncios: a fala nunca ouvida acende a propria unidade em %2d de 10; acende a unidade errada em %d de %d; d' mediano %.2f" % (n, hits, fps, 10 * (len(PAL) - 1), float(np.median(dps))), flush=True)
    print('  previsto: o anuncio a partir do qual cada palavra acende a propria unidade: %s' % ', '.join(('%s %s' % (PAL[S[k]], primeiro.get(k, 'nunca')) for k in range(N_ACONT))), flush=True)
    nmid = DIA // 2 * P_ANUNCIO / N_ACONT
    for k in EXTINTOS:
        sk = S[k]
        fundo = p.copy()
        fundo[sk] = 0.0
        fundo /= fundo.sum()
        qbar = fundo @ qw
        saida = []
        for m in MS:
            N1 = nmid * N_VIVAS * (1 + SOZINHO) + 0.1 * m * N_VIVAS
            a = nmid * qw[sk] + nmid * (N_VIVAS - 1 + SOZINHO * N_VIVAS) * qbar + 0.1 * m * N_VIVAS * qbar
            passos = nmid / (P_ANUNCIO / N_ACONT) + m / (P_ANUNCIO / N_ACONT)
            N0 = passos - N1
            b = (nmid / (P_ANUNCIO / N_ACONT) - nmid * N_VIVAS * (1 + SOZINHO)) * qbar + m * qw[sk] + (m / (P_ANUNCIO / N_ACONT) - m - 0.1 * m * N_VIVAS) * qbar
            h, _, dp = medir(pesos(a, b, N1, N0), V, fundo, sk)
            saida.append("%d sem: %s (d' %.1f)" % (m, 'acende' if h else 'apagou', dp))
        print('  previsto para %s, que para de anunciar no meio do dia (%d anuncios antes): %s' % (PAL[sk], nmid, '; '.join(saida)), flush=True)

def vida(PAL, f, V, S):
    rng = np.random.default_rng(SEMENTE)
    p, livres = pesos_da_corrente(f, S)
    cpl = np.cumsum(f[livres] / f[livres].sum())
    a = np.zeros((N_ACONT, NBITS))
    b = np.zeros((N_ACONT, NBITS))
    N1 = np.zeros(N_ACONT)
    N0 = np.zeros(N_ACONT)
    mu = np.zeros(N_ACONT)
    m2 = np.zeros(N_ACONT)
    viva = deque()
    pend_agora, pend_prox = ([], [])
    n_anun = np.zeros(N_ACONT, int)
    n_sem = np.zeros(N_ACONT, int)
    acendeu_em = np.full(N_ACONT, -1)
    apagou_em = np.full(N_ACONT, -1)
    ultimo = np.zeros(N_ACONT, bool)
    t0 = time.time()
    print('A VIDA', flush=True)
    for t in range(DIA):
        metade2 = t >= DIA // 2
        k = -1
        if rng.random() < P_ANUNCIO:
            k = int(rng.integers(N_ACONT))
            w = S[k]
            if metade2 and k in EXTINTOS:
                n_sem[k] += 1
            else:
                pend_prox.append(k)
                n_anun[k] += 1
        else:
            w = int(livres[min(int(np.searchsorted(cpl, rng.random())), len(livres) - 1)])
        x = V[w, int(rng.integers(2))]
        W = pesos(a, b, N1[:, None], N0[:, None])
        s = W @ x
        sig = np.sqrt(np.maximum(m2 - mu * mu, 0.0))
        acende = s > mu + DP * sig
        if k >= 0:
            if acende[k] and acendeu_em[k] < 0 and (not metade2):
                acendeu_em[k] = n_anun[k]
            if metade2 and k in EXTINTOS:
                if ultimo[k] and (not acende[k]) and (apagou_em[k] < 0):
                    apagou_em[k] = n_sem[k]
            ultimo[k] = acende[k]
        mu += (s - mu) / JANELA
        m2 += (s * s - m2) / JANELA
        viva.append([w, x, np.zeros(N_ACONT, bool)])
        if len(viva) > N_VIVAS:
            _, x0, visto = viva.popleft()
            y = visto.astype(np.float64)
            a += y[:, None] * x0[None, :]
            b += (1.0 - y)[:, None] * x0[None, :]
            N1 += y
            N0 += 1.0 - y
        ev = set(pend_agora)
        for kk in range(N_ACONT):
            if rng.random() < P_ANUNCIO / N_ACONT * SOZINHO:
                ev.add(kk)
        for kk in ev:
            for item in viva:
                item[2][kk] = True
        pend_agora, pend_prox = (pend_prox, [])
        if (t + 1) % 3600 == 0:
            W = pesos(a, b, N1[:, None], N0[:, None])
            st = V[:, 2] @ W.T
            sig = np.sqrt(np.maximum(m2 - mu * mu, 0.0))
            lim = mu + DP * sig
            hits, fps, dps = ([], 0, [])
            for kk, sk in enumerate(S):
                hits.append(bool(st[sk, kk] > lim[kk]))
                fps += int(np.sum(st[:, kk] > lim[kk])) - int(st[sk, kk] > lim[kk])
                dps.append((st[sk, kk] - mu[kk]) / max(sig[kk], 1e-12))
            print("  %2d h de vida: a fala nunca ouvida acende a propria unidade em %d de 10 (as que param: %s); a unidade errada em %d de %d; d' mediano %.2f; anuncios por acontecimento %d a %d" % ((t + 1) * PASSO_S / 3600, sum(hits), ''.join(('S' if hits[e] else 'n' for e in EXTINTOS)), fps, 10 * (len(PAL) - 1), float(np.median(dps)), n_anun.min(), n_anun.max()), flush=True)
    dt = time.time() - t0
    print('  o anuncio em que cada palavra acendeu a propria unidade antes do acontecimento: %s' % ', '.join(('%s %d' % (PAL[S[kk]], acendeu_em[kk]) for kk in range(N_ACONT))), flush=True)
    print('  as que pararam de anunciar: %s' % '; '.join(('%s apagou na %d vez sem o acontecimento (%d vezes ditas sem ele)' % (PAL[S[kk]], apagou_em[kk], n_sem[kk]) for kk in EXTINTOS)), flush=True)
    print('  o custo da regra neste roteiro (numpy, sem compilar): %.1f ms por palavra, %.3f s de servidor por segundo de vida' % (dt / DIA * 1000.0, dt / DIA / PASSO_S), flush=True)

def main():
    PAL, f, V, S = carregar()
    conta(PAL, f, V, S)
    if '--vida' in sys.argv:
        vida(PAL, f, V, S)
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
