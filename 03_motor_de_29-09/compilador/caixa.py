"""A caixa onde roda o código que a IA propõe (modelos de cálculo, testes, exportação): um processo à parte, com tempo limite, sem
arquivo, rede ou processo, e só com as importações da lista.

  python -B -m compilador.caixa < lote.json > resultado.json

Um lote: {"codigo", "funcao", "p_base", "variacoes": [{...}], "candidatos": [{...}], "modo": "modelo" | "teste" | "exportar"}.
- modelo: para cada candidato e cada variação de Π, chama funcao(x, p) e guarda o dicionário que ela devolve (ou o erro);
- teste: chama funcao(calcular, p_base) de cada teste, onde calcular é o modelo do lote, e guarda (ok, detalhe);
- exportar: chama funcao(x, p, saidas) e guarda o dicionário devolvido.
Isto não é uma fronteira de segurança forte: o código vem do subagente desta sessão. A caixa existe para que um erro dele não quebre
o motor, e para que tempo e importações fiquem sob regra.
"""
import builtins
import json
import math
import sys
import time
import traceback

PERMITIDOS = {"math", "cmath", "statistics", "itertools", "functools", "numpy", "random", "bisect", "heapq", "collections", "fractions",
              "decimal", "operator"}
SEGUROS = ("abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int", "isinstance", "len", "list", "map", "max", "min",
           "pow", "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip", "ValueError", "ZeroDivisionError",
           "Exception", "ArithmeticError", "KeyError", "IndexError", "TypeError", "divmod", "frozenset", "hasattr", "getattr", "print",
           "True", "False", "None", "object", "iter", "next", "slice", "complex", "OverflowError", "StopIteration", "NotImplementedError")


def _importar(nome, *a, **k):
    raiz = nome.split(".")[0]
    if raiz not in PERMITIDOS:
        raise ImportError(f"importação fora da lista: {nome}")
    return __import__(nome, *a, **k)


def ambiente():
    b = {n: getattr(builtins, n) for n in SEGUROS if hasattr(builtins, n)}
    b["__import__"] = _importar
    import numpy
    return {"__builtins__": b, "math": math, "np": numpy, "numpy": numpy}


def _limpo(v):
    """O que a função devolveu, em JSON: números do NumPy viram números, NaN e infinito viram texto."""
    try:
        import numpy
        if isinstance(v, numpy.generic):
            v = v.item()
        if isinstance(v, numpy.ndarray):
            v = v.tolist()
    except ImportError:
        pass
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return str(v)
    if isinstance(v, dict):
        return {str(k): _limpo(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_limpo(x) for x in v]
    return v


def compilar(codigo, funcao):
    g = ambiente()
    exec(compile(codigo, "<proposta>", "exec"), g)
    if funcao not in g:
        raise NameError(f"o código não define {funcao}")
    return g[funcao], g


def rodar(lote):
    t0 = time.perf_counter()
    modo = lote.get("modo", "modelo")
    out = {"resultados": [], "erro_de_compilacao": None}
    try:
        f, g = compilar(lote["codigo"], lote["funcao"])
    except Exception:  # noqa: BLE001
        out["erro_de_compilacao"] = traceback.format_exc(limit=3)[-1500:]
        return out
    if modo == "teste":
        calc, _ = compilar(lote["codigo_modelo"], lote.get("funcao_modelo", "calcular"))
        for nome in lote["testes"]:
            try:
                ft = g[nome]
                r = ft(calc, dict(lote["p_base"]))
                ok, det = (r if isinstance(r, tuple) else (bool(r), ""))
                out["resultados"].append({"teste": nome, "ok": bool(ok), "detalhe": _limpo(det)})
            except Exception:  # noqa: BLE001
                out["resultados"].append({"teste": nome, "ok": False, "erro": traceback.format_exc(limit=2)[-800:]})
        out["segundos"] = round(time.perf_counter() - t0, 3)
        return out
    for x in lote["candidatos"]:
        linha = []
        for var in lote.get("variacoes") or [{}]:
            p = dict(lote["p_base"], **var)
            try:
                r = f(dict(x), p) if modo == "modelo" else f(dict(x), p, lote.get("saidas", {}).get(x.get("_id"), {}))
                linha.append({"ok": True, "saidas": _limpo(r)})
            except Exception as e:  # noqa: BLE001
                linha.append({"ok": False, "erro": f"{type(e).__name__}: {e}"[:400]})
        out["resultados"].append(linha)
    out["segundos"] = round(time.perf_counter() - t0, 3)
    return out


if __name__ == "__main__":
    sys.stdout.write(json.dumps(rodar(json.load(sys.stdin))))
