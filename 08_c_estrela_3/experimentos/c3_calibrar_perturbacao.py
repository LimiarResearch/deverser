# -*- coding: utf-8 -*-
import json
import os
import sys
import time
from multiprocessing import Pool
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
if os.name == 'nt':
    import shutil
    if shutil.which('g++'):
        os.add_dll_directory(os.path.dirname(shutil.which('g++')))
import numpy as np
EPS = (0.0, 2.0 ** (-17), 2.0 ** (-14), 2.0 ** (-11))
SEMENTES = (101, 202, 303)
FOTOS = ('foto 9326', 'foto 7582', 'foto 12039', 'foto 13109')
_AV = None

def _iniciar():
    global _AV
    from experimentos import desafio_v as DV
    DV.definir_backend('cpp')
    from experimentos import desafio_v_ser as V
    _AV = V.AvaliadorReal(backend='cpp')

def _medir(t):
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_interp as LI
    nome, eps, semente, bits = t
    LI.definir_perturbacao(eps, semente)
    t0 = time.time()
    try:
        v = V.julgar(_AV.medir(np.asarray(bits, np.uint8)))
    finally:
        LI.definir_perturbacao(0.0, 0)
    return (nome, eps, semente, {'estado': v['estado'], 'distancia': int(v['distancia']), 'valores': [float(x) for x in v['valores']], 'segundos': round(time.time() - t0, 1)})

def main():
    from experimentos import l_ser_testemunhas as LT
    fotos = json.load(open(sys.argv[1], encoding='utf-8'))
    saida = sys.argv[2]
    proc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    alvos = {f'testemunha {n}': np.asarray(b, np.uint8) for n, b in LT.testemunhas_em_bits().items()}
    for chave, bits in fotos.items():
        if any((chave.startswith(f + ' ') for f in FOTOS)):
            alvos[chave.split(' (')[0]] = np.array([int(c) for c in bits], np.uint8)
    tarefas = [(n, e, s, b) for n, b in alvos.items() for e in EPS for s in (SEMENTES if e else (0,))]
    out = {'o_que_e': __doc__.split('\n\nUso')[0], 'eps': EPS, 'sementes': SEMENTES, 'medidas': []}
    with Pool(proc, initializer=_iniciar) as pool:
        for r in pool.imap_unordered(_medir, tarefas):
            out['medidas'].append(r)
            json.dump(out, open(saida, 'w', encoding='utf-8'), ensure_ascii=False)
    resumo = {}
    for nome, eps, semente, r in out['medidas']:
        resumo.setdefault(nome, {}).setdefault(str(eps), []).append(r['distancia'])
    out['resumo'] = {n: {e: {'media': round(float(np.mean(v)), 1), 'faixa': int(max(v) - min(v)), 'valores': sorted(v)} for e, v in por.items()} for n, por in resumo.items()}
    json.dump(out, open(saida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for n, por in out['resumo'].items():
        print(n, {e: (d['media'], d['faixa']) for e, d in sorted(por.items(), key=lambda x: float(x[0]))}, flush=True)
if __name__ == '__main__':
    main()
