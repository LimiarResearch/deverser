"""As provas da Máquina do Dever-Ser 4.3.1 só com a seleção. Rodar: python -B testes/test_selecao.py (alguns segundos)."""
import json
import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exemplos import novo_d_do_zero as EX  # noqa: E402
from experimentos import condutor_de_selecao as C  # noqa: E402
from experimentos import foto_atomica as FA  # noqa: E402
from experimentos import variacao as VA  # noqa: E402

AUT = "provas do pacote"


def _pasta():
    return tempfile.mkdtemp(prefix="selecao_")


def _correr(semente, max_rodadas=3000, problema=None, **kw):
    p, av = EX.criar()
    pasta = _pasta()
    try:
        c = C.Corrida(problema or p, av, pasta, C.Config(semente=semente, max_rodadas=max_rodadas, **kw), autorizacao=AUT).rodar()
        dec = json.load(open(os.path.join(pasta, "declaracao.json"), encoding="utf-8"))
        cands = sorted(f for f in os.listdir(pasta) if f.startswith("candidata_"))
        cand = json.load(open(os.path.join(pasta, cands[0]), encoding="utf-8")) if cands else None
        n_fotos = sum(1 for _ in open(os.path.join(pasta, "fotos.jsonl"), encoding="utf-8"))
        return c, dec, cand, n_fotos
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def test_a_codificacao_do_exemplo_passa_no_contrato():
    p, _ = EX.criar()
    rel = FA.verificar_codificacao(p.codificacao)
    assert rel["ok"], rel["falhas"]


def test_a_variacao_as_cegas_e_o_operador_dao_filhos_legais_e_novos():
    p, av = EX.criar()
    cod, g = p.codificacao, np.random.default_rng(0)
    mapa = VA.Mapa(cod)
    for _ in range(30):
        b = cod.sortear(g)
        molde = VA.Molde(mapa, b, p.julgar(av.medir([b])[0]))
        for cands in (VA.amostrar_cego(molde, mapa, 10, g), VA.amostrar_operador(molde, mapa, 10, g)):
            assert cands, "nenhum filho"
            chaves = {cod.chave(c.bits) for c in cands}
            assert len(chaves) == len(cands), "filhos repetidos"
            assert molde.chave not in chaves, "um filho igual ao pai"
            for c in cands:
                assert cod.legal(c.bits) and np.array_equal(cod.canonizar(c.bits), c.bits)


def test_acha_o_D_do_exemplo_e_para_esperando_o_ok():
    for s in range(1, 6):
        c, dec, cand, _ = _correr(s)
        assert c.parada == "D cumprido: espera o Ok", (s, c.parada)
        assert cand is not None and cand["veredito"]["nfal"] == 0 and cand["veredito"]["distancia"] == 0
        p, av = EX.criar()
        bits = np.array([int(x) for x in cand["bits"]], np.uint8)
        assert p.julgar(av.medir([bits])[0])["distancia"] == 0, "a candidata não cumpre D quando medida de novo"
        assert dec["final"] and dec["autorizacao"] == AUT


def test_a_mesma_semente_da_a_mesma_corrida():
    a = _correr(7, max_rodadas=40)[1]
    b = _correr(7, max_rodadas=40)[1]
    for k in ("rodadas", "fotos_medidas", "avaliacoes_de_V", "bracos", "pais", "melhor", "curva_da_melhor", "candidatas", "parada"):
        assert a[k] == b[k], k


def test_cada_foto_medida_fica_guardada_e_nenhuma_e_medida_duas_vezes():
    c, dec, _, n_fotos = _correr(3, max_rodadas=30)
    assert n_fotos == dec["fotos_medidas"] == dec["avaliacoes_de_V"]["total"]
    assert len(c.fotos.indice) == len(c.fotos)


def test_o_acaso_puro_como_braco():
    c, dec, _, _ = _correr(2, max_rodadas=20, bracos=("sorteio",))
    assert dec["bracos"]["sorteio"]["avaliacoes_de_V"] > 0
    assert all(o in ("sorteio de partida", "sorteio") for o in c.fotos.origem)


def test_sem_autorizacao_nada_e_lancado():
    p, av = EX.criar()
    pasta = _pasta()
    try:
        for aut in (None, "", "   "):
            try:
                C.Corrida(p, av, pasta, C.Config(), autorizacao=aut)
            except PermissionError:
                continue
            raise AssertionError("lançou sem autorização")
        assert not os.listdir(pasta)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def test_uma_pasta_com_corrida_e_recusada():
    p, av = EX.criar()
    pasta = _pasta()
    try:
        C.Corrida(p, av, pasta, C.Config(max_rodadas=2), autorizacao=AUT).rodar()
        try:
            C.Corrida(p, av, pasta, C.Config(), autorizacao=AUT)
        except FileExistsError:
            return
        raise AssertionError("aceitou uma pasta que já tem corrida")
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def test_configuracao_desconhecida_e_recusada():
    for kw in ({"aprendiz": True}, {"bracos": ("aprendida",)}, {"bracos": ()}):
        try:
            C.Config(**kw)
        except (TypeError, ValueError):
            continue
        raise AssertionError(f"aceitou {kw}")


def test_V_que_reprova_nos_controles_nao_deixa_comecar():
    p, av = EX.criar()
    p.calibrar = lambda: {"ok": False, "motivo": "controle negativo passou"}
    c, dec, cand, n = _correr(1, problema=p)
    assert c.parada.startswith("V reprovou") and n == 0 and cand is None and dec["avaliacoes_de_V"]["total"] == 0


def test_hash_de_V_que_muda_anula_a_corrida():
    p, _ = EX.criar()
    estado = {"n": 0}

    def hash_de_v():
        estado["n"] += 1
        return f"h{estado['n']}"
    p.hash_de_v = hash_de_v
    c = _correr(1, max_rodadas=5, problema=p)[0]
    assert "INTEGRIDADE" in c.parada


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    n = 0
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            n += 1
            print("ok", nome)
    print(f"{n} de {n} provas passaram")
