"""nulo_codec3.py MODO N SEMENTE SAIDA: os controles da versão 3, com o mesmo orçamento e o mesmo V (d_codec3).
cego       fotos v3 sorteadas pela codificação;
estruturado  o melhor codec único (gene 108 no grupo 0) mais 64 exceções sorteadas, com grupos e cadeias sorteados para os grupos 1 a 7;
escalada   subida simples a partir do melhor codec único: o operador de mutação da própria codificação (1 a 3 campos), aceita se a
           distância não piora (o que um praticante faria com o mesmo orçamento)."""
import json, sys, time
import numpy as np
import d_codec3 as DC
modo, N, sem, saida = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
av = DC.Avaliador(); cod = av.cod; rng = np.random.default_rng(sem)
def foto_estruturada():
    grupos = [0] * DC.NC
    for j in rng.choice(DC.NC, DC.NE, replace=False): grupos[int(j)] = int(rng.integers(1, DC.NG))
    genes = [108] + [int(g) for g in rng.integers(0, 1024, DC.NG - 1)]
    return cod.canonizar(cod.codificar((tuple(grupos), tuple(genes))))
atual = cod.canonizar(cod.codificar((tuple([0] * DC.NC), tuple([108] + [int(g) for g in rng.integers(0, 1024, DC.NG - 1)]))))
d_atual = None
melhor, primeiro, t0 = None, None, time.time()
with open(saida + ".jsonl", "w") as f:
    for i in range(N):
        if modo == "cego": foto = cod.sortear(rng)
        elif modo == "estruturado": foto = foto_estruturada()
        else: foto = atual if d_atual is None else cod.mutar(atual, rng)
        r = av.medir([foto])[0]; res = DC.julgar(r)
        if modo == "escalada" and (d_atual is None or res["distancia"] <= d_atual): atual, d_atual = foto, res["distancia"]
        v = r["valores"][1] if r["estado"] == "ok" else None
        f.write(json.dumps({"i": i, "estado": r["estado"], "log2_bytes_sobre_ref": v, "nfal": res["nfal"], "distancia": res["distancia"]}) + "\n")
        if v is not None and (melhor is None or v < melhor[0]): melhor = (v, i, cod.decodificar(foto))
        if res["nfal"] == 0 and primeiro is None: primeiro = i
        if (i + 1) % 500 == 0:
            print(f"{modo}: {i + 1}/{N} medidos; melhor bytes/ref {2 ** melhor[0]:.4f}; primeiro que cumpre D: {primeiro} ({time.time() - t0:.0f} s)", flush=True)
json.dump({"modo": modo, "N": N, "semente": sem, "melhor_bytes_sobre_ref": 2 ** melhor[0], "melhor_i": melhor[1], "melhor_corpus": [list(melhor[2][0]), list(melhor[2][1])],
           "primeiro_que_cumpre_D": primeiro, "segundos": round(time.time() - t0)}, open(saida + ".json", "w"))
print(f"fim {modo}", flush=True)
