"""Coerencia interna e ordem no tempo dos registros da corrida de 8 elementos (deverser, 29/09).

Le como dados (nao executa nada do repositorio):
  argv[1] pasta corrida_motor8
  argv[2] corrida_motor8_roteiro.log
  argv[3] pasta 03_motor_de_29-09/saida/calculadora/ordenacao/motor_respostas_8

Uso: python3 -I coerencia.py <corrida_motor8> <roteiro.log> <motor_respostas_8>
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys


def sha_motor(obj):
    # a mesma serializacao declarada em compilador/motor.py (sha), reimplementada aqui
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def canon(x):
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, dict):
        return {k: canon(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [canon(v) for v in x]
    return x


def hash_nucleo(obj):
    # a mesma serializacao declarada em bancada/nucleo/modelo.py (_hash), reimplementada aqui
    return hashlib.sha256(json.dumps(canon(obj), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def t(s):
    return dt.datetime.fromisoformat(s)


def main():
    pasta, roteiro, saida03 = sys.argv[1:4]
    J = lambda *p: json.load(open(os.path.join(pasta, *p), encoding="utf-8"))
    est, aud, prob = J("estado.json"), J("auditoria.json"), J("problema.json")
    diario = [json.loads(l) for l in open(os.path.join(pasta, "diario.jsonl"), encoding="utf-8")]
    ledger = [json.loads(l) for l in open(os.path.join(pasta, "ledger.jsonl"), encoding="utf-8")]
    out = {}

    # 1 e 2: os hashes do diario contra os arquivos de resposta
    nomes = sorted(os.listdir(os.path.join(pasta, "respostas")))
    cop = {e["id"]: e for e in diario if e["evento"] == "resposta_copiada"}
    resp = {e["id"]: e for e in diario if e["evento"] == "resposta"}
    chk = {}
    for n in nomes:
        pid = n[:-5]
        b = open(os.path.join(pasta, "respostas", n), "rb").read()
        obj = json.loads(b)
        chk[pid] = {"bytes_confere_resposta_copiada": hashlib.sha256(b).hexdigest() == cop[pid]["sha256"],
                    "json_confere_evento_resposta": sha_motor(obj) == resp[pid]["sha256"],
                    "copiada_de": cop[pid]["de"]}
        f03 = os.path.join(saida03, cop[pid]["de"])
        if os.path.exists(f03):
            chk[pid]["arquivo_em_03_saida_igual"] = hashlib.sha256(open(f03, "rb").read()).hexdigest() == cop[pid]["sha256"]
    out["respostas"] = chk
    out["medida_do_alvo_igual_resposta_006"] = open(os.path.join(pasta, "medida_do_alvo_006_medir_alvo.json"), "rb").read() == open(os.path.join(pasta, "respostas", "006_medir_alvo.json"), "rb").read()

    # 3: o hash do modelo
    r4 = json.load(open(os.path.join(pasta, "respostas", "004_propor_modelo.json"), encoding="utf-8"))["modelo"]
    h = sha_motor({k: r4.get(k) for k in ("entradas", "representacao", "modelos", "testes", "exportacao", "carga", "oraculo", "metricas")})
    out["hash_do_modelo_recalculado"] = h
    out["hash_do_modelo_registrado"] = est["modelo"]["hash"]

    # 4 e 5: D e Pi do ledger
    v = ledger[0]
    out["ledger_versoes"] = {k: v[k] for k in ("d", "d_versao", "pi", "pi_versao")}
    out["hash_D_recalculado_do_estado"] = hash_nucleo(est["D"])
    nums = {n: i["aceito"] for n, i in est["numeros"].items()}
    nums["modelo_de_calculo"] = {"valor": est["modelo"]["hash"], "tipo": "escolha", "unidade": None, "incerteza": None,
                                 "metodo": "o modelo que a IA propôs e o motor aceitou", "fonte": "ia"}
    out["hash_Pi_recalculado_do_estado"] = hash_nucleo({"provedor": "compilador", "numeros": nums, "versao": 1, "pai": None, "catalogo": []})
    out["D_confere"] = out["hash_D_recalculado_do_estado"] == v["d"]
    out["Pi_confere"] = out["hash_Pi_recalculado_do_estado"] == v["pi"]

    # 6: contadores
    ger = [e for e in diario if e["evento"] == "geracao"]
    cc = est["criacoes"][-1]["calculo_antes"]["concorrencia"]
    out["diario_eventos_geracao"] = len(ger)
    out["diario_soma_avaliados"] = sum(e["avaliados"] for e in ger)
    out["diario_melhor_violacao_por_lote"] = [e["melhor_violacao"] for e in ger]
    out["diario_horas_dos_lotes"] = [e["hora"][11:19] for e in ger]
    out["diario_intervalos_entre_lotes_s"] = [(t(b["hora"]) - t(a["hora"])).total_seconds() for a, b in zip(ger, ger[1:])]
    out["estado_concorrencia"] = {"codigos_que_concorreram": cc["codigos_que_concorreram"], "geracoes": cc["geracoes"], "parada": cc["parada"], "populacao": cc["sigma"]["populacao"]}
    out["estado_criacao"] = {k: est["criacoes"][-1][k] for k in ("candidatos", "calculados", "validos", "nulos", "segundos", "cadaveres")}
    out["estado_contadores"] = est["contadores"]
    out["auditoria_contadores"] = aud["contadores"]
    out["ledger_vereditos"] = sum(1 for e in ledger if e["tipo"] == "veredito")
    out["regra_384"] = {"48_iniciais_mais_7_geracoes_de_48": 48 + 7 * 48, "8_lotes_de_48": 8 * 48}
    out["segundos"] = {"parada_nsga2": cc["parada"]["segundos"], "criacao": est["criacoes"][-1]["segundos"], "motor_estado": est["contadores"]["segundos_motor"],
                       "motor_auditoria": aud["contadores"]["segundos_motor"], "diferenca_estado_menos_auditoria": round(est["contadores"]["segundos_motor"] - aud["contadores"]["segundos_motor"], 2),
                       "minutos_parada": round(cc["parada"]["segundos"] / 60, 3)}
    # sigma: a populacao pela regra declarada
    s = cc["sigma"]
    lotes = int(max(2, min(16, s["teto_s"] / s["seg_por_lote_medido"] / s["geracoes_minimas"])))
    out["sigma_recalculada"] = {"lotes": lotes, "populacao": lotes * int(prob["paralelo_no_alvo"])}
    out["melhor_violacao_por_ordem"] = cc["melhor_violacao_por_ordem"]
    out["melhor_violacao_por_ordem_decodificada_se_correta"] = [round(0.97 + 0.1 * x, 5) if x < 1 else None for x in cc["melhor_violacao_por_ordem"]]

    # 7: ordem no tempo
    pend = {}
    for n in sorted(os.listdir(os.path.join(pasta, "pendentes"))):
        p = json.load(open(os.path.join(pasta, "pendentes", n), encoding="utf-8"))
        pend[p["id"]] = p["criado_em"]
    out["pendentes_criado_em"] = pend
    eventos = [(e["hora"], e["evento"], e.get("id", "")) for e in diario]
    out["diario_em_ordem"] = all(t(a[0]) <= t(b[0]) for a, b in zip(eventos, eventos[1:]))
    ult_pre = max(t(e["hora"]) for e in diario if e["evento"] in ("resposta", "resposta_copiada", "pedido", "mapa_de_numeros", "modelo_testado", "alvo_medido_pela_ia"))
    out["ultimo_evento_antes_da_busca"] = ult_pre.isoformat()
    out["primeiro_lote"] = ger[0]["hora"]
    out["D_confirmado_antes_da_busca"] = t(resp["002_confirmar_D"]["hora"]) < t(ger[0]["hora"])
    out["distinguibilidade_antes_da_busca"] = t(resp["007_conferir_distinguibilidade"]["hora"]) < t(ger[0]["hora"])
    out["modelo_recebido_em"] = est["modelo"]["recebido_em"]
    # o roteiro
    lin = open(roteiro, encoding="utf-8").read().splitlines()
    horas = [l[:8] for l in lin if re.match(r"\d\d:\d\d:\d\d ", l)]
    out["roteiro_primeira_e_ultima_hora"] = (horas[0], horas[-1])
    out["roteiro_passo_final_ate_desfecho_s"] = None
    for a, b in zip(lin, lin[1:]):
        if a.endswith("passo") and "desfecho" in b:
            ta = dt.datetime.strptime(a[:8], "%H:%M:%S")
            tb = dt.datetime.strptime(b[:8], "%H:%M:%S")
            out["roteiro_passo_final_ate_desfecho_s"] = (tb - ta).total_seconds()
    m = re.search(r'"contadores": \{(.*?)\}', open(roteiro, encoding="utf-8").read(), re.S)
    out["roteiro_contadores"] = json.loads("{" + m.group(1) + "}") if m else None
    out["roteiro_tem_trecho_cortado"] = any(l.startswith("02:41:30 ia contra") for l in lin)
    out["intervencoes_citam_script"] = sorted({re.sub(r".*\((.*)\).*", r"\1", json.loads(l)["texto"]) for l in open(os.path.join(pasta, "intervencoes.jsonl"), encoding="utf-8") if "(" in l})
    out["problema"] = {k: prob[k] for k in ("ia_responde_pelo_criador", "avaliador", "paralelo_no_alvo", "rodadas", "repeticoes", "busca", "populacao")}
    out["pedidos_ao_criador"] = est["contadores"]["pedidos_criador"]
    out["clausulas_confirmadas_por"] = {c["id"]: c.get("confirmada_por") for c in est["D"]["clausulas"]}
    out["exportacao"] = est.get("exportacao")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
