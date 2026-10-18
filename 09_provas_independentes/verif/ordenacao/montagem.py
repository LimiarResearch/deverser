"""Confere se o decodificador, as metricas e o oraculo usados na corrida (respostas/004) sao os do script publicado
experimentos/montar_ordenacao_motor.py. O script e lido so com ast.parse (as constantes CANDIDATO, METRICAS, ORACULO), sem executar.
Tambem compara os genes e as redes decodificadas dos tres da fronteira.
Uso: python3 -I montagem.py <montar_ordenacao_motor.py> <respostas/004_propor_modelo.json> <estado.json>
"""
import ast, json, sys

src = open(sys.argv[1], encoding="utf-8").read()
k = {}
for no in ast.parse(src).body:
    if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name) and no.targets[0].id in ("CANDIDATO", "METRICAS", "ORACULO", "OTIMAS"):
        k[no.targets[0].id] = ast.literal_eval(no.value)
m = json.load(open(sys.argv[2], encoding="utf-8"))["modelo"]
print("decodificador (CANDIDATO) igual ao da corrida:", m["representacao"]["arquetipos"][0]["codigo"] == k["CANDIDATO"])
print("metricas iguais:", m["metricas"] == k["METRICAS"])
print("oraculo igual:", m["oraculo"] == k["ORACULO"])
carga = json.loads(m["carga"][m["carga"].index("return ") + 7:].strip())
print("rede 'otima' da carga igual a OTIMAS[8] do script:", [list(c) for c in k["OTIMAS"][8]] == carga["redes"]["otima"])
print("variantes no L da corrida:", m["representacao"]["arquetipos"][0]["variaveis"][1]["valores"])
print("repeticoes passadas ao medidor:", carga["repeticoes"])

est = json.load(open(sys.argv[3], encoding="utf-8"))
fr = est["criacoes"][-1]["fronteira"]


def niveis(rede):
    u, o = [0] * 8, []
    for i, j in rede:
        nv = max(u[i], u[j]) + 1; u[i] = u[j] = nv; o.append(nv)
    return o


base = carga["redes"]["otima"]
niv = niveis(base)
for f in fr:
    g = dict(p.split("=") for p in f["id"].split("|")[1:])
    mant = [q for q in range(len(base)) if not int(g.get(f"rem_{q}", 0))]
    mant.sort(key=lambda q: (niv[q], float(g.get(f"pri_{q}", 0.5)), q))
    rede = [tuple(base[q]) for q in mant]
    print(f["medidas"]["razao_vs_melhor"], "registradores=", g["registradores"], "variante=", g["variante"], "rede=", rede)
ids = [dict(p.split("=") for p in f["id"].split("|")[1:]) for f in fr]
iguais = [x for x in ids[0] if x.startswith("pri_") and ids[0][x] == ids[2][x]]
print("genes pri iguais entre o 1o e o 3o da fronteira (seq 3 e seq 9):", len(iguais), "de 28")
