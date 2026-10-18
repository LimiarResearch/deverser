"""Pares de codigos quase iguais no ledger (mesma base, variante e registradores; redes que diferem na ordem de poucas camadas):
a diferenca das razoes medidas em processos separados da uma ideia (fraca) da estabilidade entre processos.
Uso: python3 -I vizinhos.py <ledger.jsonl> <estado.json>
"""
import itertools, json, sys


def niveis(rede):
    u, o = [0] * 8, []
    for i, j in rede:
        nv = max(u[i], u[j]) + 1; u[i] = u[j] = nv; o.append(nv)
    return o


def decod(f, base):
    niv = niveis(base)
    mant = [q for q in range(len(base)) if not int(f.get(f"rem_{q}", 0))]
    mant.sort(key=lambda q: (niv[q], float(f.get(f"pri_{q}", 0.5)), q))
    return [tuple(base[q]) for q in mant]


def camadas(rede):
    nv = niveis(rede); d = {}
    for c, k in zip(rede, nv):
        d.setdefault(k, []).append(c)
    return [d[k] for k in sorted(d)]


L = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
est = json.load(open(sys.argv[2], encoding="utf-8"))
c = est["modelo"]["carga"]; cd = json.loads(c[c.index("return ") + 7:].strip())
form = {e["formulacao"]["_id"]: e["formulacao"] for e in L if e["tipo"] == "formulacao"}
itens = []
for v in L:
    if v["tipo"] != "veredito":
        continue
    f = form[v["formulacao_id"]]
    rede = decod(f, cd["redes"][f["base"]])
    itens.append((v["seq"], f["base"], f["variante"], f["registradores"], rede, v["medidas"]["razao_vs_melhor"], v["medidas"]["erro_de_ordenacao"] == 0))
pares = []
for a, b in itertools.combinations(itens, 2):
    if a[1:4] != b[1:4] or len(a[4]) != len(b[4]):
        continue
    if sorted(a[4]) != sorted(b[4]):
        continue  # redes diferentes (outro comparador retirado)
    ca, cb = camadas(a[4]), camadas(b[4])
    if len(ca) != len(cb):
        continue
    dif = sum(1 for x, y in zip(ca, cb) if x != y)
    pos = sum(1 for x, y in zip(a[4], b[4]) if x != y)
    pares.append((dif, pos, abs(a[5] - b[5]), a[0], b[0], a[5], b[5], a[1:4], a[6]))
pares.sort()
print("pares com o mesmo conjunto de comparadores, mesma variante e mesmos registradores:", len(pares))
for p in pares[:25]:
    print("camadas_diferentes=%d posicoes_diferentes=%d |dif razao|=%.5f seq %d x %d: %.5f x %.5f %s correta=%s" % p)
import statistics as st
for k in range(0, 7):
    xs = [p[2] for p in pares if p[0] == k]
    if xs:
        print("camadas diferentes =", k, "pares:", len(xs), "mediana |dif|:", round(st.median(xs), 5), "max:", round(max(xs), 5))
