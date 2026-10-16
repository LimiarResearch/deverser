# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
PERT = (6, 7, 8, 9, 10)
FOTOS = ('9326', '7582', '12039', '13109')

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fotos', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--autorizacao', required=True)
    ap.add_argument('--processos', type=int, default=4)
    a = ap.parse_args(argv)
    if not a.autorizacao.strip():
        sys.exit('RECUSADO: sem a frase de autorização')
    if os.name == 'nt':
        import shutil
        if shutil.which('g++'):
            os.add_dll_directory(os.path.dirname(shutil.which('g++')))
    from multiprocessing import get_context
    from experimentos import c3_falsas as F
    from experimentos import c3_t3 as T3
    from experimentos import c3_v_da_busca as VB
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    from experimentos import l_ser_testemunhas as LT
    fotos = F._fotos(a.fotos)
    test = LT.testemunhas_em_bits()
    nomes = [f'foto {n}' for n in FOTOS] + [f'testemunha {n}' for n in ('sgd', 'ewc', 'cbp', 'sp')]
    bits = [fotos[n.split()[1]]['bits'] for n in nomes[:4]] + [test[n.split()[1]] for n in nomes[4:]]
    t0 = time.time()
    out = {'o_que_e': __doc__.split('\nUso')[0], 'autorizacao': a.autorizacao, 'eps': VB.EPS, 'pert': list(PERT), 'semente_das_vidas': V.SEMENTE_DA_VIDA, 'hash_de_V2': VB.hash_de_V2(()), 'por_programa': {}}
    T3._gravar(a.saida, out)
    tarefas = [(i, 0.0, 0) for i in range(len(bits))] + [(i, VB.EPS, p) for i in range(len(bits)) for p in PERT]
    pacotes = [(V.SEMENTE_DA_VIDA, eps, p, L.CODIFICACAO.empacotar(np.asarray(bits[i], np.uint8))) for i, eps, p in tarefas]
    with get_context('spawn').Pool(a.processos, initializer=VB._iniciar, initargs=([V.SEMENTE_DA_VIDA], V.TEMPO_MAX_PADRAO, 'cpp')) as pool:
        res = pool.map(VB._medir, pacotes, chunksize=1)
    dist = {}
    for (i, eps, p), r in zip(tarefas, res):
        j = V.julgar(r)
        dist.setdefault(i, {})['sem' if eps == 0 else p] = int(j['distancia']) if j['estado'] == 'ok' else None
    for i, n in enumerate(nomes):
        d = dist[i]
        ds = [d[p] for p in PERT]
        if d['sem'] is None or None in ds:
            out['por_programa'][n] = {'sem_perturbacao': d['sem'], 'perturbadas': ds, 'erro': 'medida sem estado ok'}
            continue
        m, ep = F._media_ep(ds)
        out['por_programa'][n] = {'sem_perturbacao': d['sem'], 'perturbadas': ds, 'media': round(m, 1), 'erro_padrao': round(ep, 1), 'mudanca': round(m - d['sem'], 1)}
    pp = out['por_programa']
    ok = all(('mudanca' in pp[n] for n in nomes))
    if ok:
        mf = float(np.mean([pp[n]['mudanca'] for n in nomes[:4]]))
        mt = float(np.mean([pp[n]['mudanca'] for n in nomes[4:]]))
        ep = float(np.hypot(np.sqrt(sum((pp[n]['erro_padrao'] ** 2 for n in nomes[:4]))) / 4, np.sqrt(sum((pp[n]['erro_padrao'] ** 2 for n in nomes[4:]))) / 4))
        out.update({'mudanca_media_das_fotos': round(mf, 1), 'mudanca_media_das_testemunhas': round(mt, 1), 'diferenca': round(mf - mt, 1), 'erro_padrao_da_diferenca': round(ep, 1), 'passa': bool(mf - mt > ep)})
    else:
        out['passa'] = False
    out['hash_igual'] = VB.hash_de_V2(()) == out['hash_de_V2']
    out['segundos'] = round(time.time() - t0, 1)
    T3._gravar(a.saida, out)
    print(json.dumps({k: out.get(k) for k in ('mudanca_media_das_fotos', 'mudanca_media_das_testemunhas', 'diferenca', 'erro_padrao_da_diferenca', 'passa', 'hash_igual', 'segundos')}, ensure_ascii=False), flush=True)
if __name__ == '__main__':
    main()
