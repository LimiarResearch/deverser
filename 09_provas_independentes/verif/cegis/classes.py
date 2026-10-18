"""Hipotese: no CEGIS, formulacoes - verificacoes = k x (classes de sensores dentro do limite), isto e, uma busca vazia por classe
(numero de estados de 1 a k, conjunto de sensores) da familia. classes_no_limite vem da auditoria do z3; k vem do rotulo.

Uso: python3 -I classes.py <resultados.jsonl> <auditoria_z3.json>
"""
import json, sys
from collections import Counter
L = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()}
A = {c["id"]: c for c in json.load(open(sys.argv[2], encoding="utf-8"))["casos"]}
for m in ("cegis_poda", "cegis"):
    t = Counter()
    exemplos = []
    for i, r in L.items():
        k = int(r["rotulo"].split("-")[3][1:])
        vazio = r[m]["formulacoes"] - r[m]["verificacoes"]
        alvo = k * A[i]["classes_no_limite"]
        chave = (r[m]["tipo"], vazio == alvo, vazio < alvo)
        t[chave] += 1
        if r[m]["tipo"] != "timeout" and vazio != alvo and len(exemplos) < 6:
            exemplos.append((i, r["rotulo"], r[m]["tipo"], vazio, k, A[i]["classes_no_limite"], A[i]["classes_maximais"]))
    print(m)
    for kk, v in sorted(t.items()):
        print("   desfecho=%-24s vazias==k*classes_no_limite=%s menor=%s : %d" % (kk[0], kk[1], kk[2], v))
    print("   exemplos fora da regra:", exemplos)
# na formula
t = Counter()
for i, r in L.items():
    t[(r["f"]["tipo"], r["f"]["formulacoes"] - r["f"]["verificacoes"])] += 1
print("f: (desfecho, formulacoes - verificacoes):", dict(sorted(t.items())))
t = Counter()
for i, r in L.items():
    t[(r["f"]["tipo"], r["f"]["formulacoes"] == A[i]["classes_maximais"], r["f"]["formulacoes"] == A[i]["classes_maximais"] + 1)] += 1
print("f: (desfecho, formulacoes == classes_maximais, == classes_maximais+1):", dict(sorted(t.items())))
