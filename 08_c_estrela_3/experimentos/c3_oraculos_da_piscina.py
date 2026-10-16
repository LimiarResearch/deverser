# -*- coding: utf-8 -*-
import os
import sys
import time
from multiprocessing import Pool
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

def _um(semente):
    from experimentos import desafio_v_ser as V
    t0 = time.time()
    faltavam = [os.path.basename(a) for a in V.caminhos_dos_oraculos(semente) if not os.path.exists(a)]
    if faltavam:
        V.oraculos(V.gerar_familias(semente), semente)
    return (semente, faltavam, round(time.time() - t0, 1))

def main():
    from experimentos import c3_v_da_busca as V2
    proc = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    sementes = list(V2.DESENVOLVIMENTO) + list(V2.PISCINA_PADRAO)
    V2.conferir_piscina(V2.PISCINA_PADRAO)
    with Pool(proc) as pool:
        for s, faltavam, dt in pool.imap_unordered(_um, sementes):
            print(f"{time.strftime('%H:%M:%S')} semente {s}: {('calculados ' + ', '.join(faltavam) if faltavam else 'já existiam')} ({dt} s)", flush=True)
    print('fim', flush=True)
if __name__ == '__main__':
    main()
