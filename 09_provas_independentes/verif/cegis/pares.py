"""Coerencia entre os pares folgado/curto do mesmo problema (mesmo J, ordem, tipo e k).

Uso: python3 -I pares.py <resultados.jsonl>
"""
import json, sys
from collections import Counter, defaultdict
L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
par = defaultdict(dict)
for r in L:
    p = r["rotulo"].split("-")
    par[tuple(p[:4])][p[4]] = r
print("pares:", len(par), "| completos:", sum(1 for v in par.values() if set(v) == {"curto", "folgado"}))
print("ids do par sao consecutivos (folgado par, curto impar):",
      sum(1 for v in par.values() if v["folgado"]["id"] % 2 == 0 and v["curto"]["id"] == v["folgado"]["id"] + 1))
tab = Counter((v["folgado"]["f"]["tipo"], v["curto"]["f"]["tipo"]) for v in par.values())
print("desfecho f (folgado, curto):", dict(tab))
print("\nfolgado=solucao: custo folgado, custo curto, B curto, desfecho curto")
dc = []
for k, v in sorted(par.items()):
    a, b = v["folgado"], v["curto"]
    if a["f"]["tipo"] == "solucao":
        dc.append((a["f"]["custo"], b["f"]["custo"], b["B"], b["f"]["tipo"]))
incoer = [x for x in dc if x[3] == "over_budget" and x[0] <= x[2] * 0.9]
print(" curto=over_budget com custo do folgado bem abaixo de B (<= 0.9 B):", incoer)
print(" curto=solucao: custo curto <= B em todos:", all(x[1] <= x[2] for x in dc if x[3] == "solucao"))
dif = [x[1] - x[0] for x in dc if x[3] == "solucao"]
print(" diferenca de custo curto-folgado quando os dois tem solucao: n=%d min=%.2f max=%.2f" % (len(dif), min(dif), max(dif)))
ob = [(x[0], x[2]) for x in dc if x[3] == "over_budget"]
print(" curto=over_budget: (custo folgado, B curto):", sorted(ob))
print(" fracao custo_folgado/B_curto nos over_budget: min %.2f" % min(c / B for c, B in ob))
so = [(x[0], x[2]) for x in dc if x[3] == "solucao"]
print(" curto=solucao: max custo_folgado/B_curto %.2f" % max(c / B for c, B in so))
# estados e sensores iguais entre o par?
mesmo = sum(1 for v in par.values() if v["folgado"]["f"]["tipo"] == v["curto"]["f"]["tipo"] == "solucao"
            and v["folgado"]["f"]["estados"] == v["curto"]["f"]["estados"] and v["folgado"]["f"]["sensores"] == v["curto"]["f"]["sensores"])
print(" pares com solucao nos dois e mesma maquina (estados e sensores):", mesmo)
print("\nk x desfecho f:")
t = Counter((r["rotulo"].split("-")[3], r["rotulo"].split("-")[2], r["f"]["tipo"]) for r in L)
for k in sorted(t): print("  ", k, t[k])
print("\nseg: casos em que f levou mais segundos que cegis_poda, por tipo:",
      Counter(r["rotulo"].split("-")[2] for r in L if r["f"]["segundos"] > r["cegis_poda"]["segundos"]))
print("seg f por tipo:", {t: round(sum(r['f']['segundos'] for r in L if r['rotulo'].split('-')[2] == t), 1) for t in ('autorizado','eventos','encerrar','sem_reset')})
print("seg cegis_poda por tipo:", {t: round(sum(r['cegis_poda']['segundos'] for r in L if r['rotulo'].split('-')[2] == t), 1) for t in ('autorizado','eventos','encerrar','sem_reset')})
