# -*- coding: utf-8 -*-
import numpy as np
from experimentos import foto_atomica as FA
from experimentos import nivel3b_bits as B
from experimentos import nivel3b_fotos as F

class CodificacaoDeOrdenacao(FA.CodificacaoBase):

    def __init__(self, n=8, m=10, prefixo=()):
        self.n, self.m, self.prefixo = (int(n), int(m), tuple((tuple(x) for x in prefixo)))
        self.w = B.largura(self.n)
        self.nome = f'rede de ordenação (n={self.n}, {self.m} comparadores)'
        self.versao = 1
        self.n_bits = 2 * self.w * self.m
        self.nomes_dos_grupos = ['rede']
        self.campos = [{'nome': f'comparador_{k}', 'grupo': 0, 'tipo': 'comparador', 'bits': 2 * self.w, 'inicio': k * 2 * self.w} for k in range(self.m)]
        self.unidades = tuple(({'inicio': c['inicio'], 'bits': c['bits'], 'grupo': 0} for c in self.campos))

    def decodificar(self, bits):
        rede = B.decodificar(self.n, np.asarray(bits, np.uint8))
        return None if rede is None else tuple(F.canonica(self.n, self.prefixo, rede))

    def codificar(self, corpus):
        return B.codificar(self.n, F.canonica(self.n, self.prefixo, list(corpus)))

    def canonizar(self, bits):
        c = self.decodificar(bits)
        return None if c is None else self.codificar(c)

    def ativos(self, bits):
        return np.ones(self.n_bits, bool)

    def sortear(self, rng):
        rede = []
        while len(rede) < self.m:
            i, j = (int(x) for x in rng.choice(self.n, 2, replace=False))
            rede.append((min(i, j), max(i, j)))
        return self.codificar(rede)

    def valores_dos_campos(self, bits):
        i, j = B.valores(self.n, np.asarray(bits, np.uint8))
        return ((i * self.n + j) / float(self.n * self.n)).astype(np.float32)

    def valor_do_campo(self, bits, i):
        return float(self.valores_dos_campos(bits)[i])

class CodificacaoDoL2(FA.CodificacaoBase):

    def __init__(self):
        from experimentos import desafio_genoma as G
        self.G = G
        self.nome = 'L2 (genoma do programa de aprendizagem contínua)'
        self.versao = G.VERSAO_DA_CODIFICACAO
        self.n_bits = G.N_BITS
        self.campos = G.CAMPOS
        self.nomes_dos_grupos = G.NOMES_DOS_GRUPOS

    def decodificar(self, bits):
        return self.G.decodificar(bits)

    def codificar(self, corpus):
        return self.G.codificar(corpus)

    def canonizar(self, bits):
        return self.G.canonizar(bits)

    def ativos(self, bits):
        return self.G.ativos(bits)

    def sortear(self, rng):
        return self.G.sortear(rng)

    def valor_do_campo(self, bits, i):
        return self.G.valor_do_campo(bits, i)

    def valores_dos_campos(self, bits):
        return np.array([self.G.valor_do_campo(bits, i) for i in range(len(self.G.CAMPOS))], np.float32)

    def grupos_presentes(self, bits):
        return np.asarray(self.G.presencas(bits), np.uint8)

    def escalar_do_cabecalho(self, bits):
        return float(min(self.G._ler_int(np.asarray(bits, np.uint8), self.G.CAMPOS[self.G._NCAM]), 2) + 1) / 3.0

    def resumo(self, bits):
        return np.asarray(self.G.vetor_de_valores(bits), np.float32)

    def n_resumo(self):
        return int(self.G.N_VETOR)

    def mutar(self, bits, rng, forca=1.0):
        return self.G.mutar(bits, rng, forca)

    def cruzar(self, a, b, rng):
        return self.G.cruzar(a, b, rng)
