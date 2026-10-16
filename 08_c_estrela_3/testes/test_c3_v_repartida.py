# -*- coding: utf-8 -*-
import os
import shutil
import sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
if os.name == 'nt' and shutil.which('g++'):
    os.add_dll_directory(os.path.dirname(shutil.which('g++')))
from experimentos import c3_v_da_busca as VB
from experimentos import c3_v_repartida as VR
from experimentos import l_ser_testemunhas as LT

def test_o_roteamento_nao_muda_nenhuma_medida():
    P = VB.PISCINA_PADRAO[:3]
    fotos = list(LT.testemunhas_em_bits().values())
    a = VB.AvaliacoesV2(trabalhadores=2, piscina=P, desenvolvimento=(), conferir=False)
    try:
        ra = a.medir(fotos, sal=0, nivel=2)
    finally:
        a.fechar()
    b = VR.AvaliacoesV2Repartida(trabalhadores=3, replicas=2, piscina=P, desenvolvimento=(), conferir=False)
    try:
        rb = b.medir(fotos + fotos, sal=0, nivel=2)
        espalhou = list(b.por_trabalhador)
    finally:
        b.fechar()
    for x, y in zip(ra + ra, rb):
        assert x['medidas_do_nivel'] == y['medidas_do_nivel'], (x['medidas_do_nivel'], y['medidas_do_nivel'])
    print(f'  {len(rb)} medidas iguais nos dois caminhos; medidas por trabalhador na repartida: {espalhou}')
    assert sum((1 for n in espalhou if n > 0)) >= 2
if __name__ == '__main__':
    test_o_roteamento_nao_muda_nenhuma_medida()
    print('ok')
