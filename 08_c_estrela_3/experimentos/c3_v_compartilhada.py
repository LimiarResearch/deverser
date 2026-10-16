# -*- coding: utf-8 -*-
import multiprocessing as mp
import numpy as np
from experimentos import c3_v_da_busca as VB
_TODAS = {}

def _medir_qualquer(pacote):
    from experimentos import l_ser_interp as LI
    from experimentos import l_ser_lang as LL
    semente, eps, semente_pert, bits_emp = pacote
    LI.definir_perturbacao(eps, semente_pert)
    try:
        return _TODAS[semente].medir(LL.CODIFICACAO.desempacotar(bits_emp))
    finally:
        LI.definir_perturbacao(0.0, 0)

class AvaliacoesV2Compartilhada(VB.AvaliacoesV2):

    def __init__(self, trabalhadores=6, piscina=VB.PISCINA_PADRAO, eps=VB.EPS, backend='cpp', tempo_max=None, desenvolvimento=VB.DESENVOLVIMENTO, conferir=True):
        from experimentos import desafio_v as DV
        from experimentos import desafio_v_ser as V
        if conferir:
            VB.conferir_piscina(piscina)
        self.piscina, self.eps, self.backend = (tuple((int(s) for s in piscina)), float(eps), backend)
        self.desenvolvimento = tuple((int(s) for s in desenvolvimento))
        self.tempo_max = V.TEMPO_MAX_PADRAO if tempo_max is None else float(tempo_max)
        todas = list(dict.fromkeys(list(self.piscina) + list(self.desenvolvimento)))
        DV.definir_backend(backend)
        if backend == 'cpp':
            from experimentos import l_ser_cpp
            l_ser_cpp.compilar()
        for s in todas:
            _TODAS[s] = V.AvaliadorReal(s, self.tempo_max, backend=backend)
        self.dono = {s: 0 for s in todas}
        self.por_trabalhador = [0]
        self._pool = mp.get_context('fork').Pool(int(trabalhadores), maxtasksperchild=40)
        self._pools = [self._pool]
        self.medidos = 0

    def _enviar(self, semente, semente_pert, bits):
        from experimentos import l_ser_lang as LL
        self.medidos += 1
        self.por_trabalhador[0] += 1
        return self._pool.apply_async(_medir_qualquer, ((semente, self.eps, semente_pert, LL.CODIFICACAO.empacotar(np.asarray(bits, np.uint8))),))

def avaliador(trabalhadores=6, replicas=2, backend='cpp'):
    if 'fork' in mp.get_all_start_methods():
        return AvaliacoesV2Compartilhada(trabalhadores=trabalhadores, backend=backend)
    from experimentos import c3_v_repartida as VR
    return VR.AvaliacoesV2Repartida(trabalhadores=trabalhadores, replicas=replicas, backend=backend)
