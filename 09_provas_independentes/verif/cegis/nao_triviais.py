"""As solucoes fora da familia 'autorizado' (sem o sensor s_autorizado) e as razoes nelas.

Uso: python3 -I nao_triviais.py <resultados.jsonl>
"""
import json, sys, statistics as st
L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
fam = lambda r: r["rotulo"].split("-")[2]
for nome, rs in (("solucoes da familia autorizado", [r for r in L if r["f"]["tipo"] == "solucao" and fam(r) == "autorizado"]),
                 ("solucoes fora da familia autorizado", [r for r in L if r["f"]["tipo"] == "solucao" and fam(r) != "autorizado"]),
                 ("todos os casos fora da familia autorizado", [r for r in L if fam(r) != "autorizado"])):
    print(nome, len(rs))
    for m in ("cegis_poda", "cegis"):
        for k in ("formulacoes", "verificacoes", "segundos"):
            a = sum(r["f"][k] for r in rs); b = sum(r[m][k] for r in rs)
            print("  %s/f %s: %.1f/%.1f = %.2f" % (m, k, b, a, b / a))
    print("  cegis resolveu:", sum(1 for r in rs if r["cegis"]["tipo"] == "solucao"), "| estados das solucoes de f:",
          sorted({r["f"]["estados"] for r in rs if r["f"]["estados"]}))
    rz = [r["cegis_poda"]["formulacoes"] / r["f"]["formulacoes"] for r in rs]
    print("  mediana da razao cegis_poda/f por caso: %.2f" % st.median(rz))
