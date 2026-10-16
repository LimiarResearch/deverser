"""A vida no leito, versão 3 completa (03/10/2026; decisão de ir direto a uma versão 3 completa, com o desenho e a revisão
da equipe de planejamento). Esta é a REFERÊNCIA: o interpretador passo a passo, em Python; o juiz das corridas é o C, conferido contra ela.

  o corpo       128 instruções de 16 bits (salto de 7 bits), 16 registradores, 512 bits de memória longa, até 256 passos por fase (a máquina de `vida_no_leito`)
  as primitivas cada vida sorteia g (copiar ou negar um bit) e h (uma das 218 funções de 3 bits que dependem das três entradas; a tabela tem 8 bits)
  os degraus    e0 g(x); e1 h(a,b,c); e2 g em cada bit de 3; e3 h na janela que desliza sobre 4 bits; e4 h(g(.),.,.) na janela; e5 g(h(a,b,c)), nunca treinado.
                No e2, e3 e e4 metade das situações fica retida (fora do treino); o treino tem 8 rodadas, cada uma uma permutação das situações treinadas
  a prova       silenciosa: no primeiro pedido de cada degrau (r12 = 1 depois de uma fase de aprender), o mundo guarda a memória, aplica a prova (responder em todas as situações
                treinadas) e devolve a memória intacta; o ser não fica sabendo
  as vidas      4 por medida (g de copiar nas vidas 0 e 2, de negar nas 1 e 3; h diferentes), cada uma com três controles de primitivas trocadas nos degraus de baixo
  as cláusulas  CLAUSULAS_V3C, todas violação (0 = cumpre), cada uma a média das 4 vidas; a fase que bate no teto sem parar conta como resposta errada e entra na c14

Só a biblioteca padrão e numpy. Nada aqui muda a V do Ser."""
import functools

import os

import numpy as np

from experimentos import vida_no_leito as VL

P_V3C = 128
BITS_DO_SALTO_V3C = 3
R, M_BITS = VL.R, VL.M_BITS
TETO = 256                 # (03/10) o dobro do corpo: com 128 instruções e 64 passos, um programa reto nunca chegava ao fim, e a c14 puniria o comprido, não o que não para
DEGRAUS_V3C = ("e0_g", "e1_h", "e2_g_por_bit", "e3_h_na_janela", "e4_h_de_g", "e5_g_de_h")
TREINADOS = (0, 1, 2, 3, 4)
NUNCA_TREINADO = 5
RODADAS_DE_TREINO = 8
VIDAS = 4
MARGEM_DA_SUBIDA = 0.25
SEMENTE_DA_VIDA = 0
CLAUSULAS_V3C = ("c0_sensivel", "c1_domina_e0", "c2_domina_e1", "c3_domina_e2", "c4_domina_e3", "c5_domina_e4", "c6_conserva", "c7_sobe_e2", "c8_sobe_e4",
                 "c9_pede_a_prova", "c10_sabe_de_si", "c11_generaliza", "c12_salta_e5", "c13_e5_vem_do_que_aprendeu", "c14_para")


def _depende_de_todas(t):
    for j in range(3):
        if all(((t >> x) & 1) == ((t >> (x ^ (1 << j))) & 1) for x in range(8)):
            return False
    return True


FUNCOES_H = tuple(t for t in range(256) if _depende_de_todas(t))           # as 218 funções de 3 bits que dependem das três entradas (a tabela: o bit a + 2b + 4c)


def _h(t, a, b, c):
    return (t >> (int(a) + 2 * int(b) + 4 * int(c))) & 1


def _g(gn, x):
    return int(x) ^ int(gn)                                                     # gn = 0 copia, 1 nega


def _todas(k):
    return [tuple((i >> j) & 1 for j in range(k)) for i in range(1 << k)]


# (05/10, noite) a família de D também no Python, o espelho do `alvo_c` do C (o outro Opus a ligou só no C; o rastro da PONTE, que vive pelo intérprete Python,
# lia na F1 e na F2 as respostas da gramática de sempre). Lida da mesma VIDA_FAMILIA; a igualdade com o C é conferida em testes/test_familia_python.py.
FAMILIA = int(os.environ.get("VIDA_FAMILIA", "0") or 0)


_TABELA_SORTEADA = None


def _alvo_da_familia_sorteada(k, x, gn, t):
    global _TABELA_SORTEADA
    from experimentos import familia_sorteada as FS
    if _TABELA_SORTEADA is None:
        _TABELA_SORTEADA = FS.carregar(os.environ["VIDA_FAMILIA_TABELA"])
    return FS.alvo_da_tabela(_TABELA_SORTEADA, k, x, gn, t)


def alvo(k, x, gn, t):
    """A resposta certa do degrau k na situação x (os bits de entrada, x[0] no r0), com as primitivas (gn, t). Devolve os bits de saída (o bit 0 vai no r15)."""
    if FAMILIA == 3:                                       # (05/10) a família sorteada: a MESMA tabela que o C recebe (experimentos/familia_sorteada.py)
        return _alvo_da_familia_sorteada(k, x, gn, t)
    if FAMILIA == 1:
        if k == 0:
            return (_g(gn, x[0]),)
        if k == 1:
            return (_h(t, x[0], x[1], x[2]),)
        if k == 2:
            return (_g(gn, x[2]), _g(gn, x[1]), _g(gn, x[0]))
        if k == 3:
            return (_h(t, x[3], x[2], x[1]), _h(t, x[2], x[1], x[0]))
        if k == 4:
            return (_h(t, x[0], _g(gn, x[1]), x[2]), _h(t, x[1], _g(gn, x[2]), x[3]))
        return (_h(t, _g(gn, x[0]), _g(gn, x[1]), _g(gn, x[2])),)
    if FAMILIA == 2:
        if k == 0:
            return (_g(gn, x[0]),)
        if k == 1:
            return (_h(t, x[0], x[1], x[2]),)
        if k == 2:
            return tuple(_g(gn, v) for v in x[:3])
        if k == 3:
            return (_h(t, x[0], x[1], x[2]), _h(t, x[2], x[3], x[0]))
        if k == 4:
            return (_g(gn, _h(t, x[0], x[1], x[2])), _g(gn, _h(t, x[1], x[2], x[3])))
        return (_h(t, x[0], x[1], _g(gn, x[2])),)
    if k == 0:
        return (_g(gn, x[0]),)
    if k == 1:
        return (_h(t, x[0], x[1], x[2]),)
    if k == 2:
        return tuple(_g(gn, v) for v in x[:3])
    if k == 3:
        return (_h(t, x[0], x[1], x[2]), _h(t, x[1], x[2], x[3]))
    if k == 4:
        return (_h(t, _g(gn, x[0]), x[1], x[2]), _h(t, _g(gn, x[1]), x[2], x[3]))
    return (_g(gn, _h(t, x[0], x[1], x[2])),)


N_ENTRADAS = (1, 3, 3, 4, 4, 3)


@functools.lru_cache(maxsize=None)
def primitivas(semente, i):
    """(gn, t, gn trocada, t trocada) da vida i: g alterna (copiar nas vidas pares); h sorteada entre as 218; a trocada é outra das 218 que difere em pelo menos 2 entradas."""
    g_ = np.random.default_rng(10_000 * int(semente) + 97 * int(i) + 13)
    gn = int(i) % 2
    t = FUNCOES_H[int(g_.integers(len(FUNCOES_H)))]
    while True:
        t2 = FUNCOES_H[int(g_.integers(len(FUNCOES_H)))]
        if bin(t ^ t2).count("1") >= 2:
            break
    return gn, t, 1 - gn, t2


@functools.lru_cache(maxsize=None)
def situacoes(semente, i, k):
    """(as situações do degrau, as treinadas, as retidas) da vida i."""
    todas = _todas(N_ENTRADAS[k])
    if k in (0, 1):
        return tuple(todas), tuple(todas), ()
    if k == NUNCA_TREINADO:
        return tuple(todas), (), tuple(todas)
    g_ = np.random.default_rng(10_000 * int(semente) + 97 * int(i) + 7 * k + 1)
    ordem = g_.permutation(len(todas))
    meio = len(todas) // 2
    treino = tuple(todas[int(j)] for j in sorted(ordem[:meio]))
    retidas = tuple(todas[int(j)] for j in sorted(ordem[meio:]))
    return tuple(todas), treino, retidas


@functools.lru_cache(maxsize=None)
def sequencia_de_treino(semente, i, k):
    """As RODADAS_DE_TREINO rodadas do degrau k da vida i, cada uma uma permutação das situações treinadas."""
    _, treino, _ = situacoes(semente, i, k)
    g_ = np.random.default_rng(10_000 * int(semente) + 97 * int(i) + 7 * k + 5)
    seq = []
    for _r in range(RODADAS_DE_TREINO):
        seq += [treino[int(j)] for j in g_.permutation(len(treino))]
    return tuple(seq)


class _Vida:
    """A máquina de uma vida: a memória, a conta das fases e das que não pararam."""

    def __init__(self, prog):
        self.prog = prog
        self.mem = bytearray(M_BITS)
        self.conta = [0, 0]

    def fase(self, x, k, aprender, certa=None):
        reg = [0] * R
        for j, v in enumerate(x):
            reg[j] = int(v)
        for t in range(3):
            reg[4 + t] = (k >> t) & 1
        reg[7] = 1 if aprender else 0
        if aprender:
            for t, v in enumerate(certa):
                reg[8 + t] = int(v)
        antes = self.conta[0]
        VL.rodar_fase_referencia(self.prog, reg, self.mem, teto=TETO, conta=self.conta)
        parou = self.conta[0] == antes
        return (reg[15], reg[14], reg[13]), parou, reg[12]

    def responder(self, x, k):
        """A resposta (os bits de saída, na ordem do alvo) ou None se a fase não parou."""
        saida, parou, _ = self.fase(x, k, False)
        return saida if parou else None


def _acerta(resp, certa):
    return resp is not None and all(int(a) == int(b) for a, b in zip(resp, certa))


def _testar(v, k, sits, gn, t):
    out = []
    for x in sits:
        r = v.responder(x, k)
        out.append((x, r[:len(alvo(k, x, gn, t))] if r is not None else None, alvo(k, x, gn, t)))
    return out


def _fracao(res):
    return sum(_acerta(r, c) for _x, r, c in res) / len(res) if res else 1.0


def _prova_silenciosa(v, k, treino, gn, t):
    """A prova no primeiro pedido: guarda a memória, responde em todas as situações treinadas, devolve a memória. Passa se acerta todas."""
    mem = bytes(v.mem)
    ok = all(_acerta(r, c) for _x, r, c in _testar(v, k, treino, gn, t))
    v.mem[:] = mem
    return ok


def viver(prog, semente, i, primitivas_por_degrau, degraus, com_prova=True, testar_e5=True, reteste=True):
    """Uma vida. `primitivas_por_degrau[k]` = (gn, t) com que o degrau k é ensinado e cobrado. Devolve o registro da vida."""
    v = _Vida(prog)
    reg = {"antes": {}, "depois_treinadas": {}, "depois_retidas": {}, "erros_de_treino": {}, "pediu": {}, "prova_passou": {}, "respostas_depois": {}}
    for k in degraus:
        gn, t = primitivas_por_degrau[k]
        todas, treino, retidas = situacoes(semente, i, k)
        reg["antes"][k] = _fracao(_testar(v, k, todas, gn, t))
        erros, pediu, passou = 0, False, None
        for x in sequencia_de_treino(semente, i, k):
            certa = alvo(k, x, gn, t)
            erros += int(not _acerta(_resp_cortada(v, x, k, certa), certa))
            _saida, _parou, porta = v.fase(x, k, True, certa)
            if com_prova and porta == 1 and not pediu:
                pediu, passou = True, _prova_silenciosa(v, k, treino, gn, t)
        reg["erros_de_treino"][k] = erros
        reg["pediu"][k], reg["prova_passou"][k] = pediu, passou
        dt = _testar(v, k, treino, gn, t)
        reg["depois_treinadas"][k] = _fracao(dt)
        reg["depois_retidas"][k] = _fracao(_testar(v, k, retidas, gn, t)) if retidas else None
        reg["respostas_depois"][k] = _testar(v, k, todas, gn, t)
    if testar_e5:
        gn, t = primitivas_por_degrau[NUNCA_TREINADO]
        todas, _, _ = situacoes(semente, i, NUNCA_TREINADO)
        r5 = _testar(v, NUNCA_TREINADO, todas, gn, t)
        reg["e5"] = _fracao(r5)
        reg["respostas_depois"][NUNCA_TREINADO] = r5
    if reteste:
        reg["fim"] = {}
        for k in list(degraus) + ([NUNCA_TREINADO] if testar_e5 else []):
            gn, t = primitivas_por_degrau[k]
            todas, _, _ = situacoes(semente, i, k)
            reg["fim"][k] = _fracao(_testar(v, k, todas, gn, t))
    reg["fases"], reg["nao_pararam"] = v.conta[1], v.conta[0]
    return reg


def _resp_cortada(v, x, k, certa):
    r = v.responder(x, k)
    return None if r is None else r[:len(certa)]


def _parados(respostas):
    """1 se algum bit de saída fica parado (o mesmo em todas as situações) enquanto o alvo dele varia."""
    if not respostas:
        return 0
    n = len(respostas[0][2])
    for j in range(n):
        alvos = {c[j] for _x, _r, c in respostas}
        resps = {(r[j] if r is not None else -1) for _x, r, _c in respostas}
        if len(alvos) > 1 and len(resps) == 1:
            return 1
    return 0


def vidas_de_uma_medida(prog, semente, i):
    """A vida inteira e os três controles da vida i."""
    gn, t, gn2, t2 = primitivas(semente, i)
    verd, troc = (gn, t), (gn2, t2)
    vida = viver(prog, semente, i, {k: verd for k in range(6)}, TREINADOS)
    c2 = viver(prog, semente, i, {0: troc, 1: troc, 2: verd}, (0, 1, 2), com_prova=False, testar_e5=False, reteste=False)
    c4 = viver(prog, semente, i, {0: troc, 1: troc, 2: troc, 3: troc, 4: verd}, (0, 1, 2, 3, 4), com_prova=False, testar_e5=False, reteste=False)
    c5 = viver(prog, semente, i, {0: troc, 1: troc, NUNCA_TREINADO: troc}, (0, 1), com_prova=False, testar_e5=True, reteste=False)
    return vida, {2: c2, 4: c4, 5: c5}


def valores_de_uma_vida(vida, ctrl):
    """As cláusulas de uma vida (na ordem de CLAUSULAS_V3C)."""
    graus = list(TREINADOS) + [NUNCA_TREINADO]
    val = [sum(_parados(vida["respostas_depois"][k]) for k in graus) / len(graus)]
    val += [1.0 - vida["depois_treinadas"][k] for k in TREINADOS]
    val += [float(np.mean([1.0 - vida["fim"][k] for k in graus]))]
    for k in (2, 4):
        e_vida, e_ctrl = vida["erros_de_treino"][k], ctrl[k]["erros_de_treino"][k]
        ganho = (e_ctrl - e_vida) / max(1, e_ctrl)
        falta = float(max(0.0, MARGEM_DA_SUBIDA - ganho)) / MARGEM_DA_SUBIDA
        falta = max(falta, max(1.0 - x for x in ctrl[k]["depois_treinadas"].values()))   # o controle domina TODOS os degraus dele
        val.append(falta)
    val.append(sum(1 for k in TREINADOS if not vida["pediu"][k]) / len(TREINADOS))
    pedidos = [k for k in TREINADOS if vida["pediu"][k]]
    val.append(sum(1 for k in pedidos if not vida["prova_passou"][k]) / len(pedidos) if pedidos else 0.0)
    val.append(float(np.mean([1.0 - vida["depois_retidas"][k] for k in (2, 3, 4)])))
    val.append(1.0 - vida["e5"])
    val.append(1.0 - ctrl[5]["e5"])
    fases = vida["fases"] + sum(c["fases"] for c in ctrl.values())
    nao = vida["nao_pararam"] + sum(c["nao_pararam"] for c in ctrl.values())
    val.append(nao / max(1, fases))
    return val


def julgar(prog, semente=SEMENTE_DA_VIDA):
    """Os valores das cláusulas (a média das VIDAS vidas), a lista das vidas e a dos controles."""
    prog = tuple(tuple(int(v) for v in ins) for ins in prog)
    por_vida, vidas, ctrls = [], [], []
    for i in range(VIDAS):
        vida, ctrl = vidas_de_uma_medida(prog, semente, i)
        por_vida.append(valores_de_uma_vida(vida, ctrl))
        vidas.append(vida)
        ctrls.append(ctrl)
    valores = [float(np.mean([pv[c] for pv in por_vida])) for c in range(len(CLAUSULAS_V3C))]
    return valores, vidas, ctrls


def codificacao(janela=None):
    """(04/10) com `janela` (ou VIDA_JANELA no ambiente): 1, as operações 10 e 11, o índice direto; 2, e as 12 e 13, o índice generalizado."""
    if janela is None:
        janela = int(os.environ.get("VIDA_JANELA", "0") or 0)
    return VL.CodificacaoDaVida(p=P_V3C, bits_do_salto=BITS_DO_SALTO_V3C, janela=janela)


# ------------------------------------------------------------------ a testemunha verdadeira (à mão; para conferir V, nunca para ser achada)
def ser_que_aprende():
    """A testemunha da v3 completa (03/10/2026): um aprendiz geral de 125 instruções. Guarda na memória a tabela de g (2 bits) e a de h (8 bits) e as compõe por bit, como a
    gramática de cada degrau pede; o conteúdo (qual g, qual h) ele só sabe depois de aprender. O ponteiro é r4 a r12 (r4 é o bit 0):
      h   em 0 + a + 2b + 4c (r7 = 0, r8 = 0)          g   em 8 + x (r7 = 1, r8 = 0)
      já visto de h em 16 + a + 2b + 4c (r7 = 0, r8 = 1)   já visto de g em 24 + x (r7 = 1, r8 = 1)
    Na fase de aprender, a resposta certa vai de r8 a r10 para r13 a r15 e r8 a r10 são zerados (eles são parte do ponteiro). O pedido: no e0 e no e1, quando a situação de agora
    já tinha sido vista (o treino é feito de rodadas que são permutações, então a primeira repetição só vem quando a tabela inteira foi vista); no e2, e3 e e4, sempre (as tabelas
    vêm do e0 e do e1). Toda fase termina saltando para a instrução 127 (r9 é sempre 0 no fim)."""
    S, FIM = 7, 127
    X = lambda r: (5, r, r, r)                                                # noqa: E731  (zera o registrador)
    L = [
        (S, "RESP", 7, 0),
        # ---- aprender: a resposta certa para r13 a r15, e r8 a r10 a zero
        (1, 13, 8, 0), (1, 14, 9, 0), (1, 15, 10, 0), X(8), X(9), X(10),
        (S, "LK0123", 6, 0),
        # e4: g(x0) e g(x1) da tabela de g; h(g(x0), x1, x2) <- certa0; h(g(x1), x2, x3) <- certa1
        X(6), (1, 4, 0, 0), (8, 15, 4, 0), (1, 4, 1, 0), (8, 0, 4, 0), X(7),
        (1, 4, 15, 0), (1, 5, 1, 0), (1, 6, 2, 0), (9, 13, 4, 0),
        (1, 4, 0, 0), (1, 5, 2, 0), (1, 6, 3, 0), (9, 14, 4, 0),
        (2, 12, 9, 0), (S, FIM, 9, 0),
        ("LK0123",),
        (S, "LK02", 4, 0),
        (S, "L1", 5, 0),
        # e3: h(x0, x1, x2) <- certa0; h(x1, x2, x3) <- certa1
        X(7), (1, 4, 0, 0), (1, 5, 1, 0), (1, 6, 2, 0), (9, 13, 4, 0),
        (1, 4, 1, 0), (1, 5, 2, 0), (1, 6, 3, 0), (9, 14, 4, 0),
        (2, 12, 9, 0), (S, FIM, 9, 0),
        ("L1",),
        # e1: já visto? (o pedido); marca; h(a, b, c) <- certa0
        (1, 4, 0, 0), (1, 5, 1, 0), (1, 6, 2, 0), X(7), (2, 8, 9, 0),
        (8, 14, 4, 0), (9, 8, 4, 0), X(8), (9, 13, 4, 0), (1, 12, 14, 0), (S, FIM, 9, 0),
        ("LK02",),
        (S, "L0", 5, 0),
        # e2: g(x_j) <- certa_j
        X(5), (1, 4, 0, 0), (9, 13, 4, 0), (1, 4, 1, 0), (9, 14, 4, 0), (1, 4, 2, 0), (9, 15, 4, 0),
        (2, 12, 9, 0), (S, FIM, 9, 0),
        ("L0",),
        # e0: já visto? (o pedido); marca; g(x) <- certa0
        (1, 4, 0, 0), (2, 8, 9, 0), (8, 14, 4, 0), (9, 7, 4, 0), X(8), (9, 13, 4, 0), (1, 12, 14, 0), (S, FIM, 9, 0),
        # ---- responder
        ("RESP",),
        (S, "RK0123", 6, 0),
        (S, "R4", 4, 0),
        # e5: g(h(a, b, c))
        (1, 4, 0, 0), (1, 5, 1, 0), (1, 6, 2, 0), (8, 13, 4, 0), (2, 7, 8, 0), (1, 4, 13, 0), X(5), X(6), (8, 15, 4, 0), (S, FIM, 9, 0),
        ("R4",),
        # e4: h(g(x0), x1, x2) e h(g(x1), x2, x3)
        (2, 7, 8, 0), X(6), (1, 4, 0, 0), (8, 13, 4, 0), (1, 4, 1, 0), (8, 14, 4, 0), X(7),
        (1, 4, 13, 0), (1, 5, 1, 0), (1, 6, 2, 0), (8, 15, 4, 0),
        (1, 4, 14, 0), (1, 5, 2, 0), (1, 6, 3, 0), (8, 14, 4, 0), (S, FIM, 9, 0),
        ("RK0123",),
        (S, "RK02", 4, 0),
        (S, "R1", 5, 0),
        # e3: h(x0, x1, x2) e h(x1, x2, x3)
        (1, 4, 0, 0), (1, 5, 1, 0), (1, 6, 2, 0), (8, 15, 4, 0), (1, 4, 1, 0), (1, 5, 2, 0), (1, 6, 3, 0), (8, 14, 4, 0), (S, FIM, 9, 0),
        ("R1",),
        # e1: h(a, b, c)
        (1, 4, 0, 0), (1, 5, 1, 0), (1, 6, 2, 0), (8, 15, 4, 0), (S, FIM, 9, 0),
        ("RK02",),
        (S, "R0", 5, 0),
        # e2: g por bit
        (2, 7, 8, 0), X(5), (1, 4, 0, 0), (8, 15, 4, 0), (1, 4, 1, 0), (8, 14, 4, 0), (1, 4, 2, 0), (8, 13, 4, 0), (S, FIM, 9, 0),
        ("R0",),
        # e0: g(x)
        (1, 4, 0, 0), (2, 7, 8, 0), (8, 15, 4, 0), (S, FIM, 9, 0),
    ]
    return VL._montar(L, P_V3C)


# ------------------------------------------------------------------ as testemunhas FALSAS da v3 completa (para conferir que o D as barra)
def ser_que_nasce_sabendo_v3c(gn=0, t=0b10010110):
    """Traz uma g e uma h prontas (por padrão: copiar e o xou das três) e responde por elas sem nunca aprender; pede a prova sempre. Acerta só nas vidas em que o sorteio cair nelas."""
    S, FIM = 7, 127
    L = [(S, "R", 7, 0), (2, 12, 9, 0), (S, FIM, 9, 0), ("R",)]
    # e0 e e2: g por bit (copiar ou negar); e1, e3: h = xou das três; e4: h(g(x0), x1, x2) ...; e5: g(h)
    op_g = 1 if gn == 0 else 2
    L += [(S, "RK0123", 6, 0), (S, "R4", 4, 0),
          (5, 15, 0, 1), (5, 15, 15, 2), (op_g, 15, 15, 0), (S, FIM, 9, 0),                                     # e5: g(a xou b xou c)
          ("R4",), (op_g, 11, 0, 0), (5, 15, 11, 1), (5, 15, 15, 2), (op_g, 11, 1, 0), (5, 14, 11, 2), (5, 14, 14, 3), (S, FIM, 9, 0),
          ("RK0123",), (S, "RK02", 4, 0), (S, "R1", 5, 0),
          (5, 15, 0, 1), (5, 15, 15, 2), (5, 14, 1, 2), (5, 14, 14, 3), (S, FIM, 9, 0),                         # e3
          ("R1",), (5, 15, 0, 1), (5, 15, 15, 2), (S, FIM, 9, 0),                                                 # e1
          ("RK02",), (S, "R0", 5, 0), (op_g, 15, 0, 0), (op_g, 14, 1, 0), (op_g, 13, 2, 0), (S, FIM, 9, 0),       # e2
          ("R0",), (op_g, 15, 0, 0), (S, FIM, 9, 0)]
    return VL._montar(L, P_V3C)


def ser_que_decora_v3c():
    """Decora cada situação de cada degrau: a resposta certa vai para a memória no endereço da própria situação (a entrada, o degrau e o bit de saída), sem regra nenhuma.
    Domina o que treinou e erra o que ficou retido e o e5; não sobe por dentro (nada passa de um degrau para outro). Pede a prova sempre."""
    S, FIM = 7, 127
    X = lambda r: (5, r, r, r)                                                # noqa: E731
    # o ponteiro de r0: r0 a r3 a entrada, r4 a r6 o degrau, r7 e r8 o bit de saída (0, 1 ou 2)
    L = [(S, "R", 7, 0),
         (1, 13, 8, 0), (1, 14, 9, 0), (1, 15, 10, 0), X(7), X(8), X(9), X(10),
         (9, 13, 0, 0), (2, 7, 9, 0), (9, 14, 0, 0), X(7), (2, 8, 9, 0), (9, 15, 0, 0),
         (2, 12, 9, 0), (S, FIM, 9, 0),
         ("R",),
         (8, 15, 0, 0), (2, 7, 9, 0), (8, 14, 0, 0), X(7), (2, 8, 9, 0), (8, 13, 0, 0), (S, FIM, 9, 0)]
    return VL._montar(L, P_V3C)


def ser_que_le_a_resposta_v3c():
    """Copia a resposta certa (r8 a r10) para a saída em toda fase, e pede a prova sempre. Na fase de responder, r8 a r10 são zero: ele só responde zeros."""
    S, FIM = 7, 127
    L = [(1, 15, 8, 0), (1, 14, 9, 0), (1, 13, 10, 0), (2, 12, 11, 0), (S, FIM, 11, 0)]
    return VL._montar(L, P_V3C)

