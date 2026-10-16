# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import numpy as np
if os.name == 'nt':
    import shutil
    if shutil.which('g++'):
        os.add_dll_directory(os.path.dirname(shutil.which('g++')))
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(AQUI))
from experimentos import compositor_de_corpus as CC
from experimentos import condutor_de_fotos as C
from experimentos import coletor_de_intervencoes as CI
from experimentos import l_ser_interp as I
from experimentos import l_ser_lang as L
from mundos_falsos import MundoDoSerOculto
from test_c3_condutor_v2 import V2DeMentira
from test_condutor_de_fotos import _config

def _env():
    g = np.random.default_rng(12)
    env = [g.uniform(-0.5, 0.5, 9).astype(np.float32) for _ in L.ENTRADAS['peso']]
    env[0] *= 0
    env[1] = np.ones(9, np.float32)
    return env

def ex(op, *a):
    return CC.Expr(op, tuple(a), 0)

def test_a_montagem_leva_as_dependencias():
    env = _env()
    doador = CC.compilar(ex('mul', ex('add', 'w', 'P'), ex('sub', 'Q', 'err')))
    pai = CC.compilar(ex('sub', ex('neg', 'w'), ex('add', 'P', 'err')))
    raw = [L.No(*n.como_tupla()) for n in pai]
    raw[7] = L.No(*doador[7].como_tupla())
    assert not np.allclose(I.Plano(raw, 'peso').rodar(env), I.Plano(doador, 'peso').rodar(env))
    e, _ = CC.extrair(doador, 'peso')
    np.testing.assert_allclose(I.Plano(CC.compilar(e), 'peso').rodar(env), I.Plano(doador, 'peso').rodar(env))
    alvo = L.codificar_programa(L.programa(W_SAIDA=L.E('mul', L.E('add', 'w', 'P'), L.E('sub', 'Q', 'err'))))
    base = L.codificar_programa(L.programa(W_SAIDA=L.E('id', 'w')))
    seq = base.copy()
    for n in (5, 6, 7):
        pos = L._POR_NOME[f'W_SAIDA.n{n}.op']['inicio']
        seq[pos:pos + 25] = alvo[pos:pos + 25]
        seq = L.canonizar_bits(seq)
    palvo = L.decodificar_bits(alvo)
    assert not np.allclose(I.Plano(L.decodificar_bits(seq).secoes['W_SAIDA'], 'peso').rodar(env), I.Plano(palvo.secoes['W_SAIDA'], 'peso').rodar(env))
    e, _ = CC.extrair(palvo.secoes['W_SAIDA'], 'peso')
    atomico = L.decodificar_bits(CC.reencadernar(base, 'W_SAIDA', e))
    np.testing.assert_allclose(I.Plano(atomico.secoes['W_SAIDA'], 'peso').rodar(env), I.Plano(palvo.secoes['W_SAIDA'], 'peso').rodar(env))
    print('  a raiz sozinha muda de função; o fragmento fechado e a regravação de uma vez a mantêm')

class V2PareadaDeMentira(V2DeMentira):

    def __init__(self, mundo):
        super().__init__(mundo)
        self.vidas_pedidas = []

    def medir_nas_vidas(self, lista_de_bits, vidas):
        self.vidas_pedidas.append([tuple(v) for v in vidas])
        res = self.base.medir(lista_de_bits)
        return [[dict(r) for _ in vidas] for r in res]

def _corrida(pasta, fracao, rodadas=12):
    mundo = MundoDoSerOculto(0)
    av = V2PareadaDeMentira(mundo)
    cfg = _config(max_rodadas=rodadas, v2_nivel_decisao=3, v2_epoca_geracoes=50, v2_elite=4, coletor_fracao=fracao, coletor_vidas=3)
    c = C.Corrida(mundo.problema(), av, pasta, cfg)
    c.rodar()
    return (c, av)

def test_o_grupo_e_pareado_e_os_bits_voltam():
    pasta = tempfile.mkdtemp()
    c, av = _corrida(pasta, 0.2)
    linhas = [json.loads(x) for x in open(os.path.join(pasta, 'intervencoes.jsonl'), encoding='utf-8')]
    assert linhas, 'nenhum grupo coletado'
    for reg in linhas:
        assert set(reg['medidas']) >= {'P', 'A', 'B', 'AB'}
        vidas = {tuple(((m['semente'], m['semente_pert']) for m in ms)) for ms in reg['medidas'].values()}
        assert len(vidas) == 1 and len(next(iter(vidas))) == 3
        bits = {v: CI.desempacotar(t) for v, t in reg['bits'].items()}
        assert all((not np.array_equal(bits[v], bits['P']) for v in bits if v != 'P'))
        for b in bits.values():
            L.decodificar_bits(b)
    assert all((len(set(v)) == 3 for v in av.vidas_pedidas))
    reusos = sum((1 for reg in linhas if reg.get('reuso_de_A')))
    reparos = sum((1 for reg in linhas if reg.get('reparo')))
    print(f"  {len(linhas)} grupos, todos pareados; {reparos} com reparo cego, {reusos} com o fragmento A reusado noutro pai; descartes do último: {linhas[-1]['descartes']}")

def test_a_sombra_nao_muda_a_corrida():
    pa, pb = (tempfile.mkdtemp(), tempfile.mkdtemp())
    a, _ = _corrida(pa, 0.0)
    b, _ = _corrida(pb, 0.2)
    assert len(a.fotos) == len(b.fotos)
    for k in range(len(a.fotos)):
        assert np.array_equal(a.fotos.foto(k), b.fotos.foto(k)) and a.fotos.veredito(k)['distancia'] == b.fotos.veredito(k)['distancia']
    ra = [{k: v for k, v in json.loads(x).items() if k not in ('t',)} for x in open(os.path.join(pa, 'log_rodadas.jsonl'), encoding='utf-8')]
    rb = [{k: v for k, v in json.loads(x).items() if k not in ('t',)} for x in open(os.path.join(pb, 'log_rodadas.jsonl'), encoding='utf-8')]
    assert ra == rb
    col = b.contadores.get('avaliacoes_do_coletor', 0)
    tot = b.contadores['avaliacoes_de_V']
    assert a.contadores['avaliacoes_de_V'] == tot - col
    frac = col / tot
    print(f'  o mesmo arquivo ({len(a.fotos)} fotos) e as mesmas {len(ra)} rodadas; coletor {col} de {tot} medidas ({frac:.0%})')
    assert 0.1 < frac < 0.3

def test_a_interrupcao_no_aquecimento_grava_e_a_retomada_termina_o_aquecimento():
    pasta = tempfile.mkdtemp()
    mundo = MundoDoSerOculto(0)
    cfg = dict(max_rodadas=4, v2_nivel_decisao=3, v2_epoca_geracoes=50, v2_elite=4, aquecimento_piscinas=4)
    c = C.Corrida(mundo.problema(), V2PareadaDeMentira(mundo), pasta, _config(**cfg))
    original, feitas = (c._rotular, [])

    def rotular_e_parar(n, finalidade='piscinas (decisões rotuladas por inteiro)'):
        for _ in range(n):
            if len(feitas) == 2:
                raise KeyboardInterrupt
            original(1, finalidade)
            feitas.append(1)
    c._rotular = rotular_e_parar
    try:
        c.rodar()
    except KeyboardInterrupt:
        pass
    est = json.load(open(os.path.join(pasta, 'estado.json'), encoding='utf-8'))
    assert est['rodada'] == 0 and est['contadores']['piscinas_rotuladas'] == 2
    d = C.Corrida(mundo.problema(), V2PareadaDeMentira(mundo), pasta, _config(**dict(cfg, coletor_fracao=0.2)))
    d.rodar()
    ev = [json.loads(x) for x in open(os.path.join(pasta, 'log_eventos.jsonl'), encoding='utf-8')]
    ret = [e for e in ev if e.get('evento') == 'aquecimento_retomado']
    assert ret and ret[0]['faltam'] == 2 and (d.contadores['piscinas_rotuladas'] >= 4) and (d.rodada_n >= 4)
    print(f"  parou com 2 de 4 piscinas; a retomada fez as 2 que faltavam e rodou {d.rodada_n} rodadas, com {d.contadores.get('grupos_do_coletor', 0)} grupos do coletor")

def test_o_arquivo_parar_para_na_fronteira_da_geracao_e_a_retomada_segue():
    pasta = tempfile.mkdtemp()
    mundo = MundoDoSerOculto(0)
    cfg = dict(max_rodadas=9, v2_nivel_decisao=3, v2_epoca_geracoes=50, v2_elite=4)
    open(os.path.join(pasta, 'PARAR'), 'w').close()
    c = C.Corrida(mundo.problema(), V2PareadaDeMentira(mundo), pasta, _config(**cfg))
    c.rodar()
    assert c.parada.startswith('pedido de parada') and c.rodada_n == 3 and os.path.exists(os.path.join(pasta, 'PARAR.atendido'))
    d = C.Corrida(mundo.problema(), V2PareadaDeMentira(mundo), pasta, _config(**cfg))
    d.rodar()
    assert d.rodada_n == 9 and d.parada.startswith('fusível')
    print(f'  parou na rodada {c.rodada_n} (fim da 1ª geração), gravou, e a retomada seguiu até a {d.rodada_n}')
if __name__ == '__main__':
    test_o_arquivo_parar_para_na_fronteira_da_geracao_e_a_retomada_segue()
    test_a_interrupcao_no_aquecimento_grava_e_a_retomada_termina_o_aquecimento()
    test_a_montagem_leva_as_dependencias()
    test_o_grupo_e_pareado_e_os_bits_voltam()
    test_a_sombra_nao_muda_a_corrida()
    print('ok')
