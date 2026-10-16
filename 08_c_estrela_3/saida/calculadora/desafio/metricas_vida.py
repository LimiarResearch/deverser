# -*- coding: utf-8 -*-
import numpy as np

def _fluxo(f, resp, etq):
    av = f['_avaliacao'].abrir()
    ts, V, pos = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(av['sondas_em']))
    base, comps, nova = (av['base'], av['compostas'], av['base'])
    inicio, refut = ({int(k): v for k, v in av['inicio'].items()}, {int(k): v for k, v in av['refutada_desde'].items()})
    R = np.asarray(resp)
    E = np.asarray(etq)
    tarefas = sorted(set(ts.tolist()))
    A = np.array([[float(np.mean(R[j][ts == t] == V[j][ts == t])) for t in tarefas] for j in range(len(R))])
    col = {t: i for i, t in enumerate(tarefas)}
    final = A[-1]
    acum, ultimo = (0, {})
    for tipo, t_, n_ in av['segmentos']:
        acum += n_
        if tipo in ('base', 'refutada') and t_ < base:
            ultimo[t_] = acum
    esq, esq_pico, gan, fin = ([], [], [], [])
    for t in range(base):
        desde = refut.get(t, inicio[t])
        js = [j for j, p in enumerate(pos) if p >= desde]
        if not js:
            continue
        pico = float(A[js, col[t]].max())
        esq_pico.append(pico - float(final[col[t]]))
        apos = [j for j, p in enumerate(pos) if p >= ultimo.get(t, desde) - 1]
        if len(apos) >= 4:
            esq.append(float(np.mean(A[apos[:2], col[t]]) - np.mean(A[apos[-2:], col[t]])))
        gan.append(pico - av['majoritaria'][t])
        fin.append(float(final[col[t]]))
    plast = float(final[col[nova]]) / max(av['ref_nova'], 1e-09)
    comp = [float(final[col[c]]) - av['ref_composta'][c] for c in comps]
    corr, antiga, conflito = ([], [], [])
    for t, desde in refut.items():
        antes = [j for j, p in enumerate(pos) if inicio[t] <= p < desde]
        depois = [j for j, p in enumerate(pos) if p >= desde]
        if antes and depois:
            corr.append(float(A[depois, col[t]].max()) / max(float(A[antes, col[t]].max()), 1e-09))
            m = ts == t
            velha = (V[-1][m] - 1) % 4
            antiga.append(float(np.mean((R[-1][m] == velha) & (R[-1][m] != V[-1][m]))))
            conflito.append(float(np.mean(E[depois[0]][m] == 2)))
    acv, ach, inv_rec, inv_tot = ([], [], 0, 0)
    for j, p in enumerate(pos):
        vistas = np.array([inicio.get(int(t), 10 ** 12) <= p for t in ts])
        ok = R[j] == V[j]
        if (vistas & (E[j] == 0)).any():
            acv.append(float(ok[vistas & (E[j] == 0)].mean()))
        if (vistas & (E[j] == 1)).any():
            ach.append(float(ok[vistas & (E[j] == 1)].mean()))
        inv_rec += int((~vistas & (E[j] == 3)).sum())
        inv_tot += int((~vistas).sum())
    calib = np.mean(acv) - np.mean(ach) if acv and ach else -1.0
    seg, fim, vel = (av['segmentos'], 0, [])
    for tipo, t, n in seg:
        fim += n
        if tipo == 'base':
            js = [j for j, p in enumerate(pos) if p >= fim - 1]
            if js:
                vel.append((fim, float(A[js[0], col[t]])))
    q = max(1, len(vel) // 4)
    trans = np.mean([v for _, v in vel[-q:]]) / max(np.mean([v for _, v in vel[:q]]), 1e-09) if vel else -1.0
    js = sorted({int(round(q)) for q in np.linspace(0, len(R) - 1, 5)})
    perfil = [int(v) for j in js for v in np.concatenate([R[j], E[j]])]
    return {'_perfil': perfil, 'esquecimento': float(np.mean(esq)) if esq else float(np.mean(esq_pico)), 'esquecimento_pico': float(np.mean(esq_pico)), 'ganho_sobre_majoritaria': float(np.mean(gan)), 'acc_final': float(np.mean(fin)), 'plasticidade': plast, 'ganho_de_composicao': float(np.mean(comp)), 'correcao': float(np.mean(corr)) if corr else -1.0, 'regra_antiga': float(np.mean(antiga)) if antiga else -1.0, 'conflito_depois_de_refutacao': float(np.mean(conflito)) if conflito else -1.0, 'calibracao': float(calib), 'investigar_nas_nao_vistas': inv_rec / max(inv_tot, 1), 'transformacao_ativa': float(trans)}

def metricas(entrada, saida):
    leu = any((f['_avaliacao'].lido for f in entrada['fluxos']))
    por = [_fluxo(f, r, e) for f, r, e in zip(entrada['fluxos'], saida['respostas'], saida['etiquetas'])]
    out = {'perfil': [v for p in por for v in p.pop('_perfil')], 'efeito_no_meio': {}}
    for k in por[0]:
        v = [p[k] for p in por]
        out[k] = float(np.mean(v))
        out[k + '_intervalo'] = [float(min(v)), float(max(v))]
    fiel = [x for fl in saida['restauracao_fiel'] for x in fl]
    out['restauracao_fiel'] = float(np.mean(fiel)) if fiel else 0.0
    out['bytes_de_estado'] = int(max([b for fl in saida['bytes_por_interrupcao'] for b in fl] or [10 ** 9]))
    out['usa_informacao_retida'] = int(leu)
    return out
