"""O núcleo: versionamento de D e Π, a regra de transferência e a seleção, sem domínio nenhum."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bancada.nucleo.ledger import Ledger  # noqa: E402
from bancada.nucleo.modelo import D, Pi  # noqa: E402
from bancada.nucleo.selecao import pareto, preferir  # noqa: E402


def _d():
    return D({"escopo": {"n": 10}, "clausulas": [
        {"id": "a", "tipo": "rigida", "teste": {"medida": "x", "op": "<=", "valor": 1}},
        {"id": "o1", "tipo": "objetivo", "teste": {"medida": "x", "sentido": "min"}},
        {"id": "o2", "tipo": "objetivo", "teste": {"medida": "y", "sentido": "max"}}]})


def _pi(v=5.0, inc=None, unidade="s", tipo="medido", grandeza=None):
    return Pi({"numeros": {"t": {"valor": v, "tipo": tipo, "incerteza": inc, "unidade": unidade, "grandeza": grandeza}}})


def test_versoes_ligadas_pelo_hash():
    d1 = _d()
    d2 = d1.nova_versao(mudar={"a": {"teste": {"medida": "x", "op": "<=", "valor": 2}}}, motivo="relaxa")
    assert d2.versao == 2 and d2.dados["pai"] == d1.hash() and d1.dados["clausulas"][0]["teste"]["valor"] == 1


def test_clausula_da_ia_so_entra_confirmada():
    d = D({"clausulas": [{"id": "a", "tipo": "rigida", "origem": "ia", "teste": {"medida": "x", "op": "<=", "valor": 1}}]})
    assert d.rigidas() == [] and d.incompleto()


def test_transferencia():
    d1, p1 = _d(), _pi(5.0, [4.0, 6.0])
    led = Ledger()
    led.acrescentar("evidencia", {"hipoteses": Ledger.hipoteses(d1, ["a"], p1, ["t"], escopo=["n"])})
    assert len(led.transferir(d1, p1)[0]) == 1
    # a cláusula mudou: cai
    d2 = d1.nova_versao(mudar={"a": {"teste": {"medida": "x", "op": "<=", "valor": 2}}})
    v, c = led.transferir(d2, p1)
    assert not v and "mudou" in c[0]["caiu_porque"]
    # o enunciado mudou, o teste não: vale
    d3 = d1.nova_versao(mudar={"a": {"enunciado": "outro texto"}})
    assert len(led.transferir(d3, p1)[0]) == 1
    # o mesmo número: vale; o valor andou, mesmo dentro da incerteza: cai (a regra padrão, emenda de 28/09); ficou ausente: cai
    assert len(led.transferir(d1, _pi(5.0, [4.0, 6.0]))[0]) == 1
    assert "mudou de valor" in led.transferir(d1, _pi(5.5, [4.0, 6.0]))[1][0]["caiu_porque"]
    ausente = Pi({"numeros": {"t": {"valor": None, "tipo": "ausente"}}})
    assert "ausente" in led.transferir(d1, ausente)[1][0]["caiu_porque"]
    # o escopo mudou: cai
    d4 = D(dict(d1.dados, escopo={"n": 11}))
    assert "escopo" in led.transferir(d4, p1)[1][0]["caiu_porque"]


def _pic(v=25.0, inc=(18.0, 32.0), unidade="m/s", tipo="aproximacao", grandeza=None, metodo="m1", fonte="f1"):
    return Pi({"numeros": {"t": {"valor": v, "tipo": tipo, "incerteza": list(inc) if inc else None, "unidade": unidade,
                                 "grandeza": grandeza or {"estatistica": "rajada 3 s"}, "metodo": metodo, "fonte": fonte}}})


def test_transferencia_cada_dimensao_e_combinacoes():
    """A regra padrão ("igual", emenda de 28/09): a evidência só fica com o mesmo número. Cada dimensão sozinha derruba, e as
    combinações também; o mesmo número mantém. É o que dá veredito igual ao de uma corrida sem reuso."""
    d1, p1 = _d(), _pic()
    led = Ledger()
    led.acrescentar("evidencia", {"hipoteses": Ledger.hipoteses(d1, (), p1, ["t"])})
    assert len(led.transferir(d1, _pic())[0]) == 1
    uma = {"unidade": _pic(unidade="km/h"), "tipo": _pic(tipo="hipotese"), "grandeza": _pic(grandeza={"estatistica": "média horária"}),
           "metodo": _pic(metodo="m2"), "fonte": _pic(fonte="f2"), "centro": _pic(v=26.0), "mais_larga": _pic(inc=(10.0, 40.0)),
           "mais_estreita": _pic(inc=(20.0, 30.0)), "sem_incerteza": _pic(inc=None)}
    for nome, p in uma.items():
        v, c = led.transferir(d1, p)
        assert not v, nome
    combos = {"unidade_e_estreita": _pic(unidade="km/h", inc=(20.0, 30.0)), "tipo_e_larga": _pic(tipo="medido", inc=(10.0, 40.0)),
              "fonte_e_centro": _pic(fonte="f2", v=24.0)}
    for nome, p in combos.items():
        assert not led.transferir(d1, p)[0], nome


def test_transferencia_modos_declarados():
    """Os modos em que o verificador declara a validade: "estado" (o centro dentro de uma tolerância declarada) e "declarado" (o
    intervalo dentro de uma região declarada). A validade nunca sai da amostra."""
    d1 = _d()
    p_ns = Pi({"numeros": {"t": {"valor": 300.0, "tipo": "medido", "incerteza": [280.0, 380.0], "unidade": "ns"}}})
    led = Ledger()
    led.acrescentar("evidencia", {"hipoteses": Ledger.hipoteses(d1, (), p_ns, [Ledger.estado("t", p_ns, 0.15)])})
    ok = Pi({"numeros": {"t": {"valor": 330.0, "tipo": "medido", "incerteza": [300.0, 400.0], "unidade": "ns"}}})
    fora = Pi({"numeros": {"t": {"valor": 360.0, "tipo": "medido", "incerteza": [340.0, 380.0], "unidade": "ns"}}})
    assert len(led.transferir(d1, ok)[0]) == 1 and not led.transferir(d1, fora)[0]
    led2 = Ledger()
    led2.acrescentar("evidencia", {"hipoteses": Ledger.hipoteses(d1, (), _pic(), [("t", "declarado", [10.0, 50.0])])})
    assert len(led2.transferir(d1, _pic(inc=(15.0, 45.0)))[0]) == 1 and not led2.transferir(d1, _pic(inc=(5.0, 45.0)))[0]


def test_rigidas_exatas():
    d1, p1 = _d(), _pi(5.0, [4.0, 6.0])
    led = Ledger()
    led.acrescentar("evidencia", {"hipoteses": Ledger.hipoteses(d1, ["a"], p1, (), rigidas_exatas=True)})
    d2 = d1.nova_versao(acrescentar=[{"id": "b", "tipo": "rigida", "teste": {"medida": "y", "op": ">=", "valor": 0}}])
    v, c = led.transferir(d2, p1)
    assert not v and "entrou ['b']" in c[0]["caiu_porque"]


def test_hash_nao_distingue_2500_de_2500_0():
    from bancada.nucleo.modelo import hash_clausula
    a = {"id": "r", "tipo": "rigida", "teste": {"medida": "x", "op": ">=", "valor": 2500}}
    b = {"id": "r", "tipo": "rigida", "teste": {"medida": "x", "op": ">=", "valor": 2500.0}}
    assert hash_clausula(a) == hash_clausula(b)


def test_pareto_e_preferencia():
    d = _d()
    vs = [{"veredito": {"medidas": {"x": 1, "y": 1}}}, {"veredito": {"medidas": {"x": 2, "y": 3}}}, {"veredito": {"medidas": {"x": 2, "y": 0}}}]
    fr = pareto(vs, d.objetivos())
    assert fr["fronteira"] == [0, 1] and fr["dominados"] == [{"corpo": 2, "dominado_por": 0}]
    assert preferir(vs, {"ordem": [["y", "max"]]})["ordem"][0] == 1


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok", nome)
