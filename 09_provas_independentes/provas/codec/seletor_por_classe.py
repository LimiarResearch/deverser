"""seletor_por_classe.py: para cada classe da regra fixa, os 1.024 genes da L, medidos nos dias de desenvolvimento; guarda o melhor
gene de cada classe (o seletor exaustivo, no estilo do BtrBlocks). A soma por classe é exata: o tamanho do bloco é a soma das partes,
e a decodificação de uma classe usa as colunas de outras classes já decodificadas (a regra da irmã)."""
import json, sys, time
import numpy as np
import codec as K

def bytes_da_classe(blocos, cl, k, gene):
    cadeias = [K.gene_para_cadeia(0)] * 8; cadeias[k] = K.gene_para_cadeia(gene)
    cols = [j for j, c in enumerate(cl) if c == k]
    tot = 0
    for b in blocos:
        enc = K.codificar_bloco(b, cl, cadeias, so=k)
        base = b.copy(); base[:, cols] = -1
        dec = K.decodificar_bloco(enc, b.shape[0], cl, cadeias, so=k, base=base)
        if not np.array_equal(dec, b): return None
        tot += len(enc)
    return tot

cab, esc, x = K.ler_tabela("dados/itens.csv")
dias = [x[i * K.MIN_DIA:(i + 1) * K.MIN_DIA] for i in range(x.shape[0] // K.MIN_DIA)]
cl = K.classificar(esc, dias[5:7])
dev = [dias[5], dias[6]]
res = {}
t0 = time.time()
for k in range(8):
    if k not in cl: continue
    melhor = None
    for g in range(1024):
        try: n = bytes_da_classe(dev, cl, k, g)
        except Exception: n = None
        if n is not None and (melhor is None or n < melhor[0]): melhor = (n, g)
    res[K.CLASSES[k]] = {"bytes": melhor[0], "gene": melhor[1], "cadeia": K.gene_para_cadeia(melhor[1])}
    print(K.CLASSES[k], res[K.CLASSES[k]], f"{time.time() - t0:.0f} s", flush=True)
genes = [res[K.CLASSES[k]]["gene"] if K.CLASSES[k] in res else 0 for k in range(8)]
m = K.medir_codec(dev, [None, None], esc, cl, genes)
res["total_dev"] = m; res["genes"] = genes
json.dump(res, open("seletor_por_classe.json", "w"), ensure_ascii=False, indent=1)
print("total nos dias de desenvolvimento:", m)
