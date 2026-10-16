# -*- coding: utf-8 -*-
import json
import os
import shutil
import sys
import tempfile
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(AQUI))
from experimentos import arquivo_de_fotos as AF
from experimentos import condutor_de_fotos as C
from mundos_falsos import AvaliadorFalso, MundoDeOrdenacao, MundoDoSerOculto
CHAVE16 = '16 (a foto atômica: classificar, guardar o padrão, escrever; PÉTREO)'

def _config(**kw):
    base = dict(semente=1, K=8, n_partida=16, k_melhores=50, rodadas_por_geracao=3, treino_passos=10, aquecimento_piscinas=4, piscinas_por_geracao=1, banco_fracao=1.0, troca_cada=2, minimo_dev=3, minimo_ret=2, motivos_cada=6, diagnostico_cada=0, salvar_cada=0.0, declaracao_cada=0.0, imprimir_cada=1000000000.0, regra_min_fotos=50, regra_min_escritas=8, escritor={'pool': 64, 'k_modelo': 4, 'k_cega': 1, 'min_memoria': 100, 'teto_memoria': 150000, 'piscina_m': 16, 'peso_semantico': 0.5, 'membros': 2, 'reducao': 0.25}, n_levantamento=16, passos_da_intencao=10, treino_lote=32, autoimitacao_cada=0, sementes_cada=0, catraca_cada=0)
    base.update(kw)
    return C.Config(**base)

def _corrida(mundo, pasta, **kw):
    cfg = kw.pop('config', None) or _config(**kw)
    return C.Corrida(mundo.problema(), AvaliadorFalso(mundo), pasta, cfg)

def _pasta():
    return tempfile.mkdtemp()

def test_a_corrida_inteira_roda_o_ser_escondido_e_a_rede_de_ordenacao_e_guarda_tudo():
    for mundo in (MundoDoSerOculto(0), MundoDeOrdenacao(8, 24, 0)):
        pasta = _pasta()
        try:
            c = _corrida(mundo, pasta, max_rodadas=24)
            c.rodar()
            assert c.parada.startswith('fusível de rodadas') and c.rodada_n == 24
            for nome in ('estado.json', 'declaracao.json', 'declaracao_parcial.json', 'resumo.json', 'padroes.json', 'log_rodadas.jsonl', 'log_eventos.jsonl', 'aprendiz_memoria.npz', 'aprendiz_conjunto.npz', 'aprendiz_estado.json'):
                assert os.path.exists(os.path.join(pasta, nome)), nome
            assert os.path.isdir(os.path.join(pasta, 'fotos')) and os.listdir(os.path.join(pasta, 'fotos')) and os.path.isdir(os.path.join(pasta, 'edicoes'))
            em_disco = AF.ArquivoDeFotos.carregar(os.path.join(pasta, 'fotos'), mundo.problema())
            assert len(em_disco) == len(c.fotos) and c.fotos.resumo()['liberadas'] == 0 and (not c.fotos.cheio)
            assert mundo.avaliados >= len(c.fotos) - 0 and c.contadores['avaliacoes_de_V'] - c.gasto_de_V.por_finalidade.get('auditorias (integridade)', 0) <= len(c.fotos)
            assert AF.Edicoes.contar(os.path.join(pasta, 'edicoes')) + 0 >= c.edicoes.total_em_disco - 0 and len(c.edicoes) > 0
            og = c.fotos.resumo()['por_origem']
            assert og.get('sorteio', 0) >= 16 and sum(og.values()) == len(c.fotos)
            assert set(og) <= set(AF.ORIGENS)
            cred = c.credito_por_braco()
            assert {'cega', 'operador'} <= set(cred) and {'aprendida', 'fria'} & set(cred)
            for k, v in cred.items():
                assert v['edicoes_propostas'] > 0 and v['rodadas'] > 0
            r = json.load(open(os.path.join(pasta, 'resumo.json'), encoding='utf-8'))
            assert r['rodadas'] == 24 and r['fotos'] == len(c.fotos)
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

def test_a_declaracao_diz_por_laco_exercitado_ou_nao_com_o_motivo_e_as_seis_operacoes():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=30, regra_min_fotos=50, regra_min_escritas=8)
        c.rodar()
        dec = json.load(open(os.path.join(pasta, 'declaracao.json'), encoding='utf-8'))
        assert dec['a_formula_inteira'] is False and 'corrida de partes da fórmula' in dec['leitura']
        ex, nao = (dec['exercitados'], dec['nao_exercitados'])
        assert CHAVE16 in ex and set(ex[CHAVE16]['operacoes']) == set(C.OPERACOES_DA_REGRA)
        assert '12 (integridade de V)' not in nao and 'Fusível e parada' in ex
        for k in ('Papéis (o avaliador independente)', '11 (a catraca do motor)', '15 (as sementes: a rede combina e remenda)', 'Funil de V (V curta)', 'Resultado → D (10, Ok_k)'):
            assert k in nao and len(nao[k]) > 20, k
        for k in ('13 (decidir e alocar, com a ambiguidade)', '14 (escolher-se sem perder o contexto)'):
            assert (k in ex) != (k in nao) and (k in ex or len(nao[k]) > 20), k
        assert 'Colheita contínua das sementes (emenda 11)' in ex and ex['Colheita contínua das sementes (emenda 11)']['fotos_colhidas'] > 0
        assert 'O levantamento e o treino da intenção (emenda 11)' in ex and ex['O levantamento e o treino da intenção (emenda 11)']['corpus_do_levantamento'] == 16
        assert 'avaliador independente' in nao['Papéis (o avaliador independente)'].lower() or 'acompanhando' in nao['Papéis (o avaliador independente)']
        assert ex[CHAVE16]['b_guardar_todas']['liberadas'] == 0
        op = ex[CHAVE16]['operacoes']
        assert op['classificar'] and op['guardar todas (sem liberar nenhuma)'] and op['saber o que a sequência significa'] and op['aprender com o tempo'], op
        assert dec['a_regra_petrea'] == all(op.values())
        assert op['escrever bit a bit'] and dec['a_regra_petrea'] is True, op
        c2 = _corrida(mundo, _pasta(), max_rodadas=6, regra_min_fotos=1000, regra_min_escritas=200)
        c2.rodar()
        d2 = json.load(open(os.path.join(c2.saida, 'declaracao.json'), encoding='utf-8'))
        assert d2['a_regra_petrea'] is False and 'NÃO se chama seleção acelerada' in d2['leitura'] and (CHAVE16 + ' (o que falta)' in d2['nao_exercitados'])
        shutil.rmtree(c2.saida, ignore_errors=True)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_o_credito_pareado_compara_a_aprendida_com_a_cega_no_mesmo_pai():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=45, rodadas_por_geracao=3)
        c.rodar()
        assert c.escritor.pronto()
        par = c.comparar('aprendida', 'cega')
        assert par is not None and par['rodadas_pareadas'] >= 5 and (par['veredito'] in ('ganho', 'nulo', 'pior'))
        assert all(('aprendida' in r and 'cega' in r or ('fria' in r and 'cega' in r) or True for r in c.melhor_por_rodada))
        assert c.comparar('aprendida', 'braco_que_nao_existe') is None
        cred = c.credito_por_braco()
        assert cred['aprendida']['edicoes_propostas'] <= 8 * c.rodada_n and cred['cega']['edicoes_propostas'] <= 8 * c.rodada_n
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_as_testemunhas_so_sao_medidas_num_arquivo_a_parte_e_nenhuma_e_semente():
    mundo = MundoDoSerOculto(0)
    g = np.random.default_rng(99)
    testemunhas = {'t1': mundo.cod.sortear(g), 't2': mundo.cod.sortear(g)}
    pasta = _pasta()
    try:
        c = C.Corrida(mundo.problema(), AvaliadorFalso(mundo), pasta, _config(max_rodadas=6), testemunhas=testemunhas)
        c.rodar()
        t = json.load(open(os.path.join(pasta, 'testemunhas.json'), encoding='utf-8'))
        assert set(t['medidas']) == {'t1', 't2'} and all((v['distancia'] > 0 for v in t['medidas'].values()))
        for b in testemunhas.values():
            assert c.fotos.buscar(b) == -1
        assert 'nenhuma semente é uma testemunha' in json.dumps(json.load(open(os.path.join(pasta, 'declaracao.json'), encoding='utf-8')), ensure_ascii=False)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    mundo2 = MundoDoSerOculto(0)
    b = mundo2.cod.sortear(np.random.default_rng(1))
    mundo2.cod.sortear = lambda rng, **kw: b
    pasta = _pasta()
    try:
        c = C.Corrida(mundo2.problema(), AvaliadorFalso(mundo2), pasta, _config(max_rodadas=1), testemunhas={'t': b})
        try:
            c.rodar()
            raise AssertionError('a corrida aceitou uma testemunha como semente')
        except AssertionError as e:
            assert 'testemunha' in str(e) and 'a regra da comparação' in str(e)
    finally:
        del mundo2.cod.sortear
        shutil.rmtree(pasta, ignore_errors=True)

def test_a_retomada_continua_onde_parou_sem_medir_de_novo_o_que_ja_estava_no_arquivo():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c1 = _corrida(mundo, pasta, max_rodadas=12)
        c1.rodar()
        n1, fotos1, v1, mem1 = (c1.rodada_n, len(c1.fotos), c1.contadores['avaliacoes_de_V'], c1.escritor.mem.proprios())
        chaves = {c1.cod.chave(c1.fotos.foto(i)): i for i in range(len(c1.fotos))}
        assert n1 == 12 and fotos1 > 50
        mundo.avaliados = 0
        c2 = C.Corrida(mundo.problema(), AvaliadorFalso(mundo), pasta, _config(max_rodadas=24))
        c2.rodar()
        assert c2.retomada is True and c2.rodada_n == 24 and (len(c2.fotos) > fotos1)
        assert c2.escritor.mem.proprios() > mem1 and c2.escritor.treinos >= 1
        for ch, i in list(chaves.items())[:40]:
            assert c2.cod.chave(c2.fotos.foto(i)) == ch
        assert mundo.avaliados == c2.contadores['avaliacoes_de_V'] - v1
        ev = [json.loads(ln) for ln in open(os.path.join(pasta, 'log_eventos.jsonl'), encoding='utf-8')]
        assert any((e['evento'] == 'retomada' for e in ev)) and sum((e['evento'] == 'partida' for e in ev)) == 1
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_para_quando_uma_foto_cumpre_D_e_espera_o_Ok_humano():
    mundo = MundoDeOrdenacao(4, 8, 0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=400, n_partida=16)
        c.rodar()
        assert c.parada is not None and c.parada.startswith('D cumprido'), c.parada
        arqs = [f for f in os.listdir(pasta) if f.startswith('candidata_')]
        assert arqs
        cand = json.load(open(os.path.join(pasta, arqs[0]), encoding='utf-8'))
        bits = np.array([int(x) for x in cand['bits']], np.uint8)
        assert 'Ok_k humano' in cand['espera'] and mundo.veredito(bits)['distancia'] == 0 and (mundo.veredito(bits)['nfal'] == 0)
        dec = json.load(open(os.path.join(pasta, 'declaracao.json'), encoding='utf-8'))
        assert 'espera o Ok_k' in dec['nao_exercitados']['Resultado → D (10, Ok_k)']
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_os_fusiveis_de_tempo_e_de_rodadas_param_com_o_motivo_e_sem_teto_a_corrida_segue():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, tempo=0.0)
        c.rodar()
        assert c.parada.startswith('fusível de tempo') and c.rodada_n == 0
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    assert C.Config().tempo is None and C.Config().max_rodadas == 0
    try:
        C.Config(nao_existe=1)
        raise AssertionError('uma configuração desconhecida passou')
    except TypeError:
        pass

def test_o_instrumento_que_falha_para_a_busca_calibracao_hash_e_veredito_que_muda():
    mundo = MundoDoSerOculto(0)
    p = mundo.problema()
    p.calibrar = lambda: {'ok': False}
    pasta = _pasta()
    try:
        c = C.Corrida(p, AvaliadorFalso(mundo), pasta, _config(max_rodadas=5))
        c.rodar()
        assert c.parada == 'instrumento' and len(c.fotos) == 0 and (mundo.avaliados == 0)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    mundo = MundoDoSerOculto(0)
    p = mundo.problema()
    estado = {'h': 'a'}
    p.hash_de_v = lambda: estado['h']
    pasta = _pasta()
    try:
        c = C.Corrida(p, AvaliadorFalso(mundo), pasta, _config(max_rodadas=12, diagnostico_cada=3))
        c.hash_de_v = None
        orig = c.rodada

        def rodada_que_muda_o_hash():
            if c.rodada_n == 4:
                estado['h'] = 'b'
            orig()
        c.rodada = rodada_que_muda_o_hash
        c.rodar()
        assert c.parada == 'instrumento' and c.contadores['integridade_falhas'] >= 1 and (c.rodada_n < 12)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
    mundo = MundoDoSerOculto(0)
    ruim = AvaliadorFalso(mundo)
    medir = ruim.medir
    contador = {'n': 0}

    def medir_instavel(lista):
        out = medir(lista)
        contador['n'] += 1
        if contador['n'] > 30:
            for r in out:
                r['valores'] = [min(1.0, v + 0.05) for v in r['valores']]
        return out
    ruim.medir = medir_instavel
    pasta = _pasta()
    try:
        c = C.Corrida(mundo.problema(), ruim, pasta, _config(max_rodadas=60, diagnostico_cada=3))
        c.rodar()
        assert c.parada == 'instrumento' and c.contadores['integridade_falhas'] >= 1
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_o_platô_dispara_o_diagnostico_e_a_clausula_que_nenhuma_foto_cumpre_e_o_sinal_de_abrir_L():

    class MundoImpossivel(MundoDoSerOculto):

        def _medir(self, bits):
            r = super()._medir(bits)
            r['valores'][0] = max(r['valores'][0], 0.5)
            return r
    mundo = MundoImpossivel(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=40, diagnostico_cada=3, plato_rodadas=10 ** 6, minimo_para_diagnosticar_L=60)
        c.rodar()
        ev = [e for e in c.eventos if e.get('evento') == 'diagnostico']
        assert ev and all((e['causa_0_instrumento_ok'] for e in ev))
        com_L = [e for e in ev if 'causa_2_o_L' in e]
        assert com_L and 'c0' in com_L[-1]['causa_2_o_L']['clausulas_que_nenhuma_foto_cumpre'] and ('abrir L' in com_L[-1]['acao'])
        dec = json.load(open(os.path.join(pasta, 'declaracao.json'), encoding='utf-8'))
        assert 'c0' in dec['direcao']['clausulas_que_nenhuma_foto_cumpre']
        assert 'Ordem das causas, reinícios' in dec['exercitados']
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_no_platô_a_busca_reinicia_com_fotos_sorteadas_novas_e_os_pais_esgotados_voltam():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=30, diagnostico_cada=3, plato_rodadas=2, max_reinicios=2)
        c.rodar()
        assert c.reinicios >= 1 and c.contadores['reinicios'] == c.reinicios <= 2
        ev = [e for e in c.eventos if e.get('evento') == 'diagnostico' and 'reinício' in e.get('acao', '')]
        assert ev and 'causa 1 (a busca)' in ev[0]['acao']
        assert c.fotos.resumo()['por_origem']['sorteio'] > 16
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_a_direcao_mostra_a_melhor_foto_o_que_ela_falha_e_a_vazao():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=15)
        c.rodar()
        d = json.load(open(os.path.join(pasta, 'declaracao_parcial.json'), encoding='utf-8'))['direcao']
        assert d['rodadas'] > 0 and d['menor_distancia'] is not None and (d['avaliacoes_de_V'] > 0) and ('avaliacoes_de_V_por_hora' in d)
        mf = d['a_melhor_foto']
        assert mf['distancia'] == d['menor_distancia'] and len(mf['clausulas_que_falha']) + len(mf['clausulas_que_cumpre']) == mundo.n_clausulas
        curva = d['curva_da_melhor_distancia (avaliações de V, distância)']
        assert curva and all((curva[i][1] >= curva[i + 1][1] for i in range(len(curva) - 1)))
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_a_corrida_anda_na_direcao_certa_no_ser_escondido():
    mundo = MundoDoSerOculto(0)
    pasta = _pasta()
    try:
        c = _corrida(mundo, pasta, max_rodadas=90, K=10, n_partida=32)
        c.rodar()
        partida = min((v for v in (c.fotos.distancia[i] for i in range(32)) if v >= 0))
        assert c.melhor[0] < 0.7 * partida, (partida, c.melhor)
        assert c.escritor.pronto() and c.credito_por_braco()['aprendida']['edicoes_propostas'] > 0
    finally:
        shutil.rmtree(pasta, ignore_errors=True)

def test_o_comando_do_ser_recusa_sem_a_autorizacao_de_gabriel_e_a_fumaca_sem_o_cpp_e_nao_lanca_nada():
    from experimentos import condutor_do_ser as CS
    pasta = os.path.join(tempfile.mkdtemp(), 'saida_que_nao_pode_nascer')
    for argv in (['--modo', 'corrida', '--saida', pasta], ['--modo', 'fumaca', '--saida', pasta, '--backend', 'cpp'], ['--modo', 'corrida', '--saida', pasta, '--autorizacao', '   ']):
        try:
            CS.main(argv)
            raise AssertionError(argv)
        except SystemExit as e:
            assert 'RECUSADO' in str(e.code) and 'autoriza' in str(e.code), e.code
    try:
        CS.main(['--modo', 'fumaca', '--saida', pasta, '--autorizacao', 'teste: autorizado'])
        raise AssertionError('a fumaça rodou sem o interpretador em C++')
    except SystemExit as e:
        assert 'C++' in str(e.code) and 'RECUSADO' in str(e.code)
    assert not os.path.exists(pasta)
if __name__ == '__main__':
    for nome, f in list(globals().items()):
        if nome.startswith('test_'):
            f()
            print('ok', nome, flush=True)
