"""grupo_unico.py: o melhor codec único da L para a tabela inteira (todas as colunas num grupo só), pelos 1.024 genes, nos dias 5 e 6."""
import json, time
import codec as K
cab, esc, x = K.ler_tabela("dados/itens.csv")
dias = [x[i * K.MIN_DIA:(i + 1) * K.MIN_DIA] for i in range(x.shape[0] // K.MIN_DIA)]
dev = [dias[5], dias[6]]
grupos = [0] * x.shape[1]
melhor, t0 = None, time.time()
for g in range(1024):
    r = K.medir_codec(dev, [None, None], esc, grupos, [g] + [0] * 7)
    if r["estado"] == "ok" and r["erros"] == 0 and (melhor is None or r["bytes"] < melhor[0]): melhor = (r["bytes"], g, r)
res = {"bytes": melhor[0], "gene": melhor[1], "cadeia": K.gene_para_cadeia(melhor[1]), "medida": melhor[2], "segundos": round(time.time() - t0)}
json.dump(res, open("grupo_unico.json", "w"), ensure_ascii=False, indent=1); print(res)
