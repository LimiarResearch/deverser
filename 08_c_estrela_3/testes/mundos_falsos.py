# -*- coding: utf-8 -*-
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from experimentos import codificacoes_existentes as CE
from experimentos import escritor_de_fotos as EF
from experimentos import l_ser_lang as L
from experimentos import problema_de_d as PD
CLASSES = ('cumpre D', 'a 1 cláusula de D', '2 a 3 cláusulas', '4 a 6 cláusulas', '7 ou mais cláusulas', 'sem classe (estouro, erro ou oráculo)')

def classe_da_distancia(nfal, estado='ok'):
    if estado != 'ok':
        return len(CLASSES) - 1
    return 0 if nfal == 0 else 1 if nfal == 1 else 2 if nfal <= 3 else 3 if nfal <= 6 else 4

class PredicadosFalsos:
    versao = 1

    def __init__(self, nomes, n_duras):
        self.nomes, self.duras = (list(nomes), list(range(n_duras)))

    def __len__(self):
        return len(self.nomes)

    def mascara_das_duras(self):
        return (1 << len(self.duras)) - 1

    def duras_que_falham(self, comp):
        return [i for i in self.duras if int(comp) >> i & 1]

    def descricao(self):
        return {'versao': self.versao, 'predicados': len(self.nomes), 'duras': len(self.duras)}

class _Mundo:
    nome = 'mundo de mentira'

    def __init__(self, cod, n_clausulas, nomes_dos_predicados):
        self.cod = cod
        self.n_clausulas = n_clausulas
        self.clausulas = [(f'c{i}', 'violacao', '<=', 0.0, 1.0) for i in range(n_clausulas)]
        self.nomes = list(nomes_dos_predicados)
        self.predicados = PredicadosFalsos(self.nomes, n_clausulas)
        self.avaliados = 0

    def violacoes(self, valores):
        return [max(0.0, float(v)) for v in valores]

    def violacoes_de_coluna(self, i, v):
        return np.maximum(0.0, np.asarray(v, np.float64))

    def julgar(self, res):
        if res['estado'] != 'ok':
            return {'estado': res['estado'], 'valores': [float('nan')] * self.n_clausulas, 'violacoes': [1.0] * self.n_clausulas, 'distancia': 1000 * self.n_clausulas + 1, 'nfal': self.n_clausulas, 'classe': classe_da_distancia(self.n_clausulas, res['estado']), 'comportamento': 0, 'cpu_s': float(res.get('cpu_s', 0.0)), 'bytes': 0}
        viol = self.violacoes(res['valores'])
        nfal = sum((1 for v in viol if v > 1e-09))
        return {'estado': 'ok', 'valores': [float(v) for v in res['valores']], 'violacoes': viol, 'distancia': int(round(1000.0 * sum((min(v, 1.0) for v in viol)))), 'nfal': nfal, 'classe': classe_da_distancia(nfal), 'comportamento': int(res['comportamento']), 'cpu_s': float(res.get('cpu_s', 0.001)), 'bytes': int(res.get('bytes_de_estado', 1000))}

    def problema(self):
        return PD.Problema(self.nome, self.cod, self.predicados, self.nomes, self.clausulas, CLASSES, self.violacoes, self.violacoes_de_coluna, self.julgar)

    def medir(self, bits):
        self.avaliados += 1
        return self._medir(np.asarray(bits, np.uint8))

    def veredito(self, bits):
        return self.julgar(self.medir(bits))

class MundoDoSerOculto(_Mundo):

    def __init__(self, semente=0, n_clausulas=18):
        cod = L.CODIFICACAO
        self.mapa = EF.Mapa(cod)
        g = np.random.default_rng(1000 + semente)
        nomes = [f'falha:c{i}' for i in range(n_clausulas)] + [f'longe:c{i}' for i in range(n_clausulas)] + [f'secao_{s}_longe' for s in range(cod.n_grupos - 1)]
        super().__init__(cod, n_clausulas, nomes)
        self.nome = 'o Ser escondido (de mentira)'
        n_papeis = len(self.mapa.nomes_dos_papeis)
        valor_do_papel = [int(g.integers(0, 1 << 20)) for _ in range(n_papeis)]
        b = np.zeros(cod.n_bits, np.uint8)
        for i, c in enumerate(cod.campos):
            nb = c['bits']
            v = valor_do_papel[int(self.mapa.papel[i])] % (1 << nb)
            if c['tipo'] == 'presenca':
                v = 1 if valor_do_papel[int(self.mapa.papel[i])] % 4 else 0
            for t in range(nb):
                b[c['inicio'] + t] = v >> nb - 1 - t & 1
        self.alvo = cod.canonizar(b)
        at = np.asarray(cod.ativos(self.alvo), bool)
        self.pos_alvo = np.flatnonzero(at)
        campos = np.unique(self.mapa.campo_de[self.pos_alvo])
        self.clausula_do_campo = {int(i): int(self.mapa.papel[i]) % n_clausulas for i in campos}
        self.campos_por_clausula = [[i for i, c in self.clausula_do_campo.items() if c == k] for k in range(n_clausulas)]
        self.secao_do_campo = {int(i): int(self.mapa.grupo_de[self.mapa.inicio[i]]) for i in campos}

    def _acerto_por_campo(self, bits):
        return {i: bool(np.array_equal(bits[self.mapa.inicio[i]:self.mapa.inicio[i] + self.mapa.bits_do_campo[i]], self.alvo[self.mapa.inicio[i]:self.mapa.inicio[i] + self.mapa.bits_do_campo[i]])) for i in self.clausula_do_campo}

    def _medir(self, bits):
        acerto = self._acerto_por_campo(bits)
        viol = []
        for k in range(self.n_clausulas):
            cs = self.campos_por_clausula[k]
            viol.append(1.0 - sum((acerto[i] for i in cs)) / float(len(cs)) if cs else 0.0)
        pred = [1 if v > 1e-09 else 0 for v in viol] + [1 if v > 0.5 else 0 for v in viol]
        for s in range(1, self.cod.n_grupos):
            cs = [i for i, sec in self.secao_do_campo.items() if sec == s]
            pred.append(1 if cs and sum((acerto[i] for i in cs)) / float(len(cs)) < 0.5 else 0)
        return {'estado': 'ok', 'valores': viol, 'comportamento': sum((int(p) << j for j, p in enumerate(pred))), 'cpu_s': 0.001, 'bytes_de_estado': 1000}

def res_da_v2(V2, violacoes):
    cumpre_piso = {'esquecimento': 0.0, 'ganho_sobre_majoritaria': 0.5, 'acc_final': 0.95, 'plasticidade': 1.0, 'ganho_de_composicao': 0.3, 'correcao': 1.0, 'regra_antiga': 0.0, 'conflito_depois_de_refutacao': 1.0, 'calibracao': 0.3, 'investigar_nas_nao_vistas': 1.0, 'transformacao_ativa': 1.0}
    epistemicas = {'erro_de_calibracao': 0.0, 'conflito_J': 1.0, 'novidade': 1.0}
    estado_e_pi = {'crescimento_do_estado': 0.0, 'crescimento_da_computacao': 0.0, 'flops_por_interacao': 1000.0}
    historico = {'lacuna_de_memoria': 0.0, 'copias_no_estado': 0.0, 'deficit': 0.0, 'deficit_conserva': 0.0, 'deficit_aprende': 0.0, 'deficit_revisa': 0.0, 'acima_do_oraculo': 1.0}
    vidas = [dict(familia='seq', **cumpre_piso, **epistemicas, **estado_e_pi, **historico) for _ in range(4)] + [dict(familia='ling', **cumpre_piso, **epistemicas, **estado_e_pi, **historico) for _ in range(2)] + [dict(familia='tri:comp', compoe_0=0.0, compoe_8=0.3, compoe_32=0.3, compoe_150=0.3, crescimento_da_computacao=0.0, flops_por_interacao=1000.0) for _ in range(2)] + [dict(familia='tri:fam', melhora_com_o_uso=0.3, crescimento_da_computacao=0.0, flops_por_interacao=1000.0) for _ in range(2)] + [dict(familia='tri:reg', latencia_de_adaptacao=0.0, custo_da_volta=0.0, crescimento_da_computacao=0.0, flops_por_interacao=1000.0) for _ in range(2)] + [dict(familia='tri:der', deficit_de_deriva=0.0, crescimento_da_computacao=0.0, flops_por_interacao=1000.0)] + [dict(familia='age', **cumpre_piso, **epistemicas, **estado_e_pi, sucesso_final=0.9) for _ in range(2)]
    res = {'estado': 'ok', 'oraculo': True, 'oraculo_msg': 'ok', 'cpu_s': 0.002, 'tempo_por_familia': {}, 'por_vida': vidas, 'deficit_medido': True, 'memoria_medida': True, 'bytes_de_estado': 1000, 'restauracao_fiel': 1.0, 'usa_informacao_retida': 0, 'divergiu_por_vida': [0, 0, 0, 0], 'diag': {}, 'detalhe': [{'esq': {}, 'gan': {}, 'fin': {}, 'comp': {}, 'corr': {}, 'antiga': {}, 'conflito': {}, 'deficit_por_tarefa': {}} for _ in range(6)]}
    for (cid, medida, op, lim, esc), v in zip(V2.CLAUSULAS, violacoes):
        alvo = lim + float(v) * esc if op == '<=' else lim - float(v) * esc if op == '>=' else float(v)
        if medida in V2.SO_GLOBAIS:
            res[medida] = alvo
        else:
            [vida for vida in vidas if medida in vida][0][medida] = alvo
    return res

class MundoDaV2(MundoDoSerOculto):

    def __init__(self, semente=0):
        from experimentos import desafio_v_ser as V2
        super().__init__(semente, n_clausulas=len(V2.CLAUSULAS))
        self.V2 = V2
        self.nome = 'o Ser escondido (de mentira) medido pela V2 no formato real'

    def problema(self):
        return PD.problema_do_ser()

    def _medir(self, bits):
        return res_da_v2(self.V2, MundoDoSerOculto._medir(self, bits)['valores'])

class MundoDeOrdenacao(_Mundo):

    def __init__(self, n=8, m=24, semente=0):
        cod = CE.CodificacaoDeOrdenacao(n, m)
        self.n = n
        g = np.random.default_rng(2000 + semente)
        self.entradas = (np.arange(1 << n)[:, None] >> np.arange(n)[None, :] & 1).astype(np.uint8)
        self.sondas = g.choice(len(self.entradas), min(96, len(self.entradas)), replace=False)
        nomes = [f'par_{c}_fora_de_ordem' for c in range(n - 1)] + [f'entrada_{int(j)}_nao_ordena' for j in self.sondas]
        super().__init__(cod, n - 1, nomes)
        self.nome = f'rede de ordenação de {n} fios (de verdade, V barata)'

    def _medir(self, bits):
        rede = self.cod.decodificar(bits)
        X = self.entradas.copy()
        for i, j in rede:
            a, b = (X[:, i].copy(), X[:, j].copy())
            X[:, i], X[:, j] = (np.minimum(a, b), np.maximum(a, b))
        fora = X[:, :-1] > X[:, 1:]
        viol = fora.mean(0)
        nao_ordena = fora.any(1)
        pred = [1 if v > 0 else 0 for v in viol] + [int(nao_ordena[j]) for j in self.sondas]
        return {'estado': 'ok', 'valores': [float(v) for v in viol], 'comportamento': sum((int(p) << j for j, p in enumerate(pred))), 'cpu_s': 0.001, 'bytes_de_estado': 100}

class AvaliadorFalso:

    def __init__(self, mundo):
        self.mundo = mundo
        self.medidos = 0

    def medir(self, lista_de_bits):
        self.medidos += len(lista_de_bits)
        return [self.mundo.medir(b) for b in lista_de_bits]

    def fechar(self):
        pass
