# -*- coding: utf-8 -*-
import multiprocessing as mp
import os
import sys
import time
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
from experimentos import c3_v_compartilhada as CC
from experimentos import c3_v_da_busca as VB
from experimentos import l_ser_testemunhas as LT

def test_o_mesmo_resultado_e_todos_trabalhando():
    if 'fork' not in mp.get_all_start_methods():
        print('  sem fork aqui: o teste é da VPS')
        return
    P = VB.PISCINA_PADRAO[:3]
    fotos = list(LT.testemunhas_em_bits().values())
    a = VB.AvaliacoesV2(trabalhadores=3, piscina=P, desenvolvimento=(), conferir=False)
    try:
        ra = a.medir(fotos, sal=0, nivel=3)
    finally:
        a.fechar()
    b = CC.AvaliacoesV2Compartilhada(trabalhadores=6, piscina=P, desenvolvimento=(), conferir=False)
    try:
        t0 = time.time()
        rb = b.medir(fotos, sal=0, nivel=3)
        tb = time.time() - t0
        mesma = [fotos[0]] * 6
        t0 = time.time()
        b.medir(mesma, sal=0, nivel=1)
        t6 = time.time() - t0
    finally:
        b.fechar()
    for x, y in zip(ra, rb):
        assert x['medidas_do_nivel'] == y['medidas_do_nivel'], (x['medidas_do_nivel'], y['medidas_do_nivel'])
    print(f'  {len(rb)} fotos na pior de 3 iguais nos dois caminhos ({tb:.0f} s); 6 fotos da mesma assinatura em {t6:.0f} s (em paralelo, se for perto do tempo de uma)')
if __name__ == '__main__':
    test_o_mesmo_resultado_e_todos_trabalhando()
    print('ok')
