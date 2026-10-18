"""O nulo: sorteio cego e uniforme na mesma L do motor, medido pelo mesmo caminho do motor e julgado pelo mesmo D.

  python3 -B nulo.py <pasta_da_corrida> <modo: principal | todos_mantidos> <semente> <pasta_de_saida>

Lê a pasta da corrida só para leitura (estado.json e problema.json): o modelo que o motor aceitou, o D confirmado, o alvo, o
paralelo, a população e o número de candidatos que o motor mediu. O sorteio usa compilador.gerar._valor_novo, a função do motor
para valores novos. A medida usa compilador.adaptador_maquina.AdaptadorMaquina.medir_lote (executor_generico ->
ferramenta_ordenacao.medir), com rodadas, repetições e paralelo do problema. O julgamento usa avaliar.julgar e
Motor._violacao_pior, como a seleção do motor.
"""
import json
import os
import random
import sys
import time
import types

R = os.environ["R"]
sys.path.insert(0, R)

from bancada.nucleo.modelo import D as Dcls  # noqa: E402
from bancada.provedores.maquina import Alvo  # noqa: E402
from compilador import avaliar, gerar  # noqa: E402
from compilador.adaptador_maquina import AdaptadorMaquina  # noqa: E402
from compilador.motor import Motor  # noqa: E402


def decodificador(codigo):
    """O código do arquétipo, com uma ferramenta muda: executar devolve só a rede que o candidato monta (para registrar a rede)."""
    mudo = types.ModuleType("ferramenta_ordenacao")
    mudo.medir = lambda *a, **k: {}
    sys.modules["ferramenta_ordenacao"] = mudo
    g = {}
    exec(compile(codigo, "<arquetipo>", "exec"), g)
    return g["executar"]


def main():
    # modo: L0 (só o arquétipo rede), L1 (metade rede, metade composição, como a população inicial do motor em m2) ou
    # todos_mantidos (o arquétipo rede com todos os rem_k = 0); criacoes: os índices das criações do motor cujo N o nulo espelha
    pasta, modo, semente, saida, criacoes = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], [int(x) for x in sys.argv[5].split(",")]
    os.makedirs(saida, exist_ok=False)
    e = json.load(open(os.path.join(pasta, "estado.json"), encoding="utf-8"))
    prob = json.load(open(os.path.join(pasta, "problema.json"), encoding="utf-8"))
    modelo, d = e["modelo"], Dcls(e["D"])
    concs = [e["criacoes"][k]["calculo_antes"]["concorrencia"] for k in criacoes]
    N = sum(int(c["codigos_que_concorreram"]) + int(prob["paralelo_no_alvo"]) for c in concs)      # cada busca + o lote que o σ mede antes dela
    lote = int(concs[-1]["sigma"]["populacao"])
    arq = next(a for a in modelo["representacao"]["arquetipos"] if a["nome"] == "rede")
    comp = modelo["representacao"].get("composicao")
    if modo == "L1" and not comp:
        raise SystemExit("o modelo atual não tem composição")
    cfg = prob["alvos"][0]
    alvo = Alvo(**{k: v for k, v in cfg.items() if k in ("id", "tipo", "python", "host", "chave", "pasta_remota", "descricao")})
    ad = AdaptadorMaquina(modelo, [], alvo, None, rodadas=int(prob.get("rodadas", 3)), usar_ledger=False,
                          paralelo=int(prob.get("paralelo_no_alvo", 1)), repeticoes=int(prob.get("repeticoes", 5)), pasta_fotos=None)
    juiz = Motor.__new__(Motor)                      # só os métodos puros de violação; nada do estado do motor é tocado
    executar = decodificador(arq["codigo"])
    carga = {}
    exec(compile(modelo["carga"], "<carga>", "exec"), carga)
    entrada = carga["gerar_carga"](modelo.get("semente", 1))
    r = random.Random(semente)
    cands, vistos = [], set()
    while len(cands) < N:
        if modo == "L1" and r.random() < 0.5:
            # a composição, como em gerar.compostos: o número de peças uniforme, cada peça com _peca_nova, os genes com _valor_novo
            pecas = [gerar._peca_nova(comp["primitivas"], r) for _ in range(r.randint(int(comp.get("min_pecas", 1)), int(comp["max_pecas"])))]
            c = gerar._composto(comp, pecas, {v["nome"]: gerar._valor_novo(v, r) for v in comp.get("variaveis", [])})
        else:
            x = {v["nome"]: gerar._valor_novo(v, r) for v in arq["variaveis"]}
            if modo == "todos_mantidos":
                x.update({k: 0 for k in x if k.startswith("rem_")})
            c = dict(x, _arquetipo="rede", _id=gerar._id("rede", x))
        if c["_id"] not in vistos:
            vistos.add(c["_id"])
            cands.append(c)
    plano = {"modo": modo, "semente": semente, "N": N, "criacoes_espelhadas": criacoes, "lote": lote,
             "por_arquetipo": {a: sum(1 for c in cands if c["_arquetipo"] == a) for a in sorted({c["_arquetipo"] for c in cands})}, "paralelo": ad.paralelo, "rodadas": ad.rodadas, "repeticoes": ad.rep,
             "modelo_hash": modelo["hash"], "alvo": alvo.descrever(), "FERRAMENTA_GXX": os.environ.get("FERRAMENTA_GXX"),
             "FERRAMENTA_GXX_SHA256": os.environ.get("FERRAMENTA_GXX_SHA256"), "inicio": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    json.dump(plano, open(os.path.join(saida, "plano_rodado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t0 = time.perf_counter()
    linhas = []
    with open(os.path.join(saida, "medidas.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for i in range(0, N, lote):
            parte = cands[i:i + lote]
            med = ad.medir_lote(parte)
            for c in parte:
                m = med.get(c["_id"])
                params = {k: v for k, v in c.items() if not k.startswith("_")}
                rede = executar(entrada, **params)["rede"]
                if m is None:
                    li = {"id": c["_id"], "arquetipo": c["_arquetipo"], "params": params, "rede": rede, "erro": True}
                else:
                    vi = juiz._violacao_pior(d, m) + (0 if m.get("correto") else 1.0)
                    jul = {cl["id"]: avaliar.julgar(cl["teste"], m, {}) for cl in d.rigidas()}
                    # "correto" do motor é só o oráculo (a medida concorda com o princípio 0-1); ordenar é erro_de_ordenacao = 0 (r_correto)
                    li = {"id": c["_id"], "arquetipo": c["_arquetipo"], "params": params, "rede": rede, "n_comparadores": len(rede),
                          "oraculo_ok": m.get("correto"), "ordena": bool(m.get("correto")) and m.get("erro_de_ordenacao") == 0, "julgamento": jul, "cumpre_D": bool(m.get("correto")) and all(v == "passa" for v in jul.values()),
                          "violacao_no_pior": round(vi, 6),
                          "medidas": {k: m.get(k) for k in ("erro_de_ordenacao", "razao_vs_melhor", "razao_vs_rede", "razao_vs_simd", "ciclos_por_vetor",
                                                            "ciclos_referencia", "ciclos_simd", "razao_ref_contra_ref", "ruido", "comparadores", "ns_std_sort")}}
                f.write(json.dumps(li, ensure_ascii=False) + "\n")
                f.flush()
                linhas.append(li)
            print(f"{time.strftime('%H:%M:%S')} {min(i + lote, N)}/{N} medidos, que ordenam até aqui: {sum(1 for x in linhas if x.get('ordena'))}", flush=True)
    seg = round(time.perf_counter() - t0, 1)
    corretos = sorted((x for x in linhas if x.get("ordena")), key=lambda x: x["medidas"]["razao_vs_melhor"])
    resumo = dict(plano, fim=time.strftime("%Y-%m-%dT%H:%M:%S%z"), segundos=seg, medidos=len(linhas), erros=sum(1 for x in linhas if x.get("erro")),
                  oraculo_ok=sum(1 for x in linhas if x.get("oraculo_ok")), corretos_que_ordenam=len(corretos), cumprem_D=sum(1 for x in linhas if x.get("cumpre_D")),
                  melhor_violacao=min((x["violacao_no_pior"] for x in linhas if "violacao_no_pior" in x), default=None),
                  melhores_corretos=[{"id": x["id"], "arquetipo": x["arquetipo"], "razao_vs_melhor": x["medidas"]["razao_vs_melhor"], "razao_vs_rede": x["medidas"]["razao_vs_rede"],
                                      "variante": x["params"]["variante"], "registradores": x["params"]["registradores"], "base": x["params"]["base"],
                                      "n_comparadores": x["n_comparadores"]} for x in corretos[:10]])
    json.dump(resumo, open(os.path.join(saida, "resumo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: resumo[k] for k in ("N", "segundos", "medidos", "erros", "oraculo_ok", "corretos_que_ordenam", "cumprem_D", "melhor_violacao")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
