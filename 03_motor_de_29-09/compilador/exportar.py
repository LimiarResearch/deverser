"""A exportação genérica: o que a função exportar da IA devolveu vira arquivo, e o arquivo é relido e conferido.

A função exportar(x, p, saidas) devolve um dicionário com:
- uma chave com o nome de um formato registrado em compilador/formatos (hoje, "primitivas": caixas e cilindros -> glTF, OBJ e PNG),
  gravada e conferida pelo módulo do formato, fora do núcleo;
- "arquivos": {nome: texto} -> gravados como estão (o código de um artefato que roda numa máquina, por exemplo);
- "descricao": {...} -> descricao.json.
Sempre sai escolha.json (a formulação, as medidas, a força da conclusão, os hashes de D, Π e do modelo).
"""
import hashlib
import json
import os

from . import formatos

# os nomes antigos continuam valendo para quem os importava
from .formatos.primitivas import conferir, gltf, obj, render  # noqa: F401


def gravar(pasta, saida, x, ult, estado):
    os.makedirs(pasta, exist_ok=True)
    out = {"ok": True, "arquivos": []}
    esc = {"formulacao": x, "medidas": ult["escolhido"]["medidas"], "forca": ult["escolhido"].get("forca"), "d_hash": hashlib.sha256(json.dumps(estado["D"], sort_keys=True).encode()).hexdigest(),
           "modelo": {"id": estado["modelo"]["id"], "hash": estado["modelo"]["hash"]}, "fronteira": ult.get("fronteira", [])[:20],
           "aviso": "conceito calculado sob as hipóteses declaradas; não é projeto executivo"}
    with open(os.path.join(pasta, "escolha.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(esc, f, ensure_ascii=False, indent=1, default=str)
    out["arquivos"].append("escolha.json")
    if saida.get("descricao"):
        with open(os.path.join(pasta, "descricao.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(saida["descricao"], f, ensure_ascii=False, indent=1, default=str)
        out["arquivos"].append("descricao.json")
    for nome, texto in (saida.get("arquivos") or {}).items():
        nome = os.path.basename(nome)
        with open(os.path.join(pasta, nome), "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        out["arquivos"].append(nome)
    for nome in formatos.REGISTRADOS:
        if saida.get(nome):
            r = formatos.gravar(nome, pasta, saida[nome])
            out["arquivos"] += r.pop("arquivos", [])
            out.update(r)
    return out
