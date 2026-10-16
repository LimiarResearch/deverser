"""A avaliação dos candidatos pelos modelos que a IA propôs, sem confiar só neles.

- propagar: cada candidato é calculado no centro de Π e nos cantos dos intervalos dos números que têm incerteza (até 4 números:
  todos os cantos; mais que isso: o centro, os extremos de cada um e 16 pontos sorteados com semente fixa). A saída vira um intervalo;
- julgar: uma cláusula rígida passa quando o intervalo inteiro cumpre, falha quando nenhum ponto cumpre, e fica incerta no resto;
- testar: os testes de refutação rodam contra o modelo, e um teste que falha derruba a premissa;
- cruzar: o modelo alternativo calcula as mesmas saídas, e uma diferença acima da tolerância é discordância.
"""
import itertools
import json
import os
import random
import subprocess
import sys

from bancada.nucleo.artefato import RAIZ

LOTE = 400


def caixa(lote, timeout=600):
    """Roda um lote na caixa (compilador/caixa.py), num processo à parte."""
    r = subprocess.run([sys.executable, "-B", "-m", "compilador.caixa"], input=json.dumps(lote), capture_output=True, text=True, cwd=RAIZ,
                       timeout=timeout, env=dict(os.environ, PYTHONIOENCODING="utf-8", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1"))
    if r.returncode != 0:
        return {"erro_de_compilacao": None, "erro_de_execucao": r.stderr[-1500:], "resultados": []}
    return json.loads(r.stdout)


def variacoes(intervalos, semente=11):
    """As variações de Π a calcular: o centro primeiro, depois os cantos (ou a amostra)."""
    nomes = sorted(intervalos)
    out = [{}]
    if not nomes:
        return out
    if len(nomes) <= 4:
        for canto in itertools.product(*[(intervalos[n][0], intervalos[n][1]) for n in nomes]):
            out.append(dict(zip(nomes, canto)))
        return out
    for n in nomes:
        out += [{n: intervalos[n][0]}, {n: intervalos[n][1]}]
    r = random.Random(semente)
    for _ in range(16):
        out.append({n: r.uniform(*intervalos[n]) for n in nomes})
    return out


def propagar(codigo, candidatos, p_base, intervalos, timeout=900):
    """Para cada candidato: {saida: [mín, máx]} sobre as variações, o valor no centro, e os erros."""
    vs = variacoes(intervalos)
    out = []
    for a in range(0, len(candidatos), LOTE):
        parte = candidatos[a:a + LOTE]
        r = caixa({"codigo": codigo, "funcao": "calcular", "p_base": p_base, "variacoes": vs, "candidatos": parte, "modo": "modelo"}, timeout)
        if r.get("erro_de_compilacao") or r.get("erro_de_execucao"):
            return {"erro": r.get("erro_de_compilacao") or r.get("erro_de_execucao")}
        for x, linha in zip(parte, r["resultados"]):
            erros = [l["erro"] for l in linha if not l["ok"]]
            centro = linha[0]["saidas"] if linha and linha[0]["ok"] else None
            faixa = {}
            if not erros and isinstance(centro, dict):
                for k in centro:
                    vals = [l["saidas"].get(k) for l in linha]
                    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
                        faixa[k] = [min(vals), max(vals)]
            out.append({"id": x["_id"], "centro": centro, "faixa": faixa, "erros": erros[:3],
                        "fora_de_validade": bool(isinstance(centro, dict) and centro.get("_fora_de_validade"))})
    return {"avaliados": out, "variacoes": len(vs)}


def julgar(teste, centro, faixa):
    m = teste["medida"]
    if m not in (centro or {}):
        return "sem_medida"
    lo, hi = faixa.get(m, [centro[m], centro[m]])
    op, lim = teste["op"], teste["valor"]
    f = {"<=": lambda v: v <= lim, ">=": lambda v: v >= lim, "<": lambda v: v < lim, ">": lambda v: v > lim, "==": lambda v: v == lim}[op]
    a, b = f(lo), f(hi)
    return "passa" if a and b else ("falha" if not a and not b else "incerto")


def testar(codigo_modelo, testes, p_base, timeout=300):
    """Os testes de refutação: cada um é uma função teste_*(calcular, p) -> (ok, detalhe)."""
    if not testes:
        return []
    codigo = "\n\n".join(t["codigo"] for t in testes)
    nomes = [t["funcao"] for t in testes]
    r = caixa({"codigo": codigo, "funcao": nomes[0], "codigo_modelo": codigo_modelo, "testes": nomes, "p_base": p_base, "modo": "teste"}, timeout)
    if r.get("erro_de_compilacao") or r.get("erro_de_execucao"):
        return [{"teste": n, "ok": False, "erro": r.get("erro_de_compilacao") or r.get("erro_de_execucao")} for n in nomes]
    return r["resultados"]


def cruzar(a, b, saidas, tolerancia):
    """A discordância entre dois modelos, candidato a candidato: a diferença relativa no centro, por saída comum."""
    out = []
    ib = {x["id"]: x for x in b}
    for x in a:
        y = ib.get(x["id"])
        if not y or not isinstance(x["centro"], dict) or not isinstance(y["centro"], dict):
            continue
        for s in saidas:
            va, vb = x["centro"].get(s), y["centro"].get(s)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                rel = abs(va - vb) / max(abs(va), abs(vb), 1e-12)
                if rel > tolerancia.get(s, 0.10):
                    out.append({"id": x["id"], "saida": s, "modelo": va, "alternativo": vb, "diferenca_relativa": round(rel, 4)})
    return out
