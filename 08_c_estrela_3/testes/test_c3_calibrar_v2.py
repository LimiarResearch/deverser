# -*- coding: utf-8 -*-
import os
import shutil
import sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
from experimentos import c3_calibrar_v2 as CAL2
from experimentos import c3_v_da_busca as VB

def test_o_cal_v2_numa_semente_do_desenvolvimento():
    if os.name == 'nt' and (not shutil.which('g++')):
        raise AssertionError('o g++ não está no PATH: sem ele o interpretador em C++ não carrega e o SGD sai com erro')
    r = CAL2._controles_de_uma_semente((58210473, VB.EPS, 'cpp'))
    print('  ok', r['ok'], 'SGD perturbado', r['degenerados']['sgd_perturbado'], 'déficit', r['deficit'], f"({r['segundos']} s)")
    assert r['controles']['ideal']['cumpre_as_28']
    assert all((v['positivo_cumpre'] and v['negativo_reprova'] for v in r['clausulas'].values()))
    assert r['degenerados']['sgd_perturbado']['estado'] == 'ok' and (not r['degenerados']['sgd_perturbado']['cumpre_D'])
    assert r['ok']
if __name__ == '__main__':
    test_o_cal_v2_numa_semente_do_desenvolvimento()
    print('ok')
