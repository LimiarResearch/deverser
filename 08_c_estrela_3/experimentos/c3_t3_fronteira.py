# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
EXTENSAO = {'cbp': [dict(lr=lr, eta=eta, limiar=0.0001) for lr in (0.01, 0.02) for eta in (0.001, 0.003)], 'sp': [dict(lr=lr, encolhe=0.0001, ruido=ru) for lr in (0.01, 0.02) for ru in (0.0001, 0.0003)]}
CRITERIOS = ('r_deficit_aprende', 'r_deficit_conserva')

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--t3', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--autorizacao', required=True)
    ap.add_argument('--processos', type=int, default=3)
    a = ap.parse_args(argv)
    if not a.autorizacao.strip():
        sys.exit('RECUSADO: sem a frase de autorização')
    from experimentos import c3_t3 as T3
    from experimentos import c3_v_da_busca as VB
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    from experimentos import l_ser_testemunhas as LT
    t3 = json.load(open(a.t3, encoding='utf-8'))
    fab = {'sgd': LT.sgd, 'ewc': LT.ewc, 'cbp': LT.cbp, 'sp': LT.sp}
    conf = {n: dict(c) for n, c in t3['configuracoes'].items()}
    for n, c in conf.items():
        c['bits'] = L.codificar_programa(fab[c['testemunha']](**c['parametros']))
    vistos = {c['bits'].tobytes(): n for n, c in conf.items()}
    novas = []
    for t, lista in EXTENSAO.items():
        for k, p in enumerate(lista):
            b = L.codificar_programa(fab[t](**p))
            if b.tobytes() in vistos:
                continue
            n = f'{t}_borda_{k}'
            conf[n] = {'testemunha': t, 'parametros': p, 'publicada': False, 'bits': b, 'da_borda': True}
            vistos[b.tobytes()] = n
            novas.append(n)
    ic = {c: t3['clausulas'].index(c) for c in CRITERIOS}
    t0 = time.time()
    h_antes = VB.hash_de_V2(())
    assert h_antes == t3['hash_de_V2_sem_piscina'], 'a V mudou desde o T3: a fronteira não se compara com ele'
    out = {'o_que_e': __doc__.split('\nUso')[0], 'autorizacao': a.autorizacao, 't3': a.t3, 'extensao_declarada': EXTENSAO, 'novas': novas, 'configuracoes_novas': {n: {k: v for k, v in conf[n].items() if k != 'bits'} for n in novas}, 'hash_de_V2_sem_piscina': h_antes, 'fase1': {}, 'fase2': {}}
    T3._gravar(a.saida, out)
    av = VB.AvaliacoesV2(trabalhadores=a.processos, piscina=(), backend='cpp')
    try:
        res = av.medir_no_desenvolvimento([conf[n]['bits'] for n in novas], sementes_pert=T3.PERT_DA_GRADE)
        for n, por in zip(novas, res):
            out['fase1'][n] = T3._resumo([(s, p, r) for s, d in por.items() for p, r in d.items()], V)
        T3._gravar(a.saida, out)
        f1 = dict(t3['fase1'], **out['fase1'])
        ok = [n for n in f1 if f1[n].get('media') is not None]
        escolha = {}
        for t in ('cbp', 'sp'):
            escolha[f'{t} pela distância'] = min((n for n in ok if conf[n]['testemunha'] == t), key=lambda n: (f1[n]['media'], f1[n]['pior']))
        for c, i in ic.items():
            escolha[f'melhor em {c}'] = min(ok, key=lambda n: (f1[n]['valores_medios'][i], f1[n]['media']))
        out['escolha_pela_fase1'] = escolha
        faltam = [n for n in dict.fromkeys(escolha.values()) if n not in t3['fase2']]
        out['remedidas_agora'] = faltam
        if faltam:
            res = av.medir_no_desenvolvimento([conf[n]['bits'] for n in faltam], sementes_pert=T3.PERT_DA_MEDIDA)
            for n, por in zip(faltam, res):
                out['fase2'][n] = T3._resumo([(s, p, r) for s, d in por.items() for p, r in d.items()], V)
    finally:
        av.fechar()
    f2 = dict(t3['fase2'], **out['fase2'])
    barras = {}
    for c, i in ic.items():
        n = min(f2, key=lambda k: f2[k]['valores_medios'][i])
        barras[c] = {'configuracao': n, 'testemunha': conf[n]['testemunha'], 'parametros': conf[n]['parametros'], 'valor': f2[n]['valores_medios'][i], 'erro_padrao': f2[n]['valores_erro_padrao'][i], 'distancia_da_configuracao': f2[n]['media']}
    out['barras'] = barras
    out['distancia_a_bater'] = min(({'configuracao': n, 'media': f2[n]['media'], 'erro_padrao': f2[n]['erro_padrao']} for n in f2), key=lambda x: x['media'])
    na_borda = {}
    for t in ('cbp', 'sp'):
        n = escolha[f'{t} pela distância']
        p = conf[n]['parametros']
        na_borda[t] = {'vencedora': n, 'parametros': p, 'ainda_na_borda_estendida': bool(p['lr'] == 0.01 or p.get('eta') == 0.001 or p.get('ruido') == 0.0001)}
    out['borda'] = na_borda
    out['hash_igual'] = VB.hash_de_V2(()) == h_antes
    out['segundos'] = round(time.time() - t0, 1)
    T3._gravar(a.saida, out)
    print(json.dumps({'escolha': escolha, 'barras': barras, 'distancia_a_bater': out['distancia_a_bater'], 'borda': na_borda, 'hash_igual': out['hash_igual']}, ensure_ascii=False), flush=True)
if __name__ == '__main__':
    main()
