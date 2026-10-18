"""nulo_codec.py MODO N SEMENTE SAIDA: os controles com o mesmo orçamento da máquina, pelo mesmo V (d_codec.Avaliador).
cego         codecs inteiros sorteados pela própria codificação (sortear);
estruturado  o melhor codec único da L (gene 108) em todos os grupos, e só o agrupamento das colunas sorteado (cada coluna num dos 8 grupos)."""
import json, sys, time
import numpy as np
import d_codec as DC
modo, N, sem, saida = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
av = DC.Avaliador(); cod = av.cod; rng = np.random.default_rng(sem)
melhor, primeiro, t0 = None, None, time.time()
with open(saida + ".jsonl", "w") as f:
    for i in range(N):
        if modo == "cego":
            corpus = cod.decodificar(cod.sortear(rng))
        else:
            corpus = cod.decodificar(cod.codificar((tuple(int(g) for g in rng.integers(0, DC.NG, DC.NC)), tuple([108] * DC.NG))))
        r = av.medir_corpus(corpus)
        res = DC.julgar(r)
        f.write(json.dumps({"i": i, "estado": r["estado"], "valores": r.get("valores"), "nfal": res["nfal"], "distancia": res["distancia"]}) + "\n")
        if r["estado"] == "ok" and (melhor is None or r["valores"][1] < melhor[0]):
            melhor = (r["valores"][1], i, corpus)
        if res["nfal"] == 0 and primeiro is None:
            primeiro = i
        if (i + 1) % 500 == 0:
            print(f"{modo}: {i + 1}/{N} medidos; melhor bytes/ref {melhor[0]:.4f}; primeiro que cumpre D: {primeiro} ({time.time() - t0:.0f} s)", flush=True)
json.dump({"modo": modo, "N": N, "semente": sem, "melhor_bytes_sobre_ref": melhor[0], "melhor_i": melhor[1], "melhor_corpus": [list(melhor[2][0]), list(melhor[2][1])],
           "primeiro_que_cumpre_D": primeiro, "segundos": round(time.time() - t0)}, open(saida + ".json", "w"))
print(f"fim {modo}", flush=True)
