"""Recontagem independente da bateria CEGIS x formula e da auditoria do z3.

Uso (so le os arquivos de dados; nao importa nada do repositorio):
  python3 -I recontagem.py <resultados.jsonl> <resumo.json> <protocolo.json> <auditoria_z3.json>
"""
import json
import sys
from collections import Counter, defaultdict

M = ["f", "cegis_poda", "cegis"]


def carregar(p_res, p_resumo, p_prot, p_aud):
    linhas = []
    with open(p_res, encoding="utf-8") as fh:
        for n, l in enumerate(fh, 1):
            if l.strip():
                linhas.append(json.loads(l))
    resumo = json.load(open(p_resumo, encoding="utf-8"))
    prot = json.load(open(p_prot, encoding="utf-8"))
    aud = json.load(open(p_aud, encoding="utf-8"))
    return linhas, resumo, prot, aud


def secao(t):
    print("\n" + "=" * 8 + " " + t)


def main():
    linhas, resumo, prot, aud = carregar(*sys.argv[1:5])
    por_id = {r["id"]: r for r in linhas}

    secao("1. casos")
    print("linhas:", len(linhas), "| ids unicos:", len(por_id), "| ids = 0..191:", sorted(por_id) == list(range(192)))
    print("rotulos unicos:", len({r["rotulo"] for r in linhas}))
    print("linhas fora da ordem de id:", sum(1 for i, r in enumerate(linhas) if r["id"] != i))
    fatores = [Counter() for _ in range(5)]
    for r in linhas:
        for i, x in enumerate(r["rotulo"].split("-")):
            fatores[i][x] += 1
    print("fatores do rotulo:", [dict(c) for c in fatores])
    print("protocolo.casos:", prot["casos"], "| resumo.casos:", resumo["casos"], "| auditoria.resumo.casos:", aud["resumo"]["casos"])

    secao("2. totais por metodo (recontados) x resumo.json")
    tot = {}
    for m in M:
        t = defaultdict(float)
        des = Counter()
        conf = Counter()
        for r in linhas:
            x = r[m]
            for k in ("formulacoes", "verificacoes", "buscas", "nos", "segundos"):
                t[k] += x[k]
            des[x["tipo"]] += 1
            conf[repr(x["conferido"])] += 1
        tot[m] = t
        rm = resumo[m]
        print(f"[{m}]")
        print("  desfechos recontados:", dict(sorted(des.items())), "| resumo:", rm["desfechos"], "| iguais:", dict(des) == rm["desfechos"])
        for k, kr in (("formulacoes", "formulacoes_total"), ("verificacoes", "verificacoes_total"), ("nos", "nos_total"), ("segundos", "segundos_total")):
            v = round(t[k], 1) if k == "segundos" else int(t[k])
            print(f"  {k}: recontado {v} | resumo {rm[kr]} | iguais: {abs(v - rm[kr]) < 0.051}")
        print("  buscas (nao esta no resumo):", int(t["buscas"]))
        print("  campo conferido:", dict(conf), "| resumo conferidos:", rm["conferidos"], "| falhas (conferido == False):", conf.get("False", 0),
              "| resumo falhas:", rm["falhas_de_conferencia"])
        # coerencia: conferido so em quem tem solucao? (para f, tambem nos impossiveis)
        por_tipo = defaultdict(Counter)
        for r in linhas:
            por_tipo[r[m]["tipo"]][repr(r[m]["conferido"])] += 1
        print("  conferido por desfecho:", {k: dict(v) for k, v in por_tipo.items()})

    secao("3. concordancia de custo e contradicoes entre metodos")
    for a, b in (("f", "cegis_poda"), ("f", "cegis"), ("cegis_poda", "cegis")):
        ambos = [r for r in linhas if r[a]["tipo"] == "solucao" and r[b]["tipo"] == "solucao"]
        mesmo = [r for r in ambos if r[a]["custo"] == r[b]["custo"]]
        mesma_maq = [r for r in ambos if r[a]["estados"] == r[b]["estados"] and r[a]["sensores"] == r[b]["sensores"]]
        print(f"{a} x {b}: ambos com maquina {len(ambos)}, mesmo custo {len(mesmo)}, mesmos estados e sensores {len(mesma_maq)}",
              "| resumo:", resumo["concordancia_de_custo"].get(f"{a}_x_{b}"))
    # contradicao: um metodo acha maquina e outro declara que nao ha (sem_maquina, insufficient_memory, unobservable, over_budget)
    nega = {"sem_maquina_na_familia", "insufficient_memory", "unobservable", "over_budget"}
    contra = []
    for r in linhas:
        for a in M:
            for b in M:
                if r[a]["tipo"] == "solucao" and r[b]["tipo"] in nega:
                    contra.append((r["id"], a, r[a]["custo"], b, r[b]["tipo"]))
    print("contradicoes (um acha maquina, outro nega):", contra, "| resumo:", resumo["contradicoes_entre_metodos"])
    sol_acima = [(r["id"], m, r[m]["custo"], r["B"]) for r in linhas for m in M if r[m]["tipo"] == "solucao" and r[m]["custo"] > r["B"]]
    print("solucoes com custo acima de B:", sol_acima)

    secao("4. tabela cruzada de desfechos")
    ct = Counter((r["f"]["tipo"], r["cegis_poda"]["tipo"], r["cegis"]["tipo"]) for r in linhas)
    for k, v in sorted(ct.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  f={k[0]:20s} cegis_poda={k[1]:24s} cegis={k[2]:24s} {v}")

    secao("5. auditoria do z3: recontagem")
    ra = aud["resumo"]
    casos = aud["casos"]
    print("casos na auditoria:", len(casos), "| ids unicos:", len({c["id"] for c in casos}))
    cont = Counter(c["tipo_da_regra_f"] for c in casos)
    print("vereditos por desfecho (recontado):", dict(cont))
    print("resumo.por_desfecho:", ra["por_desfecho"])
    print("perguntas ao z3 (soma):", sum(c["perguntas_ao_z3"] for c in casos), "| resumo:", ra["perguntas_ao_z3"])
    print("discordancias (soma de listas):", sum(len(c["discordancias"]) for c in casos), "| resumo:", ra["discordancias"])
    print("desconhecidos (soma):", sum(c["desconhecidos"] for c in casos), "| resumo:", ra["desconhecidos"])
    print("tabelas_sat_conferidas:", dict(Counter(repr(c["tabelas_sat_conferidas"]) for c in casos)))
    print("segundos (soma):", round(sum(c["segundos"] for c in casos), 2), "| segundos_z3 (soma):", round(sum(c["segundos_z3"] for c in casos), 2),
          "| resumo.segundos:", ra["segundos"])
    s_aut = [c for c in casos if c["usa_s_autorizado"]]
    print("usa_s_autorizado True:", len(s_aut), "| entre solucoes:", sum(1 for c in s_aut if c["tipo_da_regra_f"] == "solucao"),
          "| por desfecho:", dict(Counter(c["tipo_da_regra_f"] for c in s_aut)), "| resumo.solucoes_com_s_autorizado:", ra["solucoes_com_s_autorizado"])
    print("hash_dos_casos auditoria:", ra["hash_dos_casos"])
    print("hash_dos_casos protocolo:", prot["hash_dos_casos"])
    print("iguais:", ra["hash_dos_casos"] == prot["hash_dos_casos"])

    secao("6. auditoria x resultados, caso a caso")
    dif = []
    for c in casos:
        r = por_id.get(c["id"])
        if r is None:
            dif.append((c["id"], "sem linha em resultados"))
            continue
        for ka, kr in (("rotulo", "rotulo"), ("B", "B")):
            if c[ka] != r[kr]:
                dif.append((c["id"], ka, c[ka], r[kr]))
        if c["tipo_da_regra_f"] != r["f"]["tipo"]:
            dif.append((c["id"], "tipo", c["tipo_da_regra_f"], r["f"]["tipo"]))
        if c["custo_da_regra_f"] != r["f"]["custo"]:
            dif.append((c["id"], "custo", c["custo_da_regra_f"], r["f"]["custo"]))
        sens = r["f"]["sensores"] or []
        if c["usa_s_autorizado"] != ("s_autorizado" in sens):
            dif.append((c["id"], "usa_s_autorizado", c["usa_s_autorizado"], sens))
    print("diferencas auditoria x resultados.f:", dif if dif else "nenhuma")
    # o veredito do z3 (implicito: veredito da regra f confirmado) contra cada metodo
    for m in ("cegis_poda", "cegis"):
        tab = Counter((c["tipo_da_regra_f"], por_id[c["id"]][m]["tipo"]) for c in casos)
        print(f"veredito confirmado pelo z3 x desfecho de {m}:", dict(sorted(tab.items())))
        custo_ok = sum(1 for c in casos if c["tipo_da_regra_f"] == "solucao" and por_id[c["id"]][m]["tipo"] == "solucao"
                       and por_id[c["id"]][m]["custo"] == c["custo_da_regra_f"])
        print(f"  solucoes de {m} com o mesmo custo confirmado pelo z3:", custo_ok)

    secao("7. limites do protocolo")
    print("protocolo: limite_de_nos", prot["limite_de_nos"], "| max_formulacoes", prot["max_formulacoes"])
    for m in M:
        fx = [r[m]["formulacoes"] for r in linhas]
        nx = [r[m]["nos"] for r in linhas]
        print(f"{m}: formulacoes max {max(fx)} | casos com formulacoes >= 400: {sum(1 for v in fx if v >= prot['max_formulacoes'])}"
              f" | nos max {max(nx)} | casos com nos >= 300000: {sum(1 for v in nx if v >= prot['limite_de_nos'])}")
    to = [r for r in linhas if r["cegis"]["tipo"] == "timeout"]
    print("cegis timeout:", len(to), "| buscas == formulacoes + 1:", sum(1 for r in to if r["cegis"]["buscas"] == r["cegis"]["formulacoes"] + 1),
          "| nos >= 300000:", sum(1 for r in to if r["cegis"]["nos"] >= 300000), "| nos min:", min(r["cegis"]["nos"] for r in to))
    nto = [r for r in linhas if r["cegis"]["tipo"] != "timeout"]
    print("cegis nao-timeout: buscas == formulacoes:", sum(1 for r in nto if r["cegis"]["buscas"] == r["cegis"]["formulacoes"]), "de", len(nto),
          "| nos max:", max(r["cegis"]["nos"] for r in nto))
    for m in ("f", "cegis_poda"):
        print(f"{m}: buscas == formulacoes em", sum(1 for r in linhas if r[m]["buscas"] == r[m]["formulacoes"]), "de 192")
    for m in M:
        print(f"{m}: verificacoes <= formulacoes em", sum(1 for r in linhas if r[m]["verificacoes"] <= r[m]["formulacoes"]), "de 192")

    secao("8. razoes agregadas")
    F = tot["f"]
    for m in ("cegis_poda", "cegis"):
        for k in ("formulacoes", "verificacoes", "nos", "segundos"):
            print(f"{m}/f em {k}: {tot[m][k]:.1f}/{F[k]:.1f} = {tot[m][k] / F[k]:.3f}")


if __name__ == "__main__":
    main()
