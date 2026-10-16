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
from experimentos import l_ser_cpp as LC
from experimentos import l_ser_interp as LI
from experimentos import l_ser_testemunhas as LT
D, C = (24, 4)

def _lado_a_lado(prog, passos=300, semente_fluxo=7):
    Wt = np.random.default_rng(5).normal(0, 1, (D, C))
    a = LI.AprendizSer(D, C, np.random.default_rng(100), prog)
    b = LC.AprendizSerCpp(D, C, np.random.default_rng(100), prog)
    r = np.random.default_rng(semente_fluxo)
    for _ in range(passos):
        x = r.normal(0, 1, D).astype(np.float32)
        y = int(np.argmax(np.tanh(x @ Wt)))
        a.aprender(x, y)
        b.aprender(x, y)
    return (max((float(np.max(np.abs(np.asarray(wa, np.float64) - np.asarray(wb, np.float64)))) for wa, wb in zip(a.W, b.W))), a)

def test_o_fator_e_o_mesmo_nos_dois_motores():
    for nome in ('sgd', 'ewc', 'cbp'):
        prog = LT.testemunhas()[nome]
        try:
            LI.definir_perturbacao(2.0 ** (-10), 12345)
            dw, a = _lado_a_lado(prog)
            LI.definir_perturbacao(0.0, 0)
            d0, a0 = _lado_a_lado(prog)
        finally:
            LI.definir_perturbacao(0.0, 0)
        mudou = max((float(np.max(np.abs(w1 - w0))) for w1, w0 in zip(a.W, a0.W)))
        print(f'  {nome}: com a perturbação, numpy x C++ {dw:.1e} (sem ela {d0:.1e}); a perturbação mudou os pesos em {mudou:.1e}')
        assert dw < 1e-05 and mudou > 0.0001, (nome, dw, mudou)

def test_os_fatores_sao_os_do_contador_e_eps_tem_de_ser_potencia_de_2():
    f = LI.fatores_de_perturbacao(42, 3, 1, 1000, 2.0 ** (-14))
    assert f.dtype == np.float32 and float(np.max(np.abs(f.astype(np.float64) - 1.0))) <= 2.0 ** (-14)
    assert np.array_equal(f, LI.fatores_de_perturbacao(42, 3, 1, 1000, 2.0 ** (-14)))
    assert not np.array_equal(f, LI.fatores_de_perturbacao(43, 3, 1, 1000, 2.0 ** (-14)))
    try:
        LI.definir_perturbacao(0.0001, 1)
        raise AssertionError('aceitou eps que não é potência de 2')
    except AssertionError as e:
        assert 'potência de 2' in str(e)
    finally:
        LI.definir_perturbacao(0.0, 0)
if __name__ == '__main__':
    for nome, f in list(globals().items()):
        if nome.startswith('test_'):
            f()
            print('ok', nome, flush=True)
