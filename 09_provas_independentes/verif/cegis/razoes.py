"""Distribuicao caso a caso da razao de formulacoes (e de verificacoes, nos e segundos) entre CEGIS e a formula.

Uso: python3 -I razoes.py <resultados.jsonl>
"""
import json
import statistics as st
import sys
from collections import defaultdict


def q(xs, p):
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def resumo_razoes(rs, nome):
    if not rs:
        print(f"  {nome}: (vazio)")
        return
    print(f"  {nome}: n={len(rs)} min={min(rs):.2f} p25={q(rs, .25):.2f} mediana={st.median(rs):.2f} p75={q(rs, .75):.2f} max={max(rs):.2f}"
          f" media={st.mean(rs):.2f} media_geom={st.geometric_mean(rs):.2f}")


def main():
    L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
    L.sort(key=lambda r: r["id"])

    for m in ("cegis_poda", "cegis"):
        print("\n" + "=" * 10, m, "contra f")
        for k in ("formulacoes", "verificacoes", "nos", "segundos"):
            menos = sum(1 for r in L if r["f"][k] < r[m][k])
            mais = sum(1 for r in L if r["f"][k] > r[m][k])
            igual = sum(1 for r in L if r["f"][k] == r[m][k])
            print(f" {k}: f usou menos em {menos}, mais em {mais}, igual em {igual}")
            if k in ("formulacoes", "verificacoes"):
                rs = [r[m][k] / r["f"][k] for r in L]  # f nunca tem 0 formulacoes ou verificacoes (conferido abaixo)
                resumo_razoes(rs, f"razao {m}/f por caso ({k})")
        print(" f com 0 formulacoes:", sum(1 for r in L if r["f"]["formulacoes"] == 0), "| f com 0 verificacoes:", sum(1 for r in L if r["f"]["verificacoes"] == 0))

        print(" -- por desfecho da formula (soma de formulacoes):")
        g = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
        for r in L:
            x = g[r["f"]["tipo"]]
            x[0] += 1
            x[1] += r["f"]["formulacoes"]
            x[2] += r[m]["formulacoes"]
            x[3] += r["f"]["verificacoes"]
            x[4] += r[m]["verificacoes"]
            x[5] += r[m]["formulacoes"] - r["f"]["formulacoes"]
        dtot = sum(v[5] for v in g.values())
        for t, (n, ff, mm, vf, vm, d) in sorted(g.items()):
            print(f"   {t:20s} casos {n:3d} | formulacoes f {ff:5d} {m} {mm:6d} razao {mm / ff:6.2f} | parte da diferenca {d / dtot:6.1%}"
                  f" | verificacoes f {vf:4d} {m} {vm:5d} razao {vm / vf:5.2f}")
        com = [r for r in L if r["f"]["tipo"] == "solucao" and r[m]["tipo"] == "solucao"]
        sf = sum(r["f"]["formulacoes"] for r in com)
        sm = sum(r[m]["formulacoes"] for r in com)
        vf = sum(r["f"]["verificacoes"] for r in com)
        vm = sum(r[m]["verificacoes"] for r in com)
        tf = sum(r["f"]["segundos"] for r in com)
        tm = sum(r[m]["segundos"] for r in com)
        print(f" -- so os casos que os dois resolveram ({len(com)}): formulacoes {sm}/{sf} = {sm / sf:.2f};"
              f" verificacoes {vm}/{vf} = {vm / vf:.2f}; segundos {tm:.1f}/{tf:.1f} = {tm / tf:.2f}")
        resumo_razoes([r[m]["formulacoes"] / r["f"]["formulacoes"] for r in com], "razao por caso, so os resolvidos pelos dois")
        resumo_razoes([r[m]["verificacoes"] / r["f"]["verificacoes"] for r in com], "razao de verificacoes, so os resolvidos pelos dois")

        # concentracao: quanto da diferenca vem dos casos de maior diferenca
        dif = sorted((r[m]["formulacoes"] - r["f"]["formulacoes"] for r in L), reverse=True)
        D = sum(dif)
        for frac in (0.1, 0.25, 0.5):
            n = int(len(dif) * frac)
            print(f" os {n} casos de maior diferenca ({frac:.0%}) somam {sum(dif[:n]) / D:.1%} da diferenca total")
        # sem os casos em que f decidiu com 1 formulacao
        um = [r for r in L if r["f"]["formulacoes"] == 1]
        print(f" casos em que f usou 1 formulacao: {len(um)} (desfechos: "
              f"{dict((t, sum(1 for r in um if r['f']['tipo'] == t)) for t in sorted({r['f']['tipo'] for r in um}))});"
              f" {m} gastou neles {sum(r[m]['formulacoes'] for r in um)} formulacoes")
        resto = [r for r in L if r["f"]["formulacoes"] > 1]
        print(f" sem esses casos: {sum(r[m]['formulacoes'] for r in resto)}/{sum(r['f']['formulacoes'] for r in resto)} ="
              f" {sum(r[m]['formulacoes'] for r in resto) / sum(r['f']['formulacoes'] for r in resto):.2f}")

        print(" -- por fator do rotulo (soma de formulacoes, razao):")
        for i, nome in enumerate(("familia J", "ordem", "tipo", "memoria k", "orcamento")):
            g2 = defaultdict(lambda: [0, 0])
            for r in L:
                v = r["rotulo"].split("-")[i]
                g2[v][0] += r["f"]["formulacoes"]
                g2[v][1] += r[m]["formulacoes"]
            print("   " + nome + ": " + "; ".join(f"{k} {b}/{a}={b / a:.1f}" for k, (a, b) in sorted(g2.items())))

    print("\n" + "=" * 10, "distribuicao das formulacoes da formula")
    from collections import Counter
    print(" f.formulacoes:", dict(sorted(Counter(r["f"]["formulacoes"] for r in L).items())))
    for t in ("insufficient_memory", "unobservable", "over_budget", "solucao"):
        xs = [r["f"]["formulacoes"] for r in L if r["f"]["tipo"] == t]
        print(f"  {t}: n={len(xs)} soma={sum(xs)} min={min(xs)} mediana={st.median(xs)} max={max(xs)}")
    for m in ("cegis_poda", "cegis"):
        for t in ("insufficient_memory", "unobservable", "over_budget", "solucao"):
            xs = [r[m]["formulacoes"] for r in L if r["f"]["tipo"] == t]
            print(f"  {m} quando f={t}: soma={sum(xs)} min={min(xs)} mediana={st.median(xs)} max={max(xs)}")

    print("\n" + "=" * 10, "familia autorizado (sensor s_autorizado)")
    for fam in ("autorizado", "eventos", "encerrar", "sem_reset"):
        sub = [r for r in L if r["rotulo"].split("-")[2] == fam]
        des = Counter(r["f"]["tipo"] for r in sub)
        sol = [r for r in sub if r["f"]["tipo"] == "solucao"]
        est = Counter(r["f"]["estados"] for r in sol)
        sa = sum(1 for r in sol if "s_autorizado" in (r["f"]["sensores"] or []))
        print(f"  {fam}: desfechos f {dict(des)} | estados das solucoes {dict(est)} | solucoes com s_autorizado {sa}"
              f" | formulacoes f {sum(r['f']['formulacoes'] for r in sub)} cegis_poda {sum(r['cegis_poda']['formulacoes'] for r in sub)}"
              f" cegis {sum(r['cegis']['formulacoes'] for r in sub)}")

    print("\n" + "=" * 10, "os 24 casos f=insufficient_memory e cegis_poda=over_budget: orcamento")
    x = [r for r in L if r["f"]["tipo"] == "insufficient_memory" and r["cegis_poda"]["tipo"] == "over_budget"]
    print("  ", Counter(r["rotulo"].split("-")[4] for r in x))
    x = [r for r in L if r["f"]["tipo"] == "insufficient_memory" and r["cegis_poda"]["tipo"] == "sem_maquina_na_familia"]
    print("   f=insufficient_memory e cegis_poda=sem_maquina:", Counter(r["rotulo"].split("-")[4] for r in x))
    x = [r for r in L if r["f"]["tipo"] == "over_budget"]
    print("   f=over_budget:", Counter(r["rotulo"].split("-")[4] for r in x))


if __name__ == "__main__":
    main()
