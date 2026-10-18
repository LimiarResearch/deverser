"""O tempo total da auditoria (resumo.segundos) e a soma dos tempos por caso: que paralelismo os torna compativeis?

Uso: python3 -I auditoria_tempo.py <auditoria_z3.json>
"""
import heapq, json, sys
a = json.load(open(sys.argv[1], encoding="utf-8"))
c = a["casos"]
ids = [x["id"] for x in c]
print("casos em ordem de id:", ids == sorted(ids))
s = [x["segundos"] for x in c]
sz = [x["segundos_z3"] for x in c]
print("soma segundos %.2f | soma segundos_z3 %.2f | resumo.segundos %.1f | max por caso %.2f" % (sum(s), sum(sz), a["resumo"]["segundos"], max(s)))
print("segundos >= segundos_z3 em", sum(1 for x in c if x["segundos"] >= x["segundos_z3"]), "de", len(c))
print("paralelismo minimo para caber em resumo.segundos: %.2f" % (sum(s) / a["resumo"]["segundos"]))
by = {x["id"]: x["segundos"] for x in c}
for P in (1, 2, 4, 5, 6, 8):
    livres = [0.0] * P
    heapq.heapify(livres)
    fim = 0
    for i in sorted(by):
        t = heapq.heappop(livres); t += by[i]; fim = max(fim, t); heapq.heappush(livres, t)
    print("P=%d: duracao simulada da fila %.1f s" % (P, fim))
# perguntas por desfecho
from collections import defaultdict
g = defaultdict(list)
for x in c: g[x["tipo_da_regra_f"]].append(x["perguntas_ao_z3"])
for k, v in g.items(): print("perguntas ao z3, %s: soma %d min %d max %d" % (k, sum(v), min(v), max(v)))
print("classes_no_limite distintos:", sorted({x["classes_no_limite"] for x in c}))
print("perguntas == classes_maximais + 3:", sum(1 for x in c if x["perguntas_ao_z3"] == x["classes_maximais"] + 3))
import collections
print("perguntas - classes_maximais:", collections.Counter(x["perguntas_ao_z3"] - x["classes_maximais"] for x in c))
print("por desfecho, perguntas - classes_maximais:", {k: dict(collections.Counter(x["perguntas_ao_z3"] - x["classes_maximais"] for x in c if x["tipo_da_regra_f"] == k)) for k in g})
