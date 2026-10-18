"""testar_codec.py: a prova da forma canônica nos 25 dias e a ida e volta exata de genes sorteados (todas as peças de L)."""
import sys, time, numpy as np
import codec as K
cab, esc, x = K.ler_tabela("dados/itens.csv")
dias = [x[i * K.MIN_DIA:(i + 1) * K.MIN_DIA] for i in range(x.shape[0] // K.MIN_DIA)]
linhas = open("dados/itens.csv", "rb").read().split(b"\n")[1:-1]
textos = [b"".join(l + b"\n" for l in linhas[i * K.MIN_DIA:(i + 1) * K.MIN_DIA]) for i in range(len(dias))]
t = time.time(); print("forma canônica nos", len(dias), "dias:", K.provar_forma_canonica(dias, textos, esc), f"({time.time() - t:.0f} s)")
cl = K.classificar(esc, dias[5:7])
print("classes:", {K.CLASSES[k]: cl.count(k) for k in range(8)})
rng = np.random.default_rng(1)
falhas = 0
for k in range(300):
    genes = [int(g) for g in rng.integers(0, 1024, 8)]
    grupos = cl if k % 2 else [int(g) for g in rng.integers(0, 8, len(cl))]
    r = K.medir_codec([dias[5]], [textos[5]], esc, grupos, genes)
    if r["estado"] != "ok" or r["erros"]:
        falhas += 1
        if falhas <= 3: print("FALHA", genes, r)
print("300 codecs sorteados (metade com grupos sorteados): falhas", falhas)
