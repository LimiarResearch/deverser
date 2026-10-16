# -*- coding: utf-8 -*-
import hashlib
import os
import sys
import time
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
import metricas_vida
import oraculo_vida
from experimentos import agentes_do_ser as AG
from experimentos import desafio_memoria as MEM
from experimentos import desafio_oraculo as OR
from experimentos import desafio_v as DV
from experimentos import metricas_do_ser as MS
from experimentos import oraculo_do_ser as OS
from experimentos import trilhas_do_ser as TR
from experimentos import vidas_do_ser as VS
VERSAO_DOS_PREDICADOS = 4
N_PREDICADOS = 128
SEMENTE_DA_VIDA = DV.SEMENTE_DA_VIDA
FAMILIAS = ('seq', 'ling', 'tri', 'age')
TEMPO_MAX_PADRAO = 440.0
Estouro = DV.Estouro
ETA = {'r_deficit': 0.12, 'r_deficit_conserva': 0.12, 'r_deficit_aprende': 0.06, 'r_sem_historico_lacuna': DV.ETA['r_sem_historico_lacuna'], 'r_sem_historico_estado': DV.ETA['r_sem_historico_estado']}
R_COMPOE_8, R_COMPOE_32, R_MELHORA, R_LATENCIA, ETA_DERIVA = (0.04, 0.04, 0.03, 0.04, 0.02)
ETA['r_deriva'] = ETA_DERIVA

def _com_eta(c):
    cid, medida, op, lim, esc = c
    return (cid, medida, op, ETA[cid], esc) if cid in ETA and ETA[cid] is not None else c
CLAUSULAS = [_com_eta(c) for c in DV.CLAUSULAS]
CLAUSULAS += [('r_calibra', 'erro_de_calibracao', '<=', 0.02, 1.0), ('r_conflito_fino', 'conflito_J', '>=', 0.85, 1.0), ('r_novidade', 'novidade', '>=', 0.9, 1.0), ('r_tempo_fixo', 'crescimento_da_computacao', '<=', 0.05, 1.0), ('r_compoe_8', 'compoe_8', '>=', R_COMPOE_8, 1.0), ('r_compoe_32', 'compoe_32', '>=', R_COMPOE_32, 1.0), ('r_melhora_com_o_uso', 'melhora_com_o_uso', '>=', R_MELHORA, 1.0), ('r_latencia', 'latencia_de_adaptacao', '<=', R_LATENCIA, 1.0), ('r_recorrencia', 'custo_da_volta', '<=', 0.1, 1.0), ('r_deriva', 'deficit_de_deriva', '<=', ETA_DERIVA, 1.0)]
IDS = [c[0] for c in CLAUSULAS]
N_CLAUSULAS = len(CLAUSULAS)
N_PISO = DV.N_PISO
NIVEIS = DV.NIVEIS + ['ser'] * (N_CLAUSULAS - len(DV.NIVEIS))
IDS_NOVOS = IDS[len(DV.CLAUSULAS):]
ORIGEM = dict(DV.ORIGEM)
ORIGEM.update({'r_deficit': ('I+R', 'sem reiniciar o treinamento a cada habilidade nova, sem perder as habilidades anteriores: o valor é 0 (a intenção) e a tolerância é a variação entre dois recomeços, no pior das seis vidas de sequências e de linguagem (a resolução de V)'), 'r_deficit_conserva': ('I+R', 'sem perder as habilidades anteriores: o déficit nas tarefas treinadas há tempo é 0, com a tolerância medida entre dois recomeços, no pior das seis vidas'), 'r_deficit_aprende': ('I+R', 'aprenda operando: o déficit na tarefa treinada agora é 0, com a tolerância medida entre dois recomeços, no pior das seis vidas'), 'r_calibra': ('I+E', 'distinga o que sabe, o que supõe e o que precisa investigar: o erro de calibração das etiquetas é 0 (a intenção), com a folga de 0,02 e as bordas 0,9 e 0,5 do intervalo de cada etiqueta (escolha da IA)'), 'r_conflito_fino': ('I+E', 'distinga o que conflita: a revocação do conflito depois de uma refutação menos o alarme falso é 1 (a intenção); a cláusula pede 0,85 (escolha da IA, a confirmar pelo positivo)'), 'r_novidade': ('I+E', "precise investigar o que nunca viu: a sensibilidade do 'investigar' a tarefa nunca vista é 1 (a intenção); a cláusula pede 0,9 (escolha da IA)"), 'r_tempo_fixo': ('I+E', 'memória e computação limitadas, aprendendo enquanto interage: a computação por interação não cresce com a vida (a intenção), com a folga de 5% (escolha da IA)'), 'r_compoe_8': ('I+R', 'combine habilidades já aprendidas com poucos exemplos: o ganho sobre o aprendiz fresco com 8 exemplos da composta é no mínimo a resolução de V (o nulo, um fresco contra outro)'), 'r_compoe_32': ('I+R', 'combine habilidades já aprendidas com poucos exemplos: o ganho sobre o fresco com 32 exemplos da composta é no mínimo a resolução de V (o nulo)'), 'r_melhora_com_o_uso': ('I+R', 'aprenda cada vez mais depressa com o uso: o ganho sobre o aprendiz fresco da mesma tarefa, nas últimas tarefas menos nas primeiras, é no mínimo a resolução de V (o nulo: um fresco a cada tarefa)'), 'r_latencia': ('I+R', 'a capacidade de se transformar continua ativa: a velocidade que se perde (o ganho sobre o fresco nas primeiras tarefas menos nas últimas) é no máximo a resolução de V (o nulo: quem reaprende cada tarefa igual)'), 'r_recorrencia': ('I+E', 'não perca o que já aprendeu: reaprender uma tarefa que volta custa até 10% do que custou da primeira vez (o texto do D ampliado; quem guardou tem custo 0)'), 'r_deriva': ('I+R', 'acompanhe uma regra que muda devagar: o déficit contra o recomeço de janela (a rede fora de linha treinada só nos últimos exemplos) é 0, com a tolerância medida entre dois recomeços de janela')})
ORIGENS_VALIDAS = DV.ORIGENS_VALIDAS
CLASSES = ('cumpre D', 'a 1 cláusula de D', '2 a 3 cláusulas', '4 a 6 cláusulas', '7 a 12 cláusulas', '13 ou mais cláusulas', 'sem classe (estouro, erro ou oráculo)')
DIST_MAX = 1000 * N_CLAUSULAS + 1
POR_VIDA = DV.POR_VIDA
DEFICITS = DV.DEFICITS
IDS_DEFICIT = DV.IDS_DEFICIT
SO_GLOBAIS = ('usa_informacao_retida', 'bytes_de_estado', 'restauracao_fiel')

def gerar_familias(semente=SEMENTE_DA_VIDA):
    return {'seq': DV.gerar_vidas(semente), 'ling': VS.gerar_carga(VS.MundoDeLinguagem(), OS.semente_da_linguagem(semente), 2), 'tri': TR.gerar_trilhas(semente), 'age': AG.gerar_carga(semente, 2)}

def _zerar(familias):
    for e in familias.values():
        DV._zerar(e)

def oraculos(familias, semente=SEMENTE_DA_VIDA, variante=0):
    out = {'seq': OR.oraculo_das_vidas(familias['seq'], DV.caminho_do_oraculo(semente, variante), variante=variante), 'ling': OR.oraculo_das_vidas(familias['ling'], OS.caminho_ling(semente, variante), variante=variante, **OS.CONFIG_LING)}
    arq = OS.caminho_der(semente, variante)
    if not os.path.exists(arq):
        der = [f for f in familias['tri']['fluxos'] if f['tipo'] == 'der'][0]
        OS.guardar_der(arq, OS.oraculo_der_da_vida(der, variante))
    out['der'] = OS.carregar_der(arq)
    return out

def sondas_de_memoria(familias):
    return {n: [MEM.montar_sondas_de_memoria(f) for f in familias[n]['fluxos']] for n in ('seq', 'ling')}

def _interprete():
    if DV.BACKEND_DO_SER == 'cpp':
        from experimentos import l_ser_cpp as LI
    else:
        from experimentos import l_ser_interp as LI
    return LI

def executar_ser(familias, bits, sondas_mem, tempo_max=TEMPO_MAX_PADRAO):
    fab, rest = _interprete().fabricar(bits)
    return executar_fabrica(familias, fab, rest, sondas_mem, tempo_max)

class ComAlvoSuave:

    def __init__(self, p):
        self._p = p

    def aprender(self, x, y):
        y = np.asarray(y)
        if y.ndim == 0:
            self._p.aprender(x, int(y))
            return
        zeros = int((y <= 1e-09).sum())
        if zeros == 1 and np.allclose(np.sort(y)[1:], 1.0 / (len(y) - 1), atol=1e-06):
            return
        self._p.aprender(x, int(np.argmax(y)))

    def prever(self, X):
        return self._p.prever(X)

    def estado(self):
        return self._p.estado()

    def diagnostico(self):
        return self._p.diagnostico()

    def flops_por_interacao(self):
        f = getattr(self._p, 'flops_por_interacao', None)
        return None if f is None else f()

def fabrica_do_l2(bits):
    p = DV.L2.normalizar(DV.G.decodificar(bits))
    return (lambda d, c, r: ComAlvoSuave(DV.L2._P(d, c, r, p)), lambda b, d, c: ComAlvoSuave(DV.L2._P.restaurar(b, d, c)))

def executar_fabrica(familias, fab, rest, sondas_mem, tempo_max=TEMPO_MAX_PADRAO):
    limite, contagem = (time.time() + float(tempo_max), [0])
    mk = lambda d, c, r: DV._Guarda(fab(d, c, r), limite, contagem)
    rs = lambda b, d, c: DV._Guarda(rest(b, d, c), limite, contagem)
    t0 = time.time()
    saidas, tempos = ({}, {})
    for nome in FAMILIAS:
        t1 = time.time()
        if nome in ('seq', 'ling'):
            saidas[nome] = MEM.rodar_com_memoria(familias[nome], mk, rs, sondas_mem[nome])
        elif nome == 'tri':
            saidas[nome] = MEM.rodar_com_memoria(familias[nome], mk, rs, None, varrer_estado=False)
        else:
            saidas[nome] = AG.rodar_agentes(familias[nome], mk, rs)
        tempos[nome] = time.time() - t1
    return (saidas, time.time() - t0, tempos)

def _crescimento(lista):
    return float(max(0.0, (lista[-1] - lista[0]) / lista[0])) if len(lista) >= 2 and lista[0] > 0 else 0.0

def _epistemicas(av, R, E):
    ep = MS.epistemicas(av, R, E)
    return {k: float(ep[k]) for k in ('erro_de_calibracao', 'conflito_J', 'novidade') if np.isfinite(ep[k])}

def _vida_de_agentes(f, resp, etq, tam, flo, sucessos):
    av = f['_avaliacao'].abrir()
    R = AG.ajustar_respostas(av, resp)
    m = metricas_vida._fluxo(f, R, etq)
    m.pop('_perfil', None)
    pv = {k: float(m[k]) for k in POR_VIDA}
    pv.update(_epistemicas(av, R, etq))
    pv['crescimento_do_estado'] = _crescimento(tam)
    pv['crescimento_da_computacao'] = _crescimento(flo)
    pv['flops_por_interacao'] = float(flo[-1]) if flo else 0.0
    pv['sucesso_final'] = float(np.mean(sucessos[-300:])) if len(sucessos) else 0.0
    return pv

def _vida_de_trilha(f, resp, flo, orac_der):
    av = f['_avaliacao'].abrir()
    m = TR.medir_trilha(av, resp, orac_der if av['tipo'] == 'der' else None)
    pv = {k: v for k, v in m.items() if not isinstance(v, list)}
    pv['crescimento_da_computacao'] = _crescimento(flo)
    pv['flops_por_interacao'] = float(flo[-1]) if flo else 0.0
    for k, v in m.items():
        if isinstance(v, list):
            pv[k] = [float(x) for x in v]
    return pv

def conferir(familias, saidas):
    for nome in FAMILIAS:
        ok, msg = TR.conferir_trilha(familias[nome], saidas[nome]) if nome == 'tri' else oraculo_vida.conferir(familias[nome], saidas[nome])
        if not ok:
            return (False, f'{nome}: {msg}')
    return (True, 'ok')

def resultado_de_saida(familias, saidas, cpu_s=0.0, com_oraculo=True, orac=None, sondas_mem=None, tempos=None):
    ok, msg = conferir(familias, saidas) if com_oraculo else (True, 'sem oráculo (controle)')
    por_vida, det, divergiu = ([], [], [])
    for nome in ('seq', 'ling'):
        o = None if orac is None else orac[nome]
        sm = None if sondas_mem is None else sondas_mem[nome]
        r = DV.resultado_de_saida(familias[nome], saidas[nome], 0.0, False, o, sm)
        for k, (f, pv) in enumerate(zip(familias[nome]['fluxos'], r['por_vida'])):
            pv['familia'] = nome
            pv.update(_epistemicas(f['_avaliacao'].abrir(), saidas[nome]['respostas'][k], saidas[nome]['etiquetas'][k]))
            por_vida.append(pv)
        det += r['detalhe']
        if nome == 'seq':
            divergiu = r['divergiu_por_vida']
    s = saidas['tri']
    flops_tri = s.get('flops') or [[] for _ in familias['tri']['fluxos']]
    for k, f in enumerate(familias['tri']['fluxos']):
        pv = _vida_de_trilha(f, s['respostas'][k], flops_tri[k], None if orac is None else orac['der'])
        pv['familia'] = 'tri:' + f['tipo']
        por_vida.append(pv)
    s = saidas['age']
    n_age = len(familias['age']['fluxos'])
    flops_age, tam_age, suc_age = (s.get('flops') or [[]] * n_age, s.get('tamanho_logico') or [[]] * n_age, s.get('sucessos') or [[]] * n_age)
    for k, f in enumerate(familias['age']['fluxos']):
        pv = _vida_de_agentes(f, s['respostas'][k], s['etiquetas'][k], tam_age[k], flops_age[k], suc_age[k])
        pv['familia'] = 'age'
        por_vida.append(pv)
    fiel = [x for n in FAMILIAS for fl in saidas[n]['restauracao_fiel'] for x in fl]
    bytes_ = [b for n in FAMILIAS for fl in saidas[n]['bytes_por_interrupcao'] for b in fl]
    diag = {}
    for d in saidas['seq'].get('diagnostico', []):
        for k, v in d.items():
            if isinstance(v, (int, float)):
                diag[k] = diag.get(k, 0) + v
    return {'estado': 'ok' if ok else 'oraculo', 'oraculo': bool(ok), 'oraculo_msg': msg, 'cpu_s': float(cpu_s), 'tempo_por_familia': {k: round(float(v), 2) for k, v in (tempos or {}).items()}, 'por_vida': por_vida, 'detalhe': det, 'deficit_medido': orac is not None, 'memoria_medida': sondas_mem is not None and bool(saidas['seq'].get('memoria')), 'bytes_de_estado': int(max(bytes_ or [10 ** 9])), 'restauracao_fiel': float(np.mean(fiel)) if fiel else 0.0, 'usa_informacao_retida': int(any((f['_avaliacao'].lido for n in FAMILIAS for f in familias[n]['fluxos']))), 'divergiu_por_vida': divergiu or [0] * len(familias['seq']['fluxos']), 'diag': {k: float(v) for k, v in diag.items()}}

def _pior(vals, op):
    return DV._pior(vals, op)

def valores_das_clausulas(res):
    out = []
    for cid, medida, op, lim, esc in CLAUSULAS:
        if medida in SO_GLOBAIS:
            out.append(float(res[medida]))
            continue
        vals = [v[medida] for v in res['por_vida'] if medida in v and np.isfinite(v[medida])]
        if not vals:
            raise ValueError(f'nenhuma vida traz a medida {medida} (cláusula {cid}): V mal montada')
        out.append(float(_pior(vals, op)))
    return out

def violacoes(valores):
    out = []
    for (cid, medida, op, lim, esc), v in zip(CLAUSULAS, valores):
        out.append((max(0.0, v - lim) if op == '<=' else max(0.0, lim - v) if op == '>=' else abs(v - lim)) / esc)
    return out

def violacoes_de_coluna(i, v):
    cid, medida, op, lim, esc = CLAUSULAS[i]
    v = np.asarray(v, np.float64)
    f = np.maximum(0.0, v - lim) if op == '<=' else np.maximum(0.0, lim - v) if op == '>=' else np.abs(v - lim)
    return f / esc

def classe_da_distancia(nfal, estado='ok'):
    if estado != 'ok':
        return len(CLASSES) - 1
    return 0 if nfal == 0 else 1 if nfal == 1 else 2 if nfal <= 3 else 3 if nfal <= 6 else 4 if nfal <= 12 else 5

def _nomes_dos_predicados():
    nomes = [f'falha:{c}' for c in IDS]
    nomes += [f'longe:{c}' for c in IDS]
    cauda = DV.NOMES_DOS_PREDICADOS[2 * DV.N_CLAUSULAS:]
    return nomes + list(cauda)
NOMES_DOS_PREDICADOS = _nomes_dos_predicados()
N_DEFINIDOS = len(NOMES_DOS_PREDICADOS)
N_DURAS = N_CLAUSULAS
_IDX = {n: i for i, n in enumerate(NOMES_DOS_PREDICADOS)}
assert N_DEFINIDOS == 2 * N_CLAUSULAS + 60 and N_DEFINIDOS <= N_PREDICADOS

class Predicados:
    versao = VERSAO_DOS_PREDICADOS
    duras = list(range(N_DURAS))

    def __len__(self):
        return N_DEFINIDOS

    def mascara_das_duras(self):
        return (1 << N_DURAS) - 1

    def duras_que_falham(self, comp):
        return bin(int(comp) & self.mascara_das_duras()).count('1')

    def descricao(self):
        return {'versao': VERSAO_DOS_PREDICADOS, 'predicados': N_DEFINIDOS, 'duras': N_DURAS, 'nomes': NOMES_DOS_PREDICADOS, 'regra': 'cada predicado é 1 quando o concorrente faz o que D não quer (falha a cláusula, esqueceu a tarefa, não compôs, não corrigiu, ficou aquém do recomeço...); as duras são as cláusulas de D no pior das vidas'}

def comportamento(res, viol, estado):
    bits = np.zeros(N_PREDICADOS, np.uint8)
    if estado != 'ok':
        bits[_IDX['estouro_de_tempo']] = 1 if estado == 'estouro' else 0
        return DV._inteiro(bits)
    for i, v in enumerate(viol):
        bits[i] = 1 if v > 1e-09 else 0
        bits[N_CLAUSULAS + i] = 1 if v > 0.25 else 0
    det, pv = (res['detalhe'], res['por_vida'])
    for t in range(12):
        e = [d['esq'][t] for d in det if t in d['esq']]
        if e and max(e) > 0.1:
            bits[_IDX[f'esqueceu:t{t}']] = 1
        f = [d['fin'][t] for d in det if t in d['fin']]
        if f and float(np.mean(f)) < 0.4:
            bits[_IDX[f'nao_aprendeu:t{t}']] = 1
        dd = [d['deficit_por_tarefa'][t] for d in det if t in d.get('deficit_por_tarefa', {})]
        if dd and max(dd) > 0.15:
            bits[_IDX[f'deficit_alto:t{t}']] = 1
    comps = sorted({c for d in det for c in d['comp']})
    for j, c in enumerate(comps[:3]):
        v = [d['comp'][c] for d in det if c in d['comp']]
        if v and min(v) < 0.01:
            bits[_IDX[f'nao_compoe:c{j}']] = 1
    refs = sorted({r for d in det for r in d['corr']})
    for j, r in enumerate(refs[:3]):
        c = [d['corr'][r] for d in det if r in d['corr']]
        if c and min(c) < 0.9:
            bits[_IDX[f'nao_corrigiu:r{j}']] = 1
        a = [d['antiga'][r] for d in det if r in d['antiga']]
        if a and max(a) > 0.1:
            bits[_IDX[f'regra_antiga:r{j}']] = 1
        k = [d['conflito'][r] for d in det if r in d['conflito']]
        if k and min(k) < 0.5:
            bits[_IDX[f'sem_conflito:r{j}']] = 1
    for v in range(min(4, len(pv))):
        if pv[v]['acc_final'] < 0.35:
            bits[_IDX[f'vida_ruim:v{v}']] = 1
        if res['divergiu_por_vida'][v] > 0:
            bits[_IDX[f'divergiu:v{v}']] = 1
    bits[_IDX['estado_grande']] = 1 if res['bytes_de_estado'] > 65536 else 0
    bits[_IDX['nao_fiel']] = 1 if res['restauracao_fiel'] < 1.0 else 0
    bits[_IDX['leu_o_cofre']] = 1 if res['usa_informacao_retida'] else 0
    return DV._inteiro(bits)

def julgar(res):
    estado = res['estado']
    if estado != 'ok':
        return {'estado': estado, 'valores': [float('nan')] * N_CLAUSULAS, 'violacoes': [1.0] * N_CLAUSULAS, 'distancia': DIST_MAX, 'nfal': N_CLAUSULAS, 'classe': classe_da_distancia(N_CLAUSULAS, estado), 'comportamento': comportamento(res, [1.0] * N_CLAUSULAS, estado), 'cpu_s': float(res.get('cpu_s', 0.0)), 'bytes': int(res.get('bytes_de_estado', 0))}
    vals = valores_das_clausulas(res)
    viol = violacoes(vals)
    nfal = sum((1 for v in viol if v > 1e-09))
    return {'estado': 'ok', 'valores': vals, 'violacoes': viol, 'distancia': int(round(1000.0 * sum((min(v, 1.0) for v in viol)))), 'nfal': nfal, 'classe': classe_da_distancia(nfal), 'comportamento': comportamento(res, viol, 'ok'), 'cpu_s': float(res['cpu_s']), 'bytes': int(res['bytes_de_estado'])}

class AvaliadorReal:

    def __init__(self, semente=SEMENTE_DA_VIDA, tempo_max=TEMPO_MAX_PADRAO, com_deficit=True, backend=None, familias=None, orac=None, sondas_mem=None):
        if backend is not None:
            DV.definir_backend(backend)
        self.semente, self.tempo_max = (int(semente), float(tempo_max))
        if familias is not None and orac is None and com_deficit:
            raise ValueError('famílias de fora trazem o oráculo delas (`orac`) ou pedem `com_deficit=False`')
        self.familias = gerar_familias(self.semente) if familias is None else familias
        self.orac = orac if orac is not None else oraculos(self.familias, self.semente) if com_deficit else None
        self.sondas_mem = sondas_de_memoria(self.familias) if sondas_mem is None else sondas_mem

    def medir(self, bits):
        return self._medir_com(lambda: _interprete().fabricar(np.asarray(bits, np.uint8)))

    def medir_l2(self, bits_l2):
        return self._medir_com(lambda: fabrica_do_l2(np.asarray(bits_l2, np.uint8)))

    def _medir_com(self, construir):
        _zerar(self.familias)
        try:
            fab, rest = construir()
            saidas, dt, tempos = executar_fabrica(self.familias, fab, rest, self.sondas_mem, self.tempo_max)
        except Estouro:
            return {'estado': 'estouro', 'oraculo': True, 'cpu_s': self.tempo_max}
        except Exception as e:
            return {'estado': 'erro', 'oraculo': True, 'cpu_s': 0.0, 'erro': repr(e)[:200]}
        return resultado_de_saida(self.familias, saidas, dt, True, self.orac, self.sondas_mem, tempos)
_PROCESSO = {}

def _iniciar(semente, tempo_max, backend=None):
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    _PROCESSO['av'] = AvaliadorReal(semente, tempo_max, backend=backend)

def _medir_no_processo(pacote):
    from experimentos import l_ser_lang as LL
    return _PROCESSO['av'].medir(LL.CODIFICACAO.desempacotar(pacote))

def _medir_l2_no_processo(bits):
    return _PROCESSO['av'].medir_l2(np.asarray(bits, np.uint8))

class Avaliacoes:

    def __init__(self, processos=4, semente=SEMENTE_DA_VIDA, tempo_max=TEMPO_MAX_PADRAO, avaliador=None, alvo='ser', backend=None):
        if alvo != 'ser':
            raise ValueError('a V completa (V2) mede o Ser; o L2 segue em `desafio_v.Avaliacoes`')
        if backend is not None:
            DV.definir_backend(backend)
        self.processos, self.semente, self.tempo_max = (int(processos), int(semente), float(tempo_max))
        self.avaliador = avaliador
        self._pool = None
        self._local = None
        self.medidos = 0
        if avaliador is None and processos > 0:
            oraculos(gerar_familias(self.semente), self.semente)
            import multiprocessing as mp
            self._pool = mp.get_context('spawn').Pool(processos, initializer=_iniciar, initargs=(self.semente, self.tempo_max, DV.BACKEND_DO_SER))

    def _um_local(self):
        if self.avaliador is not None:
            return self.avaliador
        if self._local is None:
            self._local = AvaliadorReal(self.semente, self.tempo_max)
        return self._local

    def medir(self, lista_de_bits):
        from experimentos import l_ser_lang as LL
        self.medidos += len(lista_de_bits)
        if self._pool is not None:
            return self._pool.map(_medir_no_processo, [LL.CODIFICACAO.empacotar(b) for b in lista_de_bits], chunksize=1)
        av = self._um_local()
        return [av.medir(b) for b in lista_de_bits]

    def medir_l2(self, lista_de_bits):
        self.medidos += len(lista_de_bits)
        if self._pool is not None:
            return self._pool.map(_medir_l2_no_processo, [np.asarray(b, np.uint8) for b in lista_de_bits], chunksize=1)
        av = self._um_local()
        return [av.medir_l2(b) for b in lista_de_bits]

    def fechar(self):
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None
FONTES_NOVAS = ('desafio_v.py', 'vidas_do_ser.py', 'trilhas_do_ser.py', 'agentes_do_ser.py', 'metricas_do_ser.py', 'oraculo_do_ser.py', 'nulos_do_ser.py', 'calibrar_v_ser.py', 'desafio_v_ser.py')

def caminhos_dos_oraculos(semente=SEMENTE_DA_VIDA):
    return [DV.caminho_do_oraculo(semente), OS.caminho_ling(semente), OS.caminho_der(semente)]

def hashes_dos_oraculos(semente=SEMENTE_DA_VIDA):
    return {os.path.basename(a): hashlib.sha256(open(a, 'rb').read()).hexdigest() for a in caminhos_dos_oraculos(semente) if os.path.exists(a)}

def hash_de_V():
    h = hashlib.sha256()
    h.update(DV.hash_de_V().encode())
    for n in FONTES_NOVAS:
        h.update(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), n), 'rb').read())
    h.update(repr(CLAUSULAS).encode())
    h.update(repr(sorted(ORIGEM.items())).encode())
    h.update(repr(sorted(((k, v) for k, v in ETA.items()))).encode())
    h.update(repr((R_COMPOE_8, R_COMPOE_32, R_MELHORA, R_LATENCIA, ETA_DERIVA, TEMPO_MAX_PADRAO, VERSAO_DOS_PREDICADOS)).encode())
    for arq in caminhos_dos_oraculos():
        if os.path.exists(arq):
            h.update(open(arq, 'rb').read())
    return h.hexdigest()

def calibrar(**kw):
    from experimentos import calibrar_v_ser as CAL
    return CAL.calibrar(**kw)
