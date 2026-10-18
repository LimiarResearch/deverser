"""Para os candidatos corretos do ledger: a ordem de cada um comparada com a da referencia, camada a camada.
Uso: python3 -I ordens.py <ledger.jsonl> <estado.json>
"""
import json, sys


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


L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
est = json.load(open(sys.argv[2], encoding="utf-8"))
carga = est["modelo"]["carga"]
cd = json.loads(carga[carga.index("return ") + 7:].strip())
ref = [tuple(c) for c in cd["referencia"]]
form = {e["formulacao"]["_id"]: e["formulacao"] for e in L if e["tipo"] == "formulacao"}
linhas = []
for v in L:
    if v["tipo"] != "veredito":
        continue
    f = form[v["formulacao_id"]]
    rede = decodifica(f, cd["redes"][f["base"]])
    m = v["medidas"]
    if m["erro_de_ordenacao"] != 0:
        continue
    pos_iguais = sum(1 for a, b in zip(rede, ref) if a == b)
    linhas.append((m["razao_vs_melhor"], v["seq"], f["base"], f["variante"], f["registradores"], rede == ref, pos_iguais, len(rede)))
for x in sorted(linhas):
    print("razao=%.5f seq=%d base=%s var=%s reg=%d ordem_igual_a_ref=%s posicoes_iguais=%d/%d" % x)
