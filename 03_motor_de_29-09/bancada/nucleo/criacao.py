"""O laço da 𝔉, o mesmo para todo domínio: C_{k+1} = 𝔉(D, Π, N_k).

A cada passo, a próxima formulação é a primeira da ordem do adaptador que nenhuma restrição válida do ledger elimina e que ainda não
foi julgada. A formulação é construída inteira, julgada, e o veredito entra no ledger; um nulo vira restrições com hipóteses, que
eliminam formulações futuras sem construí-las. O laço segue depois do primeiro corpo aprovado, até o orçamento: a multiplicidade é
esperada. Nenhuma formulação lê o corpo anterior; o que passa de uma para outra é só o ledger.

Com reaproveitar=True, o laço começa com as evidências do ledger que ainda valem em (D, Π) pela regra de transferência; as que caíram
ficam listadas com o motivo.
"""
import time

from bancada.nucleo.ledger import CLASSES_DE_NULO

PRIORIDADE_DO_DESFECHO = ["d_contraditorio", "meio_insuficiente", "modelo_incerto", "orcamento_insuficiente", "candidato_falho"]


def criar(D, Pi, adaptador, ledger, orcamento=None, reaproveitar=True, contexto=None):
    orcamento = dict({"verificacoes": 200, "segundos": 3600.0, "validos": 50}, **(orcamento or {}))
    t0 = time.perf_counter()
    ledger.acrescentar("versoes", {"d": D.hash(), "d_versao": D.versao, "pi": Pi.hash(), "pi_versao": Pi.versao,
                                   "adaptador": adaptador.nome})
    caidas = []
    restricoes = []
    if reaproveitar:
        validas, caidas = ledger.transferir(D, Pi)
        restricoes = [e for e in validas if e.get("adaptador") == adaptador.nome]
    # o adaptador vê as evidências que valem (as reaproveitadas e as que esta criação acrescenta), para reusar medidas cujas hipóteses
    # continuam de pé
    contexto = dict(contexto or {}, reaproveitadas=list(restricoes), evidencias=restricoes)
    julgadas, validos, nulos = set(), [], []
    cont = {"formulacoes": 0, "verificacoes": 0, "puladas_por_restricao": 0, "impossiveis_sem_verificar": 0}
    # a classe do nulo de onde cada restrição saiu: uma formulação eliminada por restrição conta no desfecho com a classe dela (sem
    # isso, um meio insuficiente já aprendido viraria só candidato falho na criação seguinte)
    origem, ultimo = {}, {}
    for e in ledger.entradas:
        if e["tipo"] == "veredito" and e.get("nulo"):
            ultimo[e["formulacao_id"]] = e["nulo"]["classe"]
        elif e["tipo"] == "evidencia" and e.get("restricao"):
            origem[e["seq"]] = e.get("classe_do_nulo") or ultimo.get(e.get("origem"), "candidato_falho")
    eliminadas = {}
    custo = {}
    interrompida = None
    for f in adaptador.formulacoes(D, Pi):
        if f["id"] in julgadas:
            continue
        quem = next((r for r in restricoes if r.get("restricao") and adaptador.elimina(r["restricao"], f)), None)
        if quem is not None:
            cont["puladas_por_restricao"] += 1
            c = quem.get("classe_do_nulo") or origem.get(quem["seq"], "candidato_falho")
            eliminadas[c] = eliminadas.get(c, 0) + 1
            continue
        if cont["verificacoes"] >= orcamento["verificacoes"]:
            interrompida = "orçamento de verificações"
            break
        if time.perf_counter() - t0 > orcamento["segundos"]:
            interrompida = "orçamento de tempo"
            break
        if len(validos) >= orcamento["validos"]:
            break
        julgadas.add(f["id"])
        cont["formulacoes"] += 1
        ledger.acrescentar("formulacao", {"adaptador": adaptador.nome, "formulacao": f, "d_versao": D.versao, "pi_versao": Pi.versao})
        corpo = adaptador.construir(f, D, Pi, contexto)
        if isinstance(corpo, dict) and corpo.get("_veredito"):
            ver = corpo
            cont["impossiveis_sem_verificar"] += 1
        else:
            ver = adaptador.verificar(corpo, f, D, Pi, contexto)
            cont["verificacoes"] += 1
        for k, v in ver.get("custo", {}).items():
            custo[k] = custo.get(k, 0) + v
        ledger.acrescentar("veredito", {"adaptador": adaptador.nome, "formulacao_id": f["id"],
                                        **{k: v for k, v in ver.items() if k not in ("_veredito", "evidencias")}})
        # as medidas que o verificador tirou, aprovado ou não, também são evidência, cada uma com as hipóteses de que depende
        for m in ver.get("evidencias", []):
            restricoes.append(ledger.acrescentar("evidencia", {"adaptador": adaptador.nome, "origem": f["id"], **m}))
        if ver["aprovado"]:
            ver["forca"] = forca(ver, Pi, restricoes)
            validos.append({"formulacao": f, "corpo": corpo, "veredito": ver})
            continue
        assert ver["nulo"]["classe"] in CLASSES_DE_NULO, ver["nulo"]
        nulos.append(ver["nulo"])
        for r in adaptador.restricoes(ver, f, D, Pi):
            e = ledger.acrescentar("evidencia", {"adaptador": adaptador.nome, "origem": f["id"], "classe_do_nulo": ver["nulo"]["classe"], **r})
            restricoes.append(e)
    cont["eliminadas_por_classe"] = eliminadas
    return _fechar(validos, nulos, interrompida, contexto, caidas, cont, custo, t0, set(eliminadas))


def forca(ver, Pi, evidencias):
    """A força da conclusão de um veredito aprovado: "forte" quando todo número de Π de que as evidências dele dependem é medido,
    calibrado, aproximação declarada ou escolha do criador; "condicional" quando algum é hipótese (e ela é listada). Um número ausente
    não aprova nada, por construção do verificador."""
    usadas = set(ver.get("medidas_reusadas_de", []))
    nomes = set()
    for e in evidencias:
        if e.get("seq") in usadas:
            nomes |= set(e.get("hipoteses", {}).get("pi", {}))
    for m in ver.get("evidencias", []):
        nomes |= set(m.get("hipoteses", {}).get("pi", {}))
    hip = sorted(n for n in nomes if (Pi.numero(n) or {}).get("tipo") == "hipotese")
    return {"conclusao": "condicional" if hip else "forte", "numeros_hipotese": hip, "numeros_usados": len(nomes)}


def _fechar(validos, nulos, interrompida, contexto, caidas, cont, custo, t0, classes_eliminadas=()):
    if validos:
        desfecho = "solucao"
    elif interrompida:
        desfecho = "busca_interrompida"
    elif nulos or classes_eliminadas:
        classes = {n["classe"] for n in nulos} | set(classes_eliminadas)
        desfecho = next((c for c in PRIORIDADE_DO_DESFECHO if c in classes), "candidato_falho")
    else:
        desfecho = "familia_esgotada"
    return {"desfecho": desfecho, "validos": validos, "nulos": nulos, "interrompida": interrompida,
            "evidencias_reaproveitadas": len(contexto["reaproveitadas"]), "evidencias_que_cairam": caidas,
            "contagens": dict(cont, segundos=round(time.perf_counter() - t0, 3)), "custo": custo}
