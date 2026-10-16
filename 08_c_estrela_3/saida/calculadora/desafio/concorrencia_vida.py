# -*- coding: utf-8 -*-
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
try:
    import gerar
except ImportError:
    sys.path.insert(0, os.path.join(AQUI, '..', '..', '..', 'compilador'))
    import gerar
import carga_vida
import metricas_vida
import oraculo_vida
SEMENTES = (1, 2)
FONTE = {n: open(os.path.join(AQUI, n + '.py'), encoding='utf-8').read() for n in ('comum_vida', 'nucleo_vida', 'ref_sgd')}
D = [('c1_sem_aviso', 'usa_informacao_retida', 'le', 0, 1), ('c2_memoria_fixa', 'bytes_de_estado', 'le', 65536, 65536), ('c3_conserva', 'esquecimento', 'le', 0.1, 1), ('c4_aprende_no_fim', 'plasticidade', 'ge', 0.9, 1), ('c5_corrige', 'correcao', 'ge', 0.9, 1), ('c5_regra_antiga_nao_volta', 'regra_antiga', 'le', 0.1, 1), ('c6_combina', 'ganho_de_composicao', 'ge', 0.01, 1), ('c7_sabe_o_que_sabe', 'calibracao', 'ge', 0.01, 1), ('c7_conflito_depois_da_refutacao', 'conflito_depois_de_refutacao', 'ge', 0.5, 1), ('c8_restaura', 'restauracao_fiel', 'ge', 1.0, 1), ('c9_transformacao_ativa', 'transformacao_ativa', 'ge', 1.0, 1)]
DECISOES_DA_IA = 'limites de D (0,10; 0,90; 0,01; 0,5; 1,0), sementes de desenvolvimento 1 e 2, faixas dos genes e o teto de tempo: postos pela IA pelo criador'
GENES = [{'nome': 'tamanho', 'tipo': 'categoria', 'valores': ['16x8', '24x10', '32x8', '32x12', '48x8', '64x6']}, {'nome': 'w', 'tipo': 'inteiro', 'min': 15, 'max': 60, 'passo': 5}, {'nome': 'limiar', 'tipo': 'real', 'min': 3.0, 'max': 20.0}, {'nome': 'detector', 'tipo': 'categoria', 'valores': ['janela', 'cusum']}, {'nome': 'marco', 'tipo': 'categoria', 'valores': [0, 1]}, {'nome': 'fusao', 'tipo': 'categoria', 'valores': [0, 1]}, {'nome': 'desempate', 'tipo': 'categoria', 'valores': ['verossimilhanca', 'recente']}, {'nome': 'refutacao', 'tipo': 'categoria', 'valores': ['corrigir', 'nova']}, {'nome': 'combinador', 'tipo': 'categoria', 'valores': [0, 1]}, {'nome': 'auditoria', 'tipo': 'categoria', 'valores': [0, 1]}, {'nome': 'epistemico', 'tipo': 'categoria', 'valores': [0, 1]}, {'nome': 'lr', 'tipo': 'real', 'min': 0.01, 'max': 0.15}, {'nome': 'conflito_dur', 'tipo': 'inteiro', 'min': 5, 'max': 80, 'passo': 5}, {'nome': 'limiar_investigar', 'tipo': 'real', 'min': 1.0, 'max': 6.0}, {'nome': 'limiar_validado', 'tipo': 'real', 'min': 0.5, 'max': 3.0}, {'nome': 'comb_limiar', 'tipo': 'real', 'min': 0.3, 'max': 0.9}, {'nome': 'tol_reconhecer', 'tipo': 'real', 'min': 0.05, 'max': 0.3}, {'nome': 'salto_rotulo', 'tipo': 'real', 'min': 0.1, 'max': 0.4}, {'nome': 'taxa_estatistica', 'tipo': 'real', 'min': 0.002, 'max': 0.05}, {'nome': 'taxa_erro', 'tipo': 'real', 'min': 0.001, 'max': 0.02}, {'nome': 'cusum_k', 'tipo': 'real', 'min': 1.0, 'max': 2.0}, {'nome': 'maturidade', 'tipo': 'real', 'min': 1.0, 'max': 6.0}, {'nome': 'erro_validado', 'tipo': 'real', 'min': 0.15, 'max': 0.5}, {'nome': 'passo_comb', 'tipo': 'real', 'min': 0.1, 'max': 1.0}, {'nome': 'reforco_correcao', 'tipo': 'real', 'min': 1.0, 'max': 5.0}, {'nome': 'taxa_de_mutacao', 'tipo': 'real', 'min': 0.05, 'max': 0.6}]
DO_MOTOR = {'taxa_de_mutacao'}
_CARGAS = None

def _cargas():
    global _CARGAS
    if _CARGAS is None:
        _CARGAS = [carga_vida.gerar_carga(s) for s in SEMENTES]
    return _CARGAS

def viver(tarefa):
    nome, genes = tarefa
    genes = {k: v for k, v in genes.items() if not k.startswith('_') and k not in DO_MOTOR}
    t0 = time.process_time()
    try:
        ns = {'np': np, '__name__': 'concorrente'}
        exec(FONTE['comum_vida'], ns)
        exec(FONTE[nome], ns)
        ms, bits = ([], [])
        for e in _cargas():
            s = ns['executar'](e, **genes)
            ok, porque = oraculo_vida.conferir(e, s)
            if not ok:
                return {'erro': porque, 'cpu_s': time.process_time() - t0}
            ms.append(metricas_vida.metricas(e, s))
            bits += [np.asarray(r, np.int8).ravel() for fl in s['respostas'] for r in fl]
            bits += [np.asarray(x, np.int8).ravel() for fl in s['etiquetas'] for x in fl]
    except Exception as ex:
        return {'erro': f'{type(ex).__name__}: {ex}', 'cpu_s': time.process_time() - t0}
    foto = np.concatenate(bits)
    pior, media = ({}, {})
    for _, med, sentido, _, _ in D + [(0, 'acc_final', 'ge', 0, 0), (0, 'investigar_nas_nao_vistas', 'ge', 0, 0)]:
        vals = [v for m in ms for v in (m[med + '_intervalo'] if med + '_intervalo' in m else [m[med]])]
        pior[med] = max(vals) if sentido == 'le' else min(vals)
        media[med] = float(np.mean([m[med] for m in ms]))
    return {'pior': pior, 'media': media, 'foto': foto.tobytes(), 'cpu_s': time.process_time() - t0}

def violacao(pior):
    v, por = (0.0, {})
    for cid, med, sentido, lim, escala in D:
        falta = max(0.0, pior[med] - lim if sentido == 'le' else lim - pior[med]) / escala
        por[cid] = round(falta, 4)
        v += falta
    return (v, por)

def main():
    proc = int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()
    pop = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    teto = float(sys.argv[3]) if len(sys.argv) > 3 else 7200
    saida = sys.argv[4] if len(sys.argv) > 4 else os.path.join(AQUI, 'corrida')
    os.makedirs(saida, exist_ok=True)
    ledger = open(os.path.join(saida, 'ledger.jsonl'), 'a', encoding='utf-8', newline='\n')
    arquivo, t_ini = ([], time.time())
    dist = [g for s_ in SEMENTES for f in carga_vida.gerar_carga(s_)['fluxos'] for g in f['_avaliacao'].abrir()['distinguibilidade']]
    pior_sep = min((g['separacao_por_contexto'] for g in dist))
    print('distinguibilidade: separação pelo contexto no pior grupo', round(pior_sep, 3), '; teto sem contexto de', round(min((g['teto_sem_contexto'] for g in dist)), 2), 'a', round(max((g['teto_sem_contexto'] for g in dist)), 2), flush=True)
    if pior_sep < 0.95:
        json.dump({'estado': 'impossível no meio', 'prova': 'as tarefas que dividem o conteúdo não se separam pela informação da entrada', 'distinguibilidade': dist}, open(os.path.join(saida, 'resultado.json'), 'w', encoding='utf-8', newline=chr(10)), ensure_ascii=False, indent=1)
        print('parado antes da busca: impossível no meio', flush=True)
        return
    with Pool(proc) as pool:
        refs = {'nucleo_a_mao': ('nucleo_vida', {}), 'controle': ('nucleo_vida', {'epistemico': 0, 'auditoria': 0, 'combinador': 0, 'refutacao': 'nova'}), 'sgd': ('ref_sgd', {})}
        rr = pool.map(viver, list(refs.values()))
        referencias = {}
        for (k, _), r in zip(refs.items(), rr):
            if 'erro' in r:
                referencias[k] = {'erro': r['erro']}
                continue
            v, por = violacao(r['pior'])
            referencias[k] = {'violacao': round(v, 4), 'por_clausula': por, 'pior': r['pior'], 'media': r['media'], 'cpu_s': round(r['cpu_s'], 1), 'foto_sha256': hashlib.sha256(r['foto']).hexdigest()}
            arquivo.append(np.frombuffer(r['foto'], np.int8))
        foto_controle = arquivo[1] if len(arquivo) > 1 else None
        json.dump(referencias, open(os.path.join(saida, 'referencias.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
        print('referências:', json.dumps({k: v.get('violacao', v.get('erro')) for k, v in referencias.items()}, ensure_ascii=False), flush=True)

        def avaliar_lote(cs):
            rs = pool.map(viver, [('nucleo_vida', c) for c in cs])
            out = []
            for c, r in zip(cs, rs):
                if 'erro' in r:
                    out.append(([1000000000.0] * 5, 1000000000.0))
                    ledger.write(json.dumps({'id': c['_id'], 'erro': r['erro']}, ensure_ascii=False) + '\n')
                    continue
                f = np.frombuffer(r['foto'], np.int8)
                ds = sorted((float(np.mean(f != a)) for a in arquivo)) if arquivo else [0.0]
                nov = float(np.mean(ds[:5]))
                arquivo.append(f)
                v, por = violacao(r['pior'])
                obj = [r['media']['esquecimento'], -r['media']['acc_final'], -r['media']['ganho_de_composicao'], r['cpu_s'], -nov]
                out.append((obj, v))
                ledger.write(json.dumps({'id': c['_id'], 'genes': {k: v2 for k, v2 in c.items() if not k.startswith('_')}, 'violacao': round(v, 4), 'por_clausula': por, 'pior': r['pior'], 'media': r['media'], 'cpu_s': round(r['cpu_s'], 1), 'novidade': round(nov, 4), 'foto_sha256': hashlib.sha256(r['foto']).hexdigest(), 'diferenca_do_controle': None if foto_controle is None else round(float(np.mean(f != foto_controle)), 4), 't_s': round(time.time() - t_ini, 1)}, ensure_ascii=False) + '\n')
            ledger.flush()
            melhor = min((o[1] for o in out), default=None)
            print(f'{time.time() - t_ini:7.0f}s  lote {len(cs)}  melhor violação do lote {melhor:.4f}  fotos {len(arquivo)}', flush=True)
            return out
        rep = {'arquetipos': [{'nome': 'nucleo', 'variaveis': GENES}]}
        pop_final, n = gerar.nsga2(rep, avaliar_lote, None, None, orcamento=100000, semente=1, populacao=pop, parar_sem_melhora=3, teto_s=teto)
    parada = dict(gerar.nsga2.ultima_parada)
    viaveis = sorted(pop_final, key=lambda c: (c['_avaliacao'][1], c['_avaliacao'][0][1]))
    res = {'parada': parada, 'avaliados': n, 'processos': proc, 'populacao': pop, 'D': D, 'decisoes_da_ia': DECISOES_DA_IA, 'melhor': {'id': viaveis[0]['_id'], 'violacao': viaveis[0]['_avaliacao'][1], 'objetivos': viaveis[0]['_avaliacao'][0], 'genes': {k: v for k, v in viaveis[0].items() if not k.startswith('_')}}, 'cumprem_o_D': sum((1 for c in pop_final if c['_avaliacao'][1] == 0)), 'referencias': referencias, 'segundos': round(time.time() - t_ini, 1), 'distinguibilidade': dist}
    res['estado'] = 'solução: o melhor encontrado e verificado, com L amostrada e parada por ' + parada['motivo'] if res['cumprem_o_D'] else 'não encontrado no orçamento; primeira causa a perguntar: L estreita (L de composição zero, a família das gavetas)'
    json.dump(res, open(os.path.join(saida, 'resultado.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    print('fim:', json.dumps({k: res[k] for k in ('parada', 'avaliados', 'cumprem_o_D')}, ensure_ascii=False), flush=True)
    print('melhor:', json.dumps(res['melhor'], ensure_ascii=False), flush=True)
if __name__ == '__main__':
    main()
