# -*- coding: utf-8 -*-
import threading
import numpy as np
from experimentos import c3_v_da_busca as VB

class AvaliacoesV2Repartida(VB.AvaliacoesV2):

    def __init__(self, trabalhadores=6, replicas=2, piscina=VB.PISCINA_PADRAO, eps=VB.EPS, backend='cpp', tempo_max=None, desenvolvimento=VB.DESENVOLVIMENTO, conferir=True):
        from experimentos import desafio_v_ser as V
        if conferir:
            VB.conferir_piscina(piscina)
        self.piscina, self.eps, self.backend = (tuple((int(s) for s in piscina)), float(eps), backend)
        self.desenvolvimento = tuple((int(s) for s in desenvolvimento))
        self.tempo_max = V.TEMPO_MAX_PADRAO if tempo_max is None else float(tempo_max)
        todas = list(dict.fromkeys(list(self.piscina) + list(self.desenvolvimento)))
        r = max(1, min(int(replicas), int(trabalhadores)))
        passo = max(1, trabalhadores // r)
        self.donos = {s: sorted({(i + j * passo) % trabalhadores for j in range(r)}) for i, s in enumerate(todas)}
        self.dono = {s: d[0] for s, d in self.donos.items()}
        for s in todas:
            V.oraculos(V.gerar_familias(s), s)
        import multiprocessing as mp
        ctx = mp.get_context('spawn')
        self._pools = [ctx.Pool(1, initializer=VB._iniciar, initargs=([s for s in todas if w in self.donos[s]], self.tempo_max, backend)) for w in range(trabalhadores)]
        self._pendentes = [0] * trabalhadores
        self._trava = threading.Lock()
        self.medidos = 0
        self.por_trabalhador = [0] * trabalhadores

    def _feito(self, w):

        def f(_res):
            with self._trava:
                self._pendentes[w] -= 1
        return f

    def _enviar(self, semente, semente_pert, bits):
        from experimentos import l_ser_lang as LL
        self.medidos += 1
        with self._trava:
            w = min(self.donos[semente], key=lambda k: (self._pendentes[k], k))
            self._pendentes[w] += 1
        self.por_trabalhador[w] += 1
        cb = self._feito(w)
        return self._pools[w].apply_async(VB._medir, ((semente, self.eps, semente_pert, LL.CODIFICACAO.empacotar(np.asarray(bits, np.uint8))),), callback=cb, error_callback=cb)
