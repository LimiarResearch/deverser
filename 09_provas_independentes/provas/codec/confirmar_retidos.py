"""confirmar_retidos.py: o melhor da máquina, o melhor codec único da L e as alternativas genéricas nos 23 dias retidos (todos menos 5 e 6),
cada dia um bloco. Exatidão conferida em cada dia."""
import json, lzma
import numpy as np
import codec as K
cab, esc, x = K.ler_tabela("dados/itens.csv")
nd = x.shape[0] // K.MIN_DIA
dias = [x[i * K.MIN_DIA:(i + 1) * K.MIN_DIA] for i in range(nd)]
linhas = open("dados/itens.csv", "rb").read().split(b"\n")[1:-1]
textos = [b"".join(l + b"\n" for l in linhas[i * K.MIN_DIA:(i + 1) * K.MIN_DIA]) for i in range(nd)]
ret = [i for i in range(nd) if i not in (5, 6)]
assert K.provar_forma_canonica([dias[i] for i in ret], [textos[i] for i in ret], esc)
m = json.load(open("melhor_da_maquina.json"))
out = {"dias_retidos": ret, "bytes_csv": sum(len(textos[i]) for i in ret)}
for nome, grupos, genes in (("melhor da máquina", m["grupos"], m["genes"]), ("melhor codec único da L (gene 108)", [0] * x.shape[1], [108] + [0] * 7)):
    r = K.medir_codec([dias[i] for i in ret], [None] * len(ret), esc, grupos, genes)
    out[nome] = {"bytes": r["bytes"], "dias_errados": r["erros"], "s_decodificar": round(r["s_decodificar"], 3)}
cs = [lzma.compress(dias[i].T.astype("<i4").tobytes(), preset=9 | lzma.PRESET_EXTREME) for i in ret]
out["colunar int32 + xz -9e"] = {"bytes": sum(map(len, cs))}
out["xz -9e no CSV"] = {"bytes": sum(len(lzma.compress(textos[i], preset=9 | lzma.PRESET_EXTREME)) for i in ret)}
json.dump(out, open("confirmacao_retidos.json", "w"), ensure_ascii=False, indent=1)
ref = out["melhor codec único da L (gene 108)"]["bytes"]
for k, v in out.items():
    if isinstance(v, dict): print(f"{k:40s} {v['bytes']:>9d}  {v['bytes'] / ref:.3f} do codec único  {out['bytes_csv'] / v['bytes']:.0f}x menor que o CSV  {v.get('dias_errados', '')}")
