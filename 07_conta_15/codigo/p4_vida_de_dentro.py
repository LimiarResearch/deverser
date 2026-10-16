# -*- coding: utf-8 -*-
import sys
import time
from collections import deque
from math import exp, log, sqrt
import numpy as np
import p1_aprender as P
import p1b_limiar as B
DT = 5.0
DIA = 86400.0
N_DIAS = 7
T0 = 7 * 3600.0
PASSOS = int((N_DIAS * DIA - T0) / DT)
TAU = sqrt(1.0 * 60.0) * 60.0
DEC = exp(-DT / TAU)
INC = int(round(255 * (1.0 - DEC)))
VIDA_ITEM = int(round(4 * 60 / DT))
VIDA_FASE = int(round(14 * 60 / DT))
N_ITENS = 3
FASES = 144
CONHECE = int(round(4 * P.DP * P.DP))
SEMENTE = 20260926
ENT = ['presenca', 'perto', 'voz', 'tom_bom', 'tom_duro', 'bola', 'brincar', 'estalo', 'estrondo', 'objeto']
NE = len(ENT) + FASES
ALVOS = ['perto', 'brincar', 'estrondo']
SENT = ['alegria', 'medo', 'curiosidade', 'apego', 'procura', 'saudade', 'frustracao', 'calma']
iP, iPe, iV, iTB, iTD, iB, iBr, iE, iEs, iO = range(len(ENT))

def mundo(duro=0.95):
    rng = np.random.default_rng(SEMENTE)
    n = PASSOS
    X = np.zeros((n, len(ENT)), bool)
    t_abs = T0 + DT * np.arange(n)
    dia = (t_abs // DIA).astype(int) + 1
    hora = t_abs % DIA / 3600.0
    dorme = (hora >= 23.0) | (hora < 7.0) | (hora >= 13.5) & (hora < 16.5)
    fase = (t_abs % DIA // 600).astype(int)
    obj = np.full(n, -1)
    for d in range(1, N_DIAS + 1):
        base = (d - 1) * DIA - T0
        visitas = [] if d == 5 else [(7.5, 0.75), (12.0, 0.75), (18.5, None)]
        for h, dur in visitas:
            ini = h * 3600.0 + rng.normal(0, 15 * 60)
            fim = ini + dur * 3600.0 if dur is not None else 22.5 * 3600.0
            a, b = (max(int((base + ini) / DT), 0), min(int((base + fim) / DT), n))
            if a >= b:
                continue
            X[a:b, iP] = True
            t = a
            while t < b:
                L = int(rng.exponential(5 * 60 / DT)) + 1
                if rng.random() < 0.5:
                    X[t:min(t + L, b), iPe] = True
                t += L
            for t in range(a, b):
                if rng.random() < 0.3:
                    X[t, iV] = True
                    u = rng.random()
                    X[t, iTB] = u < 0.8
                    X[t, iTD] = u > duro
            if dur is None:
                for k in range(3):
                    tb = a + int((0.5 + k) * (b - a) / 3.5)
                    if k < 2:
                        X[tb:tb + int(6 * 60 / DT), iB] = True
                        X[tb + int(60 / DT):tb + int(6 * 60 / DT), iBr] = True
                    else:
                        X[tb:tb + int(6 * 60 / DT), iB] = True
        for k in range(3):
            t = int((base + (9.0 + rng.random() * 9.0) * 3600.0) / DT)
            if 0 <= t < n - 2:
                X[t, iE] = True
                if d <= 3:
                    X[t + 2, iEs] = True
        t = int((base + (9.0 + rng.random() * 9.0) * 3600.0) / DT)
        if 0 <= t < n:
            X[t, iEs] = True
        t = int((base + 10.0 * 3600.0) / DT)
        if 0 <= t < n:
            X[t:t + 1, iO] = True
            obj[t:] = d
    return (X, fase, dorme, dia, hora, obj)

def conta():
    print('A CONTA DA VIDA DE DENTRO (antes da vida)', flush=True)
    passos_zero, s = (0, 255)
    while s > 0:
        s = int(s * DEC)
        passos_zero += 1
    print('  a constante dos sentimentos: %.2f min; o byte sobe %d por passo com a causa; depois dela, de 255 ate 0 em %d passos, %.1f min (o D pede de 1 a 60)' % (TAU / 60, INC, passos_zero, passos_zero * DT / 60), flush=True)
    print('  previsto: cada sentimento fica aceso no maximo %.1f min depois da causa; nenhum acende sem causa' % (passos_zero * DT / 60), flush=True)
    print('  previsto, o filhote: na primeira meia hora, sozinho, a saudade acesa em quase todos os passos (ele nunca viu uma ausencia); com o contato, a alegria, e depois dela a calma', flush=True)
    print('  previsto, a saudade: no dia 1 ela acende a cada ausencia mais longa que as ja vistas (o filhote aprendendo que Gabriel volta); nos dias 2, 3, 4, 6 e 7 ela nao acende; no dia 5, acende quando a ausencia passa da mais longa ja vista, a da noite (umas 9 h), por volta das 7h30, e fica acesa enquanto ele esta acordado', flush=True)
    print('  previsto, o medo aprendido: o estalo passa a acender a espera do estrondo entre o 2o e o 6o estalo dos dias 1 a 3 (o intervalo da p1b), e ela se apaga nos dias 4 a 7 por volta do 5o estalo sem estrondo (o teste de Page da p1b)', flush=True)
    print('  previsto, a espera de Gabriel: a procura acende nos 20 min antes das chegadas a partir do dia 3 ou 4 (a fase de antes da chegada precisa do 2o ao 8o anuncio, e cada dia da um), e quase nunca nas outras horas sem ele', flush=True)
    print('  previsto, a frustracao: acende na bola que nao vem, das noites em que a bola ja anuncia a brincadeira em diante, quando a espera passa da mais longa ja vista (1 min)', flush=True)
    print('  previsto, o apego: acende com Gabriel ali desde o primeiro dia, e continua no dia 6, depois da viagem, porque a ausencia nao desmente nada', flush=True)
    print('  previsto, o repassar: no sono, toda passagem repassada foi vivida naquela ordem, bem acima da chance de um par ao acaso ter sido vivido, a tres desvios', flush=True)

def vida():
    X, fase, dorme, dia, hora, obj = mundo()
    n = len(fase)
    K = len(ALVOS)
    alvo_idx = [ENT.index(a) for a in ALVOS]
    a = np.zeros((K, NE))
    b = np.zeros((K, NE))
    N1, N0 = (np.zeros(K), np.zeros(K))
    buf = np.zeros((K, B.N_GUARDA))
    nbuf, pos = (np.zeros(K, int), np.zeros(K, int))
    Fk, Hk, C = (np.zeros(K), np.zeros(K), np.zeros(K))
    falhas = [[] for _ in range(K)]
    episodios = [deque() for _ in range(K)]
    itens = deque()
    fases_vivas = deque()
    T = np.zeros((NE, NE))
    ultimo_item = -1
    s = {k: 0 for k in SENT}
    fam = {}
    ausencias, ini_aus = ([], None)
    demoras, ini_quer = ([], None)
    antes = np.zeros(len(ENT), bool)
    dis_antes = np.zeros(K, bool)
    reg = {k: np.zeros(n, np.uint8) for k in SENT}
    score_linha = np.zeros((VIDA_ITEM, K))
    estalo_medo, estalo_n, esquec = ([], 0, [])
    repasses = []
    fase_atual = -1
    t0 = time.time()
    print('A VIDA', flush=True)
    for t in range(n):
        x = X[t]
        acordado = not dorme[t]
        subida = x & ~antes
        antes = x.copy()
        for k, ia in enumerate(alvo_idx):
            if subida[ia]:
                for item in itens:
                    item[2][k] = True
                for fz in fases_vivas:
                    fz[2][k] = True
        if fase[t] != fase_atual:
            fase_atual = fase[t]
            fases_vivas.append([t, len(ENT) + fase[t], np.zeros(K, bool)])
        while fases_vivas and t - fases_vivas[0][0] > VIDA_FASE:
            _, fb, visto = fases_vivas.popleft()
            y = visto.astype(float)
            a[:, fb] += y
            b[:, fb] += 1.0 - y
            N1 += y
            N0 += 1.0 - y
        for i in np.where(subida)[0]:
            if i in (iTB, iTD):
                continue
            for j, _, _ in itens:
                T[j, i] += 1
            itens.append((i, t, np.zeros(K, bool)))
            ultimo_item = i
            if i == iE:
                estalo_n += 1
        while itens and (len(itens) > N_ITENS or t - itens[0][1] > VIDA_ITEM):
            i0, _, visto = itens.popleft()
            y = visto.astype(float)
            a[:, i0] += y
            b[:, i0] += 1.0 - y
            N1 += y
            N0 += 1.0 - y
        W = P.pesos(a, b, N1[:, None], N0[:, None])
        viv = [it[0] for it in itens] + [len(ENT) + fase[t]]
        sc = W[:, viv].sum(axis=1)
        thr = np.array([B.limiar_guardado(buf[k], nbuf[k]) for k in range(K)])
        dis = sc > thr
        if t >= VIDA_ITEM:
            tt = t - VIDA_ITEM
            veio = (X[tt + 1:t + 1][:, alvo_idx] & ~X[tt:t][:, alvo_idx]).any(axis=0)
            for k in range(K):
                if not veio[k]:
                    buf[k, pos[k]] = score_linha[tt % VIDA_ITEM, k]
                    pos[k] = (pos[k] + 1) % B.N_GUARDA
                    nbuf[k] = min(nbuf[k] + 1, B.N_GUARDA)
        score_linha[t % VIDA_ITEM] = sc
        for k in range(K):
            if dis[k] and (not dis_antes[k]):
                episodios[k].append((t, [it[0] for it in itens] + [len(ENT) + fase[t]]))
            while episodios[k] and (subida[alvo_idx[k]] or t - episodios[k][0][0] > VIDA_ITEM):
                t_e, bits = episodios[k].popleft()
                ok = bool(subida[alvo_idx[k]])
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
        if x[iB] and esp_brincar and (ini_quer is None):
            ini_quer = t
        if ini_quer is not None and subida[iBr]:
            demoras.append(t - ini_quer)
            ini_quer = None
        if ini_quer is not None and (not x[iB]):
            ini_quer = None
        causa = {k: 0 for k in SENT}
        if acordado:
            causa['alegria'] = int(x[iPe]) + int(x[iBr]) + int(x[iV] and x[iTB])
            causa['medo'] = int(x[iEs]) + int(esp_estrondo) + int(x[iV] and x[iTD])
            if obj[t] >= 0:
                fam[obj[t]] = fam.get(obj[t], 0) + 1
                causa['curiosidade'] = int(fam[obj[t]] <= CONHECE)
            causa['apego'] = int(esp_perto and x[iP])
            causa['procura'] = int(esp_perto and (not x[iP]))
            if ini_aus is not None:
                lim_a = B.limiar_guardado(np.array(ausencias, float), len(ausencias)) if ausencias else -1.0
                causa['saudade'] = int(t - ini_aus > lim_a)
            if ini_quer is not None and (not x[iBr]):
                lim_d = B.limiar_guardado(np.array(demoras, float), len(demoras)) if demoras else np.inf
                causa['frustracao'] = int(t - ini_quer > lim_d)
            causa['calma'] = int(s['alegria'] > 0 and s['medo'] == 0 and (s['saudade'] == 0) and (s['frustracao'] == 0) and (not x[iPe]) and (not x[iBr]))
        for k in SENT:
            s[k] = min(255, int(s[k] * DEC) + INC * causa[k])
            reg[k][t] = s[k]
        if subida[iE]:
            estalo_medo.append((dia[t], estalo_n, bool(esp_estrondo)))
        if dorme[t] and (t == 0 or not dorme[t - 1]) and (ultimo_item >= 0):
            cad, cur = ([ultimo_item], ultimo_item)
            for _ in range(20):
                linha = T[cur].copy()
                linha[cur] = 0
                if linha.max() <= 0:
                    break
                cur = int(np.argmax(linha))
                cad.append(cur)
            repasses.append((dia[t], hora[t], cad))
    dt = time.time() - t0
    return (X, dorme, dia, hora, reg, estalo_medo, repasses, T, dt, esquec)

def relatorio(X, dorme, dia, hora, reg, estalo_medo, repasses, T, dt, esquec):
    acordado = ~dorme
    n = len(dorme)
    print('  a semana: %d passos de 5 s em %.0f s de servidor (%.4f s por segundo de vida)' % (n, dt, dt / (n * DT)), flush=True)
    m = (dia == 1) & (hora < 7.5) & ~X[:, iP]
    m2 = (dia == 1) & (hora < 9.0) & X[:, iP]
    print('  o filhote, sozinho antes da primeira chegada: saudade acesa em %.0f%% dos passos, alegria em %.0f%%; na primeira visita, alegria em %.0f%% e calma em %.0f%%' % (100 * np.mean(reg['saudade'][m] > 0), 100 * np.mean(reg['alegria'][m] > 0), 100 * np.mean(reg['alegria'][m2] > 0), 100 * np.mean(reg['calma'][m2] > 0)), flush=True)
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
    print('  o estalo acendeu a espera do estrondo: %s' % ', '.join(('d%d #%d %s' % (d, i, 'sim' if v else 'nao') for d, i, v in estalo_medo)), flush=True)
    print('  esquecimentos pelo teste de Page: %s' % (', '.join(('%s no dia %d as %.1f h' % (k, d, h) for d, h, k in esquec)) or 'nenhum'), flush=True)
    cheg = np.where(X[1:, iP] & ~X[:-1, iP])[0] + 1
    antes20 = np.zeros(n, bool)
    for c in cheg:
        j0 = max(0, c - int(20 * 60 / DT))
        antes20[j0:c] = True
        print('  chegada no dia %d as %5.2f h: a procura acesa em %3.0f%% dos 20 min antes' % (dia[c], hora[c], 100 * np.mean(reg['procura'][j0:c] > 0)), flush=True)
    sem = acordado & ~X[:, iP] & ~antes20
    print('  a procura nas outras horas sem Gabriel, acordado: %.1f%%' % (100 * np.mean(reg['procura'][sem] > 0)), flush=True)
    for d in range(1, N_DIAS + 1):
        md = (dia == d) & acordado
        com = md & X[:, iP]
        print('  dia %d: saudade em %4.1f%% do tempo acordado; apego com Gabriel ali em %4.1f%%; frustracao em %4.1f%%' % (d, 100 * np.mean(reg['saudade'][md] > 0), 100 * np.mean(reg['apego'][com] > 0) if com.any() else 0.0, 100 * np.mean(reg['frustracao'][md] > 0)), flush=True)
    vividos = [u for u in range(len(ENT)) if T[u].sum() + T[:, u].sum() > 0 and u not in (iTB, iTD)]
    pares = [(u, v) for u in vividos for v in vividos if u != v]
    f0 = np.mean([T[u, v] > 0 for u, v in pares]) if pares else 0.0
    acerto, total = (0, 0)
    for _, _, cad in repasses:
        for u, v in zip(cad[:-1], cad[1:]):
            total += 1
            acerto += int(T[u, v] > 0)
    z = (acerto - total * f0) / sqrt(max(total * f0 * (1 - f0), 1e-09)) if total else 0.0
    print('  o repassar: %d sonos, %d passagens repassadas, %d delas vividas naquela ordem; a chance de um par ao acaso ter sido vivido e %.2f; z = %.1f (o criterio, 3)' % (len(repasses), total, acerto, f0, z), flush=True)
    for d, h, cad in repasses[:3]:
        print('    no sono do dia %d as %.1f h: %s' % (d, h, ' > '.join((ENT[c] for c in cad[:10]))), flush=True)

def main():
    conta()
    if '--vida' in sys.argv:
        relatorio(*vida())
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
