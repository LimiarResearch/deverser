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
from experimentos import c3_sonda_do_ser as S
from experimentos import l_ser_lang as L
from experimentos import l_ser_testemunhas as LT
E = L.E

def _sgd(lr=0.05, forma=0):
    pol = LT._politica_por_confianca()
    regra = [E('mulk', 'P', c=lr), E('mul', 'P', E('k', c=lr)), E('add', E('mulk', 'P', c=lr), 'zero'), E('mulk', E('add', 'P', 'zero'), c=lr)][forma]
    return L.programa(tecido=LT._tecido(64, 4), W_SAIDA=regra, W_OCULTA=E('mulk', 'P', c=lr), RETRO=E('mul', 'T', E('thr', 's')), rotulos=pol.pop('rotulos'), **pol)

def test_variantes_neutras_dao_a_mesma_assinatura():
    bits = [L.codificar_programa(_sgd(forma=k)) for k in range(4)]
    print(f'  {len({b.tobytes() for b in bits})} formas com bits diferentes depois da forma canônica')
    assert len({b.tobytes() for b in bits}) >= 2, 'as variantes têm de ter bits diferentes'
    sig = {S.assinatura(b) for b in bits}
    print(f'  as variantes neutras da SGD: {len(sig)} assinatura(s)')
    assert len(sig) == 1

def test_comportamentos_diferentes_dao_assinaturas_diferentes():
    sig = {n: S.assinatura(b) for n, b in LT.testemunhas_em_bits().items()}
    sig['sgd lr 0,02'] = S.assinatura(L.codificar_programa(_sgd(lr=0.02)))
    print(f'  {len(sig)} comportamentos: {len(set(sig.values()))} assinaturas')
    assert len(set(sig.values())) == len(sig)
if __name__ == '__main__':
    for nome, f in list(globals().items()):
        if nome.startswith('test_'):
            f()
            print('ok', nome, flush=True)
