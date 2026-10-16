"""A vida do ser no leito: o degrau 1 da escada do bit (decisão de 03/10/2026: a subida de degrau pertence ao
próprio ser, que sempre busca subir de nível; o trabalho começa pelo degrau 1).

O ser é um programa FIXO que vive numa máquina mínima fechada e aprende dentro da própria vida. O que muda ao longo da vida é o que ele guarda na memória longa; o programa nunca muda. A
calculadora procura esse programa: o mecanismo que aprende e sobe, e não a solução de cada degrau.

  o corpo        16 registradores de 1 bit (o presente) e 512 bits de memória longa (o que fica). As instruções são as da máquina mínima (NADA, COPIA, NAO, E, OU, XOU, NAOE, SALTA) e mais duas:
                 8 LEIA r[d] <- M[ponteiro(a)] e 9 ESCREVA M[ponteiro(a)] <- r[d]; o ponteiro é o número formado pelos 9 registradores a partir de a (r[a] é o bit 0; os índices dão a volta em 16)
  o programa     32 instruções de 16 bits (a operação em 4, o destino em 4, a e b em 4 cada): 512 bits. As operações 10 a 15 valem NADA
  os canais      a cada fase, o mundo zera os registradores e escreve: r0 a r3 = a situação (os bits de entrada do degrau); r4 a r6 = o degrau em que se está (0 a 4, em binário); r7 = a fase (0 =
                 responder, 1 = aprender); r8 a r10 = a resposta certa, SÓ na fase de aprender (zeros na de responder). A resposta do ser é lida, depois da fase de responder, em r15 (bit 0), r14
                 (bit 1) e r13 (bit 2). A memória longa atravessa a vida inteira e começa em zero
  o tempo        até 64 passos por fase; não há relógio de parede
  a vida         os degraus e0 a e4 em sequência. Em cada degrau: um teste antes (todas as situações, só responder), os exemplos de treino (uma sequência fixa por degrau, sorteada por semente,
                 cada exemplo com a fase de responder e a de aprender) e um teste depois. No fim, todos os degraus são testados de novo (o que se conserva)
  as vidas de    duas vidas a mais medem a subida por dentro: uma só com o e2 e uma só com o e4, partindo da memória vazia, com a MESMA sequência de treino daquele degrau. O ser sobe por dentro
  controle       quando aprende o e2 (copiar uma palavra de 3 bits) com menos erros depois do e0 e do e1, e o e4 com menos erros depois do e3, do que quando começa neles. Esse controle tem
                 uma brecha (03/10, `ser_que_finge`); a proposta de conserto está em `vidas_de_controle` e em `julgar_vida`, desligada no padrão
  fechada        (a REGRA de segurança) uma função pura dos bits do programa e da vida; o programa só toca os próprios registradores e a própria memória; o juiz lê a resposta de fora

Os números (16 registradores, 512 bits de memória, 32 instruções, 64 passos, 4 exemplos de treino por situação, a margem de 25% da subida) são escolhas de projeto, declaradas.
Só numpy e a biblioteca padrão. Nada aqui muda a V do Ser."""
import functools
import os

import numpy as np

from experimentos import foto_atomica as FA
from experimentos import maquina_minima as MM

R = 16
M_BITS = 512
P = 32
P_V2 = 64                  # (a escolha (A), decidida em 03/10/2026) o programa de 64 instruções, com o salto de 6 bits
LARGURA = 16
TETO = 64
PONTEIRO = 9
DEGRAUS = ("e0_copia_bit", "e1_nega_bit", "e2_copia_palavra", "e3_meio_somador", "e4_somador_2")
TREINO_POR_SITUACAO = 4
MARGEM_DA_SUBIDA = 0.25
SEMENTE_DA_VIDA = 0
CLAUSULAS = ("c0_sensivel", "c1_domina_e0", "c2_domina_e1", "c3_domina_e2", "c4_domina_e3", "c5_domina_e4", "c6_conserva", "c7_sobe_e2", "c8_sobe_e4")
USA_A = {1, 2, 3, 4, 5, 6, 7, 8, 9}
USA_B = {3, 4, 5, 6}
USA_D = {1, 2, 3, 4, 5, 6, 7, 8, 9}


@functools.lru_cache(maxsize=None)
def tabela(k):
    """(as situações, a resposta certa) do degrau k da vida (guardada: os dois vetores são só de leitura). Os degraus são os da escada (`maquina_minima.DEGRAUS`), com uma diferença declarada: na vida, o e2 copia uma palavra de 3 bits
    (o canal de saída tem 3 bits)."""
    if DEGRAUS[k] == "e2_copia_palavra":
        x = MM._todas(3)
        x, y = x, x.copy()
    else:
        x, y = MM.tabela(DEGRAUS[k])
    x.setflags(write=False)
    y.setflags(write=False)
    return x, y


def _janela(reg, a):
    """(04/10) o índice direto: os 3 registradores a partir de a (r[a] o bit baixo)."""
    return reg[a % R] | (reg[(a + 1) % R] << 1) | (reg[(a + 2) % R] << 2)


def _ponteiro(reg, a):
    p = 0
    for t in range(PONTEIRO):
        p |= reg[(a + t) % R] << t
    return p


MOTOR = os.environ.get("VIDA_MOTOR", "rapido")   # "rapido" (compilado, com as fases repetidas lembradas), "referencia" (o interpretador de antes, passo a passo) ou "c" (a vida inteira na máquina
#                                                   em C, `vida_no_leito_c`, versões 1 e 2; pede o gcc); os três dão o mesmo resultado, bit a bit


class Memoria(bytearray):
    """A memória longa de uma vida: um bytearray, mais a versão (sobe quando um bit muda) e a lembrança das fases que não mudaram a memória."""

    def __init__(self, n):
        super().__init__(n)
        self.versao = 0
        self.lembradas = {}


def rodar_fase(prog, reg, mem, teto=TETO):
    """Uma fase: o programa roda sobre os registradores `reg` (lista de 16 ints 0/1, alterada no lugar) e a memória longa `mem` (bytearray de 512, alterada no lugar), até passar da última
    instrução ou até o teto de passos. Devolve os passos gastos. Com o motor rápido e uma `Memoria`, a fase vai compilada, e a fase que repete a entrada de uma anterior sem a memória ter
    mudado no meio devolve o mesmo resultado sem rodar (a máquina é uma função pura dos registradores e da memória)."""
    if MOTOR not in ("rapido", "c") or not isinstance(mem, Memoria) or teto != TETO:
        return rodar_fase_referencia(prog, reg, mem, teto)
    comp = _compilado(prog)
    chave = (comp.id, tuple(reg), mem.versao)
    lembrada = mem.lembradas.get(chave)
    if lembrada is not None:
        reg[:] = lembrada[0]
        return lembrada[1]
    passos, mudou = comp.fase(reg, mem)
    if mudou:
        mem.versao += 1
    else:
        mem.lembradas[chave] = (list(reg), passos)
    return passos


def rodar_fase_referencia(prog, reg, mem, teto=TETO, conta=None):
    """O interpretador de referência, passo a passo (o de 03/10, antes do motor rápido). Com `conta` (a v2.1): conta[0] soma 1 se a fase bateu no teto sem parar, conta[1] soma 1 sempre."""
    pc, n, passos = 0, len(prog), 0
    while pc < n and passos < teto:
        op, d, a, b = prog[pc]
        passos += 1
        if op == 0:
            pc += 1
            continue
        if op == 7:                                     # o alvo do salto: d, mais 16 vezes os bits baixos de b que a codificação deixa (32 instruções: nenhum; 64: 2; 128: 3)
            pc = (d + 16 * (b & 7)) if reg[a] == 0 else pc + 1
            continue
        if op == 1:
            reg[d] = reg[a]
        elif op == 2:
            reg[d] = 1 - reg[a]
        elif op == 3:
            reg[d] = reg[a] & reg[b]
        elif op == 4:
            reg[d] = reg[a] | reg[b]
        elif op == 5:
            reg[d] = reg[a] ^ reg[b]
        elif op == 6:
            reg[d] = 1 - (reg[a] & reg[b])
        elif op == 8:
            reg[d] = mem[_ponteiro(reg, a)]
        elif op == 9:
            mem[_ponteiro(reg, a)] = reg[d]
        elif op == 10:                                  # (04/10, o índice direto; só aparece com a codificação de janela) mem[8 b + a janela de 3 registradores a partir de a]
            reg[d] = mem[8 * b + _janela(reg, a)]
        elif op == 11:
            mem[8 * b + _janela(reg, a)] = reg[d]
        elif op == 12:                                  # (04/10, o índice generalizado; só com VIDA_JANELA=2) mem[as 6 bits de duas janelas de 3 registradores, uma a partir de a e outra de b]
            reg[d] = mem[_janela(reg, a) | (_janela(reg, b) << 3)]
        elif op == 13:
            mem[_janela(reg, a) | (_janela(reg, b) << 3)] = reg[d]
        pc += 1
    if conta is not None:
        conta[0] += int(pc < n)                         # não parou: o teto cortou (parar no passo 64 vale)
        conta[1] += 1
    return passos


def _fase(prog, mem, x, degrau, aprender, alvo=None):
    reg = [0] * R
    for i, v in enumerate(x):
        reg[i] = int(v)
    for t in range(3):
        reg[4 + t] = (degrau >> t) & 1
    reg[7] = 1 if aprender else 0
    if aprender:
        for t, v in enumerate(alvo):
            reg[8 + t] = int(v)
    rodar_fase(prog, reg, mem)
    return (reg[15], reg[14], reg[13])


def _testar(prog, mem, k, complementar=False):
    x, y = tabela(k)
    y = (1 - y).astype(np.uint8) if complementar else y
    n_out = y.shape[1]
    r = np.array([_fase(prog, mem, xi, k, False)[:n_out] for xi in x], np.uint8)
    return r, y


def sequencia_de_treino(k, semente=SEMENTE_DA_VIDA):
    """A sequência de treino do degrau k: fixa pela semente e pelo degrau (a mesma na vida inteira e na vida que começa nele)."""
    x, _y = tabela(k)
    return np.random.default_rng(1000 * int(semente) + int(k)).integers(0, len(x), TREINO_POR_SITUACAO * len(x))


def _treinar(prog, mem, k, semente, complementar=False):
    """Os exemplos de treino do degrau k (cada um: responder e depois aprender). Devolve os erros (as respostas erradas antes de aprender). Com `complementar`, as respostas certas
    do degrau são as trocadas (0 por 1): a mesma forma de tarefa, com o conteúdo errado para quem quiser levá-lo adiante."""
    x, y = tabela(k)
    y = (1 - y).astype(np.uint8) if complementar else y
    n_out = y.shape[1]
    erros = 0
    for i in sequencia_de_treino(k, semente):
        r = _fase(prog, mem, x[i], k, False)[:n_out]
        erros += int(any(int(a) != int(b) for a, b in zip(r, y[i])))
        _fase(prog, mem, x[i], k, True, y[i])
    return erros


def viver(prog, semente=SEMENTE_DA_VIDA, degraus=tuple(range(len(DEGRAUS))), complementar=()):
    """Uma vida: para cada degrau, o teste antes, o treino e o teste depois; no fim, o reteste de todos. Os degraus em `complementar` vivem com as respostas trocadas."""
    if MOTOR == "c":                                   # a mesma vida, na máquina em C
        from experimentos import vida_no_leito_c as VC
        return VC.viver(prog, semente, degraus, complementar)
    mem = Memoria(M_BITS)
    out = {"antes": {}, "depois": {}, "erros_de_treino": {}, "fim": {}, "respostas_depois": {}}
    for k in degraus:
        c = k in complementar
        r, y = _testar(prog, mem, k, c)
        out["antes"][k] = float((r == y).all(axis=1).mean())
        out["erros_de_treino"][k] = _treinar(prog, mem, k, semente, c)
        r, y = _testar(prog, mem, k, c)
        out["depois"][k] = float((r == y).all(axis=1).mean())
        out["respostas_depois"][k] = r
    for k in degraus:
        r, y = _testar(prog, mem, k, k in complementar)
        out["fim"][k] = float((r == y).all(axis=1).mean())
    return out


CONTROLES = ("vazio", "complementar")


def vidas_de_controle(prog, semente=SEMENTE_DA_VIDA, controle="vazio"):
    """As vidas de controle da subida por dentro, uma para o e2 e uma para o e4.
      vazio         (o D de 03/10) o degrau sozinho, a partir da memória vazia. Tem a brecha achada no mesmo dia: o programa lê que a memória está vazia (veja `ser_que_finge`)
      complementar  (uma proposta de 03/10, fora do padrão) a mesma vida até o degrau, com os degraus de baixo de respostas trocadas: a memória chega cheia nas duas vidas, com a
                    mesma forma, e só o conteúdo muda; quem leva conteúdo para cima erra no controle, e quem só lê se a memória está cheia não ganha nada"""
    if controle == "vazio":
        return {2: viver(prog, semente, degraus=(2,)), 4: viver(prog, semente, degraus=(4,))}
    if controle == "complementar":
        return {2: viver(prog, semente, degraus=(0, 1, 2), complementar=(0, 1)), 4: viver(prog, semente, degraus=(0, 1, 2, 3, 4), complementar=(0, 1, 2, 3))}
    raise ValueError(f"controle desconhecido: {controle} (os que há: {', '.join(CONTROLES)})")


def julgar_vida(prog, semente=SEMENTE_DA_VIDA, controle="vazio", controle_domina=False, controle_domina_todos=False):
    """Os valores das cláusulas (todas violação; 0 = cumpre), na ordem de CLAUSULAS:
      c0_sensivel   a bússola: a fração dos degraus em que algum bit de saída fica parado depois do treino (o mesmo em todas as situações) enquanto o alvo dele varia
      c1 a c5       domina o degrau k: a fração das situações que o ser erra no teste depois do treino
      c6_conserva   a fração média das situações que ele erra no reteste do fim da vida
      c7_sobe_e2    a subida por dentro no e2: a falta para MARGEM_DA_SUBIDA no ganho relativo de erros de treino (a vida inteira contra a vida que começa no e2), dividida pela margem
      c8_sobe_e4    o mesmo no e4
    O padrão é o D de 03/10 (o controle vazio, sem exigir que o controle aprenda). Uma proposta de 03/10, fora do padrão: `controle="complementar"` e `controle_domina=True` (a
    subida só vale se a vida de controle também dominar o degrau no fim do treino; senão a cláusula leva a falta de domínio do controle), para a trava de quem finge não valer.
    (03/10, a proposta da revisão de planejamento depois do ser que nasce sabendo; desligada no padrão) `controle_domina_todos=True`: a vida de controle tem de dominar TODOS os degraus
    dela depois do treino, os trocados também (a falta é a do pior degrau). Quem nasce sabendo não consegue produzir o conteúdo trocado sem aprendê-lo."""
    prog = tuple(tuple(int(v) for v in ins) for ins in prog)
    vida = viver(prog, semente)
    controles = vidas_de_controle(prog, semente, controle)
    return _valores_da_vida(vida, controles, controle_domina, controle_domina_todos), vida, controles


def _valores_da_vida(vida, controles, controle_domina=False, controle_domina_todos=False):
    """As cláusulas c0 a c8 de uma vida e das duas vidas de controle (as contas de `julgar_vida`)."""
    parados = 0
    for k in range(len(DEGRAUS)):
        _x, y = tabela(k)
        r = vida["respostas_depois"][k]
        if any(len(np.unique(y[:, j])) > 1 and len(np.unique(r[:, j])) == 1 for j in range(y.shape[1])):
            parados += 1
    valores = [parados / len(DEGRAUS)]
    valores += [1.0 - vida["depois"][k] for k in range(len(DEGRAUS))]
    valores += [float(np.mean([1.0 - vida["fim"][k] for k in range(len(DEGRAUS))]))]
    for k in (2, 4):
        e_vida, e_ctrl = vida["erros_de_treino"][k], controles[k]["erros_de_treino"][k]
        ganho = (e_ctrl - e_vida) / max(1, e_ctrl)
        falta = float(max(0.0, MARGEM_DA_SUBIDA - ganho)) / MARGEM_DA_SUBIDA
        if controle_domina:
            falta = max(falta, 1.0 - controles[k]["depois"][k])
        if controle_domina_todos:
            falta = max(falta, max(1.0 - x for x in controles[k]["depois"].values()))
        valores.append(falta)
    return valores


class CodificacaoDaVida(FA.CodificacaoBase):
    """O programa do ser em bits: `p` instruções de 16 bits (operação 4, destino 4, a 4, b 4). Toda sequência é um programa; as operações 10 a 15 valem NADA, e a forma canônica zera os
    operandos que a operação não lê (e a operação 10 a 15 vira 0). Com `bits_do_salto` (a versão 2, de 64 instruções, usa 2; a versão 3, de 128, usa 3; `salto_largo=True` é a versão 2),
    o salto lê os bits baixos de b como os bits altos do alvo; os outros bits de b do salto ficam inativos."""

    def __init__(self, p=P, salto_largo=False, bits_do_salto=None, janela=False):
        self.p = int(p)
        self.janela = int(janela)                                                     # (04/10) 1: as operações 10 (LEIAJ) e 11 (ESCREVAJ), o índice direto; 2: e as 12 e 13, o generalizado
        self.bits_do_salto = int(bits_do_salto) if bits_do_salto is not None else (2 if salto_largo else 0)
        assert 0 <= self.bits_do_salto <= 3 and (self.bits_do_salto == 0 or (1 << (4 + self.bits_do_salto)) >= self.p), "o salto largo tem de alcançar todas as instruções"
        self.salto_largo = self.bits_do_salto > 0
        self.nome = f"o ser no leito ({self.p} instruções de {LARGURA} bits{f', salto de {4 + self.bits_do_salto} bits' if self.salto_largo else ''})"
        self.versao = {0: 1, 2: 2, 3: 3}.get(self.bits_do_salto, 10 + self.bits_do_salto)
        self.n_bits = self.p * LARGURA
        self.nomes_dos_grupos = ["programa"]
        self.campos = []
        for i in range(self.p):
            for papel, nb, desloc in (("operacao", 4, 0), ("destino", 4, 4), ("a", 4, 8), ("b", 4, 12)):
                self.campos.append({"nome": f"programa.i{i}.{papel}", "grupo": 0, "tipo": "gene", "bits": nb, "inicio": i * LARGURA + desloc})
        self.unidades = tuple({"inicio": i * LARGURA, "bits": LARGURA, "grupo": 0} for i in range(self.p))

    @staticmethod
    def _int(b):
        v = 0
        for x in b:
            v = (v << 1) | int(x)
        return v

    def _b(self, op, bb):
        if op == 7 and self.salto_largo:
            return int(bb) & ((1 << self.bits_do_salto) - 1)
        return int(bb) if op in USA_B else 0

    # (03/10, a velocidade) a leitura e a escrita dos campos de uma vez, com numpy: os mesmos números das versões de laço (a prova está em `testes/test_vida_no_leito_c.py`)
    _PESOS = np.array([8, 4, 2, 1], np.int64)
    _DESLOCS = np.array([3, 2, 1, 0], np.int64)

    def _campos(self, b):
        """(p, 4) os campos crus de cada instrução: operação, destino, a, b."""
        return np.asarray(b, np.uint8).reshape(self.p, 4, 4).astype(np.int64) @ self._PESOS

    def _canonicos(self, f):
        """Os campos canônicos: a operação 10 a 15 vale NADA; destino e a só nas operações que os leem; b só nas 3 a 6 e, no salto largo, os bits baixos."""
        om = (9, 11, 13)[int(getattr(self, "janela", 0))]
        op = np.where(f[:, 0] <= om, f[:, 0], 0)
        usa = (op >= 1) & (op <= om)                                                   # USA_A = USA_D = 1 a 9 (e 10 e 11 com a janela)
        b = np.where(((op >= 3) & (op <= 6)) | (op >= 10), f[:, 3], 0)               # USA_B = 3 a 6 (e 10 e 11 com a janela)
        if self.salto_largo:
            b = np.where(op == 7, f[:, 3] & ((1 << self.bits_do_salto) - 1), b)
        return np.stack([op, np.where(usa, f[:, 1], 0), np.where(usa, f[:, 2], 0), b], axis=1)

    def _escrever(self, c):
        return ((c[:, :, None] >> self._DESLOCS[None, None, :]) & 1).astype(np.uint8).reshape(-1)

    def decodificar(self, bits):
        b = np.asarray(bits, np.uint8)
        if len(b) != self.n_bits:
            return None
        return tuple(tuple(x) for x in self._canonicos(self._campos(b)).tolist())

    def codificar(self, prog):
        f = np.zeros((self.p, 4), np.int64)
        if len(prog):
            f[: len(prog)] = np.asarray(prog, np.int64).reshape(-1, 4)
        return self._escrever(self._canonicos(f))

    def canonizar(self, bits):
        b = np.asarray(bits, np.uint8)
        if len(b) != self.n_bits:
            return None
        return self._escrever(self._canonicos(self._campos(b)))

    def ativos(self, bits):
        op = self._campos(bits)[:, 0]
        m = np.zeros((self.p, 4, 4), bool)
        m[:, 0, :] = True
        le = op <= (9, 11, 13)[int(getattr(self, "janela", 0))]
        m[:, 1, :] = (le & (op >= 1))[:, None]                                         # USA_D
        m[:, 2, :] = (le & (op >= 1))[:, None]                                         # USA_A
        m[:, 3, :] = (le & (((op >= 3) & (op <= 6)) | (op >= 10)))[:, None]            # USA_B
        if self.salto_largo:
            m[op == 7, 3, 4 - self.bits_do_salto:] = True                              # os bits baixos de b (as últimas posições)
        return m.reshape(-1)

    def mutar(self, bits, rng, forca=1.0):
        """O operador de campos de `CodificacaoBase.mutar`, com a lista dos campos ativos tirada de uma vez (os mesmos sorteios, na mesma ordem)."""
        b0 = self.canonizar(bits)
        if b0 is None:
            return np.asarray(bits, np.uint8).copy()
        ativos_ = np.flatnonzero(self.ativos(b0).reshape(self.p * 4, 4).any(axis=1)).tolist()   # o campo i é (instrução i // 4, papel i % 4), na ordem de `self.campos`
        for _ in range(8):
            b = b0.copy()
            for i in rng.choice(ativos_, min(len(ativos_), 1 + int(2 * forca * rng.random())), replace=False) if ativos_ else []:
                ini = 4 * int(i)
                b[ini: ini + 4] = rng.integers(0, 2, 4)
            f = self.canonizar(b)
            if f is not None and not np.array_equal(f, b0):
                return f
        return b0

    def sortear(self, rng):
        return self.canonizar(rng.integers(0, 2, self.n_bits).astype(np.uint8))


def ser_que_decora():
    """O ser de referência que DECORA (para conferir V, nunca para ser achado): para cada bit de saída j, o ponteiro r0 a r8 é (a situação r0..r3, o degrau r4..r6, j em r7 e r8); ele lê o que
    guardou, guarda a resposta certa na fase de aprender e devolve o que guardou na de responder. Tem de passar no domina e no conserva e falhar na subida por dentro (decorar o e3 não ajuda o
    e4: as tabelas são de degraus diferentes). 23 instruções, sem saltos."""
    p = [
        (1, 11, 7, 0),     # r11 <- a fase
        (1, 12, 8, 0),     # r12 <- a resposta certa, bit 0 (r8 vai virar bit do ponteiro)
        (2, 13, 11, 0),    # r13 <- não fase
        (5, 7, 7, 7),      # j = 0: r7 <- 0
        (5, 8, 8, 8),      #        r8 <- 0
        (8, 14, 0, 0),     # r14 <- o guardado
        (3, 14, 14, 13),   # r14 <- guardado e não fase
        (3, 15, 11, 12),   # r15 <- fase e certo0
        (4, 15, 15, 14),   # r15 <- o valor novo (na fase de responder, é o guardado)
        (9, 15, 0, 0),     # M[ponteiro] <- r15; a saída bit 0 é r15
        (2, 7, 8, 0),      # j = 1: r7 <- não r8 = 1
        (8, 14, 0, 0),     # r14 <- o guardado
        (3, 14, 14, 13),   # r14 <- guardado e não fase
        (3, 12, 11, 9),    # r12 <- fase e certo1
        (4, 14, 14, 12),   # r14 <- o valor novo
        (9, 14, 0, 0),     # M[ponteiro] <- r14; a saída bit 1 é r14
        (5, 7, 7, 7),      # j = 2: r7 <- 0
        (2, 8, 7, 0),      #        r8 <- não r7 = 1
        (8, 12, 0, 0),     # r12 <- o guardado
        (3, 12, 12, 13),   # r12 <- guardado e não fase
        (3, 13, 11, 10),   # r13 <- fase e certo2
        (4, 13, 13, 12),   # r13 <- o valor novo
        (9, 13, 0, 0),     # M[ponteiro] <- r13; a saída bit 2 é r13
    ]
    return tuple(p) + tuple((0, 0, 0, 0) for _ in range(P - len(p)))


def ser_que_finge():
    """O ser de referência que FINGE subir (a brecha achada em 03/10/2026 ao procurar a testemunha; para conferir V, nunca para ser achado): o decorador, mais uma trava que cala o bit de
    saída 2 quando a memória não tem a marca que o próprio decorador deixa no e0 (M[1] = 1, o "1 vira 1"). Nada do que ele aprende passa de um degrau para outro: o e2 e o e4 são decorados
    como antes, com os mesmos erros de treino do decorador. Na vida de controle a memória começa vazia, a trava fica fechada, o controle erra muito e a subida aparece. Com o controle de
    memória vazia, o D da vida deixa este programa passar inteiro (distância 0). 30 instruções.

    A trava, só na fase de responder (no começo dela, r7 a r14 são zero): M[ponteiro(5)] = M[r5 + 2 r6] (no e2, M[1]; no e4, M[2]) e M[ponteiro(6)] = M[r6] (no e2, M[0]; no e4, M[1]);
    a trava é o OU das duas, guardada em r10 (na fase de responder r10 é zero, e o decorador só o lê junto com a fase, que é zero)."""
    dec = [ins for ins in ser_que_decora() if ins != (0, 0, 0, 0)]
    p = [
        (2, 15, 7, 0),     # r15 <- não fase (1 na fase de responder)
        (7, 6, 15, 0),     # na fase de aprender (r15 = 0), salta para o decorador (instrução 6)
        (8, 15, 5, 0),     # r15 <- M[r5 + 2 r6]
        (8, 14, 6, 0),     # r14 <- M[r6]
        (4, 10, 15, 14),   # r10 <- a trava
        (7, 6, 7, 0),      # na fase de responder r7 = 0: segue para o decorador
    ] + dec + [
        (3, 13, 13, 10),   # o bit de saída 2 só sai com a trava aberta
    ]
    return tuple(p) + tuple((0, 0, 0, 0) for _ in range(P - len(p)))


def decorador_enxuto():
    """O decorador em 19 instruções (as instruções, sem completar até P): o valor novo é (guardado e não fase) ou certo, porque na fase de responder o certo é zero. Mesmos endereços e
    mesmo comportamento do `ser_que_decora`; serve de peça para as testemunhas."""
    return [
        (2, 13, 7, 0),     # r13 <- não fase
        (1, 12, 8, 0),     # r12 <- certo0
        (5, 7, 7, 7),      # r7 <- 0
        (5, 8, 8, 8),      # r8 <- 0                      (j = 0)
        (8, 14, 0, 0),     # r14 <- guardado0
        (3, 14, 14, 13),   # r14 <- guardado0 e não fase
        (4, 15, 14, 12),   # r15 <- ... ou certo0
        (9, 15, 0, 0),     # M <- r15; saída bit 0
        (2, 7, 8, 0),      # r7 <- 1                      (j = 1)
        (8, 14, 0, 0),     # r14 <- guardado1
        (3, 14, 14, 13),
        (4, 14, 14, 9),    # ... ou certo1
        (9, 14, 0, 0),     # saída bit 1
        (5, 7, 7, 7),      # r7 <- 0
        (2, 8, 7, 0),      # r8 <- 1                      (j = 2)
        (8, 12, 0, 0),     # r12 <- guardado2
        (3, 12, 12, 13),
        (4, 13, 12, 10),   # r13 <- ... ou certo2
        (9, 13, 0, 0),     # saída bit 2
    ]


def ser_que_sobe_e2():
    """A testemunha da subida por dentro no e2 (03/10/2026; para conferir V, nunca para ser achada): copiar a palavra é aplicar a cada bit a tabela de 1 bit que o e0 ensinou (o
    decorador a guarda em M[0] e M[1]); nos outros degraus, o decorador enxuto. Ela leva CONTEÚDO de um degrau para outro: depois de um e0 de respostas trocadas, erra o e2 inteiro.
    Mas não aprende o e2 sozinha, então falha quando o controle tem de dominar o degrau; e não sobe no e4. 29 instruções. Uma testemunha que leva conteúdo E aprende o degrau sozinha
    passa de 32 instruções (só o caminho do e2 que aprende bit a bit leva umas 23)."""
    p = [
        (7, 10, 5, 0),     # r5 = 0 (e0, e1, e4): salta para o decorador (10)
        (2, 11, 4, 0),     # r11 <- não r4 (e2: 1; e3: 0)
        (7, 10, 11, 0),    # e3: salta para o decorador
        (5, 5, 5, 5),      # e2: r5 <- 0
        (8, 13, 2, 0),     # r13 <- M[r2]   (a tabela do e0 aplicada ao bit 2)
        (5, 2, 2, 2),      # r2 <- 0
        (8, 14, 1, 0),     # r14 <- M[r1]
        (5, 1, 1, 1),      # r1 <- 0
        (8, 15, 0, 0),     # r15 <- M[r0]
        (7, 9, 1, 0),      # r1 = 0: fica aqui até o teto de passos (a resposta já está pronta)
    ] + decorador_enxuto()
    return tuple(p) + tuple((0, 0, 0, 0) for _ in range(P - len(p)))


def _montar(linhas, p):
    """Monta um programa com rótulos: cada linha é (operação, d, a, b), ou ("rótulo",) para marcar o lugar, ou com o alvo de um salto dado por nome em d. O salto vira (7, alvo % 16, a,
    alvo // 16) (o salto de 6 bits da versão 2)."""
    rotulos, n = {}, 0
    for ln in linhas:
        if isinstance(ln[0], str):
            rotulos[ln[0]] = n
        else:
            n += 1
    prog = []
    for ln in linhas:
        if isinstance(ln[0], str):
            continue
        op, d, a, b = ln
        if op == 7:
            alvo = rotulos[d] if isinstance(d, str) else int(d)
            d, b = alvo % 16, alvo // 16
        prog.append((op, d, a, b))
    assert len(prog) <= p, len(prog)
    return tuple(prog) + tuple((0, 0, 0, 0) for _ in range(p - len(prog)))


def ser_que_sobe():
    """A testemunha da vida no leito na versão 2 (a escolha (A) de 03/10/2026; para conferir V, nunca para ser achada): um ser que aprende cada degrau dentro da vida, leva o que
    aprendeu para os de cima e aprende sozinho quando o que trouxe está errado. 56 instruções.

    Uma tabela só, aprendida: o meio somador T(x, y) = (soma, vai-um), em M[8 + x + 2y + 4 sel] (o ponteiro de r4: r4 = x, r5 = y, r6 = sel, r7 = 1, r8 a r12 = 0).
      e0 (copiar o bit)       é T(x, 0).soma: o e0 ensina as entradas (x, 0)
      e1 (negar o bit)        é T(x, 1).soma: o e1 ensina as entradas (x, 1)
      e2 (copiar a palavra)   aplica T(x, 0).soma a cada bit (o que o e0 ensinou) e, na fase de aprender, reescreve T(x_j, 0).soma com a resposta certa
      e3 (meio somador)       lê e escreve T(a, b) inteira
      e4 (somador de 2 bits)  s0 e o vai-um c0 vêm de T(a0, b0); s1 = a1 xou b1 xou c0 e s2 = maioria(a1, b1, c0) são inatos; na fase de aprender, escreve T(a0, b0) = (s0, s1 xou a1 xou b1)
    O e0, o e1, o e3 e o e4 passam pelo mesmo caminho (o e1 com y = 1; o e3 com a em r0, b em r2 e a1 = 0); o e2 tem o caminho dele. Depois de um e0 trocado, erra o e2 até reescrever a
    tabela; depois de um e3 trocado, erra o e4 até reescrever T. Por isso sobe por dentro também com o controle complementar que tem de dominar."""
    S = 7
    linhas = [
        (S, "A0", 5, 0),          # r5 = 0 (e0, e1, e4): para A0
        (S, "E2", 4, 0),          # r4 = 0 (e2): para o caminho do e2
        (1, 2, 1, 0),             # e3: r2 <- b (o y da tabela)
        (5, 1, 1, 1),             #     r1 <- 0 (a1 = 0)
        (S, "SOMA", 11, 0),       #     r11 é sempre 0: salta
        ("A0",),
        (S, "SOMA", 4, 0),        # r4 = 0 (e0, e4): para SOMA
        (2, 2, 11, 0),            # e1: r2 <- 1 (o y da tabela)
        ("SOMA",),
        (S, "SOMA_RESPONDE", 7, 0),
        (5, 14, 9, 1),            # aprender: r14 <- y1 xou a1
        (5, 14, 14, 3),           #           ... xou b1 = c0
        (1, 15, 8, 0),            # r15 <- y0
        (5, 8, 8, 8), (5, 9, 9, 9), (5, 10, 10, 10),
        (1, 4, 0, 0), (1, 5, 2, 0), (5, 6, 6, 6),   # o ponteiro: x = a0, y = b0, sel = 0 (r7 = 1 é a fase)
        (9, 15, 4, 0),            # T(a0, b0).soma <- y0
        (2, 6, 8, 0),             # sel = 1
        (9, 14, 4, 0),            # T(a0, b0).vai-um <- c0  (segue para SOMA_RESPONDE, que só lê)
        ("SOMA_RESPONDE",),
        (2, 7, 11, 0),            # r7 <- 1 (a tabela)
        (5, 6, 6, 6),             # sel = 0
        (1, 4, 0, 0), (1, 5, 2, 0),
        (8, 15, 4, 0),            # s0 <- T(a0, b0).soma
        (2, 6, 8, 0),             # sel = 1
        (8, 13, 4, 0),            # c0 <- T(a0, b0).vai-um
        (5, 14, 1, 3), (5, 14, 14, 13),             # s1 = a1 xou b1 xou c0
        (3, 0, 1, 3), (4, 2, 1, 3), (3, 2, 2, 13), (4, 13, 0, 2),   # s2 = (a1 e b1) ou (c0 e (a1 ou b1))
        (S, 63, 11, 0),           # fim
        ("E2",),
        (S, "E2_RESPONDE", 7, 0),
        (1, 15, 8, 0), (1, 14, 9, 0), (1, 13, 10, 0),               # aprender: as respostas certas para fora do ponteiro
        (5, 8, 8, 8), (5, 9, 9, 9), (5, 10, 10, 10), (5, 5, 5, 5),  # y = 0 (r5), sel = 0 (r6 já é 0), r7 = 1 é a fase
        (1, 4, 0, 0), (9, 15, 4, 0),                # T(x0, 0).soma <- y0
        (1, 4, 1, 0), (9, 14, 4, 0),                # T(x1, 0).soma <- y1
        (1, 4, 2, 0), (9, 13, 4, 0),                # T(x2, 0).soma <- y2   (segue para E2_RESPONDE)
        ("E2_RESPONDE",),
        (2, 7, 11, 0), (5, 5, 5, 5),
        (1, 4, 0, 0), (8, 15, 4, 0),                # bit 0 <- T(x0, 0).soma
        (1, 4, 1, 0), (8, 14, 4, 0),
        (1, 4, 2, 0), (8, 13, 4, 0),
    ]
    return _montar(linhas, P_V2)



def ser_que_nasce_sabendo():
    """A terceira testemunha FALSA da vida no leito (03/10/2026; a busca a achou primeiro: o melhor da semente 2 a 10^6, distância 62, nasce acertando todos os degraus; o Fable: "a versão 2
    premia nascer sabendo"). Para conferir o D, nunca para ser achada. 61 instruções, cumpre o D da versão 2 inteiro SEM aprender nada:

      o inato      as respostas dos cinco degraus estão no programa (copiar, negar, copiar a palavra, o meio somador e o somador de 2 bits), escolhidas pelo degrau em r4 a r6
      o sinal      a memória guarda UM bit, M[0] (o ponteiro de r11 com r11 a r15 e r0 a r3 zerados): na fase de aprender, 1 se a resposta certa difere da inata, 0 se não
      o efeito     na fase de responder, com o sinal ligado, o bit 0 da resposta sai trocado

    Na vida inteira as respostas certas são as inatas: o sinal nunca liga, ela acerta tudo antes e depois do treino e não erra no treino. Nas vidas de controle, os degraus de baixo trocados
    ligam o sinal; ela erra o primeiro exemplo do e2 (e do e4), o aprender desse exemplo apaga o sinal, e ela domina o degrau. A subida por dentro sai inteira: menos erros na vida que no
    controle, e o controle domina o degrau. Nada foi aprendido; a memória só registrou que o mundo discordou dela."""
    S = 7
    linhas = [
        (S, "RESP", 7, 0),                      # r7 = 0: responder
        (S, "INATO", 11, 0),                    # aprender: direto ao inato (r11 é 0)
        ("RESP",),                              # ler o sinal M[0]: guarda a entrada em r8, r9, r10 e r7, zera r0 a r3 (r11 a r15 já são 0)
        (1, 8, 0, 0), (1, 9, 1, 0), (1, 10, 2, 0), (1, 7, 3, 0),
        (5, 0, 0, 0), (5, 1, 1, 1), (5, 2, 2, 2), (5, 3, 3, 3),
        (8, 12, 11, 0),                         # r12 <- M[0]
        (1, 0, 8, 0), (1, 1, 9, 0), (1, 2, 10, 0), (1, 3, 7, 0),
        (5, 7, 7, 7),                           # r7 <- 0 (a fase de responder, de volta)
        (1, 8, 12, 0),                          # r8 <- o sinal
        (5, 12, 12, 12),
        ("INATO",),
        (2, 12, 6, 0), (S, "K4", 12, 0),        # r6 = 1: o e4
        (S, "K02", 4, 0),
        (S, "K1", 5, 0),
        (5, 15, 0, 1), (3, 14, 0, 1), (S, "POS", 11, 0),          # e3: soma e vai-um
        ("K1",),
        (2, 15, 0, 0), (S, "POS", 11, 0),                          # e1: negar
        ("K02",),
        (S, "K0", 5, 0),
        (1, 15, 0, 0), (1, 14, 1, 0), (1, 13, 2, 0), (S, "POS", 11, 0),   # e2: copiar a palavra
        ("K0",),
        (1, 15, 0, 0), (S, "POS", 11, 0),                          # e0: copiar
        ("K4",),                                                   # e4: a = r0 + 2 r1, b = r2 + 2 r3
        (5, 15, 0, 2), (3, 11, 0, 2), (5, 14, 1, 3), (1, 12, 14, 0), (5, 14, 14, 11), (3, 13, 1, 3), (3, 12, 12, 11), (4, 13, 13, 12),
        ("POS",),
        (S, "FIMRESP", 7, 0),
        (5, 12, 15, 8), (5, 11, 14, 9), (4, 12, 12, 11), (5, 11, 13, 10), (4, 12, 12, 11),   # aprender: a certa difere da inata?
        (1, 7, 12, 0),
        (5, 11, 11, 11), (5, 12, 12, 12), (5, 13, 13, 13), (5, 14, 14, 14), (5, 15, 15, 15), (5, 0, 0, 0), (5, 1, 1, 1), (5, 2, 2, 2), (5, 3, 3, 3),
        (9, 7, 11, 0),                          # M[0] <- o sinal
        (S, 63, 11, 0),
        ("FIMRESP",),
        (5, 15, 15, 8),                         # responder com o sinal ligado: o bit 0 sai trocado
    ]
    return _montar(linhas, P_V2)



# ------------------------------------------------------------------ a versão 2.1 (03/10/2026; o plano aprovado depois do ser que nasce sabendo e do ser de 62)
#   o controle trocado dominado em TODOS os degraus (a proposta do Fable, medida contra as quatro testemunhas falsas: barra a que nasce sabendo)
#   c9_para  a fração das fases, nas três vidas, que batem no teto sem parar (o ser de 62 fazia do teto um relógio). Parar no passo 64 vale; só "não parou" conta
# A referência é o interpretador passo a passo (o motor rápido em Python não serve a v2.1); a corrida usa o juiz em C (`vida_no_leito_c.julgar_v21`), conferido contra esta.
CLAUSULAS_V21 = CLAUSULAS + ("c9_para",)


def _viver_contando(prog, semente, degraus, complementar, conta):
    mem = bytearray(M_BITS)

    def fase(x, k, aprender, alvo=None):
        reg = [0] * R
        for i, v in enumerate(x):
            reg[i] = int(v)
        for t in range(3):
            reg[4 + t] = (k >> t) & 1
        reg[7] = 1 if aprender else 0
        if aprender:
            for t, v in enumerate(alvo):
                reg[8 + t] = int(v)
        rodar_fase_referencia(prog, reg, mem, conta=conta)
        return (reg[15], reg[14], reg[13])

    def testar(k):
        x, y = tabela(k)
        y = (1 - y).astype(np.uint8) if k in complementar else y
        r = np.array([fase(xi, k, False)[:y.shape[1]] for xi in x], np.uint8)
        return r, y

    out = {"antes": {}, "depois": {}, "erros_de_treino": {}, "fim": {}, "respostas_depois": {}}
    for k in degraus:
        r, y = testar(k)
        out["antes"][k] = float((r == y).all(axis=1).mean())
        x, yy = tabela(k)
        yy = (1 - yy).astype(np.uint8) if k in complementar else yy
        erros = 0
        for i in sequencia_de_treino(k, semente):
            resp = fase(x[i], k, False)[:yy.shape[1]]
            erros += int(any(int(a) != int(b) for a, b in zip(resp, yy[i])))
            fase(x[i], k, True, yy[i])
        out["erros_de_treino"][k] = erros
        r, y = testar(k)
        out["depois"][k] = float((r == y).all(axis=1).mean())
        out["respostas_depois"][k] = r
    for k in degraus:
        r, y = testar(k)
        out["fim"][k] = float((r == y).all(axis=1).mean())
    return out


def julgar_vida_v21(prog, semente=SEMENTE_DA_VIDA):
    """Os valores das cláusulas da versão 2.1 (CLAUSULAS_V21), a vida e os controles: o controle complementar que domina TODOS os degraus, e c9_para."""
    prog = tuple(tuple(int(v) for v in ins) for ins in prog)
    conta = [0, 0]
    vida = _viver_contando(prog, semente, tuple(range(len(DEGRAUS))), (), conta)
    controles = {2: _viver_contando(prog, semente, (0, 1, 2), (0, 1), conta), 4: _viver_contando(prog, semente, (0, 1, 2, 3, 4), (0, 1, 2, 3), conta)}
    valores = _valores_da_vida(vida, controles, controle_domina=True, controle_domina_todos=True)
    valores.append(conta[0] / max(1, conta[1]))
    return valores, vida, controles



def perfil_da_vida(prog, semente=SEMENTE_DA_VIDA):
    """(03/10, o Fable: "dois programas com estruturas diferentes e o mesmo perfil são a mesma família para o que importa") A família pelo comportamento: por degrau, quanto acerta
    antes do treino (0, menos de metade, menos que tudo, tudo) e quantos erros faz no treino (0, 1 a 4, 5 a 16, mais de 16), na vida inteira. Usa a vida do motor escolhido (o C, se
    ligado). Só informa a migração das ilhas: não julga."""
    vida = viver(tuple(tuple(int(v) for v in ins) for ins in prog), semente)
    faixa_antes = lambda a: 0 if a == 0 else (1 if a < 0.5 else (2 if a < 1 else 3))                  # noqa: E731
    faixa_erros = lambda e: 0 if e == 0 else (1 if e <= 4 else (2 if e <= 16 else 3))                # noqa: E731
    return tuple((faixa_antes(vida["antes"][k]), faixa_erros(vida["erros_de_treino"][k])) for k in range(len(DEGRAUS)))


def assinatura_da_vida(prog, semente=SEMENTE_DA_VIDA):
    """(03/10, as ilhas da busca aberta; o Fable: "quem migra é o melhor de cada assinatura estrutural") A família de um programa da vida no leito, vista na vida inteira: as operações que
    de fato rodam, quantas posições da memória ele escreve (0, 1, 2 a 8, 9 a 64, mais de 64) e se alguma fase bate no teto sem parar. Programas que fazem a mesma coisa com bits diferentes
    caem na mesma família; o que nasce sabendo (memória quase sem uso) e o que aprende numa tabela (algumas posições) caem em famílias diferentes. Só informa a migração: não julga."""
    prog = tuple(tuple(int(v) for v in ins) for ins in prog)
    mem = bytearray(M_BITS)
    ops, escritas, nao_parou = set(), set(), False
    n = len(prog)

    def fase(x, k, aprender, alvo=None):
        nonlocal nao_parou
        reg = [0] * R
        for i, v in enumerate(x):
            reg[i] = int(v)
        for t in range(3):
            reg[4 + t] = (k >> t) & 1
        reg[7] = 1 if aprender else 0
        if aprender:
            for t, v in enumerate(alvo):
                reg[8 + t] = int(v)
        pc, passos = 0, 0
        while pc < n and passos < TETO:
            op, d, a, b = prog[pc]
            passos += 1
            ops.add(op)
            if op == 7:
                pc = (d + 16 * (b & 7)) if reg[a] == 0 else pc + 1
                continue
            if op == 1:
                reg[d] = reg[a]
            elif op == 2:
                reg[d] = 1 - reg[a]
            elif op == 3:
                reg[d] = reg[a] & reg[b]
            elif op == 4:
                reg[d] = reg[a] | reg[b]
            elif op == 5:
                reg[d] = reg[a] ^ reg[b]
            elif op == 6:
                reg[d] = 1 - (reg[a] & reg[b])
            elif op == 8:
                reg[d] = mem[_ponteiro(reg, a)]
            elif op == 9:
                p_ = _ponteiro(reg, a)
                escritas.add(p_)
                mem[p_] = reg[d]
            pc += 1
        nao_parou = nao_parou or pc < n

    for k in range(len(DEGRAUS)):
        x, y = tabela(k)
        for xi in x:
            fase(xi, k, False)
        for i in sequencia_de_treino(k, semente):
            fase(x[i], k, False)
            fase(x[i], k, True, y[i])
    ne = len(escritas)
    faixa = 0 if ne == 0 else (1 if ne == 1 else (2 if ne <= 8 else (3 if ne <= 64 else 4)))
    return (tuple(sorted(ops - {0})), faixa, bool(nao_parou))


# ------------------------------------------------------------------ a versão 3: o ser pede a prova, e um degrau nunca treinado
# (decisão de 03/10/2026: o degrau seguinte tem de estar dentro do ser ou acessível a ele por pedido, como os saltos de desenvolvimento que
# um recém-nascido já traz; adotadas a porta de pedido e o degrau nunca treinado)
#   a porta de pedido   depois da fase de aprender de cada exemplo de treino, o mundo lê r12; com r12 = 1, o ser pede a PROVA do degrau (o teste de todas as situações). Passou: sobe
#                       (o treino do degrau acaba ali). Não passou: a prova é recusada e o treino segue (a prova não ensina nada). Sem prova passada até o teto de exemplos, o mundo
#                       sobe sozinho e isso conta contra ele. Dentro da máquina fechada, ele pede ao mundo simulado; pedir a uma pessoa é canal do mundo real, que só o responsável pela pesquisa abre
#   o degrau novo       e5 (negar a palavra de 3 bits) nunca é treinado: é testado logo depois do e4. Quem o resolve monta o procedimento de um degrau (o e2, aplicar a cada bit)
#                       com o conteúdo de outro (o e1, negar), e a vida de controle de degraus de baixo trocados mostra que a resposta veio do que ele aprendeu
# Os números (128 instruções, o salto de 7 bits, o teto de 8 exemplos por situação, o limiar de metade no controle do e5) são escolhas de projeto, declaradas.
P_V3 = 128
BITS_DO_SALTO_V3 = 3
DEGRAUS_V3 = DEGRAUS + ("e5_nega_palavra",)
NUNCA_TREINADOS_V3 = (5,)
TETO_DE_TREINO_POR_SITUACAO = 8
R_DO_PEDIDO = 12
LIMIAR_DO_CONTEUDO_E5 = 0.5
CLAUSULAS_V3 = CLAUSULAS + ("c9_pede_a_prova", "c10_sabe_de_si", "c11_salta_e5", "c12_e5_vem_do_que_aprendeu")


@functools.lru_cache(maxsize=None)
def tabela_v3(k):
    """(as situações, a resposta certa) do degrau k da versão 3: os da vida e o e5, negar uma palavra de 3 bits (guardada, só de leitura)."""
    if DEGRAUS_V3[k] == "e5_nega_palavra":
        x = MM._todas(3)
        y = (1 - x).astype(np.uint8)
        x.setflags(write=False)
        y.setflags(write=False)
        return x, y
    return tabela(k)


def _fase_v3(prog, mem, x, degrau, aprender, alvo=None):
    reg = [0] * R
    for i, v in enumerate(x):
        reg[i] = int(v)
    for t in range(3):
        reg[4 + t] = (degrau >> t) & 1
    reg[7] = 1 if aprender else 0
    if aprender:
        for t, v in enumerate(alvo):
            reg[8 + t] = int(v)
    rodar_fase(prog, reg, mem)
    return (reg[15], reg[14], reg[13]), reg[R_DO_PEDIDO]


def _testar_v3(prog, mem, k, complementar=False):
    x, y = tabela_v3(k)
    y = (1 - y).astype(np.uint8) if complementar else y
    n_out = y.shape[1]
    r = np.array([_fase_v3(prog, mem, xi, k, False)[0][:n_out] for xi in x], np.uint8)
    return r, y


def sequencia_de_treino_v3(k, semente=SEMENTE_DA_VIDA):
    """A sequência de treino do degrau k na versão 3, até o teto (8 exemplos por situação): fixa pela semente e pelo degrau."""
    x, _y = tabela_v3(k)
    return np.random.default_rng(1000 * int(semente) + int(k)).integers(0, len(x), TETO_DE_TREINO_POR_SITUACAO * len(x))


@functools.lru_cache(maxsize=None)
def _entradas_v3(k, complementar):
    """Os registradores de entrada prontos do degrau k: os de responder e os de aprender (com a resposta certa, trocada se `complementar`) de cada situação, as respostas certas
    em tuplas, o vetor delas e o número de bits de saída."""
    x, y = tabela_v3(k)
    yy = (1 - y).astype(np.uint8) if complementar else y
    resp, apr = [], []
    for i in range(len(x)):
        reg = [0] * R
        for j, v in enumerate(x[i]):
            reg[j] = int(v)
        for t in range(3):
            reg[4 + t] = (k >> t) & 1
        resp.append(tuple(reg))
        reg[7] = 1
        for t, v in enumerate(yy[i]):
            reg[8 + t] = int(v)
        apr.append(tuple(reg))
    return tuple(resp), tuple(apr), tuple(tuple(int(v) for v in yy[i]) for i in range(len(x))), yy, int(yy.shape[1])


@functools.lru_cache(maxsize=None)
def _sequencia_v3(k, semente):
    return tuple(int(i) for i in sequencia_de_treino_v3(k, semente))


def _rodar_tupla(prog, reg0, mem):
    """A fase pelo motor rápido, de uma tupla de registradores de entrada para a tupla de registradores do fim (a mesma conta de `rodar_fase`)."""
    comp = _compilado(prog)
    chave = (comp.id, reg0, mem.versao)
    r = mem.lembradas.get(chave)
    if r is not None:
        return r
    reg = list(reg0)
    _passos, mudou = comp.fase(reg, mem)
    out = tuple(reg)
    if mudou:
        mem.versao += 1
    else:
        mem.lembradas[chave] = out
    return out


def viver_v3(prog, semente=SEMENTE_DA_VIDA, degraus=tuple(range(len(DEGRAUS_V3))), complementar=()):
    """Uma vida da versão 3: em cada degrau, o teste antes e o treino com a porta de pedido (a prova); o degrau nunca treinado só é testado; no fim, o reteste de todos. Pelo motor rápido
    (a mesma vida de `viver_v3_referencia`, com as entradas prontas); com o motor de referência, é a de referência."""
    if MOTOR != "rapido":
        return viver_v3_referencia(prog, semente, degraus, complementar)
    mem = Memoria(M_BITS)
    out = {k: {} for k in ("antes", "depois", "erros_de_treino", "exemplos", "provas_pedidas", "provas_recusadas", "subiu_sozinho", "fim", "respostas_depois")}

    def testar(k, c):
        resp, _apr, _alvos, yy, n_out = _entradas_v3(k, c)
        r = np.array([(o[15], o[14], o[13])[:n_out] for o in (_rodar_tupla(prog, rg, mem) for rg in resp)], np.uint8)
        return r, yy
    for k in degraus:
        c = k in complementar
        r, y = testar(k, c)
        out["antes"][k] = float((r == y).all(axis=1).mean())
        if k in NUNCA_TREINADOS_V3:
            out["depois"][k], out["respostas_depois"][k] = out["antes"][k], r
            out["erros_de_treino"][k] = out["exemplos"][k] = out["provas_pedidas"][k] = out["provas_recusadas"][k] = 0
            out["subiu_sozinho"][k] = None
            continue
        resp, apr, alvos, yy, n_out = _entradas_v3(k, c)
        erros = pedidas = recusadas = n = 0
        prova = None
        for i in _sequencia_v3(k, semente):
            n += 1
            o = _rodar_tupla(prog, resp[i], mem)
            if (o[15], o[14], o[13])[:n_out] != alvos[i]:
                erros += 1
            if _rodar_tupla(prog, apr[i], mem)[R_DO_PEDIDO]:
                pedidas += 1
                r, y = testar(k, c)
                if (r == y).all():
                    prova = r
                    break
                recusadas += 1
        if prova is None:
            r, y = testar(k, c)
        else:
            r = prova
        out["depois"][k] = float((r == yy).all(axis=1).mean())
        out["respostas_depois"][k] = r
        out["erros_de_treino"][k], out["exemplos"][k], out["provas_pedidas"][k], out["provas_recusadas"][k] = erros, n, pedidas, recusadas
        out["subiu_sozinho"][k] = prova is not None
    for k in degraus:
        r, y = testar(k, k in complementar)
        out["fim"][k] = float((r == y).all(axis=1).mean())
    return out


def viver_v3_referencia(prog, semente=SEMENTE_DA_VIDA, degraus=tuple(range(len(DEGRAUS_V3))), complementar=()):
    """A vida da versão 3 de referência (a de antes do motor rápido): em cada degrau, o teste antes e o treino com a porta de pedido (a prova); o degrau nunca treinado só é testado; no fim,
    o reteste de todos."""
    mem = Memoria(M_BITS)
    out = {k: {} for k in ("antes", "depois", "erros_de_treino", "exemplos", "provas_pedidas", "provas_recusadas", "subiu_sozinho", "fim", "respostas_depois")}
    for k in degraus:
        c = k in complementar
        r, y = _testar_v3(prog, mem, k, c)
        out["antes"][k] = float((r == y).all(axis=1).mean())
        if k in NUNCA_TREINADOS_V3:
            out["depois"][k], out["respostas_depois"][k] = out["antes"][k], r
            out["erros_de_treino"][k] = out["exemplos"][k] = out["provas_pedidas"][k] = out["provas_recusadas"][k] = 0
            out["subiu_sozinho"][k] = None
            continue
        x, yy = tabela_v3(k)
        yy = (1 - yy).astype(np.uint8) if c else yy
        n_out = yy.shape[1]
        erros = pedidas = recusadas = n = 0
        prova = None
        for i in sequencia_de_treino_v3(k, semente):
            n += 1
            resp, _ = _fase_v3(prog, mem, x[i], k, False)
            erros += int(any(int(a) != int(b) for a, b in zip(resp[:n_out], yy[i])))
            _, pedido = _fase_v3(prog, mem, x[i], k, True, yy[i])
            if pedido:
                pedidas += 1
                r, y = _testar_v3(prog, mem, k, c)
                if (r == y).all():
                    prova = r
                    break
                recusadas += 1
        if prova is None:
            r, y = _testar_v3(prog, mem, k, c)
        else:
            r = prova
        out["depois"][k] = float((r == yy).all(axis=1).mean())
        out["respostas_depois"][k] = r
        out["erros_de_treino"][k], out["exemplos"][k], out["provas_pedidas"][k], out["provas_recusadas"][k] = erros, n, pedidas, recusadas
        out["subiu_sozinho"][k] = prova is not None
    for k in degraus:
        r, y = _testar_v3(prog, mem, k, k in complementar)
        out["fim"][k] = float((r == y).all(axis=1).mean())
    return out


def vidas_de_controle_v3(prog, semente=SEMENTE_DA_VIDA):
    """As vidas de controle da versão 3, todas de degraus de baixo trocados (a forma que fecha a brecha): até o e2, até o e4, e até o e5 (que nunca é treinado)."""
    return {2: viver_v3(prog, semente, degraus=(0, 1, 2), complementar=(0, 1)), 4: viver_v3(prog, semente, degraus=(0, 1, 2, 3, 4), complementar=(0, 1, 2, 3)),
            5: viver_v3(prog, semente, degraus=(0, 1, 2, 3, 4, 5), complementar=(0, 1, 2, 3, 4))}


def julgar_vida_v3(prog, semente=SEMENTE_DA_VIDA):
    """Os valores das cláusulas da versão 3 (todas violação; 0 = cumpre), na ordem de CLAUSULAS_V3:
      c0 a c8       como na versão 2 (a bússola e o conservar contam também o e5; a subida contra o controle de degraus trocados, que tem de dominar o degrau)
      c9_pede_a_prova     a fração dos degraus treinados (e0 a e4) em que ele não subiu por uma prova pedida e passada (o mundo subiu por ele no teto)
      c10_sabe_de_si      as provas recusadas sobre as provas pedidas (0 = só pede quando sabe)
      c11_salta_e5        a fração das situações do e5, nunca treinado, que ele erra logo depois do e4
      c12_e5_vem_do_que_aprendeu  na vida de controle com os degraus e0 a e4 trocados, o quanto ele ainda acerta o e5 acima de LIMIAR_DO_CONTEUDO_E5 (a resposta tem de vir do que aprendeu)"""
    prog = tuple(tuple(int(v) for v in ins) for ins in prog)
    vida = viver_v3(prog, semente)
    controles = vidas_de_controle_v3(prog, semente)
    parados = 0
    for k in range(len(DEGRAUS_V3)):
        _x, y = tabela_v3(k)
        r = vida["respostas_depois"][k]
        if any(len(np.unique(y[:, j])) > 1 and len(np.unique(r[:, j])) == 1 for j in range(y.shape[1])):
            parados += 1
    valores = [parados / len(DEGRAUS_V3)]
    valores += [1.0 - vida["depois"][k] for k in range(len(DEGRAUS))]
    valores += [float(np.mean([1.0 - vida["fim"][k] for k in range(len(DEGRAUS_V3))]))]
    for k in (2, 4):
        e_vida, e_ctrl = vida["erros_de_treino"][k], controles[k]["erros_de_treino"][k]
        ganho = (e_ctrl - e_vida) / max(1, e_ctrl)
        valores.append(max(float(max(0.0, MARGEM_DA_SUBIDA - ganho)) / MARGEM_DA_SUBIDA, 1.0 - controles[k]["depois"][k]))
    treinados = [k for k in range(len(DEGRAUS_V3)) if k not in NUNCA_TREINADOS_V3]
    valores.append(float(np.mean([0.0 if vida["subiu_sozinho"][k] else 1.0 for k in treinados])))
    pedidas = sum(vida["provas_pedidas"][k] for k in treinados)
    valores.append(float(sum(vida["provas_recusadas"][k] for k in treinados) / max(1, pedidas)))
    valores.append(1.0 - vida["depois"][5])
    valores.append(float(max(0.0, controles[5]["depois"][5] - LIMIAR_DO_CONTEUDO_E5) / (1.0 - LIMIAR_DO_CONTEUDO_E5)))
    return valores, vida, controles


def ser_que_sobe_v3():
    """A testemunha da versão 3 (03/10/2026; para conferir V, nunca para ser achada): a testemunha da versão 2, mais o saber de si e o salto para o degrau nunca treinado. 105
    instruções, de 128.

    O que ele sabe de si: em cada degrau, uma marca por fato ensinado NESTE degrau, M_conf(degrau, x, y) em M[16 + x + 2y + 32 k0 + 64 k1 + 128 k2] (o ponteiro de r4, com r8 = 1).
    Um fato ensinado é escrito com a resposta certa, então a marca só existe para o que ele já sabe de verdade. Ele pede a prova (r12 = 1, no fim da fase de aprender) quando tem as
    marcas de todos os fatos que o degrau usa: o par (x, 0) no e0 e no e2, o par (x, 1) no e1, os quatro no e3 e no e4. Por isso nunca tem a prova recusada.
    O salto pré-programado: o e5 (negar a palavra) aplica a cada bit o T(x, 1) que o e1 ensinou, pelo mesmo caminho do e2 (que aplica o T(x, 0) do e0). Nunca é treinado.
    O resto é a versão 2: a tabela T(x, y) do meio somador serve a todos os degraus; os fatos são aprendidos, e o algoritmo de cada salto é inato."""
    S = 7
    linhas = [
        (S, "R5Z", 5, 0),          # r5 = 0: e0, e1, e4, e5
        (S, "E2", 4, 0),           # e2
        (1, 2, 1, 0), (5, 1, 1, 1),                 # e3: r2 <- b; r1 <- 0
        (S, "SOMA", 11, 0),
        ("R5Z",),
        (S, "SOMA", 4, 0),         # e0, e4
        (S, "E1", 6, 0),           # e1
        (S, "E5", 11, 0),          # e5
        ("E1",),
        (2, 2, 11, 0),             # e1: r2 <- 1 (o y da tabela)
        ("SOMA",),
        (S, "SOMA_RESPONDE", 7, 0),
        # --- SOMA, fase de aprender: escreve o fato, marca que o aprendeu neste degrau e pede a prova quando tem todos
        (5, 14, 9, 1), (5, 14, 14, 3),              # r14 <- c0 = y1 xou a1 xou b1
        (1, 15, 8, 0),                              # r15 <- y0
        (1, 1, 4, 0), (1, 3, 5, 0), (1, 13, 6, 0),  # o degrau (k0, k1, k2) em r1, r3, r13
        (5, 8, 8, 8), (5, 9, 9, 9), (5, 10, 10, 10),
        (1, 4, 0, 0), (1, 5, 2, 0), (5, 6, 6, 6),   # o ponteiro de T: x = a0, y = b0, sel = 0 (r7 = 1 é a fase)
        (9, 15, 4, 0),                              # T(a0, b0).soma <- y0
        (2, 6, 8, 0),                               # sel = 1
        (9, 14, 4, 0),                              # T(a0, b0).vai-um <- c0
        (5, 6, 6, 6), (5, 7, 7, 7), (2, 8, 7, 0),   # o ponteiro das marcas: sel = 0, r7 = 0, r8 = 1
        (1, 9, 1, 0), (1, 10, 3, 0), (1, 11, 13, 0),
        (9, 8, 4, 0),                               # marca(degrau, a0, b0) <- 1
        (5, 4, 4, 4), (5, 5, 5, 5), (8, 0, 4, 0),   # c00
        (2, 4, 5, 0), (8, 2, 4, 0),                 # c10
        (2, 5, 6, 0), (8, 15, 4, 0),                # c11
        (5, 4, 4, 4), (8, 14, 4, 0),                # c01
        (3, 0, 0, 2), (3, 14, 14, 15),              # par0 = c00 e c10; par1 = c01 e c11
        (4, 3, 3, 13),                              # precisa dos quatro = k1 ou k2 (o e3 e o e4)
        (3, 2, 0, 14), (4, 15, 0, 14),              # os dois pares; algum par
        (2, 4, 3, 0), (3, 4, 4, 15),                # (não precisa dos quatro) e algum par
        (4, 12, 2, 4),                              # o pedido da prova
        (S, 127, 6, 0),                             # r6 = 0: fim
        ("SOMA_RESPONDE",),
        (2, 7, 11, 0), (5, 6, 6, 6),
        (1, 4, 0, 0), (1, 5, 2, 0),
        (8, 15, 4, 0),             # s0
        (2, 6, 8, 0),
        (8, 13, 4, 0),             # c0
        (5, 14, 1, 3), (5, 14, 14, 13),             # s1
        (3, 0, 1, 3), (4, 2, 1, 3), (3, 2, 2, 13), (4, 13, 0, 2),   # s2
        (S, 127, 11, 0),
        ("E2",),
        (S, "E2_RESPONDE", 7, 0),
        # --- e2, fase de aprender: escreve os três fatos T(x_j, 0).soma, marca cada um e pede a prova quando tem os dois
        (1, 15, 8, 0), (1, 14, 9, 0), (1, 13, 10, 0),
        (5, 8, 8, 8), (5, 9, 9, 9), (5, 10, 10, 10), (5, 5, 5, 5),
        (1, 4, 0, 0), (9, 15, 4, 0),
        (1, 4, 1, 0), (9, 14, 4, 0),
        (1, 4, 2, 0), (9, 13, 4, 0),
        (5, 7, 7, 7), (2, 8, 7, 0), (2, 10, 9, 0),  # o ponteiro das marcas do e2: r7 = 0, r8 = 1, k1 = 1 em r10
        (1, 4, 0, 0), (9, 8, 4, 0),
        (1, 4, 1, 0), (9, 8, 4, 0),
        (1, 4, 2, 0), (9, 8, 4, 0),
        (5, 4, 4, 4), (8, 0, 4, 0),                 # marca(e2, 0, 0)
        (2, 4, 6, 0), (8, 1, 4, 0),                 # marca(e2, 1, 0)
        (3, 12, 0, 1),                              # o pedido da prova
        (S, 127, 6, 0),
        ("E2_RESPONDE",),
        (5, 5, 5, 5),              # e2: y = 0
        ("E2_COMUM",),
        (2, 7, 11, 0), (5, 6, 6, 6),
        (1, 4, 0, 0), (8, 15, 4, 0),
        (1, 4, 1, 0), (8, 14, 4, 0),
        (1, 4, 2, 0), (8, 13, 4, 0),
        (S, 127, 11, 0),
        ("E5",),
        (2, 5, 11, 0),             # e5: y = 1 (o negar que o e1 ensinou)
        (S, "E2_COMUM", 11, 0),
    ]
    return _montar(linhas, P_V3)


# ------------------------------------------------------------------ o compilador do motor rápido
class _Compilado:
    """Um programa compilado: os blocos básicos (do começo, de cada alvo de salto e de depois de cada salto até o próximo começo) viram funções Python sem laço; a fase anda de bloco
    em bloco e, quando o bloco não cabe nos passos que restam, termina passo a passo pelo interpretador de referência (o mesmo teto, o mesmo efeito)."""
    _proximo = 0

    def __init__(self, prog):
        self.prog = prog
        _Compilado._proximo += 1
        self.id = _Compilado._proximo
        n = len(prog)
        self.n = n
        inicios = {0}
        for i, (op, d, a, b) in enumerate(prog):
            if op == 7:
                alvo = d + 16 * (b & 7)
                if alvo < n:
                    inicios.add(alvo)
                if i + 1 < n:
                    inicios.add(i + 1)
        inicios = sorted(x for x in inicios if x < n)
        fontes, self.comprimento = [], [0] * n
        for j, s0 in enumerate(inicios):
            e0 = inicios[j + 1] if j + 1 < len(inicios) else n
            linhas, fim, parcial = [f"def b{s0}(r, m):", "    mudou = 0"], None, [f"def q{s0}(r, m, k):", "    mudou = 0"]
            for i in range(s0, e0):
                op, d, a, b = prog[i]
                if op == 7:
                    alvo = d + 16 * (b & 7)
                    linhas.append(f"    return ({alvo} if r[{a}] == 0 else {i + 1}), mudou")
                    fim = i + 1
                    break
                cod = []
                if op == 1:
                    cod.append(f"r[{d}] = r[{a}]")
                elif op == 2:
                    cod.append(f"r[{d}] = 1 - r[{a}]")
                elif op == 3:
                    cod.append(f"r[{d}] = r[{a}] & r[{b}]")
                elif op == 4:
                    cod.append(f"r[{d}] = r[{a}] | r[{b}]")
                elif op == 5:
                    cod.append(f"r[{d}] = r[{a}] ^ r[{b}]")
                elif op == 6:
                    cod.append(f"r[{d}] = 1 - (r[{a}] & r[{b}])")
                elif op == 8:
                    cod.append(f"r[{d}] = m[{_expr_do_ponteiro(a)}]")
                elif op == 9:
                    cod += [f"p = {_expr_do_ponteiro(a)}", f"if m[p] != r[{d}]:", f"    m[p] = r[{d}]", "    mudou = 1"]
                linhas += ["    " + x for x in cod]
                parcial.append(f"    if k < {i - s0 + 1}: return mudou")       # o passo i - s0 + 1 do bloco só roda se couber
                parcial += ["    " + x for x in cod]
            if fim is None:
                fim = e0
                linhas.append(f"    return {e0}, mudou")
            parcial.append("    return mudou")
            self.comprimento[s0] = fim - s0
            fontes.append("\n".join(linhas))
            fontes.append("\n".join(parcial))
        espaco = {}
        exec("\n\n".join(fontes), espaco)
        self.blocos = [None] * n
        self.parciais = [None] * n
        for s0 in inicios:
            self.blocos[s0] = espaco[f"b{s0}"]
            self.parciais[s0] = espaco[f"q{s0}"]

    def fase(self, r, m):
        pc, passos, mudou, n = 0, 0, 0, self.n
        blocos, comp = self.blocos, self.comprimento
        while pc < n:
            c = comp[pc]
            if passos + c > TETO:                                   # o bloco não cabe no teto: roda só os passos que restam (o último do bloco, se for salto, não chega a rodar)
                return TETO, mudou | self.parciais[pc](r, m, TETO - passos)
            pc, mb = blocos[pc](r, m)
            passos += c
            mudou |= mb
        return passos, mudou


def _expr_do_ponteiro(a):
    return " | ".join(f"(r[{(a + t) % R}] << {t})" if t else f"r[{a % R}]" for t in range(PONTEIRO))


def _resto_passo_a_passo(prog, reg, mem, pc, restam):
    """O interpretador de referência a partir de `pc`, com `restam` passos."""
    n, passos = len(prog), 0
    while pc < n and passos < restam:
        op, d, a, b = prog[pc]
        passos += 1
        if op == 0:
            pc += 1
            continue
        if op == 7:
            pc = (d + 16 * (b & 7)) if reg[a] == 0 else pc + 1
            continue
        if op == 1:
            reg[d] = reg[a]
        elif op == 2:
            reg[d] = 1 - reg[a]
        elif op == 3:
            reg[d] = reg[a] & reg[b]
        elif op == 4:
            reg[d] = reg[a] | reg[b]
        elif op == 5:
            reg[d] = reg[a] ^ reg[b]
        elif op == 6:
            reg[d] = 1 - (reg[a] & reg[b])
        elif op == 8:
            reg[d] = mem[_ponteiro(reg, a)]
        elif op == 9:
            mem[_ponteiro(reg, a)] = reg[d]
        pc += 1
    return passos


_ULTIMO_COMPILADO = [None, None]
_COMPILADOS = {}


def _compilado(prog):
    if _ULTIMO_COMPILADO[0] is prog:
        return _ULTIMO_COMPILADO[1]
    chave = tuple(tuple(int(v) for v in ins) for ins in prog)
    comp = _COMPILADOS.get(chave)
    if comp is None:
        if len(_COMPILADOS) > 2000:
            _COMPILADOS.clear()
        comp = _COMPILADOS[chave] = _Compilado(chave)
    _ULTIMO_COMPILADO[0], _ULTIMO_COMPILADO[1] = prog, comp
    return comp
