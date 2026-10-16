# -*- coding: utf-8 -*-
from dataclasses import dataclass
from experimentos import l_ser_lang as L

@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple = ()
    q: int = 0

def extrair(nos, tipo):
    entradas = L.ENTRADAS[tipo]
    memo = {}

    def rec(i):
        if i in memo:
            return memo[i]
        n = nos[i]
        ar = L.ARIDADE[n.op]
        aa = []
        for r in (n.a, n.b)[:ar]:
            aa.append(entradas[r] if r < len(entradas) else rec(r - len(entradas)))
        memo[i] = Expr(L.NOME_DA_OP[n.op], tuple(aa), n.c if L.USA_C[n.op] else 0)
        return memo[i]
    root = rec(L.K_NOS - 1)
    return (root, memo)

def para_e(e, memo=None):
    if isinstance(e, str):
        return e
    if memo is None:
        memo = {}
    if e not in memo:
        memo[e] = L.E(e.op, *(para_e(a, memo) for a in e.args), c=L.valor_da_constante(e.q) if L.USA_C[L.OP_DE[e.op]] else None)
    return memo[e]

def compilar(e, tipo='peso'):
    return L.compilar_secao(para_e(e), tipo)

def reencadernar(bits, secao, e):
    p = L.decodificar_bits(bits)
    tipo = L.TIPO_DA_SECAO[secao]
    secoes = {k: None if v is None else [L.No(*n.como_tupla()) for n in v] for k, v in p.secoes.items()}
    secoes[secao] = compilar(e, tipo)
    return L.codificar_programa(L.Programa(dict(p.tecido), secoes, dict(p.rotulos)))

def numero_nos(e):
    vistos = set()

    def rec(a):
        if isinstance(a, str) or a in vistos:
            return
        vistos.add(a)
        for b in a.args:
            rec(b)
    rec(e)
    return len(vistos)

def caminhos(e, prefixo=()):
    yield prefixo
    if isinstance(e, Expr):
        for i, a in enumerate(e.args):
            yield from caminhos(a, prefixo + (i,))

def no_em(e, caminho):
    for i in caminho:
        e = e.args[i]
    return e

def enxertar(e, caminho, f):
    if not caminho:
        return f
    if isinstance(e, str):
        raise ValueError('caminho atravessa uma entrada')
    i = caminho[0]
    args = list(e.args)
    args[i] = enxertar(args[i], caminho[1:], f)
    return Expr(e.op, tuple(args), e.q)
