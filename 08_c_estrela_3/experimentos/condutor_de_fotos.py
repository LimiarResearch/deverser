# -*- coding: utf-8 -*-
import hashlib
import json
import math
import os
import time
import numpy as np
from collections import deque
from experimentos import aprendiz_de_fotos as AP
from experimentos import arquivo_de_fotos as AF
from experimentos import catraca_do_motor as CM
from experimentos import colheita_de_sementes as CS
from experimentos import contabilidade_de_v as CV
from experimentos import escritor_de_fotos as EF
from experimentos import nivel3b_meta as M
from experimentos import sementes_de_fotos as SF
VERSAO_DO_CONDUTOR = '4.3.1'
BRACOS = ('aprendida', 'cega', 'operador')
ORIGEM_DO_BRACO = {'aprendida': 'escrita_aprendida', 'fria': 'escrita_fria', 'cega': 'escrita_cega', 'operador': 'operador', 'piscina': 'piscina', 'evo': 'evo', 'cega_gemea': 'escrita_cega'}
GEMEOS = {'cega_gemea': 'cega'}
OPERACOES_DA_REGRA = ('classificar', 'guardar todas (sem liberar nenhuma)', 'guardar o padrão', 'escrever bit a bit', 'saber o que a sequência significa', 'aprender com o tempo')

class Config:
    semente = 1
    K = 10
    bracos = BRACOS
    n_partida = 64
    k_melhores = 200
    escala_do_posto = 12.0
    politica_do_pai = 'posto'
    niveis_k = 8
    niveis_q = 0.6
    persistencia_do_pai = 0
    torneio_populacao = 64
    torneio_tamanho = 8
    evo_populacao = 64
    evo_torneio = 8
    estagnacao_rodadas = 15
    prioridade_em_niveis = ()
    prioridade_clausulas = None
    rotulo_por_d = False
    rotulo_w = 10.0
    rotulo_lambda = 2.0
    pai_sem_clones = False
    doadoras_de_corridas = ()
    doadoras_por_geracao = 4
    prioridade_clausula = None
    eixo = ()
    graus_do_eixo = ('C', 'B')
    colheita_sem_clones = False
    testemunhas_doadoras = False
    aprendiz_pela_prioridade = False
    peso_da_prioridade_no_aprendiz = 100.0
    progresso_pela_prioridade = False
    pais_por_rodada = 1
    torneio_sem_limite_de_tentativas = False
    frac_acaso = 0.25
    max_tentativas_por_pai = 6
    rodadas_por_geracao = 5
    treino_passos = 25
    aquecimento_piscinas = 10
    coletor_fracao = 0.0
    coletor_vidas = 3
    piscinas_por_geracao = 1
    banco_fracao = 0.5
    troca_cada = 8
    minimo_dev = 20
    minimo_ret = 10
    motivos_cada = 20
    diagnostico_cada = 120
    plato_rodadas = 60
    max_reinicios = 2
    minimo_para_diagnosticar_L = 2000
    tempo = None
    max_rodadas = 0
    salvar_cada = 300.0
    declaracao_cada = 300.0
    imprimir_cada = 60.0
    regra_min_fotos = 1000
    regra_min_escritas = 200
    escritor = {'pool': 384, 'k_modelo': 8, 'k_cega': 2, 'min_memoria': 800, 'teto_memoria': 150000, 'piscina_m': 16, 'peso_semantico': 0.5, 'membros': 5, 'reducao': 1.0}
    treino_lote = 128
    n_levantamento = 192
    passos_da_intencao = 100
    blocos_da_intencao = 10
    m_candidatos_pai = 8
    p_desacordo = 0.5
    autoimitacao_cada = 4
    sementes_cada = 20
    moldes_por_lote_de_sementes = 2
    sementes_por_fonte = 2
    sementes_passos_de_remendo = 3
    sementes_edicoes_por_passo = 6
    sementes_no_reinicio = True
    colheita_por_clausula = 16
    catraca_cada = 30
    catraca_pares_dev = 24
    catraca_pares_confirmacao = 12
    catraca_min_fotos = 300
    confirmacao_um_em = 64
    remedir_estouro = 1
    final_um_em = 32
    final_pares = 48
    leitura_final = True
    mapa_por_assinatura = False
    mapa_assinatura = 'experimentos.mapa_de_assinaturas:assinatura_ativa_do_ser'
    mapa_pilares = ('RETRO', 'W_OCULTA')
    mapa_peso_pilar = 4.0
    mapa_p_molde = 0.25
    mapa_doadoras = 4
    mapa_processos = 1
    v2_nivel_decisao = 0
    v2_epoca_geracoes = 10
    v2_elite = 16
    lixo_muito_pior = CV.MUITO_PIOR_PADRAO

    def __init__(self, **kw):
        for k, v in kw.items():
            if not hasattr(Config, k):
                raise TypeError(f'configuração desconhecida: {k}')
            setattr(self, k, v)

    def para_json(self):
        return {k: list(v) if isinstance(v, tuple) else v for k in dir(Config) if not k.startswith('_') and k != 'para_json' for v in [getattr(self, k)]}

def _gravar(caminho, obj):
    tmp = caminho + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=_json_padrao)
    os.replace(tmp, caminho)

def _json_padrao(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (set, tuple)):
        return list(x)
    return str(x)

def cfg_catraca(corrida):
    return bool(corrida.cfg.catraca_cada)

def _erro_padrao_pareado(d):
    d = np.asarray(d, np.float64)
    return float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else float('nan')

def _veredito_da_diferenca(dif, ep):
    if not math.isfinite(ep):
        return 'sem dados'
    if dif + 2 * ep < 0:
        return 'ganho'
    if dif - 2 * ep > 0:
        return 'pior'
    return 'nulo'

class Corrida:

    def __init__(self, problema, avaliador, saida, config=None, testemunhas=None, ok_de_gabriel=None, modo='corrida'):
        self.problema, self.avaliador, self.saida = (problema, avaliador, saida)
        self.cfg = config or Config()
        self.v2 = int(self.cfg.v2_nivel_decisao) > 1
        if self.v2 and (not hasattr(avaliador, 'piscina')):
            raise ValueError('v2_nivel_decisao pede a V da busca v2 (`c3_v_da_busca.AvaliacoesV2`)')
        self.sal, self.confirmadas, self.margens = (0, set(), {})
        self.populacao = deque(maxlen=max(1, int(self.cfg.torneio_populacao)))
        if int(self.cfg.pais_por_rodada) > 1 and self.cfg.persistencia_do_pai:
            raise ValueError('a persistência do pai vale só com um pai por rodada (pais_por_rodada = 1)')
        self.testemunhas = testemunhas or {}
        self.ok_de_gabriel, self.modo = (ok_de_gabriel, modo)
        self.cod = problema.codificacao
        os.makedirs(saida, exist_ok=True)
        os.makedirs(os.path.join(saida, 'fotos'), exist_ok=True)
        self.t0 = time.time()
        self.seg_anteriores = 0.0
        self.g = np.random.default_rng(self.cfg.semente * 7919)
        self.fotos = AF.ArquivoDeFotos.carregar(os.path.join(saida, 'fotos'), problema, semente=self.cfg.semente)
        self.edicoes = AF.Edicoes.carregar(os.path.join(saida, 'edicoes'))
        self.escritor = AP.AprendizDeFotos(problema, self.fotos, semente=self.cfg.semente, **self.cfg.escritor)
        if self.cfg.aprendiz_pela_prioridade:
            if not self._indices_da_prioridade():
                raise ValueError('o aprendiz pela prioridade pede a prioridade_clausula ou as prioridade_clausulas')
            if self.cfg.rotulo_por_d:
                raise ValueError('o aprendiz pela chave e o rótulo por D são duas formas do mesmo rótulo: uma de cada vez')
            if self.cfg.prioridade_em_niveis:
                raise ValueError('o aprendiz pela chave soma a violação à distância; com a prioridade em níveis ela não é uma violação só')
            self._embrulhar_o_aprendiz()
        self.colheita = CS.Colheita(problema, self.cfg.colheita_por_clausula, sem_clones=self.cfg.colheita_sem_clones)
        self.mapa = None
        if self.cfg.mapa_por_assinatura:
            from experimentos.mapa_de_assinaturas import MapaDeAssinaturas
            self.mapa = MapaDeAssinaturas(self.cfg.mapa_assinatura, self.cfg.mapa_pilares, self.cfg.mapa_peso_pilar, processos=self.cfg.mapa_processos, pasta=saida)
        self.retomada = False
        self.rodada_n = 0
        self.geracao = 0
        self.reinicios = 0
        self.plato = 0
        self.melhor = None
        self.so_doadoras = set()
        self._doadoras_vistas = set()
        self._fila_de_fora = []
        self._pedacos_de_fora = {}
        self._comportamentos_de_fora = set()
        self.melhor_chave = None
        self.parada = None
        self.tentativas = {}
        self.pai_persistente, self.rodadas_sem_melhora_do_pai = (None, 0)
        self.braco = {}
        self.gerador_evo = None
        self.melhor_por_rodada = []
        self.curva_do_escritor = []
        self.curva_da_melhor = []
        self.eventos = []
        self.contadores = {'rodadas': 0, 'avaliacoes_de_V': 0, 'candidatas_do_arquivo': 0, 'pais_por_distancia_a_D': 0, 'pais_ao_acaso': 0, 'pais_por_desacordo': 0, 'pais_persistentes': 0, 'piscinas_rotuladas': 0, 'reinicios': 0, 'integridade_falhas': 0, 'auditorias': 0, 'erros_na_declaracao_parcial': 0, 'erros_nos_padroes': 0, 'candidatas_que_cumprem_D': 0, 'consultas_das_testemunhas': 0}
        self.politicas = {}
        self.alocacao_por_desacordo = False
        self.alocacao_teste = None
        self.alocacao_testes = {'feitos': 0, 'abertos': 0}
        self.sementes = {'lotes': 0, 'moldes': 0, 'fontes': {}, 'por_lote': [], 'no_reinicio': {'aprendidas': 0, 'sorteadas': 0}, 'caminhos': []}
        self.catraca_est = {'propostas': 0, 'adotadas': 0, 'recusadas_porta': 0, 'recusadas_confirmacao': 0, 'recusadas_integridade': 0, 'puladas': 0, 'voltas': 0, 'pares_dev': 0, 'pares_conf': 0}
        self.H_cfg = []
        self.cfg_anterior = None
        self.cfg_inicial = dict(self.escritor.config_de_escrita)
        self.espaco_cfg = CM.espaco_a_partir_de(self.escritor.config_de_escrita, self.escritor.total_avaliado)
        self.meta_cfg = CM.MetaDeConfig(self.espaco_cfg)
        self.selo_inicial = None
        self.migracao_do_hash = None
        self.migracoes_do_hash = []
        self.pais_vistos = set()
        self.moldes_de_confirmacao_usados = set()
        self._conf = np.zeros(4096, bool)
        self.confirmacao_um_em_na_partida = None
        self.estouros = {'na_primeira_medida': 0, 'dos_quais_em_lote': 0, 'remedidas_sozinhas': 0, 'recuperadas': 0, 'confirmadas': 0, 'remedidas_na_auditoria': 0}
        self.gasto_de_V = CV.GastoDeV()
        self.lixo = CV.LixoDasEdicoes(self.cfg.lixo_muito_pior)
        self.alarme_de_lixo = False
        self._final = np.zeros(4096, bool)
        self.leitura_final_feita = None
        self._ultima_leitura_final = None
        self.levantamento = None
        self.hash_de_v = None
        self.calibracao = None
        self.selo_do_banco = None
        self.hashes_dos_oraculos = None
        self.testemunhas_medidas = {}
        self._t_salvar = time.time()
        self._t_declaracao = 0.0
        self._t_imprimir = 0.0
        self._consultas_da_sessao = 0
        self.log_r = open(os.path.join(saida, 'log_rodadas.jsonl'), 'a', encoding='utf-8')
        self.log_e = open(os.path.join(saida, 'log_eventos.jsonl'), 'a', encoding='utf-8')
        self.log_t = open(os.path.join(saida, 'traco.jsonl'), 'a', encoding='utf-8')
        self.pais_da_ultima_rodada = []
        self.coletor = None
        if float(getattr(self.cfg, 'coletor_fracao', 0.0)) > 0:
            if not self.v2:
                raise ValueError('o coletor de intervenções pede a V v2 (as vidas pareadas)')
            from experimentos.coletor_de_intervencoes import Coletor
            self.coletor = Coletor(self, self.cfg.coletor_fracao, self.cfg.coletor_vidas)

    def segundos(self):
        return self.seg_anteriores + (time.time() - self.t0)

    def _traco(self, obj):
        try:
            self.log_t.write(json.dumps(dict(obj, t=round(self.segundos(), 1), rodada=self.rodada_n, geracao=self.geracao), ensure_ascii=False, default=_json_padrao) + '\n')
            self.log_t.flush()
        except (OSError, ValueError, AttributeError):
            pass

    def _evento(self, obj):
        obj = dict(obj, t=round(self.segundos(), 1), rodada=self.rodada_n)
        self.eventos.append(obj)
        self.log_e.write(json.dumps(obj, ensure_ascii=False, default=_json_padrao) + '\n')
        self.log_e.flush()

    def _pedir_a_V(self, lista_de_bits, finalidade, nivel=1):
        if self.mapa is not None and finalidade != CV.FINALIDADE_TESTEMUNHAS:
            self.mapa.antecipar(lista_de_bits)
        t0_v = time.time()
        if self.v2:
            res = self.avaliador.medir(lista_de_bits, sal=self.sal, nivel=nivel)
            n_medidas = len(lista_de_bits) * max(1, int(nivel))
        else:
            res = self.avaliador.medir(lista_de_bits)
            n_medidas = len(lista_de_bits)
        self.gasto_de_V.contar(finalidade, n_medidas)
        self._consultas_da_sessao += n_medidas
        if finalidade == CV.FINALIDADE_TESTEMUNHAS:
            self.contadores['consultas_das_testemunhas'] += n_medidas
        else:
            self.contadores['avaliacoes_de_V'] += n_medidas
        self._traco({'tipo': 'V', 'finalidade': finalidade, 'fotos': len(lista_de_bits), 'nivel': int(nivel), 'sal': int(getattr(self, 'sal', 0)), 'medidas': int(n_medidas), 'segundos': round(time.time() - t0_v, 2), 'por_trabalhador': list(getattr(self.avaliador, 'por_trabalhador', []) or [])})
        return res

    def _pedir_a_V_nas_vidas(self, lista_de_bits, vidas, finalidade):
        t0_v = time.time()
        av = self.avaliador
        if hasattr(av, 'medir_nas_vidas'):
            res = av.medir_nas_vidas(lista_de_bits, vidas)
        else:
            pend = [[av._enviar(int(s), int(sp), b) for s, sp in vidas] for b in lista_de_bits]
            res = [[a.get() for a in por] for por in pend]
        n_medidas = len(lista_de_bits) * len(vidas)
        self.gasto_de_V.contar(finalidade, n_medidas)
        self._consultas_da_sessao += n_medidas
        self.contadores['avaliacoes_de_V'] += n_medidas
        self.contadores['avaliacoes_do_coletor'] = int(self.contadores.get('avaliacoes_do_coletor', 0)) + n_medidas
        self._traco({'tipo': 'V', 'finalidade': finalidade, 'fotos': len(lista_de_bits), 'nivel': len(vidas), 'sal': int(getattr(self, 'sal', 0)), 'medidas': int(n_medidas), 'segundos': round(time.time() - t0_v, 2), 'por_trabalhador': list(getattr(av, 'por_trabalhador', []) or [])})
        return res

    def _coletar_se_devido(self):
        if self.coletor is None or self.parada or (not self.pais_da_ultima_rodada) or (not self.coletor.devido()):
            return
        try:
            self.coletor.coletar(self.pais_da_ultima_rodada[0])
        except Exception as e:
            self.contadores['erros_no_coletor'] = int(self.contadores.get('erros_no_coletor', 0)) + 1
            self._evento({'evento': 'erro_no_coletor', 'erro': repr(e)[:300]})

    def _confirmar(self, k):
        self._confirmar_varias([k])
        return self.fotos.veredito(int(k))

    def _confirmar_varias(self, ids, finalidade='confirmação v2 (a pior de k)'):
        if not self.v2:
            return
        faltam = list(dict.fromkeys((int(k) for k in ids if int(k) not in self.confirmadas)))
        if not faltam:
            return
        res = self._pedir_a_V([self.fotos.foto(k) for k in faltam], finalidade, nivel=int(self.cfg.v2_nivel_decisao))
        for k, r in zip(faltam, res):
            ver, antes = (self.problema.julgar(r), self.fotos.veredito(k))
            if ver['estado'] != 'ok' or antes['estado'] != 'ok' or ver['distancia'] > antes['distancia']:
                self.fotos.reverificar(k, ver)
            ds = [m['distancia'] for m in r.get('medidas_do_nivel', [])]
            self.margens[k] = float(np.std(ds, ddof=1) / np.sqrt(len(ds))) if len(ds) > 1 else 0.0
            self.confirmadas.add(k)
            self._traco({'tipo': 'confirmacao', 'finalidade': finalidade, 'foto': k, 'antes': int(antes['distancia']), 'medidas': ds, 'guardada': int(self.fotos.veredito(k)['distancia']), 'margem': round(self.margens[k], 1)})
        self.contadores['confirmacoes_v2'] = self.contadores.get('confirmacoes_v2', 0) + len(faltam)

    def _virar_o_sal(self):
        self.sal += 1
        self.confirmadas.clear()
        elite = self.fotos.melhores(int(self.cfg.v2_elite))
        if elite:
            res = self._pedir_a_V([self.fotos.foto(k) for k in elite], 'virada do sal v2 (a elite)', nivel=int(self.cfg.v2_nivel_decisao))
            for k, r in zip(elite, res):
                ver = self.problema.julgar(r)
                self.fotos.reverificar(k, ver)
                ds = [m['distancia'] for m in r.get('medidas_do_nivel', [])]
                self.margens[k] = float(np.std(ds, ddof=1) / np.sqrt(len(ds))) if len(ds) > 1 else 0.0
                self.confirmadas.add(int(k))
            ok = [(self.fotos.veredito(k)['distancia'], int(k)) for k in elite if self.fotos.veredito(k)['estado'] == 'ok']
            if ok:
                self.melhor = min(ok)
        self._evento({'evento': 'virada_do_sal', 'sal': self.sal, 'elite': [int(k) for k in elite], 'melhor': None if self.melhor is None else list(self.melhor)})

    def _medir(self, lista_de_bits, finalidade=CV.FINALIDADE_SEM_ROTULO):
        vers = [None] * len(lista_de_bits)
        pedir, onde = ([], {})
        for i, b in enumerate(lista_de_bits):
            k = self.fotos.buscar(b)
            if k >= 0:
                vers[i] = self.fotos.veredito(k)
                self.contadores['candidatas_do_arquivo'] += 1
                continue
            ch = self.cod.chave(self.cod.canonizar(b))
            if ch in onde:
                onde[ch].append(i)
            else:
                onde[ch] = [i]
                pedir.append((ch, b))
        if pedir:
            res = self._pedir_a_V([b for _, b in pedir], finalidade)
            for (ch, b), r in zip(pedir, res):
                v = self.problema.julgar(r)
                if v['estado'] == 'estouro':
                    v, _ = self._remedir_estouro(b, v, len(pedir), CV.FINALIDADE_REMEDIDA_DO_ESTOURO)
                for i in onde[ch]:
                    vers[i] = v
        return vers

    def _remedir_estouro(self, b, ver, n_do_lote, finalidade, contar=True):
        e = self.estouros if contar else {}
        for chave in ('na_primeira_medida', 'dos_quais_em_lote', 'remedidas_sozinhas', 'recuperadas', 'confirmadas'):
            e.setdefault(chave, 0)
        e['na_primeira_medida'] += 1
        e['dos_quais_em_lote'] += int(n_do_lote > 1)
        for t in range(int(self.cfg.remedir_estouro)):
            e['remedidas_sozinhas'] += 1
            v2 = self.problema.julgar(self._pedir_a_V([b], finalidade)[0])
            if v2['estado'] != 'estouro':
                e['recuperadas'] += 1
                self._evento({'evento': 'estouro_remedido', 'chave': int(self.cod.chave(self.cod.canonizar(b))), 'remedidas': t + 1, 'estado_final': v2['estado'], 'lote_da_primeira_medida': int(n_do_lote), 'finalidade': finalidade})
                return (v2, t + 1)
        if self.cfg.remedir_estouro:
            e['confirmadas'] += 1
            self._evento({'evento': 'estouro_confirmado', 'chave': int(self.cod.chave(self.cod.canonizar(b))), 'remedidas': int(self.cfg.remedir_estouro), 'lote_da_primeira_medida': int(n_do_lote), 'finalidade': finalidade})
        return (ver, int(self.cfg.remedir_estouro))

    def _crescer_final(self, n):
        if n > len(self._final):
            self._final = np.concatenate([self._final, np.zeros(max(n, 2 * len(self._final)) - len(self._final), bool)])
        if n > len(self._conf):
            self._conf = np.concatenate([self._conf, np.zeros(max(n, 2 * len(self._conf)) - len(self._conf), bool)])

    def _mascara_final(self):
        self._crescer_final(len(self.fotos) + 1)
        return self._final[:len(self.fotos)]

    def _mascara_confirmacao(self):
        self._crescer_final(len(self.fotos) + 1)
        return self._conf[:len(self.fotos)]

    def _mascara_reservada(self):
        return self._mascara_final() | self._mascara_confirmacao()

    def _mascara_de_pais(self):
        m = self._mascara_reservada()
        if self.so_doadoras:
            m = np.array(m, bool, copy=True)
            idx = np.fromiter(self.so_doadoras, np.int64)
            m[idx[idx < len(m)]] = True
        return m

    def _do_conjunto_final(self, bits_empacotados):
        um = int(self.cfg.final_um_em)
        if um <= 0:
            return False
        h = int.from_bytes(hashlib.blake2b(np.asarray(bits_empacotados, np.uint8).tobytes(), digest_size=8, person=b'conjunto-final').digest(), 'big')
        return h % um == 0

    def _da_reserva_de_confirmacao(self, bits_empacotados):
        um = int(self.cfg.confirmacao_um_em)
        if um <= 0:
            return False
        h = int.from_bytes(hashlib.blake2b(np.asarray(bits_empacotados, np.uint8).tobytes(), digest_size=8, person=b'molde-confirma').digest(), 'big')
        return h % um == 0

    def _e_semente(self, k):
        return str(AF.ORIGENS[int(self.fotos.origem[int(k)])]).startswith('semente')

    def _reservar_se_final(self, k):
        if k < 0 or self._e_semente(k) or (not self._do_conjunto_final(self.fotos.bits[int(k)])):
            return False
        self._crescer_final(int(k) + 1)
        self._final[int(k)] = True
        self.escritor.marcar_intocada(int(k))
        return True

    def _reservar_se_confirmacao(self, k):
        if k < 0 or self._e_semente(k) or (not self._da_reserva_de_confirmacao(self.fotos.bits[int(k)])):
            return False
        self._crescer_final(int(k) + 1)
        if self._final[int(k)]:
            return False
        self._conf[int(k)] = True
        self.escritor.marcar_intocada(int(k))
        return True

    def _remarcar_finais(self):
        self._final = np.zeros(max(4096, len(self.fotos) + 1), bool)
        self._conf = np.zeros(max(4096, len(self.fotos) + 1), bool)
        for k in range(len(self.fotos)):
            if self._e_semente(k):
                continue
            if self._do_conjunto_final(self.fotos.bits[k]):
                self._final[k] = True
                self.escritor.marcar_intocada(k)
            elif self._da_reserva_de_confirmacao(self.fotos.bits[k]):
                self._conf[k] = True
                self.escritor.marcar_intocada(k)

    def _guardar(self, bits, ver, origem, pai=-1):
        k, nova = self.fotos.adicionar(bits, ver, origem=origem, pai=pai, gen=self.geracao)
        final = bool(nova and self._reservar_se_final(k))
        reservada = final or bool(nova and self._reservar_se_confirmacao(k))
        if nova and ver['estado'] == 'ok':
            if not reservada:
                self.colheita.entrar(k, ver)
                if self.mapa is not None:
                    self.mapa.entrar(k, bits, int(self._chave_de_nivel(np.asarray([k], np.int64))[0]))
            pela_chave = self._avanco_pela_prioridade()
            passa_a_margem = True
            if self.v2 and (self.melhor is None or ver['distancia'] < self.melhor[0]) and (not reservada):
                ver = self._confirmar(k)
                passa_a_margem = self.melhor is None or ver['distancia'] + self.margens.get(int(k), 0.0) < self.melhor[0]
            if self.v2 and (not passa_a_margem):
                self._traco({'tipo': 'recorde_negado', 'foto': int(k), 'distancia': int(ver['distancia']), 'margem': round(self.margens.get(int(k), 0.0), 1), 'melhor': None if self.melhor is None else int(self.melhor[0]), 'origem': origem})
            if passa_a_margem and (self.melhor is None or ver['distancia'] < self.melhor[0]):
                self._traco({'tipo': 'recorde', 'foto': int(k), 'distancia': int(ver['distancia']), 'nfal': int(ver['nfal']), 'origem': origem, 'pai': int(pai), 'margem': round(self.margens.get(int(k), 0.0), 1), 'antes': None if self.melhor is None else int(self.melhor[0]), 'valores': [round(float(x), 4) for x in ver['valores']]})
                self.melhor = (int(ver['distancia']), int(k))
                if not pela_chave:
                    self.plato = 0
                self.curva_da_melhor.append((int(self.contadores['avaliacoes_de_V']), int(ver['distancia'])))
            if pela_chave:
                chave = self._chave_do_veredito(ver)
                if self.melhor_chave is None or chave < self.melhor_chave[0]:
                    self.melhor_chave = (chave, int(k))
                    self.plato = 0
            if ver['nfal'] == 0 and ver['distancia'] == 0:
                self.contadores['candidatas_que_cumprem_D'] += 1
                self._candidata(k, ver)
        return (k, nova)

    def _candidata(self, k, ver):
        bits = self.fotos.foto(k)
        _gravar(os.path.join(self.saida, f'candidata_{k}.json'), {'id': int(k), 'chave': int(self.cod.chave(bits)), 'veredito': {c: ver[c] for c in ('estado', 'distancia', 'nfal', 'classe', 'valores')}, 'bits': ''.join((str(int(x)) for x in bits)), 'espera': 'o Ok_k humano: a corrida não a entrega nem a declara sozinha'})
        self._evento({'evento': 'candidata', 'id': int(k), 'distancia': int(ver['distancia'])})
        if self.parada is None:
            self.parada = 'D cumprido: espera o Ok_k'

    def _registrar(self, pai, pai_id, c, ver, braco, k, etiqueta=None):
        y = self.escritor.registrar(pai, pai_id, c, ver, braco, gen=self.geracao, filho_id=k)
        codigo = EF.CODIGO_DE_BRACO.get(etiqueta or braco, 0)
        dist, comp = (int(ver['distancia']), ver['comportamento'])
        if isinstance(c, SF.Semente) and len(c.passos) > 1:
            for t, (did, p, kk, seq) in enumerate(c.passos):
                self.edicoes.adicionar(pai_id, EF.TIPOS.index('doador'), p, min(kk, 255), seq, k, min(t, 255), dist, comp, codigo, self.geracao)
        else:
            self.edicoes.adicionar(pai_id, EF.TIPOS.index(c.tipo), c.p, min(c.k, 255), c.seq, k, 0, dist, comp, codigo, self.geracao)
        return y

    def _sortear_distintas(self, n):
        chaves_testemunhas = {self.cod.chave(self.cod.canonizar(b)) for b in self.testemunhas.values()}
        novas, vistas = ([], set())
        while len(novas) < n:
            b = self.cod.sortear(self.g)
            ch = self.cod.chave(b)
            assert ch not in chaves_testemunhas, 'uma testemunha saiu no sorteio de partida (a regra da comparação)'
            if ch not in vistas and self.fotos.buscar(b) < 0:
                vistas.add(ch)
                novas.append(b)
        return novas

    def _partida(self):
        novas = self._sortear_distintas(self.cfg.n_partida)
        for b, v in zip(novas, self._medir(novas, 'partida (sorteio)')):
            self._guardar(b, v, 'sorteio')
        self._evento({'evento': 'partida', 'fotos_sorteadas': len(novas), 'menor_distancia': None if self.melhor is None else self.melhor[0]})

    def _levantamento(self):
        cfg = self.cfg
        if cfg.n_levantamento <= 0 and cfg.passos_da_intencao <= 0:
            return None
        novas = self._sortear_distintas(cfg.n_levantamento) if cfg.n_levantamento > 0 else []
        for b, v in zip(novas, self._medir(novas, 'levantamento da intenção (pré-treino)')):
            self._guardar(b, v, 'sorteio')
        reg = self.escritor.treinar_a_intencao(passos=cfg.passos_da_intencao, lote=cfg.treino_lote, blocos=cfg.blocos_da_intencao) if cfg.passos_da_intencao > 0 else {}
        self.levantamento = dict(reg, corpus_do_levantamento=len(novas), fotos_no_arquivo=len(self.fotos))
        self._evento(dict(self.levantamento, evento='levantamento_da_intencao'))
        return self.levantamento

    def _medir_testemunhas(self):
        if not self.testemunhas or self.testemunhas_medidas:
            return
        nomes = list(self.testemunhas)
        res = self._pedir_a_V([self.testemunhas[n] for n in nomes], CV.FINALIDADE_TESTEMUNHAS)
        for n, r in zip(nomes, res):
            v = self.problema.julgar(r)
            remedidas = 0
            if v['estado'] == 'estouro':
                v, remedidas = self._remedir_estouro(self.testemunhas[n], v, len(nomes), CV.FINALIDADE_TESTEMUNHAS, contar=False)
            self.testemunhas_medidas[n] = {k: v[k] for k in ('estado', 'distancia', 'nfal', 'classe', 'valores', 'cpu_s', 'bytes')}
            if remedidas:
                self.testemunhas_medidas[n]['remedidas_do_estouro'] = remedidas
            self.testemunhas_medidas[n]['cumpre_D'] = bool(v['nfal'] == 0 and v['estado'] == 'ok')
        obs = 'só comparação: nenhuma é semente, pai nem fonte de motivo; ficam fora do arquivo de fotos da busca' if not self.cfg.testemunhas_doadoras else 'comparação e (C★2, decisão de 02/10/2026) doadoras da colheita das sementes: entram no arquivo com a origem testemunha_doadora; nunca pai, molde, recorde nem exemplo de treino'
        _gravar(os.path.join(self.saida, 'testemunhas.json'), {'obs': obs, 'medidas': self.testemunhas_medidas})
        self._evento({'evento': 'testemunhas', 'distancias': {n: v['distancia'] for n, v in self.testemunhas_medidas.items()}})

    def _recuperar_doadoras(self):
        n = len(self.fotos)
        if n == 0:
            return
        og = self.fotos.origem[:n]
        cods = [AF.ORIGENS.index(o) for o in ('testemunha_doadora', 'doadora_da_celula')]
        for k in np.flatnonzero(np.isin(og, cods)):
            self.so_doadoras.add(int(k))
        if self.so_doadoras:
            for k in self.so_doadoras:
                self.escritor.marcar_intocada(k)
            self._refazer_o_recorde_sem_doadoras()

    def _refazer_o_recorde_sem_doadoras(self):
        d = self.fotos.distancias()
        ok = np.flatnonzero(d >= 0)
        ok = ok[~np.isin(ok, np.fromiter(self.so_doadoras, np.int64))]
        if len(ok):
            j = int(ok[np.argmin(d[ok])])
            self.melhor = (int(d[j]), j)
            if self._avanco_pela_prioridade():
                ch = self._chave_de_nivel(ok)
                j = int(ok[np.lexsort((d[ok], ch))[0]])
                self.melhor_chave = ((int(ch[ok == j][0] // 10 ** 7), int(d[j])), j)

    def _fotos_de_outra_corrida(self, pasta):
        import glob as _glob
        import zipfile as _zip
        lidos = self._pedacos_de_fora.setdefault(pasta, set())
        out = []
        for nome in sorted((x for x in _glob.glob(os.path.join(pasta, 'fotos', 'fotos_*.npz')) if not x.endswith('.tmp.npz'))):
            if nome in lidos:
                continue
            try:
                with np.load(nome) as z:
                    bits, dist, est = (z['bits'], z['distancia'].astype(np.int64), z['estado'])
                    vals, lo, hi = (z['valores'], z['comp_lo'], z['comp_hi'])
            except (OSError, ValueError, KeyError, EOFError, _zip.BadZipFile):
                break
            lidos.add(nome)
            for i in np.flatnonzero(est == 0):
                comp = (tuple(np.round(np.nan_to_num(vals[i].astype(np.float64), nan=9.9), 6)), int(lo[i]), int(hi[i]))
                out.append((int(dist[i]), comp, self.cod.desempacotar(bits[i])))
        return out

    def _importar_doadoras(self):
        cfg = self.cfg
        if not cfg.doadoras_de_corridas:
            return
        for pasta in cfg.doadoras_de_corridas:
            for d, comp, b in self._fotos_de_outra_corrida(pasta):
                b = self.cod.canonizar(b)
                if b is None:
                    continue
                ch = self.cod.chave(b)
                if ch in self.fotos.chaves:
                    if self.fotos.chaves[ch] in self.so_doadoras:
                        self._comportamentos_de_fora.add(comp)
                    self._doadoras_vistas.add(ch)
                    continue
                if ch in self._doadoras_vistas:
                    continue
                self._doadoras_vistas.add(ch)
                self._fila_de_fora.append((d, ch, comp, b))
        if not self._fila_de_fora:
            return
        self._fila_de_fora.sort(key=lambda t: (t[0], t[1]))
        escolhidas, resto = ([], [])
        for t in self._fila_de_fora:
            if t[1] in self.fotos.chaves:
                continue
            if len(escolhidas) < int(cfg.doadoras_por_geracao) and t[2] not in self._comportamentos_de_fora:
                self._comportamentos_de_fora.add(t[2])
                escolhidas.append(t)
            elif t[2] not in self._comportamentos_de_fora:
                resto.append(t)
        self._fila_de_fora = resto
        if not escolhidas:
            return
        vers = self._medir([t[3] for t in escolhidas], 'doadoras de outra corrida (a célula)')
        entrou = []
        for (d_celula, ch, comp, b), v in zip(escolhidas, vers):
            if v['estado'] != 'ok':
                continue
            k, _nova = self.fotos.adicionar(b, v, origem='doadora_da_celula', pai=-1, gen=self.geracao)
            if k < 0:
                continue
            self.so_doadoras.add(int(k))
            self.escritor.marcar_intocada(k)
            self.colheita.entrar(k, v)
            entrou.append({'id': int(k), 'distancia_na_celula': int(d_celula), 'distancia_aqui': int(v['distancia']), 'violacao_da_prioridade': self._chave_do_veredito(v)[0] if self._indices_da_prioridade() else None})
        self._evento({'evento': 'doadoras_da_celula', 'entraram': entrou, 'na_fila': len(self._fila_de_fora)})

    def _doar_testemunhas(self):
        if not self.cfg.testemunhas_doadoras or not self.testemunhas:
            return
        faltam = []
        for n, b in self.testemunhas.items():
            bc = self.cod.canonizar(b)
            k = self.fotos.buscar(bc)
            if k >= 0:
                self.so_doadoras.add(int(k))
            else:
                faltam.append((n, bc))
        if faltam:
            res = self._pedir_a_V([b for _, b in faltam], CV.FINALIDADE_TESTEMUNHAS)
            for (n, b), r in zip(faltam, res):
                v = self.problema.julgar(r)
                if v['estado'] != 'ok':
                    continue
                k, _nova = self.fotos.adicionar(b, v, origem='testemunha_doadora', pai=-1, gen=self.geracao)
                self.so_doadoras.add(int(k))
                self.colheita.entrar(k, v)
        for k in self.so_doadoras:
            self.escritor.marcar_intocada(k)
        self._refazer_o_recorde_sem_doadoras()
        self._evento({'evento': 'testemunhas_doadoras', 'ids': sorted((int(k) for k in self.so_doadoras)), 'premissa': 'decisão de 02/10/2026: as testemunhas como doadoras da colheita; o resultado só vale cumprindo D inteiro e distinto delas (ganhar delas não basta)'})

    def _ler_o_eixo(self):
        cfg = self.cfg
        if not cfg.eixo:
            return
        from experimentos import elo as EL
        elos = [EL.carregar(p) for p in cfg.eixo]
        ev = {'evento': 'eixo', 'elos': [{'rotulo': e.get('rotulo'), 'D': e['a_intencao_e_o_juiz']['D'], 'selo': e['_selo'][:16], 'cumpriu_D': e['o_resultado']['cumpriu_D']} for e in elos], 'graus': list(cfg.graus_do_eixo)}
        if 'C' in cfg.graus_do_eixo:
            com_pesos = [e for e in elos if '_pesos' in e]
            if com_pesos:
                rel = EL.transplantar(self.escritor, com_pesos[-1])
                ev['transplante'] = {k: rel[k] for k in ('inteiros', 'em_bloco', 'ficaram')}
                ev['transplante_por_tensor'] = rel['por_tensor']
                cfg_esc = (com_pesos[-1].get('_aprendiz') or {}).get('config_de_escrita')
                if cfg_esc:
                    self.escritor.config_de_escrita = dict(cfg_esc)
                self.escritor.pronto_pelo_eixo = True
                self.escritor.treinos = max(1, int(self.escritor.treinos))
        if 'B' in cfg.graus_do_eixo:
            vistos, unicos = (set(), [])
            for e in elos:
                for b in EL.corpos_para(e, self.cod):
                    ch = self.cod.chave(b)
                    if ch not in vistos and self.fotos.buscar(b) < 0:
                        vistos.add(ch)
                        unicos.append(b)
            if unicos:
                for b, v in zip(unicos, self._medir(unicos, 'eixo: os corpos bons dos elos')):
                    self._guardar(b, v, 'corpo_do_eixo')
            ev['corpos_medidos'] = len(unicos)
        self._evento(ev)

    def _livres(self):
        d = self.fotos.distancias()
        ok = np.flatnonzero((d >= 0) & ~self._mascara_de_pais())
        if len(ok) == 0:
            raise RuntimeError('nenhuma foto medida para ser pai')
        livres = [int(i) for i in ok if self.tentativas.get(int(i), 0) < self.cfg.max_tentativas_por_pai]
        if not livres:
            self.tentativas.clear()
            livres = [int(i) for i in ok]
        return livres

    def _pai_por_posto(self, livres):
        cfg = self.cfg
        if cfg.politica_do_pai == 'niveis':
            return self._pai_por_nivel(livres)
        if cfg.politica_do_pai == 'torneio' or (cfg.politica_do_pai == 'estagnacao' and self.plato >= cfg.estagnacao_rodadas):
            pai = self._pai_por_torneio(livres)
            if pai is not None:
                return pai
        reservada = self._mascara_de_pais()
        topo = self._topo_do_posto()
        melhores = [i for i in topo if not reservada[i] and self.tentativas.get(i, 0) < cfg.max_tentativas_por_pai] or livres
        return int(melhores[min(int(self.g.exponential(cfg.escala_do_posto)), len(melhores) - 1)])

    def _topo_do_posto(self):
        cfg = self.cfg
        filtrar = bool(cfg.pai_sem_clones or self.so_doadoras)
        if not self._indices_da_prioridade():
            if not filtrar:
                return self.fotos.melhores(cfg.k_melhores)
            return self._um_por_comportamento([i for i in self.fotos.melhores(len(self.fotos)) if i not in self.so_doadoras], cfg.k_melhores)
        ok = np.flatnonzero(self.fotos.distancias() >= 0)
        ordem = ok[np.lexsort((self.g.random(len(ok)), self._chave_de_nivel(ok)))]
        if not filtrar:
            return [int(i) for i in ordem[:cfg.k_melhores]]
        return self._um_por_comportamento([int(i) for i in ordem if int(i) not in self.so_doadoras], cfg.k_melhores)

    def _ver_de_trabalho(self, ver):
        if ver is None or ver.get('estado') != 'ok':
            return ver
        v = dict(ver)
        viol, d = self._chave_do_veredito(ver)
        v['distancia'] = int(min(d + float(self.cfg.peso_da_prioridade_no_aprendiz) * viol, 1000 * len(ver['valores'])))
        return v

    def _embrulhar_o_aprendiz(self):
        esc = self.escritor
        pai0, reg0, pisc0 = (esc.pai, esc.registrar, esc.registrar_piscina)
        esc.pai = lambda bits, ver, passo=0: pai0(bits, self._ver_de_trabalho(ver), passo)
        esc.registrar = lambda pai, pai_foto, c, ver_filho, braco, gen=0, passo=0, filho_id=None: reg0(pai, pai_foto, c, self._ver_de_trabalho(ver_filho), braco, gen=gen, passo=passo, filho_id=filho_id)
        esc.registrar_piscina = lambda pai, pai_foto, cands, vers, rodada=0, destino='piscina', ids=None: pisc0(pai, pai_foto, cands, [self._ver_de_trabalho(v) for v in vers], rodada=rodada, destino=destino, ids=ids)

    def _avanco_pela_prioridade(self):
        return bool(self.cfg.progresso_pela_prioridade) and bool(self._indices_da_prioridade())

    def _indices_da_prioridade(self):
        if self.cfg.prioridade_em_niveis:
            return tuple((int(i) for nivel in self.cfg.prioridade_em_niveis for i in nivel))
        if self.cfg.prioridade_clausulas:
            return tuple((int(i) for i in self.cfg.prioridade_clausulas))
        return () if self.cfg.prioridade_clausula is None else (int(self.cfg.prioridade_clausula),)

    def _um_por_comportamento(self, ids, limite=None):
        if not self.cfg.pai_sem_clones:
            return list(ids) if limite is None else list(ids)[:int(limite)]
        f = self.fotos
        vistos, out = (set(), [])
        for i in ids:
            i = int(i)
            ch = (tuple(np.round(np.nan_to_num(f.valores[i].astype(np.float64), nan=9.9), 6)), int(f.comp_lo[i]), int(f.comp_hi[i]))
            if ch not in vistos:
                vistos.add(ch)
                out.append(i)
                if limite is not None and len(out) >= int(limite):
                    break
        return out

    def _niveis_em_milesimos(self, valores_por_clausula):
        total, finito = (None, None)
        for nivel in self.cfg.prioridade_em_niveis:
            v = None
            for i in nivel:
                vi = np.asarray(self.problema.violacoes_de_coluna(int(i), np.asarray(valores_por_clausula(int(i)), np.float64)), np.float64)
                ok = np.isfinite(vi)
                vi = np.where(ok, np.minimum(vi, 1.0), 1.0)
                v = vi if v is None else v + vi
                finito = ok if finito is None else finito & ok
            mil = np.round(v * 1000.0).astype(np.int64)
            total = mil if total is None else total * 10 ** 4 + mil
        return (total, finito)

    def _chave_do_veredito(self, ver):
        if self.cfg.prioridade_em_niveis:
            p, ok = self._niveis_em_milesimos(lambda i: [ver['valores'][i]])
            return (int(p[0]) if bool(ok[0]) else 10 ** 15, int(ver['distancia']))
        v = 0.0
        for i in self._indices_da_prioridade():
            vi = float(np.asarray(self.problema.violacoes_de_coluna(i, np.asarray([ver['valores'][i]], np.float64)), np.float64)[0])
            v += min(vi, 1.0) if len(self._indices_da_prioridade()) > 1 else vi
        return (int(np.round(min(v, 1000.0) * 1000.0)) if np.isfinite(v) else 10 ** 9, int(ver['distancia']))

    def _violacao_da_prioridade(self):
        n = len(self.fotos)
        ind = self._indices_da_prioridade()
        if len(ind) == 1:
            v = np.asarray(self.problema.violacoes_de_coluna(ind[0], self.fotos.valores[:n, ind[0]].astype(np.float64)), np.float64)
        else:
            v = np.zeros(n)
            for i in ind:
                v += np.minimum(np.asarray(self.problema.violacoes_de_coluna(i, self.fotos.valores[:n, i].astype(np.float64)), np.float64), 1.0)
        v[~np.isfinite(v)] = np.inf
        v[self.fotos.distancias() < 0] = np.inf
        return v

    def _chave_de_nivel(self, ids):
        d = self.fotos.distancias()[ids].astype(np.int64)
        if not self._indices_da_prioridade():
            return d
        if self.cfg.prioridade_em_niveis:
            ids = np.asarray(ids, np.int64)
            p, ok = self._niveis_em_milesimos(lambda i: self.fotos.valores[ids, i].astype(np.float64))
            p = np.where(ok & (d >= 0), p, 10 ** 11)
            return p * 10 ** 7 + d
        vp = self._violacao_da_prioridade()[ids]
        return np.where(np.isfinite(vp), np.round(np.minimum(vp, 1000.0) * 1000.0), 10 ** 9).astype(np.int64) * 10 ** 7 + d

    def _pai_por_torneio(self, livres):
        cfg = self.cfg
        if len(self.populacao) < cfg.torneio_tamanho:
            self.populacao.extend(range(max(0, len(self.fotos) - cfg.torneio_populacao), len(self.fotos)))
        reservada = self._mascara_de_pais()
        d = self.fotos.distancias()
        livre = None if cfg.torneio_sem_limite_de_tentativas else set((int(i) for i in livres))
        pop = np.asarray(self._um_por_comportamento([k for k in self.populacao if (livre is None or k in livre) and (not reservada[k]) and (d[k] >= 0)]), np.int64)
        if len(pop) < 2:
            return None
        amostra = pop[self.g.choice(len(pop), min(int(cfg.torneio_tamanho), len(pop)), replace=False)]
        return int(amostra[np.lexsort((self.g.random(len(amostra)), self._chave_de_nivel(amostra)))[0]])

    def _pai_por_nivel(self, livres):
        cfg = self.cfg
        reservada = self._mascara_de_pais()
        cand = np.asarray(self._um_por_comportamento([i for i in livres if not reservada[i]]), np.int64)
        if len(cand) == 0:
            cand = np.asarray(livres, np.int64)
        chave = self._chave_de_nivel(cand)
        niveis = np.unique(chave)[:max(1, int(cfg.niveis_k))]
        w = float(cfg.niveis_q) ** np.arange(len(niveis))
        j = int(self.g.choice(len(niveis), p=w / w.sum()))
        do_nivel = cand[chave == niveis[j]]
        return int(do_nivel[self.g.integers(len(do_nivel))])

    def _escolher_pai(self, apenas=None):
        cfg, g, esc = (self.cfg, self.g, self.escritor)
        livres = self._livres()
        politica = 'distancia'
        if apenas is None and g.random() < max(cfg.frac_acaso, CM.FRACAO_CEGA_MINIMA):
            pai, politica = (int(livres[g.integers(len(livres))]), 'acaso')
        elif apenas is None and self.mapa is not None and (g.random() < cfg.mapa_p_molde) and ((m := self._molde_do_mapa(set(livres))) is not None):
            pai, politica = (int(m[0]), 'mapa')
        elif apenas is None and cfg.persistencia_do_pai and (self.pai_persistente is not None) and (self.pai_persistente in set(livres)):
            pai, politica = (int(self.pai_persistente), 'persistencia')
        elif apenas is None and self.alocacao_por_desacordo and esc.pronto() and (len(esc.rede) >= 2) and (g.random() < cfg.p_desacordo):
            cands = []
            for _ in range(cfg.m_candidatos_pai):
                c = self._pai_por_posto(livres)
                if c not in cands:
                    cands.append(c)
            des = []
            for c in cands:
                d = esc.desacordo_do_molde(esc.pai(self.fotos.foto(c), self.fotos.veredito(c)), 32, g)
                des.append(-1.0 if d is None else d)
            if len(cands) >= 2 and max(des) >= 0:
                ordem = np.argsort(des)[::-1][:max(1, (len(cands) + 1) // 2)]
                pai, politica = (int(cands[int(g.choice(ordem))]), 'desacordo')
            else:
                pai = self._pai_por_posto(livres)
        else:
            pai = self._pai_por_posto(livres)
        if politica == 'mapa':
            self.contadores['pais_pelo_mapa'] = self.contadores.get('pais_pelo_mapa', 0) + 1
        else:
            self.contadores['pais_ao_acaso' if politica == 'acaso' else 'pais_por_desacordo' if politica == 'desacordo' else 'pais_persistentes' if politica == 'persistencia' else 'pais_por_distancia_a_D'] += 1
        self.tentativas[pai] = self.tentativas.get(pai, 0) + 1
        self.pais_vistos.add(pai)
        if self.v2:
            self._confirmar(pai)
        return (pai, politica)

    def _molde_do_mapa(self, livres=None):
        proibida = self._mascara_de_pais()
        return self.mapa.sortear_molde(self.g, lambda i: i < len(proibida) and (not proibida[i]) and (livres is None or i in livres))

    def _credito_da_politica(self, politica, melhores_da_rodada):
        if not melhores_da_rodada:
            return
        y = melhores_da_rodada.get('aprendida', melhores_da_rodada.get('fria', min(melhores_da_rodada.values())))
        c = self.politicas.setdefault(politica, {'rodadas': 0, 'soma': 0.0, 'soma2': 0.0, 'com_melhora': 0})
        c['rodadas'] += 1
        c['soma'] += float(y)
        c['soma2'] += float(y) ** 2
        c['com_melhora'] += int(y < 0)

    def credito_por_politica(self):
        out = {}
        for k, c in sorted(self.politicas.items()):
            n = max(c['rodadas'], 1)
            m = c['soma'] / n
            out[k] = {'rodadas': c['rodadas'], 'melhor_efeito_medio_da_escrita_aprendida': round(m, 4), 'erro_padrao': round(math.sqrt(max(c['soma2'] / n - m * m, 0.0) / n), 4), 'rodadas_com_melhora': c['com_melhora'], 'taxa_de_rodadas_com_melhora': round(c['com_melhora'] / n, 4)}
        return out

    def comparar_politicas(self, a, b):
        ca, cb = (self.politicas.get(a), self.politicas.get(b))
        if not ca or not cb or ca['rodadas'] < 5 or (cb['rodadas'] < 5):
            return None
        ma, mb = (ca['soma'] / ca['rodadas'], cb['soma'] / cb['rodadas'])
        va = max(ca['soma2'] / ca['rodadas'] - ma * ma, 0.0) / ca['rodadas']
        vb = max(cb['soma2'] / cb['rodadas'] - mb * mb, 0.0) / cb['rodadas']
        ep = math.sqrt(va + vb)
        return {'rodadas': [ca['rodadas'], cb['rodadas']], 'diferenca': round(ma - mb, 5), 'erro_padrao': round(ep, 5), 'veredito': _veredito_da_diferenca(ma - mb, ep)}

    def _credito(self, braco, ys, avaliacoes):
        b = self.braco.setdefault(braco, {'n': 0, 'avaliacoes_de_V': 0, 'melhoras': 0, 'soma_y': 0.0, 'soma_y2': 0.0, 'rodadas': 0, 'rodadas_com_melhora': 0})
        b['n'] += len(ys)
        b['avaliacoes_de_V'] += avaliacoes
        b['melhoras'] += sum((1 for y in ys if y < 0))
        b['soma_y'] += float(sum(ys))
        b['soma_y2'] += float(sum((y * y for y in ys)))
        b['rodadas'] += 1
        b['rodadas_com_melhora'] += int(bool(ys) and min(ys) < 0)

    def rodada(self):
        cfg, esc = (self.cfg, self.escritor)
        n_pais = max(1, min(int(cfg.pais_por_rodada), int(cfg.K)))
        pais = []
        for _ in range(n_pais):
            pai_id, politica = self._escolher_pai()
            pai_bits, pai_ver = (self.fotos.foto(pai_id), self.fotos.veredito(pai_id))
            pais.append((pai_id, politica, pai_ver, esc.pai(pai_bits, pai_ver)))
        cotas = [cfg.K // n_pais + int(j < cfg.K % n_pais) for j in range(n_pais)]
        self.pais_da_ultima_rodada = [int(p[0]) for p in pais]
        pais_da_rodada = list(pais)
        propostas = {}
        escolhas_da_rede = []
        for braco in cfg.bracos:
            if braco == 'evo':
                if self.gerador_evo is None:
                    from experimentos.peca import GeradorEvo
                    self.gerador_evo = GeradorEvo(cfg.evo_populacao, cfg.evo_torneio)
                filhos = []
                for pai_id_e, c in self.gerador_evo.propor(self, cfg.K, self.g):
                    pai_ver_e = self.fotos.veredito(pai_id_e)
                    pai_e = esc.pai(self.fotos.foto(pai_id_e), pai_ver_e)
                    if hasattr(esc, 'layout'):
                        EF.caracteristicas(pai_e, [c], esc.mapa, esc.layout)
                    pais.append((pai_id_e, 'evo', pai_ver_e, pai_e))
                    filhos.append((len(pais) - 1, c))
                propostas[braco] = ('evo', filhos)
                continue
            br, filhos = (braco, [])
            gerador = GEMEOS.get(braco, braco)
            for j, (_, _, _, pai) in enumerate(pais_da_rodada):
                esc.ultima_escolha = None
                br, cs = esc.propor(pai, gerador, cfg.K, self.g) if n_pais == 1 else esc.propor(pai, gerador, cotas[j], self.g, n=cotas[j])
                filhos += [(j, c) for c in cs]
                if br == 'aprendida' and getattr(esc, 'ultima_escolha', None):
                    escolhas_da_rede.append(esc.ultima_escolha)
            propostas[braco] = (braco if braco in GEMEOS else br, filhos)
        todos = [c.bits for _, filhos in propostas.values() for _, c in filhos]
        antes_v = self.contadores['avaliacoes_de_V']
        vers = self._medir(todos, 'rodadas')
        pago = self.contadores['avaliacoes_de_V'] - antes_v
        melhores_da_rodada, classes_da_rodada, i = ({}, {}, 0)
        melhores_por_pai = [{} for _ in pais]
        notas_previstas = {}
        for e in escolhas_da_rede:
            notas_previstas.update(e.get('notas', {}))
        traco_bracos = {}
        for braco, (br, filhos) in propostas.items():
            ys = []
            novas_do_braco = 0
            for j, c in filhos:
                pai_id, _, pai_ver, pai = pais[j]
                ver = vers[i]
                i += 1
                k, nova = self._guardar(c.bits, ver, ORIGEM_DO_BRACO[br], pai=pai_id)
                if cfg.politica_do_pai in ('torneio', 'estagnacao') and k >= 0:
                    self.populacao.append(int(k))
                novas_do_braco += int(nova)
                cls = self.lixo.contar(br, c.origem, pai_ver, ver, nova)
                if cls is not None:
                    classes_da_rodada.setdefault(br, []).append(cls)
                y = self._registrar(pai, pai_id, c, ver, GEMEOS.get(br, br), k)
                ys.append(y)
                traco_bracos.setdefault(br, []).append({'o': c.origem, 't': c.tipo, 'p': int(c.p), 'k': int(c.k), 'pai': int(pai_id), 'foto': int(k), 'nova': bool(nova), 'd': int(ver['distancia']), 'nfal': int(ver['nfal']), 'y': round(float(y), 4), 'nota': notas_previstas.get(self.cod.chave(c.bits)) if br == 'aprendida' else None})
                melhores_por_pai[j][br] = min(y, melhores_por_pai[j].get(br, y))
            esc.registrar_rodada(br, [c for _, c in filhos], ys)
            self._credito(br, ys, novas_do_braco)
            if ys:
                melhores_da_rodada[br] = min(ys)
        self.lixo.fechar_rodada(classes_da_rodada)
        self._traco({'tipo': 'rodada', 'pais': [{'id': int(p[0]), 'politica': p[1], 'd': int(p[3].dist)} for p in pais[:n_pais]], 'bracos': traco_bracos, 'escolhas_da_rede': [{k_: v for k_, v in e.items() if k_ != 'notas'} for e in escolhas_da_rede], 'melhor': None if self.melhor is None else list(self.melhor), 'sal': int(getattr(self, 'sal', 0)), 'fotos': int(len(self.fotos))})
        pai_id, politica, _, pai = pais[0]
        if cfg.persistencia_do_pai and politica != 'acaso':
            if melhores_da_rodada and min(melhores_da_rodada.values()) < 0:
                self.pai_persistente, self.rodadas_sem_melhora_do_pai = (int(pai_id), 0)
            elif self.pai_persistente == int(pai_id):
                self.rodadas_sem_melhora_do_pai += 1
                if self.rodadas_sem_melhora_do_pai >= cfg.persistencia_do_pai:
                    self.pai_persistente, self.rodadas_sem_melhora_do_pai = (None, 0)
        self.melhor_por_rodada.append(melhores_da_rodada)
        for j, (_, politica_j, _, _) in enumerate(pais):
            self._credito_da_politica(politica_j, melhores_por_pai[j])
        self.rodada_n += 1
        self.contadores['rodadas'] += 1
        self.plato += 1
        linha = {'rodada': self.rodada_n, 'pai': int(pai_id), 'politica_do_pai': politica, 'distancia_do_pai': int(pai.dist), 'melhor_por_braco': {k: round(v, 4) for k, v in melhores_da_rodada.items()}, 'avaliacoes_de_V': pago, 't': round(self.segundos(), 1)}
        if n_pais > 1:
            linha.update({'pais': [int(p[0]) for p in pais], 'politicas_dos_pais': [p[1] for p in pais], 'distancias_dos_pais': [int(p[3].dist) for p in pais]})
        self.log_r.write(json.dumps(linha) + '\n')
        self.log_r.flush()

    def _rotular(self, n, finalidade='piscinas (decisões rotuladas por inteiro)'):
        cfg, esc = (self.cfg, self.escritor)
        for _ in range(n):
            ok = np.flatnonzero((self.fotos.distancias() >= 0) & ~self._mascara_de_pais())
            pai_id = int(ok[self.g.integers(len(ok))])
            self.pais_vistos.add(pai_id)
            pai = esc.pai(self.fotos.foto(pai_id), self.fotos.veredito(pai_id))
            cs = esc.propor_piscina(pai, cfg.escritor['piscina_m'], self.g)
            if len(cs) < 6:
                continue
            vers = self._medir([c.bits for c in cs], finalidade)
            ids = []
            for c, v in zip(cs, vers):
                k, nova = self._guardar(c.bits, v, 'piscina', pai=pai_id)
                self.lixo.contar('piscina', c.origem, self.fotos.veredito(pai_id), v, nova)
                ids.append(k)
                self.edicoes.adicionar(pai_id, EF.TIPOS.index(c.tipo), c.p, min(c.k, 255), c.seq, k, 0, int(v['distancia']), v['comportamento'], EF.CODIGO_DE_BRACO['piscina'], self.geracao)
            esc.registrar_piscina(pai, pai_id, cs, vers, rodada=self.geracao, destino='piscina' if self.g.random() < cfg.banco_fracao else 'treino', ids=ids)
            self.contadores['piscinas_rotuladas'] += 1

    def _aquecer(self):
        self._rotular(self.cfg.aquecimento_piscinas, 'aquecimento (piscinas antes da 1ª rodada)')
        self._evento({'evento': 'aquecimento_do_escritor', 'piscinas': self.cfg.aquecimento_piscinas, 'exemplos': self.escritor.mem.proprios(), 'pronto': self.escritor.pronto()})

    def fim_de_geracao(self):
        cfg, esc = (self.cfg, self.escritor)
        self.geracao += 1
        if self.v2 and int(cfg.v2_epoca_geracoes) > 0 and (self.geracao % int(cfg.v2_epoca_geracoes) == 0):
            self._virar_o_sal()
        esc.treinar(passos=cfg.treino_passos, lote=cfg.treino_lote)
        self._rotular(cfg.piscinas_por_geracao)
        ligado, comp = self.lixo.alarme()
        if ligado != self.alarme_de_lixo:
            self.alarme_de_lixo = ligado
            self._evento({'evento': 'alarme_de_lixo', 'ligado': ligado, 'aprendida_contra_cega': comp})
        if cfg.autoimitacao_cada and self.geracao % cfg.autoimitacao_cada == 0 and esc.pronto():
            n = esc.colher_autoimitacao(g=self.g)
            if n:
                self._evento({'evento': 'autoimitacao', 'guardou': n, 'total': len(esc.auto)})
        if self.geracao % cfg.troca_cada == 0:
            reg = esc.rodada_de_selecao(minimo_dev=cfg.minimo_dev, minimo_ret=cfg.minimo_ret)
            if not reg.get('pulou'):
                self._evento(dict(reg))
            teste = esc.teste_da_alocacao()
            self.alocacao_teste = teste
            if not teste.get('pulou'):
                self.alocacao_testes['feitos'] += 1
                self.alocacao_por_desacordo = bool(teste.get('vale'))
                self.alocacao_testes['abertos'] += int(self.alocacao_por_desacordo)
                self._evento(dict(teste, evento='teste_da_alocacao', alocar_por_desacordo=self.alocacao_por_desacordo))
        if self.rodada_n % cfg.motivos_cada < cfg.rodadas_por_geracao:
            if esc.atualizar_motivos(self.fotos, self.g):
                self._evento({'evento': 'motivos', 'fotos_boas': esc.motivos.n_bons, 'motivos': len(esc.motivos.info)})
        if not self.parada:
            self._importar_doadoras()
        if cfg.sementes_cada and self.geracao % cfg.sementes_cada == 0 and esc.pronto() and (not self.parada):
            self._lote_de_sementes()
        if cfg.catraca_cada and self.geracao % cfg.catraca_cada == 0 and esc.pronto() and (not self.parada):
            self.catraca()
        curva = esc.curva()
        snap = {'geracao': self.geracao, 't': round(self.segundos(), 1), 'rodadas': self.rodada_n, 'exemplos': esc.mem.proprios(), 'fotos': len(self.fotos), 'padroes': esc.biblioteca.tamanho(), 'melhor_distancia': None if self.melhor is None else self.melhor[0], 'velocidade': esc.velocidade()}
        if curva:
            snap.update(curva)
        sig = esc.significado_por_predicado()
        if sig:
            snap['significado_auc_medio'] = round(float(np.mean([v['auc'] for v in sig.values()])), 3)
        self.curva_do_escritor.append(snap)
        if self.cfg.diagnostico_cada and (self.rodada_n % self.cfg.diagnostico_cada < cfg.rodadas_por_geracao or self.plato >= cfg.plato_rodadas):
            self.diagnosticar('platô' if self.plato >= cfg.plato_rodadas else 'periódico')

    def _guardar_semente(self, bits, ver, origem, pai_id):
        k, nova = self._guardar(bits, ver, origem, pai=pai_id)
        if pai_id >= 0:
            self.lixo.contar(origem, 'semente', self.fotos.veredito(pai_id), ver, nova)
        return (k, nova)

    def _registrar_semente(self, pai, pai_id, c, ver, braco, k):
        return self._registrar(pai, pai_id, c, ver, braco, k, etiqueta=braco)

    def _lote_de_sementes(self):
        cfg, esc = (self.cfg, self.escritor)
        feitos = 0
        for _ in range(cfg.moldes_por_lote_de_sementes):
            sig = None
            if self.mapa is not None and self.g.random() < cfg.mapa_p_molde and ((m := self._molde_do_mapa()) is not None):
                pai_id, sig = (int(m[0]), m[1])
            else:
                pai_id, _pol = self._escolher_pai(apenas='distancia')
            if self.v2:
                self._confirmar(pai_id)
            pai = esc.pai(self.fotos.foto(pai_id), self.fotos.veredito(pai_id))
            doad, ganho = self.colheita.doadores_para(self.fotos, pai_id, n_max=12)
            if self.v2 and len(doad):
                self._confirmar_varias(doad, 'confirmação v2 (doadores do lote)')
                doad, ganho = self.colheita.doadores_para(self.fotos, pai_id, n_max=12)
                fica = np.asarray([int(x) in self.confirmadas for x in doad], bool)
                doad, ganho = (np.asarray(doad)[fica], np.asarray(ganho)[fica])
            if self.mapa is not None and cfg.mapa_doadoras:
                sig = sig if sig is not None else self.mapa.assinatura(self.fotos.foto(pai_id))
                proibida = self._mascara_de_pais()
                ja = set((int(x) for x in doad)) | {int(pai_id)}
                extra = [i for i in self.mapa.doadoras(self.g, sig, cfg.mapa_doadoras, lambda i: i < len(proibida) and (not proibida[i])) if i not in ja]
                if extra:
                    self._confirmar_varias(extra, 'confirmação v2 (doadores do mapa)')
                    doad = np.concatenate([np.asarray(doad, np.int64), np.asarray(extra, np.int64)])
                    ganho = np.concatenate([np.asarray(ganho, np.float64), np.zeros(len(extra))])
                self._evento({'evento': 'mapa_no_lote', 'molde': int(pai_id), 'assinatura_do_molde': list(sig), 'doadoras_do_mapa': [int(i) for i in extra], 'assinaturas_delas': [list(self.mapa.de_foto.get(int(i), ())) for i in extra]})
            if len(doad) == 0:
                self._evento({'evento': 'lote_de_sementes', 'pai': int(pai_id), 'pulou': 'a colheita não tem doador que melhore este molde'})
                continue
            antes_v = self.contadores['avaliacoes_de_V']
            planos, caminhos = SF.escrever_planos(esc, pai, self.fotos, doad, cfg.sementes_por_fonte, self.g)
            if not planos['aprendida']:
                self._evento({'evento': 'lote_de_sementes', 'pai': int(pai_id), 'pulou': 'a rede não achou composição que melhore a nota prevista'})
                continue
            estados = SF.conduzir(esc, pai, pai_id, planos, lambda l: self._medir(l, 'sementes (composição e remendo)'), self._guardar_semente, self._registrar_semente, self.g, passos=cfg.sementes_passos_de_remendo, edicoes_por_passo=cfg.sementes_edicoes_por_passo)
            self._credito_de_sementes(estados, pai_id, self.contadores['avaliacoes_de_V'] - antes_v, caminhos, ganho, doad)
            feitos += 1
        self.sementes['lotes'] += int(feitos > 0)
        return feitos

    def _credito_de_sementes(self, estados, pai_id, pago, caminhos, ganho, doad=()):
        da_celula = self._ids_da_celula() if self.cfg.doadoras_de_corridas else set()
        por_fonte = {}
        for e in estados:
            por_fonte.setdefault(e.fonte, []).append(e)
        linha = {}
        for f, es in por_fonte.items():
            c = self.sementes['fontes'].setdefault(f, {'sementes': 0, 'composicoes_medidas': 0, 'melhoraram_na_composicao': 0, 'melhoraram_no_fim': 0, 'soma_y_compor': 0.0, 'soma_y_final': 0.0, 'remendos_aceitos': 0, 'remendos_pedidos': 0, 'soma_do_tamanho_escolhido': 0, 'avaliacoes_pedidas': 0})
            for e in es:
                c['sementes'] += 1
                c['composicoes_medidas'] += e.composicoes
                c['melhoraram_na_composicao'] += int(e.y_compor < 0)
                c['melhoraram_no_fim'] += int(e.y_final < 0)
                c['soma_y_compor'] += float(e.y_compor)
                c['soma_y_final'] += float(e.y_final)
                c['remendos_aceitos'] += e.remendos_aceitos
                c['remendos_pedidos'] += e.remendos_pedidos
                c['soma_do_tamanho_escolhido'] += e.tamanho_escolhido
                c['avaliacoes_pedidas'] += e.pedidas
            linha[f] = {'y_compor': min((e.y_compor for e in es)), 'y_final': min((e.y_final for e in es)), 'media_y_final': float(np.mean([e.y_final for e in es])), 'sementes': len(es), 'pedidas': int(sum((e.pedidas for e in es)))}
            if da_celula:
                usam = [e for e in es if set(getattr(e, 'doadores', ())) & da_celula]
                c['com_doadora_da_celula'] = c.get('com_doadora_da_celula', 0) + len(usam)
                linha[f]['com_doadora_da_celula'] = len(usam)
        self.sementes['moldes'] += 1
        self.sementes['por_lote'].append(linha)
        del self.sementes['por_lote'][:-2000]
        if caminhos:
            self.sementes['caminhos'].append({'molde': int(pai_id), 'partes_por_caminho': [len(c[0]) for c in caminhos if c], 'nota_prevista_final': [round(c[1][-1], 4) for c in caminhos if c and c[1]]})
            del self.sementes['caminhos'][:-50]
        ev = {'evento': 'lote_de_sementes', 'pai': int(pai_id), 'doadores': int(len(ganho)), 'avaliacoes_de_V': int(pago), 'por_fonte': {f: {k: round(v, 4) for k, v in d.items()} for f, d in linha.items()}}
        if da_celula:
            ev['doadoras_da_celula_oferecidas'] = int(sum((1 for x in doad if int(x) in da_celula)))
        self._evento(ev)

    def _ids_da_celula(self):
        n = len(self.fotos)
        cod = AF.ORIGENS.index('doadora_da_celula')
        return set((int(k) for k in np.flatnonzero(self.fotos.origem[:n] == cod)))

    def comparar_sementes(self, a, b, fase='y_final'):
        d = [r[a][fase] - r[b][fase] for r in self.sementes['por_lote'] if a in r and b in r]
        if len(d) < 3:
            return None
        m, ep = (float(np.mean(d)), _erro_padrao_pareado(d))
        return {'moldes_pareados': len(d), 'fase': fase, 'diferenca': round(m, 5), 'erro_padrao': round(ep, 5), 'veredito': _veredito_da_diferenca(m, ep)}

    def _sementes_do_reinicio(self, n):
        cfg, esc = (self.cfg, self.escritor)
        feitas = tentativas = 0
        while feitas < n and tentativas < 3 * n and esc.pronto():
            tentativas += 1
            pai_id = self._pai_por_posto(self._livres())
            self.pais_vistos.add(pai_id)
            pai = esc.pai(self.fotos.foto(pai_id), self.fotos.veredito(pai_id))
            doad, _ = self.colheita.doadores_para(self.fotos, pai_id, n_max=12)
            if len(doad) == 0:
                continue
            material = SF.Material(esc, pai, self.fotos, doad, self.g)
            plano, _tam, _cam = SF.plano_aprendido(esc, material, self.g, set())
            if plano is None:
                continue
            est = SF.conduzir(esc, pai, pai_id, {'aprendida': [plano]}, lambda l: self._medir(l, 'reinício: sementes da rede'), self._guardar_semente, self._registrar_semente, self.g, passos=cfg.sementes_passos_de_remendo, edicoes_por_passo=cfg.sementes_edicoes_por_passo)
            feitas += len(est)
        self.sementes['no_reinicio']['aprendidas'] += feitas
        return min(feitas, n)

    def _selo(self):
        return CM.selo_do_que_nao_muda({'bracos': list(self.cfg.bracos), 'K': self.cfg.K, 'hash_de_v': self.hash_de_v, 'final_um_em': self.cfg.final_um_em, 'confirmacao_um_em': self.cfg.confirmacao_um_em})

    def _moldes_de_confirmacao(self, n):
        d = self.fotos.distancias()
        if int(self.cfg.confirmacao_um_em) > 0:
            base = (d >= 0) & self._mascara_confirmacao()
        else:
            base = (d >= 0) & ~self._mascara_final()
        cand = [int(i) for i in np.flatnonzero(base) if int(i) not in self.pais_vistos and int(i) not in self.moldes_de_confirmacao_usados and (int(i) not in self.so_doadoras)]
        if len(cand) < n:
            return []
        ordem = sorted(cand, key=lambda i: (d[i], i))
        out = []
        while len(out) < n and ordem:
            out.append(ordem.pop(min(int(self.g.exponential(self.cfg.escala_do_posto)), len(ordem) - 1)))
        return out

    def _prova_pareada(self, pai_id, cand, finalidade=CV.FINALIDADE_SEM_ROTULO, base=None, registrar=True, rotulos=('prova_atual', 'prova_candidata')):
        esc, cfg = (self.escritor, self.cfg)
        self.pais_vistos.add(pai_id)
        pai_ver = self.fotos.veredito(pai_id)
        pai = esc.pai(self.fotos.foto(pai_id), pai_ver)
        semente = int(self.g.integers(1 << 31))
        _, cs_a = esc.propor(pai, 'aprendida', cfg.K, np.random.default_rng(semente), cfg=base)
        _, cs_b = esc.propor(pai, 'aprendida', cfg.K, np.random.default_rng(semente), cfg=cand)
        if not cs_a or not cs_b:
            return None
        vers = self._medir([c.bits for c in cs_a] + [c.bits for c in cs_b], finalidade)
        ys = {rotulos[0]: [], rotulos[1]: []}
        for j, (c, v) in enumerate(zip(cs_a + cs_b, vers)):
            rotulo = rotulos[0] if j < len(cs_a) else rotulos[1]
            k, nova = self._guardar(c.bits, v, 'prova_atual' if rotulo == rotulos[0] else 'prova_candidata', pai=pai_id)
            self.lixo.contar(rotulo, c.origem, pai_ver, v, nova)
            if registrar:
                ys[rotulo].append(self._registrar(pai, pai_id, c, v, 'aprendida', k, etiqueta=rotulo))
            else:
                y = EF.alvo(pai.dist, v['distancia']) if v['estado'] == 'ok' else EF.CLIP_DO_ALVO
                self.edicoes.adicionar(pai_id, EF.TIPOS.index(c.tipo), c.p, min(c.k, 255), c.seq, k, 0, int(v['distancia']), v['comportamento'], EF.CODIGO_DE_BRACO.get(rotulo, 0), self.geracao)
                ys[rotulo].append(y)
        return (min(ys[rotulos[0]]), min(ys[rotulos[1]]))

    def catraca(self):
        cfg, esc, est = (self.cfg, self.escritor, self.catraca_est)
        if len(self.fotos) < cfg.catraca_min_fotos:
            est['puladas'] += 1
            return self._evento({'evento': 'config', 'pulou': f'poucas fotos ({len(self.fotos)} de {cfg.catraca_min_fotos})'})
        confirmacao = self._moldes_de_confirmacao(cfg.catraca_pares_confirmacao)
        if len(confirmacao) < cfg.catraca_pares_confirmacao:
            est['puladas'] += 1
            onde = f'na reserva de confirmação (1 em {cfg.confirmacao_um_em} fotos, marcadas pelo hash no nascimento)' if int(cfg.confirmacao_um_em) > 0 else '(fotos que nunca foram pai)'
            return self._evento({'evento': 'config', 'pulou': f'poucos moldes de confirmação {onde}'})
        if self.selo_inicial is None:
            self.selo_inicial = self._selo()
        if not (self._integridade() and self._selo() == self.selo_inicial):
            est['recusadas_integridade'] += 1
            self.parada = 'instrumento'
            return self._evento({'evento': 'config', 'recusada': 'a integridade falhou ANTES da prova (V, o oráculo, o banco retido da prova cega ou a porta)'})
        valida = lambda c: CM.cfg_valida(c, self.espaco_cfg, cfg.K, esc.total_avaliado)
        cand, cego, nota, volta = self.meta_cfg.propor(self.H_cfg, esc.config_de_escrita, self.g, anterior=self.cfg_anterior, valida=valida)
        if cand == esc.config_de_escrita:
            est['puladas'] += 1
            return self._evento({'evento': 'config', 'pulou': 'nenhuma configuração vizinha válida'})
        est['propostas'] += 1
        n_proposta = est['propostas']
        est['voltas'] += int(volta)
        minimo_dev, minimo_conf = (max(4, cfg.catraca_pares_dev * 5 // 6), max(3, cfg.catraca_pares_confirmacao * 2 // 3))
        d_dev = []
        for _ in range(cfg.catraca_pares_dev):
            pai_id, _pol = self._escolher_pai(apenas='distancia')
            r = self._prova_pareada(pai_id, cand, 'catraca: desenvolvimento')
            if r is not None:
                d_dev.append(r[1] - r[0])
        est['pares_dev'] += len(d_dev)
        d_conf = []
        if CM.passa_com_folga(d_dev, minimo_dev, CM.folga_da_proposta(n_proposta, len(d_dev))):
            reserva = int(cfg.confirmacao_um_em) > 0
            for pid in confirmacao:
                r = self._prova_pareada(pid, cand, 'catraca: confirmação (moldes de uso único)', registrar=not reserva)
                self.moldes_de_confirmacao_usados.add(pid)
                if r is not None:
                    d_conf.append(r[1] - r[0])
            est['pares_conf'] += len(d_conf)
        dec = CM.decidir(d_dev, d_conf, minimo_dev, minimo_conf, n_proposta)
        integra = self._integridade() and self._selo() == self.selo_inicial
        if not integra:
            dec['adota'], dec['motivo_da_recusa'] = (False, 'a integridade falhou DEPOIS da prova (V, o oráculo, o banco retido da prova cega ou a porta): a corrida para')
            est['recusadas_integridade'] += 1
            self.parada = 'instrumento'
        elif dec['adota']:
            self.cfg_anterior = dict(esc.config_de_escrita)
            esc.config_de_escrita = dict(cand)
            est['adotadas'] += 1
        else:
            est['recusadas_porta' if not dec['passa_a_porta'] else 'recusadas_confirmacao'] += 1
        self.H_cfg.append({'cfg_candidata': dict(cand), 'd_dev': dec['d_dev'] if dec['d_dev'] is not None else 0.0, 'adotou': bool(dec['adota'])})
        return self._evento(dict(dec, evento='config', cfg_candidata=cand, cfg_atual=dict(esc.config_de_escrita), cego=bool(cego), volta=bool(volta), nota_do_meta_modelo=round(float(nota), 5)))

    def reverter_catraca(self):
        if self.cfg_anterior is None:
            return False
        atual = dict(self.escritor.config_de_escrita)
        self.escritor.config_de_escrita, self.cfg_anterior = (dict(self.cfg_anterior), atual)
        self._evento({'evento': 'config', 'reversao': True, 'cfg_atual': dict(self.escritor.config_de_escrita)})
        return True

    def _moldes_finais(self, n):
        d = self.fotos.distancias()
        cand = [int(i) for i in np.flatnonzero((d >= 0) & self._mascara_final()) if int(i) not in self.so_doadoras]
        ordem = sorted(cand, key=lambda i: (d[i], i))
        out = []
        while len(out) < n and ordem:
            out.append(ordem.pop(min(int(self.g.exponential(self.cfg.escala_do_posto)), len(ordem) - 1)))
        return out

    def leitura_final(self):
        cfg, esc = (self.cfg, self.escritor)
        if self.leitura_final_feita is not None:
            return self.leitura_final_feita
        if dict(self.cfg_inicial) == dict(esc.config_de_escrita):
            return {'feita': False, 'motivo': 'a configuração de agora é a de partida (a catraca não mudou nada, ou voltou a ela): não há o que comparar'}
        moldes = self._moldes_finais(cfg.final_pares)
        minimo = max(4, cfg.final_pares // 4)
        if len(moldes) < minimo:
            return {'feita': False, 'motivo': f'poucas fotos no conjunto final intocado ({len(moldes)} de, no mínimo, {minimo}): 1 em {cfg.final_um_em} das fotos medidas é reservada'}
        antes = self.gasto_de_V.por_finalidade.get('catraca: leitura final (conjunto final intocado)', 0)
        d = []
        for pid in moldes:
            r = self._prova_pareada(pid, dict(esc.config_de_escrita), 'catraca: leitura final (conjunto final intocado)', base=dict(self.cfg_inicial), registrar=False, rotulos=('final_de_partida', 'final_de_agora'))
            if r is not None:
                d.append(r[1] - r[0])
        m, ep = (float(np.mean(d)), _erro_padrao_pareado(d)) if len(d) > 1 else (float('nan'), float('nan'))
        veredito = _veredito_da_diferenca(m, ep)
        self.leitura_final_feita = {'feita': True, 'moldes_do_conjunto_final': len(d), 'd_medio_de_agora_menos_partida': round(m, 5) if math.isfinite(m) else None, 'erro_padrao': round(ep, 5) if math.isfinite(ep) else None, 'veredito': veredito, 'configuracao_de_partida': dict(self.cfg_inicial), 'configuracao_final': dict(esc.config_de_escrita), 'adotadas_pela_catraca': self.catraca_est['adotadas'], 'v_gasto': self.gasto_de_V.por_finalidade.get('catraca: leitura final (conjunto final intocado)', 0) - antes, 'o_motor_melhorou_a_si_mesmo': bool(veredito == 'ganho'), 'obs': "negativo = a configuração final aproxima mais de D que a de partida, em fotos que nenhuma decisão viu; só o veredito 'ganho' sustenta a frase 'o motor melhorou a si mesmo'"}
        self._evento(dict(self.leitura_final_feita, evento='leitura_final'))
        return self.leitura_final_feita

    def _parada_final(self):
        return bool(self.parada and (str(self.parada).startswith('D cumprido') or str(self.parada).startswith('fusível')))

    def _integridade(self):
        self.contadores['auditorias'] += 1
        ok = True
        if self.problema.hash_de_v is not None:
            ok = ok and self.problema.hash_de_v() == self.hash_de_v
        d = self.fotos.distancias()
        candidatos = np.flatnonzero(d >= 0)
        if len(candidatos):
            k = int(candidatos[self.g.integers(len(candidatos))])
            v2 = self.problema.julgar(self._pedir_a_V([self.fotos.foto(k)], 'auditorias (integridade)')[0])
            for _ in range(int(self.cfg.remedir_estouro)):
                if v2['estado'] != 'estouro':
                    break
                self.estouros['remedidas_na_auditoria'] += 1
                v2 = self.problema.julgar(self._pedir_a_V([self.fotos.foto(k)], CV.FINALIDADE_REMEDIDA_DO_ESTOURO)[0])
            if v2['estado'] == 'estouro':
                self._evento({'evento': 'auditoria_estourou', 'foto': k, 'obs': 'uma foto que tinha medida estourou o prazo de V também sozinha: a máquina está sobrecarregada ou V mudou'})
            v1 = self.fotos.veredito(k)
            ok = ok and v2['distancia'] == v1['distancia'] and np.allclose(np.asarray(v2['valores'], float), np.asarray(v1['valores'], float), atol=1e-05, equal_nan=True)
        if not ok:
            self.contadores['integridade_falhas'] += 1
        return bool(ok)

    def diagnosticar(self, motivo):
        cfg = self.cfg
        ev = {'evento': 'diagnostico', 'motivo': motivo, 'plato': self.plato, 'reinicios': self.reinicios, 'melhor_distancia': None if self.melhor is None else self.melhor[0]}
        ev['causa_0_instrumento_ok'] = self._integridade()
        if not ev['causa_0_instrumento_ok']:
            ev['acao'] = 'o instrumento falhou (o hash de V mudou ou uma foto medida de novo deu outro veredito): a busca para, a pergunta vai ao instrumento'
            self.parada = 'instrumento'
            self._evento(ev)
            return
        res = self.fotos.resumo()
        sem = {cid: v['melhor_valor'] for cid, v in res['por_clausula'].items() if v['medidas'] >= cfg.minimo_para_diagnosticar_L and v['cumprem'] == 0}
        if self.plato >= cfg.plato_rodadas and self.reinicios < cfg.max_reinicios:
            self.reinicios += 1
            self.contadores['reinicios'] += 1
            n_total = max(8, cfg.n_partida // 2)
            n_rede = self._sementes_do_reinicio(n_total // 2) if cfg.sementes_no_reinicio else 0
            novas = self._sortear_distintas(n_total - n_rede)
            for b, v in zip(novas, self._medir(novas, 'reinício: sorteadas')):
                self._guardar(b, v, 'sorteio')
            self.sementes['no_reinicio']['sorteadas'] += len(novas)
            self.tentativas.clear()
            self.plato = 0
            ev['acao'] = f'causa 1 (a busca): reinício {self.reinicios}: {len(novas)} fotos sorteadas novas e {n_rede} sementes da rede, e os pais esgotados voltam a valer'
        elif sem:
            ev['causa_2_o_L'] = {'clausulas_que_nenhuma_foto_cumpre': sem, 'fotos_medidas': res['fotos']}
            ev['acao'] = 'causa 2 (o L): a cláusula que nenhuma foto cumpre depois de milhares é o sinal de abrir L; o condutor registra, e abrir é outra versão da codificação, declarada antes de continuar'
            self.plato = 0
        else:
            ev['acao'] = 'nenhuma causa dispara agora: a busca segue'
            self.plato = 0
        self._evento(ev)

    def credito_por_braco(self):
        out = {}
        for k, b in sorted(self.braco.items()):
            n = max(b['n'], 1)
            m = b['soma_y'] / n
            out[k] = {'edicoes_propostas': b['n'], 'avaliacoes_de_V_pagas': b['avaliacoes_de_V'], 'edicoes_que_melhoraram': b['melhoras'], 'taxa_de_melhora': round(b['melhoras'] / n, 4), 'y_medio': round(m, 4), 'erro_padrao_de_y': round(math.sqrt(max(b['soma_y2'] / n - m * m, 0.0) / n), 4), 'rodadas': b['rodadas'], 'rodadas_com_melhora': b['rodadas_com_melhora'], 'melhoras_por_mil_avaliacoes_pagas': round(1000.0 * b['melhoras'] / max(b['avaliacoes_de_V'], 1), 3)}
        return out

    def comparar(self, a, b):
        d = [r[a] - r[b] for r in self.melhor_por_rodada if a in r and b in r]
        if len(d) < 5:
            return None
        m, ep = (float(np.mean(d)), _erro_padrao_pareado(d))
        return {'rodadas_pareadas': len(d), 'diferenca_do_melhor_delta': round(m, 5), 'erro_padrao': round(ep, 5), 'veredito': _veredito_da_diferenca(m, ep)}

    def laco16(self):
        cfg, esc, fotos, c = (self.cfg, self.escritor, self.fotos, self.contadores)
        res = fotos.resumo()
        sig = esc.significado()
        propostas_do_modelo = esc.contadores.get('propostas_do_modelo', 0)
        propostas_cegas = esc.contadores.get('propostas_as_cegas', 0)
        ops = {'classificar': len(fotos) >= cfg.regra_min_fotos and res['menor_distancia'] is not None, 'guardar todas (sem liberar nenhuma)': not fotos.cheio and (not self.edicoes.cheio) and (len(fotos) >= cfg.regra_min_fotos) and (len(self.edicoes) >= cfg.regra_min_fotos) and (res['liberadas'] == 0), 'guardar o padrão': esc.biblioteca.tamanho() >= 10 and esc.mem.proprios() > 0 and (c['pais_por_distancia_a_D'] > 0) and esc.pronto(), 'escrever bit a bit': propostas_do_modelo >= cfg.regra_min_escritas, 'saber o que a sequência significa': len(self.problema.predicados) > 0 and sig is not None and (esc.treinos > 0), 'aprender com o tempo': esc.treinos > 0 and esc.contadores['rodadas_de_selecao'] >= 1 and (propostas_cegas >= max(1, cfg.regra_min_escritas // 4))}
        cod = self.cod
        det = {'operacoes': ops, 'minimos': {'fotos_e_edicoes': cfg.regra_min_fotos, 'escritas_aprendidas': cfg.regra_min_escritas}, 'codificacao': cod.descricao(), 'a_classificar': {'arquivo_de_fotos': res, 'pasta': 'fotos/', 'obs': 'a foto é a sequência de bits do concorrente, em forma canônica; cada uma com o veredito de V, a distância a D, a classe e o comportamento'}, 'b_guardar_todas': {'fotos': len(fotos), 'edicoes_avaliadas_guardadas': len(self.edicoes), 'liberadas': res['liberadas'], 'cheio': bool(fotos.cheio or self.edicoes.cheio), 'obs': 'toda foto e toda edição que V julgou fica em disco, em pedaços que só acrescentam'}, 'c_guardar_o_padrao': {'exemplos_do_escritor': esc.mem.proprios(), 'edicoes_que_melhoraram_a_foto': int((esc.mem.y < 0).sum()), 'padroes_na_biblioteca': esc.biblioteca.tamanho(), 'motivos_nos_bons_corpus': len(esc.motivos.info), 'pais_escolhidos_pela_distancia_a_D': c['pais_por_distancia_a_D'], 'relatorio': 'padroes.json', 'obs': 'as duas leituras de padrão (decisão de 30/09): a sequência que aproxima de D e a estrutura que se repete nos bons corpus'}, 'd_escrever': {'escritas_da_rede_que_foram_a_V': propostas_do_modelo, 'melhoras_das_escritas_da_rede': esc.contadores.get('melhoras_do_modelo', 0), 'sorteadas_que_a_rede_escolheu_(filtro)': esc.contadores.get('propostas_do_filtro', 0), 'melhoras_do_filtro': esc.contadores.get('melhoras_do_filtro', 0), 'as_cegas': propostas_cegas, 'melhoras_as_cegas': esc.contadores.get('melhoras_as_cegas', 0), 'do_operador': esc.contadores.get('propostas_do_operador', 0), 'edicoes_avaliadas_por_V': esc.contadores['edicoes_avaliadas'], 'obs': "'escrever bit a bit' conta só o que a REDE escreveu (o lugar e os bits saem da cabeça que escreve); a sorteada que ela só escolhe é filtro, e conta à parte"}, 'e_o_significado': {'sondas': self.problema.predicados.descricao(), 'o_que_o_modelo_sabe_prever': sig, 'edicoes_que_mudaram_o_comportamento': esc.contadores['edicoes_que_mudaram_o_comportamento']}, 'uma_rede_so': {'membros_do_conjunto': len(esc.rede), 'parametros': int(esc.rede.n_parametros()), 'cabecas': ['ler (a foto, pelos campos e papéis)', 'julgar (o veredito da foto; o efeito de uma edição parte do veredito previsto e aprende só a correção)', 'escrever (o lugar; o conteúdo novo do lugar)'], 'objetivo': 'D, desde o início: toda saída é em termos de D e todo sinal de treino sai de V (as edições e as fotos que V julgou; e a escolha da própria rede, com peso menor)'}, 'f_aprender_com_o_tempo': {'treinos': esc.treinos, 'piscinas': len(esc.piscinas), 'rodadas_de_selecao': esc.contadores['rodadas_de_selecao'], 'trocas_adotadas': esc.contadores['trocas_adotadas'], 'trocas_recusadas': esc.contadores['trocas_recusadas'], 'politicas_adotadas': esc.contadores['politicas_adotadas'], 'politicas_recusadas': esc.contadores['politicas_recusadas'], 'autoimitacoes_guardadas': esc.contadores['autoimitacoes'], 'curva_de_aprendizado_e_de_velocidade': self.curva_do_escritor[-12:], 'credito_por_braco': self.credito_por_braco(), 'aprendida_contra_cega': self.comparar('aprendida', 'cega'), 'aprendida_contra_o_operador': self.comparar('aprendida', 'operador')}, 'obs': "o crédito é medido por V no mesmo orçamento, sobre os mesmos pais, e não decide se a regra foi cumprida. O crédito positivo sustenta a frase 'a escrita aprendida propôs melhor que a cega nos mesmos pais'. A frase 'acelerou' pede mais, porque os braços dividem o arquivo e a trajetória da corrida: 'acelerou' (a máquina chega a D, ou a uma distância-alvo, com menos medidas de V e menos computação) só se diz com corridas independentes, com e sem a escrita aprendida, várias sementes, o mesmo orçamento total de V e toda a computação contada (regra de alegação, emenda 13); 'cada vez mais rápido' só se diz com a curva de velocidade subindo"}
        return (all(ops.values()), det)

    def declaracao(self):
        c = self.contadores
        regra, detalhe16 = self.laco16()
        exercitados, nao = ({}, {})
        exercitados['V ↔ instrumento (8, Cal)'] = {'calibracao': self.calibracao} if self.calibracao is not None else None
        if exercitados['V ↔ instrumento (8, Cal)'] is None:
            del exercitados['V ↔ instrumento (8, Cal)']
            nao['V ↔ instrumento (8, Cal)'] = 'o problema não traz calibração de V (`Problema.calibrar`)'
        exercitados['12 (integridade de V)'] = {'hash_de_V': self.hash_de_v, 'auditorias': c['auditorias'], 'falhas': c['integridade_falhas'], 'hashes_dos_oraculos': self.hashes_dos_oraculos, 'obs': 'o hash de V na partida e em cada diagnóstico; uma foto do arquivo medida de novo tem de dar o mesmo veredito; os hashes dos arquivos de oráculo na partida'}
        if self.selo_do_banco is not None:
            exercitados['V2-9 (o banco retido da prova cega, selado antes da busca)'] = {**self.selo_do_banco, 'obs': 'registrado na partida, antes de qualquer medida; a busca nunca abre o banco (só o arquivo do selo); só a prova cega o usa (`julgar_o_ser.py`); escrito por nós, sem independência: o avaliador independente não foi exercitado'}
        else:
            nao['V2-9 (o banco retido da prova cega, selado antes da busca)'] = 'o problema não traz prova cega (`Problema.selo_do_banco`)'
        exercitados['Ordem das causas, reinícios'] = {'diagnosticos': [e for e in self.eventos if e.get('evento') == 'diagnostico'][-10:], 'reinicios': self.reinicios} if any((e.get('evento') == 'diagnostico' for e in self.eventos)) else None
        if exercitados['Ordem das causas, reinícios'] is None:
            del exercitados['Ordem das causas, reinícios']
            nao['Ordem das causas, reinícios'] = 'nenhum diagnóstico disparou ainda (platô de `plato_rodadas` ou o ciclo de `diagnostico_cada` rodadas)'
        exercitados['Fusível e parada'] = {'estado': self.parada or 'em andamento (sem teto de tempo: roda até achar D)', 'segundos': round(self.segundos(), 1), 'tempo': self.cfg.tempo, 'max_rodadas': self.cfg.max_rodadas}
        exercitados['A partida por sorteio (regra da comparação)'] = {'fotos_sorteadas': self.cfg.n_partida, 'testemunhas': {n: v['distancia'] for n, v in self.testemunhas_medidas.items()}, 'obs': 'nenhuma semente é uma testemunha: as testemunhas só foram medidas, num arquivo à parte, para o relatório'}
        chave16 = '16 (a foto atômica: classificar, guardar o padrão, escrever; PÉTREO)'
        exercitados[chave16] = dict(detalhe16, a_regra_petrea=regra)
        if not regra:
            nao[chave16 + ' (o que falta)'] = '; '.join((k for k, v in detalhe16['operacoes'].items() if not v)) or 'nenhuma operação faltou'
        nao['Resultado → D (10, Ok_k)'] = 'há candidata: espera o Ok_k humano' if c['candidatas_que_cumprem_D'] else 'nenhuma foto cumpriu D inteiro'
        ce = self.catraca_est
        if ce['propostas'] > 0:
            n = ce['propostas']
            exercitados['11 (a catraca do motor)'] = {'propostas': n, 'adotadas': ce['adotadas'], 'recusadas_pela_porta': ce['recusadas_porta'], 'recusadas_pela_confirmacao': ce['recusadas_confirmacao'], 'recusadas_pela_integridade': ce['recusadas_integridade'], 'voltas_propostas': ce['voltas'], 'pares_de_desenvolvimento': ce['pares_dev'], 'pares_de_confirmacao': ce['pares_conf'], 'moldes_de_confirmacao_gastos (uso unico)': len(self.moldes_de_confirmacao_usados), 'configuracao_de_partida': self.cfg_inicial, 'configuracao_de_agora': self.escritor.config_de_escrita, 'a_volta_a_anterior_e_possivel': self.cfg_anterior is not None, 'historia': self.H_cfg[-10:], 'erro_acumulado': {'maximo': CM.ERRO_ACUMULADO_MAXIMO, 'nivel_gasto_ate_a_proposta_atual': round(sum((CM.nivel_da_proposta(i) for i in range(1, n + 1))), 6), 'folga_exigida_na_proxima_proposta': {'desenvolvimento': round(CM.folga_da_proposta(n + 1, self.cfg.catraca_pares_dev), 3), 'confirmacao': round(CM.folga_da_proposta(n + 1, self.cfg.catraca_pares_confirmacao), 3)}, 'regra': 'a proposta de número n gasta o nível 0,05/(n(n+1)) do erro total, repartido entre as duas portas, na cauda de uma t de Student; nunca abaixo da folga 2 da fórmula'}, 'obs': 'o que muda é a configuração da escrita aprendida; V, os braços de controle, K, a fração às cegas (nunca menos de 25%), a porta, a confirmação e a regra do erro acumulado ficam fora do alcance dela; ' + (f'os moldes de confirmação saem da reserva de confirmação (1 em {self.cfg.confirmacao_um_em} fotos, marcadas pelo hash no nascimento: nunca pai, molde, doadora nem exemplo de treino), a confirmação não ensina a rede e cada uma gasta os seus moldes (uso único)' if int(self.cfg.confirmacao_um_em) > 0 else 'os moldes de confirmação são fotos que nunca foram pai (a regra da 4.3-final: podem ter treinado a rede) e cada confirmação os gasta (uso único)') + ', e NÃO são o banco retido da prova cega (as famílias seladas por hash)'}
        else:
            onde = 'da reserva de confirmação' if int(self.cfg.confirmacao_um_em) > 0 else '(fotos que nunca foram pai)'
            nao['11 (a catraca do motor)'] = 'desligada nesta corrida (`catraca_cada` = 0)' if not cfg_catraca(self) else f"implementada e ainda não disparou nesta corrida: a primeira proposta vem depois de {self.cfg.catraca_cada} gerações, com a rede pronta, {self.cfg.catraca_min_fotos} fotos e {self.cfg.catraca_pares_confirmacao} moldes de confirmação {onde} (puladas: {ce['puladas']})"
        conf = self._mascara_confirmacao()
        bloco_conf = {'reserva': f'1 em {self.cfg.confirmacao_um_em} fotos, escolhidas pelo hash da foto no nascimento (com outra chave que a do conjunto final, e fora dele): nunca pai, molde, doadora nem exemplo de treino; só a catraca as usa, uma vez cada, como moldes de confirmação, e a confirmação não ensina a rede', 'fotos_reservadas': int(conf.sum()), 'reservadas_e_medidas': int((self.fotos.distancias() >= 0)[:len(conf)][conf].sum()) if len(conf) else 0, 'gastas_pela_catraca': len(self.moldes_de_confirmacao_usados), 'desde_a_partida': self.confirmacao_um_em_na_partida == self.cfg.confirmacao_um_em, 'obs': 'versão 4.3.1 (a crítica de 01/10, corrigida): na 4.3-final os moldes de confirmação eram as fotos que nunca tinham sido pai, e podiam ter treinado a rede ou servido de doadora'}
        if not bloco_conf['desde_a_partida']:
            bloco_conf['aviso'] = 'a corrida não partiu com esta reserva (partiu numa versão anterior, ou com outro `confirmacao_um_em`): as fotos reservadas agora podem ter treinado a rede antes'
        if int(self.cfg.confirmacao_um_em) > 0:
            exercitados['A reserva de confirmação (4.3.1)'] = bloco_conf
        else:
            nao['A reserva de confirmação (4.3.1)'] = 'desligada (`confirmacao_um_em` = 0): os moldes de confirmação são as fotos que nunca foram pai, como na 4.3-final, e podem ter treinado a rede'
        bloco_estouro = dict(self.estouros, remedir_estouro=int(self.cfg.remedir_estouro), remedidas_na_conta_de_V=self.gasto_de_V.por_finalidade.get(CV.FINALIDADE_REMEDIDA_DO_ESTOURO, 0), obs="o prazo de V é de relógio e o arquivo é cache: a foto que estoura volta a V sozinha antes de entrar no arquivo; 'recuperadas' mediram sozinhas, 'confirmadas' estouraram também sozinhas e ficam como estouro (4.3.1)")
        if self.estouros['na_primeira_medida'] or self.estouros['remedidas_na_auditoria']:
            exercitados['O estouro medido de novo, sozinho (4.3.1)'] = bloco_estouro
        else:
            nao['O estouro medido de novo, sozinho (4.3.1)'] = f'nenhuma medida estourou o prazo de V ainda; quando estourar, a foto volta a V sozinha até {self.cfg.remedir_estouro} vez(es) antes de entrar no arquivo' if self.cfg.remedir_estouro else 'desligado (`remedir_estouro` = 0): o estouro entra no arquivo como veredito final, como na 4.3-final'
        fin = self._mascara_final()
        ok_fin = int((self.fotos.distancias() >= 0)[:len(fin)][fin].sum()) if len(fin) else 0
        bloco_final = {'reserva': f'1 em {self.cfg.final_um_em} fotos, escolhidas pelo hash da foto: nunca pai, molde de confirmação, molde de semente, doadora nem exemplo de treino' if self.cfg.final_um_em else 'desligada (`final_um_em` = 0)', 'fotos_reservadas': int(fin.sum()), 'reservadas_e_medidas': ok_fin, 'uso': 'consultado UMA vez, no fim (D cumprido ou fusível), se a catraca mudou a configuração; a rede não aprende com o resultado'}
        if self.leitura_final_feita is not None:
            exercitados['Conjunto final intocado e leitura final (ajuste C da revisão externa, 01/10)'] = dict(bloco_final, leitura=self.leitura_final_feita)
        else:
            motivo = (self._ultima_leitura_final or {}).get('motivo') or ('só no fim da corrida (D cumprido ou fusível)' if not self._parada_final() else 'não foi feita')
            nao['Conjunto final intocado e leitura final (ajuste C da revisão externa, 01/10)'] = f"{motivo}; reserva: {bloco_final['reserva']}; fotos reservadas até agora: {bloco_final['fotos_reservadas']}"
        if any((c['pagas'] + c['repetidas'] > 0 for c in self.lixo.tabela.values())):
            exercitados['O lixo das edições (ajuste A da revisão externa, 01/10)'] = self.lixo.relatorio()
        else:
            nao['O lixo das edições (ajuste A da revisão externa, 01/10)'] = 'nenhuma edição foi à V ainda'
        sem = {f: v['avaliacoes_pedidas'] for f, v in self.sementes['fontes'].items()}
        exercitados['A contabilidade de V (ajuste B da revisão externa, 01/10)'] = self.gasto_de_V.relatorio(consultas_desta_sessao=self._consultas_da_sessao, avaliador_medidos=getattr(self.avaliador, 'medidos', None), por_braco={b: v['avaliacoes_de_V'] for b, v in sorted(self.braco.items())}, por_fonte=sem)
        c13 = {'membros_do_conjunto': len(self.escritor.rede), 'teste_offline_da_alocacao': self.alocacao_teste, 'testes_feitos': self.alocacao_testes['feitos'], 'testes_que_abriram_a_alocacao': self.alocacao_testes['abertos'], 'alocacao_por_desacordo_ligada_agora': self.alocacao_por_desacordo, 'pais_por_desacordo': c['pais_por_desacordo'], 'pais_por_distancia_a_D': c['pais_por_distancia_a_D'], 'pais_ao_acaso': c['pais_ao_acaso'], 'credito_por_politica': self.credito_por_politica(), 'desacordo_contra_acaso': self.comparar_politicas('desacordo', 'acaso'), 'desacordo_contra_distancia': self.comparar_politicas('desacordo', 'distancia'), 'obs': 'a média das redes decide a edição; o desacordo aloca os pais só se o critério offline (o teto do ganho de decisão é maior na metade de mais desacordo, nas piscinas que nunca treinam) admite; nunca serve para fugir para o acaso'}
        if len(self.escritor.rede) >= 2 and (self.alocacao_testes['feitos'] > 0 or c['pais_por_desacordo'] > 0):
            exercitados['13 (decidir e alocar, com a ambiguidade)'] = c13
        else:
            nao['13 (decidir e alocar, com a ambiguidade)'] = 'ainda sem o teste offline da alocação (precisa de piscinas de banco e da rede pronta: a cada `troca_cada` gerações) ou um membro só no conjunto'
        ec = self.escritor.contadores
        if ec['rodadas_de_selecao'] > 0:
            exercitados['14 (escolher-se sem perder o contexto)'] = {'rodadas_de_selecao': ec['rodadas_de_selecao'], 'trocas_de_membro_adotadas': ec['trocas_adotadas'], 'trocas_de_membro_recusadas': ec['trocas_recusadas'], 'politicas_adotadas': ec['politicas_adotadas'], 'politicas_recusadas': ec['politicas_recusadas'], 'peso_do_significado_de_agora': self.escritor.peso_semantico, 'historia_de_redes': len(self.escritor.H), 'historia_de_politicas': len(self.escritor.H_politica), 'obs': 'a memória (as fotos e o que V disse delas) e a história H ficam fora das redes; a rede nova nasce destilada do conjunto'}
        else:
            nao['14 (escolher-se sem perder o contexto)'] = 'nenhuma rodada de seleção completou ainda (precisa de piscinas de desenvolvimento e de 300 exemplos de edição)'
        if self.sementes['lotes'] > 0:
            ap_ = self.sementes['fontes']
            exercitados['15 (as sementes: a rede combina e remenda)'] = {'lotes': self.sementes['lotes'], 'moldes': self.sementes['moldes'], 'fontes': ap_, 'caminhos_imaginados_pela_rede': self.sementes['caminhos'][-5:], 'aprendida_contra_a_mao_depois_da_composicao': self.comparar_sementes('aprendida', 'a_mao', 'y_compor'), 'aprendida_contra_a_mao_depois_do_remendo': self.comparar_sementes('aprendida', 'a_mao', 'y_final'), 'aprendida_contra_a_sorteada_depois_da_composicao': self.comparar_sementes('aprendida', 'sorteada', 'y_compor'), 'aprendida_contra_a_sorteada_depois_do_remendo': self.comparar_sementes('aprendida', 'sorteada', 'y_final'), 'nos_reinicios': self.sementes['no_reinicio'], 'fracao_maxima_da_rede_no_lote': SF.FRACAO_MAXIMA_DA_APRENDIDA, 'obs': 'o crédito é medido por V no mesmo orçamento (as composições e os passos de remendo), pareado por molde; um gerador aprendido só interessa se iguala ou supera a semente feita à mão'}
        else:
            nao['15 (as sementes: a rede combina e remenda)'] = 'desligado nesta corrida (`sementes_cada` = 0)' if not self.cfg.sementes_cada else f'implementado e ainda não disparou nesta corrida: o primeiro lote vem depois de {self.cfg.sementes_cada} gerações, com a rede pronta e doadores na colheita'
        exercitados['Colheita contínua das sementes (emenda 11)'] = dict(self.colheita.resumo(), entradas_nos_saloes=self.colheita.entradas, por_clausula_no_salao=self.cfg.colheita_por_clausula, obs='a cada foto que V julga, ao longo de todas as rodadas, reinícios e retomadas: as fotos que cumprem cada cláusula, mesmo ruins no resto (menos as do conjunto final intocado)')
        if self.levantamento is not None:
            exercitados['O levantamento e o treino da intenção (emenda 11)'] = dict(self.levantamento, obs='o pré-treino aprovado: sobre qual a intenção (o veredito exato de V sobre corpus sorteados, sem busca), e não sobre como chegar lá')
        else:
            nao['O levantamento e o treino da intenção (emenda 11)'] = 'desligado nesta corrida (`n_levantamento` e `passos_da_intencao` = 0) ou ainda não rodou'
        nao['Papéis (o avaliador independente)'] = "não exercitado (decisão de 30/09: acompanhamento direto pelo responsável): papéis colapsados; o banco retido da prova cega (as famílias seladas por hash), se houver, é escrito por nós"
        nao['2 a 6 (ponto fixo, deriva, mapa das formas, domínio de M, o mundo)'] = 'o problema não os aciona nesta versão'
        nao['Funil de V (V curta)'] = 'não usado: toda foto é medida por V inteira'
        leitura = "corrida de partes da fórmula (os laços que ficaram de fora estão em 'nao_exercitados', cada um com o motivo; o avaliador independente fica de fora por decisão do responsável)"
        if not regra:
            leitura += '; o laço 16 (pétreo, emenda 6) não foi exercitado por inteiro: a seleção nesta corrida NÃO se chama seleção acelerada'
        acelerou = {'o_que_esta_corrida_pode_dizer': 'se a escrita aprendida propôs melhor que a cega nos mesmos pais (o crédito pareado abaixo)', 'credito_pareado_aprendida_contra_cega': self.comparar('aprendida', 'cega'), 'o_que_ela_nao_pode_dizer_sozinha': 'que a seleção acelerou', 'regra': "(emenda 13) 'acelerou' quer dizer que a máquina chega a D, ou a uma distância-alvo, com menos medidas de V e menos computação; só se diz com corridas independentes, com e sem a escrita aprendida, várias sementes, o mesmo orçamento total de V e toda a computação contada (V e o treino da rede). Os braços de uma corrida dividem o arquivo e a trajetória, e o crédito pareado não mede o que a máquina inteira economizou"}
        return {'problema': self.problema.nome, 'modo': self.modo, 'ok_de_gabriel': self.ok_de_gabriel, 'a_formula_inteira': False, 'a_regra_petrea': regra, 'leitura': leitura, 'a_frase_acelerou': acelerou, 'exercitados': exercitados, 'nao_exercitados': nao, 'direcao': self.direcao(), 'config': self.cfg.para_json(), 'versao_do_condutor': VERSAO_DO_CONDUTOR}

    def direcao(self):
        res = self.fotos.resumo()
        out = {'rodadas': self.rodada_n, 'geracoes': self.geracao, 'fotos': res['fotos'], 'avaliacoes_de_V': self.contadores['avaliacoes_de_V'], 'segundos': round(self.segundos(), 1), 'avaliacoes_de_V_por_hora': round(3600.0 * self.contadores['avaliacoes_de_V'] / max(self.segundos(), 1e-09), 1), 'menor_distancia': res['menor_distancia'], 'fotos_na_menor_distancia': res['fotos_na_menor_distancia'], 'curva_da_melhor_distancia (avaliações de V, distância)': self.curva_da_melhor[-60:], 'por_classe': res['por_classe'], 'por_origem': res['por_origem']}
        if self.melhor is not None:
            k = self.melhor[1]
            v = self.fotos.veredito(k)
            cl = self.problema.clausulas
            out['a_melhor_foto'] = {'id': int(k), 'distancia': int(v['distancia']), 'clausulas_que_falha': [{'clausula': cl[i][0], 'violacao': round(float(x), 4)} for i, x in enumerate(v['violacoes']) if x > 1e-09], 'clausulas_que_cumpre': [cl[i][0] for i, x in enumerate(v['violacoes']) if x <= 1e-09]}
        out['clausulas_que_nenhuma_foto_cumpre'] = {cid: {'melhor_valor': v['melhor_valor'], 'fotos_medidas': v['medidas']} for cid, v in res['por_clausula'].items() if v['cumprem'] == 0 and v['medidas'] > 0}
        out['credito_por_braco'] = self.credito_por_braco()
        out['aprendida_contra_cega'] = self.comparar('aprendida', 'cega')
        out['credito_por_politica_de_pai'] = self.credito_por_politica()
        out['sementes'] = {'lotes': self.sementes['lotes'], 'aprendida_contra_a_mao': self.comparar_sementes('aprendida', 'a_mao'), 'aprendida_contra_a_sorteada': self.comparar_sementes('aprendida', 'sorteada')}
        out['catraca'] = dict(self.catraca_est, configuracao_de_agora=self.escritor.config_de_escrita)
        out['lixo_das_edicoes'] = {'taxa_de_lixo_por_braco': {b: {'taxa_de_lixo': v['taxa_de_lixo'], 'edicoes_pagas': v['pagas']} for b, v in self.lixo.por_braco().items()}, 'alarme_a_escrita_aprendida_gasta_mais_lixo_que_a_cega': self.alarme_de_lixo}
        out['gasto_de_V_por_finalidade'] = self.gasto_de_V.para_json()
        return out

    def salvar(self, final=False):
        _gravar(os.path.join(self.saida, 'estado.json'), {'rodada': self.rodada_n, 'geracao': self.geracao, 'reinicios': self.reinicios, 'plato': self.plato, 'segundos': round(self.segundos(), 1), 'contadores': self.contadores, 'braco': self.braco, 'melhor_por_rodada': self.melhor_por_rodada[-20000:], 'tentativas': {str(k): v for k, v in self.tentativas.items()}, 'curva_do_escritor': self.curva_do_escritor[-300:], 'curva_da_melhor': self.curva_da_melhor[-2000:], 'hash_de_v': self.hash_de_v, 'parada': self.parada, 'calibracao_ok': None if self.calibracao is None else bool(self.calibracao.get('ok')), 'testemunhas_medidas': self.testemunhas_medidas, 'politicas': self.politicas, 'alocacao_por_desacordo': self.alocacao_por_desacordo, 'alocacao_teste': self.alocacao_teste, 'alocacao_testes': self.alocacao_testes, 'sementes': self.sementes, 'catraca_est': self.catraca_est, 'H_cfg': self.H_cfg[-2000:], 'cfg_anterior': self.cfg_anterior, 'cfg_inicial': self.cfg_inicial, 'moldes_de_confirmacao_usados': sorted(self.moldes_de_confirmacao_usados), 'gasto_de_V': self.gasto_de_V.para_json(), 'lixo': self.lixo.para_json(), 'alarme_de_lixo': self.alarme_de_lixo, 'leitura_final': self.leitura_final_feita, 'levantamento': self.levantamento, 'selo_inicial': self.selo_inicial, 'migracoes_do_hash': self.migracoes_do_hash, 'selo_do_banco': self.selo_do_banco, 'hashes_dos_oraculos': self.hashes_dos_oraculos, 'estouros': self.estouros, 'confirmacao_um_em_na_partida': self.confirmacao_um_em_na_partida, 'versao_do_condutor': VERSAO_DO_CONDUTOR, 'v2': {'sal': self.sal, 'confirmadas': sorted(self.confirmadas), 'margens': {str(k): v for k, v in self.margens.items()}} if self.v2 else None})
        agora = time.time()
        if final or agora - self._t_salvar >= self.cfg.salvar_cada:
            self._t_salvar = agora
            self.fotos.salvar(os.path.join(self.saida, 'fotos'))
            self.edicoes.salvar(os.path.join(self.saida, 'edicoes'))
            self.escritor.salvar(self.saida)
            if self.mapa is not None:
                self.mapa.salvar()
        if not final and agora - self._t_declaracao >= self.cfg.declaracao_cada:
            self._t_declaracao = agora
            try:
                _gravar(os.path.join(self.saida, 'declaracao_parcial.json'), self.declaracao())
            except Exception as e:
                self.contadores['erros_na_declaracao_parcial'] += 1
                self._evento({'evento': 'erro_na_declaracao_parcial', 'erro': repr(e)[:200]})

    def _retomar(self):
        pe = os.path.join(self.saida, 'estado.json')
        if not os.path.exists(pe) or len(self.fotos) == 0:
            return False
        try:
            est = json.load(open(pe, encoding='utf-8'))
        except (OSError, ValueError):
            return False
        self.rodada_n, self.geracao, self.reinicios, self.plato = (est['rodada'], est['geracao'], est.get('reinicios', 0), est.get('plato', 0))
        self.seg_anteriores = est.get('segundos', 0.0)
        self.contadores.update(est.get('contadores', {}))
        self.braco = est.get('braco', {})
        self.melhor_por_rodada = est.get('melhor_por_rodada', [])
        self.tentativas = {int(k): v for k, v in est.get('tentativas', {}).items()}
        self.curva_do_escritor = est.get('curva_do_escritor', [])
        self.curva_da_melhor = [tuple(x) for x in est.get('curva_da_melhor', [])]
        self.testemunhas_medidas = est.get('testemunhas_medidas', {})
        self.hash_de_v = est.get('hash_de_v')
        if self.v2 and est.get('v2'):
            self.sal = int(est['v2'].get('sal', 0))
            self.confirmadas = set((int(k) for k in est['v2'].get('confirmadas', [])))
            self.margens = {int(k): float(v) for k, v in est['v2'].get('margens', {}).items()}
        self.selo_do_banco = est.get('selo_do_banco')
        self.hashes_dos_oraculos = est.get('hashes_dos_oraculos')
        self.politicas = est.get('politicas', {})
        self.alocacao_por_desacordo = bool(est.get('alocacao_por_desacordo', False))
        self.alocacao_teste = est.get('alocacao_teste')
        self.alocacao_testes = est.get('alocacao_testes', self.alocacao_testes)
        self.sementes = est.get('sementes', self.sementes)
        self.catraca_est = est.get('catraca_est', self.catraca_est)
        self.H_cfg = est.get('H_cfg', [])
        self.cfg_anterior = est.get('cfg_anterior')
        self.cfg_inicial = est.get('cfg_inicial', self.cfg_inicial)
        self.moldes_de_confirmacao_usados = set(est.get('moldes_de_confirmacao_usados', []))
        self.gasto_de_V = CV.GastoDeV.de_json(est.get('gasto_de_V'))
        self.lixo = CV.LixoDasEdicoes.de_json(est.get('lixo'), self.cfg.lixo_muito_pior)
        self.alarme_de_lixo = bool(est.get('alarme_de_lixo', False))
        self.leitura_final_feita = est.get('leitura_final')
        self.levantamento = est.get('levantamento')
        self.selo_inicial = est.get('selo_inicial')
        self.migracoes_do_hash = list(est.get('migracoes_do_hash', []))
        self.estouros = dict(self.estouros, **est.get('estouros', {}))
        self.confirmacao_um_em_na_partida = est.get('confirmacao_um_em_na_partida')
        self.escritor.carregar(self.saida, semente=self.cfg.semente)
        self._remarcar_finais()
        self.colheita.refazer(self.fotos, excluir=self._mascara_reservada())
        self._refazer_o_mapa()
        self.pais_vistos = set((int(i) for i in self.escritor.mem.coluna('pai'))) | {it.pai for it in self.escritor.piscinas.itens} | set(self.tentativas) | set(self.moldes_de_confirmacao_usados)
        d = self.fotos.distancias()
        ok = np.flatnonzero(d >= 0)
        if len(ok):
            k = int(ok[np.argmin(d[ok])])
            self.melhor = (int(d[k]), k)
            if self._avanco_pela_prioridade():
                ch = self._chave_de_nivel(ok)
                j = int(ok[np.lexsort((d[ok], ch))[0]])
                self.melhor_chave = ((int(ch[ok == j][0] // 10 ** 7), int(d[j])), j)
        self.g = np.random.default_rng(self.cfg.semente * 7919 + self.rodada_n)
        self._evento({'evento': 'retomada', 'fotos': len(self.fotos), 'rodadas': self.rodada_n, 'melhor_distancia': None if self.melhor is None else self.melhor[0]})
        return True

    def _refazer_o_mapa(self):
        if self.mapa is None:
            return
        reservada = self._mascara_reservada()
        ok = [int(k) for k in np.flatnonzero(self.fotos.distancias() >= 0) if not (k < len(reservada) and reservada[k])]
        self.mapa.antecipar([self.fotos.foto(k) for k in ok], processos=max(int(self.cfg.mapa_processos), (os.cpu_count() or 2) - 1) if self.cfg.mapa_processos else 0)
        chaves = self._chave_de_nivel(np.asarray(ok, np.int64)) if ok else []
        for k, ch in zip(ok, chaves):
            self.mapa.entrar(k, self.fotos.foto(k), int(ch))
        self.mapa.fechar()
        self.mapa.salvar()
        self._evento(dict(self.mapa.resumo(), evento='mapa_refeito'))

    def _imprimir(self):
        if time.time() - self._t_imprimir >= self.cfg.imprimir_cada:
            self._t_imprimir = time.time()
            res = self.fotos.resumo()
            print(f"[{self.segundos():7.0f}s] rodada {self.rodada_n} g{self.geracao} fotos {res['fotos']} V {self.contadores['avaliacoes_de_V']:,} menor distância {res['menor_distancia']} (nas {res['fotos_na_menor_distancia']}) mem {self.escritor.mem.proprios()} bib {self.escritor.biblioteca.tamanho()} pronto {self.escritor.pronto()}" + ('  ALARME: a escrita aprendida gasta mais lixo que a às cegas' if self.alarme_de_lixo else ''), flush=True)

    def _registrar_o_selo_do_banco(self):
        if getattr(self.problema, 'hashes_dos_oraculos', None) is not None and self.hashes_dos_oraculos is None:
            self.hashes_dos_oraculos = self.problema.hashes_dos_oraculos()
        caminho = getattr(self.problema, 'selo_do_banco', None)
        if not caminho:
            return True
        if os.path.exists(caminho):
            try:
                selo = json.load(open(caminho, encoding='utf-8'))
                agora = {'selado': True, 'hash_do_selo': selo['hash_do_selo'], 'semente': selo.get('semente'), 'vidas_por_familia': selo.get('vidas_por_familia'), 'arquivo': os.path.basename(caminho), 'versao': selo.get('versao')}
            except (OSError, ValueError, KeyError):
                agora = {'selado': False, 'motivo': 'o arquivo do selo não lê'}
        else:
            agora = {'selado': False, 'motivo': 'o arquivo do selo não existe'}
        if self.selo_do_banco is not None and self.selo_do_banco.get('hash_do_selo') != agora.get('hash_do_selo'):
            self._evento({'evento': 'selo_do_banco_mudou', 'antes': self.selo_do_banco, 'agora': agora})
            return False
        self.selo_do_banco = agora
        self._evento({'evento': 'selo_do_banco', **agora})
        return bool(agora['selado'] or not getattr(self.problema, 'exige_selo', False))

    def rodar(self):
        cfg = self.cfg
        self.retomada = self._retomar()
        m = self.migracao_do_hash
        if m and self.retomada and (self.problema.hash_de_v is not None) and (self.hash_de_v == m.get('de')) and (self.problema.hash_de_v() == m.get('para')):
            selo_antes = self.selo_inicial
            self.hash_de_v = m['para']
            self.selo_inicial = self._selo()
            reg = {'de': m['de'], 'para': m['para'], 'prova': m.get('prova', ''), 'selo_antes': selo_antes, 'selo_depois': self.selo_inicial, 'rodada': self.rodada_n}
            self.migracoes_do_hash.append(reg)
            self._evento(dict(reg, evento='hash_de_v_migrado'))
        if self.problema.hash_de_v is not None and self.hash_de_v is None:
            self.hash_de_v = self.problema.hash_de_v()
        if self.selo_inicial is None:
            self.selo_inicial = self._selo()
        if self.problema.calibrar is not None:
            self.calibracao = self.problema.calibrar()
            self._evento({'evento': 'calibracao', 'ok': bool(self.calibracao.get('ok'))})
            if not self.calibracao.get('ok'):
                self.parada = 'instrumento'
                print('O instrumento falhou nos controles (Cal): a busca não começa.', flush=True)
                self._fechar()
                return
        if self.problema.hash_de_v is not None and self.problema.hash_de_v() != self.hash_de_v:
            self.parada = 'instrumento'
            self._evento({'evento': 'hash_de_v_mudou', 'antes': self.hash_de_v, 'agora': self.problema.hash_de_v()})
            self._fechar()
            return
        if not self._registrar_o_selo_do_banco():
            self.parada = 'instrumento'
            print('O banco retido da prova cega não está selado (ou o selo mudou desde a partida): a busca não começa.', flush=True)
            self._fechar()
            return
        try:
            if not self.retomada:
                self.confirmacao_um_em_na_partida = int(cfg.confirmacao_um_em)
                self._ler_o_eixo()
                self._partida()
                self._medir_testemunhas()
                self._levantamento()
                self._aquecer()
            else:
                self._medir_testemunhas()
                faltam = int(cfg.aquecimento_piscinas) - int(self.contadores.get('piscinas_rotuladas', 0)) if self.rodada_n == 0 else 0
                if faltam > 0:
                    self._evento({'evento': 'aquecimento_retomado', 'feitas': int(self.contadores.get('piscinas_rotuladas', 0)), 'faltam': faltam})
                    self._rotular(faltam, 'aquecimento (piscinas antes da 1ª rodada)')
                    self._evento({'evento': 'aquecimento_do_escritor', 'piscinas': self.cfg.aquecimento_piscinas, 'exemplos': self.escritor.mem.proprios(), 'pronto': self.escritor.pronto()})
            self._recuperar_doadoras()
            self._doar_testemunhas()
            if cfg.rotulo_por_d:
                self.escritor.definir_rotulo_por_d(self._indices_da_prioridade(), cfg.rotulo_w, cfg.rotulo_lambda)
                self._evento({'evento': 'rotulo_por_d', 'indices': list(self._indices_da_prioridade()), 'W': cfg.rotulo_w, 'LAMBDA': cfg.rotulo_lambda, 'refeitos': self.escritor.reetiquetar()})
            self._evento({'evento': 'inicio', 'retomada': self.retomada, 'fotos': len(self.fotos), 'config': cfg.para_json()})
            while not self.parada:
                if cfg.tempo is not None and self.segundos() >= cfg.tempo:
                    self.parada = 'fusível de tempo: não encontrado no orçamento'
                    break
                if cfg.max_rodadas and self.rodada_n >= cfg.max_rodadas:
                    self.parada = 'fusível de rodadas: não encontrado no orçamento'
                    break
                for _ in range(cfg.rodadas_por_geracao):
                    if self.parada:
                        break
                    self.rodada()
                    self._coletar_se_devido()
                self.fim_de_geracao()
                self.salvar()
                self._imprimir()
                self._parada_pedida()
        finally:
            self._fechar()

    def _parada_pedida(self):
        pedido = os.path.join(self.saida, 'PARAR')
        if os.path.exists(pedido) and (not self.parada):
            self.parada = 'pedido de parada (arquivo PARAR): retomável'
            os.replace(pedido, pedido + '.atendido')
            self._evento({'evento': 'parada_pedida'})

    def _fechar(self):
        if self.cfg.leitura_final and self._parada_final():
            try:
                self._ultima_leitura_final = self.leitura_final()
            except Exception as e:
                self._evento({'evento': 'erro_na_leitura_final', 'erro': repr(e)[:200]})
        try:
            self.salvar(final=True)
        finally:
            dec = self.declaracao()
            fim = {'problema': self.problema.nome, 'rodadas': self.rodada_n, 'geracoes': self.geracao, 'fotos': len(self.fotos), 'segundos': round(self.segundos(), 1), 'parada': self.parada, 'contadores': self.contadores, 'credito_por_braco': self.credito_por_braco(), 'aprendida_contra_cega': self.comparar('aprendida', 'cega'), 'direcao': self.direcao(), 'a_regra_petrea': dec['a_regra_petrea'], 'eventos': [e for e in self.eventos if e.get('evento') != 'geracao'][-50:]}
            try:
                _gravar(os.path.join(self.saida, 'padroes.json'), {'escritor': self.escritor.padroes(self.fotos), 'fotos': self.fotos.resumo(), 'curva_de_aprendizado': self.curva_do_escritor, 'credito_por_braco': self.credito_por_braco()})
            except Exception as e:
                self.contadores['erros_nos_padroes'] += 1
                fim['contadores'] = self.contadores
                self._evento({'evento': 'erro_nos_padroes', 'erro': repr(e)[:200]})
            _gravar(os.path.join(self.saida, 'declaracao.json'), dec)
            _gravar(os.path.join(self.saida, 'resumo.json'), fim)
            if self.mapa is not None:
                _gravar(os.path.join(self.saida, 'mapa.json'), self.mapa.resumo(lambda k: self.fotos.distancias()[k]))
                self.mapa.fechar()
            self.log_r.close()
            self.log_e.close()
            self.log_t.close()
