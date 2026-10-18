"""CEGIS com poda x CEGIS sem poda: onde difere, fora dos casos cortados pelo limite de nos.

Uso: python3 -I poda.py <resultados.jsonl>
"""
import json, sys, statistics as st
L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
nt = [r for r in L if r["cegis"]["tipo"] != "timeout"]
to = [r for r in L if r["cegis"]["tipo"] == "timeout"]
def s(rs, m, k): return sum(r[m][k] for r in rs)
for nome, rs in (("sem timeout do cegis", nt), ("com timeout do cegis", to)):
    print(nome, len(rs))
    for k in ("formulacoes", "verificacoes", "nos", "segundos"):
        print("  %s: f %.1f | cegis_poda %.1f | cegis %.1f" % (k, s(rs, "f", k), s(rs, "cegis_poda", k), s(rs, "cegis", k)))
print("casos sem timeout em que cegis tem mais formulacoes que cegis_poda:", sum(1 for r in nt if r["cegis"]["formulacoes"] > r["cegis_poda"]["formulacoes"]),
      "| menos:", sum(1 for r in nt if r["cegis"]["formulacoes"] < r["cegis_poda"]["formulacoes"]),
      "| igual:", sum(1 for r in nt if r["cegis"]["formulacoes"] == r["cegis_poda"]["formulacoes"]))
print("diferenca cegis - cegis_poda em formulacoes (sem timeout): mediana", st.median(r["cegis"]["formulacoes"] - r["cegis_poda"]["formulacoes"] for r in nt))
print("diferenca cegis - cegis_poda em verificacoes (sem timeout): mediana", st.median(r["cegis"]["verificacoes"] - r["cegis_poda"]["verificacoes"] for r in nt))
print("diferenca formulacoes - verificacoes, cegis (sem timeout) == cegis_poda?:",
      sum(1 for r in nt if r["cegis"]["formulacoes"] - r["cegis"]["verificacoes"] == r["cegis_poda"]["formulacoes"] - r["cegis_poda"]["verificacoes"]), "de", len(nt))
# fracao das buscas que terminaram sem candidato verificado
for m in ("f", "cegis_poda", "cegis"):
    F = s(L, m, "formulacoes"); V = s(L, m, "verificacoes")
    print("%s: formulacoes sem verificacao = %d de %d (%.1f%%)" % (m, F - V, F, 100 * (F - V) / F))
# formulacoes por verificacao no caso f
print("f: casos com formulacoes == verificacoes:", sum(1 for r in L if r["f"]["formulacoes"] == r["f"]["verificacoes"]))
