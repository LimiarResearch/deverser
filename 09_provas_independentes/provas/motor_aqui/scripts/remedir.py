"""A remedida (contra a maldição do vencedor): os melhores que ordenam de cada busca e a vencedora de 29/09, medidos de novo em
processo novo, 5 rodadas, com o mesmo medidor do motor (executor_generico -> ferramenta_ordenacao.medir, 21 repetições da carga),
em sequência (sem paralelo), com a ordem dos candidatos mudando a cada rodada.

  python3 -B remedir.py <pasta_da_corrida> <estado_29-09.json> <rede_vencedora_29-09.json> <saida> <rodadas> <grupo>=<fonte> ...

Cada grupo é "motor=<pasta_da_corrida>" (os 5 melhores que ordenam no ledger da criação) ou "<nome>=<pasta de um nulo>" (os 5
melhores que ordenam em medidas.jsonl). A vencedora de 29/09 entra sempre, como "vencedora_29-09".
"""
import json
import os
import statistics
import sys
import tempfile
import time
import types

R = os.environ["R"]
sys.path.insert(0, R)

from bancada.provedores.maquina import Alvo  # noqa: E402
from compilador.adaptador_maquina import EXECUTOR  # noqa: E402

K = 5
CAMPOS = ("razao_vs_melhor", "razao_vs_rede", "razao_vs_simd", "ciclos_por_vetor", "ciclos_referencia", "ciclos_simd", "razao_ref_contra_ref", "ruido",
          "erro_de_ordenacao", "comparadores")


def params_de(f):
    return {k: v for k, v in f.items() if not k.startswith("_") and k != "id"}


def do_motor(pasta):
    """Os K melhores que ordenam (erro zero e oráculo de acordo) entre as medidas que o motor guardou: os vereditos da criação no ledger."""
    L = [json.loads(l) for l in open(os.path.join(pasta, "ledger.jsonl"), encoding="utf-8")]
    form = {}
    for x in L:
        if x.get("tipo") == "formulacao":
            f = x["formulacao"]
            form[f.get("_id") or f.get("id")] = f
    vistos, out = set(), []
    ver = [x for x in L if x.get("tipo") == "veredito" and (x.get("medidas") or {}).get("correto") == 1 and (x.get("medidas") or {}).get("erro_de_ordenacao") == 0]
    for x in sorted(ver, key=lambda x: x["medidas"]["razao_vs_melhor"]):
        fid = x["formulacao_id"]
        if fid in vistos:
            continue
        vistos.add(fid)
        out.append({"id": fid, "params": params_de(form[fid]), "na_busca": {k: x["medidas"].get(k) for k in CAMPOS}, "aprovado_na_busca": x.get("aprovado")})
    return out[:K], len(ver)


def do_nulo(pastas):
    L = [json.loads(l) for pasta in pastas.split(",") for l in open(os.path.join(pasta, "medidas.jsonl"), encoding="utf-8")]
    ok = sorted((x for x in L if x.get("ordena")), key=lambda x: x["medidas"]["razao_vs_melhor"])
    return [{"id": x["id"], "params": x["params"], "na_busca": x["medidas"], "aprovado_na_busca": x.get("cumpre_D")} for x in ok[:K]], len(ok)


def fonte_sha(carga, rede, params):
    """O hash da fonte C++ que a ferramenta gera para o candidato (o mesmo cálculo de ferramenta_ordenacao.medir, sem compilar):
    dois candidatos com o mesmo hash são o mesmo programa."""
    import hashlib
    import importlib.util
    spec = importlib.util.spec_from_file_location("ferramenta_real", os.path.join(R, "compilador", "ferramenta_ordenacao.py"))
    fe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fe)
    n = carga["n"]
    comps, ref = fe.normalizar(n, rede), fe.normalizar(n, carga["referencia"])
    src = (fe.MOLDE.replace("__N__", str(n)).replace("__CAND__", fe._corpo(n, comps, params["variante"], bool(int(params["registradores"]))))
           .replace("__REFE__", fe._corpo(n, ref, "ternario", True)).replace("__REFS__", fe._simd(n, ref, False)))
    return hashlib.sha256(src.encode()).hexdigest()[:24]


def rede_de(codigo, carga, params):
    mudo = types.ModuleType("ferramenta_ordenacao")
    mudo.medir = lambda *a, **k: {}
    sys.modules["ferramenta_ordenacao"] = mudo
    g = {}
    exec(compile(codigo, "<arquetipo>", "exec"), g)
    return g["executar"](carga, **params)["rede"]


def main():
    pasta, est29, rv29, saida, rodadas = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    grupos = [a.split("=", 1) for a in sys.argv[6:]]
    os.makedirs(saida, exist_ok=False)
    e = json.load(open(os.path.join(pasta, "estado.json"), encoding="utf-8"))
    prob = json.load(open(os.path.join(pasta, "problema.json"), encoding="utf-8"))
    m = e["modelo"]
    arq = next(a for a in m["representacao"]["arquetipos"] if a["nome"] == "rede")
    g = {}
    exec(compile(m["carga"], "<carga>", "exec"), g)
    carga = g["gerar_carga"](m.get("semente", 1))
    cands = []
    contagem = {}
    for nome, fonte in grupos:
        lst, n_ok = do_motor(fonte) if nome == "motor" else do_nulo(fonte)
        contagem[nome] = {"que_ordenam_na_fonte": n_ok, "levados": len(lst)}
        for i, c in enumerate(lst):
            cands.append(dict(c, grupo=nome, rotulo=f"{nome}_{i + 1}"))
    e29 = json.load(open(est29, encoding="utf-8"))
    f29 = e29["criacoes"][-1]["escolhido"]["formulacao"]
    v29 = json.load(open(rv29, encoding="utf-8"))
    c29 = {"id": f29["_id"], "params": params_de(f29), "grupo": "vencedora_29-09", "rotulo": "vencedora_29-09",
           "na_busca": {k: v29["medidas_no_servidor"].get(k) for k in CAMPOS}, "aprovado_na_busca": True, "medida_na_busca_foi": "na VPS em 29/09"}
    if [list(x) for x in rede_de(arq["codigo"], carga, c29["params"])] != v29["rede_vencedora"]:
        raise SystemExit("a rede decodificada da vencedora de 29/09 não bate com rede_vencedora.json")
    cands.append(c29)
    for c in cands:
        c["rede"] = [list(x) for x in rede_de(arq["codigo"], carga, c["params"])]
        c["fonte_sha256_24"] = fonte_sha(carga, c["rede"], c["params"])
    alvo = Alvo(**{k: v for k, v in prob["alvos"][0].items() if k in ("id", "tipo", "python", "host", "chave", "pasta_remota", "descricao")})
    n = len(cands)
    ordens = []
    for k in range(rodadas):
        s = (k * n) // rodadas
        o = list(range(n))[s:] + list(range(n))[:s]
        ordens.append(o[::-1] if k % 2 else o)
    json.dump({"candidatos": cands, "contagem": contagem, "ordens": [[cands[i]["rotulo"] for i in o] for o in ordens], "rodadas": rodadas,
               "alvo": alvo.descrever(), "FERRAMENTA_GXX": os.environ.get("FERRAMENTA_GXX"), "FERRAMENTA_GXX_SHA256": os.environ.get("FERRAMENTA_GXX_SHA256"),
               "inicio": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
              open(os.path.join(saida, "plano_rodado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t0 = time.perf_counter()
    medidas = {c["rotulo"]: [] for c in cands}
    with open(os.path.join(saida, "medidas.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for k, o in enumerate(ordens):
            for pos, i in enumerate(o):
                c = cands[i]
                codigo = m["representacao"]["composicao"]["codigo"] if "pecas" in c["params"] else arq["codigo"]
                t = {"carga": m["carga"], "candidato": codigo, "metricas": m.get("metricas"), "oraculos": [m["oraculo"]],
                     "params": c["params"], "semente": m.get("semente", 1), "repeticoes": 1, "rodadas": 1, "tempo_limite_s": m.get("tempo_limite_s", 300)}
                with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8", newline="\n") as fh:
                    json.dump(t, fh)
                    caminho = fh.name
                try:
                    r = alvo.executar(EXECUTOR, "medir", caminho, timeout=int(t["tempo_limite_s"]) * 2)
                finally:
                    os.unlink(caminho)
                met = r.get("metricas") or {}
                li = {"rodada": k, "posicao": pos, "rotulo": c["rotulo"], "hora": time.strftime("%H:%M:%S"), "erro": r.get("erro"),
                      "oraculos_ok": r.get("oraculos_ok"), **{q: met.get(q) for q in CAMPOS}}
                f.write(json.dumps(li, ensure_ascii=False) + "\n")
                f.flush()
                medidas[c["rotulo"]].append(li)
            print(f"{time.strftime('%H:%M:%S')} rodada {k + 1}/{rodadas} feita", flush=True)
    seg = round(time.perf_counter() - t0, 1)
    tab = []
    for c in cands:
        ms = [x for x in medidas[c["rotulo"]] if not x["erro"]]
        lin = {"rotulo": c["rotulo"], "grupo": c["grupo"], "id": c["id"], "fonte_sha256_24": c["fonte_sha256_24"],
               "arquetipo": "composicao" if "pecas" in c["params"] else "rede", "variante": c["params"]["variante"], "registradores": c["params"]["registradores"],
               "base": c["params"]["base"], "comparadores": len(c["rede"]), "rede": c["rede"], "na_busca": c["na_busca"], "medidas_ok": len(ms),
               "oraculos_ok": all(x["oraculos_ok"] for x in ms), "erro_de_ordenacao_max": max((x["erro_de_ordenacao"] for x in ms), default=None)}
        for q in ("razao_vs_melhor", "razao_vs_rede", "razao_vs_simd", "ruido", "razao_ref_contra_ref", "ciclos_por_vetor"):
            vs = [x[q] for x in ms]
            lin[q] = {"mediana": statistics.median(vs), "min": min(vs), "max": max(vs), "rodadas": vs} if vs else None
        tab.append(lin)
    json.dump({"segundos": seg, "fim": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "contagem": contagem, "tabela": tab},
              open(os.path.join(saida, "resumo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for lin in sorted(tab, key=lambda x: x["razao_vs_melhor"]["mediana"]):
        q = lin["razao_vs_melhor"]
        print(f'{lin["rotulo"]:22s} {q["mediana"]:.4f} [{q["min"]:.4f}, {q["max"]:.4f}]  rede {lin["razao_vs_rede"]["mediana"]:.4f}  {lin["variante"]} reg={lin["registradores"]} {lin["base"]} {lin["fonte_sha256_24"][:10]}')


if __name__ == "__main__":
    main()
