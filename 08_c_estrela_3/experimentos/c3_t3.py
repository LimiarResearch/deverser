# -*- coding: utf-8 -*-
import argparse
import importlib.util
import json
import os
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
PERT_DA_GRADE = (1,)
PERT_DA_MEDIDA = (2, 3, 4, 5, 6)

def _grade():
    spec = importlib.util.spec_from_file_location('t3_antigo', os.path.join(RAIZ, 'corridas_vps', 't3_e_passo1.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return (m.GRADE, m.PUBLICADAS)

def _gravar(caminho, out):
    tmp = caminho + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)

def _resumo(medidas, V):
    vs = [V.julgar(r) for _s, _p, r in medidas]
    if any((v['estado'] != 'ok' for v in vs)):
        return {'media': None, 'estados': [v['estado'] for v in vs]}
    d = np.asarray([v['distancia'] for v in vs], np.float64)
    val = np.asarray([v['valores'] for v in vs], np.float64)
    return {'media': round(float(d.mean()), 1), 'erro_padrao': round(float(d.std(ddof=1) / np.sqrt(len(d))), 1) if len(d) > 1 else None, 'pior': int(d.max()), 'n': len(d), 'distancias': [int(x) for x in d], 'valores_medios': [round(float(x), 5) for x in val.mean(0)], 'valores_erro_padrao': [round(float(x), 5) for x in (val.std(0, ddof=1) / np.sqrt(len(d)) if len(d) > 1 else np.zeros(val.shape[1]))]}

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--autorizacao', required=True)
    ap.add_argument('--processos', type=int, default=3)
    ap.add_argument('--fumaca', action='store_true', help='só a publicada de cada testemunha, uma semente de perturbação em cada fase: o teste do roteiro (o resultado NÃO conta)')
    a = ap.parse_args(argv)
    if not a.autorizacao.strip():
        sys.exit('RECUSADO: sem a frase de autorização')
    from experimentos import c3_v_da_busca as VB
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    from experimentos import l_ser_testemunhas as LT
    GRADE, PUBLICADAS = _grade()
    fab = {'sgd': LT.sgd, 'ewc': LT.ewc, 'cbp': LT.cbp, 'sp': LT.sp}
    conf = {}
    for t, grade in GRADE.items():
        assert PUBLICADAS[t] in grade, t
        for k, p in enumerate(grade):
            conf[f'{t}_{k:02d}'] = {'testemunha': t, 'parametros': p, 'publicada': p == PUBLICADAS[t], 'bits': L.codificar_programa(fab[t](**p))}
    nomes = [n for n in conf if conf[n]['publicada']] if a.fumaca else list(conf)
    pert_medida = PERT_DA_MEDIDA[:1] if a.fumaca else PERT_DA_MEDIDA
    t0 = time.time()
    h_antes = VB.hash_de_V2(())
    out = {'o_que_e': __doc__.split('\nUso')[0], 'autorizacao': a.autorizacao, 'fumaca': bool(a.fumaca), 'desenvolvimento': list(VB.DESENVOLVIMENTO), 'eps': VB.EPS, 'pert_da_grade': list(PERT_DA_GRADE), 'pert_da_medida': list(pert_medida), 'grade': GRADE, 'publicadas': PUBLICADAS, 'clausulas': [c[0] for c in V.CLAUSULAS], 'hash_de_V2_sem_piscina': h_antes, 'configuracoes': {n: {k: v for k, v in c.items() if k != 'bits'} for n, c in conf.items()}, 'fase1': {}, 'fase2': {}}
    _gravar(a.saida, out)
    av = VB.AvaliacoesV2(trabalhadores=a.processos, piscina=(), backend='cpp')
    try:
        res = av.medir_no_desenvolvimento([conf[n]['bits'] for n in nomes], sementes_pert=PERT_DA_GRADE)
        for n, por in zip(nomes, res):
            out['fase1'][n] = _resumo([(s, p, r) for s, d in por.items() for p, r in d.items()], V)
        _gravar(a.saida, out)
        escolha = {}
        for t in GRADE:
            ok = [n for n in nomes if conf[n]['testemunha'] == t and out['fase1'][n]['media'] is not None]
            if ok:
                escolha[t] = min(ok, key=lambda n: (out['fase1'][n]['media'], out['fase1'][n]['pior']))
        out['escolha_da_grade'] = escolha
        finais = list(dict.fromkeys(list(escolha.values()) + [n for n in nomes if conf[n]['publicada']]))
        res = av.medir_no_desenvolvimento([conf[n]['bits'] for n in finais], sementes_pert=pert_medida)
        for n, por in zip(finais, res):
            out['fase2'][n] = _resumo([(s, p, r) for s, d in por.items() for p, r in d.items()], V)
    finally:
        av.fechar()
    out['hash_de_V2_sem_piscina_depois'] = VB.hash_de_V2(())
    out['hash_igual'] = out['hash_de_V2_sem_piscina_depois'] == h_antes
    out['segundos'] = round(time.time() - t0, 1)
    _gravar(a.saida, out)
    print(json.dumps({'escolha': out['escolha_da_grade'], 'fase2': {n: {k: v for k, v in r.items() if k in ('media', 'erro_padrao', 'pior')} for n, r in out['fase2'].items()}, 'hash_igual': out['hash_igual'], 'segundos': out['segundos']}, ensure_ascii=False), flush=True)
if __name__ == '__main__':
    main()
