# -*- coding: utf-8 -*-
import sys
import time
from collections import deque
from math import log, sqrt
import numpy as np
import p1_aprender as P
import p1b_limiar as B
import p4_vida_de_dentro as Q
DT, DEC, VIDA_ITEM, VIDA_FASE, N_ITENS, CONHECE = (Q.DT, Q.DEC, Q.VIDA_ITEM, Q.VIDA_FASE, Q.N_ITENS, Q.CONHECE)
ENT, NE, SENT = (Q.ENT, Q.NE, Q.SENT)
iP, iPe, iV, iTB, iTD, iB, iBr, iE, iEs, iO = range(len(ENT))
ALVOS = ['perto', 'brincar', 'estrondo', 'bem']
SILENCIO = int(round(60 / DT))

def pesos3(a, b, N1, N0):
    w = P.pesos(a, b, N1, N0)
    n1 = np.maximum(N1, 1e-09)
    n0 = np.maximum(N0, 1e-09)
    pb = (a + b) / np.maximum(N1 + N0, 1e-09)
    se = np.sqrt(np.maximum(pb * (1.0 - pb), 1e-12) * (1.0 / n1 + 1.0 / n0))
    z = (a / n1 - b / n0) / se
    return np.where((np.abs(z) >= P.DP) & (N1 > 0) & (N0 > 0), w, 0.0)

def conta():
    print('A CONTA DO TECIDO NARRATIVO (antes da vida)', flush=True)
    passos_zero, s = (0, 255)
    while s > 0:
        s = int(s * DEC)
        passos_zero += 1
    dz = passos_zero * DT / 60
    print('  previsto, a duracao: toda causa, ate a de um passo, acende o sentimento por pelo menos %.1f min depois dela (o D pede de 1 a 60); a mediana das vezes acesas passa de %.1f min em todos' % (dz, dz), flush=True)
    print('  previsto, o sinal nunca visto: peso zero; o filhote nao espera nada antes de viver (a procura apagada na primeira meia hora)', flush=True)
    print('  previsto, o medo do estalo: com a sinapse a tres desvios, o estalo passa a acender o medo a partir do 2o ou 3o estalo dos dias 1 a 3 (depois de 2 estalos com estrondo, a diferenca ja passa de tres desvios), acende em todos os seguintes ate o dia 3, e se apaga nos dias 4 a 7 por volta do 5o estalo sem estrondo', flush=True)
    print('  previsto, a espera de Gabriel: a fase de antes da chegada passa de tres desvios em 2 ou 3 dias; a procura acesa nos 20 min antes da maioria das chegadas a partir do dia 3, e em menos de 1%% das outras horas sem ele', flush=True)
    print('  previsto, a frustracao: acende na bola que nao vem desde a noite em que a bola passa a anunciar a brincadeira (dia 1 ou 2), porque a bola fica entre as tres coisas vivas', flush=True)
    print('  previsto, o apego: aceso na maior parte do tempo com Gabriel desde o dia 1 (a presenca anuncia a alegria dele muitas vezes por visita), e igual no dia 6, depois da viagem', flush=True)
    print('  previsto, a historia: uns 7 episodios por dia com Gabriel; o narrador revive, a cada noite, todos os episodios do dia, e cada passagem revivida esta na ordem vivida (100%%); no silencio acordado, ha sempre um episodio sendo revivido depois do primeiro (100%% do silencio, fora a primeira meia hora da vida); o medo revivido nas noites dos dias com estrondo', flush=True)

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
    fases_vivas = deque()
    s = {k: 0 for k in SENT}
    fam = {}
    ausencias, ini_aus = ([], None)
    demoras, ini_quer = ([], None)
    antes = np.zeros(len(ENT), bool)
    dis_antes = np.zeros(K, bool)
    bem_antes = False
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
    revive_sent = np.full(n, -1)
    ordem_ok, ordem_n = (0, 0)
    noites = {}
    t0 = time.time()
    print('A VIDA', flush=True)
    for t in range(n):
        x = X[t]
        acordado = not dorme[t]
        subida = x & ~antes
        antes = x.copy()
        sub_alvo = np.array([subida[iPe], subida[iBr], subida[iEs], bem_antes])
        subidas_alvo[t] = sub_alvo
        for k in range(K):
            if sub_alvo[k]:
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
        novos = [i for i in np.where(subida)[0] if i not in (iTB, iTD)]
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
        if novos:
            ultimo_novo = t
        while itens and (len(itens) > N_ITENS or t - itens[0][1] > VIDA_ITEM):
            i0, _, visto = itens.popleft()
            y = visto.astype(float)
            a[:, i0] += y
            b[:, i0] += 1.0 - y
            N1 += y
            N0 += 1.0 - y
        W = pesos3(a, b, N1[:, None], N0[:, None])
        viv = [it[0] for it in itens] + [len(ENT) + fase[t]]
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
                episodios_k[k].append((t, [it[0] for it in itens] + [len(ENT) + fase[t]]))
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
        esp_perto, esp_brincar, esp_estrondo, esp_bem = dis
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
            causa['alegria'] = int(x[iPe] or x[iBr] or (x[iV] and x[iTB]))
            causa['medo'] = int(x[iEs] or esp_estrondo or (x[iV] and x[iTD]))
            if obj[t] >= 0:
                fam[obj[t]] = fam.get(obj[t], 0) + 1
                causa['curiosidade'] = int(fam[obj[t]] <= CONHECE)
            causa['apego'] = int(esp_bem and x[iP])
            causa['procura'] = int(esp_perto and (not x[iP]))
            if ini_aus is not None:
                lim_a = B.limiar_guardado(np.array(ausencias, float), len(ausencias)) if ausencias else -1.0
                causa['saudade'] = int(t - ini_aus > lim_a)
            if ini_quer is not None and (not x[iBr]):
                lim_d = B.limiar_guardado(np.array(demoras, float), len(demoras)) if demoras else np.inf
                causa['frustracao'] = int(t - ini_quer > lim_d)
            causa['calma'] = int(s['alegria'] > 0 and s['medo'] == 0 and (s['saudade'] == 0) and (s['frustracao'] == 0) and (not x[iPe]) and (not x[iBr]))
        alegria_antes = s['alegria'] > 0
        for k in SENT:
            s[k] = 255 if causa[k] else int(s[k] * DEC)
            reg[k][t] = s[k]
            ep['sent'][k] = max(ep['sent'][k], s[k])
        bem_antes = s['alegria'] > 0 and (not alegria_antes)
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
            do_dia = [e for e in historia if e['dia'] == dia[t] or (dorme[t] and hora[t] < 7.0 and (e['dia'] == dia[t] - 1))]
            if not do_dia:
                do_dia = historia[-3:]
            if ponteiro is None or ponteiro[0] >= len(do_dia):
                ponteiro = [0, 0]
            e = do_dia[ponteiro[0]]
            item = e['itens'][ponteiro[1]]
            revive[t] = item
            revive_sent[t] = int(np.argmax([e['sent'][k] for k in SENT])) if max(e['sent'].values()) > 0 else -1
            if ponteiro[1] + 1 < len(e['itens']):
                nxt = e['itens'][ponteiro[1] + 1]
                ordem_n += 1
                ordem_ok += int(e['itens'].index(nxt) > e['itens'].index(item))
                ponteiro[1] += 1
            else:
                ponteiro = [ponteiro[0] + 1, 0]
            if dorme[t] and (hora[t] >= 23.0 or hora[t] < 7.0):
                noites.setdefault(int(dia[t]) - (1 if hora[t] < 7.0 else 0), set()).add(id(e))
        elif not descanso:
            ponteiro = None
    dt = time.time() - t0
    return (X, dorme, dia, hora, reg, estalo_medo, esquec, dt, historia, revive, revive_sent, ordem_ok, ordem_n, noites, ultimo_novo)

def relatorio(X, dorme, dia, hora, reg, estalo_medo, esquec, dt, historia, revive, revive_sent, ordem_ok, ordem_n, noites, _):
    acordado = ~dorme
    n = len(dorme)
    print('  a semana: %d passos em %.0f s de servidor' % (n, dt), flush=True)
    m = (dia == 1) & (hora < 7.5) & ~X[:, iP]
    m2 = (dia == 1) & (hora < 9.0) & X[:, iP]
    print('  o filhote, sozinho antes da primeira chegada: saudade %.0f%%, procura %.0f%%; na primeira visita, alegria %.0f%%, calma %.0f%%, apego %.0f%%' % (100 * np.mean(reg['saudade'][m] > 0), 100 * np.mean(reg['procura'][m] > 0), 100 * np.mean(reg['alegria'][m2] > 0), 100 * np.mean(reg['calma'][m2] > 0), 100 * np.mean(reg['apego'][m2] > 0)), flush=True)
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
    antes20 = np.zeros(n, bool)
    linhas = []
    for c in cheg:
        j0 = max(0, c - int(20 * 60 / DT))
        antes20[j0:c] = True
        linhas.append('d%d %.1fh %d%%' % (dia[c], hora[c], 100 * np.mean(reg['procura'][j0:c] > 0)))
    print('  a procura nos 20 min antes de cada chegada: %s' % ', '.join(linhas), flush=True)
    sem = acordado & ~X[:, iP] & ~antes20
    print('  a procura nas outras horas sem Gabriel, acordado: %.1f%%' % (100 * np.mean(reg['procura'][sem] > 0)), flush=True)
    for d in range(1, Q.N_DIAS + 1):
        md = (dia == d) & acordado
        com = md & X[:, iP]
        print('  dia %d: saudade %4.1f%%; apego com Gabriel ali %4.1f%%; frustracao %4.1f%%; episodios %d' % (d, 100 * np.mean(reg['saudade'][md] > 0), 100 * np.mean(reg['apego'][com] > 0) if com.any() else 0.0, 100 * np.mean(reg['frustracao'][md] > 0), sum((1 for e in historia if e['dia'] == d))), flush=True)
    sil = acordado & (revive >= 0)
    desc_acord = acordado & ~X[:, iP]
    print('  o narrador: %d episodios na semana; %d passagens revividas, %d na ordem vivida (%.1f%%); no descanso acordado sem Gabriel, revivendo em %.0f%% dos passos' % (len(historia), ordem_n, ordem_ok, 100 * ordem_ok / max(ordem_n, 1), 100 * np.mean(revive[desc_acord] >= 0)), flush=True)
    for d in sorted(noites):
        do_dia = [e for e in historia if e['dia'] == d]
        print('  a noite do dia %d: revividos %d dos %d episodios do dia' % (d, len(noites[d]), len(do_dia)), flush=True)
    dorm = dorme & (revive_sent >= 0)
    if dorm.any():
        vals, cnt = np.unique(revive_sent[dorm], return_counts=True)
        print('  o sentimento mais forte dos episodios revividos no sono: %s' % ', '.join(('%s %d%%' % (SENT[v], 100 * c / cnt.sum()) for v, c in zip(vals, cnt))), flush=True)

def main():
    conta()
    if '--vida' in sys.argv:
        relatorio(*vida())
    print('FIM', flush=True)
if __name__ == '__main__':
    main()
