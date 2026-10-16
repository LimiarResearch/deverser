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
import carga_vida
import comum_vida
import metricas_vida
import nucleo_l2 as L2
import oraculo_vida
import simulador_vida
from experimentos import desafio_genoma as G
from experimentos import desafio_memoria as MEM
from experimentos import desafio_oraculo as OR
from experimentos.montar_desafio_motor import D as D_PISO
VERSAO_DOS_PREDICADOS = 3
N_PREDICADOS = 128
ETA = {'r_deficit': 0.11, 'r_deficit_conserva': 0.11, 'r_deficit_aprende': 0.06, 'r_sem_historico_lacuna': 0.02, 'r_sem_historico_estado': 0.02}
CLAUSULAS = [(c['id'], c['teste']['medida'], c['teste']['op'], float(c['teste']['valor']), float(c['teste'].get('escala', 1.0))) for c in D_PISO]
CLAUSULAS += [('r_deficit', 'deficit', '<=', ETA['r_deficit'], 1.0), ('r_deficit_conserva', 'deficit_conserva', '<=', ETA['r_deficit_conserva'], 1.0), ('r_deficit_aprende', 'deficit_aprende', '<=', ETA['r_deficit_aprende'], 1.0)]
CLAUSULAS += [('r_sem_historico_lacuna', 'lacuna_de_memoria', '<=', ETA['r_sem_historico_lacuna'], 1.0), ('r_sem_historico_copias', 'copias_no_estado', '<=', float(MEM.COPIAS_TOLERADAS), 256.0), ('r_sem_historico_estado', 'crescimento_do_estado', '<=', ETA['r_sem_historico_estado'], 1.0)]
IDS = [c[0] for c in CLAUSULAS]
N_CLAUSULAS = len(CLAUSULAS)
N_PISO = len(D_PISO)
ORIGEM = {c['id']: ('G', 'o piso de 28 e 29/09, derivado do texto da intenção (montar_desafio_motor.DERIVACOES)') for c in D_PISO}
ORIGEM['r_memoria_fixa'] = ('E', 'memória limitada: os 64 KiB são escolha da IA (29/09), para a confirmação do responsável; a intenção não dá o tamanho e ele não se apoia no de nenhum método')
ORIGEM.update({'r_deficit': ('I+R', 'sem reiniciar o treinamento a cada habilidade nova, sem perder as habilidades anteriores: o valor é 0 (a intenção) e a tolerância é a variação entre dois recomeços (a resolução de V)'), 'r_deficit_conserva': ('I+R', 'sem perder as habilidades anteriores: o déficit nas tarefas treinadas há tempo é 0, com a tolerância medida entre dois recomeços'), 'r_deficit_aprende': ('I+R', 'aprenda operando: o déficit na tarefa treinada agora é 0, com a tolerância medida entre dois recomeços'), 'r_sem_historico_lacuna': ('I+R+E', "sem guardar todo o histórico: acertar os exemplos de muito tempo atrás igual aos novos (lacuna 0, a intenção), com a tolerância do ruído da amostra (a resolução de V); 'muito tempo atrás' = mais de 5000 exemplos (escolha da IA)"), 'r_sem_historico_copias': ('I+E', 'sem guardar todo o histórico: nenhum vetor do estado é cópia de uma entrada velha (a intenção); um lote de trabalho de até 16 cópias, de exemplos com mais de 256 de idade, passa (escolha da IA)'), 'r_sem_historico_estado': ('I+E', 'sem guardar todo o histórico e com memória limitada: o estado lógico não cresce com a vida (a intenção), com a folga de 2% (escolha da IA)')})
ORIGENS_VALIDAS = ('I', 'R', 'G', 'E', 'I+R', 'I+E', 'I+R+E')
NIVEIS = ['piso'] * N_PISO + ['ser'] * (N_CLAUSULAS - N_PISO)
POR_VIDA = ('esquecimento', 'ganho_sobre_majoritaria', 'acc_final', 'plasticidade', 'ganho_de_composicao', 'correcao', 'regra_antiga', 'conflito_depois_de_refutacao', 'calibracao', 'investigar_nas_nao_vistas', 'transformacao_ativa')
DEFICITS = ('deficit', 'deficit_conserva', 'deficit_aprende', 'deficit_revisa')
CLASSES = ('cumpre D', 'a 1 cláusula de D', '2 a 3 cláusulas', '4 a 6 cláusulas', '7 a 12 cláusulas', 'sem classe (estouro, erro ou oráculo)')
DIST_MAX = 1000 * N_CLAUSULAS + 1
SEMENTE_DA_VIDA = 1
BACKENDS_DO_SER = ('numpy', 'cpp')
BACKEND_DO_SER = os.environ.get('SER_BACKEND', 'numpy')

def definir_backend(nome):
    global BACKEND_DO_SER
    if nome not in BACKENDS_DO_SER:
        raise ValueError(f'backend desconhecido: {nome} (vale {BACKENDS_DO_SER})')
    BACKEND_DO_SER = nome
    os.environ['SER_BACKEND'] = nome
TEMPO_MAX_PADRAO = 90.0
FONTES_DE_V = ('carga_vida.py', 'comum_vida.py', 'metricas_vida.py', 'oraculo_vida.py', 'nucleo_l2.py', 'simulador_vida.py')
CLASSES_DE_CLAUSULAS = 'piso e ser'

class Estouro(Exception):
    pass

def gerar_vidas(semente=SEMENTE_DA_VIDA):
    a, b = (carga_vida.gerar_carga(semente), carga_vida.gerar_carga(semente + 1))
    a['fluxos'] = a['fluxos'] + b['fluxos']
    return a

def _zerar(entrada):
    for f in entrada['fluxos']:
        av = f['_avaliacao']
        reg = av.abrir()['registro']
        reg['aberturas'], reg['completos'] = (0, 0)
        av.__dict__['lido'] = False

class _Guarda:

    def __init__(self, interno, limite, contagem):
        self._a, self._limite, self._c = (interno, limite, contagem)

    def aprender(self, x, y):
        self._c[0] += 1
        if self._c[0] & 255 == 0 and time.time() > self._limite:
            raise Estouro()
        self._a.aprender(x, y)

    def aprender_varios(self, X, Y):
        self._c[0] += len(Y)
        if time.time() > self._limite:
            raise Estouro()
        if hasattr(self._a, 'aprender_varios'):
            self._a.aprender_varios(X, Y)
        else:
            for x, y in zip(X, Y):
                self._a.aprender(x, y)

    def prever(self, X):
        return self._a.prever(X)

    def __getattr__(self, nome):
        if nome == 'episodio' and hasattr(self.__dict__.get('_a'), 'episodio'):
            return self.__dict__['_a'].episodio
        raise AttributeError(nome)

    def estado(self):
        return self._a.estado()

    def diagnostico(self):
        return self._a.diagnostico()

    def flops_por_interacao(self):
        f = getattr(self._a, 'flops_por_interacao', None)
        return None if f is None else f()

def executar(entrada, prog, tempo_max=TEMPO_MAX_PADRAO, sondas_mem=None):
    p = L2.normalizar(prog)
    limite, contagem = (time.time() + float(tempo_max), [0])
    t0 = time.time()
    saida = MEM.rodar_com_memoria(entrada, lambda d, c, r: _Guarda(L2._P(d, c, r, p), limite, contagem), lambda b, d, c: _Guarda(L2._P.restaurar(b, d, c), limite, contagem), sondas_mem)
    return (saida, time.time() - t0)

def executar_ser(entrada, bits, tempo_max=TEMPO_MAX_PADRAO, sondas_mem=None):
    if BACKEND_DO_SER == 'cpp':
        from experimentos import l_ser_cpp as LI
    else:
        from experimentos import l_ser_interp as LI
    fab, rest = LI.fabricar(bits)
    limite, contagem = (time.time() + float(tempo_max), [0])
    t0 = time.time()
    saida = MEM.rodar_com_memoria(entrada, lambda d, c, r: _Guarda(fab(d, c, r), limite, contagem), lambda b, d, c: _Guarda(rest(b, d, c), limite, contagem), sondas_mem)
    return (saida, time.time() - t0)

class AlvoL2:
    nome = 'l2'
    codificacao = G

    @staticmethod
    def executar(entrada, bits, tempo_max, sondas_mem):
        return executar(entrada, G.decodificar(bits), tempo_max, sondas_mem)

class AlvoSer:
    nome = 'ser'

    @property
    def codificacao(self):
        from experimentos import l_ser_lang as LL
        return LL.CODIFICACAO

    @staticmethod
    def executar(entrada, bits, tempo_max, sondas_mem):
        return executar_ser(entrada, bits, tempo_max, sondas_mem)
ALVOS = {'l2': AlvoL2(), 'ser': AlvoSer()}

class _CodificacaoDoModuloL2:
    empacotar = staticmethod(G.empacotar)
    desempacotar = staticmethod(G.desempacotar)
AlvoL2.codificacao = _CodificacaoDoModuloL2()

def detalhe_por_tarefa(f, resp, etq):
    av = f['_avaliacao'].abrir()
    ts, V, pos = (np.asarray(av['tarefa_sonda']), np.asarray(av['verdade']), list(av['sondas_em']))
    base, comps = (av['base'], av['compostas'])
    inicio, refut = ({int(k): v for k, v in av['inicio'].items()}, {int(k): v for k, v in av['refutada_desde'].items()})
    R, E = (np.asarray(resp), np.asarray(etq))
    tarefas = sorted(set(ts.tolist()))
    A = np.array([[float(np.mean(R[j][ts == t] == V[j][ts == t])) for t in tarefas] for j in range(len(R))])
    col = {t: i for i, t in enumerate(tarefas)}
    final = A[-1]
    acum, ultimo = (0, {})
    for tipo, t_, n_ in av['segmentos']:
        acum += n_
        if tipo in ('base', 'refutada') and t_ < base:
            ultimo[t_] = acum
    esq, gan, fin = ({}, {}, {})
    for t in range(base):
        desde = refut.get(t, inicio[t])
        js = [j for j, p in enumerate(pos) if p >= desde]
        if not js:
            continue
        pico = float(A[js, col[t]].max())
        apos = [j for j, p in enumerate(pos) if p >= ultimo.get(t, desde) - 1]
        if len(apos) >= 4:
            esq[t] = float(np.mean(A[apos[:2], col[t]]) - np.mean(A[apos[-2:], col[t]]))
        gan[t] = pico - av['majoritaria'][t]
        fin[t] = float(final[col[t]])
    comp = {c: float(final[col[c]]) - av['ref_composta'][c] for c in comps}
    corr, antiga, conflito = ({}, {}, {})
    for t, desde in refut.items():
        antes = [j for j, p in enumerate(pos) if inicio[t] <= p < desde]
        depois = [j for j, p in enumerate(pos) if p >= desde]
        if antes and depois:
            corr[t] = float(A[depois, col[t]].max()) / max(float(A[antes, col[t]].max()), 1e-09)
            m = ts == t
            velha = (V[-1][m] - 1) % 4
            antiga[t] = float(np.mean((R[-1][m] == velha) & (R[-1][m] != V[-1][m])))
            conflito[t] = float(np.mean(E[depois[0]][m] == 2))
    return {'esq': esq, 'gan': gan, 'fin': fin, 'comp': comp, 'corr': corr, 'antiga': antiga, 'conflito': conflito}

def resultado_de_saida(entrada, saida, cpu_s=0.0, com_oraculo=True, orac=None, sondas_mem=None):
    ok, msg = oraculo_vida.conferir(entrada, saida) if com_oraculo else (True, 'sem oráculo (controle)')
    por_vida, det = ([], [])
    memoria_medida = sondas_mem is not None and bool(saida.get('memoria'))
    for k, (f, r, e) in enumerate(zip(entrada['fluxos'], saida['respostas'], saida['etiquetas'])):
        m = metricas_vida._fluxo(f, r, e)
        m.pop('_perfil', None)
        pv = {kk: float(m[kk]) for kk in POR_VIDA}
        d = detalhe_por_tarefa(f, r, e)
        A = OR.acerto_por_sonda(f, r)
        lac, cop, cresc = (float('nan'), 0.0, 0.0)
        if memoria_medida:
            lac = MEM.lacuna_de_memoria(A, MEM.acerto_de_memoria(f, saida['memoria'][k], sondas_mem[k]))
            cop = float(max(saida['copias'][k] or [0.0]))
            tam = saida['tamanho_logico'][k]
            cresc = max(0.0, (tam[-1] - tam[0]) / max(tam[0], 1)) if len(tam) >= 2 else 0.0
        pv['lacuna_de_memoria'] = float(lac) if np.isfinite(lac) else 0.0
        pv['copias_no_estado'] = cop
        pv['crescimento_do_estado'] = float(cresc)
        fl = (saida.get('flops') or [[]] * len(entrada['fluxos']))[k]
        pv['crescimento_da_computacao'] = float(max(0.0, (fl[-1] - fl[0]) / fl[0])) if len(fl) >= 2 and fl[0] > 0 else 0.0
        pv['flops_por_interacao'] = float(fl[-1]) if fl else 0.0
        if orac is not None:
            dfc = OR.deficit(A, orac[k], orac[k]['G'])
            for nome, v in zip(DEFICITS, dfc[:4]):
                pv[nome] = float(v) if np.isfinite(v) else 0.0
            pv['acima_do_oraculo'] = float(dfc[4]) if np.isfinite(dfc[4]) else 0.0
            pv['lacuna_ao_teto'] = OR.lacuna_ao_teto(A, orac[k])
            pv['lacuna_do_recomeco_ao_teto'] = OR.lacuna_ao_teto(orac[k]['O'], orac[k])
            d['deficit_por_tarefa'] = OR.deficits_por_tarefa(A, orac[k])
        else:
            for nome in DEFICITS:
                pv[nome] = 0.0
            pv['acima_do_oraculo'] = 0.0
            pv['lacuna_ao_teto'] = pv['lacuna_do_recomeco_ao_teto'] = 0.0
            d['deficit_por_tarefa'] = {}
        por_vida.append(pv)
        det.append(d)
    fiel = [x for fl in saida['restauracao_fiel'] for x in fl]
    diag = {}
    for d in saida.get('diagnostico', []):
        for k, v in d.items():
            if isinstance(v, (int, float)):
                diag[k] = diag.get(k, 0) + v
    return {'estado': 'ok' if ok else 'oraculo', 'oraculo': bool(ok), 'oraculo_msg': msg, 'cpu_s': float(cpu_s), 'por_vida': por_vida, 'detalhe': det, 'deficit_medido': orac is not None, 'memoria_medida': bool(memoria_medida), 'bytes_de_estado': int(max([b for fl in saida['bytes_por_interrupcao'] for b in fl] or [10 ** 9])), 'restauracao_fiel': float(np.mean(fiel)) if fiel else 0.0, 'usa_informacao_retida': int(any((f['_avaliacao'].lido for f in entrada['fluxos']))), 'divergiu_por_vida': [int(d.get('divergiu', 0)) for d in saida.get('diagnostico', [])] or [0] * len(por_vida), 'diag': {k: float(v) for k, v in diag.items()}}

def _pior(vals, op):
    return max(vals) if op in ('<=', '==') else min(vals)

def valores_das_clausulas(res):
    out = []
    for cid, medida, op, lim, esc in CLAUSULAS:
        if medida in ('usa_informacao_retida', 'bytes_de_estado', 'restauracao_fiel'):
            out.append(float(res[medida]))
        else:
            out.append(float(_pior([v[medida] for v in res['por_vida']], op)))
    return out

def violacoes(valores):
    out = []
    for (cid, medida, op, lim, esc), v in zip(CLAUSULAS, valores):
        if op == '<=':
            f = max(0.0, v - lim)
        elif op == '>=':
            f = max(0.0, lim - v)
        else:
            f = abs(v - lim)
        out.append(f / esc)
    return out

def violacoes_de_coluna(i, v):
    cid, medida, op, lim, esc = CLAUSULAS[i]
    v = np.asarray(v, np.float64)
    if op == '<=':
        f = np.maximum(0.0, v - lim)
    elif op == '>=':
        f = np.maximum(0.0, lim - v)
    else:
        f = np.abs(v - lim)
    return f / esc

def classe_da_distancia(nfal, estado='ok'):
    if estado != 'ok':
        return len(CLASSES) - 1
    if nfal == 0:
        return 0
    if nfal == 1:
        return 1
    if nfal <= 3:
        return 2
    if nfal <= 6:
        return 3
    return 4

def _nomes_dos_predicados():
    nomes = [f'falha:{c}' for c in IDS]
    nomes += [f'longe:{c}' for c in IDS]
    nomes += [f'esqueceu:t{t}' for t in range(12)]
    nomes += [f'nao_aprendeu:t{t}' for t in range(12)]
    nomes += [f'nao_compoe:c{c}' for c in range(3)]
    nomes += [f'nao_corrigiu:r{r}' for r in range(3)]
    nomes += [f'regra_antiga:r{r}' for r in range(3)]
    nomes += [f'sem_conflito:r{r}' for r in range(3)]
    nomes += [f'vida_ruim:v{v}' for v in range(4)]
    nomes += [f'divergiu:v{v}' for v in range(4)]
    nomes += ['estado_grande', 'nao_fiel', 'leu_o_cofre', 'estouro_de_tempo']
    nomes += [f'deficit_alto:t{t}' for t in range(12)]
    return nomes
NOMES_DOS_PREDICADOS = _nomes_dos_predicados()
N_DEFINIDOS = len(NOMES_DOS_PREDICADOS)
N_DURAS = N_CLAUSULAS
_IDX = {n: i for i, n in enumerate(NOMES_DOS_PREDICADOS)}

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
        return _inteiro(bits)
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
    return _inteiro(bits)

def _inteiro(bits):
    v = 0
    for i, b in enumerate(bits):
        if b:
            v |= 1 << i
    return v

def julgar(res):
    estado = res['estado']
    if estado != 'ok':
        return {'estado': estado, 'valores': [float('nan')] * N_CLAUSULAS, 'violacoes': [1.0] * N_CLAUSULAS, 'distancia': DIST_MAX, 'nfal': N_CLAUSULAS, 'classe': classe_da_distancia(N_CLAUSULAS, estado), 'comportamento': comportamento(res, [1.0] * N_CLAUSULAS, estado), 'cpu_s': float(res.get('cpu_s', 0.0)), 'bytes': int(res.get('bytes_de_estado', 0))}
    vals = valores_das_clausulas(res)
    viol = violacoes(vals)
    nfal = sum((1 for v in viol if v > 1e-09))
    return {'estado': 'ok', 'valores': vals, 'violacoes': viol, 'distancia': int(round(1000.0 * sum((min(v, 1.0) for v in viol)))), 'nfal': nfal, 'classe': classe_da_distancia(nfal), 'comportamento': comportamento(res, viol, 'ok'), 'cpu_s': float(res['cpu_s']), 'bytes': int(res['bytes_de_estado'])}

class AvaliadorReal:

    def __init__(self, semente=SEMENTE_DA_VIDA, tempo_max=TEMPO_MAX_PADRAO, com_deficit=True, alvo='l2', backend=None):
        if backend is not None:
            definir_backend(backend)
        self.semente, self.tempo_max, self.alvo = (int(semente), float(tempo_max), ALVOS[alvo])
        self.entrada = gerar_vidas(self.semente)
        self.orac = OR.oraculo_das_vidas(self.entrada, caminho_do_oraculo(self.semente)) if com_deficit else None
        self.sondas_mem = [MEM.montar_sondas_de_memoria(f) for f in self.entrada['fluxos']]

    def medir(self, bits):
        _zerar(self.entrada)
        try:
            saida, dt = self.alvo.executar(self.entrada, np.asarray(bits, np.uint8), self.tempo_max, self.sondas_mem)
        except Estouro:
            return {'estado': 'estouro', 'oraculo': True, 'cpu_s': self.tempo_max}
        except Exception as e:
            return {'estado': 'erro', 'oraculo': True, 'cpu_s': 0.0, 'erro': repr(e)[:200]}
        return resultado_de_saida(self.entrada, saida, dt, True, self.orac, self.sondas_mem)

def caminho_do_oraculo(semente, variante=0):
    return os.path.join(RAIZ, 'experimentos', f"oraculo_vidas_s{int(semente)}{('' if not variante else '_v%d' % int(variante))}.npz")
_PROCESSO = {}

def _iniciar(semente, tempo_max, alvo='l2', backend=None):
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    _PROCESSO['av'] = AvaliadorReal(semente, tempo_max, alvo=alvo, backend=backend)

def _medir_no_processo(pacote):
    return _PROCESSO['av'].medir(_PROCESSO['av'].alvo.codificacao.desempacotar(pacote))

class Avaliacoes:

    def __init__(self, processos=4, semente=SEMENTE_DA_VIDA, tempo_max=TEMPO_MAX_PADRAO, avaliador=None, alvo='l2', backend=None):
        if backend is not None:
            definir_backend(backend)
        self.processos, self.semente, self.tempo_max, self.alvo = (int(processos), int(semente), float(tempo_max), ALVOS[alvo])
        self.avaliador = avaliador
        self._pool = None
        self._local = None
        self.medidos = 0
        if avaliador is None and processos > 0:
            OR.oraculo_das_vidas(gerar_vidas(self.semente), caminho_do_oraculo(self.semente))
            import multiprocessing as mp
            self._pool = mp.get_context('spawn').Pool(processos, initializer=_iniciar, initargs=(self.semente, self.tempo_max, self.alvo.nome, BACKEND_DO_SER))

    def _um_local(self):
        if self.avaliador is not None:
            return self.avaliador
        if self._local is None:
            self._local = AvaliadorReal(self.semente, self.tempo_max, alvo=self.alvo.nome)
        return self._local

    def medir(self, lista_de_bits):
        self.medidos += len(lista_de_bits)
        if self._pool is not None:
            return self._pool.map(_medir_no_processo, [self.alvo.codificacao.empacotar(b) for b in lista_de_bits], chunksize=1)
        av = self._um_local()
        return [av.medir(b) for b in lista_de_bits]

    def fechar(self):
        if self._pool is not None:
            self._pool.close()
            self._pool.join()
            self._pool = None

def hash_de_V():
    h = hashlib.sha256()
    for n in FONTES_DE_V:
        h.update(open(os.path.join(DES, n), 'rb').read())
    h.update(repr(CLAUSULAS).encode())
    h.update(repr(sorted(ORIGEM.items())).encode())
    h.update(open(os.path.abspath(__file__), 'rb').read())
    h.update(open(os.path.abspath(G.__file__), 'rb').read())
    h.update(open(os.path.abspath(OR.__file__), 'rb').read())
    h.update(open(os.path.abspath(MEM.__file__), 'rb').read())
    h.update(BACKEND_DO_SER.encode())
    for nome in ('foto_atomica.py', 'l_ser_lang.py', 'l_ser_interp.py', 'l_ser_cpp.py', 'l_ser_nucleo.cpp'):
        arq = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome)
        if os.path.exists(arq):
            h.update(open(arq, 'rb').read())
    arq = caminho_do_oraculo(SEMENTE_DA_VIDA)
    if os.path.exists(arq):
        h.update(open(arq, 'rb').read())
    return h.hexdigest()
CONTROLES = {'ideal': {}, 'esquecedor': {'esquece': 0.6}, 'sem_correcao': {'corrige': 0}, 'sem_composicao': {'compoe': 0}, 'descalibrado': {'calibrado': -1}, 'sem_conflito': {'conflito': 0}, 'sem_restauracao': {'fiel': 0}, 'pesado': {'bytes_estado': 10 ** 7}, 'sem_plasticidade': {'plastico': 0}, 'degradante': {'transforma': 0.5}, 'trapaceiro': {'le': 1}, 'nulo': {'acerto': 0.25, 'calibrado': 0, 'conflito': 0}, 'majoritaria': {'majoritaria': 1}}
NEGATIVO = {'r_sem_aviso': 'trapaceiro', 'r_memoria_fixa': 'pesado', 'r_conserva': 'esquecedor', 'r_aprende': 'majoritaria', 'r_plastico_no_fim': 'sem_plasticidade', 'r_corrige': 'sem_correcao', 'r_regra_antiga': 'sem_correcao', 'r_combina': 'sem_composicao', 'r_sabe_o_que_sabe': 'descalibrado', 'r_conflito': 'sem_conflito', 'r_restaura': 'sem_restauracao', 'r_transforma': 'degradante'}
CONTROLES_DE_HISTORICO = {'memorizador': {'memoriza': 0.25}, 'guardador': {'copias': 256.0}, 'crescente': {'cresce': 1.0}}
NEGATIVO.update({'r_sem_historico_lacuna': 'memorizador', 'r_sem_historico_copias': 'guardador', 'r_sem_historico_estado': 'crescente'})
IDS_DEFICIT = ('r_deficit', 'r_deficit_conserva', 'r_deficit_aprende')

def _arredondar_para_cima(x, piso=0.02):
    return np.maximum(piso, np.ceil(np.round(np.asarray(x, np.float64), 6) / 0.01 - 1e-09) * 0.01)

def calibrar(entrada=None, orac=None, outros=None, sondas_mem=None):
    entrada = entrada or gerar_vidas()
    orac = orac if orac is not None else OR.oraculo_das_vidas(entrada, caminho_do_oraculo(SEMENTE_DA_VIDA))
    sondas_mem = sondas_mem or [MEM.montar_sondas_de_memoria(f) for f in entrada['fluxos']]
    out = {'controles': {}, 'clausulas': {}, 'degenerados': {}, 'deficit': {}, 'historico': {}, 'ok': True}
    veredito = {}

    def julgar_simulado(saida, cpu=0.0, **memoria):
        MEM.simular_memoria(entrada, saida, sondas_mem, **memoria)
        return julgar(resultado_de_saida(entrada, saida, cpu, com_oraculo=False, orac=orac, sondas_mem=sondas_mem))
    for nome, params in CONTROLES.items():
        _zerar(entrada)
        t0 = time.time()
        saida = simulador_vida.executar(entrada, **dict(params, semente=1))
        veredito[nome] = julgar_simulado(saida, time.time() - t0, semente=1)
        out['controles'][nome] = {'nfal': veredito[nome]['nfal'], 'reprovadas': [IDS[i] for i, v in enumerate(veredito[nome]['violacoes']) if v > 1e-09]}
    for nome, extra in CONTROLES_DE_HISTORICO.items():
        _zerar(entrada)
        saida = simulador_vida.executar(entrada, semente=1)
        veredito[nome] = julgar_simulado(saida, 0.0, semente=1, **extra)
        out['controles'][nome] = {'nfal': veredito[nome]['nfal'], 'reprovadas': [IDS[i] for i, v in enumerate(veredito[nome]['violacoes']) if v > 1e-09]}
    if veredito['ideal']['nfal'] != 0:
        out['ok'] = False
    for cid, neg in NEGATIVO.items():
        i = IDS.index(cid)
        pos_ok = veredito['ideal']['violacoes'][i] <= 1e-09
        neg_ok = veredito[neg]['violacoes'][i] > 1e-09
        out['clausulas'][cid] = {'positivo_cumpre': bool(pos_ok), 'negativo': neg, 'negativo_reprova': bool(neg_ok)}
        if not (pos_ok and neg_ok):
            out['ok'] = False
    for nome in ('nulo', 'majoritaria'):
        out['degenerados'][nome] = {'cumpre_D': veredito[nome]['nfal'] == 0}
        if veredito[nome]['nfal'] == 0:
            out['ok'] = False

    def deficits_de(saida):
        _zerar(entrada)
        r = resultado_de_saida(entrada, saida, 0.0, com_oraculo=False, orac=orac)
        return ([max((pv[n] for pv in r['por_vida'])) for n in DEFICITS], julgar(r))
    ruido = np.asarray([deficits_de(OR.simular_do_oraculo(entrada, orac, fator=1.0, esquece=0.0, semente=sem))[0] for sem in range(1, 6)])
    esq4, ve = deficits_de(OR.simular_do_oraculo(entrada, orac, fator=1.0, esquece=0.3, semente=1))
    if outros is None:
        outros = [OR.oraculo_das_vidas(entrada, caminho_do_oraculo(SEMENTE_DA_VIDA, v), variante=v) for v in range(1, 9) if os.path.exists(caminho_do_oraculo(SEMENTE_DA_VIDA, v))]
    assert outros, 'falta ao menos um segundo recomeço (a variante 1 do oráculo)'
    var = np.concatenate([OR.variacao_entre_recomecos(orac, o) for o in outros])
    por_recomeco = var.reshape(len(outros), len(entrada['fluxos']), 4).max(1)
    n3 = len(IDS_DEFICIT)
    eta = np.asarray([ETA[c] for c in IDS_DEFICIT])
    medido = np.maximum(por_recomeco.max(0)[:n3], ruido.max(0)[:n3])
    regra = por_recomeco.mean(0) + 3 * por_recomeco.std(0)
    pos_ok = bool((medido <= eta + 1e-12).all() and (_arredondar_para_cima(regra[:n3]) <= eta + 1e-12).all())
    esq = np.asarray(esq4)
    neg_ok = bool(ve['violacoes'][IDS.index('r_deficit')] > 1e-09 and ve['violacoes'][IDS.index('r_deficit_conserva')] > 1e-09 and (esq[0] >= 2 * eta[0]) and (esq[1] >= 2 * eta[1]))
    out['deficit'] = {'eta': {c: ETA[c] for c in IDS_DEFICIT}, 'eta_pela_regra (media + 3 desvios dos recomeços, para cima em 0,01)': dict(zip(DEFICITS, _arredondar_para_cima(regra).tolist())), 'media_e_desvio_dos_recomecos [total, conserva, aprende, revisa]': [np.round(por_recomeco.mean(0), 4).tolist(), np.round(por_recomeco.std(0), 4).tolist()], 'pior_das_vidas_de_cada_recomeco [variantes, 4]': np.round(por_recomeco, 4).tolist(), 'ruido_do_positivo (media, maximo por parte)': [np.round(ruido.mean(0), 4).tolist(), np.round(ruido.max(0), 4).tolist()], 'positivo_cumpre': pos_ok, 'esquecedor_de_0,3 [total, conserva, aprende, revisa]': np.round(esq, 4).tolist(), 'negativo_reprova': neg_ok, 'recomecos_medidos': len(outros)}
    if not (pos_ok and neg_ok):
        out['ok'] = False
    lac = []
    for sem in range(1, 17):
        _zerar(entrada)
        saida = simulador_vida.executar(entrada, semente=sem)
        MEM.simular_memoria(entrada, saida, sondas_mem, memoriza=0.0, semente=sem)
        r = resultado_de_saida(entrada, saida, 0.0, com_oraculo=False, orac=None, sondas_mem=sondas_mem)
        lac.append(max((pv['lacuna_de_memoria'] for pv in r['por_vida'])))
    _zerar(entrada)
    saida = simulador_vida.executar(entrada, semente=1)
    MEM.simular_memoria(entrada, saida, sondas_mem, memoriza=0.25, semente=1)
    rm = resultado_de_saida(entrada, saida, 0.0, com_oraculo=False, orac=None, sondas_mem=sondas_mem)
    lac_mem = max((pv['lacuna_de_memoria'] for pv in rm['por_vida']))
    eta_l = ETA['r_sem_historico_lacuna']
    pos_l = bool(max(lac) <= eta_l + 1e-12)
    neg_l = bool(lac_mem >= 2 * eta_l)
    out['historico'] = {'eta_da_lacuna': eta_l, 'eta_da_lacuna_medido_e_arredondado': float(_arredondar_para_cima(max(lac))), 'lacuna_media_e_desvio': [round(float(np.mean(lac)), 4), round(float(np.std(lac)), 4)], 'lacuna_do_positivo (16 sorteios, pior das vidas)': np.round(lac, 4).tolist(), 'lacuna_do_memorizador_de_0,25': round(float(lac_mem), 4), 'positivo_cumpre': pos_l, 'negativo_reprova_com_folga': neg_l}
    if not (pos_l and neg_l):
        out['ok'] = False
    av = AvaliadorReal.__new__(AvaliadorReal)
    av.semente, av.tempo_max, av.entrada, av.orac, av.sondas_mem, av.alvo = (SEMENTE_DA_VIDA, TEMPO_MAX_PADRAO, entrada, orac, sondas_mem, ALVOS['l2'])
    v = julgar(av.medir(G.codificar(L2.referencias()['sgd'])))
    out['degenerados']['sgd_simples'] = {'cumpre_D': v['nfal'] == 0, 'clausulas_que_cumpre': N_CLAUSULAS - v['nfal']}
    if v['nfal'] == 0:
        out['ok'] = False
    return out
