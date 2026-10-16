"""O juiz da vida v3 completa em C (`vida_v3c_c.c`; 03/10/2026). As mesmas vidas de `vida_v3c` (a referência), bit a bit; o plano de cada vida (situações, alvos, treinadas,
retidas, sequência) é montado aqui uma vez por semente e guardado. Compilado com o gcc na primeira vez, guardado por hash da fonte e da máquina."""
import ctypes
import functools
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile

import numpy as np

from experimentos import vida_v3c as V

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, "vida_v3c_c.c")
FLAGS = ["-O3", "-march=native", "-ffp-contract=off", "-fopenmp", "-shared", "-fPIC", "-std=c99"]   # (03/10) -fopenmp: as 16 vidas de uma medida em paralelo (VIDA_FIOS)
_LIB = None
CAMPOS = 15


def _chave():
    h = hashlib.sha256()
    h.update(open(FONTE, "rb").read())
    h.update(" ".join(FLAGS).encode())
    h.update(subprocess.run(["gcc", "--version"], capture_output=True, text=True).stdout.encode())
    h.update(platform.machine().encode())
    return h.hexdigest()[:20]


def compilar(forcar=False):
    pasta = os.environ.get("VIDA_C_CACHE") or os.path.join(tempfile.gettempdir(), "vida_no_leito_c_cache")
    os.makedirs(pasta, exist_ok=True)
    alvo = os.path.join(pasta, f"libv3c_{_chave()}.so")
    if os.path.exists(alvo) and not forcar:
        return alvo
    tmp = f"{alvo}.{os.getpid()}.tmp"
    r = subprocess.run(["gcc", *FLAGS, "-o", tmp, FONTE], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("a compilação da v3 completa em C falhou:\n" + r.stderr[-3000:])
    try:
        os.replace(tmp, alvo)
    except OSError:                       # no Windows, outro processo já carregou a mesma biblioteca (compilaram juntos): vale a dele
        if not os.path.exists(alvo):
            raise
        os.remove(tmp)
    return alvo


def biblioteca():
    global _LIB
    if _LIB is None:
        alvo = compilar()
        if os.name == "nt" and shutil.which("gcc"):                            # no Windows, a libgomp e a winpthread moram junto do gcc
            os.add_dll_directory(os.path.dirname(shutil.which("gcc")))
        lib = ctypes.CDLL(alvo)
        lib.vida.restype = ctypes.c_int
        lib.vida.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_int, ctypes.c_void_p]
        lib.medida.restype = ctypes.c_int
        lib.medida.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        lib.lembrar.restype = None
        lib.lembrar.argtypes = [ctypes.c_int]
        lib.julgar_c1.restype = ctypes.c_int
        lib.julgar_c1.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        lib.semente_do_programa.restype = ctypes.c_uint64
        lib.semente_do_programa.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.fios.restype = None
        lib.fios.argtypes = [ctypes.c_int]
        lib.sal_c.restype = None
        lib.sal_c.argtypes = [ctypes.c_uint64]
        lib.sal_atual.restype = ctypes.c_uint64
        lib.sal_atual.argtypes = []
        lib.sonda_c.restype = ctypes.c_uint64
        lib.sonda_c.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        lib.fios(int(os.environ.get("VIDA_FIOS", "1")))
        lib.sonda_ligada.argtypes = [ctypes.c_int]
        lib.janela.argtypes = [ctypes.c_int]
        lib.regua_v32.argtypes = [ctypes.c_int]
        lib.regua_v32(1 if os.environ.get("VIDA_REGUA_V32", "0") == "1" else 0)     # (04/10) a régua v3c.2: a soma antes da razão na subida; desligada por padrão
        lib.janela(int(os.environ.get("VIDA_JANELA", "0") or 0))           # (04/10) 1: o índice direto (10 e 11); 2: e o generalizado (12 e 13); desligado por padrão
        lib.sonda_ligada(int(os.environ.get("VIDA_SONDA", "1")))
        lib.familia.argtypes = [ctypes.c_int]
        lib.familia(int(os.environ.get("VIDA_FAMILIA", "0") or 0))
        if int(os.environ.get("VIDA_FAMILIA", "0") or 0) == 3:                  # (05/10) a família sorteada: os MESMOS bytes que o Python interpreta (familia_sorteada.codificar)
            from experimentos import familia_sorteada as FS
            tb = np.ascontiguousarray(FS.codificar(FS.carregar(os.environ["VIDA_FAMILIA_TABELA"])), np.uint8)
            lib.familia_tabela.argtypes = [ctypes.c_void_p]
            lib.familia_tabela(tb.ctypes.data)
            lib._tabela_da_familia = tb     # (05/10) a família de D: 0 o leito de sempre, 1 "espelho", 2 "deslocada" (vida_v3c_c.c, alvo_c)           # (depuração) 0 só para medir o custo da sonda numa cópia                      # quantos fios correm as 16 vidas de uma medida (1 = em série, como antes)
        _LIB = lib
    return _LIB


@functools.lru_cache(maxsize=None)
def _plano(semente, i, tipo):
    """O plano de uma vida: tipo "vida", "c2", "c4" ou "c5". Devolve (cab, X, Y, idx, reteste, as etapas)."""
    gn, t, gn2, t2 = V.primitivas(semente, i)
    verd, troc = (gn, t), (gn2, t2)
    if tipo == "vida":
        etapas = [(k, verd, False, True) for k in V.TREINADOS] + [(V.NUNCA_TREINADO, verd, True, False)]
        reteste = 1
    elif tipo == "c2":
        etapas = [(0, troc, False, False), (1, troc, False, False), (2, verd, False, False)]
        reteste = 0
    elif tipo == "c4":
        etapas = [(0, troc, False, False), (1, troc, False, False), (2, troc, False, False), (3, troc, False, False), (4, verd, False, False)]
        reteste = 0
    else:
        etapas = [(0, troc, False, False), (1, troc, False, False), (V.NUNCA_TREINADO, troc, True, False)]
        reteste = 0
    cab, X, Y, idx = [], [], [], []
    for k, (g_, t_), so_teste, prova in etapas:
        todas, treino, retidas = V.situacoes(semente, i, k)
        pos = {x: j for j, x in enumerate(todas)}
        n_in, n_out = V.N_ENTRADAS[k], len(V.alvo(k, todas[0], g_, t_))
        dX, dY = len(X), len(Y)
        for x in todas:
            X += list(x)
            Y += list(V.alvo(k, x, g_, t_))
        seq = [] if so_teste else [pos[x] for x in V.sequencia_de_treino(semente, i, k)]
        tr, rt, td = [pos[x] for x in treino], [pos[x] for x in retidas], list(range(len(todas)))
        d_tr = len(idx); idx += tr
        d_rt = len(idx); idx += rt
        d_sq = len(idx); idx += seq
        d_td = len(idx); idx += td
        cab += [k, int(so_teste), int(prova), n_in, n_out, len(todas), dX, dY, len(tr), d_tr, len(rt), d_rt, len(seq), d_sq, d_td]
        if so_teste:                                                           # o e5 não tem treinadas nem retidas para o teste
            cab[-7], cab[-5] = 0, 0
    arr = (np.array(cab, np.int32), np.array(X, np.uint8), np.array(Y, np.uint8), np.array(idx + [0], np.int32))
    for a in arr:
        a.setflags(write=False)
    return arr + (reteste, tuple((k, so_teste) for k, _p, so_teste, _pr in etapas))


def _viver(b, semente, i, tipo):
    cab, X, Y, idx, reteste, etapas = _plano(semente, i, tipo)
    ne = len(etapas)
    out = np.zeros(9 * ne + 2, np.int32)
    d = lambda a: a.ctypes.data                                               # noqa: E731
    r = biblioteca().vida(d(b), V.P_V3C, V.BITS_DO_SALTO_V3C, V.TETO, ne, d(cab), d(X), d(Y), d(idx), reteste, d(out))
    if r != 0:
        raise RuntimeError(f"a vida v3c em C recusou ({r})")
    o = out.tolist()
    reg = {"antes": {}, "depois_treinadas": {}, "depois_retidas": {}, "erros_de_treino": {}, "pediu": {}, "prova_passou": {}, "parados": {}, "fim": {}}
    for e, (k, so_teste) in enumerate(etapas):
        c = cab[CAMPOS * e: CAMPOS * (e + 1)].tolist()
        n_todas, n_tr, n_rt = c[5], c[8], c[10]
        oe = o[9 * e: 9 * e + 9]
        reg["parados"][k] = oe[7]
        if so_teste:
            reg["e5"] = oe[6] / n_todas
        else:
            reg["antes"][k] = oe[0] / n_todas
            reg["erros_de_treino"][k] = oe[1]
            reg["pediu"][k] = bool(oe[2])
            reg["prova_passou"][k] = (None if oe[3] < 0 else bool(oe[3]))
            reg["depois_treinadas"][k] = oe[4] / n_tr if n_tr else 1.0
            reg["depois_retidas"][k] = oe[5] / n_rt if n_rt else None
        if reteste:
            reg["fim"][k] = oe[8] / n_todas
    reg["fases"], reg["nao_pararam"] = o[9 * ne], o[9 * ne + 1]
    return reg


def _valores(vida, ctrl):
    """As contas de `vida_v3c.valores_de_uma_vida`, com os parados já contados."""
    graus = list(V.TREINADOS) + [V.NUNCA_TREINADO]
    val = [sum(vida["parados"][k] for k in graus) / len(graus)]
    val += [1.0 - vida["depois_treinadas"][k] for k in V.TREINADOS]
    val += [float(np.mean([1.0 - vida["fim"][k] for k in graus]))]
    for k in (2, 4):
        e_vida, e_ctrl = vida["erros_de_treino"][k], ctrl[k]["erros_de_treino"][k]
        ganho = (e_ctrl - e_vida) / max(1, e_ctrl)
        falta = float(max(0.0, V.MARGEM_DA_SUBIDA - ganho)) / V.MARGEM_DA_SUBIDA
        falta = max(falta, max(1.0 - x for x in ctrl[k]["depois_treinadas"].values()))
        val.append(falta)
    val.append(sum(1 for k in V.TREINADOS if not vida["pediu"][k]) / len(V.TREINADOS))
    pedidos = [k for k in V.TREINADOS if vida["pediu"][k]]
    val.append(sum(1 for k in pedidos if not vida["prova_passou"][k]) / len(pedidos) if pedidos else 0.0)
    val.append(float(np.mean([1.0 - vida["depois_retidas"][k] for k in (2, 3, 4)])))
    val.append(1.0 - vida["e5"])
    val.append(1.0 - ctrl[5]["e5"])
    fases = vida["fases"] + sum(c["fases"] for c in ctrl.values())
    nao = vida["nao_pararam"] + sum(c["nao_pararam"] for c in ctrl.values())
    val.append(nao / max(1, fases))
    return val


def julgar(bits, semente=V.SEMENTE_DA_VIDA):
    """Os valores das cláusulas (a média das vidas) e, para a foto comportamental, as respostas resumidas (os acertos por etapa de cada vida), direto dos bits do programa."""
    b = np.ascontiguousarray(np.asarray(bits, np.uint8))
    por_vida, resumo = [], []
    for i in range(V.VIDAS):
        vida = _viver(b, semente, i, "vida")
        ctrl = {2: _viver(b, semente, i, "c2"), 4: _viver(b, semente, i, "c4"), 5: _viver(b, semente, i, "c5")}
        por_vida.append(_valores(vida, ctrl))
        resumo += [vida["erros_de_treino"][k] for k in V.TREINADOS] + [int(round(100 * vida["depois_retidas"][k])) for k in (2, 3, 4)]
    valores = [float(np.mean([pv[c] for pv in por_vida])) for c in range(len(V.CLAUSULAS_V3C))]
    return valores, resumo


# ------------------------------------------------------------------ (a velocidade) a medida inteira numa chamada
_TIPOS = ("vida", "c2", "c4", "c5")


@functools.lru_cache(maxsize=None)
def _planos_da_medida(semente):
    """Os 16 planos de uma medida (4 vidas, cada uma com a vida e os três controles), os ponteiros para o C e, por plano, as etapas e os tamanhos."""
    planos = [(i, tipo, _plano(semente, i, tipo)) for i in range(V.VIDAS) for tipo in _TIPOS]
    ptrs = (ctypes.c_void_p * (4 * len(planos)))(*[a.ctypes.data for _i, _t, pl in planos for a in pl[:4]])
    nes = np.array([len(pl[5]) for _i, _t, pl in planos], np.int32)
    retestes = np.array([pl[4] for _i, _t, pl in planos], np.int32)
    nes.setflags(write=False)
    retestes.setflags(write=False)
    total = int(sum(9 * n + 2 for n in nes))
    return planos, ptrs, nes, retestes, total


def _registro(o, pos, pl):
    cab, _X, _Y, _idx, reteste, etapas = pl
    reg = {"antes": {}, "depois_treinadas": {}, "depois_retidas": {}, "erros_de_treino": {}, "pediu": {}, "prova_passou": {}, "parados": {}, "fim": {}}
    for e, (k, so_teste) in enumerate(etapas):
        c = cab[CAMPOS * e: CAMPOS * (e + 1)]
        n_todas, n_tr, n_rt = int(c[5]), int(c[8]), int(c[10])
        oe = o[pos + 9 * e: pos + 9 * e + 9]
        reg["parados"][k] = oe[7]
        if so_teste:
            reg["e5"] = oe[6] / n_todas
        else:
            reg["antes"][k] = oe[0] / n_todas
            reg["erros_de_treino"][k] = oe[1]
            reg["pediu"][k] = bool(oe[2])
            reg["prova_passou"][k] = (None if oe[3] < 0 else bool(oe[3]))
            reg["depois_treinadas"][k] = oe[4] / n_tr if n_tr else 1.0
            reg["depois_retidas"][k] = oe[5] / n_rt if n_rt else None
        if reteste:
            reg["fim"][k] = oe[8] / n_todas
    ne = len(etapas)
    reg["fases"], reg["nao_pararam"] = o[pos + 9 * ne], o[pos + 9 * ne + 1]
    return reg


def julgar_rapido(bits, semente=V.SEMENTE_DA_VIDA, lembrar=True):
    """O mesmo que `julgar`, numa chamada ao C, com as fases repetidas lembradas (`lembrar=False`: roda todas, para conferir)."""
    planos, ptrs, nes, retestes, total = _planos_da_medida(int(semente))
    b = np.ascontiguousarray(np.asarray(bits, np.uint8))
    out = np.zeros(total, np.int32)
    lib = biblioteca()
    lib.lembrar(1 if lembrar else 0)
    r = lib.medida(b.ctypes.data, V.P_V3C, V.BITS_DO_SALTO_V3C, V.TETO, len(planos), ctypes.cast(ptrs, ctypes.c_void_p), nes.ctypes.data, retestes.ctypes.data, out.ctypes.data)
    if r != 0:
        raise RuntimeError(f"a medida v3c em C recusou ({r})")
    o = out.tolist()
    pos, regs = 0, {}
    for (i, tipo, pl), ne in zip(planos, nes.tolist()):
        regs[(i, tipo)] = _registro(o, pos, pl)
        pos += 9 * ne + 2
    por_vida, resumo = [], []
    for i in range(V.VIDAS):
        vida = regs[(i, "vida")]
        ctrl = {2: regs[(i, "c2")], 4: regs[(i, "c4")], 5: regs[(i, "c5")]}
        por_vida.append(_valores(vida, ctrl))
        resumo += [vida["erros_de_treino"][k] for k in V.TREINADOS] + [int(round(100 * vida["depois_retidas"][k])) for k in (2, 3, 4)]
    valores = [float(np.mean([pv[c] for pv in por_vida])) for c in range(len(V.CLAUSULAS_V3C))]
    return valores, resumo


# ------------------------------------------------------------------ a versão 3c.1 (`vida_v3c1`): a medida inteira no C, as vidas geradas pela semente do programa
def sonda_c1(bits):
    """(régua 4) A assinatura do comportamento (a referência é `vida_v3c1.sonda`)."""
    b = np.ascontiguousarray(np.asarray(bits, np.uint8))
    return int(biblioteca().sonda_c(b.ctypes.data, V.P_V3C, V.BITS_DO_SALTO_V3C, V.TETO))


def julgar_c1(bits, semente=None, lembrar=True, sal=None):
    """(os 15 valores, a distância, o resumo de 48 inteiros) da v3c.1, numa chamada; `semente` None = a do próprio programa (a busca), um número = o banco. O resumo: por vida
    (8 cada) os erros de treino do e0 ao e4 e o acerto nas retidas do e2 ao e4; depois, por vida (4 cada), as duas partes do c8: os erros no e4 na vida e no controle c4, e quantos
    degraus de baixo o controle domina."""
    b = np.ascontiguousarray(np.asarray(bits, np.uint8))
    val = np.zeros(15, np.float64)
    res = np.zeros(48, np.int32)
    dist = np.zeros(1, np.int32)
    lib = biblioteca()
    lib.lembrar(1 if lembrar else 0)
    antes = None
    if sal is not None:                                                     # (régua 4) o sal desta medida, e o da ilha de volta depois
        antes = int(lib.sal_atual())
        lib.sal_c(int(sal) & ((1 << 64) - 1))
    try:
        r = lib.julgar_c1(b.ctypes.data, V.P_V3C, V.BITS_DO_SALTO_V3C, V.TETO, int(semente or 0), 0 if semente is None else 1, val.ctypes.data, res.ctypes.data, dist.ctypes.data)
    finally:
        if antes is not None:
            lib.sal_c(antes)
    if r != 0:
        raise RuntimeError(f"a medida v3c.1 em C recusou ({r})")
    return val.tolist(), int(dist[0]), res.tolist()


# ------------------------------------------------------------------ a ilha em C da v3c.1 (a evo inteira no C; o Python só grava e migra)
BANCO = tuple(range(1001, 1011))
_U8, _I32, _I64 = ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_int32), ctypes.c_long


def _ligar_ilha(lib):
    if getattr(lib, "_ilha_ligada", False):
        return lib
    P = ctypes.c_void_p
    for nome, res, args in (("ilha_iniciar", None, [ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int]), ("ilha_andar", ctypes.c_int, [ctypes.c_long]),
                            ("ilha_n", ctypes.c_long, []), ("ilha_melhor", ctypes.c_int32, [P]), ("ilha_recorde", None, [ctypes.c_int, P, P, P]),
                            ("ilha_tamanho", ctypes.c_int, []), ("ilha_indiv", None, [ctypes.c_int, P, P, P]), ("ilha_inserir", None, [P, ctypes.c_int32, ctypes.c_int32]),
                            ("ilha_confirmar", None, [ctypes.c_int]), ("ilha_sortear", None, [ctypes.c_int]), ("ilha_cabeca", ctypes.c_int, []),
                            ("ilha_estado", None, [P, P, P, P]), ("ilha_restaurar", None, [P, ctypes.c_long, ctypes.c_int32, P, ctypes.c_int32]), ("ilha_esvaziar", None, []),
                            ("ilha_recalibrar", ctypes.c_int32, []), ("ilha_selecao", None, [ctypes.c_int]), ("ilha_remedidas", ctypes.c_long, []),
                            ("ilha_confirmar_forte", None, [ctypes.c_int]), ("ilha_recorde_mais", None, [ctypes.c_int, P, P, P]), ("ilha_epoca", ctypes.c_long, [])):
        f = getattr(lib, nome)
        f.restype = res
        f.argtypes = args
    lib._ilha_ligada = True
    return lib


def _faixa_e(e):
    return 0 if e == 0 else (1 if e <= 4 else (2 if e <= 16 else 3))


def _faixa_r(r):
    return 0 if r == 0 else (1 if r < 50 else (2 if r < 100 else 3))


def familia_c1(bits):
    """A família de um programa da v3c.1 pelo comportamento, nas vidas dele: por vida, a faixa de erros de treino de cada degrau e a de acerto nas retidas; e (03/10, o Fable:
    "a seleção vê as partes") as duas partes do c8 por vida: se a vida erra menos que o controle no e4 e quantos degraus de baixo o controle domina."""
    _v, _d, resumo = julgar_c1(bits)
    base = tuple((_faixa_e(x) if j % 8 < 5 else _faixa_r(x)) for j, x in enumerate(resumo[:32]))
    c8 = tuple(v for i in range(4) for v in (int(resumo[32 + 4 * i + 1] > resumo[32 + 4 * i]), int(resumo[32 + 4 * i + 2])))
    return base + c8


def banco_c1(bits):
    """A distância média e a pior no banco (10 sementes que a busca não controla)."""
    ds = [julgar_c1(bits, s)[1] for s in BANCO]
    return round(float(np.mean(ds)), 1), int(max(ds))


DESENVOLVIMENTO = tuple(range(2001, 2011))


def dev_c1(bits):
    """(régua 4) A distância média no desenvolvimento (as 10 sementes 2001 a 2010, que decidem molde, recorde e migrante)."""
    return round(float(np.mean([julgar_c1(bits, s)[1] for s in DESENVOLVIMENTO])), 1)


def regua4_c1(bits, epoca):
    """(régua 4) Os números de um recorde: a pior de três da época (as vidas do comportamento com o sal da época e as duas sementes do desenvolvimento da época) com os 15
    valores dela (por cláusula, a pior das três); a média no desenvolvimento com os 15 valores médios; e no banco a média, a pior e os 15 valores médios."""
    b = np.ascontiguousarray(np.asarray(bits, np.uint8))
    e = max(int(epoca), 0)
    tres = [julgar_c1(b, sal=e), julgar_c1(b, DESENVOLVIMENTO[e % 10]), julgar_c1(b, DESENVOLVIMENTO[(e + 5) % 10])]
    vd = [julgar_c1(b, s) for s in DESENVOLVIMENTO]
    vb = [julgar_c1(b, s) for s in BANCO]
    return {"pior3": max(m[1] for m in tres), "valores": [round(max(m[0][c] for m in tres), 4) for c in range(15)],
            "dev": round(float(np.mean([m[1] for m in vd])), 1), "valores_dev": [round(float(np.mean([m[0][c] for m in vd])), 4) for c in range(15)],
            "banco": round(float(np.mean([m[1] for m in vb])), 1), "banco_pior": int(max(m[1] for m in vb)),
            "valores_banco": [round(float(np.mean([m[0][c] for m in vb])), 4) for c in range(15)]}


def regua3_c1(bits):
    """(03/10) Os números de um recorde na régua nova: os 15 valores da busca (por cláusula, a pior das 3 sementes: a do programa, mais um e mais dois), a distância da pior das
    3, e no banco a distância média, a pior e os 15 valores médios."""
    lib = biblioteca()
    b = np.ascontiguousarray(np.asarray(bits, np.uint8))
    ch = int(lib.semente_do_programa(b.ctypes.data, V.P_V3C)) or 1
    medidas = [julgar_c1(b)] + [julgar_c1(b, (ch + q) & ((1 << 64) - 1)) for q in (1, 2)]
    vb = [julgar_c1(b, s) for s in BANCO]
    return {"distancia_3": max(m[1] for m in medidas), "valores": [round(max(m[0][c] for m in medidas), 4) for c in range(15)],
            "banco": round(float(np.mean([m[1] for m in vb])), 1), "banco_pior": int(max(m[1] for m in vb)),
            "valores_banco": [round(float(np.mean([m[0][c] for m in vb])), 4) for c in range(15)]}


class IlhaC:
    """A ilha da v3c.1 com a evo inteira no C (a interface de `bancada_c2.ilhas.Ilha`): `andar` recebe os migrantes, anda as medidas da época em blocos de 50 mil (o andamento
    gravado a cada bloco), grava cada recorde (só de confirmados) com o banco ao lado, e devolve as melhores de cada família. O estado (a população, o sorteador, o melhor) fica em
    estado.pkl a cada época; a tabela das medidas recomeça na retomada."""

    def __init__(self, semente, pasta, populacao=64, torneio=8, selecao="torneio"):
        import pickle
        self.lib = _ligar_ilha(biblioteca())
        self.semente, self.pasta, self.selecao = int(semente), pasta, selecao
        os.makedirs(pasta, exist_ok=True)
        self.lib.ilha_iniciar(ctypes.c_uint64((self.semente * 0x9E3779B97F4A7C15 + 7) & ((1 << 64) - 1)), int(populacao), int(torneio), V.TETO)
        self.lib.ilha_selecao(1 if selecao == "lexicase" else 0)
        est = os.path.join(pasta, "estado.pkl")
        if os.path.exists(est):
            e = pickle.load(open(est, "rb"))
            for b, d, c in e["pop"]:
                bb = np.ascontiguousarray(np.unpackbits(b)[: 16 * V.P_V3C])
                self.lib.ilha_inserir(bb.ctypes.data, int(d), int(c))
            rng = np.array(e["rng"], np.uint64)
            mb = np.ascontiguousarray(np.unpackbits(e["melhor_bits"])[: 16 * V.P_V3C]) if e.get("melhor_bits") is not None else np.zeros(16 * V.P_V3C, np.uint8)
            self.lib.ilha_restaurar(rng.ctypes.data, int(e["n"]), int(e["melhor"]), mb.ctypes.data, 0)
            if e.get("regua") != 4 and int(e["melhor"]) < (1 << 30):        # (03/10) a régua 4: o melhor herdado medido no desenvolvimento, marcado no registro
                novo = int(self.lib.ilha_recalibrar())
                bits = np.zeros(16 * V.P_V3C, np.uint8)
                self.lib.ilha_melhor(bits.ctypes.data)
                r4 = regua4_c1(bits, int(e["n"]) // 10000)
                assert abs(r4["dev"] - novo / 10) < 1e-6, (r4["dev"], novo)
                with open(os.path.join(pasta, "recordes.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"medida": int(e["n"]), "distancia": r4["dev"], "pior3": r4["pior3"], "banco": r4["banco"], "banco_pior": r4["banco_pior"], "regua": 4,
                                        "valores": r4["valores"], "valores_dev": r4["valores_dev"], "valores_banco": r4["valores_banco"],
                                        "evento": f"régua 4 (comportamento, sal e desenvolvimento): o melhor herdado ({int(e['melhor'])} na régua {e.get('regua', 1)}) medido de novo"}) + chr(10))
                self._gravar("melhor.json", {"distancia": r4["dev"], "medida": int(e["n"]), "bits": "".join(str(int(x)) for x in bits), "semente": self.semente, "d": "v3c1",
                                             "banco": r4["banco"], "banco_pior": r4["banco_pior"], "regua": 4})

    def _gravar(self, nome, obj):
        tmp = os.path.join(self.pasta, nome + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline=chr(10)) as f:
            json.dump(obj, f)
        os.replace(tmp, os.path.join(self.pasta, nome))

    def _populacao(self):
        """(bits, d, conf) da população, da mais velha para a mais nova."""
        n, cab = self.lib.ilha_tamanho(), self.lib.ilha_cabeca()
        out = []
        for j in range(n):
            i = (cab + j) % n
            b = np.zeros(16 * V.P_V3C, np.uint8)
            d, c = np.zeros(1, np.int32), np.zeros(1, np.int32)
            self.lib.ilha_indiv(i, b.ctypes.data, d.ctypes.data, c.ctypes.data)
            out.append((i, b, int(d[0]), int(c[0])))
        return out

    def andar(self, medidas, teto, migrantes=(), sorteados=0):
        import pickle
        lib = self.lib
        for bits, d in migrantes:
            b = np.ascontiguousarray(np.array([int(c) for c in bits], np.uint8))
            lib.ilha_inserir(b.ctypes.data, int(d), 2)
        if sorteados:
            lib.ilha_sortear(int(sorteados))
        alvo = min(lib.ilha_n() + int(medidas), int(teto))
        while lib.ilha_n() < alvo:
            bloco = min(lib.ilha_n() + 50_000, alvo)
            nrec = lib.ilha_andar(int(bloco))
            for i in range(nrec):
                n_, d_, b = np.zeros(1, np.int64), np.zeros(1, np.int32), np.zeros(16 * V.P_V3C, np.uint8)
                ep, d3, epd = np.zeros(1, np.int64), np.zeros(1, np.int32), np.zeros(1, np.float64)
                lib.ilha_recorde(i, n_.ctypes.data, d_.ctypes.data, b.ctypes.data)
                lib.ilha_recorde_mais(i, ep.ctypes.data, d3.ctypes.data, epd.ctypes.data)
                r4 = regua4_c1(b, int(ep[0]))
                bits = "".join(str(int(x)) for x in b)
                with open(os.path.join(self.pasta, "recordes.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"medida": int(n_[0]), "distancia": int(d_[0]) / 10, "erro_padrao": round(float(epd[0]) / 10, 1), "pior3": int(d3[0]), "epoca": int(ep[0]), "banco": r4["banco"],
                                        "banco_pior": r4["banco_pior"], "regua": 4, "regua_v32": os.environ.get("VIDA_REGUA_V32", "0") == "1", "valores": r4["valores"], "valores_dev": r4["valores_dev"],
                                        "valores_banco": r4["valores_banco"]}) + chr(10))
                self._gravar("melhor.json", {"distancia": int(d_[0]) / 10, "medida": int(n_[0]), "bits": bits, "semente": self.semente, "d": "v3c1", "banco": r4["banco"],
                                             "banco_pior": r4["banco_pior"], "regua": 4})
            mb = np.zeros(16 * V.P_V3C, np.uint8)
            self._gravar("progresso.json", {"medida": int(lib.ilha_n()), "melhor": int(lib.ilha_melhor(mb.ctypes.data)) / 10, "remedidas": int(lib.ilha_remedidas()),
                                            "selecao": self.selecao, "epoca_do_sal": int(lib.ilha_epoca())})
            if lib.ilha_melhor(mb.ctypes.data) == 0:
                break
        pop = self._populacao()
        familias = {}
        for i, b, d, c in sorted(pop, key=lambda x: x[2])[:16]:               # as melhores de cada família, confirmadas no nível 2 (a pior de três) antes de sair
            if c < 2:
                lib.ilha_confirmar_forte(i)
                bb, dd, cc = np.zeros(16 * V.P_V3C, np.uint8), np.zeros(1, np.int32), np.zeros(1, np.int32)
                lib.ilha_indiv(i, bb.ctypes.data, dd.ctypes.data, cc.ctypes.data)
                d = int(dd[0])
            s_ = familia_c1(b)
            if s_ not in familias or d < familias[s_][1]:
                familias[s_] = ("".join(str(int(x)) for x in b), d)
        mb = np.zeros(16 * V.P_V3C, np.uint8)
        melhor = int(lib.ilha_melhor(mb.ctypes.data))
        rng, n_, m_, cab = np.zeros(4, np.uint64), np.zeros(1, np.int64), np.zeros(1, np.int32), np.zeros(1, np.int32)
        lib.ilha_estado(rng.ctypes.data, n_.ctypes.data, m_.ctypes.data, cab.ctypes.data)
        estado = {"pop": [(np.packbits(b), d, c) for _i, b, d, c in self._populacao()], "rng": [int(x) for x in rng], "n": int(n_[0]), "melhor": int(m_[0]), "regua": 4,
                  "selecao": self.selecao,
                  "melhor_bits": np.packbits(mb) if melhor < (1 << 30) else None}
        pickle.dump(estado, open(os.path.join(self.pasta, "estado.pkl.tmp"), "wb"))
        os.replace(os.path.join(self.pasta, "estado.pkl.tmp"), os.path.join(self.pasta, "estado.pkl"))
        sig_melhor = familia_c1(mb) if melhor < (1 << 30) else None
        ultimo = 0
        rp = os.path.join(self.pasta, "recordes.jsonl")
        if os.path.exists(rp):
            linhas = open(rp, encoding="utf-8").read().splitlines()
            if linhas:
                ultimo = json.loads(linhas[-1])["medida"]
        return {"semente": self.semente, "n": int(lib.ilha_n()), "melhor": (melhor / 10 if melhor < (1 << 30) else None), "ultimo_recorde": ultimo, "familias": familias,
                "familia_do_melhor": sig_melhor, "cumpriu": melhor == 0}
