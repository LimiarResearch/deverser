"""Recontagem independente do ledger da corrida de 8 elementos (deverser, 29/09).

Le como dados (nao executa nada do repositorio):
  argv[1] ledger.jsonl
  argv[2] estado.json
  argv[3] rede_vencedora.json

Uso: python3 -I ledger.py <ledger.jsonl> <estado.json> <rede_vencedora.json>
"""
import collections
import itertools
import json
import statistics as st
import sys


def niveis_asap(rede, n=8):
    ultimo, out = [0] * n, []
    for i, j in rede:
        nv = max(ultimo[i], ultimo[j]) + 1
        ultimo[i] = ultimo[j] = nv
        out.append(nv)
    return out


def decodifica(genes, base):
    niv = niveis_asap(base)
    mantidos = [k for k in range(len(base)) if not int(genes.get(f"rem_{k}", 0))]
    mantidos.sort(key=lambda k: (niv[k], float(genes.get(f"pri_{k}", 0.5)), k))
    return [tuple(base[k]) for k in mantidos]


def ordena01(rede, n=8):
    for x in itertools.product((0, 1), repeat=n):
        v = list(x)
        for i, j in rede:
            if v[i] > v[j]:
                v[i], v[j] = v[j], v[i]
        if any(v[q] > v[q + 1] for q in range(n - 1)):
            return False
    return True


def resumo(xs):
    xs = sorted(xs)
    if not xs:
        return None
    return {"n": len(xs), "min": xs[0], "p25": xs[int(0.25 * (len(xs) - 1))], "mediana": st.median(xs), "p75": xs[int(0.75 * (len(xs) - 1))], "max": xs[-1]}


def main():
    L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
    est = json.load(open(sys.argv[2], encoding="utf-8"))
    rv = json.load(open(sys.argv[3], encoding="utf-8"))
    carga = est["modelo"]["carga"]
    redes = json.loads(carga[carga.index("return ") + 7:].strip())["redes"]
    out = {}
    out["linhas"] = len(L)
    out["por_tipo"] = dict(collections.Counter(e["tipo"] for e in L))
    out["seq_continua"] = [e["seq"] for e in L] == list(range(1, len(L) + 1))
    form = {e["formulacao"]["_id"]: e["formulacao"] for e in L if e["tipo"] == "formulacao"}
    ver = [e for e in L if e["tipo"] == "veredito"]
    evi = [e for e in L if e["tipo"] == "evidencia"]
    out["ids_unicos_formulacao"] = len(form)
    out["vereditos"] = len(ver)
    out["aprovados"] = sum(1 for v in ver if v["aprovado"])
    out["nulos_por_classe_e_clausula"] = dict(collections.Counter(((v.get("nulo") or {}).get("classe"), (v.get("nulo") or {}).get("clausula")) for v in ver if not v["aprovado"]).items()).__repr__()
    out["julgamentos"] = dict(collections.Counter(json.dumps(v.get("julgamento"), sort_keys=True) for v in ver))
    out["custo_total"] = dict(collections.Counter())
    for v in ver:
        for k, x in (v.get("custo") or {}).items():
            out["custo_total"][k] = out["custo_total"].get(k, 0) + x
    out["medidas_reusadas_de_nao_vazias"] = sum(1 for v in ver if v.get("medidas_reusadas_de"))
    out["oraculos_detalhes"] = dict(collections.Counter(o["detalhe"] for e in evi for o in e["medida"]["valores"].get("oraculos", [])))

    linhas = []
    discord = 0
    for v in ver:
        f = form[v["formulacao_id"]]
        m = v["medidas"]
        rede = decodifica(f, redes[f["base"]])
        ok01 = ordena01(rede)
        erro = m.get("erro_de_ordenacao")
        if ok01 != (erro == 0):
            discord += 1
        rr, rs, rmel = m.get("razao_vs_rede"), m.get("razao_vs_simd"), m.get("razao_vs_melhor")
        linhas.append({"seq": v["seq"], "base": f["base"], "variante": f["variante"], "reg": f["registradores"], "comp": m.get("comparadores"), "comp_decod": len(rede),
                       "ordena_0_1_meu": ok01, "erro": erro, "correto": m.get("correto"), "aprovado": v["aprovado"],
                       "razao_vs_rede": rr, "razao_vs_simd": rs, "razao_vs_melhor": rmel,
                       "max_rr_rs": max(rr, rs) if rr is not None and rs is not None else None,
                       "ciclos": m.get("ciclos_por_vetor"), "ciclos_ref": m.get("ciclos_referencia"), "ciclos_simd": m.get("ciclos_simd"),
                       "razao_das_medianas": round(m["ciclos_por_vetor"] / m["ciclos_referencia"], 5) if m.get("ciclos_referencia") else None,
                       "ref_ref": m.get("razao_ref_contra_ref"), "ruido": m.get("ruido"), "ns_std_sort": m.get("ns_std_sort"),
                       "tempo_s": m.get("tempo_mediana_s"), "nulo": (v.get("nulo") or {}).get("clausula")})
    out["discordancias_meu_0_1_vs_erro_registrado"] = discord
    out["comparadores_registrados_iguais_aos_decodificados"] = all(x["comp"] == x["comp_decod"] for x in linhas)
    out["razao_vs_melhor_igual_max_rede_simd"] = all(x["razao_vs_melhor"] == x["max_rr_rs"] for x in linhas)
    out["por_base_variante_reg"] = dict(collections.Counter(f"{x['base']}/{x['variante']}/reg={x['reg']}" for x in linhas))
    out["ordenam_pelo_meu_0_1"] = sum(1 for x in linhas if x["ordena_0_1_meu"])
    out["erro_zero"] = sum(1 for x in linhas if x["erro"] == 0)
    out["dist_razao_vs_melhor"] = resumo([x["razao_vs_melhor"] for x in linhas])
    out["dist_razao_vs_melhor_corretos"] = resumo([x["razao_vs_melhor"] for x in linhas if x["erro"] == 0])
    out["abaixo_de_0.97"] = sorted((x["razao_vs_melhor"], x["seq"]) for x in linhas if x["razao_vs_melhor"] <= 0.97)
    out["abaixo_de_1.0"] = sum(1 for x in linhas if x["razao_vs_melhor"] < 1.0)
    out["dist_ciclos_referencia_mesmo_codigo"] = resumo([x["ciclos_ref"] for x in linhas])
    cr = [x["ciclos_ref"] for x in linhas]
    out["amplitude_ciclos_ref_pct"] = round(100 * (max(cr) - min(cr)) / st.median(cr), 2)
    out["dist_ciclos_simd"] = resumo([x["ciclos_simd"] for x in linhas])
    out["dist_ns_std_sort"] = resumo([x["ns_std_sort"] for x in linhas])
    out["valores_ref_contra_ref"] = dict(collections.Counter(x["ref_ref"] for x in linhas))
    out["dist_ruido"] = resumo([x["ruido"] for x in linhas])
    dif = [x["razao_vs_rede"] - x["razao_das_medianas"] for x in linhas]
    out["mediana_das_razoes_menos_razao_das_medianas"] = resumo([round(d, 5) for d in dif])
    out["dist_razao_ciclos_simd_sobre_ref"] = resumo([round(x["ciclos_simd"] / x["ciclos_ref"], 4) for x in linhas])
    out["dist_razao_rede_sobre_simd_por_blocos"] = resumo([round(x["razao_vs_rede"] / x["razao_vs_simd"], 4) for x in linhas if x["razao_vs_simd"]])
    # os validos, ordenados
    val = sorted((x for x in linhas if x["aprovado"]), key=lambda x: x["razao_vs_melhor"])
    out["validos"] = [{k: x[k] for k in ("seq", "razao_vs_melhor", "razao_das_medianas", "ciclos", "ciclos_ref", "ruido", "ns_std_sort", "variante", "reg")} for x in val]
    out["validos_quantizados_a_0.01"] = [round(round(x["razao_vs_melhor"] / 0.01) * 0.01, 2) for x in val]
    # vencedor do ledger e o do rede_vencedora.json
    esc = est["criacoes"][-1]["escolhido"]["formulacao"]["_id"]
    out["escolhido_esta_no_ledger_seq"] = [v["seq"] for v in ver if v["formulacao_id"] == esc]
    out["escolhido_igual_descricao_rede_vencedora_json"] = esc == rv["descricao_do_candidato"]
    mv = next(v["medidas"] for v in ver if v["formulacao_id"] == esc)
    out["medidas_do_escolhido_iguais_rede_vencedora_json"] = {k: (mv.get(k) == rv["medidas_no_servidor"].get(k)) for k in rv["medidas_no_servidor"]}
    # top da populacao final, incluindo reprovados
    out["top10_razao_vs_melhor"] = [(x["razao_vs_melhor"], x["seq"], x["variante"], x["reg"], x["aprovado"]) for x in sorted(linhas, key=lambda x: x["razao_vs_melhor"])[:10]]
    out["por_variante_reg_mediana_razao"] = {}
    g = collections.defaultdict(list)
    for x in linhas:
        g[f"{x['base']}/{x['variante']}/reg={x['reg']}"].append(x["razao_vs_melhor"])
    out["por_variante_reg_mediana_razao"] = {k: (len(v), round(st.median(v), 5), min(v), max(v)) for k, v in g.items()}
    # mesma rede (ordem de comparadores) aparecendo com medidas diferentes? (repeticao implicita)
    por_rede = collections.defaultdict(list)
    for x, v in zip(linhas, ver):
        f = form[v["formulacao_id"]]
        por_rede[(tuple(decodifica(f, redes[f["base"]])), f["variante"], f["registradores"])].append(x["razao_vs_melhor"])
    out["codigos_distintos_na_populacao_final"] = len(por_rede)
    out["codigos_repetidos_com_medidas"] = [v for v in por_rede.values() if len(v) > 1]
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("\n==== tabela (ordenada por razao_vs_melhor) ====")
    for x in sorted(linhas, key=lambda x: x["razao_vs_melhor"]):
        print(json.dumps(x, ensure_ascii=False))


if __name__ == "__main__":
    main()
