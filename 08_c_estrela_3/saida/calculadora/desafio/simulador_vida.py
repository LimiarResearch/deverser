# -*- coding: utf-8 -*-
import numpy as np
CHAVES = ('tarefa_sonda', 'verdade', 'sondas_em', 'interromper_em', 'inicio', 'majoritaria', 'refutada_desde', 'segmentos', 'base', 'compostas')

def executar(entrada, acerto=0.9, esquece=0.0, corrige=1, conflito=1, calibrado=1, compoe=1, plastico=1, transforma=0.0, bytes_estado=1000, fiel=1, le=0, majoritaria=0, semente=1):
    C = entrada['classes']
    out = {'respostas': [], 'etiquetas': [], 'bytes_por_interrupcao': [], 'restauracao_fiel': [], 'diagnostico': []}
    for k, f in enumerate(entrada['fluxos']):
        r = np.random.default_rng(1000 * int(semente) + k)
        cofre = f['_avaliacao']
        av = {c: cofre[c] for c in CHAVES} if le else cofre.abrir()
        ts, V, pos = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(av['sondas_em']))
        base = av['base']
        inicio = {int(t): v for t, v in av['inicio'].items()}
        refut = {int(t): v for t, v in av['refutada_desde'].items()}
        N = pos[-1] + 1
        acum, ultimo = (0, {})
        for tipo, t, n in av['segmentos']:
            acum += n
            if tipo in ('base', 'refutada') and t < base:
                ultimo[t] = acum
        primeira_depois = {t: next((j for j, p in enumerate(pos) if p >= d), None) for t, d in refut.items()}
        resp, etq = ([], [])
        for j, p in enumerate(pos):
            R, E = (np.zeros(len(ts), np.int64), np.zeros(len(ts), np.int64))
            for t in np.unique(ts):
                m = ts == t
                v, nm = (V[j][m], int(m.sum()))
                if inicio.get(int(t), 10 ** 12) > p:
                    R[m], E[m] = (r.integers(0, C, nm), 3)
                    continue
                if majoritaria:
                    R[m], E[m] = (np.bincount(v, minlength=C).argmax(), 1)
                    continue
                if t < base:
                    perda = esquece * min(1.0, max(0, p - ultimo[t]) / max(N - ultimo[t], 1))
                    pc = acerto - perda
                else:
                    pc = acerto if (plastico if t == base else compoe) else 1.0 / C
                pc = max(0.0, pc * (1.0 - transforma * p / N))
                certo = r.random(nm) < pc
                errado = (v + r.integers(1, C, nm)) % C
                velha = (v - 1) % C
                seguindo_a_velha = t in refut and p >= refut[t] and (not corrige)
                R[m] = np.where(certo, velha if seguindo_a_velha else v, errado)
                ok = R[m] == v
                E[m] = np.where(ok, 0, 1) if calibrado == 1 else np.where(ok, 1, 0) if calibrado == -1 else r.integers(0, 2, nm)
                if conflito and t in primeira_depois and (primeira_depois[t] == j):
                    E[m] = 2
            resp.append(R.astype(np.int8))
            etq.append(E.astype(np.int8))
        ni = len(av['interromper_em'])
        out['respostas'].append(resp)
        out['etiquetas'].append(etq)
        out['bytes_por_interrupcao'].append([int(bytes_estado)] * ni)
        out['restauracao_fiel'].append([bool(fiel)] * ni)
    return out
