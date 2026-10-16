# -*- coding: utf-8 -*-
import os

class Problema:

    def __init__(self, nome, codificacao, predicados, nomes_dos_predicados, clausulas, classes, violacoes, violacoes_de_coluna, julgar=None, calibrar=None, hash_de_v=None, selo_do_banco=None, exige_selo=False, hashes_dos_oraculos=None):
        self.selo_do_banco = selo_do_banco
        self.exige_selo = bool(exige_selo)
        self.hashes_dos_oraculos = hashes_dos_oraculos
        self.nome = nome
        self.codificacao = codificacao
        self.predicados = predicados
        self.nomes_dos_predicados = list(nomes_dos_predicados)
        self.n_definidos = len(self.nomes_dos_predicados)
        self.clausulas = list(clausulas)
        self.n_clausulas = len(self.clausulas)
        self.classes = tuple(classes)
        self.violacoes = violacoes
        self.violacoes_de_coluna = violacoes_de_coluna
        self.julgar = julgar
        self.calibrar = calibrar
        self.hash_de_v = hash_de_v

def problema_do_ser():
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    selo = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco_da_prova_cega_selo.json')
    return Problema('o Ser', L.CODIFICACAO, V.Predicados(), V.NOMES_DOS_PREDICADOS, V.CLAUSULAS, V.CLASSES, V.violacoes, V.violacoes_de_coluna, V.julgar, V.calibrar, V.hash_de_V, selo_do_banco=selo, exige_selo=True, hashes_dos_oraculos=V.hashes_dos_oraculos)

def problema_do_ser_v2(piscina=None, eps=None, processos_do_cal=4):
    from experimentos import c3_calibrar_v2 as CAL2
    from experimentos import c3_v_da_busca as VB
    from experimentos import desafio_v_ser as V
    p = problema_do_ser()
    pisc = VB.PISCINA_PADRAO if piscina is None else tuple((int(s) for s in piscina))
    e = VB.EPS if eps is None else float(eps)
    p.nome = 'o Ser, na V da busca v2 (C★3)'
    p.hash_de_v = lambda: VB.hash_de_V2(pisc, e)
    p.calibrar = lambda: CAL2.calibrar_v2(pisc, VB.DESENVOLVIMENTO, e, processos=processos_do_cal, relato=lambda t: print(t, flush=True))
    p.hashes_dos_oraculos = lambda: {n: h for s in (V.SEMENTE_DA_VIDA,) + pisc + VB.DESENVOLVIMENTO for n, h in V.hashes_dos_oraculos(s).items()}
    return p
GRUPO_APRENDE = ('r_aprende', 'r_plastico_no_fim', 'r_deficit_aprende', 'r_deriva')

def problema_do_ser_restrito(nomes=GRUPO_APRENDE, rotulo='aprende'):
    import numpy as np
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    todos = [c[0] for c in V.CLAUSULAS]
    idx = [todos.index(n) for n in nomes]
    claus = [V.CLAUSULAS[i] for i in idx]
    nc = len(idx)
    dmax = 1000 * nc + 1

    def violacoes_de_coluna(j, v):
        return V.violacoes_de_coluna(idx[int(j)], v)

    def violacoes(valores):
        return [float(np.asarray(V.violacoes_de_coluna(idx[j], np.asarray([valores[j]], np.float64)), np.float64)[0]) for j in range(nc)]

    def julgar(res):
        t = V.julgar(res)
        if t['estado'] != 'ok':
            return {'estado': t['estado'], 'valores': [float('nan')] * nc, 'violacoes': [1.0] * nc, 'distancia': dmax, 'nfal': nc, 'classe': V.classe_da_distancia(nc, t['estado']), 'comportamento': t['comportamento'], 'cpu_s': t['cpu_s'], 'bytes': t['bytes']}
        viol = [float(t['violacoes'][i]) for i in idx]
        nfal = sum((1 for v in viol if v > 1e-09))
        return {'estado': 'ok', 'valores': [t['valores'][i] for i in idx], 'violacoes': viol, 'distancia': int(round(1000.0 * sum((min(v, 1.0) for v in viol)))), 'nfal': nfal, 'classe': V.classe_da_distancia(nfal), 'comportamento': t['comportamento'], 'cpu_s': t['cpu_s'], 'bytes': t['bytes']}
    selo = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco_da_prova_cega_selo.json')
    return Problema(f'''o Ser, a célula "{rotulo}" (o D restrito a {', '.join(nomes)}; a mesma V)''', L.CODIFICACAO, V.Predicados(), V.NOMES_DOS_PREDICADOS, claus, V.CLASSES, violacoes, violacoes_de_coluna, julgar, V.calibrar, V.hash_de_V, selo_do_banco=selo, exige_selo=True, hashes_dos_oraculos=V.hashes_dos_oraculos)

def problema_do_l2():
    from experimentos import codificacoes_existentes as CE
    from experimentos import desafio_v as V
    return Problema('o desafio do Ser no L2', CE.CodificacaoDoL2(), V.Predicados(), V.NOMES_DOS_PREDICADOS, V.CLAUSULAS, V.CLASSES, V.violacoes, V.violacoes_de_coluna, V.julgar, V.calibrar, V.hash_de_V)
