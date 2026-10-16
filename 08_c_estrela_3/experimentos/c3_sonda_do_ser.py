# -*- coding: utf-8 -*-
import hashlib
import os
import numpy as np
SONDA = 50505050
TREINOS_DA_SONDA = 1500
_VIDA = None

def _vida():
    global _VIDA
    if _VIDA is None:
        from experimentos import desafio_v as DV
        _VIDA = DV.gerar_vidas(SONDA)
    return _VIDA

def rotulos_da_sonda(bits, treinos=TREINOS_DA_SONDA):
    from experimentos import l_ser_cpp as LC
    from experimentos import l_ser_interp as LI
    antes = dict(LI.PERTURBACAO)
    LI.definir_perturbacao(0.0, 0)
    try:
        entrada = _vida()
        fab, rest = LC.fabricar(np.asarray(bits, np.uint8))
        d, c = (entrada['d_entrada'], entrada['classes'])
        a = fab(d, c, np.random.default_rng(100))
        ler = entrada['fluxos'][0]['abrir']()
        out, n = ([], 0)
        while n < treinos:
            ev = ler()
            if ev is None:
                break
            if ev[0] == 'treino':
                a.aprender(np.asarray(ev[1], np.float32), ev[2])
                n += 1
            elif ev[0] == 'sonda':
                classes, _etq = a.prever(np.asarray(ev[1], np.float32).copy())
                out.append(np.asarray(classes, np.int64))
            else:
                a = rest(a.estado(), d, c)
        return out
    finally:
        LI.definir_perturbacao(antes['eps'], antes['semente'])

def assinatura(bits, treinos=TREINOS_DA_SONDA):
    h = hashlib.sha256()
    for r in rotulos_da_sonda(bits, treinos):
        h.update(r.tobytes())
    return int.from_bytes(h.digest()[:8], 'little')
