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
FOTOS_NASCE_SABENDO = ('9326', '7582', '12039', '13109')
FOTO_DO_DADO = '12039'
FOTO_DO_ARREDONDAMENTO = '9326'
FOTO_QUE_FINGE = '1302'
PERT = (1, 2, 3, 4, 5)
K = 3
CLAUSULAS_DE_APRENDER = ('r_deficit_aprende', 'r_aprende')

def _gravar(caminho, out):
    tmp = caminho + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, caminho)

def _fotos(caminho):
    d = json.load(open(caminho, encoding='utf-8'))
    out = {}
    for k, v in d.items():
        num = k.split()[1]
        busca = int(k.split('busca ')[1].rstrip(')'))
        out[num] = {'bits': np.asarray([int(x) for x in v], np.uint8), 'busca_antiga': busca}
    return out

def variantes_neutras(bits, n, g, tentativas=None):
    from experimentos import c3_sonda_do_ser as S
    from experimentos import l_ser_lang as L
    cod = L.CODIFICACAO
    sig0 = S.assinatura(bits)
    ch0 = cod.chave(cod.canonizar(bits))
    out, vistas, tentadas = ([], {ch0}, 0)
    for p in g.permutation(len(bits))[:tentativas or len(bits)]:
        b = bits.copy()
        b[p] ^= 1
        tentadas += 1
        ch = cod.chave(cod.canonizar(b))
        if ch in vistas:
            continue
        vistas.add(ch)
        if S.assinatura(b) == sig0:
            out.append((int(p), b))
            if len(out) >= n:
                break
    return (out, tentadas)

def _media_ep(ds):
    d = np.asarray(ds, np.float64)
    return (float(d.mean()), float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fotos', required=True)
    ap.add_argument('--fotos-finge', dest='fotos_finge', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--autorizacao', required=True)
    ap.add_argument('--processos', type=int, default=4)
    ap.add_argument('--variantes', type=int, default=16)
    a = ap.parse_args(argv)
    if not a.autorizacao.strip():
        sys.exit('RECUSADO: sem a frase de autorização')
    if os.name == 'nt':
        import shutil
        if shutil.which('g++'):
            os.add_dll_directory(os.path.dirname(shutil.which('g++')))
    from experimentos import c3_v_da_busca as VB
    from experimentos import desafio_v_ser as V
    from experimentos import l_ser_lang as L
    from experimentos import l_ser_testemunhas as LT
    fotos = _fotos(a.fotos)
    fotos.update(_fotos(a.fotos_finge))
    test = LT.testemunhas_em_bits()
    t0 = time.time()
    out = {'o_que_e': __doc__.split('\nUso')[0], 'autorizacao': a.autorizacao, 'eps': VB.EPS, 'k': K, 'hash_de_V2': VB.hash_de_V2(), 'falsas': {}}
    _gravar(a.saida, out)
    VB.conferir_piscina(VB.PISCINA_PADRAO)
    av = VB.AvaliacoesV2(trabalhadores=a.processos, backend='cpp', desenvolvimento=(V.SEMENTE_DA_VIDA,) + VB.DESENVOLVIMENTO, conferir=False)
    av0 = VB.AvaliacoesV2(trabalhadores=1, backend='cpp', piscina=(), desenvolvimento=(V.SEMENTE_DA_VIDA,), eps=0.0, conferir=False)
    ia = {c: V.IDS.index(c) for c in CLAUSULAS_DE_APRENDER}
    try:
        g = np.random.default_rng(20261004)
        orig = fotos[FOTO_DO_DADO]['bits']
        vs, tentadas = variantes_neutras(orig, a.variantes, g)
        res = av.medir([orig] + [b for _p, b in vs], sal=0, nivel=K)
        jul = [V.julgar(r) for r in res]
        md0 = res[0]['medidas_do_nivel']
        ds0 = [m['distancia'] for m in md0]
        margem = _media_ep(ds0)[1]
        d0 = jul[0]['distancia']
        dv = [j['distancia'] for j in jul[1:]]
        mesmas = all(([(m['semente'], m['semente_pert']) for m in r['medidas_do_nivel']] == [(m['semente'], m['semente_pert']) for m in md0] for r in res[1:]))
        ganho = d0 - min(dv) if dv else 0
        out['falsas']['rola_o_dado'] = {'foto': FOTO_DO_DADO, 'tentadas': tentadas, 'variantes_neutras': len(vs), 'bits_trocados': [p for p, _b in vs], 'original_pior_de_k': d0, 'medidas_da_original': ds0, 'margem_do_recorde': round(margem, 1), 'variantes_pior_de_k': dv, 'iguais_a_original': int(sum((1 for d in dv if d == d0))), 'mesmos_conjuntos_e_sementes': bool(mesmas), 'ganho_da_melhor_variante': int(ganho), 'passa': bool(len(vs) > 0 and mesmas and (ganho <= margem))}
        _gravar(a.saida, out)
        pol = LT._politica_por_confianca()
        sgd0 = L.codificar_programa(L.programa(tecido=LT._tecido(64, 4), W_SAIDA=L.E('mul', 'P', 'zero'), W_OCULTA=L.E('mul', 'P', 'zero'), RETRO=L.E('mul', 'T', L.E('thr', 's')), rotulos=pol.pop('rotulos'), **pol))
        fingem = {'sgd com taxa zero': sgd0, f'foto {FOTO_QUE_FINGE}': fotos[FOTO_QUE_FINGE]['bits']}
        res = av.medir_no_desenvolvimento(list(fingem.values()), sementes_pert=(1,))
        tab = {}
        for nome, r in zip(fingem, res):
            por = {f'{s}/{p}': V.julgar(x) for s, d in r.items() if s != V.SEMENTE_DA_VIDA for p, x in d.items()}
            tab[nome] = {'valores': {k: {c: round(float(v['valores'][i]), 5) for c, i in ia.items()} for k, v in por.items()}, 'reprova': {k: {c: bool(v['violacoes'][i] > 1e-09) for c, i in ia.items()} for k, v in por.items()}, 'distancias': {k: int(v['distancia']) for k, v in por.items()}, 'estados': {k: v['estado'] for k, v in por.items()}}
            tab[nome]['passa'] = bool(all((all(x.values()) for x in tab[nome]['reprova'].values())) and all((e == 'ok' for e in tab[nome]['estados'].values())))
        out['falsas']['finge'] = {'programas': tab, 'clausulas': list(CLAUSULAS_DE_APRENDER), 'passa': bool(all((t['passa'] for t in tab.values())))}
        _gravar(a.saida, out)
        nomes = [f'foto {n}' for n in FOTOS_NASCE_SABENDO] + [f'testemunha {n}' for n in ('sgd', 'ewc', 'cbp', 'sp')]
        bits = [fotos[n.split()[1]]['bits'] for n in nomes[:4]] + [test[n.split()[1]] for n in nomes[4:]]
        res = av.medir_no_desenvolvimento(bits, sementes_pert=PERT)
        res0 = av0.medir_no_desenvolvimento(bits, sementes_pert=(0,))
        t1, arr = ({}, {})
        for nome, r, r0 in zip(nomes, res, res0):
            busca = [V.julgar(x)['distancia'] for x in r[V.SEMENTE_DA_VIDA].values()]
            dev = [V.julgar(x)['distancia'] for s, d in r.items() if s != V.SEMENTE_DA_VIDA for x in d.values()]
            mb, eb = _media_ep(busca)
            mdv, edv = _media_ep(dev)
            t1[nome] = {'busca_media': round(mb, 1), 'busca_ep': round(eb, 1), 'dev_media': round(mdv, 1), 'dev_ep': round(edv, 1), 'queda': round(mdv - mb, 1), 'queda_ep': round(float(np.hypot(eb, edv)), 1), 'busca': busca, 'dev': dev}
            orig0 = V.julgar(r0[V.SEMENTE_DA_VIDA][0])['distancia']
            k3 = [V.julgar(r[V.SEMENTE_DA_VIDA][p])['distancia'] for p in PERT[:K]]
            pior, ep3 = (max(k3), _media_ep(k3)[1])
            arr[nome] = {'original_sem_perturbacao': int(orig0), 'k_medidas': k3, 'pior_de_k': int(pior), 'margem': round(ep3, 1), 'piora': int(pior - orig0), 'vive_no_arredondamento': bool(pior - orig0 > ep3)}
        fq = [t1[n]['queda'] for n in nomes[:4]]
        tq = [t1[n]['queda'] for n in nomes[4:]]
        dif = float(np.mean(fq) - np.mean(tq))
        ep_k = float(np.hypot(np.sqrt(sum((t1[n]['queda_ep'] ** 2 for n in nomes[:4]))) / 4, np.sqrt(sum((t1[n]['queda_ep'] ** 2 for n in nomes[4:]))) / 4))
        ep_entre = float(np.hypot(np.std(fq, ddof=1) / 2, np.std(tq, ddof=1) / 2))
        out['falsas']['nasce_sabendo'] = {'por_programa': t1, 'queda_media_das_fotos': round(float(np.mean(fq)), 1), 'queda_media_das_testemunhas': round(float(np.mean(tq)), 1), 'diferenca': round(dif, 1), 'erro_padrao_nas_k_sementes': round(ep_k, 1), 'erro_padrao_entre_programas (só registro)': round(ep_entre, 1), 'passa': bool(dif > ep_k)}
        nome_arr = f'foto {FOTO_DO_ARREDONDAMENTO}'
        out['falsas']['vive_no_arredondamento'] = {'por_programa': {n: arr[n] for n in [nome_arr] + nomes[4:]}, 'registro_das_outras_fotos': {n: arr[n] for n in nomes[:4] if n != nome_arr}, 'passa': bool(arr[nome_arr]['vive_no_arredondamento'] and (not any((arr[n]['vive_no_arredondamento'] for n in nomes[4:]))))}
    finally:
        av.fechar()
        av0.fechar()
    out['passam_todas'] = bool(all((f.get('passa') for f in out['falsas'].values())))
    out['hash_de_V2_depois'] = VB.hash_de_V2()
    out['hash_igual'] = out['hash_de_V2_depois'] == out['hash_de_V2']
    out['segundos'] = round(time.time() - t0, 1)
    _gravar(a.saida, out)
    print(json.dumps({k: v.get('passa') for k, v in out['falsas'].items()}, ensure_ascii=False), 'passam_todas', out['passam_todas'], 'hash_igual', out['hash_igual'], flush=True)
if __name__ == '__main__':
    main()
