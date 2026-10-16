"""A máquina mínima: o leito da escada do bit (decisão de 03/10/2026: o mundo do ser opera no nível do bit, onde
ele pode operar em qualquer lugar e construir qualquer coisa; a regra de segurança abaixo foi adotada junto com essa direção).

Um computador pequeno, determinista e FECHADO, simulado no nível do bit. Ele roda igual em qualquer máquina porque é simulado, e é o mundo em que o ser começa: os degraus da escada são Ds
sobre ele, do "copie um bit" para cima.

  a memória      R = 16 células de 1 bit (0 a 15). V escreve a entrada nas primeiras células (o bit i da entrada na célula i) e lê a saída nas últimas (o bit j da saída na célula 15 - j); o resto
                 começa em 0
  o programa     P = 16 instruções de 15 bits cada (a operação em 3 bits, o destino em 4, os operandos a e b em 4 cada): 240 bits. O corpus concorrente É o programa (a foto atômica são estes 240 bits)
  as operações   0 NADA; 1 COPIA d <- a; 2 NAO d <- não a; 3 E d <- a e b; 4 OU d <- a ou b; 5 XOU d <- a xou b; 6 NAOE d <- não (a e b); 7 SALTA: se a célula a vale 0, a próxima instrução é a d
  o tempo        contado em passos: o programa começa na instrução 0, anda uma por passo (ou salta) e para ao passar da última ou no teto de passos (64). Não há relógio de parede
  fechada        (a REGRA de segurança adotada) a máquina é uma função pura dos bits do programa e da entrada para os bits da memória: não há rede, arquivo, relógio nem chamada ao
                 sistema. O juiz (V) lê a saída de fora; o programa só toca a própria memória simulada, e nunca o arquivo, o condutor ou V

Os números (16 células, 16 instruções, as 8 operações, o teto de 64 passos) são escolhas de projeto, declaradas; mudar um deles é outra versão da máquina.

Só numpy. Nada aqui muda a V do Ser."""
import os

import numpy as np

from experimentos import foto_atomica as FA

R = 16                     # células de memória
P = 16                     # instruções do programa
TETO = 64                  # passos
LARGURA = 15               # bits por instrução: operação 3, destino 4, a 4, b 4
OPERACOES = ("NADA", "COPIA", "NAO", "E", "OU", "XOU", "NAOE", "SALTA")
USA_A = {1, 2, 3, 4, 5, 6, 7}
USA_B = {3, 4, 5, 6}
USA_D = {1, 2, 3, 4, 5, 6, 7}
MOTOR = os.environ.get("ESCADA_MOTOR", "numpy")   # (03/10) "numpy" ou "c" (`maquina_minima_c`, a mesma tabela de saída, bit a bit; pede o gcc)


def executar(prog, entradas, teto=TETO):
    """A memória final (L, R) do programa `prog` (P x 4: operação, destino, a, b) para cada uma das L entradas (L x k bits, na ordem das células 0 a k-1). Todas as entradas andam juntas
    (vetorizado); o salto pode separá-las, e cada uma segue a sua instrução."""
    prog = np.asarray(prog, np.int64)
    ent = np.asarray(entradas, np.uint8)
    L, k = ent.shape
    m = np.zeros((L, R), np.uint8)
    m[:, :k] = ent
    pc = np.zeros(L, np.int64)
    n = len(prog)
    for _ in range(int(teto)):
        vivos = pc < n
        if not vivos.any():
            break
        for i in np.unique(pc[vivos]):
            faixa = np.flatnonzero(pc == i)
            op, d, a, b = (int(x) for x in prog[i])
            if op == 7:
                zero = m[faixa, a] == 0
                pc[faixa[zero]] = d
                pc[faixa[~zero]] = i + 1
                continue
            if op == 1:
                m[faixa, d] = m[faixa, a]
            elif op == 2:
                m[faixa, d] = 1 - m[faixa, a]
            elif op == 3:
                m[faixa, d] = m[faixa, a] & m[faixa, b]
            elif op == 4:
                m[faixa, d] = m[faixa, a] | m[faixa, b]
            elif op == 5:
                m[faixa, d] = m[faixa, a] ^ m[faixa, b]
            elif op == 6:
                m[faixa, d] = 1 - (m[faixa, a] & m[faixa, b])
            pc[faixa] = i + 1
    return m


def saida(memoria, n_saida):
    """Os bits de saída: o bit j está na célula R - 1 - j."""
    return np.stack([memoria[:, R - 1 - j] for j in range(n_saida)], axis=1)


class CodificacaoDaMaquina(FA.CodificacaoBase):
    """O programa da máquina mínima em bits: P instruções de 15 bits (operação 3, destino 4, a 4, b 4). Toda sequência é um programa (total); a forma canônica zera os bits de operando que a
    operação não lê (o neutro declarado: NADA não lê nenhum; COPIA, NAO e SALTA não leem b)."""

    def __init__(self, p=P):
        self.p = int(p)
        self.nome = f"a máquina mínima ({self.p} instruções de {LARGURA} bits)"
        self.versao = 1
        self.n_bits = self.p * LARGURA
        self.nomes_dos_grupos = ["programa"]
        self.campos = []
        for i in range(self.p):
            for papel, nb, desloc in (("operacao", 3, 0), ("destino", 4, 3), ("a", 4, 7), ("b", 4, 11)):
                self.campos.append({"nome": f"programa.i{i}.{papel}", "grupo": 0, "tipo": "gene", "bits": nb, "inicio": i * LARGURA + desloc})
        self.unidades = tuple({"inicio": i * LARGURA, "bits": LARGURA, "grupo": 0} for i in range(self.p))   # a instrução inteira é a unidade que o escritor reescreve

    @staticmethod
    def _int(b):
        v = 0
        for x in b:
            v = (v << 1) | int(x)
        return v

    # (03/10, a velocidade) a leitura e a escrita dos campos de uma vez, com numpy: os mesmos números das versões de laço (a prova está em `testes/test_maquina_minima_c.py`)
    _LARGURAS = (3, 4, 4, 4)
    _INICIOS = (0, 3, 7, 11)

    def decodificar(self, bits):
        b = np.asarray(bits, np.uint8)
        if len(b) != self.n_bits:
            return None
        x = b.reshape(self.p, LARGURA).astype(np.int64)
        out = np.zeros((self.p, 4), np.int64)
        for c, (ini, nb) in enumerate(zip(self._INICIOS, self._LARGURAS)):
            out[:, c] = x[:, ini:ini + nb] @ (1 << np.arange(nb - 1, -1, -1))
        return out

    def _canonicos(self, prog):
        prog = np.asarray(prog, np.int64).reshape(-1, 4)
        op = prog[:, 0]
        usa = (op >= 1) & (op <= 7)                                                    # USA_A = USA_D = 1 a 7
        return np.stack([op, np.where(usa, prog[:, 1], 0), np.where(usa, prog[:, 2], 0), np.where((op >= 3) & (op <= 6), prog[:, 3], 0)], axis=1)

    def codificar(self, prog):
        c = self._canonicos(prog)
        b = np.zeros((self.p, LARGURA), np.uint8)
        n = min(len(c), self.p)
        for k, (ini, nb) in enumerate(zip(self._INICIOS, self._LARGURAS)):
            b[:n, ini:ini + nb] = (c[:n, k, None] >> np.arange(nb - 1, -1, -1)[None, :]) & 1
        return b.reshape(-1)

    def canonizar(self, bits):
        prog = self.decodificar(bits)
        return None if prog is None else self.codificar(prog)

    def ativos(self, bits):
        op = self.decodificar(bits)[:, 0]
        m = np.zeros((self.p, LARGURA), bool)
        m[:, 0:3] = True
        usa = ((op >= 1) & (op <= 7))[:, None]
        m[:, 3:7] = usa
        m[:, 7:11] = usa
        m[:, 11:15] = ((op >= 3) & (op <= 6))[:, None]
        return m.reshape(-1)

    def sortear(self, rng):
        return self.canonizar(rng.integers(0, 2, self.n_bits).astype(np.uint8))


def texto(prog):
    """O programa legível (para o relatório e para quem confere)."""
    linhas = []
    for i, (op, d, a, b) in enumerate(np.asarray(prog, np.int64)):
        nome = OPERACOES[int(op)]
        if op == 0:
            continue
        if op == 7:
            linhas.append(f"{i:2d}: SALTA para {d} se m[{a}] = 0")
        elif op in (1, 2):
            linhas.append(f"{i:2d}: m[{d}] <- {nome} m[{a}]")
        else:
            linhas.append(f"{i:2d}: m[{d}] <- m[{a}] {nome} m[{b}]")
    return "\n".join(linhas) if linhas else "(programa vazio)"


# ------------------------------------------------------------------ os cinco primeiros degraus da escada (os alvos; as cláusulas e V ficam em `bancada_c2/ds.py`)
def _todas(k):
    return ((np.arange(1 << k)[:, None] >> np.arange(k)[None, :]) & 1).astype(np.uint8)


def _copia(x):
    return x.copy()


def _nega(x):
    return 1 - x


def _meio_somador(x):
    return np.stack([x[:, 0] ^ x[:, 1], x[:, 0] & x[:, 1]], axis=1)


def _somador_completo(x):
    a, b, c = x[:, 0], x[:, 1], x[:, 2]
    return np.stack([a ^ b ^ c, (a & b) | (c & (a ^ b))], axis=1)


def _somador_2(x):
    a = x[:, 0] + 2 * x[:, 1]
    b = x[:, 2] + 2 * x[:, 3]
    s = a + b
    return np.stack([(s >> j) & 1 for j in range(3)], axis=1).astype(np.uint8)


DEGRAUS = {
    "e0_copia_bit": {"entrada": 1, "saida": 1, "alvo": _copia, "o_que_e": "copie um bit: a saída é a entrada"},
    "e1_nega_bit": {"entrada": 1, "saida": 1, "alvo": _nega, "o_que_e": "negue um bit"},
    "e2_copia_palavra": {"entrada": 4, "saida": 4, "alvo": _copia, "o_que_e": "copie uma palavra de 4 bits"},
    "e3_meio_somador": {"entrada": 2, "saida": 2, "alvo": _meio_somador, "o_que_e": "some dois bits: a soma (a xou b) e o vai-um (a e b)"},
    "e3b_somador_completo": {"entrada": 3, "saida": 2, "alvo": _somador_completo, "o_que_e": "some três bits (a, b e o vai-um de entrada): a soma e o vai-um (o degrau entre o e3 e o e4, "
                             "apontado pelo Fable em 03/10)"},
    "e4_somador_2": {"entrada": 4, "saida": 3, "alvo": _somador_2, "o_que_e": "some dois números de 2 bits (a = bits 0 e 1, b = bits 2 e 3; a soma em 3 bits)"},
}


def tabela(nome):
    """(as entradas, a saída esperada) do degrau: todas as entradas possíveis (a tabela inteira; nos degraus maiores, um sorteio declarado por semente)."""
    g = DEGRAUS[nome]
    x = _todas(g["entrada"])
    return x, np.asarray(g["alvo"](x), np.uint8)


# ------------------------------------------------------------------ a regra de promoção: o que resolve um degrau vira instrução nos degraus de cima (o tecido é a escada; o elo é o corrimão)
LARGURA_B = 16             # com biblioteca, a operação ganha um bit: 0 a 7 são as de base; 8 + k chama a peça k da biblioteca


def promover(prog, degrau, origem):
    """Uma peça da biblioteca a partir do programa que cumpriu `degrau` (o achado pela busca, como foi achado). A peça guarda a TABELA de saída do programa em todas as entradas do degrau: a
    máquina é determinista e a tabela foi conferida por V em todas as entradas possíveis, então a instrução nova faz exatamente o que o programa provou fazer (mesmo que ele use laços e o
    teto de passos). Peças de até 2 entradas cabem numa instrução (os operandos a e b)."""
    x, y = tabela(degrau)
    s = saida(executar(prog, x), y.shape[1])
    if not (s == y).all():
        raise ValueError("o programa não cumpre o degrau: não se promove")
    k = x.shape[1]
    if k > 2:
        raise ValueError("uma instrução lê até 2 entradas (os operandos a e b)")
    return {"nome": degrau, "entrada": int(k), "saida": int(y.shape[1]), "tabela": s.astype(int).tolist(), "programa": np.asarray(prog, int).tolist(), "origem": origem}


def executar_com_biblioteca(prog, entradas, biblioteca, teto=TETO):
    """Como `executar`, com as operações 8 + k chamando a peça k: as entradas da peça vêm de m[a] (e de m[b], se ela lê duas); a saída j da peça vai para a célula (d - j) mod R, descendo como
    a saída da própria máquina. A chamada conta como um passo (a peça é uma instrução neste degrau)."""
    prog = np.asarray(prog, np.int64)
    ent = np.asarray(entradas, np.uint8)
    L, k = ent.shape
    m = np.zeros((L, R), np.uint8)
    m[:, :k] = ent
    pc = np.zeros(L, np.int64)
    n = len(prog)
    tabelas = [np.asarray(b["tabela"], np.uint8) for b in biblioteca]
    for _ in range(int(teto)):
        vivos = pc < n
        if not vivos.any():
            break
        for i in np.unique(pc[vivos]):
            faixa = np.flatnonzero(pc == i)
            op, d, a, b = (int(x) for x in prog[i])
            if op >= 8:
                kb = op - 8
                if kb < len(biblioteca):
                    peca = biblioteca[kb]
                    idx = m[faixa, a].astype(np.int64) + (2 * m[faixa, b].astype(np.int64) if peca["entrada"] == 2 else 0)
                    linha = tabelas[kb][idx]
                    for j in range(peca["saida"]):
                        m[faixa, (d - j) % R] = linha[:, j]
                pc[faixa] = i + 1
                continue
            if op == 7:
                zero = m[faixa, a] == 0
                pc[faixa[zero]] = d
                pc[faixa[~zero]] = i + 1
                continue
            if op == 1:
                m[faixa, d] = m[faixa, a]
            elif op == 2:
                m[faixa, d] = 1 - m[faixa, a]
            elif op == 3:
                m[faixa, d] = m[faixa, a] & m[faixa, b]
            elif op == 4:
                m[faixa, d] = m[faixa, a] | m[faixa, b]
            elif op == 5:
                m[faixa, d] = m[faixa, a] ^ m[faixa, b]
            elif op == 6:
                m[faixa, d] = 1 - (m[faixa, a] & m[faixa, b])
            pc[faixa] = i + 1
    return m


class CodificacaoComBiblioteca(CodificacaoDaMaquina):
    """O programa da máquina com biblioteca: P instruções de 16 bits (operação 4, destino 4, a 4, b 4). As operações 8 + k chamam a peça k; um código de peça que não existe vale NADA (a forma
    canônica o zera: toda sequência continua sendo um programa)."""

    def __init__(self, biblioteca, p=P):
        self.biblioteca = list(biblioteca)
        self.p = int(p)
        self.nome = f"a máquina mínima com biblioteca ({len(self.biblioteca)} peças; {self.p} instruções de {LARGURA_B} bits)"
        self.versao = 2
        self.n_bits = self.p * LARGURA_B
        self.nomes_dos_grupos = ["programa"]
        self.campos = []
        for i in range(self.p):
            for papel, nb, desloc in (("operacao", 4, 0), ("destino", 4, 4), ("a", 4, 8), ("b", 4, 12)):
                self.campos.append({"nome": f"programa.i{i}.{papel}", "grupo": 0, "tipo": "gene", "bits": nb, "inicio": i * LARGURA_B + desloc})
        self.unidades = tuple({"inicio": i * LARGURA_B, "bits": LARGURA_B, "grupo": 0} for i in range(self.p))

    def _usa(self, op):
        if op >= 8:
            kb = op - 8
            if kb >= len(self.biblioteca):
                return False, False, False
            return True, True, self.biblioteca[kb]["entrada"] == 2
        return op in USA_D, op in USA_A, op in USA_B

    def decodificar(self, bits):
        b = np.asarray(bits, np.uint8)
        if len(b) != self.n_bits:
            return None
        out = np.zeros((self.p, 4), np.int64)
        for i in range(self.p):
            x = b[i * LARGURA_B:(i + 1) * LARGURA_B]
            op = self._int(x[0:4])
            if op >= 8 and op - 8 >= len(self.biblioteca):
                op = 0
            out[i] = (op, self._int(x[4:8]), self._int(x[8:12]), self._int(x[12:16]))
        return out

    def codificar(self, prog):
        prog = np.asarray(prog, np.int64)
        b = np.zeros(self.n_bits, np.uint8)
        for i, (op, d, a, bb) in enumerate(prog):
            op = int(op) if not (int(op) >= 8 and int(op) - 8 >= len(self.biblioteca)) else 0
            ud, ua, ub = self._usa(op)
            d, a, bb = (int(d) if ud else 0), (int(a) if ua else 0), (int(bb) if ub else 0)
            for valor, nb, desloc in ((op, 4, 0), (d, 4, 4), (a, 4, 8), (bb, 4, 12)):
                for t in range(nb):
                    b[i * LARGURA_B + desloc + t] = (valor >> (nb - 1 - t)) & 1
        return b

    def ativos(self, bits):
        prog = self.decodificar(bits)
        m = np.zeros(self.n_bits, bool)
        for i, (op, _d, _a, _b) in enumerate(prog):
            base = i * LARGURA_B
            m[base:base + 4] = True
            ud, ua, ub = self._usa(int(op))
            m[base + 4:base + 8] = ud
            m[base + 8:base + 12] = ua
            m[base + 12:base + 16] = ub
        return m


# ------------------------------------------------------------------ a regra de promoção 1.1 (03/10/2026: apontada na revisão de planejamento e adotada): a peça tem de parar sozinha, e custa o tempo real
def executar_contando(prog, entradas, teto=TETO):
    """Como `executar`, devolvendo também quantos passos cada entrada gastou e se ela parou SOZINHA (o programa passou da última instrução antes do teto). Um programa que só acerta porque
    V o interrompe no teto não para sozinho."""
    prog = np.asarray(prog, np.int64)
    ent = np.asarray(entradas, np.uint8)
    L, k = ent.shape
    m = np.zeros((L, R), np.uint8)
    m[:, :k] = ent
    pc = np.zeros(L, np.int64)
    passos = np.zeros(L, np.int64)
    n = len(prog)
    for _ in range(int(teto)):
        vivos = pc < n
        if not vivos.any():
            break
        passos[vivos] += 1
        for i in np.unique(pc[vivos]):
            faixa = np.flatnonzero(pc == i)
            op, d, a, b = (int(x) for x in prog[i])
            if op == 7:
                zero = m[faixa, a] == 0
                pc[faixa[zero]] = d
                pc[faixa[~zero]] = i + 1
                continue
            if op == 1:
                m[faixa, d] = m[faixa, a]
            elif op == 2:
                m[faixa, d] = 1 - m[faixa, a]
            elif op == 3:
                m[faixa, d] = m[faixa, a] & m[faixa, b]
            elif op == 4:
                m[faixa, d] = m[faixa, a] | m[faixa, b]
            elif op == 5:
                m[faixa, d] = m[faixa, a] ^ m[faixa, b]
            elif op == 6:
                m[faixa, d] = 1 - (m[faixa, a] & m[faixa, b])
            pc[faixa] = i + 1
    return m, passos, pc >= n


def promover_11(prog, degrau, origem, teto=TETO):
    """A regra de promoção 1.1: como `promover`, e o programa tem de PARAR SOZINHO em todas as entradas antes do teto (uma peça que só acerta porque o juiz a interrompe é um truque com o
    juiz, o Goodhart do leito). O contrato da peça registra o teto com que ela foi conferida e o máximo de passos que ela gasta, que é o custo da chamada no degrau de cima."""
    x, y = tabela(degrau)
    m, passos, parou = executar_contando(prog, x, teto)
    s = saida(m, y.shape[1])
    if not (s == y).all():
        raise ValueError("o programa não cumpre o degrau: não se promove")
    if not parou.all():
        raise ValueError("o programa não para sozinho em todas as entradas: não se promove (regra 1.1)")
    if x.shape[1] > 2:
        raise ValueError("uma instrução lê até 2 entradas (os operandos a e b)")
    return {"nome": degrau, "entrada": int(x.shape[1]), "saida": int(y.shape[1]), "tabela": s.astype(int).tolist(), "programa": np.asarray(prog, int).tolist(), "origem": origem,
            "regra": "1.1", "teto_conferido": int(teto), "para_sozinho": True, "passos_maximos": int(passos.max())}


def executar_com_biblioteca_11(prog, entradas, biblioteca, teto=TETO):
    """Como `executar_com_biblioteca`, com o custo real (regra 1.1): a chamada da peça k gasta os `passos_maximos` dela, contados no teto de cada entrada; a entrada que estoura o teto para
    ali, com a memória como estava."""
    prog = np.asarray(prog, np.int64)
    ent = np.asarray(entradas, np.uint8)
    L, k = ent.shape
    m = np.zeros((L, R), np.uint8)
    m[:, :k] = ent
    pc = np.zeros(L, np.int64)
    gasto = np.zeros(L, np.int64)
    n = len(prog)
    tabelas = [np.asarray(b["tabela"], np.uint8) for b in biblioteca]
    while True:
        vivos = (pc < n) & (gasto < int(teto))
        if not vivos.any():
            break
        for i in np.unique(pc[vivos]):
            faixa = np.flatnonzero((pc == i) & vivos)
            op, d, a, b = (int(x) for x in prog[i])
            if op >= 8:
                kb = op - 8
                if kb < len(biblioteca):
                    peca = biblioteca[kb]
                    custo = int(peca.get("passos_maximos", 1))
                    cabe = faixa[gasto[faixa] + custo <= int(teto)]
                    estoura = faixa[gasto[faixa] + custo > int(teto)]
                    idx = m[cabe, a].astype(np.int64) + (2 * m[cabe, b].astype(np.int64) if peca["entrada"] == 2 else 0)
                    linha = tabelas[kb][idx]
                    for j in range(peca["saida"]):
                        m[cabe, (d - j) % R] = linha[:, j]
                    gasto[cabe] += custo
                    pc[cabe] += 1
                    gasto[estoura] = int(teto)
                else:
                    gasto[faixa] += 1
                    pc[faixa] += 1
                continue
            gasto[faixa] += 1
            if op == 7:
                zero = m[faixa, a] == 0
                pc[faixa[zero]] = d
                pc[faixa[~zero]] = i + 1
                continue
            if op == 1:
                m[faixa, d] = m[faixa, a]
            elif op == 2:
                m[faixa, d] = 1 - m[faixa, a]
            elif op == 3:
                m[faixa, d] = m[faixa, a] & m[faixa, b]
            elif op == 4:
                m[faixa, d] = m[faixa, a] | m[faixa, b]
            elif op == 5:
                m[faixa, d] = m[faixa, a] ^ m[faixa, b]
            elif op == 6:
                m[faixa, d] = 1 - (m[faixa, a] & m[faixa, b])
            pc[faixa] = i + 1
    return m
