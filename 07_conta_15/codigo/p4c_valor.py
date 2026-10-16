# -*- coding: utf-8 -*-
import sys
import time
from collections import deque
from math import log, sqrt
import numpy as np
import p1_aprender as P
import p1b_limiar as B
import p4_vida_de_dentro as Q
import p4b_narrativa as R
DT, DEC, VIDA_ITEM, VIDA_FASE, N_ITENS, CONHECE = (Q.DT, Q.DEC, Q.VIDA_ITEM, Q.VIDA_FASE, Q.N_ITENS, Q.CONHECE)
ENT, NE, SENT = (Q.ENT, Q.NE, Q.SENT + ['querer'])
iP, iPe, iV, iTB, iTD, iB, iBr, iE, iEs, iO = range(len(ENT))
ALVOS = ['perto', 'brincar', 'estrondo']
VIZ = 2
SILENCIO = R.SILENCIO
VALOR_DE = [iP, iB, iPe, iBr, iV, iE, iO]

def bossa(f):
    return [len(ENT) + (f + d) % Q.FASES for d in range(-VIZ, VIZ + 1)]

def valor(n_i, g_i, N, G):
    if n_i < 1 or N - n_i < 1:
        return 0.0
    p1, p0 = (g_i / n_i, (G - g_i) / (N - n_i))
    pb = G / N
    se = sqrt(max(pb * (1 - pb), 1e-12) * (1.0 / n_i + 1.0 / (N - n_i)))
    return p1 - p0 if abs(p1 - p0) / se >= P.DP else 0.0

def conta():
    print('A CONTA DA TERCEIRA FORMULACAO (antes da vida)', flush=True)
    print('  previsto, o apego: aceso em mais de 80%% do tempo com Gabriel a partir do dia 2 (a presenca ganha valor no dia 1, porque o bem vem com ele muitas vezes por visita), e igual no dia 6, depois da viagem', flush=True)
    print('  previsto, o querer e a frustracao: a bola querida a partir da primeira noite; a frustracao acesa na bola que nao vem, a cada noite a partir do dia 2, uns 5 min depois de passar a demora ja vista (1 min)', flush=True)
    print('  previsto, a espera de Gabriel: com as fases juntas, a procura acesa em mais da metade dos 20 min antes da maioria das chegadas a partir do dia 3, e nos 20 min depois das saidas; em menos de 5%% do resto do tempo sem ele', flush=True)
    print('  previsto, o medo: so o estrondo e o estalo aprendido; aceso em menos de 5%% da vida acordada', flush=True)
    print('  previsto, o contagio: depois de um tom duro, a alegria e a calma apagadas ate a proxima causa boa', flush=True)
    print('  previsto, o resto como na p4b: a duracao de 13,5 min para cima, o filhote sem espera, o medo do estalo do 3o ao 10o e apagando, a saudade, a curiosidade, e o narrador revivendo a historia do dia', flush=True)

def vida():
    X, fase, dorme, dia, hora, obj = Q.mundo()
    n = len(fase)
    K = len(ALVOS)
    a = np.zeros((K, NE))
    b = np.zeros((K, NE))
    N1, N0 = (np.zeros(K), np.zeros(K))
    buf = np.zeros((K, B.N_GUARDA))
    nbuf, pos = (np.zeros(K, int), np.zeros(K, int))
    Fk, Hk, C = (np.zeros(K), np.zeros(K), np.zeros(K))
    falhas = [[] for _ in range(K)]
    episodios_k = [deque() for _ in range(K)]
    itens = deque()
    contextos = deque()
    pres_item = None
    s = {k: 0 for k in SENT}
    fam = {}
    ausencias, ini_aus = ([], None)
    demoras, ini_quer = ([], None)
    vn = np.zeros(len(ENT))
    vg = np.zeros(len(ENT))
    VN, VG = (0.0, 0.0)
    antes = np.zeros(len(ENT), bool)
    dis_antes = np.zeros(K, bool)
    reg = {k: np.zeros(n, np.uint8) for k in SENT}
    score_linha = np.zeros((VIDA_ITEM, K))
    subidas_alvo = np.zeros((n, K), bool)
    estalo_medo, estalo_n, esquec = ([], 0, [])
    fase_atual = -1
    historia = []
    ep = {'ini': 0, 'dia': 1, 'itens': [], 'sent': {k: 0 for k in SENT}}
    ctx_antes = (bool(X[0, iP]), bool(dorme[0]))
    ponteiro = None
    ultimo_novo = 0
    revive = np.full(n, -1)
    duro = np.zeros(n, bool)
    t0 = time.time()
    print('A VIDA', flush=True)
    for t in range(n):
        x = X[t]
        acordado = not dorme[t]
        subida = x & ~antes
        antes = x.copy()
        sub_alvo = np.array([subida[iPe], subida[iBr], subida[iEs]])
        subidas_alvo[t] = sub_alvo
        for k in range(K):
            if sub_alvo[k]:
                for item in itens:
                    item[2][k] = True
                for cz in contextos:
                    cz[2][k] = True
                if pres_item is not None:
                    pres_item[2][k] = True
        if fase[t] != fase_atual:
            fase_atual = fase[t]
            contextos.append([t, bossa(fase[t]), np.zeros(K, bool)])
        while contextos and t - contextos[0][0] > VIDA_FASE:
            _, bits, visto = contextos.popleft()
            y = visto.astype(float)
            for fb in bits:
                a[:, fb] += y
                b[:, fb] += 1.0 - y
            N1 += y
            N0 += 1.0 - y
        if x[iP] and pres_item is None:
            pres_item = [t, iP, np.zeros(K, bool), None]
        if pres_item is not None and (not x[iP]):
            if pres_item[3] is None:
                pres_item[3] = t
            if t - pres_item[3] > VIDA_ITEM:
                y = pres_item[2].astype(float)
                a[:, iP] += y
                b[:, iP] += 1.0 - y
                N1 += y
                N0 += 1.0 - y
                pres_item = None
        novos = [i for i in np.where(subida)[0] if i not in (iTB, iTD, iP)]
        for i in novos:
            if i == iE:
                estalo_n += 1
            ja = [j for j, it in enumerate(itens) if it[0] == i]
            if ja:
                it = itens[ja[0]]
                del itens[ja[0]]
                itens.append((i, t, it[2]))
            else:
                itens.append((i, t, np.zeros(K, bool)))
            if i not in ep['itens']:
                ep['itens'].append(int(i))
        if subida[iP] and iP not in ep['itens']:
            ep['itens'].append(iP)
        if novos or subida[iP]:
            ultimo_novo = t
        while itens and (len(itens) > N_ITENS or t - itens[0][1] > VIDA_ITEM):
            i0, _, visto = itens.popleft()
            y = visto.astype(float)
            a[:, i0] += y
            b[:, i0] += 1.0 - y
            N1 += y
            N0 += 1.0 - y
        W = R.pesos3(a, b, N1[:, None], N0[:, None])
        viv = [it[0] for it in itens] + bossa(fase[t]) + ([iP] if pres_item is not None else [])
        sc = W[:, viv].sum(axis=1)
        thr = np.array([B.limiar_guardado(buf[k], nbuf[k]) for k in range(K)])
        dis = sc > thr
        if t >= VIDA_ITEM:
            tt = t - VIDA_ITEM
            veio = subidas_alvo[tt + 1:t + 1].any(axis=0)
            for k in range(K):
                if not veio[k]:
                    buf[k, pos[k]] = score_linha[tt % VIDA_ITEM, k]
                    pos[k] = (pos[k] + 1) % B.N_GUARDA
                    nbuf[k] = min(nbuf[k] + 1, B.N_GUARDA)
        score_linha[t % VIDA_ITEM] = sc
        for k in range(K):
            if dis[k] and (not dis_antes[k]):
                episodios_k[k].append((t, list(viv)))
            while episodios_k[k] and (sub_alvo[k] or t - episodios_k[k][0][0] > VIDA_ITEM):
                t_e, bits = episodios_k[k].popleft()
                ok = bool(sub_alvo[k])
                p0 = max(N1[k] / max(N1[k] + N0[k], 1.0), 0.001)
                q = (Hk[k] + P.PRIOR) / (Fk[k] + 2 * P.PRIOR)
                Fk[k] += 1
                if ok:
                    Hk[k] += 1
                    C[k] = max(0.0, C[k] + log(p0 / q))
                    if C[k] == 0.0:
                        falhas[k] = []
                else:
                    C[k] += log((1.0 - p0) / max(1.0 - q, 1e-09))
                    falhas[k] += bits
                    if C[k] >= B.LIM_PAGE:
                        idx = sorted(set(falhas[k]))
                        a[k, idx] = (b[k, idx] + P.PRIOR) * (N1[k] + 2 * P.PRIOR) / (N0[k] + 2 * P.PRIOR) - P.PRIOR
                        esquec.append((dia[t], hora[t], ALVOS[k]))
                        C[k] = 0.0
                        falhas[k] = []
        dis_antes = dis.copy()
        esp_perto, esp_brincar, esp_estrondo = dis
        if x[iP] and ini_aus is not None:
            ausencias.append(t - ini_aus)
            ini_aus = None
        if not x[iP] and ini_aus is None:
            ini_aus = t
        bem = s['alegria'] > 0 or s['calma'] > 0
        if acordado:
            ativos = [i for i in VALOR_DE if x[i]]
            for i in ativos:
                vn[i] += 1
                vg[i] += bem
            VN += 1
            VG += bem
        v_pres = valor(vn[iP], vg[iP], VN, VG)
        v_bola = valor(vn[iB], vg[iB], VN, VG)
        querer = bool(x[iB] and v_bola > 0)
        if querer and ini_quer is None:
            ini_quer = t
        if ini_quer is not None and subida[iBr]:
            demoras.append(t - ini_quer)
            ini_quer = None
        if ini_quer is not None and (not x[iB]):
            ini_quer = None
        causa = {k: 0 for k in SENT}
        tom_duro = bool(x[iV] and x[iTD])
        duro[t] = tom_duro
        if acordado:
            causa['alegria'] = int(x[iPe] or x[iBr] or (x[iV] and x[iTB]))
            causa['medo'] = int(x[iEs] or esp_estrondo)
            if obj[t] >= 0:
                fam[obj[t]] = fam.get(obj[t], 0) + 1
                causa['curiosidade'] = int(fam[obj[t]] <= CONHECE)
            causa['apego'] = int(x[iP] and v_pres > 0)
            causa['procura'] = int(esp_perto and (not x[iP]))
            causa['querer'] = int(querer)
            if ini_aus is not None:
                lim_a = B.limiar_guardado(np.array(ausencias, float), len(ausencias)) if ausencias else -1.0
                causa['saudade'] = int(t - ini_aus > lim_a)
            if ini_quer is not None and (not x[iBr]):
                lim_d = B.limiar_guardado(np.array(demoras, float), len(demoras)) if demoras else np.inf
                causa['frustracao'] = int(t - ini_quer > lim_d)
            causa['calma'] = int(s['alegria'] > 0 and s['medo'] == 0 and (s['saudade'] == 0) and (s['frustracao'] == 0) and (not x[iPe]) and (not x[iBr]))
        for k in SENT:
            s[k] = 255 if causa[k] else int(s[k] * DEC)
        if acordado and tom_duro:
            s['alegria'] = 0
            s['calma'] = 0
        for k in SENT:
            reg[k][t] = s[k]
            ep['sent'][k] = max(ep['sent'][k], s[k])
        if subida[iE]:
            estalo_medo.append((dia[t], estalo_n, bool(esp_estrondo)))
        ctx = (bool(x[iP]), bool(dorme[t]))
        if ctx != ctx_antes:
            if ep['itens']:
                historia.append(ep)
            ep = {'ini': t, 'dia': int(dia[t]), 'itens': [], 'sent': {k: 0 for k in SENT}}
            if dorme[t] and (not ctx_antes[1]):
                ponteiro = None
        ctx_antes = ctx
        descanso = dorme[t] or t - ultimo_novo >= SILENCIO
        if descanso and historia:
            do_dia = [e for e in historia if e['dia'] == dia[t] or (dorme[t] and hora[t] < 7.0 and (e['dia'] == dia[t] - 1))] or historia[-3:]
            if ponteiro is None or ponteiro[0] >= len(do_dia):
                ponteiro = [0, 0]
            e = do_dia[ponteiro[0]]
            revive[t] = e['itens'][ponteiro[1]]
            if ponteiro[1] + 1 < len(e['itens']):
                ponteiro[1] += 1
            else:
                ponteiro = [ponteiro[0] + 1, 0]
        elif not descanso:
            ponteiro = None
    dt = time.time() - t0
    return (X, dorme, dia, hora, reg, estalo_medo, esquec, dt, historia, revive, duro)

def relatorio(X, dorme, dia, hora, reg, estalo_medo, esquec, dt, historia, revive, duro):
    acordado = ~dorme
    n = len(dorme)
    print('  a semana: %d passos em %.0f s de servidor' % (n, dt), flush=True)
    m = (dia == 1) & (hora < 7.5) & ~X[:, iP]
    print('  o filhote, sozinho antes da primeira chegada: saudade %.0f%%, procura %.0f%%' % (100 * np.mean(reg['saudade'][m] > 0), 100 * np.mean(reg['procura'][m] > 0)), flush=True)
    for k in SENT:
        r = reg[k] > 0
        runs, c = ([], 0)
        for v in list(r) + [False]:
            if v:
                c += 1
            elif c:
                runs.append(c)
                c = 0
        if runs:
            print('  %-11s aceso em %5.1f%% da vida acordada; %4d vezes; cada vez de %.1f a %.1f min (mediana %.1f)' % (k, 100 * np.mean(r[acordado]), len(runs), min(runs) * DT / 60, max(runs) * DT / 60, np.median(runs) * DT / 60), flush=True)
        else:
            print('  %-11s nunca acendeu' % k, flush=True)
    print('  o estalo acendeu o medo: %s' % ', '.join(('d%d #%d %s' % (d, i, 'sim' if v else 'nao') for d, i, v in estalo_medo)), flush=True)
    print('  esquecimentos pelo teste de Page: %s' % (', '.join(('%s no dia %d as %.1f h' % (k, d, h) for d, h, k in esquec)) or 'nenhum'), flush=True)
    cheg = np.where(X[1:, iP] & ~X[:-1, iP])[0] + 1
    said = np.where(~X[1:, iP] & X[:-1, iP])[0] + 1
    perto_de = np.zeros(n, bool)
    linhas = []
    for c in cheg:
        j0 = max(0, c - int(20 * 60 / DT))
        perto_de[j0:c] = True
        linhas.append('d%d %.1fh %d%%' % (dia[c], hora[c], 100 * np.mean(reg['procura'][j0:c] > 0)))
    print('  a procura nos 20 min antes de cada chegada: %s' % ', '.join(linhas), flush=True)
    linhas = []
    for c in said:
        j1 = min(n, c + int(20 * 60 / DT))
        perto_de[c:j1] = True
        linhas.append('d%d %.1fh %d%%' % (dia[c], hora[c], 100 * np.mean(reg['procura'][c:j1] > 0)))
    print('  a procura nos 20 min depois de cada saida: %s' % ', '.join(linhas), flush=True)
    sem = acordado & ~X[:, iP] & ~perto_de
    print('  a procura no resto do tempo sem Gabriel, acordado: %.1f%%' % (100 * np.mean(reg['procura'][sem] > 0)), flush=True)
    for d in range(1, Q.N_DIAS + 1):
        md = (dia == d) & acordado
        com = md & X[:, iP]
        print('  dia %d: apego com Gabriel ali %5.1f%%; querer com a bola ali %5.1f%%; frustracao %4.1f min; saudade %4.1f%%' % (d, 100 * np.mean(reg['apego'][com] > 0) if com.any() else 0.0, 100 * np.mean(reg['querer'][md & X[:, iB]] > 0) if (md & X[:, iB]).any() else 0.0, np.sum(reg['frustracao'][md] > 0) * DT / 60, 100 * np.mean(reg['saudade'][md] > 0)), flush=True)
    dur_i = np.where(duro & acordado)[0]
    um_min = int(60 / DT)
    apos = [bool(reg['alegria'][min(n - 1, i + um_min)] == 0) for i in dur_i]
    bons = np.where(X[:, iV] & X[:, iTB] & acordado)[0]
    apos_b = [bool(reg['alegria'][min(n - 1, i + um_min)] == 0) for i in bons]
    print('  o contagio: 1 min depois de um tom duro, a alegria apagada em %d de %d (%.0f%%); depois de um tom bom, em %d de %d (%.0f%%)' % (sum(apos), len(apos), 100 * np.mean(apos) if apos else 0, sum(apos_b), len(apos_b), 100 * np.mean(apos_b) if apos_b else 0), flush=True)
    desc_acord = acordado & ~X[:, iP]
    print('  o narrador: %d episodios na semana; no descanso acordado sem Gabriel, revivendo em %.0f%% dos passos' % (len(historia), 100 * np.mean(revive[desc_acord] >= 0)), flush=True)

def main():
    conta()
    if '--vida' in sys.argv:
        relatorio(*vida())
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
