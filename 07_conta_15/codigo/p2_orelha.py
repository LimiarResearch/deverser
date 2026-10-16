# -*- coding: utf-8 -*-
import io
import json
import sys
import time
from collections import deque
from math import ceil, log
import numpy as np
import p1_aprender as P
import p1b_limiar as B
COC = json.load(io.open('/home/iro/casa/cerebro/coclea14_bandas.json', encoding='utf-8'))
L_LO, NDEG, FATOR, NB = (COC['L_LO'], int(COC['DEGRAUS']), 4.56, int(COC['N_BANDAS']))
HOP_S = 0.0116
PAUSA = int(ceil(0.25 / HOP_S))
RAZAO = 0.544 / 0.322
NFAIXAS = 10
NBITS2 = NB * NFAIXAS * (NDEG + 1)
N_VIDA, TESTE = (4, 4)
K = P.N_ACONT

def faixa(k):
    return 0 if k == 0 else int(np.floor(np.log(k) / np.log(RAZAO))) + 1
FAIXA = np.array([faixa(k) for k in range(2000)])

def orelha(E, ref):
    lim = 10.0 ** L_LO * FATOR ** np.arange(NDEG)
    nivel = (E[:, :, None] / ref >= lim[None, None, :]).sum(axis=2)
    som = (nivel >= 1).any(axis=1)
    eventos, t, n = ([], 0, len(som))
    while t < n:
        if not som[t]:
            t += 1
            continue
        ini, ult, s = (t, t, 0)
        while t < n:
            if som[t]:
                ult, s = (t, 0)
            else:
                s += 1
                if s >= PAUSA:
                    break
            t += 1
        eventos.append((ini, ult))
    vet = []
    for ini, ult in eventos:
        m = np.zeros((NB, NFAIXAS), int)
        for k in range(ult - ini + 1):
            j = FAIXA[k]
            if j >= NFAIXAS:
                break
            m[:, j] = np.maximum(m[:, j], nivel[ini + k])
        v = np.zeros((NB, NFAIXAS, NDEG + 1))
        v[np.arange(NB)[:, None], np.arange(NFAIXAS)[None, :], m] = 1.0
        vet.append(v.ravel())
    return (vet, [(u - i + 1) * HOP_S for i, u in eventos])

def carregar2(PAL):
    z = np.load('p2_mundo.npz')
    E, comp, rot, rep = (z['E'], z['comp'], z['rot'], z['rep'])
    ref = float(E.max())
    ini = np.concatenate([[0], np.cumsum(comp)[:-1]])
    V = np.zeros((len(PAL), 5, NBITS2))
    nev, durs = ([], [])
    for i0, c, w, r in zip(ini, comp, rot, rep):
        vet, d = orelha(E[i0:i0 + c], ref)
        nev.append(len(vet))
        durs += d
        if vet:
            V[w, r] = vet[int(np.argmax(d))]
    return (V, np.array(nev), np.array(durs))

def conta2(PAL, f, V, S, nev, durs):
    print('A CONTA DA ORELHA (antes da vida)', flush=True)
    print('  a pausa: %d quadros (0,25 s); a razao das faixas %.3f; as faixas ate %.0f ms; %d bits por palavra' % (PAUSA, RAZAO, RAZAO ** (NFAIXAS - 1) * HOP_S * 1000.0, NBITS2), flush=True)
    print('  o corte, previsto: um evento por fala em 100%% (nenhum silencio de 0,25 s dentro de uma palavra dita sozinha); medido na corrente do mundo antes da vida: %.1f%% com um evento, %d falas com dois ou mais, %d sem nenhum; duracao mediana %.0f ms (de %.0f a %.0f)' % (100 * np.mean(nev == 1), int(np.sum(nev >= 2)), int(np.sum(nev == 0)), 1000.0 * np.median(durs), 1000.0 * np.min(durs), 1000.0 * np.max(durs)), flush=True)
    p, _ = P.pesos_da_corrente(f, S)
    qw = V[:, :N_VIDA].mean(axis=1)
    primeiro = {}
    for n in B.NS:
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
            sc = (V[:, :N_VIDA] @ w).ravel()
            thr = B.limiar_pesado(sc, np.repeat(fundo, N_VIDA) / N_VIDA, min(N0, B.N_GUARDA))
            st = V[:, TESTE] @ w
            h = bool(st[sk] > thr)
            hits += h
            fps += int(np.sum(st > thr)) - int(h)
            if h and k not in primeiro:
                primeiro[k] = n
        print('  previsto depois de %3d anuncios: a fala nunca ouvida acende a propria unidade em %2d de 10; a unidade errada em %d de %d (o criterio da 5.6.1 da %.1f; a regua da p1b previa 9 e 12 depois de 50)' % (n, hits, fps, K * (len(PAL) - 1), B.ALFA * K * (len(PAL) - 1)), flush=True)
    print('  previsto: o anuncio a partir do qual a fala nunca ouvida acende a propria unidade: %s' % ', '.join(('%s %s' % (PAL[S[k]], primeiro.get(k, 'nunca')) for k in range(K))), flush=True)

def vida2(PAL, f, V, S):
    rng = np.random.default_rng(P.SEMENTE)
    _, livres = P.pesos_da_corrente(f, S)
    cpl = np.cumsum(f[livres] / f[livres].sum())
    a = np.zeros((K, NBITS2))
    b = np.zeros((K, NBITS2))
    N1 = np.zeros(K)
    N0 = np.zeros(K)
    buf = np.zeros((K, B.N_GUARDA))
    nbuf = np.zeros(K, int)
    pos = np.zeros(K, int)
    Fk, Hk, C = (np.zeros(K), np.zeros(K), np.zeros(K))
    falhas = [[] for _ in range(K)]
    viva = deque()
    pend_agora, pend_prox = ([], [])
    n_anun, n_sem = (np.zeros(K, int), np.zeros(K, int))
    acendeu_em, apagou_em = (np.full(K, -1), np.full(K, -1))
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
        x = V[w, int(rng.integers(N_VIDA))]
        W = P.pesos(a, b, N1[:, None], N0[:, None])
        s = W @ x
        thr = np.array([B.limiar_guardado(buf[kk], nbuf[kk]) for kk in range(K)])
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
                    pos[kk] = (pos[kk] + 1) % B.N_GUARDA
                    nbuf[kk] = min(nbuf[kk] + 1, B.N_GUARDA)
                if ac0[kk]:
                    q = (Hk[kk] + P.PRIOR) / (Fk[kk] + 2 * P.PRIOR)
                    Fk[kk] += 1
                    if visto[kk]:
                        Hk[kk] += 1
                        C[kk] = max(0.0, C[kk] + log(B.P0 / q))
                        if C[kk] == 0.0:
                            falhas[kk] = []
                    else:
                        C[kk] += log((1.0 - B.P0) / (1.0 - q))
                        falhas[kk].append(x0)
                        if C[kk] >= B.LIM_PAGE:
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
            st = V[:, TESTE] @ W.T
            thr = np.array([B.limiar_guardado(buf[kk], nbuf[kk]) for kk in range(K)])
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
    print('  esquecimentos falsos: %d (%s)' % (len(falsos), ', '.join(('%s as %.1f h' % (PAL[S[e[1]]], e[0] * P.PASSO_S / 3600) for e in falsos[:20]))), flush=True)
    print('  o custo neste roteiro (numpy, sem compilar): %.1f ms por palavra, %.3f s de servidor por segundo de vida' % (dt / P.DIA * 1000.0, dt / P.DIA / P.PASSO_S), flush=True)

def main():
    PAL, f, _, S = P.carregar()
    t0 = time.time()
    V, nev, durs = carregar2(PAL)
    print('  a orelha passou pelas %d falas em %.0f s' % (len(nev), time.time() - t0), flush=True)
    conta2(PAL, f, V, S, nev, durs)
    if '--vida' in sys.argv:
        vida2(PAL, f, V, S)
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
