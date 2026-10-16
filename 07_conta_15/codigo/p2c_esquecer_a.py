# -*- coding: utf-8 -*-
import sys
sys.argv.append('--dp=2')
import time
from collections import deque
from math import ceil, log
import numpy as np
import p1_aprender as P
import p1b_limiar as B
import p4e_exato as E
import p2_orelha as O2
_pesos = P.pesos

def pesos_exato(a, b, N1, N0):
    w = _pesos(a, b, N1, N0)
    p0 = (b + P.PRIOR) / (N0 + 2 * P.PRIOR)
    n1 = np.broadcast_to(N1, np.shape(a))
    i = np.clip(np.searchsorted(E.GRADE, n1 * p0), 0, len(E.GRADE) - 1)
    ai = np.floor(a + 1e-09)
    voto = (ai >= E.CIMA[i]) | (ai <= E.BAIXO[i])
    return np.where(voto & (n1 > 0), w, 0.0)
P.pesos = pesos_exato
B.ALFA = E.ALFA_C
B.N_GUARDA = E.N_GUARDA
B.LIM_PAGE = E.LIM_PAGE
K, NB2, NV, TESTE = (O2.K, O2.NBITS2, O2.N_VIDA, O2.TESTE)
P0, LIM, ALFA, NG = (B.P0, E.LIM_PAGE, E.ALFA_C, E.N_GUARDA)
R_ANUN = P.P_ANUNCIO / K
INTERVALO = 1.0 / R_ANUN
KQ = max(1, int(ceil(ALFA * NG)))
FRAC = KQ / (NG + 1.0)
KQ_D = max(1, int(np.floor(ALFA * (NG + 1))))
_memo = {}

def arl(q):
    if q <= P0 or q >= 1.0:
        return np.inf
    ch = int(round(log(log((1.0 - P0) / (1.0 - q))) / log(1.02)))
    if ch in _memo:
        return _memo[ch]
    u = 1.02 ** ch
    q = 1.0 - (1.0 - P0) * np.exp(-u)
    d = log(q / P0)
    m = int(ceil(LIM / u - 1e-12))
    g = 1.0 - q
    if d >= (m - 1) * u:
        r = (1.0 - g ** m) / ((1.0 - g) * g ** m)
    else:
        M = int(ceil(4 * LIM / u - 1e-09))
        if M > 3000:
            r = np.inf
        else:
            D = max(1, int(round(4 * d / u)))
            i = np.arange(M)
            T = np.zeros((M, M))
            ok = i + 4 < M
            T[i[ok], i[ok] + 4] = g
            T[i, np.maximum(0, i - D)] += q
            r = float(np.linalg.solve(np.eye(M) - T, np.ones(M))[0])
    _memo[ch] = r
    return r

def cauda(sc, pw, frac):
    o = np.argsort(sc)[::-1]
    cum = np.cumsum(pw[o])
    i = int(np.searchsorted(cum, frac, side='right'))
    return float(sc[o][min(i, len(o) - 1)])

def conta_c(PAL, f, V, S):
    print('A CONTA DO ESQUECIMENTO NA SINAPSE (antes da vida)', flush=True)
    print('  o limiar da vida e a %da maior das %d somas guardadas do costume; uma palavra nova sem o acontecimento passa dele em media em %d/%d = %.2f%% das decisoes, acima dos %.2f%% da 5.6.1 (a regra que cumpre a 5.6.1 e a %da maior, %.2f%%); a conta abaixo usa o limiar que a vida tem' % (KQ, NG, KQ, NG + 1, 100 * FRAC, 100 * ALFA, KQ_D, 100 * KQ_D / (NG + 1.0)), flush=True)
    p, _ = P.pesos_da_corrente(f, S)
    qw = V[:, :NV].mean(axis=1)
    n = int(round(P.DIA / 2 * R_ANUN))
    N1 = n * P.N_VIVAS * (1.0 + P.SOZINHO)
    N0 = n / R_ANUN - N1
    print('  o estado de cada unidade no fim da primeira metade (%d anuncios), pela conta da p2 com a sinapse exata' % n, flush=True)
    tot_s, tot_u = (np.zeros(K), np.zeros(K))
    hits0, hitse, fps0, fpse, viv0, vive = (0, 0, 0, 0, [], [])
    for k, sk in enumerate(S):
        fundo = p.copy()
        fundo[sk] = 0.0
        fundo /= fundo.sum()
        qbar = fundo @ qw
        a = n * qw[sk] + n * (P.N_VIVAS - 1 + P.SOZINHO * P.N_VIVAS) * qbar
        w = P.pesos(a, N0 * qbar, N1, N0)
        pw = np.repeat(fundo, NV) / NV
        sc = V[:, :NV] @ w
        thr = cauda(sc.ravel(), pw, FRAC)
        fire = sc > thr
        taxa = p.copy()
        taxa[sk] = 0.0
        FPb = np.einsum('wr,wrj->j', taxa[:, None] * fire / NV, V[:, :NV])
        TPb = R_ANUN * (fire[sk] / NV) @ V[sk, :NV]
        s_j = TPb + P0 * FPb
        e_j = (1.0 - P0) * FPb
        obs = (s_j + e_j) * P.DIA
        vj = np.where((w > 0) & (obs > 0))[0]
        qv = s_j[vj] / (s_j[vj] + e_j[vj])
        av = np.array([arl(q) for q in qv])
        t_in = av * P.DIA / obs[vj]
        lam = N1 * qbar[vj]
        ii = np.clip(np.searchsorted(E.GRADE, lam), 0, len(E.GRADE) - 1)
        exc = np.maximum(E.CIMA[ii] - lam, 1.0)
        cresce = R_ANUN * (qw[sk][vj] - qbar[vj])
        t_out = np.where(cresce > 0, exc / np.maximum(cresce, 1e-12), np.inf)
        fin, volta = (np.isfinite(t_in), np.isfinite(t_out))
        tin = np.where(fin, t_in, 1.0)
        tout = np.where(volta, t_out, 0.0)
        fora = np.where(fin, np.where(volta, tout / (tout + tin), 1.0 - tin / P.DIA * (1.0 - np.exp(-P.DIA / tin))), 0.0)
        alarmes = np.where(fin, np.where(volta, P.DIA / (tin + tout), 1.0 - np.exp(-P.DIA / tin)), 0.0)
        acaso = int(np.sum(~fin))
        tot_s[k] = alarmes.sum()
        wt = w[vj] * qw[sk][vj]
        f_out = float(wt @ fora / wt.sum())
        FPu = float((taxa[:, None] * fire / NV).sum())
        TPu = R_ANUN * fire[sk].mean()
        Su, Eu = (TPu + P0 * FPu, (1.0 - P0) * FPu)
        qu = Su / (Su + Eu)
        tot_u[k] = (Su + Eu) * P.DIA / arl(qu)
        we = w.copy()
        we[vj] *= 1.0 - fora
        sce = V[:, :NV] @ we
        thre = cauda(sce.ravel(), pw, FRAC)
        st, ste = (V[:, TESTE] @ w, V[:, TESTE] @ we)
        h0, he = (bool(st[sk] > thr), bool(ste[sk] > thre))
        hits0 += h0
        hitse += he
        fps0 += int(np.sum(st > thr)) - int(h0)
        fpse += int(np.sum(ste > thre)) - int(he)
        viv0.append(float(fire[sk].mean()))
        vive.append(float((sce[sk] > thre).mean()))
        print('  %-6s a unidade acende %4.0f vezes por dia e acerta q = %.3f (a regra velha: %.1f testes de Page falsos por dia); %3d bits votam (%d perto do acaso, sem falso na conta), q deles de %.3f a %.3f (mediana %.3f); a regra nova: %.1f bits apagados por dia sem a ligacao ter mudado, cada um fora por %.0f min (mediana), o peso da palavra %.1f%% fora em media' % (PAL[sk], (Su + Eu) * P.DIA, qu, tot_u[k], len(vj), acaso, qv.min(), qv.max(), np.median(qv), tot_s[k], np.median(t_out[np.isfinite(t_out)]) * P.PASSO_S / 60 if np.isfinite(t_out).any() else float('inf'), 100 * f_out), flush=True)
        if k in P.EXTINTOS:
            cai = qv > P0
            u = np.log((1.0 - P0) / (1.0 - qv))
            d = np.log(qv / P0)
            Cj = np.zeros(len(vj))
            wn = w.copy()
            ultimo, fora_v = (0, [])
            peso0 = float(w[vj] @ qw[sk][vj])
            for vez in range(1, 61):
                scn = V[:, :NV] @ wn
                thn = cauda(scn.ravel(), pw, FRAC)
                fr = scn[sk] > thn
                if fr.any():
                    ultimo = vez
                xf = fr / NV @ V[sk, :NV][:, vj]
                inc = (xf * (1.0 - P0) + INTERVALO * e_j[vj]) * u - (xf * P0 + INTERVALO * P0 * FPb[vj]) * d
                Cj = np.where(cai, np.maximum(0.0, Cj + inc), 0.0)
                wn[vj[Cj >= LIM]] = 0.0
                fora_v.append(1.0 - float(wn[vj] @ qw[sk][vj]) / peso0)
                if not fr.any() and vez >= ultimo + 3:
                    break
            print('         previsto para %s, quando para de anunciar: a unidade acende na palavra ate a %da vez dita sem o acontecimento; o peso dela apagado em %.0f%% na 1a vez, %.0f%% na 2a e %.0f%% na 5a (conta pela media, com cada soma saindo do zero)' % (PAL[sk], ultimo, 100 * fora_v[0], 100 * fora_v[min(1, len(fora_v) - 1)], 100 * fora_v[min(4, len(fora_v) - 1)]), flush=True)
    ativos = [k for k in range(K) if k not in P.EXTINTOS]
    print('  previsto, a regra velha: %.0f testes de Page falsos no dia (a primeira metade nas 10 unidades e a segunda nas 8 que continuam); a p2b mediu 18, e a vida com --regra=unidade tem de repetir a p2b numero por numero' % (tot_u.sum() / 2 + tot_u[ativos].sum() / 2), flush=True)
    print('  previsto, a regra nova: %.0f bits apagados sem a ligacao ter mudado no dia, cada um so, e nenhuma palavra esquecida inteira' % (tot_s.sum() / 2 + tot_s[ativos].sum() / 2), flush=True)
    print('  previsto no fim da primeira metade, sem a erosao e com ela (a media dos bits fora): a fala nunca ouvida acende a propria unidade em %d e %d de 10; a unidade errada em %d e %d de %d; a palavra certa acende a propria unidade na corrente em %.0f%% e %.0f%% das vezes' % (hits0, hitse, fps0, fpse, K * (len(PAL) - 1), 100 * np.mean(viv0), 100 * np.mean(vive)), flush=True)
    print('  previsto, nas duas regras: o costume acima do limiar em perto de %.2f%% das decisoes sem o acontecimento, a media da %da maior de %d, e nao os %.2f%% da 5.6.1; o aprender igual ao da p2b (do 2o ao 4o anuncio), porque o esquecimento so age depois das falhas' % (100 * FRAC, KQ, NG, 100 * ALFA), flush=True)

def vida_c(PAL, f, V, S, regra):
    rng = np.random.default_rng(P.SEMENTE)
    _, livres = P.pesos_da_corrente(f, S)
    cpl = np.cumsum(f[livres] / f[livres].sum())
    a = np.zeros((K, NB2))
    b = np.zeros((K, NB2))
    N1 = np.zeros(K)
    N0 = np.zeros(K)
    buf = np.zeros((K, NG))
    nbuf = np.zeros(K, int)
    pos = np.zeros(K, int)
    Fk, Hk, C = (np.zeros(K), np.zeros(K), np.zeros(K))
    falhas = [[] for _ in range(K)]
    Fs, Hs, Cs = (np.zeros((K, NB2)), np.zeros((K, NB2)), np.zeros((K, NB2)))
    viva = deque()
    pend_agora, pend_prox = ([], [])
    n_anun, n_sem = (np.zeros(K, int), np.zeros(K, int))
    acendeu_em, apagou_em = (np.full(K, -1), np.full(K, -1))
    esquec = []
    propria = [[[] for _ in range(K)] for _ in range(2)]
    sem_ac = {kk: [] for kk in P.EXTINTOS}
    fp_n, dec_n = (np.zeros((2, K)), np.zeros((2, K)))
    sinapse = regra == 'sinapse'
    t0 = time.time()
    print('A VIDA, COM O ESQUECIMENTO NA %s' % ('SINAPSE' if sinapse else 'UNIDADE (a regra da p2b)'), flush=True)
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
        x = V[w, int(rng.integers(NV))]
        W = P.pesos(a, b, N1[:, None], N0[:, None])
        s = W @ x
        thr = np.array([B.limiar_guardado(buf[kk], nbuf[kk]) for kk in range(K)])
        acende = s > thr
        if k >= 0:
            if metade2 and k in P.EXTINTOS:
                sem_ac[k].append(bool(acende[k]))
            else:
                propria[int(metade2)][k].append(bool(acende[k]))
            if acende[k] and acendeu_em[k] < 0 and (not metade2):
                acendeu_em[k] = n_anun[k]
        viva.append([w, x, np.zeros(K, bool), s.copy(), acende.copy(), W > 0 if sinapse else None])
        if len(viva) > P.N_VIVAS:
            w0, x0, visto, s0, ac0, vp0 = viva.popleft()
            y = visto.astype(np.float64)
            a += y[:, None] * x0[None, :]
            b += (1.0 - y)[:, None] * x0[None, :]
            N1 += y
            N0 += 1.0 - y
            hh = int(metade2)
            for kk in range(K):
                if not visto[kk]:
                    buf[kk, pos[kk]] = s0[kk]
                    pos[kk] = (pos[kk] + 1) % NG
                    nbuf[kk] = min(nbuf[kk] + 1, NG)
                    dec_n[hh, kk] += 1
                    fp_n[hh, kk] += ac0[kk]
                if not ac0[kk]:
                    continue
                verdadeiro = metade2 and kk in P.EXTINTOS
                if not sinapse:
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
                        if C[kk] >= LIM:
                            bits = np.any(np.array(falhas[kk]) > 0, axis=0)
                            a[kk, bits] = (b[kk, bits] + P.PRIOR) * (N1[kk] + 2 * P.PRIOR) / (N0[kk] + 2 * P.PRIOR) - P.PRIOR
                            esquec.append((t, kk, verdadeiro, w0 == S[kk], int(bits.sum())))
                            if verdadeiro and apagou_em[kk] < 0:
                                apagou_em[kk] = n_sem[kk]
                            C[kk] = 0.0
                            falhas[kk] = []
                    continue
                idx = np.nonzero((x0 > 0) & vp0[kk])[0]
                if idx.size == 0:
                    continue
                q = (Hs[kk, idx] + P.PRIOR) / (Fs[kk, idx] + 2 * P.PRIOR)
                Fs[kk, idx] += 1
                cai = q > P0
                if visto[kk]:
                    Hs[kk, idx] += 1
                    Cs[kk, idx] = np.where(cai, np.maximum(0.0, Cs[kk, idx] + np.log(P0 / q)), Cs[kk, idx])
                    continue
                Cs[kk, idx] = np.where(cai, Cs[kk, idx] + np.log((1.0 - P0) / (1.0 - q)), Cs[kk, idx])
                ap = idx[Cs[kk, idx] >= LIM]
                if ap.size:
                    a[kk, ap] = (b[kk, ap] + P.PRIOR) * (N1[kk] + 2 * P.PRIOR) / (N0[kk] + 2 * P.PRIOR) - P.PRIOR
                    Cs[kk, ap] = 0.0
                    Hs[kk, ap] = 0.0
                    Fs[kk, ap] = 0.0
                    esquec.append((t, kk, verdadeiro, w0 == S[kk], int(ap.size)))
                    if verdadeiro and apagou_em[kk] < 0:
                        apagou_em[kk] = n_sem[kk]
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
            hh = int(metade2)
            nv = sum((e[4] if sinapse else 1 for e in esquec if e[2]))
            nf = sum((e[4] if sinapse else 1 for e in esquec if not e[2]))
            print('  %2d h de vida: a fala nunca ouvida acende a propria unidade em %d de 10 (as que param: %s); a unidade errada em %d de %d; o costume acima do limiar em %.2f%% das decisoes desta metade; %s: %d verdadeiros e %d falsos' % ((t + 1) * P.PASSO_S / 3600, sum(hits), ''.join(('S' if hits[e] else 'n' for e in P.EXTINTOS)), fps, K * (len(PAL) - 1), 100 * fp_n[hh].sum() / max(dec_n[hh].sum(), 1.0), 'bits apagados' if sinapse else 'esquecimentos', nv, nf), flush=True)
    dt = time.time() - t0
    print('  o anuncio em que cada palavra acendeu a propria unidade antes do acontecimento: %s' % ', '.join(('%s %d' % (PAL[S[kk]], acendeu_em[kk]) for kk in range(K))), flush=True)
    for kk in P.EXTINTOS:
        sq = sem_ac[kk]
        acesas = [i + 1 for i, v in enumerate(sq) if v]
        print('  %s, dita %d vezes sem o acontecimento: acendeu a unidade em %d das 10 primeiras e em %d de todas; a ultima vez que acendeu foi a %s%s' % (PAL[S[kk]], len(sq), sum(sq[:10]), len(acesas), '%da' % acesas[-1] if acesas else 'nenhuma', '' if sinapse else '; o teste de Page da unidade disparou na %da' % apagou_em[kk]), flush=True)
    ativos = [kk for kk in range(K) if kk not in P.EXTINTOS]
    c1 = [v for kk in range(K) for v in propria[0][kk][4:]]
    c2 = [v for kk in ativos for v in propria[1][kk]]
    print('  a palavra certa acendendo a propria unidade na corrente: na primeira metade, do 5o anuncio em diante, %.1f%% de %d; na segunda, nas %d que continuam, %.1f%% de %d (a pior unidade, %.1f%%)' % (100 * np.mean(c1), len(c1), len(ativos), 100 * np.mean(c2), len(c2), 100 * min((np.mean(propria[1][kk]) for kk in ativos))), flush=True)
    for hh, nome in ((0, 'primeira'), (1, 'segunda')):
        print('  o costume acima do limiar na %s metade: %.2f%% das %d decisoes sem o acontecimento (de %.2f%% a %.2f%% por unidade)' % (nome, 100 * fp_n[hh].sum() / dec_n[hh].sum(), int(dec_n[hh].sum()), 100 * np.min(fp_n[hh] / dec_n[hh]), 100 * np.max(fp_n[hh] / dec_n[hh])), flush=True)
    falsos = [e for e in esquec if not e[2]]
    if sinapse:
        por = np.zeros(K, int)
        for e in falsos:
            por[e[1]] += e[4]
        print('  bits apagados sem a ligacao ter mudado: %d, em %d passos; por unidade: %s' % (sum((e[4] for e in falsos)), len(falsos), ', '.join(('%s %d' % (PAL[S[kk]], por[kk]) for kk in range(K)))), flush=True)
    else:
        print('  esquecimentos falsos: %d (%s)' % (len(falsos), ', '.join(('%s as %.1f h%s' % (PAL[S[e[1]]], e[0] * P.PASSO_S / 3600, '' if e[3] else ' por palavra parecida') for e in falsos[:20]))), flush=True)
    print('  o custo neste roteiro (numpy, sem compilar): %.1f ms por palavra' % (dt / P.DIA * 1000.0), flush=True)

def main():
    regra = 'sinapse'
    for x in sys.argv:
        if x.startswith('--regra='):
            regra = x[8:]
    print("O ESQUECIMENTO NA SINAPSE, com d' = 2 e a sinapse exata: alfa %.5f, costume de %d, Page %.2f, p0 %.4f" % (ALFA, NG, LIM, P0), flush=True)
    PAL, f, _, S = P.carregar()
    V, _, _ = O2.carregar2(PAL)
    if '--vida' in sys.argv:
        vida_c(PAL, f, V, S, regra)
    else:
        conta_c(PAL, f, V, S)
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
