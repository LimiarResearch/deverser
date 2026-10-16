# -*- coding: utf-8 -*-
import math
import numpy as np
from experimentos import foto_atomica as FA
VERSAO_DA_CODIFICACAO = 1
K_NOS = 8
BITS_OP, BITS_ARG, BITS_CONST = (5, 6, 8)
BITS_NO = BITS_OP + BITS_ARG + BITS_ARG + BITS_CONST
NIVEIS = 256
CL = 1000.0
EPS = 1e-06
OPS = [('add', 2, False, True), ('sub', 2, False, False), ('mul', 2, False, True), ('div', 2, False, False), ('max', 2, False, True), ('min', 2, False, True), ('neg', 1, False, False), ('abs', 1, False, False), ('sq', 1, False, False), ('sqrt', 1, False, False), ('tanh', 1, False, False), ('relu', 1, False, False), ('sig', 1, False, False), ('thr', 1, False, False), ('sign', 1, False, False), ('exp', 1, False, False), ('log', 1, False, False), ('inv', 1, False, False), ('avg', 2, False, True), ('k', 0, True, False), ('mulk', 1, True, False), ('addk', 1, True, False), ('gt', 2, False, False), ('absdiff', 2, False, True), ('mean0', 1, False, False), ('mean1', 1, False, False), ('clip1', 1, False, False), ('ema', 2, True, False), ('shrk', 1, True, False), ('hyp', 2, False, True), ('sel', 2, False, False), ('id', 1, False, False)]
N_OPS = len(OPS)
NOME_DA_OP = [o[0] for o in OPS]
OP_DE = {o[0]: i for i, o in enumerate(OPS)}
ARIDADE = [o[1] for o in OPS]
USA_C = [o[2] for o in OPS]
COMUTATIVA = [o[3] for o in OPS]
C_LO, C_HI = (0.0001, 10.0)

def valor_da_constante(q):
    return float(math.exp(math.log(C_LO) + int(q) / (NIVEIS - 1.0) * (math.log(C_HI) - math.log(C_LO))))

def nivel_da_constante(v):
    v = min(max(float(v), C_LO), C_HI)
    return int(min(max(round((math.log(v) - math.log(C_LO)) / (math.log(C_HI) - math.log(C_LO)) * (NIVEIS - 1)), 0), NIVEIS - 1))
ENTRADAS = {'peso': ['zero', 'um', 'w', 'P', 'Q', 'P2', 'Q2', 'pre', 'post', 'err', 'pre2', 'post2', 'err2', 'S1', 'S2', 'S3', 'U1', 'U2', 'G1', 'G2', 't', 'xi', 'prof'], 'retro': ['zero', 'um', 'T', 's', 'a', 'u1', 'u2', 'g1', 'g2', 't', 'perda', 'conf', 'enorm'], 'unid': ['zero', 'um', 'post', 'post2', 'err', 'err2', 'inn', 'outn', 'u1', 'u2', 'idade', 'g1', 'g2', 't'], 'glob': ['zero', 'um', 'perda', 'acerto', 'enorm', 'conf', 'g1', 'g2', 't', 'wnorm', 'ativas'], 'pol': ['zero', 'um', 'conf', 'marg', 'ent', 'nov', 'g1', 'g2', 't']}
SECOES = [('RETRO', 'retro'), ('W_OCULTA', 'peso'), ('W_SAIDA', 'peso'), ('S1', 'peso'), ('S2', 'peso'), ('S3', 'peso'), ('U1', 'unid'), ('U2', 'unid'), ('REINIT', 'unid'), ('ATIVA', 'unid'), ('LIBERA', 'unid'), ('G1', 'glob'), ('G2', 'glob'), ('POL1', 'pol'), ('POL2', 'pol'), ('POL3', 'pol')]
NOMES_DAS_SECOES = [s[0] for s in SECOES]
TIPO_DA_SECAO = {s[0]: s[1] for s in SECOES}
N_SECOES = len(SECOES)
N_ENTRADAS = {t: len(v) for t, v in ENTRADAS.items()}
ATIVACOES = ('relu', 'tanh', 'softsign', 'leaky')
LOTES = (1, 2, 4, 8)
CADAS = (1, 2, 4, 8, 16, 32, 64, 128)
INIT_S = ('zeros', 'uns', 'copia_de_w', 'ruido')
INIT_U = ('zeros', 'uns', 'meio', 'uniforme')
INIT_G = ('zero', 'um')
SEMENTE_MAX = 9999
FAIXAS = {'ativas0': (0.25, 1.0, 'lin'), 'porta_entrada': (0.25, 1.0, 'lin'), 'densidade': (0.25, 1.0, 'lin'), 'escala_init': (0.25, 2.0, 'log')}

def _gray(q):
    return q ^ q >> 1

def _gray_inv(g):
    q = g
    s = g >> 1
    while s:
        q ^= s
        s >>= 1
    return q

def _montar_campos():
    campos = []
    pos = [0]

    def add(nome, grupo, tipo, bits, **extra):
        campos.append(dict({'nome': nome, 'grupo': grupo, 'tipo': tipo, 'bits': bits, 'inicio': pos[0]}, **extra))
        pos[0] += bits
    add('tecido.n_camadas', 0, 'ncam', 2)
    for i in range(3):
        add(f'tecido.largura_{i + 1}', 0, 'larg', 7, indice=i)
    for i in range(3):
        add(f'tecido.ativ_{i + 1}', 0, 'cat', 2, chave='ativ', indice=i, opcoes=ATIVACOES)
    for k in ('ativas0', 'porta_entrada', 'densidade', 'escala_init'):
        add(f'tecido.{k}', 0, 'num', 8, chave=k)
    add('tecido.lote', 0, 'cat', 2, chave='lote', opcoes=LOTES)
    add('tecido.cada', 0, 'cat', 3, chave='cada', opcoes=CADAS)
    add('tecido.semente', 0, 'semente', 14, chave='semente')
    add('tecido.pol_padrao', 0, 'cat', 2, chave='pol_padrao', opcoes=(0, 1, 2, 3))
    for k in (1, 2, 3):
        add(f'tecido.init_S{k}', 0, 'cat', 2, chave=f'init_S{k}', opcoes=INIT_S)
    for k in (1, 2):
        add(f'tecido.init_U{k}', 0, 'cat', 2, chave=f'init_U{k}', opcoes=INIT_U)
    for k in (1, 2):
        add(f'tecido.init_G{k}', 0, 'cat', 1, chave=f'init_G{k}', opcoes=INIT_G)
    n_cab = pos[0]
    for s, (nome, tipo) in enumerate(SECOES, start=1):
        add(f'{nome}.presente', s, 'presenca', 1, secao=nome)
        for n in range(K_NOS):
            add(f'{nome}.n{n}.op', s, 'op', BITS_OP, secao=nome, no=n)
            add(f'{nome}.n{n}.a', s, 'arg', BITS_ARG, secao=nome, no=n, qual='a')
            add(f'{nome}.n{n}.b', s, 'arg', BITS_ARG, secao=nome, no=n, qual='b')
            add(f'{nome}.n{n}.c', s, 'const', BITS_CONST, secao=nome, no=n)
        if tipo == 'pol':
            add(f'{nome}.rotulo', s, 'rotulo', 2, secao=nome)
    return (campos, pos[0], n_cab)
CAMPOS, N_BITS, N_BITS_CABECALHO = _montar_campos()
NOMES_DOS_GRUPOS = ['tecido'] + NOMES_DAS_SECOES
_POR_NOME = {c['nome']: c for c in CAMPOS}

def _ler(b, c):
    v = 0
    for x in b[c['inicio']:c['inicio'] + c['bits']]:
        v = v << 1 | int(x)
    return v

def _escrever(b, c, v):
    n = c['bits']
    for t in range(n):
        b[c['inicio'] + t] = int(v) >> n - 1 - t & 1

def _faixa(chave, q):
    lo, hi, esc = FAIXAS[chave]
    x = q / (NIVEIS - 1.0)
    return float(math.exp(math.log(lo) + x * (math.log(hi) - math.log(lo)))) if esc == 'log' else float(lo + x * (hi - lo))

def _nivel_da_faixa(chave, v):
    lo, hi, esc = FAIXAS[chave]
    v = min(max(float(v), lo), hi)
    x = (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) if esc == 'log' else (v - lo) / (hi - lo)
    return int(min(max(round(x * (NIVEIS - 1)), 0), NIVEIS - 1))

class No:
    __slots__ = ('op', 'a', 'b', 'c')

    def __init__(self, op=0, a=0, b=0, c=0):
        self.op, self.a, self.b, self.c = (int(op), int(a), int(b), int(c))

    def como_tupla(self):
        return (self.op, self.a, self.b, self.c)

class Programa:

    def __init__(self, tecido, secoes, rotulos=None):
        self.tecido = tecido
        self.secoes = secoes
        self.rotulos = rotulos or {}

    def chave(self):
        return (tuple(sorted(((k, tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in self.tecido.items()))), tuple(((n, None if self.secoes[n] is None else tuple((x.como_tupla() for x in self.secoes[n]))) for n in NOMES_DAS_SECOES)), tuple(sorted(self.rotulos.items())))

    def __eq__(self, o):
        return isinstance(o, Programa) and self.chave() == o.chave()

    def __hash__(self):
        return hash(self.chave())

def _avail(tipo, n):
    return N_ENTRADAS[tipo] + n

def _nos_vivos(nos, tipo):
    n_in = N_ENTRADAS[tipo]
    vivos = set()
    pilha = [len(nos) - 1]
    while pilha:
        i = pilha.pop()
        if i in vivos:
            continue
        vivos.add(i)
        no = nos[i]
        ar = ARIDADE[no.op]
        for arg, usa in ((no.a, ar >= 1), (no.b, ar >= 2)):
            if usa and arg >= n_in:
                pilha.append(arg - n_in)
    nomes = ENTRADAS[tipo]
    lidas = set()
    for i in vivos:
        no = nos[i]
        ar = ARIDADE[no.op]
        for arg, usa in ((no.a, ar >= 1), (no.b, ar >= 2)):
            if usa and arg < n_in:
                lidas.add(nomes[arg])
    return (vivos, lidas)

def _ler_secao(b, nome):
    tipo = TIPO_DA_SECAO[nome]
    nos = []
    for n in range(K_NOS):
        op = _ler(b, _POR_NOME[f'{nome}.n{n}.op']) % N_OPS
        av = _avail(tipo, n)
        a = _ler(b, _POR_NOME[f'{nome}.n{n}.a']) % av
        bb = _ler(b, _POR_NOME[f'{nome}.n{n}.b']) % av
        c = _ler(b, _POR_NOME[f'{nome}.n{n}.c'])
        nos.append(No(op, a, bb, c))
    return nos

def _canonizar_no(no, tipo, n):
    ar = ARIDADE[no.op]
    a, b, c = (no.a, no.b, no.c)
    if ar < 1:
        a = 0
    if ar < 2:
        b = 0
    if ar == 2 and COMUTATIVA[no.op] and (a > b):
        a, b = (b, a)
    if not USA_C[no.op]:
        c = 0
    return No(no.op, a, b, c)

def _tecido_de(b):
    T = {}
    T['n_camadas'] = min(_ler(b, _POR_NOME['tecido.n_camadas']), 2) + 1
    T['larguras'] = [8 + min(_gray_inv(_ler(b, _POR_NOME[f'tecido.largura_{i + 1}'])), 120) for i in range(3)]
    T['ativ'] = [ATIVACOES[_ler(b, _POR_NOME[f'tecido.ativ_{i + 1}']) % len(ATIVACOES)] for i in range(3)]
    for k in ('ativas0', 'porta_entrada', 'densidade', 'escala_init'):
        T[k] = _faixa(k, _gray_inv(_ler(b, _POR_NOME[f'tecido.{k}'])))
    T['lote'] = LOTES[_ler(b, _POR_NOME['tecido.lote']) % len(LOTES)]
    T['cada'] = CADAS[_ler(b, _POR_NOME['tecido.cada']) % len(CADAS)]
    T['semente'] = min(_ler(b, _POR_NOME['tecido.semente']), SEMENTE_MAX)
    T['pol_padrao'] = _ler(b, _POR_NOME['tecido.pol_padrao']) % 4
    for k in (1, 2, 3):
        T[f'init_S{k}'] = INIT_S[_ler(b, _POR_NOME[f'tecido.init_S{k}']) % len(INIT_S)]
    for k in (1, 2):
        T[f'init_U{k}'] = INIT_U[_ler(b, _POR_NOME[f'tecido.init_U{k}']) % len(INIT_U)]
    for k in (1, 2):
        T[f'init_G{k}'] = INIT_G[_ler(b, _POR_NOME[f'tecido.init_G{k}']) % len(INIT_G)]
    return T
_VARS_DA_FENDA = {'S1': ('S1',), 'S2': ('S2',), 'S3': ('S3',), 'U1': ('U1', 'u1'), 'U2': ('U2', 'u2'), 'G1': ('G1', 'g1'), 'G2': ('G2', 'g2')}
_CONSUMIDORES_DA_VOLTA = ('W_OCULTA', 'S1', 'S2', 'S3', 'U1', 'U2', 'REINIT', 'ATIVA', 'LIBERA')
_VARS_DA_VOLTA = ('P', 'P2', 'err', 'err2')

def _analisar(b):
    T = _tecido_de(b)
    nos = {}
    for nome in NOMES_DAS_SECOES:
        presente = bool(b[_POR_NOME[f'{nome}.presente']['inicio']])
        nos[nome] = _ler_secao(b, nome) if presente else None
    ativa = {n: nos[n] is not None for n in NOMES_DAS_SECOES}
    while True:
        vivos, lidas = ({}, {})
        for nome in NOMES_DAS_SECOES:
            if ativa[nome]:
                vivos[nome], lidas[nome] = _nos_vivos(nos[nome], TIPO_DA_SECAO[nome])
        mudou = False
        for fenda, variaveis in _VARS_DA_FENDA.items():
            if ativa[fenda] and (not any((v in lidas[o] for o in lidas if o != fenda for v in variaveis))):
                ativa[fenda] = False
                mudou = True
        if ativa['RETRO'] and (not any((v in lidas[o] for o in _CONSUMIDORES_DA_VOLTA if o in lidas for v in _VARS_DA_VOLTA))):
            ativa['RETRO'] = False
            mudou = True
        if not mudou:
            break
    for nome in NOMES_DAS_SECOES:
        if not ativa[nome]:
            nos[nome] = None
    return (T, nos, {n: vivos[n] for n in vivos if ativa[n]}, {n: lidas[n] for n in lidas if ativa[n]})

def decodificar_bits(bits):
    b = np.asarray(bits, np.uint8)
    if len(b) != N_BITS:
        raise ValueError(f'a foto do Ser tem {N_BITS} bits, e vieram {len(b)}')
    T, nos, vivos, lidas = _analisar(b)
    secoes = {}
    for nome in NOMES_DAS_SECOES:
        if nos[nome] is None:
            secoes[nome] = None
            continue
        tipo = TIPO_DA_SECAO[nome]
        lista = []
        for n, no in enumerate(nos[nome]):
            lista.append(_canonizar_no(no, tipo, n) if n in vivos[nome] else No(0, 0, 0, 0))
        secoes[nome] = lista
    rotulos = {n: _ler(b, _POR_NOME[f'{n}.rotulo']) % 4 for n in ('POL1', 'POL2', 'POL3') if secoes[n] is not None}
    n = T['n_camadas']
    for i in range(n, 3):
        T['larguras'][i] = 8
        T['ativ'][i] = ATIVACOES[0]
    T['larguras'] = T['larguras'][:3]
    if n < 2:
        T['densidade'] = _faixa('densidade', 0)
    if not any((secoes[g] is not None for g in ('REINIT', 'ATIVA', 'LIBERA'))):
        T['cada'] = CADAS[0]
    for k in (1, 2, 3):
        if secoes[f'S{k}'] is None:
            T[f'init_S{k}'] = INIT_S[0]
    for k in (1, 2):
        if secoes[f'U{k}'] is None:
            T[f'init_U{k}'] = INIT_U[0]
        if secoes[f'G{k}'] is None:
            T[f'init_G{k}'] = INIT_G[0]
    return Programa(T, secoes, rotulos)

def _escrever_programa(prog):
    b = np.zeros(N_BITS, np.uint8)
    T = prog.tecido
    _escrever(b, _POR_NOME['tecido.n_camadas'], T['n_camadas'] - 1)
    for i in range(3):
        _escrever(b, _POR_NOME[f'tecido.largura_{i + 1}'], _gray(int(min(max(T['larguras'][i], 8), 128)) - 8) if i < T['n_camadas'] else 0)
        _escrever(b, _POR_NOME[f'tecido.ativ_{i + 1}'], ATIVACOES.index(T['ativ'][i]) if i < T['n_camadas'] else 0)
    for k in ('ativas0', 'porta_entrada', 'densidade', 'escala_init'):
        _escrever(b, _POR_NOME[f'tecido.{k}'], _gray(_nivel_da_faixa(k, T[k])))
    _escrever(b, _POR_NOME['tecido.lote'], LOTES.index(T['lote']))
    _escrever(b, _POR_NOME['tecido.cada'], CADAS.index(T['cada']))
    _escrever(b, _POR_NOME['tecido.semente'], int(min(max(T['semente'], 0), SEMENTE_MAX)))
    _escrever(b, _POR_NOME['tecido.pol_padrao'], T['pol_padrao'])
    for k in (1, 2, 3):
        _escrever(b, _POR_NOME[f'tecido.init_S{k}'], INIT_S.index(T[f'init_S{k}']))
    for k in (1, 2):
        _escrever(b, _POR_NOME[f'tecido.init_U{k}'], INIT_U.index(T[f'init_U{k}']))
        _escrever(b, _POR_NOME[f'tecido.init_G{k}'], INIT_G.index(T[f'init_G{k}']))
    for nome in NOMES_DAS_SECOES:
        nos = prog.secoes[nome]
        if nos is None:
            continue
        b[_POR_NOME[f'{nome}.presente']['inicio']] = 1
        for n, no in enumerate(nos):
            _escrever(b, _POR_NOME[f'{nome}.n{n}.op'], no.op)
            _escrever(b, _POR_NOME[f'{nome}.n{n}.a'], no.a)
            _escrever(b, _POR_NOME[f'{nome}.n{n}.b'], no.b)
            _escrever(b, _POR_NOME[f'{nome}.n{n}.c'], no.c)
        if TIPO_DA_SECAO[nome] == 'pol':
            _escrever(b, _POR_NOME[f'{nome}.rotulo'], prog.rotulos.get(nome, 0))
    return b

def canonizar_bits(bits):
    return _escrever_programa(decodificar_bits(bits))

def codificar_programa(prog):
    return canonizar_bits(_escrever_programa(prog))

def bits_ativos(bits):
    b = np.asarray(bits, np.uint8)
    T, nos, vivos, lidas = _analisar(b)
    m = np.zeros(N_BITS, bool)
    n = T['n_camadas']
    tem_guarda = any((nos[g] is not None for g in ('REINIT', 'ATIVA', 'LIBERA')))
    for c in CAMPOS:
        if c['grupo'] != 0:
            continue
        nome = c['nome'].split('.', 1)[1]
        ativo = True
        if c['tipo'] == 'larg' or (c['tipo'] == 'cat' and c.get('chave') == 'ativ'):
            ativo = c['indice'] < n
        elif nome == 'densidade':
            ativo = n >= 2
        elif nome == 'cada':
            ativo = tem_guarda
        elif nome.startswith('init_S'):
            ativo = nos[nome[5:]] is not None
        elif nome.startswith('init_U') or nome.startswith('init_G'):
            ativo = nos[nome[5:]] is not None
        m[c['inicio']:c['inicio'] + c['bits']] = ativo
    for nome in NOMES_DAS_SECOES:
        tipo = TIPO_DA_SECAO[nome]
        m[_POR_NOME[f'{nome}.presente']['inicio']] = True
        if nos[nome] is None:
            continue
        for i in vivos[nome]:
            no = nos[nome][i]
            ar = ARIDADE[no.op]
            m[_POR_NOME[f'{nome}.n{i}.op']['inicio']:_POR_NOME[f'{nome}.n{i}.op']['inicio'] + BITS_OP] = True
            if ar >= 1:
                c = _POR_NOME[f'{nome}.n{i}.a']
                m[c['inicio']:c['inicio'] + c['bits']] = True
            if ar >= 2:
                c = _POR_NOME[f'{nome}.n{i}.b']
                m[c['inicio']:c['inicio'] + c['bits']] = True
            if USA_C[no.op]:
                c = _POR_NOME[f'{nome}.n{i}.c']
                m[c['inicio']:c['inicio'] + c['bits']] = True
        if tipo == 'pol':
            c = _POR_NOME[f'{nome}.rotulo']
            m[c['inicio']:c['inicio'] + c['bits']] = True
    return m

class CodificacaoDoSer(FA.CodificacaoBase):
    nome = 'L do Ser (L0)'
    versao = VERSAO_DA_CODIFICACAO
    n_bits = N_BITS
    campos = CAMPOS
    nomes_dos_grupos = NOMES_DOS_GRUPOS

    def decodificar(self, bits):
        return decodificar_bits(bits)

    def codificar(self, corpus):
        return codificar_programa(corpus)

    def canonizar(self, bits):
        return canonizar_bits(bits)

    def ativos(self, bits):
        return bits_ativos(bits)

    def sortear(self, rng, p_secao=0.5, p_peso=0.9):
        b = rng.integers(0, 2, N_BITS).astype(np.uint8)
        for nome in NOMES_DAS_SECOES:
            b[_POR_NOME[f'{nome}.presente']['inicio']] = 1 if rng.random() < (p_peso if nome in ('W_SAIDA',) else p_secao) else 0
        return canonizar_bits(b)

    def valores_dos_campos(self, bits):
        b = np.asarray(bits, np.uint8)
        out = np.zeros(len(CAMPOS), np.float32)
        for i, c in enumerate(CAMPOS):
            v = _ler(b, c)
            out[i] = v / float((1 << c['bits']) - 1)
        return out

    def grupos_presentes(self, bits):
        _, nos, _, _ = _analisar(np.asarray(bits, np.uint8))
        return np.array([1 if nos[n] is not None else 0 for n in NOMES_DAS_SECOES], np.uint8)

    def escalar_do_cabecalho(self, bits):
        return float(min(_ler(np.asarray(bits, np.uint8), _POR_NOME['tecido.n_camadas']), 2) + 1) / 3.0

    def resumo(self, bits):
        b = np.asarray(bits, np.uint8)
        at = bits_ativos(b)
        _, nos, vivos, _ = _analisar(b)
        out = np.zeros(2 * len(NOMES_DOS_GRUPOS), np.float32)
        mp = self.mapas()
        for g in range(len(NOMES_DOS_GRUPOS)):
            m = mp['grupo_de'] == g
            out[2 * g] = float(at[m].mean()) if m.any() else 0.0
            if g >= 1:
                nome = NOMES_DAS_SECOES[g - 1]
                out[2 * g + 1] = len(vivos[nome]) / float(K_NOS) if nome in vivos else 0.0
        return out

    @property
    def unidades(self):
        if not hasattr(self, '_unidades'):
            self._unidades = [{'inicio': _POR_NOME[f'{nome}.n{n}.op']['inicio'], 'bits': BITS_NO, 'grupo': s} for s, nome in enumerate(NOMES_DAS_SECOES, start=1) for n in range(K_NOS)]
        return self._unidades
CODIFICACAO = CodificacaoDoSer()

class E:

    def __init__(self, op, *args, c=None):
        self.op, self.args, self.c = (op, args, c)

def compilar_secao(expr, tipo):
    nomes = ENTRADAS[tipo]
    n_in = len(nomes)
    lista = []
    memo = {}

    def emite(e):
        if isinstance(e, str):
            if e not in nomes:
                raise ValueError(f'a variável {e!r} não existe na seção do tipo {tipo}: {nomes}')
            return (nomes.index(e), False)
        chave = id(e)
        if chave in memo:
            return (memo[chave], True)
        op = OP_DE[e.op]
        ar = ARIDADE[op]
        if len(e.args) != ar:
            raise ValueError(f'a operação {e.op} leva {ar} argumento(s)')
        ra = emite(e.args[0])[0] if ar >= 1 else 0
        rb = emite(e.args[1])[0] if ar >= 2 else 0
        if USA_C[op] and e.c is None:
            raise ValueError(f'a operação {e.op} precisa de c')
        lista.append((op, ra, rb, nivel_da_constante(e.c) if USA_C[op] else 0))
        memo[chave] = ('no', len(lista) - 1)
        return (memo[chave], True)
    saida, _ = emite(expr) if not isinstance(expr, str) else (None, None)
    if isinstance(expr, str):
        lista.append((OP_DE['id'], nomes.index(expr), 0, 0))
    if len(lista) > K_NOS:
        raise ValueError(f'a expressão precisa de {len(lista)} nós e a seção tem {K_NOS}')
    deslocamento = K_NOS - len(lista)
    nos = [No(0, 0, 0, 0) for _ in range(deslocamento)]
    for op, ra, rb, c in lista:

        def reg(r):
            return n_in + deslocamento + r[1] if isinstance(r, tuple) else r
        nos.append(No(op, reg(ra), reg(rb), c))
    return nos

def programa(tecido=None, rotulos=None, **secoes):
    T = {'n_camadas': 1, 'larguras': [64, 8, 8], 'ativ': ['relu', 'relu', 'relu'], 'ativas0': 1.0, 'porta_entrada': 1.0, 'densidade': 1.0, 'escala_init': 1.0, 'lote': 1, 'cada': 1, 'semente': 0, 'pol_padrao': 0, 'init_S1': 'zeros', 'init_S2': 'zeros', 'init_S3': 'zeros', 'init_U1': 'zeros', 'init_U2': 'zeros', 'init_G1': 'zero', 'init_G2': 'zero'}
    if tecido:
        if 'camadas' in tecido:
            cam = list(tecido['camadas'])
            T['n_camadas'] = len(cam)
            T['larguras'] = (cam + [8, 8, 8])[:3]
        for k, v in tecido.items():
            if k != 'camadas':
                T[k] = v
        if 'ativ' in tecido and (not isinstance(tecido['ativ'], list)):
            T['ativ'] = [tecido['ativ']] * 3
    S = {n: None for n in NOMES_DAS_SECOES}
    for nome, expr in secoes.items():
        if nome not in S:
            raise ValueError(f'a seção {nome!r} não existe')
        S[nome] = compilar_secao(expr, TIPO_DA_SECAO[nome])
    return Programa(T, S, rotulos or {})
