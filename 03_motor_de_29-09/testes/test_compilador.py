"""Os testes do compilador: unidades, a conferência de grandeza, a caixa, o gerador e o julgamento com intervalo."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from compilador import avaliar, gerar, numeros  # noqa: E402
from compilador.unidades import ErroDeUnidade, converter  # noqa: E402


def test_unidades():
    assert abs(converter(25.2, "km/h", "m/s") - 7.0) < 1e-9
    assert abs(converter(1, "kWh/m^2/d", "W/m^2") - 41.6667) < 1e-3
    try:
        converter(1, "m/s", "kg")
        assert False
    except ErroDeUnidade:
        pass


def test_dado_oficial_da_grandeza_errada_e_recusado():
    ent = {"unidade": "m/s", "grandeza": {"quantidade": "velocidade do vento", "estatistica": "rajada 3 s", "local": {"lat": -23.5, "lon": -46.6, "raio_km": 30}}}
    media = {"valor": 14.1, "unidade": "m/s", "tipo_de_fonte": "reanalise", "origem": "NASA POWER",
             "grandeza": {"quantidade": "velocidade do vento", "estatistica": "media horaria", "local": {"lat": -23.5, "lon": -46.6}}}
    longe = dict(media, grandeza=dict(media["grandeza"], estatistica="rajada 3 s", local={"lat": -22.9, "lon": -43.2}))
    boa = dict(media, valor=144, unidade="km/h", tipo_de_fonte="estacao", grandeza=dict(media["grandeza"], estatistica="rajada 3 s"))
    assert numeros.aceitar(ent, media, ".")[0] is None
    assert numeros.aceitar(ent, longe, ".")[0] is None
    num, mot = numeros.aceitar(ent, boa, ".")
    assert num and num["tipo"] == "medido" and abs(num["valor"] - 40.0) < 1e-9 and not mot
    sem_fonte = dict(boa, origem=None)
    assert numeros.aceitar(ent, sem_fonte, ".")[0] is None


def test_caixa_bloqueia_importacao_e_isola_erro():
    r = avaliar.caixa({"codigo": "import os\ndef calcular(x, p):\n    return {}", "funcao": "calcular", "p_base": {}, "candidatos": [{"_id": "a"}], "modo": "modelo"})
    assert r["erro_de_compilacao"] and "fora da lista" in r["erro_de_compilacao"]
    r = avaliar.propagar("def calcular(x, p):\n    return {'y': 1 / x['v']}", [{"_id": "a", "v": 0}, {"_id": "b", "v": 2}], {}, {})
    assert r["avaliados"][0]["erros"] and r["avaliados"][1]["centro"]["y"] == 0.5


def test_propagar_e_julgar_com_intervalo():
    r = avaliar.propagar("def calcular(x, p):\n    return {'y': x['a'] * p['k']}", [{"_id": "a", "a": 2.0}], {"k": 1.0}, {"k": [0.9, 1.2]})
    x = r["avaliados"][0]
    assert x["faixa"]["y"] == [1.8, 2.4]
    assert avaliar.julgar({"medida": "y", "op": "<=", "valor": 3.0}, x["centro"], x["faixa"]) == "passa"
    assert avaliar.julgar({"medida": "y", "op": "<=", "valor": 2.0}, x["centro"], x["faixa"]) == "incerto"
    assert avaliar.julgar({"medida": "y", "op": "<=", "valor": 1.0}, x["centro"], x["faixa"]) == "falha"


def test_gerador():
    rep = {"arquetipos": [{"nome": "a", "variaveis": [{"nome": "x", "tipo": "real", "min": 0, "max": 1, "passo": 0.5}, {"nome": "c", "tipo": "categoria", "valores": ["p", "q"]}]},
                          {"nome": "b", "variaveis": [{"nome": "n", "tipo": "inteiro", "min": 1, "max": 3}]}]}
    cs = gerar.grade_ou_amostra(rep, 100)
    assert len(cs) == 6 + 3 and len({c["_id"] for c in cs}) == 9
    cs = gerar.grade_ou_amostra({"arquetipos": [{"nome": "a", "variaveis": [{"nome": "x", "tipo": "real", "min": 0, "max": 1}] * 1 + [{"nome": "y", "tipo": "real", "min": 0, "max": 1}]}]}, 10)
    assert len(cs) == 10


def test_calcular_antes_de_buscar():
    """O cálculo acha os mesmos aprovados da grade inteira calculando menos, e o que ele poda fica marcado."""
    import itertools
    from compilador.calcular import Calculo, HIPOTESE
    rep = {"arquetipos": [{"nome": "a", "variaveis": [{"nome": "x", "tipo": "real", "min": 0, "max": 10, "passo": 1},
                                                     {"nome": "y", "tipo": "real", "min": 0, "max": 10, "passo": 1},
                                                     {"nome": "k", "tipo": "categoria", "valores": ["p", "q"]}]}]}
    f = lambda p: {"centro": {"s": p["x"] + 2 * p["y"] + (3 if p["k"] == "q" else 0)}, "erros": [],
                   "faixa": {"s": [p["x"] + 2 * p["y"] + (3 if p["k"] == "q" else 0) - 0.5, p["x"] + 2 * p["y"] + (3 if p["k"] == "q" else 0) + 0.5]}}
    n = []
    c = Calculo(rep, [{"medida": "s", "op": ">=", "valor": 25}], lambda pts: n.extend(pts) or {p["_id"]: f(p) for p in pts}, 10000).rodar()
    ref = sum(1 for x, y, k in itertools.product(range(11), range(11), "pq") if x + 2 * y + (3 if k == "q" else 0) - 0.5 >= 25)
    achou = sum(1 for p in c["a_calcular"] if f(p)["faixa"]["s"][0] >= 25)
    assert achou == ref == 29
    assert len({p["_id"] for p in n}) < 242 / 2
    assert c["podados"] and c["hipotese"] == HIPOTESE


def test_perfil_do_alvo_vem_da_ia():
    """O motor não mede o alvo sozinho: o perfil entra como resposta da IA, e um número sem método é recusado."""
    import shutil, tempfile
    from compilador.motor import Motor
    pasta = os.path.join(tempfile.mkdtemp(), "m")
    os.makedirs(pasta)
    shutil.copy(os.path.join(os.path.dirname(__file__), "..", "protocolos", "dev", "dev_maquina.json"), os.path.join(pasta, "problema.json"))
    m = Motor(pasta)
    m.estado["pedidos"]["009_medir_alvo"] = {"respondido": False}
    m.aplicar("009_medir_alvo", {"tipo": "medir_alvo"}, {"numeros": {
        "ns_por_hash_splitmix": {"valor": 600.0, "unidade": "ns", "incerteza": [590.0, 640.0], "tipo": "medido", "metodo": "7 repetições"},
        "cpus": {"valor": 6, "unidade": "núcleos lógicos"}}})
    x = m.estado["numeros"]["ns_por_hash_splitmix"]
    assert x["fornecido_por"] == "ia" and x["perfil_do_alvo"] and not x.get("fornecido_pelo_motor")
    assert "cpus" not in m.estado["numeros"]


def test_trabalho_so_com_autorizacao():
    """O trabalho longo roda fora da caixa só com o hash autorizado; qualquer mudança no comando é outro trabalho."""
    import tempfile
    from compilador import trabalho
    t = {"nome": "t", "comando": ["{python}", "-c", "open('r.txt', 'w').write('42')"], "saidas": ["r.txt"], "teto_s": 60}
    pasta = tempfile.mkdtemp()
    try:
        trabalho.rodar(t, pasta, [])
        assert False, "rodou sem autorização"
    except PermissionError:
        pass
    _, h = trabalho.descrever(t)
    r = trabalho.rodar(t, pasta, [h])
    assert r["ok"] and r["saidas"]["r.txt"]["bytes"] == 2
    _, h2 = trabalho.descrever(dict(t, comando=t["comando"][:2] + ["open('r.txt', 'w').write('43')"]))
    assert h2 != h


def test_executor_no_alvo_so_com_permitidos():
    from compilador import executor_generico as x
    for proibido in ("os", "sqlite3", "socket", "subprocess", "ctypes"):
        try:
            x._importar(proibido)
            assert False, proibido
        except ImportError:
            pass
    assert not hasattr(x._importar("io"), "open") and x._importar("zlib").__name__ == "zlib"


def test_auditoria_desfaz_a_poda_quando_a_monotonia_cai():
    """Um modelo com ondulação engana a monotonia amostrada; a auditoria calcula podados, acha um que passa e desfaz a poda."""
    import math
    from compilador.calcular import Calculo
    rep = {"arquetipos": [{"nome": "a", "variaveis": [{"nome": "x", "tipo": "real", "min": 0, "max": 40, "passo": 1}]}]}
    f = lambda p: {"centro": {"v": p["x"] + 6 * math.sin(p["x"])}, "faixa": {"v": [p["x"] + 6 * math.sin(p["x"])] * 2}, "erros": []}
    aval = lambda pts: {p["_id"]: f(p) for p in pts}
    ref = {i for i in range(41) if i + 6 * math.sin(i) >= 30}
    sem = Calculo(rep, [{"medida": "v", "op": ">=", "valor": 30}], aval, 1000, forma={"auditoria": 0, "pontos_por_linha": 2}).rodar()
    com = Calculo(rep, [{"medida": "v", "op": ">=", "valor": 30}], aval, 1000, forma={"auditoria": 40, "pontos_por_linha": 2}).rodar()
    achou = lambda c: {int(p["x"]) for p in c["a_calcular"] if f(p)["centro"]["v"] >= 30}
    assert achou(com) == ref  # a auditoria ligada explicitamente
    assert achou(sem) != ref or not sem["podados"]
    assert any(v.get("refutada") for v in com["auditoria"].values()) or not com["podados"]


def test_mapa_de_numeros_vem_do_D_e_cobre_o_modelo():
    """O mapa dos números sai do D; a união da IA e do avaliador; um número do mapa que o modelo não usa nem justifica reprova o modelo."""
    import shutil, tempfile
    from compilador.motor import Motor
    pasta = os.path.join(tempfile.mkdtemp(), "m")
    os.makedirs(pasta)
    shutil.copy(os.path.join(os.path.dirname(__file__), "..", "protocolos", "dev", "dev_lugar.json"), os.path.join(pasta, "problema.json"))
    m = Motor(pasta)
    for pid, quem, nums in (("004_mapear_numeros", "ia", {"chuva": {"clausulas": ["r1"]}, "consumo": {"clausulas": ["r1"]}}),
                            ("005_mapear_numeros", "avaliador", {"chuva": {"clausulas": ["r2"]}, "evaporacao": {"clausulas": ["r1"]}})):
        m.estado["pedidos"][pid] = {"respondido": False}
        m.aplicar(pid, {"tipo": "mapear_numeros", "para": quem}, {"numeros": nums})
    mapa = m.estado["mapa_numeros"]
    assert set(mapa) == {"chuva", "consumo", "evaporacao"} and mapa["chuva"]["origens"] == ["ia", "avaliador"]
    m.estado["modelo"] = {"entradas": [{"nome": "chuva"}], "numeros_excluidos": {"consumo": "o criador fixou o consumo no D"}}
    falhas = m._cobertura_do_mapa()
    assert [f["numero"] for f in falhas] == ["evaporacao"]


def _motor_de_teste(problema_extra=None):
    import json, shutil, tempfile
    from compilador.motor import Motor
    pasta = os.path.join(tempfile.mkdtemp(), "m")
    os.makedirs(pasta)
    prob = json.load(open(os.path.join(os.path.dirname(__file__), "..", "protocolos", "dev", "dev_lugar.json"), encoding="utf-8"))
    prob.update(problema_extra or {})
    with open(os.path.join(pasta, "problema.json"), "w", encoding="utf-8") as f:
        json.dump(prob, f, ensure_ascii=False)
    return Motor(pasta)


def test_cinco_estados_do_resultado():
    """Solução (melhor demonstrado ou só encontrado), impossível nesta forma, impossível no meio, não encontrado no orçamento e indeterminado."""
    m = _motor_de_teste()
    base = {"sensibilidade": [], "nulos": {"candidato_falho": 10}, "calculo_antes": {}, "cadaveres": 10}
    casos = [(dict(base, escolhido={"id": "x", "forca": {}}, cobertura={"amostrados": [], "poda_heuristica": False}), "solucao", "melhor demonstrado"),
             (dict(base, escolhido={"id": "x", "forca": {}}, cobertura={"amostrados": [], "poda_heuristica": True}), "solucao", "melhor encontrado"),
             (dict(base, cobertura={"amostrados": [], "poda_heuristica": False}), "impossivel_nesta_forma", None),
             (dict(base, cobertura={"amostrados": ["a"], "poda_heuristica": False}), "nao_encontrado_no_orcamento", None),
             (dict(base, nulos={"modelo_incerto": 3}, cobertura={"amostrados": [], "poda_heuristica": False}), "indeterminado", None)]
    for ult, tipo, otim in casos:
        m.estado["criacoes"] = [ult]
        d = m._desfecho()
        assert d["tipo"] == tipo, (tipo, d["tipo"])
        assert otim is None or d["otimalidade"].startswith(otim)
        assert "validado_no_mundo" in d["premissas"]


def test_ia_responde_pelo_criador_e_fica_marcado():
    m = _motor_de_teste({"ia_responde_pelo_criador": True})
    assert m._quem_decide() == "ia" and m._papel_de_criador()
    m.estado["D_proposto"] = {"clausulas": [{"id": "r1", "tipo": "rigida", "enunciado": "e", "teste": {"medida": "v", "op": ">=", "valor": 1}}],
                              "escopo": {}, "ambiguidades": [{"id": "a1"}]}
    m.estado["pedidos"]["002_confirmar_D"] = {"respondido": False}
    m.aplicar("002_confirmar_D", {"tipo": "confirmar_D", "para": "ia"}, {"clausulas": {"r1": {"acao": "confirmar", "justificativa": "cabe no pedido"}},
                                                                        "ambiguidades": {"a1": "opção 2"}})
    assert m.estado["D"]["clausulas"][0]["confirmada_por"] == "ia"
    assert {"clausula", "ambiguidade"} <= {k for x in m.estado["decisoes_da_ia"] for k in x}


def test_foto_tirada_no_executor_e_metricas_da_foto():
    """O executor devolve a foto com hash; o adaptador a guarda e a reusa: as métricas saem da foto sem rodar o candidato de novo."""
    import json, subprocess, sys, tempfile
    from compilador import adaptador_maquina as AM
    from compilador.executor_generico import _carregar
    nl = chr(10)
    t = {"carga": "def gerar_carga(semente):" + nl + "    return {'n': 5}",
         "candidato": "def executar(entrada, a=1):" + nl + "    return {'v': [a * i for i in range(entrada['n'])]}",
         "metricas": "def metricas(entrada, saida):" + nl + "    return {'soma': sum(saida['v'])}",
         "oraculos": ["def conferir(entrada, saida):" + nl + "    return True, 'ok'"],
         "foto": "def foto(entrada, saida):" + nl + "    return {'v': saida['v']}",
         "params": {"a": 2}, "semente": 1, "repeticoes": 1, "rodadas": 1, "tempo_limite_s": 60}
    arq = os.path.join(tempfile.mkdtemp(), "t.json")
    json.dump(t, open(arq, "w", encoding="utf-8"))
    saida = subprocess.run([sys.executable, "-B", AM.EXECUTOR, "medir", arq], capture_output=True, text=True, timeout=120).stdout
    r = json.loads(saida.strip().splitlines()[-1])
    assert r["metricas"]["soma"] == 20 and "foto_b64" in r
    ad = AM.AdaptadorMaquina({"representacao": {"arquetipos": []}, "id": "m", "carga": t["carga"], "oraculo": t["oraculos"][0],
                              "metricas_da_foto": "def metricas_da_foto(foto):" + nl + "    return {'soma': sum(foto['v'])}"},
                             [], __import__("types").SimpleNamespace(id="local", tipo="local"), pasta_fotos=tempfile.mkdtemp())
    r2 = ad._guardar_foto(r, "x")
    foto = ad.ler_foto(r2["foto"])
    assert foto == {"v": [0, 2, 4, 6, 8]} and "foto_b64" not in r2
    assert _carregar(ad.m["metricas_da_foto"], "metricas_da_foto")(foto)["soma"] == 20




def test_voltas_da_emenda_1():
    """As sete voltas da emenda 1 da fórmula 4.0: distinguibilidade, ponto fixo, horizonte, Mapa(D, L), Dom(M), mundo e σ da concorrência."""
    from compilador import motor as mo
    assert mo._no_horizonte({"valor": 10.0, "incerteza": [9, 11]}, 0.5, 4)["incerteza"] == [9, 13]
    d = mo._meio_com_efeito({"numeros": {"cpu": {"valor": 6.0, "incerteza": [5.5, 6.5]}}}, {"cpu": -1})
    assert d["numeros"]["cpu"]["valor"] == 5.0 and d["numeros"]["cpu"]["incerteza"] == [4.5, 5.5]
    dom = {"arquetipos": ["a"], "variaveis": {"k": [1, 3]}}
    assert mo._no_dominio({"_arquetipo": "a", "k": 2}, dom) and not mo._no_dominio({"_arquetipo": "a", "k": 5}, dom) and not mo._no_dominio({"_arquetipo": "b"}, dom)
    assert mo._sigma_da_concorrencia(10.0, 3600, 6)["populacao"] == 96 and mo._sigma_da_concorrencia(100.0, 3600, 6)["populacao"] == 12
    m = _motor_de_teste()
    m.estado["impossivel_no_meio"] = {"r1": {"distinguivel": False, "prova": "mesma entrada, verdades diferentes"}}
    assert m._desfecho()["tipo"] == "impossivel_no_meio"
    m = _motor_de_teste()
    m.estado["desfecho"] = {"tipo": "solucao"}
    m.registrar_mundo({"artefato": "x", "resultado": "falhou", "detalhe": "vazou"})
    assert m.estado["desfecho"] is None and len(m.estado["falhas_no_mundo"]) == 1
    # o horizonte e o Mapa(D, L) no laço
    m = _motor_de_teste({"avaliador": False})
    m.estado["D_proposto"] = {"clausulas": [{"id": "r1", "tipo": "rigida", "enunciado": "e", "teste": {"medida": "v", "op": ">=", "valor": 1}}],
                              "escopo": {"alem_do_horizonte": True}, "ambiguidades": []}
    m.estado["pedidos"]["001_confirmar_D"] = {"respondido": False}
    m.aplicar("001_confirmar_D", {"tipo": "confirmar_D", "para": "criador"}, {"clausulas": {"r1": {"acao": "confirmar"}}})
    m._decidir()
    ult = sorted(m.estado["pedidos"])[-1]
    assert ult.endswith("confirmar_D") and not m.estado["D_confirmado"]
    m.estado["pedidos"][ult]["respondido"] = True
    m.aplicar(ult, {"tipo": "confirmar_D", "para": "criador"}, {"clausulas": {"r1": {"acao": "confirmar"}}})
    m.estado["mapa_pedido"] = True
    m.estado["modelo"] = {"id": "m1", "hash": "h", "representacao": {"arquetipos": [{"nome": "sem_pulmao", "variaveis": []}]}}
    m._decidir()
    ult = sorted(m.estado["pedidos"])[-1]
    assert ult.endswith("mapear_numeros") and m.estado["L_mapeada"] == ["sem_pulmao"]
    # em L que compõe, as primitivas também são formas
    m.estado["pedidos"][ult]["respondido"] = True
    m.estado["modelo"]["representacao"]["composicao"] = {"primitivas": [{"nome": "gaveta", "variaveis": []}], "max_pecas": 3}
    m._decidir()
    assert sorted(m.estado["pedidos"])[-1].endswith("mapear_numeros") and "composicao:gaveta" in m.estado["L_mapeada"]


def test_L_que_compoe():
    """L como linguagem: corpos feitos de peças de primitivas, com mutação que acrescenta, tira e troca peças, e cruzamento de listas."""
    import random
    from compilador import gerar
    rep = {"arquetipos": [], "composicao": {"primitivas": [{"nome": "gaveta", "variaveis": [{"nome": "w", "tipo": "inteiro", "min": 10, "max": 50, "passo": 10}]},
                                                          {"nome": "tabela", "variaveis": []}], "min_pecas": 1, "max_pecas": 4,
                                           "variaveis": [{"nome": "taxa_de_mutacao", "tipo": "real", "min": 0.3, "max": 0.9}]}}
    cs = gerar.grade_ou_amostra(rep, 12, 3)
    assert len(cs) == 12 and all(c["_arquetipo"] == "composicao" and 1 <= len(c["pecas"]) <= 4 for c in cs)
    assert len({c["_id"] for c in cs}) == 12
    r = random.Random(1)
    arq = dict(rep["composicao"], nome="composicao")
    filhos = [gerar.mutar(cs[0], arq, r) for _ in range(30)]
    assert len({len(f["pecas"]) for f in filhos}) > 1 and all(1 <= len(f["pecas"]) <= 4 for f in filhos)
    vistos = []

    def aval(lote):
        vistos.extend(lote)
        return [([len(c["pecas"])], 0.0) for c in lote]
    pop, n = gerar.nsga2(rep, aval, None, None, 60, semente=2, populacao=8)
    assert n >= 20 and all(c["_arquetipo"] == "composicao" for c in pop)


def test_ferramenta_declarada_do_executor():
    """Emenda 2: o candidato importa só a ferramenta declarada; sem a declaração, ou com o binário mudado, ela recusa."""
    import os, tempfile
    import importlib, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compilador"))
    import executor_generico as ex
    assert "ferramenta_passeio" in ex.PERMITIDOS and "subprocess" not in ex.PERMITIDOS and "os" not in ex.PERMITIDOS
    fp = importlib.import_module("ferramenta_passeio")
    velho = {k: os.environ.pop(k, None) for k in ("FERRAMENTA_PASSEIO", "FERRAMENTA_PASSEIO_SHA256")}
    assert not fp.disponivel()
    arq = os.path.join(tempfile.mkdtemp(), "bin")
    open(arq, "wb").write(b"x")
    os.environ.update(FERRAMENTA_PASSEIO=arq, FERRAMENTA_PASSEIO_SHA256="0" * 64)
    assert not fp.disponivel()
    for k, v_ in velho.items():
        os.environ.pop(k, None)
        if v_:
            os.environ[k] = v_


def test_parada_pela_fronteira_de_valores():
    """Com empates, a concorrência para quando os valores da fronteira ficam iguais por N gerações (não os nomes dos concorrentes)."""
    from compilador import gerar
    rep = {"arquetipos": [{"nome": "a", "variaveis": [{"nome": "x", "tipo": "real", "min": 0.0, "max": 1.0}]}]}
    pop, n = gerar.nsga2(rep, lambda cs: [([1.0], 0.062) for _ in cs], None, None, 100000, semente=1, populacao=8, parar_sem_melhora=3)
    assert gerar.nsga2.ultima_parada["motivo"].startswith("a primeira fronteira ficou igual") and gerar.nsga2.ultima_parada["geracoes"] <= 4


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok", nome)
