# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import time
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
PASSO_SGD = [dict(lr=0.005, lote=1), dict(lr=0.005, lote=4)]
CRITERIOS = ('r_deficit_aprende', 'r_deficit_conserva')

def pareto(pontos):
    out = []
    for n, (a, b) in pontos.items():
        if not any(((a2 <= a and b2 <= b) and (a2 < a or b2 < b) for m, (a2, b2) in pontos.items() if m != n)):
            out.append(n)
    return sorted(out, key=lambda n: pontos[n])

def domina(foto, fronteira):
    falham = []
    for p in fronteira:
        if not all((foto[c][0] + foto[c][1] < p['valores'][c][0] - p['valores'][c][1] for c in CRITERIOS)):
            falham.append(p)
    return (not falham, falham)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--t3', required=True)
    ap.add_argument('--borda', required=True)
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
    bo = json.load(open(a.borda, encoding='utf-8'))
    conf = {n: dict(c) for n, c in t3['configuracoes'].items()}
    conf.update({n: dict(c) for n, c in bo['configuracoes_novas'].items()})
    novas = []
    for k, p in enumerate(PASSO_SGD):
        n = f'sgd_passo_{k}'
        conf[n] = {'testemunha': 'sgd', 'parametros': p, 'publicada': False, 'do_passo': True}
        novas.append(n)
    bits = {n: L.codificar_programa({'sgd': LT.sgd, 'ewc': LT.ewc, 'cbp': LT.cbp, 'sp': LT.sp}[c['testemunha']](**c['parametros'])) for n, c in conf.items()}
    ic = {c: t3['clausulas'].index(c) for c in CRITERIOS}
    t0 = time.time()
    h = VB.hash_de_V2(())
    assert h == t3['hash_de_V2_sem_piscina'] == bo['hash_de_V2_sem_piscina'], 'a V mudou desde o T3'
    out = {'o_que_e': __doc__.split('\nUso')[0], 'autorizacao': a.autorizacao, 'passo_declarado': PASSO_SGD, 'criterios': list(CRITERIOS), 'hash_de_V2_sem_piscina': h, 'fase1': {}, 'fase2': {}}
    T3._gravar(a.saida, out)
    av = VB.AvaliacoesV2(trabalhadores=a.processos, piscina=(), backend='cpp')
    try:
        res = av.medir_no_desenvolvimento([bits[n] for n in novas], sementes_pert=T3.PERT_DA_GRADE)
        for n, por in zip(novas, res):
            out['fase1'][n] = T3._resumo([(s, p, r) for s, d in por.items() for p, r in d.items()], V)
        T3._gravar(a.saida, out)
        f1 = dict(t3['fase1'], **bo['fase1'], **out['fase1'])
        p1 = {n: tuple((f1[n]['valores_medios'][ic[c]] for c in CRITERIOS)) for n in f1 if f1[n].get('media') is not None}
        out['pareto_da_fase1'] = pareto(p1)
        f2 = dict(t3['fase2'], **bo['fase2'])
        faltam = [n for n in out['pareto_da_fase1'] if n not in f2]
        out['remedidas_agora'] = faltam
        if faltam:
            res = av.medir_no_desenvolvimento([bits[n] for n in faltam], sementes_pert=T3.PERT_DA_MEDIDA)
            for n, por in zip(faltam, res):
                out['fase2'][n] = T3._resumo([(s, p, r) for s, d in por.items() for p, r in d.items()], V)
    finally:
        av.fechar()
    f2 = dict(t3['fase2'], **bo['fase2'], **out['fase2'])
    p2 = {n: tuple((f2[n]['valores_medios'][ic[c]] for c in CRITERIOS)) for n in f2}
    front = pareto(p2)
    out['fronteira'] = [{'configuracao': n, 'testemunha': conf[n]['testemunha'], 'parametros': conf[n]['parametros'], 'distancia': f2[n]['media'], 'valores': {c: (f2[n]['valores_medios'][ic[c]], f2[n]['valores_erro_padrao'][ic[c]]) for c in CRITERIOS}} for n in front]
    out['todas_remedidas'] = {n: {c: (f2[n]['valores_medios'][ic[c]], f2[n]['valores_erro_padrao'][ic[c]]) for c in CRITERIOS} for n in f2}
    out['hash_igual'] = VB.hash_de_V2(()) == h
    out['segundos'] = round(time.time() - t0, 1)
    T3._gravar(a.saida, out)
    print(json.dumps({'pareto_da_fase1': out['pareto_da_fase1'], 'remedidas_agora': out['remedidas_agora'], 'fronteira': out['fronteira'], 'hash_igual': out['hash_igual']}, ensure_ascii=False), flush=True)
if __name__ == '__main__':
    main()
