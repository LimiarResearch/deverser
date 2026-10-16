# -*- coding: utf-8 -*-
import os
import time
import numpy as np

def _controles_de_uma_semente(pacote):
    semente, eps, backend = pacote
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    if os.name == 'nt':
        import shutil
        if shutil.which('g++'):
            os.add_dll_directory(os.path.dirname(shutil.which('g++')))
    t0 = time.time()
    from experimentos import calibrar_v_ser as CAL
    from experimentos import desafio_oraculo as OR
    from experimentos import desafio_v as DV
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_interp as LI
    from experimentos import l_ser_testemunhas as LT
    DV.definir_backend(backend)
    ctx = CAL._Ctx(semente=semente)
    out = {'semente': int(semente), 'controles': {}, 'clausulas': {}, 'degenerados': {}, 'ok': True}
    ver = {}
    for nome, params in DV.CONTROLES.items():
        ver[nome] = CAL._veredito(ctx, piso=params)
    for nome, extra in DV.CONTROLES_DE_HISTORICO.items():
        ver[nome] = CAL._veredito(ctx, historico=extra, piso=dict(acerto=CAL.ACERTO_DO_MEMORIZADOR) if 'memoriza' in extra else None)
    for cid, (nome, kw) in CAL.NEGATIVOS_NOVOS.items():
        ver[f'{cid}:{nome}'] = CAL._veredito(ctx, **kw)
    for nome, v in ver.items():
        out['controles'][nome] = {'nfal': int(v['nfal']), 'reprovadas': CAL._reprovadas(v)}
    ideal = ver['ideal']
    out['controles']['ideal']['cumpre_as_28'] = bool(ideal['nfal'] == 0)
    if ideal['nfal'] != 0:
        out['ok'] = False
    for cid, neg in list(DV.NEGATIVO.items()) + [(c, f'{c}:{n}') for c, (n, _) in CAL.NEGATIVOS_NOVOS.items()]:
        i = V.IDS.index(cid)
        pos_ok, neg_ok = (ideal['violacoes'][i] <= 1e-09, ver[neg]['violacoes'][i] > 1e-09)
        out['clausulas'][cid] = {'positivo_cumpre': bool(pos_ok), 'negativo': neg, 'negativo_reprova': bool(neg_ok)}
        if not (pos_ok and neg_ok):
            out['ok'] = False
    for nome in ('nulo', 'majoritaria'):
        out['degenerados'][nome] = {'cumpre_D': bool(ver[nome]['nfal'] == 0)}
        if ver[nome]['nfal'] == 0:
            out['ok'] = False
    pior = []
    for s in range(1, 6):
        saidas = {n: OR.simular_do_oraculo(ctx.fam[n], ctx.orac[n], fator=1.0, esquece=0.0, semente=s) for n in ('seq', 'ling')}
        p = np.zeros(4)
        for nome in ('seq', 'ling'):
            for k, f in enumerate(ctx.fam[nome]['fluxos']):
                A = OR.acerto_por_sonda(f, saidas[nome]['respostas'][k])
                d = OR.deficit(A, ctx.orac[nome][k], ctx.orac[nome][k]['G'])[:4]
                p = np.maximum(p, [x if np.isfinite(x) else 0.0 for x in d])
        pior.append(p)
    n3 = len(V.IDS_DEFICIT)
    eta = np.asarray([V.ETA[c] for c in V.IDS_DEFICIT])
    ruido = np.asarray(pior).max(0)[:n3]
    out['deficit'] = {'ruido_do_positivo (pior de 5 sorteios)': np.round(ruido, 4).tolist(), 'eta': eta.tolist(), 'dentro_dos_eta': bool((ruido <= eta + 1e-12).all())}
    if not out['deficit']['dentro_dos_eta']:
        out['ok'] = False
    av = V.AvaliadorReal.__new__(V.AvaliadorReal)
    av.semente, av.tempo_max, av.familias, av.orac, av.sondas_mem = (ctx.semente, V.TEMPO_MAX_PADRAO, ctx.fam, ctx.orac, ctx.sondas_mem)
    LI.definir_perturbacao(eps, int(semente) + 1)
    try:
        v = V.julgar(av.medir(LT.testemunhas_em_bits()['sgd']))
    finally:
        LI.definir_perturbacao(0.0, 0)
    out['degenerados']['sgd_perturbado'] = {'cumpre_D': bool(v['nfal'] == 0), 'clausulas_que_cumpre': int(V.N_CLAUSULAS - v['nfal']), 'estado': v['estado'], 'distancia': int(v['distancia'])}
    if v['nfal'] == 0 or v['estado'] != 'ok':
        out['ok'] = False
    out['segundos'] = round(time.time() - t0, 1)
    return out

def calibrar_v2(piscina=None, desenvolvimento=None, eps=None, processos=4, backend='cpp', relato=None, base=True):
    from experimentos import c3_v_da_busca as VB
    from experimentos import desafio_v_ser as V
    piscina = VB.PISCINA_PADRAO if piscina is None else tuple((int(s) for s in piscina))
    desenvolvimento = VB.DESENVOLVIMENTO if desenvolvimento is None else tuple((int(s) for s in desenvolvimento))
    eps = VB.EPS if eps is None else float(eps)
    t0 = time.time()

    def dizer(txt):
        if relato:
            relato(f'[cal v2 {round(time.time() - t0)} s] {txt}')
    out = {'eps': eps, 'piscina': list(piscina), 'desenvolvimento': list(desenvolvimento), 'ok': True, 'declarado': 'os η do déficit e as tolerâncias R vêm da semente 1 (os oito recomeços só existem nela); nas outras sementes, o ruído do positivo no déficit é conferido contra os η'}
    if base:
        out['base_semente_1'] = V.calibrar()
        out['ok'] = bool(out['base_semente_1'].get('ok'))
        dizer(f"a base (semente 1): ok = {out['ok']}")
    sementes = list(dict.fromkeys(list(piscina) + list(desenvolvimento)))
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(max(1, int(processos))) as pool:
        por = {}
        for r in pool.imap_unordered(_controles_de_uma_semente, [(s, eps, backend) for s in sementes]):
            por[r['semente']] = r
            dizer(f"semente {r['semente']}: ok = {r['ok']} ({r['segundos']} s)")
    out['conjuntos'] = {str(s): por[s] for s in sementes}
    out['falharam'] = [s for s in sementes if not por[s]['ok']]
    if out['falharam']:
        out['ok'] = False
    out['segundos'] = round(time.time() - t0, 1)
    return out
