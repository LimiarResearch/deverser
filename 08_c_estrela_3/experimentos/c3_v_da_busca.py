# -*- coding: utf-8 -*-
import hashlib
import os
import numpy as np
EPS = 2.0 ** (-17)
PISCINA_PADRAO = tuple((30000000 + 1009 * i for i in range(24)))
DESENVOLVIMENTO = (7391026, 58210473, 913004317)
PROIBIDAS = {1, 2, 424242, 424243, 20261003, 20261004, 50505050, 50505051}
M64 = (1 << 64) - 1

def _h(*xs):
    z = 2611923443488327891
    for x in xs:
        z = (z ^ int(x) & M64) & M64
        z = z + 11400714819323198485 & M64
        z = (z ^ z >> 30) * 13787848793156543929 & M64
        z = (z ^ z >> 27) * 10723151780598845931 & M64
        z = z ^ z >> 31
    return z

def conferir_piscina(piscina):
    vidas = {s + d for s in piscina for d in (0, 1)} | {s + d for s in DESENVOLVIMENTO for d in (0, 1)}
    assert len(vidas) == 2 * (len(piscina) + len(DESENVOLVIMENTO)), 'as vidas da piscina e do desenvolvimento se encostam'
    assert not vidas & PROIBIDAS, 'a piscina encosta na busca, no banco, no T1 ou na sonda'

def escolhas(assinatura, sal, nivel, piscina):
    P = len(piscina)
    out, usados = ([], set())
    j = 0
    while len(out) < min(nivel, P):
        i = _h(assinatura, sal, j, 1) % P
        j += 1
        if i in usados:
            continue
        usados.add(i)
        out.append((i, _h(assinatura, sal, j, 2)))
    return out
_TRAB = {}

def _iniciar(sementes, tempo_max, backend):
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    if os.name == 'nt':
        import shutil
        if shutil.which('g++'):
            os.add_dll_directory(os.path.dirname(shutil.which('g++')))
    from experimentos import desafio_v as DV
    DV.definir_backend(backend)
    from experimentos import desafio_v_ser as V
    for s in sementes:
        _TRAB[s] = V.AvaliadorReal(s, tempo_max, backend=backend)

def _medir(pacote):
    from experimentos import l_ser_interp as LI
    from experimentos import l_ser_lang as LL
    semente, eps, semente_pert, bits_emp = pacote
    LI.definir_perturbacao(eps, semente_pert)
    try:
        return _TRAB[semente].medir(LL.CODIFICACAO.desempacotar(bits_emp))
    finally:
        LI.definir_perturbacao(0.0, 0)

class AvaliacoesV2:

    def __init__(self, trabalhadores=4, piscina=PISCINA_PADRAO, eps=EPS, backend='cpp', tempo_max=None, desenvolvimento=DESENVOLVIMENTO, conferir=True):
        from experimentos import desafio_v_ser as V
        if conferir:
            conferir_piscina(piscina)
        self.piscina, self.eps, self.backend = (tuple((int(s) for s in piscina)), float(eps), backend)
        self.desenvolvimento = tuple((int(s) for s in desenvolvimento))
        self.tempo_max = V.TEMPO_MAX_PADRAO if tempo_max is None else float(tempo_max)
        todas = list(dict.fromkeys(list(self.piscina) + list(self.desenvolvimento)))
        self.dono = {s: i % trabalhadores for i, s in enumerate(todas)}
        for s in todas:
            V.oraculos(V.gerar_familias(s), s)
        import multiprocessing as mp
        ctx = mp.get_context('spawn')
        self._pools = [ctx.Pool(1, initializer=_iniciar, initargs=([s for s in todas if self.dono[s] == w], self.tempo_max, backend)) for w in range(trabalhadores)]
        self.medidos = 0

    def _enviar(self, semente, semente_pert, bits):
        from experimentos import l_ser_lang as LL
        self.medidos += 1
        return self._pools[self.dono[semente]].apply_async(_medir, ((semente, self.eps, semente_pert, LL.CODIFICACAO.empacotar(np.asarray(bits, np.uint8))),))

    def medir(self, lista_de_bits, sal=0, nivel=1):
        from experimentos import c3_sonda_do_ser as S
        from experimentos import desafio_v_ser as V
        pendentes = []
        for bits in lista_de_bits:
            sig = S.assinatura(bits)
            pendentes.append([(self.piscina[i], sp, self._enviar(self.piscina[i], sp, bits)) for i, sp in escolhas(sig, sal, nivel, self.piscina)])
        out = []
        for medidas in pendentes:
            res = [(s, sp, a.get()) for s, sp, a in medidas]
            dist = [V.julgar(r)['distancia'] for _s, _sp, r in res]
            pior = int(np.argmax(dist))
            r = dict(res[pior][2])
            r['medidas_do_nivel'] = [{'semente': s, 'semente_pert': sp, 'distancia': int(d)} for (s, sp, _r), d in zip(res, dist)]
            out.append(r)
        return out

    def medir_no_desenvolvimento(self, lista_de_bits, sementes_pert=(1, 2, 3, 4, 5)):
        pend = [{s: {p: self._enviar(s, p, bits) for p in sementes_pert} for s in self.desenvolvimento} for bits in lista_de_bits]
        return [{s: {p: a.get() for p, a in por.items()} for s, por in d.items()} for d in pend]

    def fechar(self):
        for p in self._pools:
            p.close()
            p.join()
        self._pools = []

def hash_de_V2(piscina=PISCINA_PADRAO, eps=EPS):
    from experimentos import c3_sonda_do_ser as S
    from experimentos import desafio_v as DV
    from experimentos import desafio_v_ser as V
    h = hashlib.sha256()
    h.update(V.hash_de_V().encode())
    aqui = os.path.dirname(os.path.abspath(__file__))
    for n in ('c3_v_da_busca.py', 'c3_sonda_do_ser.py', 'l_ser_interp.py', 'l_ser_nucleo.cpp', 'l_ser_cpp.py'):
        h.update(open(os.path.join(aqui, n), 'rb').read())
    h.update(repr((eps, tuple(piscina), DESENVOLVIMENTO, S.SONDA, S.TREINOS_DA_SONDA)).encode())
    for s in tuple(piscina) + DESENVOLVIMENTO:
        for arq in V.caminhos_dos_oraculos(s):
            if os.path.exists(arq):
                h.update(open(arq, 'rb').read())
            else:
                h.update(b'falta:' + os.path.basename(arq).encode())
    return h.hexdigest()
