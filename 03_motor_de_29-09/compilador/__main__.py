"""A linha de comando do compilador.

  python -B -m compilador iniciar <pasta> <problema.json>
  python -B -m compilador passo <pasta>                 avança até precisar de algo de fora; mostra os pedidos pendentes
  python -B -m compilador ver <pasta> <id>              o pedido inteiro
  python -B -m compilador responder <pasta> <id> <arquivo.json>   copia a resposta, sem edição, e registra o hash
  python -B -m compilador intervencao <pasta> "texto"   registra uma intervenção do operador (conta como custo do método)
  python -B -m compilador resumo <pasta>                o resumo do problema, para a avaliação
  python -B -m compilador medir <pasta>                 a ferramenta de medida do alvo, para a IA: imprime uma resposta pronta ao pedido medir_alvo
"""
import hashlib
import json
import os
import shutil
import sys

from .motor import Motor, agora


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    cmd, pasta = a[0], a[1]
    if cmd == "iniciar":
        os.makedirs(pasta, exist_ok=False)
        shutil.copy(a[2], os.path.join(pasta, "problema.json"))
        m = Motor(pasta)
        m.diario("iniciado", problema=os.path.basename(a[2]))
        m._gravar("estado.json", m.estado)
        print(pasta)
        return
    m = Motor(pasta)
    if cmd == "passo":
        sit = m.passo()
        print(json.dumps(sit, ensure_ascii=False, indent=1, default=str))
        for pid in sit["pendentes"]:
            p = m._ler(os.path.join("pendentes", pid + ".json"))
            print(f"--- pendente {pid} para {p['para']}: {p['tipo']}")
    elif cmd == "ver":
        print(json.dumps(m._ler(os.path.join("pendentes", a[2] + ".json")), ensure_ascii=False, indent=1))
    elif cmd == "responder":
        with open(a[3], "rb") as f:
            b = f.read()
        json.loads(b)
        with open(os.path.join(pasta, "respostas", a[2] + ".json"), "wb") as f:
            f.write(b)
        m.diario("resposta_copiada", id=a[2], sha256=hashlib.sha256(b).hexdigest(), de=os.path.basename(a[3]))
        print("copiada", a[2])
    elif cmd == "mundo":
        # python -m compilador mundo <pasta> <arquivo.json>: {"artefato", "resultado": "falhou" ou "cumpriu", "detalhe", "medida"}
        Motor(a[1]).registrar_mundo(json.load(open(a[2], encoding="utf-8")))
    elif cmd == "medir":
        print(json.dumps(m.resposta_de_medida(), ensure_ascii=False, indent=1, default=str))
    elif cmd == "intervencao":
        with open(os.path.join(pasta, "intervencoes.jsonl"), "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"hora": agora(), "texto": a[2]}, ensure_ascii=False) + "\n")
        print("registrada")
    elif cmd == "resumo":
        e = m.estado
        print(json.dumps({"desfecho": e["desfecho"], "contadores": e["contadores"], "modelos": e["modelos"],
                          "numeros": {n: {"tipo": (i.get("aceito") or {}).get("tipo", "ausente"), "fonte": (i.get("aceito") or {}).get("fonte"),
                                          "recusados": len(i.get("recusados", []))} for n, i in e["numeros"].items() if not Motor._do_perfil(i)},
                          "criacoes": [{k: c.get(k) for k in ("rotulo", "validos", "desfecho", "calculados", "reusados", "segundos", "forca", "nulos")} for c in e["criacoes"]],
                          "escolhido": (e["criacoes"][-1].get("escolhido") or {}).get("id") if e["criacoes"] else None,
                          "exportacao": e.get("exportacao"), "mudancas": e.get("mudancas")}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
