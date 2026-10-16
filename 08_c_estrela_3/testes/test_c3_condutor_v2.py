# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(AQUI))
from experimentos import arquivo_de_fotos as AF
from experimentos import condutor_de_fotos as C
from mundos_falsos import AvaliadorFalso, MundoDoSerOculto
from test_condutor_de_fotos import _config

class V2DeMentira:
    piscina = (1, 2, 3)

    def __init__(self, mundo):
        self.base = AvaliadorFalso(mundo)
        self.mundo = mundo
        self.chamadas = []

    def medir(self, lista_de_bits, sal=0, nivel=1):
        self.chamadas.append((len(lista_de_bits), sal, nivel))
        res = self.base.medir(lista_de_bits)
        out = []
        for r in res:
            r = dict(r)
            if nivel > 1:
                d = self.mundo.problema().julgar(r)['distancia'] if r.get('estado', 'ok') == 'ok' else 0
                r['medidas_do_nivel'] = [{'semente': s, 'semente_pert': 0, 'distancia': int(d) + 7 * j} for j, s in enumerate(self.piscina[:nivel])]
            out.append(r)
        return out

    def fechar(self):
        pass

def test_o_arquivo_corrige_o_veredito_e_a_correcao_sobrevive_ao_carregar():
    mundo = MundoDoSerOculto(0)
    pasta = tempfile.mkdtemp()
    c = C.Corrida(mundo.problema(), AvaliadorFalso(mundo), pasta, _config(max_rodadas=3))
    c.rodar()
    f = c.fotos
    k = int(f.melhores(1)[0])
    ver = dict(f.veredito(k))
    ver['distancia'] = int(ver['distancia']) + 123
    f.reverificar(k, ver)
    f.salvar(os.path.join(pasta, 'fotos'))
    g = AF.ArquivoDeFotos.carregar(os.path.join(pasta, 'fotos'), mundo.problema())
    assert g.veredito(k)['distancia'] == ver['distancia'] and len(g) == len(f)

def test_a_corrida_com_a_v2_confirma_vira_o_sal_grava_e_retoma():
    mundo = MundoDoSerOculto(0)
    pasta = tempfile.mkdtemp()
    av = V2DeMentira(mundo)
    cfg = _config(max_rodadas=18, v2_nivel_decisao=3, v2_epoca_geracoes=2, v2_elite=4)
    c = C.Corrida(mundo.problema(), av, pasta, cfg)
    c.rodar()
    eventos = [json.loads(x) for x in open(os.path.join(pasta, 'log_eventos.jsonl'), encoding='utf-8')]
    viradas = [e for e in eventos if e.get('evento') == 'virada_do_sal']
    niveis = {n for _, _, n in av.chamadas}
    sais = {s for _, s, _ in av.chamadas}
    print(f"  confirmações {c.contadores.get('confirmacoes_v2', 0)}, viradas do sal {len(viradas)}, sal {c.sal}, níveis pedidos {sorted(niveis)}, sais {sorted(sais)}")
    assert c.contadores.get('confirmacoes_v2', 0) > 0 and viradas and (c.sal == len(viradas)) and (3 in niveis) and (len(sais) > 1)
    est = json.load(open(os.path.join(pasta, 'estado.json'), encoding='utf-8'))
    assert est['v2']['sal'] == c.sal
    d = C.Corrida(mundo.problema(), V2DeMentira(mundo), pasta, _config(max_rodadas=20, v2_nivel_decisao=3, v2_epoca_geracoes=2, v2_elite=4))
    assert d._retomar() and d.sal == c.sal and (d.confirmadas == c.confirmadas)

def test_sem_a_chave_a_v2_nao_e_pedida():
    mundo = MundoDoSerOculto(0)
    try:
        C.Corrida(mundo.problema(), AvaliadorFalso(mundo), tempfile.mkdtemp(), _config(v2_nivel_decisao=3))
        raise AssertionError('aceitou a chave sem a V v2')
    except ValueError as e:
        assert 'V da busca v2' in str(e)

def test_o_braco_gemeo_tem_credito_proprio_e_a_rede_nao_o_ve_como_braco():
    mundo = MundoDoSerOculto(0)
    pasta = tempfile.mkdtemp()
    cfg = _config(max_rodadas=12)
    cfg.bracos = ('aprendida', 'cega', 'cega_gemea', 'operador')
    c = C.Corrida(mundo.problema(), AvaliadorFalso(mundo), pasta, cfg)
    c.rodar()
    b = c.braco
    print(f"  crédito: cega n={b['cega']['n']} melhoras={b['cega']['melhoras']}; gêmea n={b['cega_gemea']['n']} melhoras={b['cega_gemea']['melhoras']}")
    assert b['cega_gemea']['n'] == b['cega']['n'] > 0
    assert 'cega_gemea' not in getattr(c.escritor, 'vel', {})
    origens = {str(AF.ORIGENS[int(o)]) for o in c.fotos.origem[:len(c.fotos)]}
    assert 'escrita_cega' in origens

def test_com_a_v2_o_molde_e_os_doadores_do_lote_sao_confirmados():
    mundo = MundoDoSerOculto(0)
    pasta = tempfile.mkdtemp()
    av = V2DeMentira(mundo)
    c = C.Corrida(mundo.problema(), av, pasta, _config(max_rodadas=24, v2_nivel_decisao=3, v2_epoca_geracoes=50, v2_elite=4, sementes_cada=1))
    c.rodar()
    g = c.gasto_de_V.por_finalidade
    lotes = c.sementes['lotes']
    print(f'  lotes {lotes}, gasto: ' + ', '.join((f'{k} {v}' for k, v in g.items() if 'v2' in k)))
    assert lotes > 0 and g.get('confirmação v2 (doadores do lote)', 0) > 0
    assert g['confirmação v2 (doadores do lote)'] % 3 == 0

def test_a_migracao_declarada_do_hash_so_aceita_o_par_exato():
    mundo = MundoDoSerOculto(0)
    pasta = tempfile.mkdtemp()
    prob = mundo.problema()
    prob.hash_de_v = lambda: 'hash_A'
    C.Corrida(prob, AvaliadorFalso(mundo), pasta, _config(max_rodadas=6)).rodar()
    prob.hash_de_v = lambda: 'hash_B'
    sem = C.Corrida(prob, AvaliadorFalso(mundo), pasta, _config(max_rodadas=8))
    sem.rodar()
    assert sem.parada == 'instrumento'
    errada = C.Corrida(prob, AvaliadorFalso(mundo), pasta, _config(max_rodadas=8))
    errada.migracao_do_hash = {'de': 'hash_X', 'para': 'hash_B', 'prova': 'teste'}
    errada.rodar()
    assert errada.parada == 'instrumento'
    certa = C.Corrida(prob, AvaliadorFalso(mundo), pasta, _config(max_rodadas=12))
    certa.migracao_do_hash = {'de': 'hash_A', 'para': 'hash_B', 'prova': 'teste'}
    certa.rodar()
    assert certa.parada != 'instrumento' and certa.hash_de_v == 'hash_B' and certa.migracoes_do_hash and (certa.rodada_n > 6)
    ev = [json.loads(x) for x in open(os.path.join(pasta, 'log_eventos.jsonl'), encoding='utf-8')]
    assert any((e.get('evento') == 'hash_de_v_migrado' and e.get('de') == 'hash_A' for e in ev))
    est = json.load(open(os.path.join(pasta, 'estado.json'), encoding='utf-8'))
    assert est['migracoes_do_hash'][0]['para'] == 'hash_B'
    print(f'  sem a declaração e com o par errado, para no instrumento; com o par exato, retoma da rodada 6 e segue até {certa.rodada_n}, com a troca no registro')
if __name__ == '__main__':
    for nome, f in list(globals().items()):
        if nome.startswith('test_'):
            f()
            print('ok', nome, flush=True)
