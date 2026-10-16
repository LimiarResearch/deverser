# -*- coding: utf-8 -*-
import time
import numpy as np
from experimentos import desafio_memoria as MEM
from experimentos import desafio_oraculo as OR
from experimentos import desafio_v as DV
from experimentos import desafio_v_ser as V2
from experimentos import metricas_do_ser as MS
from experimentos import nulos_do_ser as NU
from experimentos import oraculo_do_ser as OS
from experimentos import trilhas_do_ser as TR
import simulador_vida as SV
PISO_BASE = dict(acerto=0.98)
ACERTO_DO_MEMORIZADOR = 0.7
TRI_IDEAL = dict(ganho=0.25, melhora=0.25, perda=0.0, retem=1.0, deficit=0.0)
EPIST_IDEAL = dict(rotulagem='calibrada', conflito=1.0, alarme_falso=0.0, nao_visto='investigar')
NEGATIVOS_NOVOS = {'r_calibra': ('acaso', dict(epist=dict(rotulagem='acaso'))), 'r_conflito_fino': ('nunca_marca_conflito', dict(epist=dict(conflito=0.0))), 'r_novidade': ('nunca_investiga', dict(epist=dict(nao_visto='validado'))), 'r_tempo_fixo': ('computacao_que_cresce', dict(flops='cresce')), 'r_compoe_8': ('fresco_na_composta', dict(tri=dict(ganho=0.0))), 'r_compoe_32': ('fresco_na_composta', dict(tri=dict(ganho=0.0))), 'r_melhora_com_o_uso': ('nao_aprende_a_aprender', dict(tri=dict(melhora=0.0))), 'r_latencia': ('perde_plasticidade', dict(tri=dict(perda=0.25))), 'r_recorrencia': ('esquece_a_tarefa_que_volta', dict(tri=dict(retem=0.0))), 'r_deriva': ('fica_para_tras_da_deriva', dict(tri=dict(deficit=0.3)))}
FAMILIAS_EPISTEMICAS = ('seq', 'ling', 'age')

class _Ctx:

    def __init__(self, familias=None, orac=None, sondas_mem=None, semente=V2.SEMENTE_DA_VIDA):
        self.semente = int(semente)
        self.fam = familias or V2.gerar_familias(self.semente)
        self.orac = orac or V2.oraculos(self.fam, self.semente)
        self.sondas_mem = sondas_mem or V2.sondas_de_memoria(self.fam)

def _simular(ctx, piso=None, historico=None, epist=None, tri=None, flops='const', semente=1):
    V2._zerar(ctx.fam)
    saidas = {}
    for nome in FAMILIAS_EPISTEMICAS:
        saidas[nome] = SV.executar(ctx.fam[nome], **dict(PISO_BASE, **piso or {}, semente=semente))
    for nome in ('seq', 'ling'):
        MEM.simular_memoria(ctx.fam[nome], saidas[nome], ctx.sondas_mem[nome], semente=semente, **historico or {})
    saidas['tri'] = TR.simular_trilha(ctx.fam['tri'], **dict(TRI_IDEAL, **tri or {}), orac=[ctx.orac['der']], semente=semente)
    for nome in V2.FAMILIAS:
        ni = [len(f['_avaliacao'].abrir()['interromper_em']) for f in ctx.fam[nome]['fluxos']]
        saidas[nome]['flops'] = [[1000.0 * (1 + i if flops == 'cresce' else 1.0) for i in range(n)] for n in ni]
    saidas['age']['tamanho_logico'] = [[4000] * n for n in [len(f['_avaliacao'].abrir()['interromper_em']) for f in ctx.fam['age']['fluxos']]]
    saidas['age']['sucessos'] = [[] for _ in ctx.fam['age']['fluxos']]
    res = V2.resultado_de_saida(ctx.fam, saidas, 0.0, False, ctx.orac, ctx.sondas_mem)
    ep = dict(EPIST_IDEAL, **epist or {})
    i = 0
    for nome in V2.FAMILIAS:
        n = len(ctx.fam[nome]['fluxos'])
        if nome in FAMILIAS_EPISTEMICAS:
            s_ep = MS.simular_epistemico(ctx.fam[nome], semente=semente, **ep)
            for k, f in enumerate(ctx.fam[nome]['fluxos']):
                pv = res['por_vida'][_indice_da_vida(res, nome, k)]
                for c in ('erro_de_calibracao', 'conflito_J', 'novidade'):
                    pv.pop(c, None)
                pv.update(V2._epistemicas(f['_avaliacao'].abrir(), s_ep['respostas'][k], s_ep['etiquetas'][k]))
        i += n
    return res

def _indice_da_vida(res, nome, k):
    achadas = [i for i, pv in enumerate(res['por_vida']) if pv['familia'] == nome]
    return achadas[k]

def _veredito(ctx, **kw):
    return V2.julgar(_simular(ctx, **kw))

def _reprovadas(v):
    return [V2.IDS[i] for i, x in enumerate(v['violacoes']) if x > 1e-09]

def calibrar(familias=None, orac=None, sondas_mem=None, relato=None):
    t0 = time.time()

    def dizer(txt):
        if relato:
            relato(f'[calibrar {round(time.time() - t0)} s] {txt}')
    ctx = _Ctx(familias, orac, sondas_mem)
    out = {'controles': {}, 'clausulas': {}, 'degenerados': {}, 'deficit': {}, 'historico': {}, 'tolerancias': {}, 'ok': True}
    veredito = {}
    for nome, params in DV.CONTROLES.items():
        veredito[nome] = _veredito(ctx, piso=params)
        out['controles'][nome] = {'nfal': veredito[nome]['nfal'], 'reprovadas': _reprovadas(veredito[nome])}
    for nome, extra in DV.CONTROLES_DE_HISTORICO.items():
        veredito[nome] = _veredito(ctx, historico=extra, piso=dict(acerto=ACERTO_DO_MEMORIZADOR) if 'memoriza' in extra else None)
        out['controles'][nome] = {'nfal': veredito[nome]['nfal'], 'reprovadas': _reprovadas(veredito[nome])}
    for cid, (nome, kw) in NEGATIVOS_NOVOS.items():
        veredito[f'{cid}:{nome}'] = _veredito(ctx, **kw)
        out['controles'][f'{cid}:{nome}'] = {'nfal': veredito[f'{cid}:{nome}']['nfal'], 'reprovadas': _reprovadas(veredito[f'{cid}:{nome}'])}
    dizer('controles feitos')
    ideal = veredito['ideal']
    if ideal['nfal'] != 0:
        out['ok'] = False
    out['controles']['ideal']['cumpre_as_28'] = bool(ideal['nfal'] == 0)
    for cid, neg in list(DV.NEGATIVO.items()) + [(c, f'{c}:{n}') for c, (n, _) in NEGATIVOS_NOVOS.items()]:
        i = V2.IDS.index(cid)
        pos_ok = ideal['violacoes'][i] <= 1e-09
        neg_ok = veredito[neg]['violacoes'][i] > 1e-09
        out['clausulas'][cid] = {'positivo_cumpre': bool(pos_ok), 'negativo': neg, 'negativo_reprova': bool(neg_ok)}
        if not (pos_ok and neg_ok):
            out['ok'] = False
    for nome in ('nulo', 'majoritaria'):
        out['degenerados'][nome] = {'cumpre_D': veredito[nome]['nfal'] == 0}
        if veredito[nome]['nfal'] == 0:
            out['ok'] = False
    dizer('positivo e negativos de cada cláusula conferidos')

    def deficits_das_vidas(saidas):
        pior = np.zeros(4)
        for nome in ('seq', 'ling'):
            for k, f in enumerate(ctx.fam[nome]['fluxos']):
                A = OR.acerto_por_sonda(f, saidas[nome]['respostas'][k])
                d = OR.deficit(A, ctx.orac[nome][k], ctx.orac[nome][k]['G'])[:4]
                pior = np.maximum(pior, [x if np.isfinite(x) else 0.0 for x in d])
        return pior
    ruido = np.asarray([deficits_das_vidas({n: OR.simular_do_oraculo(ctx.fam[n], ctx.orac[n], fator=1.0, esquece=0.0, semente=s) for n in ('seq', 'ling')}) for s in range(1, 6)])
    esq4 = deficits_das_vidas({n: OR.simular_do_oraculo(ctx.fam[n], ctx.orac[n], fator=1.0, esquece=0.3, semente=1) for n in ('seq', 'ling')})
    variantes = [v for v in range(1, 9) if all((__import__('os').path.exists(a) for a in (DV.caminho_do_oraculo(ctx.semente, v), OS.caminho_ling(ctx.semente, v))))]
    assert variantes, 'faltam os outros recomeços (as variantes 1 a 8 do oráculo das sequências e da linguagem)'
    por_recomeco = []
    for v in variantes:
        o_seq = OR.oraculo_das_vidas(ctx.fam['seq'], DV.caminho_do_oraculo(ctx.semente, v), variante=v)
        o_lin = OR.oraculo_das_vidas(ctx.fam['ling'], OS.caminho_ling(ctx.semente, v), variante=v)
        var = np.concatenate([OR.variacao_entre_recomecos(ctx.orac['seq'], o_seq), OR.variacao_entre_recomecos(ctx.orac['ling'], o_lin)])
        por_recomeco.append(var.max(0))
    por_recomeco = np.asarray(por_recomeco)
    n3 = len(V2.IDS_DEFICIT)
    eta = np.asarray([V2.ETA[c] for c in V2.IDS_DEFICIT])
    medido = np.maximum(por_recomeco.max(0)[:n3], ruido.max(0)[:n3])
    regra = por_recomeco.mean(0) + 3 * por_recomeco.std(0)
    pos_ok = bool((medido <= eta + 1e-12).all() and (DV._arredondar_para_cima(regra[:n3]) <= eta + 1e-12).all())
    neg_ok = bool(esq4[0] >= 2 * eta[0] and esq4[1] >= 2 * eta[1])
    out['deficit'] = {'eta': {c: V2.ETA[c] for c in V2.IDS_DEFICIT}, 'eta_pela_regra (media + 3 desvios dos recomeços, para cima em 0,01)': dict(zip(V2.DEFICITS, DV._arredondar_para_cima(regra).tolist())), 'pior_das_6_vidas_de_cada_recomeco [variantes, 4]': np.round(por_recomeco, 4).tolist(), 'ruido_do_positivo (media, maximo por parte)': [np.round(ruido.mean(0), 4).tolist(), np.round(ruido.max(0), 4).tolist()], 'esquecedor_de_0,3 [total, conserva, aprende, revisa]': np.round(esq4, 4).tolist(), 'positivo_cumpre': pos_ok, 'negativo_reprova': neg_ok, 'recomecos_medidos': len(variantes)}
    if not (pos_ok and neg_ok):
        out['ok'] = False
    dizer('déficit conferido')

    def lacuna(historico, semente, acerto=PISO_BASE['acerto']):
        pior = 0.0
        for nome in ('seq', 'ling'):
            V2._zerar({nome: ctx.fam[nome]})
            saida = SV.executar(ctx.fam[nome], **dict(PISO_BASE, acerto=acerto, semente=semente))
            MEM.simular_memoria(ctx.fam[nome], saida, ctx.sondas_mem[nome], semente=semente, **historico)
            r = DV.resultado_de_saida(ctx.fam[nome], saida, 0.0, False, None, ctx.sondas_mem[nome])
            pior = max(pior, max((pv['lacuna_de_memoria'] for pv in r['por_vida'])))
        return pior
    lac = [lacuna({'memoriza': 0.0}, s) for s in range(1, 17)]
    lac_mem = lacuna({'memoriza': 0.25}, 1, ACERTO_DO_MEMORIZADOR)
    eta_l = V2.ETA['r_sem_historico_lacuna']
    out['historico'] = {'eta_da_lacuna': eta_l, 'lacuna_media_e_desvio': [round(float(np.mean(lac)), 4), round(float(np.std(lac)), 4)], 'lacuna_do_positivo (16 sorteios, pior das 6 vidas)': np.round(lac, 4).tolist(), 'lacuna_do_memorizador_de_0,25': round(float(lac_mem), 4), 'positivo_cumpre': bool(max(lac) <= eta_l + 1e-12), 'negativo_reprova_com_folga': bool(lac_mem >= 2 * eta_l)}
    if not (out['historico']['positivo_cumpre'] and out['historico']['negativo_reprova_com_folga']):
        out['ok'] = False
    dizer('histórico conferido')
    nulos = NU.medir(ctx.semente, relato=lambda *_: None)
    t = nulos['trilhas']['tolerancia_pela_regra']
    constantes = {'compoe_8': V2.R_COMPOE_8, 'compoe_32': V2.R_COMPOE_32, 'melhora_com_o_uso': V2.R_MELHORA, 'latencia_de_adaptacao': V2.R_LATENCIA}
    medidas = {'compoe_8': t['compoe_8'], 'compoe_32': t['compoe_32'], 'melhora_com_o_uso': t['melhora_com_o_uso'], 'latencia_de_adaptacao': t['latencia_de_adaptacao']}
    ok_t = {k: bool(constantes[k] >= medidas[k] - 1e-12) for k in constantes}
    ok_t['deriva'] = bool(V2.ETA_DERIVA >= nulos['deriva']['tolerancia_pela_regra'] - 1e-12)
    out['tolerancias'] = {'constantes': dict(constantes, deriva=V2.ETA_DERIVA), 'medidas_pela_regra (media + 3 desvios do nulo, para cima em 0,01)': dict(medidas, deriva=nulos['deriva']['tolerancia_pela_regra']), 'media_do_nulo': nulos['trilhas']['media'], 'constante_cobre_o_medido': ok_t, 'variacao_entre_recomecos_da_janela': nulos['deriva']['variacao_por_recomeco']}
    if not all(ok_t.values()):
        out['ok'] = False
    dizer('tolerâncias conferidas')
    from experimentos import l_ser_testemunhas as LT
    av = V2.AvaliadorReal.__new__(V2.AvaliadorReal)
    av.semente, av.tempo_max, av.familias, av.orac, av.sondas_mem = (ctx.semente, V2.TEMPO_MAX_PADRAO, ctx.fam, ctx.orac, ctx.sondas_mem)
    v = V2.julgar(av.medir(LT.testemunhas_em_bits()['sgd']))
    out['degenerados']['sgd_simples'] = {'cumpre_D': v['nfal'] == 0, 'clausulas_que_cumpre': V2.N_CLAUSULAS - v['nfal'], 'estado': v['estado']}
    if v['nfal'] == 0:
        out['ok'] = False
    out['segundos'] = round(time.time() - t0, 1)
    dizer('pronto')
    return out
