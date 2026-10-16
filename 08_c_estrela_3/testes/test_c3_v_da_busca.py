# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
if os.name == 'nt':
    import shutil
    if shutil.which('g++'):
        os.add_dll_directory(os.path.dirname(shutil.which('g++')))
from experimentos import c3_v_da_busca as V2

def test_as_escolhas_sao_deterministas_distintas_e_mudam_com_o_sal():
    p = V2.PISCINA_PADRAO
    a = V2.escolhas(123456789, 0, 3, p)
    assert a == V2.escolhas(123456789, 0, 3, p)
    assert len({i for i, _ in a}) == 3
    outras = [V2.escolhas(123456789, s, 3, p) for s in range(1, 20)]
    assert sum((o != a for o in outras)) >= 18
    assert len(V2.escolhas(1, 0, 50, p)) == len(p)

def test_a_piscina_padrao_nao_encosta_em_nada():
    V2.conferir_piscina(V2.PISCINA_PADRAO)
    try:
        V2.conferir_piscina((1, 30000000))
        raise AssertionError('aceitou a semente da busca')
    except AssertionError as e:
        assert 'encosta' in str(e)

def test_a_v2_e_determinista_e_o_dado_neutro_nao_rola():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_c3_sonda import _sgd
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    av = V2.AvaliacoesV2(trabalhadores=1, piscina=(1,), desenvolvimento=(1,), conferir=False)
    try:
        formas = [L.codificar_programa(_sgd(forma=k)) for k in range(3)]
        r = av.medir(formas + [formas[0]], sal=0, nivel=1)
        d = [V.julgar(x)['distancia'] for x in r]
        print(f'  a SGD em 3 formas neutras e a primeira de novo: {d}')
        assert len(set(d)) == 1 and r[0]['estado'] == 'ok'
        dev = av.medir_no_desenvolvimento([formas[0]], sementes_pert=(1, 2))
        print(f"  no desenvolvimento (semente 1, perturbações 1 e 2): {[V.julgar(x)['distancia'] for x in dev[0][1].values()]}")
        assert set(dev[0]) == {1} and set(dev[0][1]) == {1, 2}
    finally:
        av.fechar()
if __name__ == '__main__':
    for nome, f in list(globals().items()):
        if nome.startswith('test_'):
            f()
            print('ok', nome, flush=True)
