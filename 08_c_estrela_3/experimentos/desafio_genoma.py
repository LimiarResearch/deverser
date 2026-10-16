# -*- coding: utf-8 -*-
import hashlib
import math
import os
import sys
import numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DES = os.path.join(RAIZ, 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
import nucleo_l2 as L2
VERSAO_DA_CODIFICACAO = 1
NIVEIS = 256
BITS_NUM = 8
BITS_LARGURA = 7
BITS_SEMENTE = 14
SEMENTE_MAX = int(L2.TECIDO['semente']['hi'])
NOMES_DOS_GRUPOS = ['tecido'] + list(L2.ORDEM)
N_GRUPOS = len(NOMES_DOS_GRUPOS)

def _nbits_categoria(spec):
    return max(1, int(math.ceil(math.log2(len(spec['op'])))))

def _montar():
    campos = []
    pos = [0]

    def add(nome, grupo, tipo, bits, spec=None, chave=None):
        campos.append({'nome': nome, 'grupo': grupo, 'tipo': tipo, 'bits': bits, 'spec': spec, 'inicio': pos[0], 'chave': chave})
        pos[0] += bits
    add('tecido.n_camadas', 0, 'ncam', 2)
    for i in range(3):
        add(f'tecido.largura_{i + 1}', 0, 'larg', BITS_LARGURA, chave=i)
    add('tecido.ativacao', 0, 'c', _nbits_categoria(L2.TECIDO['ativacao']), spec=L2.TECIDO['ativacao'], chave=('tecido', 'ativacao'))
    for k in ('ativas0', 'porta_entrada', 'densidade'):
        add(f'tecido.{k}', 0, 'f', BITS_NUM, spec=L2.TECIDO[k], chave=('tecido', k))
    add('tecido.semente', 0, 'semente', BITS_SEMENTE, spec=L2.TECIDO['semente'], chave=('tecido', 'semente'))
    for g, nome in enumerate(L2.ORDEM, start=1):
        if nome != 'sgd':
            add(f'{nome}.presente', g, 'presenca', 1, chave=nome)
        for k, spec in L2.OPS[nome].items():
            tipo = spec['t']
            add(f'{nome}.{k}', g, tipo, BITS_NUM if tipo in ('f', 'i') else _nbits_categoria(spec), spec=spec, chave=(nome, k))
    return (campos, pos[0])
CAMPOS, N_BITS = _montar()
N_CAMPOS = len(CAMPOS)
INICIO = np.array([c['inicio'] for c in CAMPOS], np.int64)
FIM = np.array([c['inicio'] + c['bits'] for c in CAMPOS], np.int64)
CAMPO_DE = np.zeros(N_BITS, np.int64)
for _i, _c in enumerate(CAMPOS):
    CAMPO_DE[_c['inicio']:_c['inicio'] + _c['bits']] = _i
GRUPO_DE_CAMPO = np.array([c['grupo'] for c in CAMPOS], np.int64)
GRUPO_DE = GRUPO_DE_CAMPO[CAMPO_DE]
POS_NO_CAMPO = np.arange(N_BITS) - INICIO[CAMPO_DE]
_PRESENCA = {c['chave']: i for i, c in enumerate(CAMPOS) if c['tipo'] == 'presenca'}
_LARG = {c['chave']: i for i, c in enumerate(CAMPOS) if c['tipo'] == 'larg'}
_POR_CHAVE = {c['chave']: i for i, c in enumerate(CAMPOS) if isinstance(c['chave'], tuple)}
_NCAM = 0

def descricao_da_codificacao():
    return {'versao': VERSAO_DA_CODIFICACAO, 'bits_da_foto': int(N_BITS), 'campos': int(N_CAMPOS), 'grupos': NOMES_DOS_GRUPOS, 'regra': 'tecido (n_camadas 2 bits, 3 larguras de 7 bits, ativação 1 bit, ativas0/porta_entrada/densidade de 8 bits, semente de 14 bits) e, para cada uma das 13 primitivas na ordem de execução, um bit de presença (o sgd não tem: está sempre presente) e os genes dela (numérico: 8 bits em código de Gray entre o mínimo e o máximo da faixa, escala linear ou logarítmica; categoria: ceil(log2 das opções) bits, índice módulo o número de opções); a forma canônica é codificar(decodificar(bits)): a primitiva ausente leva os genes no valor padrão', 'o_concorrente_que_V_mede': 'o programa decodificado da foto (quantizado); a foto e o programa são o mesmo objeto'}

def _gray(q):
    return q ^ q >> 1

def _gray_inv(g):
    q = g
    s = g >> 1
    while s:
        q ^= s
        s >>= 1
    return q

def _ler_int(b, campo):
    v = 0
    for x in b[campo['inicio']:campo['inicio'] + campo['bits']]:
        v = v << 1 | int(x)
    return v

def _escrever_int(b, campo, v):
    n = campo['bits']
    for t in range(n):
        b[campo['inicio'] + t] = v >> n - 1 - t & 1

def _nivel_de_valor(spec, v):
    lo, hi = (float(spec['lo']), float(spec['hi']))
    v = min(max(float(v), lo), hi)
    if spec.get('esc') == 'log':
        x = (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo))
    else:
        x = (v - lo) / (hi - lo)
    return int(min(max(round(x * (NIVEIS - 1)), 0), NIVEIS - 1))

def _valor_do_nivel(spec, q):
    lo, hi = (float(spec['lo']), float(spec['hi']))
    x = q / (NIVEIS - 1)
    v = math.exp(math.log(lo) + x * (math.log(hi) - math.log(lo))) if spec.get('esc') == 'log' else lo + x * (hi - lo)
    return L2._ajusta(spec, v)

def codificar(prog):
    p = L2.normalizar(prog)
    b = np.zeros(N_BITS, np.uint8)
    T = p['tecido']
    cam = list(T['camadas'])[:3]
    for i, c in enumerate(CAMPOS):
        t = c['tipo']
        if t == 'ncam':
            _escrever_int(b, c, len(cam) - 1)
        elif t == 'larg':
            if c['chave'] < len(cam):
                _escrever_int(b, c, _gray(int(min(max(cam[c['chave']], 8), 128)) - 8))
        elif c['grupo'] == 0:
            v = T[c['chave'][1]]
            if t == 'c':
                _escrever_int(b, c, c['spec']['op'].index(v))
            elif t == 'semente':
                _escrever_int(b, c, int(min(max(v, 0), SEMENTE_MAX)))
            else:
                _escrever_int(b, c, _gray(_nivel_de_valor(c['spec'], v)))
    ops = {o['op']: o for o in p['regra']}
    for i, c in enumerate(CAMPOS):
        if c['grupo'] == 0:
            continue
        nome = NOMES_DOS_GRUPOS[c['grupo']]
        t = c['tipo']
        if t == 'presenca':
            b[c['inicio']] = 1 if nome in ops else 0
            continue
        spec = c['spec']
        v = ops[nome][c['chave'][1]] if nome in ops else spec['pad']
        if t == 'c':
            _escrever_int(b, c, spec['op'].index(v) if v in spec['op'] else spec['op'].index(spec['pad']))
        else:
            _escrever_int(b, c, _gray(_nivel_de_valor(spec, v)))
    return b

def decodificar(bits):
    b = np.asarray(bits, np.uint8)
    if len(b) != N_BITS:
        raise ValueError(f'o genoma tem {N_BITS} bits, e vieram {len(b)}')
    ncam = min(_ler_int(b, CAMPOS[_NCAM]), 2) + 1
    camadas = [min(8 + _gray_inv(_ler_int(b, CAMPOS[_LARG[i]])), 128) for i in range(ncam)]
    tecido = {'camadas': camadas}
    regra = []
    for c in CAMPOS:
        if c['grupo'] != 0 or c['tipo'] in ('ncam', 'larg'):
            continue
        k = c['chave'][1]
        if c['tipo'] == 'c':
            tecido[k] = c['spec']['op'][_ler_int(b, c) % len(c['spec']['op'])]
        elif c['tipo'] == 'semente':
            tecido[k] = min(_ler_int(b, c), SEMENTE_MAX)
        else:
            tecido[k] = _valor_do_nivel(c['spec'], _gray_inv(_ler_int(b, c)))
    por_grupo = {}
    for c in CAMPOS:
        if c['grupo'] == 0:
            continue
        por_grupo.setdefault(c['grupo'], []).append(c)
    for g, cs in por_grupo.items():
        nome = NOMES_DOS_GRUPOS[g]
        if nome != 'sgd' and (not b[cs[0]['inicio']]):
            continue
        o = {'op': nome}
        for c in cs:
            if c['tipo'] == 'presenca':
                continue
            k = c['chave'][1]
            o[k] = c['spec']['op'][_ler_int(b, c) % len(c['spec']['op'])] if c['tipo'] == 'c' else _valor_do_nivel(c['spec'], _gray_inv(_ler_int(b, c)))
        regra.append(o)
    return L2.normalizar({'tecido': tecido, 'regra': regra})

def canonizar(bits):
    return codificar(decodificar(bits))

def chave_do_genoma(bits):
    return int.from_bytes(hashlib.blake2b(np.packbits(np.asarray(bits, np.uint8)).tobytes(), digest_size=8).digest(), 'little')

def empacotar(bits):
    return np.packbits(np.asarray(bits, np.uint8))

def desempacotar(pacote):
    return np.unpackbits(np.asarray(pacote, np.uint8))[:N_BITS].astype(np.uint8)

def descrever(bits):
    return L2.descrever(decodificar(bits))

def presencas(bits):
    b = np.asarray(bits, np.uint8)
    return np.array([1 if n == 'sgd' else int(b[CAMPOS[_PRESENCA[n]]['inicio']]) for n in L2.ORDEM], np.uint8)

def ativos(bits):
    b = np.asarray(bits, np.uint8)
    ncam = min(_ler_int(b, CAMPOS[_NCAM]), 2) + 1
    m = np.zeros(N_BITS, bool)
    pres = presencas(b)
    for i, c in enumerate(CAMPOS):
        if c['grupo'] == 0:
            m[c['inicio']:c['inicio'] + c['bits']] = not (c['tipo'] == 'larg' and c['chave'] >= ncam)
        elif c['tipo'] == 'presenca' or pres[c['grupo'] - 1]:
            m[c['inicio']:c['inicio'] + c['bits']] = True
    return m

def valor_do_campo(bits, i):
    b = np.asarray(bits, np.uint8)
    c = CAMPOS[i]
    t = c['tipo']
    if t == 'presenca':
        return float(b[c['inicio']])
    if t == 'ncam':
        return min(_ler_int(b, c), 2) / 2.0
    if t == 'larg':
        return min(_gray_inv(_ler_int(b, c)), 120) / 120.0
    if t == 'semente':
        return min(_ler_int(b, c), SEMENTE_MAX) / float(SEMENTE_MAX)
    if t == 'c':
        n = len(c['spec']['op'])
        return _ler_int(b, c) % n / max(n - 1, 1)
    return _gray_inv(_ler_int(b, c)) / (NIVEIS - 1.0)
CAMPOS_DO_VETOR = [i for i, c in enumerate(CAMPOS) if c['tipo'] not in ('presenca', 'semente')]
N_VETOR = len(CAMPOS_DO_VETOR)

def vetor_de_valores(bits):
    b = np.asarray(bits, np.uint8)
    ncam = min(_ler_int(b, CAMPOS[_NCAM]), 2) + 1
    pres = presencas(b)
    out = np.zeros(len(CAMPOS_DO_VETOR), np.float32)
    for j, i in enumerate(CAMPOS_DO_VETOR):
        c = CAMPOS[i]
        if c['grupo'] == 0:
            if c['tipo'] == 'larg' and c['chave'] >= ncam:
                continue
        elif not pres[c['grupo'] - 1]:
            continue
        out[j] = valor_do_campo(b, i)
    return out

def aplicar(bits, p, k, seq):
    b = np.array(bits, np.uint8, copy=True)
    b[p:p + k] = [seq >> k - 1 - t & 1 for t in range(k)]
    filho = canonizar(b)
    return None if np.array_equal(filho, bits) else filho

def sortear(rng):
    return codificar(L2.sortear(rng))

def mutar(bits, rng, forca=1.0):
    return codificar(L2.mutar(decodificar(bits), rng, forca))

def cruzar(a, b, rng):
    escolha = rng.random(N_GRUPOS) < 0.5
    filho = np.where(escolha[GRUPO_DE], np.asarray(a, np.uint8), np.asarray(b, np.uint8)).astype(np.uint8)
    return canonizar(filho)

def referencias_em_bits(largura=64):
    return {nome: codificar(p) for nome, p in L2.referencias(largura).items()}
