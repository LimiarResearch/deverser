"""Tentativas de recalcular hash_dos_casos so com o que o repositorio traz (id, rotulo, B).
O protocolo nao diz como o hash e calculado, e as definicoes dos casos (as especificacoes) nao estao no repositorio;
um acerto aqui seria sorte. Um erro nao prova nada.

Uso: python3 -I hash_tentativas.py <resultados.jsonl> <protocolo.json>
"""
import hashlib, itertools, json, sys
L = sorted((json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip()), key=lambda r: r["id"])
alvo = json.load(open(sys.argv[2], encoding="utf-8"))["hash_dos_casos"]
semente = json.load(open(sys.argv[2], encoding="utf-8"))["semente"]
formas = {
    "rotulos": [r["rotulo"] for r in L],
    "id_rotulo_B": [{"id": r["id"], "rotulo": r["rotulo"], "B": r["B"]} for r in L],
    "rotulo_B": [{"rotulo": r["rotulo"], "B": r["B"]} for r in L],
    "lista_id_rotulo_B": [[r["id"], r["rotulo"], r["B"]] for r in L],
    "lista_rotulo_B": [[r["rotulo"], r["B"]] for r in L],
    "semente_e_rotulos": {"semente": semente, "casos": [r["rotulo"] for r in L]},
}
tent = 0
for nome, obj in formas.items():
    for sk, sep, asc in itertools.product((True, False), ((", ", ": "), (",", ":")), (True, False)):
        s = json.dumps(obj, sort_keys=sk, separators=sep, ensure_ascii=asc)
        for txt in (s, s + "\n"):
            tent += 1
            if hashlib.sha256(txt.encode("utf-8")).hexdigest() == alvo:
                print("ACERTO:", nome, sk, sep, asc, repr(txt[-1]))
    for junta in ("\n", ""):
        tent += 1
        txt = junta.join(json.dumps(x, sort_keys=True, ensure_ascii=False) for x in (obj if isinstance(obj, list) else [obj]))
        if hashlib.sha256(txt.encode("utf-8")).hexdigest() == alvo:
            print("ACERTO linhas:", nome, repr(junta))
print("tentativas:", tent, "| alvo:", alvo)
