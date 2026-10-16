"""O motor do compilador: guarda o estado do problema, decide o que falta, emite pedidos, confere as respostas, cria, mede a
sensibilidade, cruza com o modelo alternativo, escolhe, exporta e diz o que refazer quando algo muda.

Uma pasta por problema:
  problema.json           o problema (a intenção, o tipo, os alvos, o orçamento)
  estado.json             o estado do motor
  pendentes/<id>.json     os pedidos esperando resposta (para "ia", "criador" ou "avaliador")
  respostas/<id>.json     as respostas, copiadas sem edição pelo operador
  diario.jsonl            tudo o que o motor fez, com hora
  ledger.jsonl            o ledger da bancada (formulações, vereditos, evidências)
  dados/                  os arquivos de dados que a IA baixou (cada um com hash)
  artefatos/              o que sai
O motor avança até precisar de algo de fora, grava os pedidos e para. Rodar de novo, com as respostas, continua dali.
"""
import copy
import datetime as dt
import hashlib
import json
import os
import random
import time

import numpy as np

from bancada.nucleo.criacao import criar
from bancada.nucleo.ledger import Ledger
from bancada.nucleo.modelo import D, Pi
from bancada.nucleo.selecao import pareto, preferir

from . import avaliar, calcular, gerar, numeros, trabalho
from .adaptador import AdaptadorCompilado

ESQUEMAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "esquemas.md")


def agora():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Motor:
    def __init__(self, pasta):
        self.pasta = pasta
        self.problema = self._ler("problema.json")
        self.estado = self._ler("estado.json") or {"fase": "inicio", "D": None, "D_confirmado": False, "modelo": None, "modelos": [],
                                                    "alternativo": None, "numeros": {}, "testes": [], "criacoes": [], "cruzamento": None,
                                                    "contadores": {"pedidos_ia": 0, "pedidos_criador": 0, "pedidos_avaliador": 0,
                                                                   "consultas_de_dados": 0, "avaliacoes": 0, "passos": 0,
                                                                   "segundos_motor": 0.0},
                                                    "pedidos": {}, "sensibilidade_pedida": [], "desfecho": None, "mudancas": {}}
        for sub in ("pendentes", "respostas", "dados", "artefatos"):
            os.makedirs(os.path.join(pasta, sub), exist_ok=True)
        self.ledger = Ledger(os.path.join(pasta, "ledger.jsonl"))

    # ------------------------------------------------------------------ arquivos
    def _ler(self, nome):
        c = os.path.join(self.pasta, nome)
        if not os.path.exists(c):
            return None
        with open(c, encoding="utf-8") as f:
            return json.load(f)

    def _gravar(self, nome, obj):
        with open(os.path.join(self.pasta, nome), "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1, default=str)

    def diario(self, evento, **k):
        with open(os.path.join(self.pasta, "diario.jsonl"), "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"hora": agora(), "evento": evento, **k}, ensure_ascii=False, default=str) + "\n")

    def _juntar_ao_mapa(self, numeros_, quem):
        mapa = self.estado.setdefault("mapa_numeros", {})
        for nome, x in numeros_.items():
            if not isinstance(x, dict):
                continue
            m = mapa.setdefault(nome, {"clausulas": [], "origens": []})
            m["clausulas"] = sorted(set(m["clausulas"]) | set(x.get("clausulas") or []))
            if quem not in m["origens"]:
                m["origens"].append(quem)
            for k in ("unidade", "grandeza", "onde", "por_que"):
                if x.get(k) and not m.get(k):
                    m[k] = x[k]

    def _quem_decide(self):
        """Quem responde às decisões do criador (confirmar o D, autorizar hipóteses): o criador, ou a IA dele quando o problema pede
        ("ia_responde_pelo_criador"). A autorização de trabalho fora da caixa é sempre do criador, porque roda comandos na máquina dele."""
        return "ia" if self.problema.get("ia_responde_pelo_criador") else "criador"

    def _papel_de_criador(self):
        if self._quem_decide() != "ia":
            return {}
        return {"papel": "responda no lugar do criador: decida e justifique cada decisão; cada uma fica marcada como decisão da IA no resultado, "
                         "e o criador pode revê-la"}

    @staticmethod
    def _causa(tipo, conteudo):
        """Onde está a lacuna que este pedido tenta fechar: D (a intenção), Π (os números do meio), L (a linguagem das criações), M (o
        modelo) ou a busca. É o que o laço 𝔉 distingue em cada volta."""
        if tipo in ("formular_D", "confirmar_D"):
            return "D"
        if tipo in ("buscar_numero", "medir_alvo", "autorizar_hipotese", "mapear_numeros"):
            return "Π"
        if tipo == "modelo_alternativo":
            return "M: validação independente"
        if tipo == "conferir_distinguibilidade":
            return "Π e D: o meio entrega a informação que decide cada cláusula?"
        if tipo == "propor_modelo":
            return "L e M: a primeira proposta"
        if tipo == "revisar":
            if conteudo.get("contraexemplos"):
                return "M: o modelo independente discorda"
            if conteudo.get("falha_no_mundo"):
                return "mundo: um artefato falhou fora do modelo; M refutado ou número ausente"
            if conteudo.get("fora_do_dominio"):
                return "M: formas de L fora do domínio em que M foi validado"
            if conteudo.get("situacao"):
                return "L ou D: nenhum candidato cumpre D, e nenhum número de Π muda isso"
            falhas = conteudo.get("falhas") or []
            if falhas and all(f.get("tipo") == "cobertura_de_pi" for f in falhas):
                return "Π: o mapa tem números que o modelo não cobre"
            return "M: um teste refutou o modelo, ou ele não cobre o que D julga"
        return None

    def pedir(self, para, tipo, conteudo):
        c = self.estado["contadores"]
        causa = self._causa(tipo, conteudo)
        if causa and isinstance(conteudo, dict):
            conteudo = dict(conteudo, causa=causa)
        chave = {"ia": "pedidos_ia", "criador": "pedidos_criador", "avaliador": "pedidos_avaliador"}[para]
        c[chave] += 1
        pid = f"{len(self.estado['pedidos']) + 1:03d}_{tipo}"
        p = {"id": pid, "para": para, "tipo": tipo, "conteudo": conteudo, "criado_em": agora(), "formato_da_resposta": f"ver {os.path.basename(ESQUEMAS)}, seção {tipo}"}
        self.estado["pedidos"][pid] = {"para": para, "tipo": tipo, "respondido": False}
        self._gravar(os.path.join("pendentes", pid + ".json"), p)
        self.diario("pedido", id=pid, para=para, tipo=tipo, causa=causa)
        return pid

    def respostas_novas(self):
        out = []
        for pid, info in sorted(self.estado["pedidos"].items()):
            if info["respondido"]:
                continue
            r = self._ler(os.path.join("respostas", pid + ".json"))
            if r is not None:
                out.append((pid, info, r))
        return out

    def pendentes(self):
        return [pid for pid, i in self.estado["pedidos"].items() if not i["respondido"]]

    # ------------------------------------------------------------------ D e Π
    def D(self):
        return D(self.estado["D"]) if self.estado["D"] else None

    @property
    def modo(self):
        """Como o candidato é julgado, e o único desvio do motor: "calculo" (o modelo da IA calcula as saídas a partir de Π, na caixa
        local, com a incerteza propagada) ou "medida" (o candidato roda num alvo, e as saídas são medidas lá). Nenhum dos dois fala de
        domínio. O mundo do problema (silício ou real) só muda o tipo do "onde" e as perguntas, e não entra no motor."""
        p = self.problema
        return p.get("execucao") or ("medida" if p.get("tipo") == "maquina" else "calculo")

    def alvo(self):
        from bancada.provedores.maquina import Alvo
        cfg = dict(self.problema["alvos"][0])
        esc = (self.estado.get("D") or {}).get("escopo", {})
        for c in self.problema["alvos"]:
            if esc.get("alvo") in (c["id"], c.get("nome")):
                cfg = dict(c)
        return Alvo(**{k: v for k, v in cfg.items() if k in ("id", "tipo", "python", "host", "chave", "pasta_remota", "descricao")})

    def resposta_de_medida(self):
        """A ferramenta que o motor oferece à IA: mede o perfil do alvo e devolve a resposta pronta para o pedido medir_alvo. Quem
        responde é a IA: o número só entra em Π como resposta dela (regra adotada em 28/09: o D e o Π vêm do usuário e da IA dele,
        nunca do motor)."""
        from bancada.adaptadores.componente.adaptador import EXECUTOR as PERFIL
        from bancada.provedores.maquina import medir_perfil
        pi = medir_perfil(self.alvo(), PERFIL)
        return {"numeros": {n: dict(x, metodo=(x.get("metodo") or "") + " (ferramenta de medida do motor)") for n, x in pi.dados["numeros"].items()}}

    @staticmethod
    def _do_perfil(info):
        return bool(info.get("fornecido_pelo_motor") or info.get("perfil_do_alvo"))

    def Pi(self):
        nums = {}
        H = ((self.estado.get("D") or {}).get("escopo") or {}).get("horizonte")
        for nome, info in self.estado["numeros"].items():
            nums[nome] = info["aceito"] if info.get("aceito") else {"valor": None, "tipo": "ausente", "unidade": info.get("unidade"),
                                                                    "grandeza": info.get("grandeza"), "incerteza": None}
            # volta 3 (emenda 1): a deriva de cada número no horizonte H alarga a incerteza, e U cobre a trajetória do meio
            if H and info.get("aceito") and info.get("deriva"):
                nums[nome] = _no_horizonte(nums[nome], float(info["deriva"]), float(H))
        if self.estado["modelo"]:
            nums["modelo_de_calculo"] = {"valor": self.estado["modelo"]["hash"], "tipo": "escolha", "unidade": None, "incerteza": None,
                                         "metodo": "o modelo que a IA propôs e o motor aceitou", "fonte": "ia"}
        return Pi({"provedor": "compilador", "numeros": nums, "versao": len(self.estado["criacoes"]) + 1})

    def p_base(self):
        """Os valores de Π para o modelo: números no centro, séries carregadas do arquivo; e os intervalos dos que têm incerteza."""
        base, inter = {}, {}
        for nome, info in self.estado["numeros"].items():
            a = info.get("aceito")
            if not a:
                base[nome] = None
                continue
            if isinstance(a["valor"], dict) and "arquivo" in a["valor"]:
                base[nome] = carregar_serie(os.path.join(self.pasta, a["valor"]["arquivo"]))
                continue
            base[nome] = a["valor"]
            if a.get("incerteza"):
                inter[nome] = a["incerteza"]
        return base, inter

    # ------------------------------------------------------------------ as respostas
    def aplicar(self, pid, info, r):
        t = info["tipo"]
        self.estado["pedidos"][pid]["respondido"] = True
        self.diario("resposta", id=pid, tipo=t, sha256=sha(r))
        if t == "formular_D":
            cls = [dict(c, origem="ia", confirmada=False) for c in r.get("clausulas", [])]
            self.estado["D_proposto"] = {"clausulas": cls, "escopo": r.get("escopo", {}), "ambiguidades": r.get("ambiguidades", []),
                                         "condicoes_de_uso": r.get("condicoes_de_uso", [])}
        elif t == "confirmar_D":
            prop = self.estado["D_proposto"]
            dec = r.get("clausulas", {})
            finais = []
            quem = info.get("para", "criador")
            for c in prop["clausulas"]:
                d = dec.get(c["id"], {"acao": "confirmar"})
                if d["acao"] == "confirmar":
                    finais.append(dict(c, confirmada=True, confirmada_por=quem))
                elif d["acao"] == "corrigir":
                    finais.append(dict(c, **d["clausula"], origem=quem, confirmada=True, confirmada_por=quem, corrigida_de=c.get("enunciado")))
                if quem == "ia":
                    self.estado.setdefault("decisoes_da_ia", []).append({"pedido": pid, "clausula": c["id"], "acao": d["acao"], "justificativa": d.get("justificativa")})
            finais += [dict(c, origem=quem, confirmada=True, confirmada_por=quem) for c in r.get("acrescentar", [])]
            if quem == "ia":
                for k, v in (r.get("ambiguidades") or {}).items():
                    self.estado.setdefault("decisoes_da_ia", []).append({"pedido": pid, "ambiguidade": k, "resposta": v})
                for c in r.get("acrescentar", []):
                    self.estado.setdefault("decisoes_da_ia", []).append({"pedido": pid, "clausula": c.get("id"), "acao": "acrescentar"})
            escopo = dict(prop.get("escopo", {}), **r.get("escopo", {}))
            escopo["respostas_das_ambiguidades"] = r.get("ambiguidades", {})
            dados = {"titulo": self.problema.get("titulo"), "escopo": escopo, "clausulas": finais,
                     "condicoes_de_uso": prop.get("condicoes_de_uso", [])}
            if self.estado["D"]:
                dados = dict(dados, versao=self.estado["D"]["versao"] + 1, pai=sha(self.estado["D"]))
            self.estado["D"] = D(dados).dados
            self.estado["D_confirmado"] = True
        elif t in ("propor_modelo", "revisar"):
            for f in self.estado.get("falhas_no_mundo", []):
                if f.get("pedida_em") == pid:
                    f["resposta"] = {"motivo": r.get("motivo"), "novo_modelo": bool(r.get("modelo")), "mapa_acrescentar": sorted(r.get("mapa_acrescentar") or [])}
            if r.get("mapa_acrescentar"):
                # um número do meio que a falha revelou e que o mapa não tinha: o mapa cresce
                self._juntar_ao_mapa(r["mapa_acrescentar"], "revisao:" + pid)
                self.diario("mapa_cresceu", pedido=pid, numeros=sorted(r["mapa_acrescentar"]))
            if r.get("modelo"):
                m = dict(r["modelo"])
                m["hash"] = sha({k: m.get(k) for k in ("entradas", "representacao", "modelos", "testes", "exportacao", "carga", "oraculo", "metricas")})
                m["id"] = f"m{len(self.estado['modelos']) + 1}"
                m["recebido_em"] = agora()
                self.estado["modelos"].append({"id": m["id"], "hash": m["hash"], "pedido": pid, "motivo": r.get("motivo")})
                self.estado["modelo"] = m
                self.estado["modelo_testado"] = False
                for e in m.get("entradas", []):
                    info_n = self.estado["numeros"].setdefault(e["nome"], {"aceito": None, "recusados": [], "pedidos": 0})
                    velho = (info_n.get("unidade"), info_n.get("grandeza"))
                    info_n.update(unidade=e.get("unidade"), grandeza=e.get("grandeza"), forma=e.get("forma", "escalar"),
                                  descricao=e.get("descricao"), fornecido_pelo_motor=e.get("fornecido_pelo_motor", False))
                    if info_n.get("aceito") and velho != (e.get("unidade"), e.get("grandeza")):
                        info_n["recusados"].append({"candidato": info_n["aceito"], "motivos": ["o modelo passou a pedir outra grandeza ou unidade"]})
                        info_n["aceito"] = None
            if r.get("mudar_D"):
                self.estado["D_proposto"] = {"clausulas": r["mudar_D"]["clausulas"], "escopo": self.estado["D"]["escopo"],
                                             "ambiguidades": [], "condicoes_de_uso": self.estado["D"].get("condicoes_de_uso", []),
                                             "motivo": r["mudar_D"].get("motivo")}
                self.estado["D_confirmado"] = False
        elif t == "buscar_numero":
            for nome, resp in r.get("numeros", {}).items():
                info_n = self.estado["numeros"].get(nome)
                if info_n is None:
                    continue
                self.estado["contadores"]["consultas_de_dados"] += int(resp.get("consultas", 1))
                ent = {"unidade": info_n.get("unidade"), "grandeza": info_n.get("grandeza"), "forma": info_n.get("forma")}
                aceito = None
                for cand in resp.get("candidatos", []):
                    num, mot = numeros.aceitar(ent, cand, self.pasta)
                    if num and aceito is None:
                        aceito = num
                    elif not num:
                        info_n["recusados"].append({"candidato": cand, "motivos": mot})
                        self.diario("dado_recusado", numero=nome, motivos=mot, origem=cand.get("origem"))
                if aceito:
                    if resp.get("deriva") is not None:
                        info_n["deriva"] = resp["deriva"]
                    if info_n.get("aceito") and info_n["aceito"] != aceito:
                        info_n.setdefault("anteriores", []).append(info_n["aceito"])
                    info_n["aceito"] = aceito
                    self.diario("dado_aceito", numero=nome, tipo=aceito["tipo"], fonte=aceito.get("fonte"))
                elif resp.get("hipotese_sugerida") is not None and not info_n.get("aceito"):
                    info_n["hipotese_sugerida"] = resp["hipotese_sugerida"]
                info_n["nao_encontrado"] = resp.get("nao_encontrado")
        elif t == "autorizar_hipotese":
            for nome, ok in r.get("autorizacoes", {}).items():
                info_n = self.estado["numeros"][nome]
                h = info_n.get("hipotese_sugerida")
                if ok and h:
                    pela_ia = info.get("para") == "ia"
                    info_n["aceito"] = {"valor": h["valor"], "unidade": info_n["unidade"], "incerteza": h.get("incerteza"), "tipo": "hipotese",
                                        "grandeza": info_n.get("grandeza"), "metodo": h.get("metodo", "hipótese autorizada pelo criador"),
                                        "fonte": "a IA autorizou a própria hipótese no lugar do criador" if pela_ia else "criador autorizou a hipótese da IA"}
                    if pela_ia:
                        self.estado.setdefault("decisoes_da_ia", []).append({"pedido": pid, "hipotese": nome, "valor": h["valor"], "incerteza": h.get("incerteza")})
                info_n["hipotese_decidida"] = True
        elif t == "mapear_numeros":
            quem = info.get("para", "ia")
            self._juntar_ao_mapa(r.get("numeros") or {}, quem)
            self.diario("mapa_de_numeros", de=quem, numeros=len(r.get("numeros") or {}), no_mapa=len(self.estado["mapa_numeros"]))
        elif t == "autorizar_trabalho":
            h = info.get("conteudo_hash") or (self._ler(os.path.join("pendentes", pid + ".json")).get("conteudo") or {}).get("hash")
            lista = "trabalhos_autorizados" if r.get("autorizado") is True else "trabalhos_recusados"
            self.estado.setdefault(lista, [])
            if h and h not in self.estado[lista]:
                self.estado[lista].append(h)
            self.diario("trabalho_" + ("autorizado" if lista == "trabalhos_autorizados" else "recusado"), hash=h)
        elif t == "medir_alvo":
            tipos = ("medido", "calibrado", "aproximacao", "escolha", "hipotese")
            for nome, x in (r.get("numeros") or {}).items():
                if not isinstance(x, dict) or "valor" not in x or not x.get("metodo"):
                    self.diario("medida_recusada", numero=nome, motivo="sem valor ou sem método")
                    continue
                aceito = {"valor": x["valor"], "unidade": x.get("unidade"), "incerteza": x.get("incerteza"),
                          "tipo": x.get("tipo") if x.get("tipo") in tipos else "hipotese", "metodo": x["metodo"],
                          "fonte": x.get("fonte") or x.get("origem") or "ia", "data": x.get("data"), "vale_para": x.get("vale_para")}
                self.estado["numeros"][nome] = {"aceito": aceito, "recusados": [], "pedidos": 0, "unidade": x.get("unidade"),
                                                "perfil_do_alvo": True, "fornecido_por": "ia"}
            self.estado["alvo_medido_para"] = (self.estado.get("modelo") or {}).get("hash")
            self.diario("alvo_medido_pela_ia", numeros=len(r.get("numeros") or {}))
        elif t == "conferir_distinguibilidade":
            self.estado["distinguibilidade"] = {"para": info.get("chave"), "clausulas": r.get("clausulas") or {}, "por": info.get("para")}
            if info.get("para") == "ia":
                self.estado.setdefault("decisoes_da_ia", []).append({"pedido": pid, "distinguibilidade": r.get("clausulas")})
        elif t == "modelo_alternativo":
            if r.get("modelo"):
                a = dict(r["modelo"])
                a["hash"] = sha(a)
                self.estado["alternativo"] = a
        elif t == "refutar":
            self.estado.setdefault("testes_extras", []).extend(r.get("testes", []))
            self.estado["modelo_testado"] = False

    # ------------------------------------------------------------------ o passo
    def passo(self):
        t0 = time.perf_counter()
        self.estado["contadores"]["passos"] += 1
        for pid, info, r in self.respostas_novas():
            self.aplicar(pid, info, r)
        try:
            self._decidir()
        finally:
            self.estado["contadores"]["segundos_motor"] += round(time.perf_counter() - t0, 2)
            self._gravar("estado.json", self.estado)
        return self.situacao()

    def _orcamento_esgotado(self):
        o, c = self.problema.get("orcamento", {}), self.estado["contadores"]
        return (c["pedidos_ia"] >= o.get("pedidos_ia", 40) or c["consultas_de_dados"] >= o.get("consultas_de_dados", 30)
                or c["avaliacoes"] >= o.get("avaliacoes", 5000))

    def _decidir(self):
        e = self.estado
        if self.pendentes() or e["desfecho"]:
            return
        if self._orcamento_esgotado() and not e["criacoes"]:
            e["desfecho"] = {"tipo": "orcamento_esgotado", "motivo": "o orçamento acabou antes da primeira criação"}
            return
        if not e.get("D_proposto") and not e["D"]:
            self.pedir("ia", "formular_D", {"intencao": self.problema["intencao"], "tipo": self.problema.get("tipo"), "execucao": self.modo, "mundo": self.problema.get("mundo"),
                                             "natureza": "marque cada cláusula com natureza: intencao (o que o criador quer) ou forma (fixa a forma do corpus, como "
                                                         "'biológica'); a forma do corpus é resultado do cálculo, e cláusula de forma só fica se o criador disser que é intenção",
                                             "alvos": self.problema.get("alvos"), "lugar": self.problema.get("lugar")})
            return
        if not e["D_confirmado"]:
            formas = [c["id"] for c in e["D_proposto"]["clausulas"] if c.get("natureza") == "forma"]
            self.pedir(self._quem_decide(), "confirmar_D", dict({"proposta": e["D_proposto"], "como_responder": "confirmar, corrigir ou recusar cada cláusula; responder as ambiguidades",
                                                                 "clausulas_de_forma": formas, "sobre_as_formas": "cada uma é intenção sua ou uma suposição? suposição sai do D e vai para L"
                                                                 if formas else None}, **self._papel_de_criador()))
            return
        # volta 3 (emenda 1): um corpus que vive além do horizonte precisa recalcular a si mesmo; se o D não pede isso, a pergunta é do criador
        esc = e["D"].get("escopo") or {}
        # a chave é o conteúdo das cláusulas e do horizonte, e não a versão do D: a resposta do criador cria uma versão nova com o mesmo conteúdo
        ch = sha([[(c["id"], c.get("enunciado"), c.get("recalcula")) for c in self.D().rigidas()], esc.get("horizonte"), esc.get("alem_do_horizonte")])
        if esc.get("alem_do_horizonte") and not any(c.get("recalcula") for c in self.D().rigidas()) and e.get("horizonte_perguntado") != ch:
            e["horizonte_perguntado"] = ch
            e["D_proposto"] = {"clausulas": e["D"]["clausulas"], "escopo": esc, "ambiguidades": [], "condicoes_de_uso": e["D"].get("condicoes_de_uso", [])}
            e["D_confirmado"] = False
            self.pedir(self._quem_decide(), "confirmar_D", dict({"proposta": e["D_proposto"], "falta": "o corpus vai viver além do horizonte H: o D precisa "
                                                                 "de uma cláusula que peça a ele recalcular a si mesmo (o C★ interno, com o V dele), marcada com "
                                                                 "recalcula; confirme, acrescente essa cláusula ou recuse"}, **self._papel_de_criador()))
            return
        # o mapa dos números do meio: sai do D, cláusula por cláusula, e não do modelo; com avaliador, ele faz o dele sem ver o da IA
        if self.problema.get("mapa_de_numeros", True):
            pedir_mapa = {"D": self._D_para_ia(), "mundo": self.problema.get("mundo"), "execucao": self.modo, "alvos": self.problema.get("alvos"),
                          "lugar": self.problema.get("lugar"),
                          "pedido": "para cada cláusula de D, todos os números do meio que decidem se ela é cumprida ou quanto ela vale: as constantes do "
                                    "meio (do servidor ou do lugar), as propriedades dos materiais ou dos componentes, as cargas, as normas e as incertezas; "
                                    "para cada número, a grandeza, a unidade, onde ele se obtém e por que ele decide a cláusula",
                          "formato": "ver esquemas.md, seção mapear_numeros"}
            if not e.get("mapa_pedido"):
                e["mapa_pedido"] = True
                self.pedir("ia", "mapear_numeros", pedir_mapa)
                return
            if self.problema.get("avaliador") and not e.get("mapa_avaliador_pedido"):
                e["mapa_avaliador_pedido"] = True
                self.pedir("avaliador", "mapear_numeros", dict(pedir_mapa, pedido=pedir_mapa["pedido"] + "; sem ver o mapa de outra IA"))
                return
        if not e["modelo"]:
            self.pedir("ia", "propor_modelo", {"D": self._D_para_ia(), "tipo": self.problema.get("tipo"), "execucao": self.modo, "mundo": self.problema.get("mundo"), "alvos": self.problema.get("alvos"),
                                                "medidas_que_D_julga": sorted({c["teste"]["medida"] for c in self.D().rigidas()}),
                                                "mapa_de_numeros": e.get("mapa_numeros") or None,
                                                "cobertura": "o modelo usa cada número do mapa como entrada, ou o põe em numeros_excluidos com a justificativa",
                                                "formato": "ver esquemas.md"})
            return
        # volta 4 (emenda 1): forma nova pede números novos; o mapa é Mapa(D, L)
        rep_ = e["modelo"].get("representacao") or {}
        formas_decl = list(rep_.get("arquetipos", []))
        if rep_.get("composicao"):
            # em L que compõe, cada primitiva é uma forma: a peça nova também pede os números de que depende
            formas_decl += [dict(q, nome="composicao:" + q["nome"]) for q in rep_["composicao"].get("primitivas", [])]
        arqs = [a["nome"] for a in formas_decl]
        novas = [a for a in arqs if a not in e.get("L_mapeada", [])]
        if novas and self.problema.get("mapa_de_numeros", True) and not self._orcamento_esgotado():
            e["L_mapeada"] = sorted(set(e.get("L_mapeada", [])) | set(arqs))
            self.pedir("ia", "mapear_numeros", {"D": self._D_para_ia(), "formas_novas": [{k: v for k, v in a.items() if k != "codigo"} for a in formas_decl if a["nome"] in novas],
                                                 "mapa_atual": sorted(e.get("mapa_numeros") or {}),
                                                 "pedido": "os números do meio de que estas formas dependem e que o mapa ainda não tem",
                                                 "formato": "ver esquemas.md, seção mapear_numeros"})
            return
        # volta 6 (emenda 1): o mundo volta à conta; cada falha fora do modelo reabre o laço como pergunta sobre M ou sobre Π
        aberta = next((f for f in e.get("falhas_no_mundo", []) if not f.get("pedida_em")), None)
        if aberta:
            e["modelo_testado"] = False
            aberta["pedida_em"] = self.pedir("ia", "revisar", {"falha_no_mundo": aberta, "modelo_id": e["modelo"]["id"],
                                                               "pedido": "a falha refuta M (revise o modelo) ou revela um número do meio ausente (mapa_acrescentar)",
                                                               "mapa_de_numeros": e.get("mapa_numeros")})
            return
        falta = [n for n, i in e["numeros"].items() if not i.get("aceito") and not self._do_perfil(i) and i.get("pedidos", 0) == 0]
        if falta and not self._orcamento_esgotado():
            for n in falta:
                e["numeros"][n]["pedidos"] = 1
            self.pedir("ia", "buscar_numero", {"numeros": {n: {"unidade": e["numeros"][n].get("unidade"), "grandeza": e["numeros"][n].get("grandeza"),
                                                               "forma": e["numeros"][n].get("forma"), "descricao": e["numeros"][n].get("descricao")} for n in falta},
                                                "lugar": self.problema.get("lugar"), "exigencias": "valor, unidade, incerteza, tipo_de_fonte, método, origem (URL), data, alcance e o descritor da grandeza"})
            return
        hip = [n for n, i in e["numeros"].items() if not i.get("aceito") and i.get("hipotese_sugerida") and not i.get("hipotese_decidida")]
        if hip:
            self.pedir(self._quem_decide(), "autorizar_hipotese", {**self._papel_de_criador(), "numeros": {n: {"hipotese": e["numeros"][n]["hipotese_sugerida"], "motivo_da_falta": e["numeros"][n].get("nao_encontrado"),
                                                                         "recusados": e["numeros"][n]["recusados"][-3:]} for n in hip}})
            return
        if not e.get("modelo_testado"):
            falhas = self._testar_modelo()
            if falhas:
                if self._orcamento_esgotado():
                    e["desfecho"] = {"tipo": "falta_modelo", "motivo": "o orçamento acabou com o modelo ainda refutado", "falhas": falhas}
                    return
                self.pedir("ia", "revisar", {"falhas": falhas, "modelo_id": e["modelo"]["id"], "pedido": "revise o modelo (ou proponha mudar D, que volta ao criador)",
                                             "mapa_de_numeros": e.get("mapa_numeros"), "sobre_o_mapa": "se a falha revela um número do meio que o mapa não tem, acrescente-o em mapa_acrescentar"})
                return
            e["modelo_testado"] = True
        # os trabalhos longos que o modelo declarou: rodam fora da caixa, só com a autorização do criador para aquele trabalho exato
        for tb in e["modelo"].get("trabalhos", []):
            desc, h = trabalho.descrever(tb)
            feitos = e.setdefault("trabalhos", {})
            if h in feitos or h in e.get("trabalhos_recusados", []):
                continue
            if h not in e.get("trabalhos_autorizados", []):
                self.pedir("criador", "autorizar_trabalho", {"trabalho": desc, "nome": tb.get("nome"), "hash": h,
                                                             "aviso": "roda fora da caixa, com as permissões do usuário; autorize só se o comando e os arquivos forem o que você espera",
                                                             "arquivos": {n: v[:4000] for n, v in (tb.get("arquivos") or {}).items()}})
                return
            feitos[h] = dict(trabalho.rodar(tb, self.pasta, e["trabalhos_autorizados"]), nome=tb.get("nome"))
            self.diario("trabalho_rodado", nome=tb.get("nome"), hash=h, ok=feitos[h]["ok"], segundos=feitos[h]["segundos"])
        # criar (ou recriar, se algo mudou desde a última criação)
        if self.modo == "medida" and e.get("alvo_medido_para") != e["modelo"]["hash"] and e.get("medida_pedida_para") != e["modelo"]["hash"]:
            # o perfil do alvo é número do meio: o motor pede à IA, e oferece a ferramenta de medida; ele não mede sozinho
            e["medida_pedida_para"] = e["modelo"]["hash"]
            self.pedir("ia", "medir_alvo", {"alvo": self.alvo().descrever(), "ferramenta": f"python -B -m compilador medir {self.pasta}",
                                            "pedido": "meça no alvo o perfil da máquina (versão do Python, núcleos, memória, microbenchmarks) e responda "
                                                      "com os números, o método e a origem; a ferramenta do motor imprime uma resposta pronta, e você pode medir de outro jeito",
                                            "formato": "ver esquemas.md, seção medir_alvo"})
            return
        # volta 1 (emenda 1): antes da busca, conferir que o meio entrega a informação que decide cada cláusula rígida
        cdist = sha({"D": e["D"], "meio": {k: e["modelo"].get(k) for k in ("carga", "entradas")}})
        if self.problema.get("conferir_distinguibilidade", True) and (e.get("distinguibilidade") or {}).get("para") != cdist:
            if e.get("distinguibilidade_pedida") != cdist:
                e["distinguibilidade_pedida"] = cdist
                pid = self.pedir("avaliador" if self.problema.get("avaliador") else "ia", "conferir_distinguibilidade",
                                 {"D": self._D_para_ia(), "meio": {k: e["modelo"].get(k) for k in ("carga", "entradas")},
                                  "pedido": "para cada cláusula rígida: a informação que o meio entrega a quem responde basta para decidi-la? Se não basta "
                                            "para nenhuma forma, dê a prova (ela não pode depender de L) e o número medido",
                                  "formato": "ver esquemas.md, seção conferir_distinguibilidade"})
                e["pedidos"][pid]["chave"] = cdist
                return
        nao = {k: v for k, v in ((e.get("distinguibilidade") or {}).get("clausulas") or {}).items() if v.get("distinguivel") is False}
        if nao and (e.get("distinguibilidade") or {}).get("para") == cdist:
            e["impossivel_no_meio"] = nao
            e["desfecho"] = self._desfecho()
            return
        chave = sha({"D": e["D"], "Pi": {k: v for k, v in self.Pi().dados["numeros"].items() if k not in ("ram_livre_mb",)}, "alt": (e["alternativo"] or {}).get("hash")})
        if not e["criacoes"] or e["criacoes"][-1]["chave"] != chave:
            self._criar(chave)
        ult = e["criacoes"][-1]
        # volta 5 (emenda 1): formas fora do domínio em que M foi validado não contam em A; a pergunta é validar M para elas
        if (ult.get("fora_do_dominio") or {}).get("n") and e.get("dominio_pedido") != e["modelo"]["hash"] and not self._orcamento_esgotado():
            e["dominio_pedido"] = e["modelo"]["hash"]
            self.pedir("ia", "revisar", {"fora_do_dominio": ult["fora_do_dominio"], "dominio": e["modelo"].get("dominio"),
                                         "pedido": "valide M para estas formas e estenda o domínio com a validação, ou tire-as de L"})
            return
        # a sensibilidade: um número fraco que decide volta a ser pedido, uma vez
        fracos = [s for s in ult.get("sensibilidade", []) if s.get("decide") and s["tipo"] in ("hipotese", "ausente", "aproximacao") and s["numero"] not in e["sensibilidade_pedida"] and s["numero"] in e["numeros"]]
        if fracos and not self._orcamento_esgotado():
            e["sensibilidade_pedida"] += [s["numero"] for s in fracos]
            self.pedir("ia", "buscar_numero", {"numeros": {s["numero"]: {"unidade": e["numeros"][s["numero"]].get("unidade"), "grandeza": e["numeros"][s["numero"]].get("grandeza"),
                                                                         "forma": e["numeros"][s["numero"]].get("forma"), "por_que": s["efeito"],
                                                                         "atual": e["numeros"][s["numero"]].get("aceito"), "recusados": e["numeros"][s["numero"]]["recusados"][-3:]} for s in fracos},
                                                "lugar": self.problema.get("lugar"), "prioridade": "estes números decidem o veredito ou a escolha; uma fonte melhor, com a grandeza certa"})
            return
        # nenhum candidato cumpre D, e nenhum número de Π, nos extremos, muda isso: D não cabe no meio com as formas propostas. O laço pede
        # outra forma (ou outro D) enquanto houver orçamento e progresso: até reformulacoes_max vezes, e para quando duas criações seguidas
        # não baixam a menor violação (corrigido em 28/09, depois de a corrida de aprendizagem contínua mostrar que o laço parava na primeira)
        n_ref = e.get("reformulacoes", 1 if e.get("reformulacao_pedida") else 0)
        vs = [c.get("melhor_violacao") for c in e["criacoes"][-3:]]
        progrediu = not (len(vs) == 3 and all(x is not None for x in vs) and min(vs[1:]) >= vs[0] - 1e-9)
        if not ult.get("escolhido") and n_ref < int(self.problema.get("reformulacoes_max", 5)) and progrediu and not self._orcamento_esgotado():
            e["reformulacoes"] = n_ref + 1
            e["reformulacao_pedida"] = True
            melhor = next((s_ for s_ in ult.get("sensibilidade", []) if s_["numero"] == "_melhor_candidato"), None)
            self.pedir("ia", "revisar", {"situacao": "nenhum candidato cumpre D, e nenhum número de Π, nos extremos da incerteza, muda isso",
                                         "melhor_candidato": melhor, "nulos": ult["nulos"], "sensibilidade": ult.get("sensibilidade"),
                                         "por_arquetipo": ult.get("por_arquetipo"), "reformulacao": n_ref + 1,
                                         "diferencas_de_fotos": ult.get("diferencas_de_fotos"),
                                         "historico_da_menor_violacao": [c.get("melhor_violacao") for c in e["criacoes"]],
                                         "ordem_das_causas": ["L estreita: abrir a forma (outro arquétipo, mais primitivas ou mais composição)",
                                                              "cláusula de forma no D: o criador diz se é intenção", "Π: número ausente, largo ou errado",
                                                              "M: modelo refutado ou fora do domínio", "D contra o meio, só depois das quatro"],
                                         "clausulas_de_forma": [c["id"] for c in self.D().rigidas() if c.get("natureza") == "forma"],
                                         "pedido": "proponha uma forma nova (outro arquétipo, ou composição de primitivas) ou uma mudança de D; a mudança de D volta ao criador",
                                         "mapa_de_numeros": e.get("mapa_numeros"), "sobre_o_mapa": "se a falha revela um número do meio que o mapa não tem, acrescente-o em mapa_acrescentar"})
            return
        # a ordem das causas (fórmula 4.0): quando L já foi reformulada sem ninguém cumprir D, as cláusulas de forma voltam ao criador antes
        # de qualquer conclusão de impossibilidade
        formas = [c for c in self.D().rigidas() if c.get("natureza") == "forma"]
        if not ult.get("escolhido") and formas and e.get("formas_perguntadas") != sha([(c["id"], c.get("enunciado")) for c in formas]):
            e["formas_perguntadas"] = sha([(c["id"], c.get("enunciado")) for c in formas])
            e["D_proposto"] = {"clausulas": e["D"]["clausulas"], "escopo": e["D"].get("escopo") or {}, "ambiguidades": [],
                               "condicoes_de_uso": e["D"].get("condicoes_de_uso", [])}
            e["D_confirmado"] = False
            self.pedir(self._quem_decide(), "confirmar_D", dict({"proposta": e["D_proposto"], "clausulas_de_forma": [c["id"] for c in formas],
                                                                 "falta": "nenhuma forma de L cumpre D; estas cláusulas fixam a forma do corpus: são intenção sua? "
                                                                          "A suposição sai do D"}, **self._papel_de_criador()))
            return
        if self.problema.get("avaliador") and not e["alternativo"] and not e.get("alternativo_pedido"):
            e["alternativo_pedido"] = True
            m = e["modelo"]
            self.pedir("avaliador", "modelo_alternativo", {"D": self._D_para_ia(), "entradas": m.get("entradas"),
                                                           "saidas": sorted({c["teste"]["medida"] for c in self.D().rigidas()}),
                                                           "representacao": m.get("representacao"),
                                                           "pedido": "o seu modelo para estas saídas, sem ver o modelo do outro"})
            return
        if e["alternativo"] and ult.get("discordancias") and not e.get("discordancia_enviada") == ult["chave"] and not self._orcamento_esgotado():
            e["discordancia_enviada"] = ult["chave"]
            self.pedir("ia", "revisar", {"contraexemplos": ult["discordancias"][:8], "pedido": "o modelo alternativo discorda nestes candidatos; revise o modelo ou explique a premissa",
                                         "mapa_de_numeros": e.get("mapa_numeros"), "sobre_o_mapa": "se a falha revela um número do meio que o mapa não tem, acrescente-o em mapa_acrescentar"})
            return
        # volta 2 (emenda 1): o corpus muda o meio; o escolhido tem de cumprir D no meio que ele mesmo produz (o ponto fixo)
        if ult.get("escolhido") and "ponto_fixo" not in ult:
            ult["ponto_fixo"] = self._ponto_fixo(ult)
            if not ult["ponto_fixo"]["cumpre"]:
                ult["escolhido_fora_do_ponto_fixo"] = ult.pop("escolhido")
                ult["sem_escolhido_porque"] = "o escolhido não cumpre D no meio que ele mesmo produz (Π ⊕ ε)"
        if not e.get("exportado") and ult.get("escolhido"):
            self._escolher_e_exportar(ult)
        if self.problema.get("mudancas_planejadas", True) and not e["mudancas"] and ult.get("escolhido"):
            self._mudancas_planejadas()
        e["desfecho"] = self._desfecho()
        self._auditoria()

    def _auditoria(self):
        """A auditoria do problema: quem decidiu cada cláusula, de onde veio cada número (e o que foi recusado), cada versão do
        modelo e por que mudou, os testes que refutaram, as criações, os nulos, as discordâncias, a sensibilidade, o artefato e o reuso."""
        from bancada.nucleo.artefato import manifesto
        e = self.estado
        d = e.get("D") or {}
        aud = {"problema": self.problema.get("id"), "desfecho": e["desfecho"], "contadores": e["contadores"],
               "D": [{"id": c["id"], "tipo": c["tipo"], "enunciado": c.get("enunciado"), "teste": c.get("teste"), "origem": c.get("origem"),
                      "confirmada": c.get("confirmada"), "corrigida_de": c.get("corrigida_de")} for c in d.get("clausulas", [])],
               "respostas_das_ambiguidades": (d.get("escopo") or {}).get("respostas_das_ambiguidades"),
               "numeros": {n: {"aceito": {k: (i.get("aceito") or {}).get(k) for k in ("valor", "unidade", "incerteza", "tipo", "fonte", "metodo", "data")} if i.get("aceito") and not isinstance((i.get("aceito") or {}).get("valor"), dict) else (i.get("aceito") or {}).get("valor"),
                               "recusados": [{"origem": (x["candidato"] or {}).get("origem"), "motivos": x["motivos"]} for x in i.get("recusados", [])],
                               "fornecido_pelo_motor": i.get("fornecido_pelo_motor", False)} for n, i in e["numeros"].items()},
               "mapa_de_numeros": {n: dict(x, estado=("usado" if n in {y["nome"] for y in (e.get("modelo") or {}).get("entradas", [])} else
                                                         ("excluido: " + str(((e.get("modelo") or {}).get("numeros_excluidos") or {}).get(n))[:200]
                                                          if n in ((e.get("modelo") or {}).get("numeros_excluidos") or {}) else "ausente")),
                                            aceito=bool((e["numeros"].get(n) or {}).get("aceito")))
                                    for n, x in (e.get("mapa_numeros") or {}).items()},
               "modelos": e["modelos"], "testes": e["testes"], "alternativo": bool(e["alternativo"]),
               "criacoes": [{k: c.get(k) for k in ("rotulo", "hora", "candidatos", "calculados", "reusados", "validos", "desfecho", "nulos", "forca", "segundos")} for c in e["criacoes"]],
               "discordancias": (e["criacoes"][-1].get("discordancias") if e["criacoes"] else None),
               "sensibilidade": (e["criacoes"][-1].get("sensibilidade") if e["criacoes"] else None),
               "escolhido": (e["criacoes"][-1].get("escolhido") if e["criacoes"] else None), "exportacao": e.get("exportacao"), "mudancas": e.get("mudancas"),
               "intervencoes": [l for l in open(os.path.join(self.pasta, "intervencoes.jsonl"), encoding="utf-8")] if os.path.exists(os.path.join(self.pasta, "intervencoes.jsonl")) else []}
        self._gravar("auditoria.json", aud)
        if e.get("exportacao", {}).get("ok"):
            manifesto(os.path.join(self.pasta, "artefatos"), self.D(), self.Pi(), {"modelo": e["modelo"]["hash"], "desfecho": e["desfecho"]})

    def _D_para_ia(self):
        d = self.estado["D"]
        return {"clausulas": [{k: c[k] for k in ("id", "tipo", "enunciado", "teste") if k in c} for c in d["clausulas"]], "escopo": d.get("escopo")}

    # ------------------------------------------------------------------ o que o motor faz sozinho
    def _testar_maquina(self):
        import tempfile
        from bancada.provedores.maquina import Alvo
        from .adaptador_maquina import EXECUTOR
        m = self.estado["modelo"]
        falhas = []
        local = Alvo("ensaio-local")
        formas = list(m["representacao"]["arquetipos"])
        if m["representacao"].get("composicao"):
            formas.append(dict(m["representacao"]["composicao"], nome="composicao"))
        for a in formas:
            x = gerar.compostos(a, 1)[0] if a["nome"] == "composicao" else gerar.grade_ou_amostra({"arquetipos": [a]}, 1)[0]
            t = {"carga": m["carga"], "candidato": a["codigo"], "metricas": m.get("metricas"), "oraculos": [m["oraculo"]],
                 "params": {k: v for k, v in x.items() if not k.startswith("_") and k != "id"}, "semente": m.get("semente", 1), "repeticoes": 1, "rodadas": 1,
                 "tempo_limite_s": m.get("tempo_limite_s", 300)}
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8", newline=chr(10)) as fh:
                json.dump(t, fh)
            r = local.executar(EXECUTOR, "medir", fh.name, timeout=int(t["tempo_limite_s"]) * 2)
            os.unlink(fh.name)
            if "erro" in r:
                falhas.append({"tipo": "execucao", "arquetipo": a["nome"], "detalhe": r["erro"][-600:]})
            elif not r["oraculos_ok"]:
                falhas.append({"tipo": "oraculo", "arquetipo": a["nome"], "detalhe": r["oraculos"]})
        ditas = {"tempo_mediana_s", "tempo_p95_s", "cpu_mediana_s", "pico_memoria_mb", "correto"} | {s_["nome"] for mm in m.get("modelos", []) for s_ in mm.get("saidas", [])}
        for c in self.D().rigidas():
            if c["teste"]["medida"] not in ditas:
                falhas.append({"tipo": "cobertura", "detalhe": f"D julga {c['teste']['medida']}, e nem o motor nem as métricas declaradas medem isso"})
        self.estado["testes"].append({"modelo": m["id"], "ensaio_local": falhas, "hora": agora()})
        self.diario("modelo_testado", modelo=m["id"], falhas=len(falhas))
        return falhas

    def _cobertura_do_mapa(self):
        m = self.estado["modelo"]
        usadas = {x["nome"] for x in m.get("entradas", [])}
        excl = m.get("numeros_excluidos") or {}
        falhas = []
        for nome, x in (self.estado.get("mapa_numeros") or {}).items():
            if nome in usadas:
                continue
            j = excl.get(nome)
            if not (isinstance(j, str) and j.strip()) and not (isinstance(j, dict) and (j.get("justificativa") or "").strip()):
                falhas.append({"tipo": "cobertura_de_pi", "numero": nome, "detalhe": f"o mapa diz que {nome} decide {', '.join(x.get('clausulas') or ['D'])} "
                               f"(mapa de: {', '.join(x.get('origens', []))}); o modelo não o usa nem justifica a exclusão"})
        return falhas

    def _testar_modelo(self):
        if self.modo == "medida":
            return self._testar_maquina() + self._cobertura_do_mapa()
        m = self.estado["modelo"]
        falhas = []
        principal = m["modelos"][0]
        saidas = {s["nome"] for s in principal.get("saidas", [])}
        for c in self.D().rigidas():
            if c["teste"]["medida"] not in saidas:
                falhas.append({"tipo": "cobertura", "detalhe": f"D julga {c['teste']['medida']}, e o modelo não declara essa saída"})
        falhas += self._cobertura_do_mapa()
        base, _ = self.p_base()
        # os números que ainda faltam entram pelo valor de ensaio que o modelo declarou (só para os testes); sem ele, ficam None
        ensaio = {x["nome"]: x.get("valor_de_ensaio") for x in m.get("entradas", [])}
        base = {k: (v if v is not None else ensaio.get(k)) for k, v in base.items()}
        cand = gerar.grade_ou_amostra(m["representacao"], 8)
        r = avaliar.propagar(principal["codigo"], cand, base, {})
        if "erro" in r:
            falhas.append({"tipo": "compilacao", "detalhe": r["erro"][-600:]})
            return falhas
        for x in r["avaliados"]:
            if x["erros"]:
                falhas.append({"tipo": "execucao", "candidato": x["id"], "detalhe": x["erros"][0]})
                break
        testes = list(m.get("testes", [])) + list(self.estado.get("testes_extras", []))
        res = avaliar.testar(principal["codigo"], testes, base)
        self.estado["testes"].append({"modelo": m["id"], "resultados": res, "hora": agora()})
        for t in res:
            if not t["ok"]:
                falhas.append({"tipo": "teste_refutou", "teste": t["teste"], "detalhe": t.get("detalhe") or t.get("erro")})
        self.diario("modelo_testado", modelo=m["id"], falhas=len(falhas))
        return falhas

    def _adaptador(self, usar_ledger=True, d=None, p=None):
        m = self.estado["modelo"]
        if self.modo == "medida":
            from .adaptador_maquina import AdaptadorMaquina
            cand = gerar.grade_ou_amostra(m["representacao"], int(self.problema.get("orcamento", {}).get("candidatos_por_criacao", 60)))
            oalt = (self.estado["alternativo"] or {}).get("oraculo")
            ad = AdaptadorMaquina(m, cand, self.alvo(), oalt, rodadas=int(self.problema.get("rodadas", 3)), usar_ledger=usar_ledger,
                                  paralelo=int(self.problema.get("paralelo_no_alvo", 1)), repeticoes=int(self.problema.get("repeticoes", 5)),
                                  pasta_fotos=os.path.join(self.pasta, "fotos"))
            ad.calculados = 0
            self._ultimo_calculo = {"amostrados": self._amostrados(m["representacao"], int(self.problema.get("orcamento", {}).get("candidatos_por_criacao", 60))),
                                    "poda_heuristica": False}
            return ad, cand
        base, inter = self.p_base()
        orc = int(self.problema.get("orcamento", {}).get("candidatos_por_criacao", 2000))
        cand = gerar.grade_ou_amostra(m["representacao"], orc)
        pre = {}
        self._ultimo_calculo = None
        d = d or self.D()
        # a adaptação ao problema: a cada criação (e toda mudança de D, de Π ou do modelo leva a uma nova), o cálculo mede a estrutura
        # do modelo e escolhe onde pode podar; o criador que pede certeza ("busca": "completa" no escopo de D) desliga a poda
        certeza = ((d.dados.get("escopo") or {}).get("busca") == "completa") if d is not None else False
        if self.problema.get("calcular_antes", True) and d is not None and not certeza:
            # calcular antes de buscar (compilador/calcular.py): a região que não pode cumprir D cai sem ser calculada; as saídas que o
            # ledger ainda dá por válidas são reusadas também aqui
            reus = {}
            if usar_ledger:
                validas, _ = self.ledger.transferir(d, p or self.Pi())
                for ev in validas:
                    mm = ev.get("medida") or {}
                    if mm.get("tipo") == "saida_compilada" and mm.get("modelo") == m["hash"]:
                        reus[mm["chave"]] = mm["valores"]
            codigo = m["modelos"][0]["codigo"]

            def pontos(cs):
                out = {c["_id"]: reus[c["_id"]] for c in cs if c["_id"] in reus}
                falta = [c for c in cs if c["_id"] not in reus]
                if falta:
                    r = avaliar.propagar(codigo, falta, base, inter)
                    if "erro" in r:
                        raise RuntimeError("o modelo não roda: " + r["erro"])
                    out.update({x["id"]: x for x in r["avaliados"]})
                return out
            calc = calcular.Calculo(m["representacao"], [c["teste"] for c in d.rigidas()], pontos, orc)
            rc = calc.rodar()
            cand = rc["a_calcular"] + rc["melhores_que_nao_passam"]
            ids = {c["_id"] for c in cand}
            pre = {k: v for k, v in calc.cache.items() if v is not None and k not in reus and k in ids}
            fora = [k for k, v in calc.cache.items() if v is not None and k not in reus and k not in ids]
            self._ultimo_calculo = {"hipotese": rc["hipotese"], "podados_sem_calcular": sum(1 for x in rc["podados"] if not x["calculado"]),
                                    "podados_por_clausula": _contar([{"classe": x["clausula"]} for x in rc["podados"]]),
                                    "calculados_so_no_calculo": len(fora), "reusados_no_calculo": sum(1 for k in calc.cache if k in reus),
                                    "amostrou_a_regiao": rc["amostrou_a_regiao"], "monotonia": rc["monotonia"],
                                    "auditoria": rc["auditoria"], "forma": rc["forma"],
                                    "refutada_em": [k for k, v in rc["auditoria"].items() if v.get("refutada")],
                                    "amostrados": rc["amostrou_a_regiao"], "poda_heuristica": any(not x["calculado"] for x in rc["podados"])}
        else:
            self._ultimo_calculo = {"amostrados": self._amostrados(m["representacao"], orc), "poda_heuristica": False}
            if certeza:
                self._ultimo_calculo["busca_completa"] = "o criador pediu certeza: sem poda, a grade ou a amostra inteira é calculada"
        entradas = [x["nome"] for x in m.get("entradas", [])]
        alt = None
        if self.estado["alternativo"]:
            alt = {"codigo": self.estado["alternativo"]["modelos"][0]["codigo"]}
        tol = (self.estado["alternativo"] or {}).get("tolerancias", {})
        return AdaptadorCompilado({"id": m["id"], "hash": m["hash"], "codigo": m["modelos"][0]["codigo"]}, cand, base, inter, entradas, alt, tol, usar_ledger,
                                  precalculados=pre), cand

    def _diferencas_de_fotos(self, ad, por_arq):
        """A seleção sobre as fotos: o melhor candidato desta criação comparado, pela função comparar_fotos que a IA declarou, com o melhor
        de cada outro arquétipo e com o melhor da criação anterior. Vai para a pergunta de revisão, para a variação seguinte ser dirigida
        pela diferença medida entre os comportamentos, e não só pela cláusula que reprovou."""
        m = self.estado.get("modelo") or {}
        fotos = getattr(ad, "fotos", {}) or {}
        if not m.get("comparar_fotos") or not fotos or not por_arq:
            return None
        from .executor_generico import _carregar
        comparar = _carregar(m["comparar_fotos"], "comparar_fotos")
        ordem = sorted(por_arq.values(), key=lambda x: x["violacao"])
        melhor = ordem[0]["melhor"]
        pares = [(melhor, x["melhor"]) for x in ordem[1:4]]
        ant = (self.estado["criacoes"][-1].get("melhor_id_com_foto") if self.estado["criacoes"] else None)
        if ant and ant.get("foto") and ant["id"] != melhor:
            pares.append((melhor, ant))
        out = []
        for a, b in pares:
            fa = fotos.get(a)
            fb = b["foto"] if isinstance(b, dict) else fotos.get(b)
            if not fa or not fb:
                continue
            try:
                res = comparar(ad.ler_foto(fa), ad.ler_foto(fb))
            except Exception as ex:  # noqa: BLE001
                res = {"erro": f"{type(ex).__name__}: {ex}"[:300]}
            out.append({"a": a, "b": b["id"] if isinstance(b, dict) else b, "resultado": res})
        self._melhor_com_foto = {"id": melhor, "foto": fotos.get(melhor)}
        return out

    @staticmethod
    def _amostrados(rep, orc):
        """Os arquétipos cuja grade passa da cota e, por isso, foram amostrados, e não calculados inteiros."""
        cota = max(1, orc // max(1, len(rep["arquetipos"])))
        out = []
        for a in rep["arquetipos"]:
            t = 1
            for v in a.get("variaveis", []):
                t *= len(gerar.niveis(v))
            if t > cota:
                out.append(a["nome"])
        return out

    def _pior_caso_interior(self, d, cands):
        """(2) O pior caso no interior de U: os cantos só dão o pior caso quando M é monótono nos números de Π. Os candidatos da fronteira
        são calculados também em pontos internos da caixa de Π; um que viola uma cláusula rígida em algum deles sai."""
        base, inter = self.p_base()
        nums = sorted(n for n, iv in inter.items() if isinstance(base.get(n), (int, float)) and iv and iv[1] > iv[0])
        if not nums or not cands:
            return None
        r = random.Random(13)
        codigo = self.estado["modelo"]["modelos"][0]["codigo"]
        pts = [c["formulacao"] for c in cands]
        n_pontos = int(self.problema.get("pontos_internos_de_U", 24))
        violam = {}
        for _ in range(n_pontos):
            p = dict(base)
            for n in nums:
                lo, hi = inter[n]
                p[n] = lo + (hi - lo) * r.random()
            res = avaliar.propagar(codigo, pts, p, {})
            for x in res.get("avaliados", []):
                if x["erros"] or not isinstance(x["centro"], dict) or x["id"] in violam:
                    continue
                for c in d.rigidas():
                    if avaliar.julgar(c["teste"], x["centro"], {}) == "falha":
                        violam[x["id"]] = {"clausula": c["id"], "cenario": {n: round(p[n], 6) for n in nums}}
                        break
        return {"violam": violam, "resumo": {"pontos_internos": n_pontos, "numeros_variados": nums, "candidatos_conferidos": len(pts),
                                             "violaram": len(violam), "exemplos": dict(list(violam.items())[:3])}}

    def _violacao_pior(self, d, med):
        """A violação no pior cenário de U: para cada cláusula rígida, o extremo desfavorável do intervalo entre fluxos (ou rodadas)."""
        pior = dict(med)
        for c in d.rigidas():
            t = c["teste"]
            iv = med.get(t["medida"] + "_intervalo")
            if isinstance(iv, (list, tuple)) and len(iv) == 2:
                pior[t["medida"]] = iv[1] if t["op"] in ("<=", "<") else iv[0]
        return self._violacao(d, pior)

    def _concorrencia(self, d, ad):
        """A concorrência acelerada dos códigos atômicos (decisão de 28/09): gerações de candidatos da representação, medidas em paralelo no
        alvo, julgadas por V no pior cenário (a violação das cláusulas rígidas) e pelos objetivos de D, com seleção e variação do NSGA-II.
        V é a única peça fixa; o cache garante que a mesma medida não roda duas vezes. Devolve a população final, que passa pelo julgamento
        normal (e pelo oráculo independente) com as medidas já feitas, e o número de códigos que concorreram."""
        rep = self.estado["modelo"]["representacao"]
        objs = d.objetivos()
        oalt, ad.oalt = ad.oalt, None           # o oráculo independente confere a população final, e não cada geração
        historico, arquivo = [], []
        novidade = bool(self.problema.get("novidade_por_foto"))
        hamming = self.problema.get("novidade_por_foto") == "hamming"

        def _novidade(v):
            # a distância média da foto às 5 mais próximas já vistas: comportamento novo sobrevive; com "hamming", a fração de bits
            # diferentes (a foto é de respostas e etiquetas), senão a distância euclidiana do perfil
            if not arquivo:
                return 0.0
            v = np.asarray(v)
            ds = sorted(float(np.mean(v != a)) if hamming else float(np.sqrt(np.sum((v - a) ** 2))) for a in arquivo)
            return float(np.mean(ds[:5]))

        def avaliar_lote(cs):
            med = ad.medir_lote(cs)
            out = []
            for c in cs:
                m = med.get(c["_id"])
                if m is None:
                    out.append(([1e9] * len(objs), 1e9))
                    continue
                vet = [(-1 if o["teste"].get("sentido") == "max" else 1) * float(m.get(o["teste"]["medida"], 0) or 0) for o in objs]
                # a volta 1 na seleção: uma diferença menor que a resolução declarada no D não decide; sem isso, o ruído da medida mexeria
                # na fronteira a cada geração e o empacamento nunca seria visto
                vet = [round(v / float(o["teste"]["resolucao"])) * float(o["teste"]["resolucao"]) if float(o["teste"].get("resolucao") or 0) > 0 else v
                       for v, o in zip(vet, objs)]
                if novidade and isinstance(m.get("perfil"), list):
                    vet.append(-_novidade(m["perfil"]))
                    arquivo.append(np.asarray(m["perfil"], np.int8 if hamming else float))
                vi = self._violacao_pior(d, m) + (0 if m.get("correto") else 1.0)
                historico.append({"id": c["_id"], "violacao_no_pior": round(vi, 4)})
                out.append((vet, vi))
            self.diario("geracao", avaliados=len(cs), melhor_violacao=min((v for _, v in out), default=None))
            return out
        # volta 7 (emenda 1): população e parada são números de f; sem valor declarado, σ os escolhe pelo custo medido de um lote
        sigma = None
        if self.problema.get("populacao") in (None, "sigma"):
            par = int(self.problema.get("paralelo_no_alvo") or self.problema.get("paralelo") or os.cpu_count() or 1)
            lote = gerar.grade_ou_amostra(rep, par, int(self.problema.get("semente_da_concorrencia", 1)))[:par]
            t_l = time.perf_counter()
            ad.medir_lote(lote)
            sigma = _sigma_da_concorrencia(time.perf_counter() - t_l, float(self.problema.get("teto_s_da_concorrencia") or 3600), par)
            self.problema["populacao"] = sigma["populacao"]
            self.problema.setdefault("parar_sem_melhora", sigma["parar_sem_melhora"])
        pop, n = gerar.nsga2(rep, avaliar_lote, objs, None, int(self.problema.get("avaliacoes_da_concorrencia", 100000)),
                             semente=int(self.problema.get("semente_da_concorrencia", 1)), populacao=int(self.problema.get("populacao", 24)),
                             parar_sem_melhora=self.problema.get("parar_sem_melhora"), teto_s=self.problema.get("teto_s_da_concorrencia"))
        ad.oalt = oalt
        final = sorted(pop, key=lambda c: c["_avaliacao"][1])[: int(self.problema.get("populacao", 24))]
        self._ultimo_calculo = dict(getattr(self, "_ultimo_calculo", None) or {}, concorrencia={"codigos_que_concorreram": n, "sigma": sigma,
                                    "parada": getattr(gerar.nsga2, "ultima_parada", None),
                                    "geracoes": max(1, (n - int(self.problema.get("populacao", 24))) // int(self.problema.get("populacao", 24)) + 1),
                                    "melhor_violacao_por_ordem": [h["violacao_no_pior"] for h in historico][:: max(1, len(historico) // 20)]})
        return [{k: v for k, v in c.items() if k != "_avaliacao"} for c in final]

    def _criar(self, chave, D_=None, Pi_=None, reaproveitar=True, rotulo="criacao", so=None):
        d = D_ or self.D()
        p = Pi_ or self.Pi()
        t0 = time.perf_counter()
        ad, cand = self._adaptador(usar_ledger=reaproveitar, d=d, p=p)
        if so is not None:
            cand = so
            ad.cand = cand
        elif self.modo == "medida" and self.problema.get("busca") == "concorrencia" and rotulo == "criacao":
            cand = self._concorrencia(d, ad)
            ad.cand = cand
        dom, fora = (self.estado.get("modelo") or {}).get("dominio"), []
        if dom:
            fora = [c["_id"] for c in cand if not _no_dominio(c, dom)]
            cand = [c for c in cand if _no_dominio(c, dom)]
            ad.cand = cand
        res = criar(d, p, ad, self.ledger if reaproveitar else Ledger(), orcamento={"verificacoes": 100000, "validos": 100000}, reaproveitar=reaproveitar)
        seg = round(time.perf_counter() - t0, 2)
        uc = getattr(self, "_ultimo_calculo", None) or {}
        viol, por_arq = [], {}
        for v in self.ledger.entradas[-(len(cand) * 3):]:
            if v.get("tipo") != "veredito":
                continue
            med = v.get("medidas") or {}
            vi = self._violacao(d, med)
            viol.append(vi)
            arq = str(v.get("formulacao_id", "")).split("|")[0]
            if arq not in por_arq or vi < por_arq[arq]["violacao"]:
                por_arq[arq] = {"melhor": v.get("formulacao_id"), "violacao": round(vi, 4), "reprovou_em": (v.get("nulo") or {}).get("clausula"),
                                "medidas": {c["teste"]["medida"]: med.get(c["teste"]["medida"]) for c in d.rigidas()}}
        self.estado["contadores"]["avaliacoes"] += (res.get("custo", {}).get("modelo_calculado", 0) + res.get("custo", {}).get("medicoes_no_alvo", 0)
                                                    + uc.get("calculados_so_no_calculo", 0))
        validos = res["validos"]
        disc = []
        for v in self.ledger.entradas[-(len(cand) * 3):]:
            if v.get("tipo") == "veredito" and v.get("discordancias"):
                disc += v["discordancias"]
        sens = self._sensibilidade(d, p, validos, ad) if rotulo == "criacao" and self.modo != "medida" else []
        # o custo contado pelo núcleo (a soma do que cada veredito declarou): calculados, medidos no alvo e reusados
        cu = res.get("custo", {})
        calculados = cu.get("modelo_calculado", 0) + cu.get("medicoes_no_alvo", 0) + uc.get("calculados_so_no_calculo", 0)
        resumo = {"chave": chave, "rotulo": rotulo, "hora": agora(), "segundos": seg, "desfecho": res["desfecho"], "candidatos": len(cand),
                  "calculados": calculados, "reusados": cu.get("medidas_reusadas", 0), "custo": cu, "validos": len(validos),
                  "nulos": _contar(res["nulos"]), "discordancias": disc[:40], "sensibilidade": sens,
                  "forca": _contar([{"classe": v["veredito"].get("forca", {}).get("conclusao")} for v in validos]),
                  "evidencias_que_cairam": _contar([{"classe": x["caiu_porque"][:80]} for x in res["evidencias_que_cairam"]]),
                  # os cadáveres dentro da conta: candidatos calculados e descartados; e o que o cálculo derrubou sem calcular
                  "cadaveres": max(0, calculados - len(validos)), "calculo_antes": {k: v for k, v in uc.items() if k != "monotonia"} or None,
                  "melhor_violacao": round(min(viol), 6) if viol else None, "por_arquetipo": por_arq,
                  "diferencas_de_fotos": self._diferencas_de_fotos(ad, por_arq),
                  "fora_do_dominio": {"n": len(fora), "exemplos": fora[:5]} if dom else None}
        amostrados = list(uc.get("amostrados", []))
        # a concorrência e a L que compõe só amostram L: sem isso, nada achado viraria "impossível nesta forma" (achado no teste de 29/09)
        if so is None and self.modo == "medida" and self.problema.get("busca") == "concorrencia" and rotulo == "criacao":
            amostrados.append("a concorrência amostra L")
        if ((self.estado.get("modelo") or {}).get("representacao") or {}).get("composicao"):
            amostrados.append("a L que compõe é amostrada: as listas de peças até max_pecas não cabem inteiras")
        resumo["cobertura"] = {"amostrados": amostrados, "poda_heuristica": bool(uc.get("poda_heuristica")),
                               "busca_completa": bool(uc.get("busca_completa"))}
        if validos:
            prefs = d.clausulas("preferencia")
            # (4) a dominância sob incerteza é declarada no D; o padrão é o pior caso em U (o extremo desfavorável da faixa de cada objetivo)
            dom = (d.dados.get("escopo") or {}).get("dominancia") or "pior_caso"
            sentidos = {c["teste"]["medida"]: c["teste"].get("sentido", "min") for c in d.objetivos()}
            if prefs:
                sentidos.update({m_: s_ for m_, s_ in prefs[0]["teste"].get("ordem", [])})

            def robusto(v):
                if dom != "pior_caso":
                    return v
                med = dict(v["veredito"]["medidas"])
                for m_, s_ in sentidos.items():
                    iv = med.get(m_ + "_intervalo")
                    if isinstance(iv, (list, tuple)) and len(iv) == 2:
                        med[m_] = iv[1] if s_ == "min" else iv[0]
                return dict(v, veredito=dict(v["veredito"], medidas=med))
            rv = [robusto(v) for v in validos]
            fr = pareto(rv, d.objetivos())
            na_r = [rv[i] for i in fr["fronteira"]]
            ordem = preferir(na_r, prefs[0]["teste"])["ordem"] if prefs else list(range(len(na_r)))
            ordenados = [validos[fr["fronteira"][j]] for j in ordem]
            resumo["dominancia"] = "pior caso em U: cada objetivo pelo extremo desfavorável da faixa" if dom == "pior_caso" else "valor central"
            # (2) o pior caso no interior de U, para os da fronteira na ordem da preferência
            pc = self._pior_caso_interior(d, ordenados[:10]) if self.modo == "calculo" else None
            violam = (pc or {}).get("violam", {})
            if pc:
                resumo["pior_caso_interior"] = pc["resumo"]
            esc = next((v for v in ordenados if v["formulacao"]["_id"] not in violam), None)
            resumo["fronteira"] = [{"id": validos[i]["formulacao"]["_id"], "medidas": validos[i]["veredito"]["medidas"],
                                    "forca": validos[i]["veredito"].get("forca")} for i in fr["fronteira"]]
            if esc is None:
                resumo["sem_escolhido_porque"] = "todos os da fronteira conferidos violam uma cláusula rígida no interior de U (o pior caso não está nos cantos)"
            else:
                resumo["escolhido"] = {"id": esc["formulacao"]["_id"], "formulacao": esc["formulacao"], "medidas": esc["veredito"]["medidas"],
                                       "forca": esc["veredito"].get("forca")}
        if getattr(self, "_melhor_com_foto", None):
            resumo["melhor_id_com_foto"] = self._melhor_com_foto
        if rotulo == "criacao":
            self.estado["criacoes"].append(resumo)
        self.diario("criacao", rotulo=rotulo, validos=len(validos), desfecho=res["desfecho"], segundos=seg)
        return resumo

    def _ponto_fixo(self, ult, voltas=3):
        """S★ = C★(D, Π ⊕ ε(S★)): o efeito do escolhido sobre o meio, declarado pelo modelo nas medidas (efeito_no_meio: número -> variação),
        é somado a Π e o escolhido é medido de novo, até o efeito parar de mudar."""
        esc = ult["escolhido"]
        eps = (esc.get("medidas") or {}).get("efeito_no_meio")
        if not eps:
            return {"declarado": "efeito_no_meio" in (esc.get("medidas") or {}), "voltas": 0, "cumpre": True}
        base = self.Pi().dados
        for k in range(voltas):
            r = self._criar("ponto_fixo", Pi_=Pi(_meio_com_efeito(base, eps)), reaproveitar=False, rotulo="ponto_fixo", so=[esc["formulacao"]])
            if not r.get("escolhido"):
                return {"declarado": True, "voltas": k + 1, "cumpre": False, "efeito": eps}
            novo = (r["escolhido"].get("medidas") or {}).get("efeito_no_meio") or {}
            if all(abs(float(novo.get(n, 0)) - float(v)) <= 1e-9 * max(1.0, abs(float(v))) for n, v in eps.items()):
                return {"declarado": True, "voltas": k + 1, "cumpre": True, "efeito": eps}
            eps = novo
        return {"declarado": True, "voltas": voltas, "cumpre": True, "efeito": eps, "aviso": "o efeito ainda mudava na última volta"}

    def registrar_mundo(self, r):
        """Volta 6: o resultado de um artefato avaliado fora do modelo. Uma falha reabre o laço."""
        e = self.estado
        e.setdefault("mundo", []).append(dict(r, registrado_em=agora()))
        if r.get("resultado") == "falhou":
            e.setdefault("falhas_no_mundo", []).append({"id": len(e["mundo"]), "artefato": r.get("artefato"), "detalhe": r.get("detalhe"), "medida": r.get("medida")})
            e["desfecho"] = None
            e["exportado"] = False
        self.diario("mundo", resultado=r.get("resultado"), artefato=r.get("artefato"))
        self._gravar("estado.json", e)

    def _violacao(self, d, centro):
        """Quanto um candidato falta para cumprir D: a soma das faltas normalizadas pelos limites (zero quando cumpre)."""
        tot = 0.0
        for c in d.rigidas():
            t = c["teste"]
            v = (centro or {}).get(t["medida"])
            if not isinstance(v, (int, float)) or not isinstance(t.get("valor"), (int, float)):
                tot += 1.0
                continue
            falta = (v - t["valor"]) if t["op"] in ("<=", "<") else ((t["valor"] - v) if t["op"] in (">=", ">") else abs(v - t["valor"]))
            # a escala declarada no teste diz quanto vale uma unidade de falta; sem ela, o próprio limite (um limite perto de zero pesaria
            # demais na seleção entre os que ainda não cumprem D)
            tot += max(0.0, falta) / float(t.get("escala") or max(abs(t["valor"]), 1e-9))
        return tot

    def _sensibilidade(self, d, p, validos, ad):
        """Que números de Π decidem. Um de cada vez, nos extremos do intervalo (ou a ±20% do valor, se ele não tem intervalo):
        - com válidos: o número decide se, num extremo, algum dos 20 melhores deixa de cumprir D;
        - sem válidos: o número decide se, num extremo, algum dos 20 mais perto de cumprir passa a cumprir.
        A comparação é sempre com o veredito do próprio candidato no centro."""
        base, inter = ad.p_base, ad.intervalos
        calc = getattr(ad, "_calc", {})
        if validos:
            top = [v["formulacao"] for v in validos[:20]]
            procura = "deixa_de_cumprir"
        else:
            ordem = sorted(ad.cand, key=lambda c: self._violacao(d, (calc.get(c["_id"]) or {}).get("centro")))
            top = ordem[:20]
            procura = "passa_a_cumprir"
        # a saída que decide: a da cláusula rígida com menos folga no melhor dos testados; quando nenhum cumpre, só entre as cláusulas
        # que o melhor não cumpre (uma cláusula que passa no limite, como um teto de área, não é o que impede)
        crit = None
        if top:
            x0 = calc.get(top[0]["_id"]) or {}
            c0, f0 = x0.get("centro") or {}, x0.get("faixa") or {}
            folgas, bloqueiam = [], []
            for c in d.rigidas():
                t = c["teste"]
                v = c0.get(t["medida"])
                if isinstance(v, (int, float)) and isinstance(t.get("valor"), (int, float)):
                    f = (abs(v - t["valor"]) / max(abs(t["valor"]), 1e-9), t["medida"])
                    folgas.append(f)
                    if avaliar.julgar(t, c0, f0) != "passa":
                        bloqueiam.append(f)
            escolha = bloqueiam if (procura == "passa_a_cumprir" and bloqueiam) else folgas
            crit = min(escolha)[1] if escolha else None
        out = []
        m = self.estado["modelo"]["modelos"][0]["codigo"]
        cumpre = lambda centro: all(avaliar.julgar(c["teste"], centro or {}, {}) == "passa" for c in d.rigidas())
        for nome, info in self.estado["numeros"].items():
            a = info.get("aceito")
            if (a and isinstance(a.get("valor"), dict)) or self._do_perfil(info):
                continue
            tipo = a["tipo"] if a else "ausente"
            v0 = base.get(nome)
            if v0 is None:
                out.append({"numero": nome, "tipo": "ausente", "decide": True, "efeito": "o número está ausente: o modelo não calcula sem ele"})
                continue
            if not isinstance(v0, (int, float)):
                continue
            lo, hi = inter.get(nome) or [v0 * 0.8, v0 * 1.2]
            mudou = set()
            nos_extremos = {}
            for extremo in (lo, hi):
                r = avaliar.propagar(m, top, dict(base, **{nome: extremo}), {})
                for x in r.get("avaliados", []):
                    antes = cumpre((calc.get(x["id"]) or {}).get("centro"))
                    depois = cumpre(x["centro"])
                    if (procura == "deixa_de_cumprir" and antes and not depois) or (procura == "passa_a_cumprir" and depois and not antes):
                        mudou.add(x["id"])
                    if crit and isinstance((x["centro"] or {}).get(crit), (int, float)):
                        nos_extremos.setdefault(x["id"], []).append(x["centro"][crit])
            # o peso: quanto este número, sozinho, move a saída que decide, em fração da largura total do intervalo dela
            pesos = []
            for cid, vals in nos_extremos.items():
                fx = ((calc.get(cid) or {}).get("faixa") or {}).get(crit)
                if len(vals) == 2 and fx and fx[1] > fx[0]:
                    pesos.append(abs(vals[1] - vals[0]) / (fx[1] - fx[0]))
            peso = round(sum(pesos) / len(pesos), 3) if pesos else 0.0
            decide = bool(mudou) or peso >= 0.25
            out.append({"numero": nome, "tipo": tipo, "decide": decide, "faixa_testada": [lo, hi], "procura": procura, "saida_que_decide": crit,
                        "peso_na_largura": peso,
                        "efeito": (f"{len(mudou)} dos {len(top)} {'melhores deixam de cumprir' if procura == 'deixa_de_cumprir' else 'mais perto de cumprir passam a cumprir'} num extremo"
                                   if mudou else (f"sozinho, responde por {100 * peso:.0f}% da largura do intervalo de {crit}" if peso >= 0.25 else "não muda o veredito dos candidatos testados"))})
        if not validos and top:
            melhor = top[0]
            out.append({"numero": "_melhor_candidato", "tipo": "-", "decide": False, "id": melhor["_id"],
                        "centro": (calc.get(melhor["_id"]) or {}).get("centro"), "violacao": round(self._violacao(d, (calc.get(melhor["_id"]) or {}).get("centro")), 4)})
        return out

    def _escolher_e_exportar(self, ult):
        e = self.estado
        e["exportado"] = True
        if not ult.get("escolhido"):
            return
        m = e["modelo"]
        exp = m.get("exportacao")
        if not exp:
            return
        base, _ = self.p_base()
        x = dict(ult["escolhido"]["formulacao"])
        if self.modo == "medida":
            # a exportação de máquina recebe o código do arquétipo escolhido
            x["_codigo"] = next(a["codigo"] for a in m["representacao"]["arquetipos"] if a["nome"] == x["_arquetipo"])
        r = avaliar.caixa({"codigo": exp["codigo"], "funcao": "exportar", "p_base": base, "candidatos": [x], "variacoes": [{}], "modo": "exportar",
                           "saidas": {x["_id"]: ult["escolhido"]["medidas"]}})
        if r.get("erro_de_compilacao") or r.get("erro_de_execucao") or not r["resultados"] or not r["resultados"][0][0]["ok"]:
            e["exportacao"] = {"ok": False, "erro": r.get("erro_de_compilacao") or r.get("erro_de_execucao") or r["resultados"][0][0].get("erro")}
            return
        from . import exportar
        saida = r["resultados"][0][0]["saidas"]
        e["exportacao"] = exportar.gravar(os.path.join(self.pasta, "artefatos"), saida, x, ult, e)
        if self.modo == "medida" and saida.get("arquivos"):
            e["exportacao"]["conferencia_no_alvo"] = self._conferir_artefato_maquina(saida, x)

    def _conferir_artefato_maquina(self, saida, x):
        """O arquivo exportado roda no alvo pelo executor genérico, com a carga e os oráculos do problema, numa semente retida."""
        import tempfile
        from .adaptador_maquina import EXECUTOR
        m = self.estado["modelo"]
        nome, texto = next(iter(saida["arquivos"].items()))
        oraculos = [m["oraculo"]] + ([self.estado["alternativo"]["oraculo"]] if (self.estado["alternativo"] or {}).get("oraculo") else [])
        t = {"carga": m["carga"], "candidato": texto, "metricas": m.get("metricas"), "oraculos": oraculos,
             "params": {k: v for k, v in x.items() if not k.startswith("_") and k != "id"} if "**" in texto.split("def executar", 1)[-1].split(")", 1)[0] else {},
             "semente": m.get("semente", 1) + 1, "repeticoes": 3, "rodadas": 1, "tempo_limite_s": m.get("tempo_limite_s", 300)}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8", newline=chr(10)) as fh:
            json.dump(t, fh)
        alvo = self.alvo()
        destino = alvo.enviar(fh.name) if alvo.tipo != "local" else fh.name
        if alvo.tipo != "local":
            alvo._garantir(EXECUTOR)
        r = alvo.executar(EXECUTOR, "medir", destino, timeout=int(t["tempo_limite_s"]) * 3)
        os.unlink(fh.name)
        return {"arquivo": nome, "semente_retida": t["semente"], "ok": ("erro" not in r) and r.get("oraculos_ok", False), "medida": r}

    def _mudancas_planejadas(self):
        """As duas mudanças fixadas no protocolo: um limite rígido apertado em 10% (o que tem menos folga no escolhido) e o número de Π
        mais largo que decide, com o intervalo reduzido à metade em torno do centro. Para cada uma: a transferência a seco (o que cai e
        por quê), a recriação com reuso e sem reuso."""
        e = self.estado
        ult = e["criacoes"][-1]
        d0, p0 = self.D(), self.Pi()
        out = {}
        med = ult["escolhido"]["medidas"]
        folgas = []
        for c in d0.rigidas():
            t = c["teste"]
            v = med.get(t["medida"])
            if isinstance(v, (int, float)) and isinstance(t.get("valor"), (int, float)) and t["op"] in ("<=", ">=") and t["valor"]:
                folgas.append((abs(t["valor"] - v) / abs(t["valor"]), c))
        if folgas:
            _, c = min(folgas, key=lambda x: x[0])
            novo = dict(c["teste"], valor=c["teste"]["valor"] * (0.9 if c["teste"]["op"] == "<=" else 1.1))
            d1 = d0.nova_versao(mudar={c["id"]: {"teste": novo}}, motivo="mudança planejada: limite apertado em 10%")
            out["D"] = self._medir_mudanca(d1, p0, f"{c['id']}: {c['teste']['valor']} -> {novo['valor']}")
        # o número de Π que muda é um dos que a IA trouxe (os que o motor mede no alvo não são trocados por outra fonte)
        largos = [(n, i["aceito"]) for n, i in e["numeros"].items() if i.get("aceito") and i["aceito"].get("incerteza") and not self._do_perfil(i)
                  and isinstance(i["aceito"].get("valor"), (int, float))]
        if largos:
            n, a = max(largos, key=lambda x: (x[1]["incerteza"][1] - x[1]["incerteza"][0]) / max(abs(x[1]["valor"]), 1e-9))
            lo, hi = a["incerteza"]
            c0 = a["valor"]
            novo = dict(a, incerteza=[c0 - (c0 - lo) / 2, c0 + (hi - c0) / 2], metodo=(a.get("metodo") or "") + "; intervalo reduzido à metade (mudança planejada)")
            antigo_estado = copy.deepcopy(e["numeros"][n])
            e["numeros"][n]["aceito"] = novo
            p1 = self.Pi()
            out["Pi"] = self._medir_mudanca(d0, p1, f"{n}: intervalo {a['incerteza']} -> {novo['incerteza']}")
            e["numeros"][n] = antigo_estado
        e["mudancas"] = out

    def _medir_mudanca(self, d1, p1, descricao):
        validas, caidas = self.ledger.transferir(d1, p1)
        a_seco = {"validas": len(validas), "caem": len(caidas), "motivos": _contar([{"classe": x["caiu_porque"][:80]} for x in caidas])}
        # as corridas usam uma cópia do ledger, para não misturar com a criação principal
        led_original = self.ledger
        self.ledger = Ledger()
        self.ledger.entradas = copy.deepcopy(led_original.entradas)
        com = self._criar("mudanca", d1, p1, True, "com_reuso")
        self.ledger = led_original
        sem = self._criar("mudanca", d1, p1, False, "sem_reuso")
        return {"descricao": descricao, "a_seco": a_seco,
                "com_reuso": {k: com[k] for k in ("segundos", "calculados", "reusados", "validos", "desfecho")} | {"escolhido": (com.get("escolhido") or {}).get("id")},
                "sem_reuso": {k: sem[k] for k in ("segundos", "calculados", "reusados", "validos", "desfecho")} | {"escolhido": (sem.get("escolhido") or {}).get("id")}}

    def _premissas(self, ult):
        """(1, 3) A força da conclusão como lista do que foi demonstrado e sob quais premissas. V certifica "cumpre D sob M e U"; se M e U
        descrevem o meio, só um teste de fora diz (verificado não é validado)."""
        e = self.estado
        m = e.get("modelo") or {}
        uc = ult.get("calculo_antes") or {}
        cob = ult.get("cobertura") or {}
        tipos = {}
        for n, i in e["numeros"].items():
            if not self._do_perfil(i):
                tipos.setdefault((i.get("aceito") or {}).get("tipo", "ausente"), []).append(n)
        mapa = e.get("mapa_numeros") or {}
        usadas = {x["nome"] for x in m.get("entradas", [])}
        excl = m.get("numeros_excluidos") or {}
        disc = ult.get("discordancias") or []
        aud = uc.get("auditoria") or {}
        if cob.get("busca_completa"):
            poda = "nenhuma: o criador pediu busca completa"
        elif cob.get("poda_heuristica"):
            poda = ("heurística: monotonia amostrada; a auditoria calculou " + str(sum(v.get("auditados", 0) for v in aud.values()))
                    + " pontos podados e achou " + str(sum(v.get("passaram", 0) for v in aud.values())) + " que passavam; uma ilha menor que a detecção pode ter escapado")
        else:
            poda = "nenhuma"
        return {"verificado": f"as cláusulas rígidas de D, segundo o modelo {m.get('id')} ({(m.get('hash') or '')[:10]}), sobre U(Π)",
                "U": "a caixa dos intervalos de Π, com os números tratados como independentes (nenhuma dependência declarada)",
                "pior_caso": ult.get("pior_caso_interior") or ("nos cantos da caixa" if self.modo == "calculo" else "nas rodadas medidas no alvo"),
                "modelo_validado": ("um modelo alternativo independente concordou, dentro da tolerância declarada" if e.get("alternativo") and not disc
                                    else ("o modelo alternativo discorda" if disc else "não: nenhum modelo independente conferiu M")),
                "validado_no_mundo": (f"{len(e.get('mundo', []))} artefatos avaliados fora do modelo, {len(e.get('falhas_no_mundo', []))} falharam"
                                      if e.get("mundo") else "não: nenhum artefato foi avaliado fora do modelo"),
                "numeros_por_tipo": tipos,
                "mapa_de_numeros": {"no_mapa": len(mapa), "usados": sorted(set(mapa) & usadas), "excluidos_com_justificativa": sorted(set(mapa) & set(excl)),
                                    "ausentes": sorted(set(mapa) - usadas - set(excl)),
                                    "aviso": "o mapa é o conhecido até aqui; não encontrar lacuna não prova que todas as grandezas foram encontradas"},
                "L": "a grade declarada da representação (os níveis de cada variável); o contínuo entre os níveis não foi calculado",
                "cobertura_de_L": "inteira" if not cob.get("amostrados") else "amostrada em " + ", ".join(cob["amostrados"]),
                "poda": poda, "dominancia": ult.get("dominancia"),
                "decisoes_da_ia_no_lugar_do_criador": e.get("decisoes_da_ia", []),
                "forma_do_motor": {"f": uc.get("forma"), "f0": "a busca de sempre (grade ou amostra, sem poda)",
                                   "origem": "o seletor escolhido no banco com o D da calculadora (saida/motor_otimo/resultado_c8.json)",
                                   "estavel_neste_problema": not uc.get("refutada_em"),
                                   "recuos": uc.get("refutada_em") or []},
                "cadaveres_na_conta": ult.get("cadaveres"),
                "distinguibilidade": e.get("distinguibilidade"),
                "ponto_fixo": ult.get("ponto_fixo") or "não conferido: nenhum escolhido",
                "horizonte": {"H": ((e.get("D") or {}).get("escopo") or {}).get("horizonte"),
                              "alem_do_horizonte": ((e.get("D") or {}).get("escopo") or {}).get("alem_do_horizonte"),
                              "numeros_com_deriva": sorted(n for n, i in e["numeros"].items() if i.get("deriva"))},
                "L_mapeada": e.get("L_mapeada"),
                "dominio_de_M": m.get("dominio") or "não declarado: M é suposto valer em toda L",
                "fora_do_dominio": ult.get("fora_do_dominio"),
                "mundo": {"avaliados": len(e.get("mundo", [])), "falharam": len(e.get("falhas_no_mundo", []))},
                "sigma_da_concorrencia": ((ult.get("calculo_antes") or {}).get("concorrencia") or {}).get("sigma")}

    def _desfecho(self):
        """(1) Cinco estados (fórmula 4.0): solução, impossível nesta forma, impossível no meio, não encontrado e indeterminado; a solução separa o melhor demonstrado do melhor encontrado (nota do Codex, 28/09): a forma estável do
        motor quer dizer que ele parou de mudar como procura, e não que achou o melhor ser. "Melhor demonstrado" exige L inteira
        calculada, sem poda heurística; senão, é o melhor encontrado e verificado, com o limite escrito."""
        e = self.estado
        ult = e["criacoes"][-1] if e["criacoes"] else None
        if e.get("impossivel_no_meio"):
            return {"tipo": "impossivel_no_meio", "motivo": "o meio não entrega a informação que decide estas cláusulas, para nenhuma forma",
                    "clausulas": e["impossivel_no_meio"], "pergunta_ao_criador": "mudar o meio (o que a pergunta carrega) ou mudar o D",
                    "premissas": self._premissas(ult) if ult else None}
        if not ult:
            return {"tipo": "indeterminado", "motivo": "nenhuma criação rodou"}
        prem = self._premissas(ult)
        cob = ult.get("cobertura") or {}
        inteira = not cob.get("amostrados") and not cob.get("poda_heuristica")
        faltas = [n for n, i in e["numeros"].items() if not i.get("aceito") and not self._do_perfil(i)]
        pesam = [{"numero": x["numero"], "tipo": x["tipo"], "efeito": x["efeito"]} for x in ult.get("sensibilidade", []) if x.get("decide") and x["numero"] != "_melhor_candidato"]
        if ult.get("escolhido"):
            return {"tipo": "solucao", "escolhido": ult["escolhido"]["id"],
                    "otimalidade": ("melhor demonstrado dentro de L, M e U: L inteira calculada, sem poda heurística" if inteira else
                                    "melhor encontrado e verificado; não demonstrado como o melhor, porque " +
                                    ("parte de L foi amostrada" if cob.get("amostrados") else "a poda é heurística")),
                    "depende_de_hipoteses": (ult["escolhido"].get("forca") or {}).get("numeros_hipotese"), "premissas": prem}
        incertos = (ult.get("nulos") or {}).get("modelo_incerto", 0)
        if faltas or incertos or ult.get("sem_escolhido_porque"):
            return {"tipo": "indeterminado", "motivo": ult.get("sem_escolhido_porque") or
                    (f"faltam números ({', '.join(faltas)})" if faltas else f"{incertos} candidatos ficam incertos: a conclusão depende de números ainda fracos"),
                    "numeros_ausentes": faltas, "numeros_que_impedem": pesam, "nulos": ult.get("nulos"), "premissas": prem}
        if inteira:
            return {"tipo": "impossivel_nesta_forma", "motivo": "nenhum candidato de L cumpre D, com L inteira calculada sob M e U",
                    "proxima_pergunta": "abrir L (mais primitivas ou mais composição) antes de culpar o D",
                    "numeros_que_pesam": pesam, "nulos": ult.get("nulos"), "premissas": prem}
        return {"tipo": "nao_encontrado_no_orcamento", "motivo": "nenhum candidato calculado cumpre D; isso não prova impossibilidade, porque " +
                ("parte de L foi amostrada" if cob.get("amostrados") else "a poda é heurística"), "numeros_que_pesam": pesam, "nulos": ult.get("nulos"),
                "premissas": prem}

    def situacao(self):
        e = self.estado
        return {"pendentes": self.pendentes(), "desfecho": e["desfecho"], "contadores": e["contadores"], "modelo": (e["modelo"] or {}).get("id"),
                "criacoes": len(e["criacoes"]), "numeros": {n: (i.get("aceito") or {}).get("tipo", "ausente") for n, i in e["numeros"].items()}}


def _no_horizonte(num, deriva, H):
    """A incerteza do número cobre a trajetória do meio no horizonte: [a, b] vira [min(a, a + dH), max(b, b + dH)]."""
    v = num.get("valor")
    if not isinstance(v, (int, float)):
        return num
    a, b = num.get("incerteza") or [v, v]
    return dict(num, incerteza=[min(a, a + deriva * H), max(b, b + deriva * H)], no_horizonte={"deriva": deriva, "H": H})


def _meio_com_efeito(dados, eps):
    """Π ⊕ ε: soma o efeito do corpus a cada número do meio que ele muda."""
    out = dict(dados)
    out["numeros"] = {k: dict(v) for k, v in dados["numeros"].items()}
    for nome, dv in eps.items():
        n = out["numeros"].get(nome)
        if n and isinstance(n.get("valor"), (int, float)):
            n["valor"] = n["valor"] + float(dv)
            if n.get("incerteza"):
                n["incerteza"] = [n["incerteza"][0] + float(dv), n["incerteza"][1] + float(dv)]
    return out


def _no_dominio(c, dom):
    """Dom(M_v): os arquétipos e as faixas de variável em que o modelo foi validado."""
    if dom.get("arquetipos") and c.get("_arquetipo") not in dom["arquetipos"]:
        return False
    for nome, faixa in (dom.get("variaveis") or {}).items():
        if nome not in c:
            continue
        v = c[nome]
        if len(faixa) == 2 and all(isinstance(x, (int, float)) for x in faixa) and isinstance(v, (int, float)):
            if not faixa[0] <= v <= faixa[1]:
                return False
        elif v not in faixa:
            return False
    return True


def _sigma_da_concorrencia(seg_por_lote, teto_s, paralelo, geracoes_minimas=20):
    """σ da concorrência (regra fixa e testável, declarada): a população é o maior múltiplo de paralelo que deixa caber geracoes_minimas
    gerações no teto de tempo, entre 2 e 16 lotes; a parada é por 3 gerações com a fronteira igual."""
    lotes = int(max(2, min(16, teto_s / max(seg_por_lote, 1e-9) / geracoes_minimas)))
    return {"populacao": lotes * paralelo, "parar_sem_melhora": 3, "seg_por_lote_medido": round(seg_por_lote, 3), "teto_s": teto_s,
            "geracoes_minimas": geracoes_minimas, "regra": "o maior múltiplo de paralelo que deixa caber geracoes_minimas gerações no teto, entre 2 e 16 lotes"}


def _contar(nulos):
    out = {}
    for n in nulos:
        k = n.get("classe") if isinstance(n, dict) else str(n)
        out[k] = out.get(k, 0) + 1
    return out


def carregar_serie(caminho):
    if caminho.endswith(".json"):
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    import csv
    with open(caminho, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        for k, v in l.items():
            try:
                l[k] = float(v)
            except (TypeError, ValueError):
                pass
    return linhas
