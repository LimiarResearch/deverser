"""Um D NOVO escrito do zero: tudo o que é preciso para ligar um problema à máquina, em um arquivo (o guia está no manual, parte IV).

O corpus concorrente  uma lista de 8 números inteiros de 0 a 15.
A foto atômica        os 32 bits da lista (4 bits por número); toda sequência de 32 bits é uma lista legal, e nenhum bit é neutro.
D (a intenção)        "uma lista de soma 60, com metade dos números pares, no máximo um zero, o primeiro número de 8 para cima, o último de 7 para baixo e exatamente dois quinzes", em seis cláusulas:
                        c0_soma        <= 0    |soma - 60| / 60
                        c1_paridade    <= 0    |quantos pares - 4| / 4
                        c2_zeros       <= 0    zeros além de um, sobre 7
                        c3_primeiro    <= 0    quanto o primeiro número fica abaixo de 8, sobre 8
                        c4_ultimo      <= 0    quanto o último número passa de 7, sobre 8
                        c5_quinzes     <= 0    |quantos quinzes - 2| / 2
V (o medidor)         `medir_lista`: devolve o valor de cada cláusula e o COMPORTAMENTO (a foto comportamental: 14 predicados, 1 = a lista faz o que D não quer; os seis primeiros são as
                      cláusulas falhando, as "duras").

Rodar (a autorização é de quem manda na corrida; a frase fica na declaração):
  python -B -m experimentos.condutor_de_d --problema exemplos.novo_d_do_zero:criar --saida /tmp/corrida_exemplo --config exemplos/config_do_exemplo.json \\
         --max-rodadas 200 --semente 2 --autorizacao "Fulano, 2026-10-01: pode rodar o exemplo"

Este é um D de brinquedo: serve para ver as peças e a forma, e uma corrida que acha D mostra a parada que espera o Ok_k (`candidata_<k>.json`). Nada aqui é V do Codex."""
import numpy as np

from experimentos import foto_atomica as FA
from experimentos import problema_de_d as PD

N, B = 8, 4                                                   # 8 números de 4 bits
SOMA = 60


# ------------------------------------------------------------------ 1. a codificação da foto atômica (o corpus vira bits, e os bits viram corpus)
class CodificacaoDaLista(FA.CodificacaoBase):
    def __init__(self):
        self.nome = "lista de 8 números de 4 bits"
        self.versao = 1                                       # mudar a codificação é outra versão, declarada
        self.n_bits = N * B
        self.nomes_dos_grupos = ["lista"]
        # o nome do campo é `grupo.nI.papel`: o PAPEL (o último pedaço) diz o que o campo é, e a rede aprende o que vale para todos os campos do mesmo papel (os 8 números têm o papel `valor`)
        self.campos = [{"nome": f"lista.n{i}.valor", "grupo": 0, "tipo": "gene", "bits": B, "inicio": i * B} for i in range(N)]
        self.unidades = tuple({"inicio": c["inicio"], "bits": c["bits"], "grupo": 0} for c in self.campos)      # o número inteiro é a unidade que o escritor reescreve

    def decodificar(self, bits):                              # o corpus que a foto descreve (None se a sequência não for corpus: aqui toda sequência é)
        b = np.asarray(bits, np.uint8)
        return tuple(int("".join(str(int(x)) for x in b[i * B:(i + 1) * B]), 2) for i in range(N))

    def codificar(self, corpus):                              # a foto canônica de um corpus
        return np.array([(int(v) >> (B - 1 - t)) & 1 for v in corpus for t in range(B)], np.uint8)

    def canonizar(self, bits):                                # duas fotos do mesmo corpus têm a mesma foto canônica: aqui a foto já é única
        return np.asarray(bits, np.uint8).copy()

    def ativos(self, bits):                                   # os bits que podem mudar o corpus: todos
        return np.ones(self.n_bits, bool)

    def sortear(self, rng):                                   # uma foto legal e canônica ao acaso
        return rng.integers(0, 2, self.n_bits).astype(np.uint8)


# ------------------------------------------------------------------ 2. V: as cláusulas de D, o medidor e o veredito
CLAUSULAS = [("c0_soma", "erro_da_soma", "<=", 0.0, 1.0), ("c1_paridade", "erro_de_paridade", "<=", 0.0, 1.0), ("c2_zeros", "zeros_demais", "<=", 0.0, 1.0),
             ("c3_primeiro", "primeiro_baixo", "<=", 0.0, 1.0), ("c4_ultimo", "ultimo_alto", "<=", 0.0, 1.0), ("c5_quinzes", "erro_de_quinzes", "<=", 0.0, 1.0)]       # (id, medida, operador, limite, escala)
CLASSES = ("cumpre D", "a 1 cláusula de D", "2 a 3 cláusulas", "4 ou mais cláusulas", "sem classe (estouro, erro ou oráculo)")      # a última é sempre "sem classe"
NOMES = [f"falha:{c[0]}" for c in CLAUSULAS] + [f"longe:{c[0]}" for c in CLAUSULAS] + ["soma_acima_de_90", "soma_abaixo_de_30"]


class Predicados:
    """A descrição da foto comportamental: os predicados são FIXOS e versionados; as `duras` são as que dizem que uma cláusula de D falha (as primeiras, uma por cláusula)."""
    versao = 1
    duras = list(range(len(CLAUSULAS)))

    def __len__(self):
        return len(NOMES)

    def mascara_das_duras(self):
        return (1 << len(self.duras)) - 1

    def duras_que_falham(self, comp):
        return [i for i in self.duras if (int(comp) >> i) & 1]

    def descricao(self):
        return {"versao": self.versao, "predicados": len(NOMES), "duras": len(self.duras), "nomes": NOMES, "regra": "1 = a lista faz o que D não quer"}


def violacoes(valores):
    """A violação de cada cláusula, em unidades da escala dela (0 = cumpre). Neste exemplo todas as cláusulas são `<=`."""
    return [max(0.0, float(v) - lim) / esc for (_, _, op, lim, esc), v in zip(CLAUSULAS, valores)]


def violacoes_de_coluna(i, v):
    """A violação da cláusula `i` para uma coluna de valores (o arquivo de fotos resume por cláusula quantas fotos a cumprem)."""
    return np.maximum(0.0, np.asarray(v, np.float64) - CLAUSULAS[i][3]) / CLAUSULAS[i][4]


def classe_da_distancia(nfal, estado="ok"):
    if estado != "ok":
        return len(CLASSES) - 1
    return 0 if nfal == 0 else (1 if nfal == 1 else (2 if nfal <= 3 else 3))


def medir_lista(lista):
    """O medidor: o que a lista FAZ diante de D. Devolve o resultado no formato que o condutor espera (`estado`, `valores` das cláusulas, `comportamento`, `cpu_s`, `bytes_de_estado`)."""
    a = np.array(lista, np.int64)
    soma = int(a.sum())
    valores = [abs(soma - SOMA) / 60.0, abs(int((a % 2 == 0).sum()) - N // 2) / (N // 2), max(0, int((a == 0).sum()) - 1) / (N - 1), max(0, 8 - int(a[0])) / 8.0, max(0, int(a[-1]) - 7) / 8.0, abs(int((a == 15).sum()) - 2) / 2.0]
    viol = violacoes(valores)
    pred = [int(v > 1e-9) for v in viol] + [int(v > 0.25) for v in viol] + [int(soma > 90), int(soma < 30)]
    return {"estado": "ok", "valores": valores, "comportamento": sum(p << j for j, p in enumerate(pred)), "cpu_s": 1e-4, "bytes_de_estado": 0}


def julgar(res):
    """O veredito de um resultado: a violação de cada cláusula, a distância a D (em milésimos: cada violação limitada a uma cláusula inteira), quantas falham, a classe e o comportamento."""
    if res["estado"] != "ok":                                 # um concorrente sem medida (estouro, erro) está pior que qualquer um
        n = len(CLAUSULAS)
        return {"estado": res["estado"], "valores": [float("nan")] * n, "violacoes": [1.0] * n, "distancia": 1000 * n + 1, "nfal": n, "classe": classe_da_distancia(n, res["estado"]),
                "comportamento": 0, "cpu_s": float(res.get("cpu_s", 0.0)), "bytes": 0}
    viol = violacoes(res["valores"])
    nfal = sum(1 for v in viol if v > 1e-9)
    return {"estado": "ok", "valores": [float(v) for v in res["valores"]], "violacoes": viol, "distancia": int(round(1000.0 * sum(min(v, 1.0) for v in viol))), "nfal": nfal,
            "classe": classe_da_distancia(nfal), "comportamento": int(res["comportamento"]), "cpu_s": float(res["cpu_s"]), "bytes": int(res["bytes_de_estado"])}


class Avaliador:
    """O que o condutor chama: `medir(lista_de_bits)` devolve, na ordem, o resultado de V para cada foto (V é determinista: a mesma foto dá o mesmo resultado)."""

    def __init__(self):
        self.cod = CodificacaoDaLista()

    def medir(self, lista_de_bits):
        return [medir_lista(self.cod.decodificar(b)) for b in lista_de_bits]

    def fechar(self):
        pass


# ------------------------------------------------------------------ 3. o Problema: a codificação e V juntas, a única coisa que muda de um D para outro
def criar():
    av = Avaliador()
    problema = PD.Problema("lista de 8 números: soma 60, metade pares, no máximo um zero, primeiro alto, último baixo e dois quinzes (exemplo)", av.cod, Predicados(), NOMES, CLAUSULAS, CLASSES, violacoes, violacoes_de_coluna, julgar)
    return problema, av
