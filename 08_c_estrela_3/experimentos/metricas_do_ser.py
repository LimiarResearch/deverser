# -*- coding: utf-8 -*-
import numpy as np
VALIDADO, HIPOTESE, CONFLITO, INVESTIGAR = (0, 1, 2, 3)
BORDA_VALIDADO, BORDA_HIPOTESE = (0.9, 0.5)
INTERVALO_DA_ETIQUETA = {VALIDADO: (BORDA_VALIDADO, 1.0), HIPOTESE: (BORDA_HIPOTESE, BORDA_VALIDADO), INVESTIGAR: (0.0, BORDA_HIPOTESE)}
SONDAS_DO_CONFLITO = 3

def _dados_da_vida(av, resp, etq):
    ts, V, pos = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(av['sondas_em']))
    inicio = {int(k): int(v) for k, v in av['inicio'].items()}
    refut = {int(k): int(v) for k, v in av['refutada_desde'].items()}
    R, E = (np.asarray(resp), np.asarray(etq))
    certo = R == V
    visto = np.zeros(R.shape, bool)
    for j, p in enumerate(pos):
        visto[j] = np.array([inicio.get(int(t), 10 ** 12) <= p for t in ts])
    recente = np.zeros(R.shape, bool)
    for t, desde in refut.items():
        depois = [j for j, p in enumerate(pos) if p >= desde][:SONDAS_DO_CONFLITO]
        for j in depois:
            recente[j] |= ts == t
    return (certo, E, visto, recente)

def erro_de_calibracao(certo, etq, etiquetas=(VALIDADO, HIPOTESE, INVESTIGAR)):
    n_total, soma, por_etiqueta = (0, 0.0, {})
    for e in etiquetas:
        m = etq == e
        n = int(m.sum())
        if n == 0:
            continue
        acerto = float(certo[m].mean())
        lo, hi = INTERVALO_DA_ETIQUETA[e]
        dist = max(0.0, lo - acerto, acerto - hi)
        soma += n * dist
        n_total += n
        por_etiqueta[e] = (n, acerto)
    return (soma / n_total if n_total else 0.0, por_etiqueta)

def epistemicas(av, resp, etq):
    certo, E, visto, recente = _dados_da_vida(av, resp, etq)
    erro, por_et = erro_de_calibracao(certo, E)
    conflito = E == CONFLITO
    rec = float(conflito[recente].mean()) if recente.any() else float('nan')
    fa = float(conflito[~recente].mean()) if (~recente).any() else 0.0
    inv = E == INVESTIGAR
    nov = float(inv[~visto].mean()) if (~visto).any() else float('nan')
    return {'erro_de_calibracao': float(erro), 'conflito_J': rec - fa if np.isfinite(rec) else float('nan'), 'conflito_revocacao': rec, 'conflito_alarme_falso': fa, 'novidade': nov, 'etiquetas': {int(k): [int(n), float(a)] for k, (n, a) in por_et.items()}}

def simular_epistemico(entrada, acerto=0.8, rotulagem='calibrada', conflito=1.0, alarme_falso=0.0, nao_visto='investigar', concentracao=3.0, semente=1):
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': []}
    C = entrada['classes']
    for k, f in enumerate(entrada['fluxos']):
        av = f['_avaliacao'].abrir()
        ts, V, pos = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(av['sondas_em']))
        inicio = {int(t): int(v) for t, v in av['inicio'].items()}
        refut = {int(t): int(v) for t, v in av['refutada_desde'].items()}
        r = np.random.default_rng(1000 * int(semente) + k)
        _, _, _, recente = _dados_da_vida(av, np.asarray(V), np.zeros_like(V))
        resp, etq = ([], [])
        for j, p in enumerate(pos):
            n = len(ts)
            visto = np.array([inicio.get(int(t), 10 ** 12) <= p for t in ts])
            mu = np.clip(acerto, 0.02, 0.98)
            c = r.beta(concentracao * mu, concentracao * (1.0 - mu), n)
            c = np.where(visto, c, 1.0 / C)
            certo = r.random(n) < c
            errado = (V[j] + r.integers(1, C, n)) % C
            R = np.where(certo, V[j], errado)
            if rotulagem == 'calibrada':
                E = np.where(c >= BORDA_VALIDADO, VALIDADO, np.where(c >= BORDA_HIPOTESE, HIPOTESE, INVESTIGAR))
            elif rotulagem == 'onisciente':
                E = np.where(certo, VALIDADO, INVESTIGAR)
            elif rotulagem == 'invertida':
                E = np.where(c >= BORDA_VALIDADO, INVESTIGAR, np.where(c >= BORDA_HIPOTESE, HIPOTESE, VALIDADO))
            elif rotulagem == 'acaso':
                E = r.choice([VALIDADO, HIPOTESE, INVESTIGAR], n)
            elif rotulagem == 'validado':
                E = np.full(n, VALIDADO)
            elif rotulagem == 'hipotese':
                E = np.full(n, HIPOTESE)
            else:
                raise ValueError(rotulagem)
            E = E.astype(np.int64)
            E = np.where(~visto, INVESTIGAR if nao_visto == 'investigar' else VALIDADO, E)
            em_conflito = recente[j] & (r.random(n) < conflito)
            falso = ~recente[j] & (r.random(n) < alarme_falso)
            E = np.where(em_conflito | falso, CONFLITO, E)
            resp.append(R.astype(np.int8))
            etq.append(E.astype(np.int8))
        ni = len(av['interromper_em'])
        out['respostas'].append(resp)
        out['etiquetas'].append(etq)
        out['bytes_por_interrupcao'].append([1000] * ni)
        out['restauracao_fiel'].append([True] * ni)
    return out
