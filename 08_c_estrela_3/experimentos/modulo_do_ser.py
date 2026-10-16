# -*- coding: utf-8 -*-
import numpy as np
from experimentos.l_ser_lang import ARIDADE, ENTRADAS, K_NOS, N_ENTRADAS, N_OPS, NOMES_DAS_SECOES, OPS, TIPO_DA_SECAO, _CONSUMIDORES_DA_VOLTA, _POR_NOME, _VARS_DA_FENDA, _VARS_DA_VOLTA, _analisar, _escrever, _ler, canonizar_bits

def _modulos():
    out = []
    for cons in _CONSUMIDORES_DA_VOLTA:
        vs = tuple((v for v in _VARS_DA_VOLTA if v in ENTRADAS[TIPO_DA_SECAO[cons]]))
        if vs:
            out.append(('RETRO', cons, vs))
    for fenda, variaveis in _VARS_DA_FENDA.items():
        for cons in NOMES_DAS_SECOES:
            if cons == fenda:
                continue
            vs = tuple((v for v in variaveis if v in ENTRADAS[TIPO_DA_SECAO[cons]]))
            if vs:
                out.append((fenda, cons, vs))
    return tuple(out)
MODULOS = _modulos()
_OPS_QUE_LEEM = tuple((i for i, o in enumerate(OPS) if o[1] >= 1))

def _sortear_secao(b, nome, g):
    b[_POR_NOME[f'{nome}.presente']['inicio']] = 1
    for n in range(K_NOS):
        for campo in ('op', 'a', 'b', 'c'):
            c = _POR_NOME[f'{nome}.n{n}.{campo}']
            _escrever(b, c, int(g.integers(1 << c['bits'])))

def _transplantar_secao(b, nome, doadora, g):
    _, nos_d, vivos_d, _ = _analisar(np.asarray(doadora, np.uint8))
    vivas = [n for n in NOMES_DAS_SECOES if nos_d[n] is not None and n != nome]
    if not vivas:
        return False
    fonte = vivas[int(g.integers(len(vivas)))]
    t_src, t_dst = (TIPO_DA_SECAO[fonte], TIPO_DA_SECAO[nome])
    n_src, n_dst = (N_ENTRADAS[t_src], N_ENTRADAS[t_dst])
    b[_POR_NOME[f'{nome}.presente']['inicio']] = 1
    for n, no in enumerate(nos_d[fonte]):
        args = []
        for x in (no.a, no.b):
            if x < n_src:
                nomev = ENTRADAS[t_src][x]
                args.append(ENTRADAS[t_dst].index(nomev) if nomev in ENTRADAS[t_dst] else int(g.integers(n_dst)))
            else:
                args.append(n_dst + (x - n_src))
        _escrever(b, _POR_NOME[f'{nome}.n{n}.op'], no.op)
        _escrever(b, _POR_NOME[f'{nome}.n{n}.a'], args[0])
        _escrever(b, _POR_NOME[f'{nome}.n{n}.b'], args[1])
        _escrever(b, _POR_NOME[f'{nome}.n{n}.c'], no.c)
    return True

def _religar(b, cons, v, g):
    tipo = TIPO_DA_SECAO[cons]
    _, nos, vivos, _ = _analisar(b)
    ult = K_NOS - 1
    if nos[cons] is None:
        _sortear_secao(b, cons, g)
        n = ult
    else:
        vs_ = sorted(vivos[cons])
        n = vs_[int(g.integers(len(vs_)))]
    op = _ler(b, _POR_NOME[f'{cons}.n{n}.op']) % N_OPS
    if ARIDADE[op] < 1:
        _escrever(b, _POR_NOME[f'{cons}.n{n}.op'], _OPS_QUE_LEEM[int(g.integers(len(_OPS_QUE_LEEM)))])
    _escrever(b, _POR_NOME[f'{cons}.n{n}.a'], ENTRADAS[tipo].index(v))

def editar_modulo(bits, g, modo='cego', doadora=None):
    b = np.array(bits, np.uint8, copy=True)
    prod, cons, vs = MODULOS[int(g.integers(len(MODULOS)))]
    v = vs[int(g.integers(len(vs)))]
    if modo == 'cego':
        for nome in (prod, cons):
            _sortear_secao(b, nome, g)
        tipo = TIPO_DA_SECAO[cons]
        ult = K_NOS - 1
        _escrever(b, _POR_NOME[f'{cons}.n{ult}.op'], _OPS_QUE_LEEM[int(g.integers(len(_OPS_QUE_LEEM)))])
        _escrever(b, _POR_NOME[f'{cons}.n{ult}.a'], ENTRADAS[tipo].index(v))
        _escrever(b, _POR_NOME[f'{cons}.n{ult}.b'], N_ENTRADAS[tipo] + int(g.integers(ult)))
    elif modo == 'religado':
        _sortear_secao(b, prod, g)
        _religar(b, cons, v, g)
    elif modo == 'transplante':
        if doadora is None or not _transplantar_secao(b, prod, doadora, g):
            return (None, None)
        _religar(b, cons, v, g)
    else:
        raise ValueError(f'modo de módulo desconhecido: {modo}')
    filho = canonizar_bits(b)
    if filho is None or np.array_equal(filho, np.asarray(bits, np.uint8)):
        return (None, None)
    return (filho, (prod, cons, v))
