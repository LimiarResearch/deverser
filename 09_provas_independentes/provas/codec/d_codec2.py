"""d_codec2.py (a d_codec.py com a escala de c1 corrigida, ver CLAUSULAS): o D do codec sem perda para a tabela de métricas, para a Máquina do Dever-Ser 4.3.1 só com a seleção, sem mudança nela.

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
REF = 61224                                                    # o melhor conhecido antes da corrida nos dias 5 e 6: o melhor codec único da L (grupo_unico.json), 19,5% menor que a melhor alternativa genérica (colunar int32 + xz -9e, 76.084, alternativas.json)
ALVO = float(os.environ.get("D_CODEC_ALVO", "0.95"))
SUBCAMPOS = (("predicao", 3), ("mapa", 1), ("empacote", 2), ("rle0", 1), ("fundo", 2), ("arranjo", 1))


class CodificacaoDoCodec(FA.CodificacaoBase):
    def __init__(self):
        self.nome = "codec sem perda: grupo de cada coluna e cadeia de cada grupo"
        self.versao = 2                                       # L2: o fundo 2 passou de bz2 -9 a lzma -9e
        self.n_bits = NC * BG + NG * BC
        self.nomes_dos_grupos = ["colunas", "cadeias"]
        self.campos = [{"nome": f"colunas.c{j}.grupo", "grupo": 0, "tipo": "gene", "bits": BG, "inicio": j * BG} for j in range(NC)]
        p = NC * BG
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
        grupos = [self._num(b[j * BG:(j + 1) * BG]) for j in range(NC)]
        genes = [self._num(b[NC * BG + k * BC: NC * BG + (k + 1) * BC]) for k in range(NG)]
        return grupos, genes

    @staticmethod
    def _gene_canonico(g, usado):
        if not usado:
            return 0
        pred = (g >> 7) & 7
        pred = {5: 1, 6: 0, 7: 1}.get(pred, pred)
        return (pred << 7) | (g & 0x7F)

    def decodificar(self, bits):
        grupos, genes = self._ler(bits)
        usados = set(grupos)
        return tuple(grupos), tuple(self._gene_canonico(g, k in usados) for k, g in enumerate(genes))

    def codificar(self, corpus):
        grupos, genes = corpus
        out = [(int(v) >> (BG - 1 - t)) & 1 for v in grupos for t in range(BG)] + [(int(g) >> (BC - 1 - t)) & 1 for g in genes for t in range(BC)]
        return np.array(out, np.uint8)

    def canonizar(self, bits):
        return self.codificar(self.decodificar(bits))

    def ativos(self, bits):
        grupos, _ = self._ler(bits)
        at = np.ones(self.n_bits, bool)
        for k in range(NG):
            if k not in grupos:
                at[NC * BG + k * BC: NC * BG + (k + 1) * BC] = False
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
