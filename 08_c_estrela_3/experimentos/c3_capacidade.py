# -*- coding: utf-8 -*-
import json
import os
import sys
import time
from multiprocessing import Pool
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
CAPACIDADE = 3316

def _entropia(v):
    c = np.bincount(np.asarray(v, np.int64))
    p = c[c > 0] / c.sum()
    return float(-(p * np.log2(p)).sum())

def _eventos(f):
    p = f['abrir']()
    out = []
    while True:
        e = p()
        if e is None:
            return out
        out.append(e)

def demanda_da_vida(f):
    a = f['_avaliacao'].abrir()
    ev = _eventos(f)
    treino = {np.asarray(e[1], np.float32).tobytes() for e in ev if e[0] == 'treino'}
    sondas = [np.asarray(e[1], np.float32) for e in ev if e[0] == 'sonda']
    verdade = [np.asarray(v, np.int64) for v in a['verdade']]
    assert len(sondas) == len(verdade), (len(sondas), len(verdade))
    grupo_da_linha = np.asarray(a['tarefa_sonda']) if 'tarefa_sonda' in a else None
    pares = {}
    rotulos = {}
    no_treino = 0
    for k, (S, v) in enumerate(zip(sondas, verdade)):
        for j in range(len(S)):
            chave = S[j].tobytes()
            if chave in treino:
                no_treino += 1
                continue
            g = int(grupo_da_linha[j]) if grupo_da_linha is not None else hash(S.tobytes()) & 65535
            pares.setdefault(g, set()).add((chave, int(v[j])))
            rotulos.setdefault(g, []).append(int(v[j]))
    bits = sum((len(p) * _entropia(rotulos[g]) for g, p in pares.items()))
    return {'bits': round(float(bits), 1), 'pares': int(sum((len(p) for p in pares.values()))), 'grupos': len(pares), 'linhas_da_sonda_no_treino': int(no_treino), 'treino_sem_x': not treino}

def demanda_da_semente(semente):
    from experimentos import desafio_v_ser as V
    t0 = time.time()
    fam = V.gerar_familias(int(semente))
    por = {n: [demanda_da_vida(f) for f in fam[n]['fluxos']] for n in ('seq', 'ling', 'tri', 'age')}
    return {'semente': int(semente), 'bits': round(sum((v['bits'] for vs in por.values() for v in vs)), 1), 'por_familia': {n: {'vidas': len(vs), 'bits': round(sum((v['bits'] for v in vs)), 1), 'linhas_da_sonda_no_treino': sum((v['linhas_da_sonda_no_treino'] for v in vs)), 'sem_x_de_treino_comparavel': any((v['treino_sem_x'] for v in vs))} for n, vs in por.items()}, 'segundos': round(time.time() - t0, 1)}

def main():
    from experimentos import c3_v_da_busca as VB
    saida = sys.argv[1]
    proc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    sementes = list(VB.DESENVOLVIMENTO) + list(VB.PISCINA_PADRAO)
    out = {'o_que_e': __doc__.split('\nUso')[0], 'capacidade': CAPACIDADE, 'por_semente': {}}
    with Pool(proc) as pool:
        for r in pool.imap_unordered(demanda_da_semente, sementes):
            out['por_semente'][str(r['semente'])] = r
            print(r['semente'], r['bits'], r['segundos'], 's', flush=True)
    dev = sum((out['por_semente'][str(s)]['bits'] for s in VB.DESENVOLVIMENTO))
    pisc = sum((out['por_semente'][str(s)]['bits'] for s in VB.PISCINA_PADRAO))
    out['sem_o_giro'] = {'vidas': 'as 3 sementes do desenvolvimento', 'demanda_bits': round(dev, 1), 'razao': round(CAPACIDADE / dev, 5)}
    out['com_o_giro'] = {'vidas': 'os 24 conjuntos da piscina', 'demanda_bits': round(pisc, 1), 'razao': round(CAPACIDADE / pisc, 5)}
    out['por_semente_media'] = round(float(np.mean([r['bits'] for r in out['por_semente'].values()])), 1)
    out['passa'] = bool(out['sem_o_giro']['razao'] < 0.1)
    with open(saida, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ('sem_o_giro', 'com_o_giro', 'por_semente_media', 'passa')}, ensure_ascii=False))
if __name__ == '__main__':
    main()
