"""d_codec3.py (a codificação v3: grupo padrão e exceções; o D e o V são os da d_codec2.py, sem mudança): o D do codec sem perda para a tabela de métricas, para a Máquina do Dever-Ser 4.3.1 só com a seleção, sem mudança nela.

O corpus concorrente  um codec: para cada uma das 496 colunas (o tempo e as 495 métricas), o grupo em que ela entra (0 a 7), e para cada grupo a cadeia de
                      transformações (predição, mapa, empacote, corrida de zeros, fundo, arranjo). Um grupo vira um fluxo por dia; os
                      grupos se decodificam em ordem, e a irmã de uma coluna (a anterior) só vale se já estiver decodificada.
A foto atômica        1.568 bits: 3 por coluna (o grupo) e 10 por grupo (a cadeia). Toda sequência é um codec legal. Os bits da cadeia
                      de um grupo vazio são neutros; as predições 5, 6 e 7 repetem 1, 0 e 1 e vão à forma canônica.
D                     c0_exato      todos os dias de desenvolvimento voltam exatos (os bytes do CSV, pela prova da forma canônica);
                      c1_tamanho    os bytes, sobre os do melhor codec conhecido antes da corrida (o melhor codec único da L, achado pela
                                    busca exaustiva nos 1.024 genes: 61.224 bytes nos dias 5 e 6), no máximo ALVO = 0,95;
                      c2_leitura    decodificar os dois dias em no máximo 0,5 s de CPU (uma trava contra codecs absurdos; a velocidade
                                    entra no relatório, comparada à das alternativas).
V                     codec.medir_codec, nos dias 5 e 6 (os de desenvolvimento). Os outros 23 dias ficam retidos para a confirmação."""
import os

import numpy as np

from experimentos import foto_atomica as FA
from experimentos import problema_de_d as PD

AQUI = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, AQUI)
import codec as K                                              # noqa: E402

NC, NG, BG, BC = 496, 8, 3, 10
NE, BCOL = 64, 9                                               # (v3) até 64 exceções; a coluna em 9 bits (496 a 511 = exceção vazia)
REF = 61224                                                    # o melhor conhecido antes da corrida nos dias 5 e 6: o melhor codec único da L (grupo_unico.json), 19,5% menor que a melhor alternativa genérica (colunar int32 + xz -9e, 76.084, alternativas.json)
ALVO = float(os.environ.get("D_CODEC_ALVO", "0.95"))
SUBCAMPOS = (("predicao", 3), ("mapa", 1), ("empacote", 2), ("rle0", 1), ("fundo", 2), ("arranjo", 1))


class CodificacaoDoCodec(FA.CodificacaoBase):
    """Versão 3 (18/10, depois da corrida 2): um grupo padrão (o 0) para todas as colunas, e até NE exceções, cada uma (coluna, grupo
    de 1 a 7). Na versão 2 (um grupo por coluna), juntar as colunas no mesmo grupo exigia mudar centenas de campos, e a corrida 2 não
    chegou ao melhor codec conhecido, que tem um grupo só. Aqui esse codec é a foto sem exceções."""
    def __init__(self):
        self.nome = "codec sem perda v3: grupo padrão, exceções (coluna, grupo) e a cadeia de cada grupo"
        self.versao = 3
        self.n_bits = NE * (BCOL + BG) + NG * BC
        self.nomes_dos_grupos = ["excecoes", "cadeias"]
        self.campos = []
        p = 0
        for e in range(NE):
            self.campos.append({"nome": f"excecoes.e{e}.coluna", "grupo": 0, "tipo": "gene", "bits": BCOL, "inicio": p}); p += BCOL
            self.campos.append({"nome": f"excecoes.e{e}.grupo", "grupo": 0, "tipo": "gene", "bits": BG, "inicio": p}); p += BG
        for k in range(NG):
            for nome, b in SUBCAMPOS:
                self.campos.append({"nome": f"cadeias.g{k}.{nome}", "grupo": 1, "tipo": "gene", "bits": b, "inicio": p}); p += b
        assert p == self.n_bits
        self.unidades = tuple({"inicio": c["inicio"], "bits": c["bits"], "grupo": c["grupo"]} for c in self.campos)

    @staticmethod
    def _num(b):
        return int("".join(str(int(x)) for x in b), 2) if len(b) else 0

    def _ler(self, bits):
        b = np.asarray(bits, np.uint8)
        exc = {}
        for e in range(NE):
            q = e * (BCOL + BG)
            col, g = self._num(b[q:q + BCOL]), self._num(b[q + BCOL:q + BCOL + BG])
            if col < NC and g != 0:
                exc[col] = g                                      # uma coluna repetida: vale a última exceção
        base = NE * (BCOL + BG)
        genes = [self._num(b[base + k * BC: base + (k + 1) * BC]) for k in range(NG)]
        return exc, genes

    @staticmethod
    def _gene_canonico(g, usado):
        if not usado:
            return 0
        pred = (g >> 7) & 7
        pred = {5: 1, 6: 0, 7: 1}.get(pred, pred)
        return (pred << 7) | (g & 0x7F)

    def decodificar(self, bits):
        exc, genes = self._ler(bits)
        grupos = [exc.get(j, 0) for j in range(NC)]
        usados = set(grupos)
        return tuple(grupos), tuple(self._gene_canonico(g, k in usados) for k, g in enumerate(genes))

    def codificar(self, corpus):
        grupos, genes = corpus
        exc = [(j, g) for j, g in enumerate(grupos) if g != 0]
        assert len(exc) <= NE
        exc += [((1 << BCOL) - 1, 0)] * (NE - len(exc))         # a exceção vazia canônica: a coluna 511 (fora da tabela) e o grupo 0
        out = []
        for col, g in exc:
            out += [(col >> (BCOL - 1 - t)) & 1 for t in range(BCOL)] + [(g >> (BG - 1 - t)) & 1 for t in range(BG)]
        out += [(int(g) >> (BC - 1 - t)) & 1 for g in genes for t in range(BC)]
        return np.array(out, np.uint8)

    def canonizar(self, bits):
        return self.codificar(self.decodificar(bits))

    def ativos(self, bits):
        grupos, _ = self.decodificar(bits)
        at = np.ones(self.n_bits, bool)
        base = NE * (BCOL + BG)
        for k in range(NG):
            if k not in grupos:
                at[base + k * BC: base + (k + 1) * BC] = False
        return at

    def sortear(self, rng):
        return self.canonizar(rng.integers(0, 2, self.n_bits).astype(np.uint8))


# (18/10, a corrida 1 parou) Na corrida 1 a escala 0,15 saturava a distância (cada violação é limitada a 1 no julgamento) para todo codec
# acima de 1,10 da referência, e os de partida ficam de 2 a 21 vezes: a máquina não distinguia nenhum. A cláusula c1 passa a medir o log2
# dos bytes sobre a referência, com o mesmo limite (log2 de ALVO, o mesmo D: bytes <= ALVO x REF) e escala 5: não satura até 2^5 = 32
# vezes, e a resolução da distância (um milésimo) fica em 0,35% dos bytes.
CLAUSULAS = [("c0_exato", "dias_errados", "<=", 0.0, 1.0), ("c1_tamanho", "log2_bytes_sobre_o_melhor_conhecido", "<=", float(np.log2(ALVO)), 5.0),
             ("c2_leitura", "segundos_de_decodificar", "<=", 0.5, 0.5)]
CLASSES = ("cumpre D", "a 1 cláusula de D", "2 cláusulas", "3 cláusulas", "sem classe (estouro, erro ou oráculo)")
NOMES = [f"falha:{c[0]}" for c in CLAUSULAS] + [f"longe:{c[0]}" for c in CLAUSULAS] + ["usa_lzma6", "usa_lzma9e", "mais_de_4_grupos"]


class Predicados:
    versao = 1
    duras = list(range(len(CLAUSULAS)))

    def __len__(self):
        return len(NOMES)

    def mascara_das_duras(self):
        return (1 << len(self.duras)) - 1

    def duras_que_falham(self, comp):
        return [i for i in self.duras if (int(comp) >> i) & 1]

    def descricao(self):
        return {"versao": self.versao, "predicados": len(NOMES), "duras": len(self.duras), "nomes": NOMES, "regra": "1 = o codec faz o que D não quer (ou o traço indicado)"}


def violacoes(valores):
    return [max(0.0, float(v) - lim) / esc for (_, _, op, lim, esc), v in zip(CLAUSULAS, valores)]


def violacoes_de_coluna(i, v):
    return np.maximum(0.0, np.asarray(v, np.float64) - CLAUSULAS[i][3]) / CLAUSULAS[i][4]


def classe_da_distancia(nfal, estado="ok"):
    if estado != "ok":
        return len(CLASSES) - 1
    return min(nfal, 3)


def julgar(res):
    n = len(CLAUSULAS)
    if res["estado"] != "ok":
        return {"estado": res["estado"], "valores": [float("nan")] * n, "violacoes": [1.0] * n, "distancia": 1000 * n + 1, "nfal": n, "classe": classe_da_distancia(n, res["estado"]),
                "comportamento": 0, "cpu_s": float(res.get("cpu_s", 0.0)), "bytes": 0}
    viol = violacoes(res["valores"])
    nfal = sum(1 for v in viol if v > 1e-9)
    return {"estado": "ok", "valores": [float(v) for v in res["valores"]], "violacoes": viol, "distancia": int(round(1000.0 * sum(min(v, 1.0) for v in viol))), "nfal": nfal,
            "classe": classe_da_distancia(nfal), "comportamento": int(res["comportamento"]), "cpu_s": float(res["cpu_s"]), "bytes": int(res["bytes_de_estado"])}


class Avaliador:
    def __init__(self, dias_de_v=(5, 6)):
        self.cod = CodificacaoDoCodec()
        cab, self.esc, x = K.ler_tabela(os.path.join(AQUI, "dados", "itens.csv"))
        assert x.shape[1] == NC
        self.blocos = [x[i * K.MIN_DIA:(i + 1) * K.MIN_DIA] for i in dias_de_v]

    def medir_corpus(self, corpus):
        grupos, genes = corpus
        r = K.medir_codec(self.blocos, [None] * len(self.blocos), self.esc, list(grupos), list(genes))
        if r["estado"] != "ok":
            return {"estado": "erro", "cpu_s": 0.0}
        valores = [r["erros"], float(np.log2(r["bytes"] / REF)), r["s_decodificar"]]
        viol = violacoes(valores)
        cad = [K.gene_para_cadeia(g) for k, g in enumerate(genes) if k in set(grupos)]
        pred = [int(v > 1e-9) for v in viol] + [int(v > 1.0) for v in viol] + [int(any(c["fundo"] == "lzma6" for c in cad)), int(any(c["fundo"] == "lzma9e" for c in cad)),
                                                                            int(len(set(grupos)) > 4)]
        return {"estado": "ok", "valores": valores, "comportamento": sum(p << j for j, p in enumerate(pred)), "cpu_s": r["s_codificar"] + r["s_decodificar"],
                "bytes_de_estado": int(r["bytes"]), "bytes": int(r["bytes"])}

    def medir(self, lista_de_bits):
        return [self.medir_corpus(self.cod.decodificar(b)) for b in lista_de_bits]

    def fechar(self):
        pass


def criar():
    av = Avaliador()
    problema = PD.Problema(f"codec sem perda para a tabela de métricas, no máximo {ALVO:.2f} da melhor alternativa", av.cod, Predicados(), NOMES, CLAUSULAS, CLASSES, violacoes,
                           violacoes_de_coluna, julgar)
    return problema, av
