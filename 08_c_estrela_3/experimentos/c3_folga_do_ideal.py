# -*- coding: utf-8 -*-
import json
import os
import sys
from multiprocessing import Pool
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

def _uma(semente):
    from experimentos import calibrar_v_ser as CAL
    from experimentos import desafio_v as DV
    from experimentos import desafio_v_ser as V
    ctx = CAL._Ctx(semente=semente)
    ideal = V.julgar(CAL._simular(ctx))
    negs = dict(DV.NEGATIVO)
    negs.update({c: f'{c}:{n}' for c, (n, _) in CAL.NEGATIVOS_NOVOS.items()})
    vers = {}
    for nome, params in DV.CONTROLES.items():
        vers[nome] = V.julgar(CAL._simular(ctx, piso=params))
    for nome, extra in DV.CONTROLES_DE_HISTORICO.items():
        vers[nome] = V.julgar(CAL._simular(ctx, historico=extra, piso=dict(acerto=CAL.ACERTO_DO_MEMORIZADOR) if 'memoriza' in extra else None))
    for cid, (nome, kw) in CAL.NEGATIVOS_NOVOS.items():
        vers[f'{cid}:{nome}'] = V.julgar(CAL._simular(ctx, **kw))
    out = {}
    for i, (cid, medida, op, lim, esc) in enumerate(V.CLAUSULAS):
        v = float(ideal['valores'][i])
        folga = lim - v if op == '<=' else v - lim if op == '>=' else None
        reg = {'medida': medida, 'op': op, 'limite': lim, 'ideal': round(v, 5), 'folga_do_ideal': None if folga is None else round(folga, 5)}
        if cid in negs and negs[cid] in vers:
            vn = float(vers[negs[cid]]['valores'][i])
            reg['negativo'] = negs[cid]
            reg['valor_do_negativo'] = round(vn, 5)
            reg['passa_do_limite'] = round(vn - lim if op == '<=' else lim - vn, 5)
        out[cid] = reg
    return (int(semente), out)

def main():
    from experimentos import c3_v_da_busca as VB
    saida = sys.argv[1]
    proc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    sementes = [1] + list(VB.PISCINA_PADRAO) + list(VB.DESENVOLVIMENTO)
    with Pool(proc) as p:
        res = dict(p.map(_uma, sementes))
    resumo = {}
    for cid in res[1]:
        fol = [res[s][cid]['folga_do_ideal'] for s in sementes if res[s][cid]['folga_do_ideal'] is not None]
        neg = [res[s][cid].get('passa_do_limite') for s in sementes if res[s][cid].get('passa_do_limite') is not None]
        resumo[cid] = {'limite': res[1][cid]['limite'], 'op': res[1][cid]['op'], 'folga_minima_do_ideal': min(fol) if fol else None, 'sementes_em_que_o_ideal_reprova': [s for s in sementes if (res[s][cid]['folga_do_ideal'] or 0) < 0], 'negativo_passa_do_limite_no_minimo': min(neg) if neg else None, 'sementes_em_que_o_negativo_nao_reprova': [s for s in sementes if res[s][cid].get('passa_do_limite') is not None and res[s][cid]['passa_do_limite'] <= 0]}
    json.dump({'por_semente': {str(k): v for k, v in res.items()}, 'resumo': resumo}, open(saida, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for cid, r in resumo.items():
        print(f"{cid:28s} {r['op']} {r['limite']:<8} folga mínima do ideal {r['folga_minima_do_ideal']}  ideal reprova em {len(r['sementes_em_que_o_ideal_reprova'])}  negativo passa do limite no mínimo {r['negativo_passa_do_limite_no_minimo']}  negativo não reprova em {len(r['sementes_em_que_o_negativo_nao_reprova'])}")
if __name__ == '__main__':
    main()
