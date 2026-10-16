# -*- coding: utf-8 -*-
import ctypes
import hashlib
import os
import platform
import subprocess
import sys
import tempfile
import numpy as np
from experimentos import l_ser_interp as LI
from experimentos import l_ser_lang as L
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, 'l_ser_nucleo.cpp')
DES = os.path.join(os.path.dirname(AQUI), 'saida', 'calculadora', 'desafio')
if DES not in sys.path:
    sys.path.insert(0, DES)
from comum_vida import _desempacotar, _empacotar
FLAGS = ['-O3', '-march=native', '-std=c++17', '-shared', '-fPIC', '-fno-math-errno', '-fno-trapping-math']
_LIB = None
BUFFER_MAX = 8

def _chave_da_compilacao():
    h = hashlib.sha256()
    h.update(open(FONTE, 'rb').read())
    h.update(' '.join(FLAGS).encode())
    h.update(subprocess.run(['g++', '--version'], capture_output=True, text=True).stdout.encode())
    try:
        for ln in open('/proc/cpuinfo', encoding='utf-8'):
            if ln.startswith('model name') or ln.startswith('flags'):
                h.update(ln.encode())
                if ln.startswith('flags'):
                    break
    except OSError:
        h.update(platform.processor().encode())
    return h.hexdigest()[:20]

def caminho_da_biblioteca():
    pasta = os.environ.get('SER_CPP_CACHE') or os.path.join(tempfile.gettempdir(), 'l_ser_cpp_cache')
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, f'libser_{_chave_da_compilacao()}.so')

def compilar(forcar=False):
    alvo = caminho_da_biblioteca()
    if os.path.exists(alvo) and (not forcar):
        return alvo
    tmp = f'{alvo}.{os.getpid()}.tmp'
    r = subprocess.run(['g++', *FLAGS, '-o', tmp, FONTE], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('a compilação do núcleo C++ falhou:\n' + r.stderr[-3000:])
    os.replace(tmp, alvo)
    return alvo

def biblioteca():
    global _LIB
    if _LIB is None:
        lib = ctypes.CDLL(compilar())
        p = ctypes.c_void_p
        lib.ser_criar.restype = p
        lib.ser_criar.argtypes = [p, p, p, p]
        lib.ser_liberar.argtypes = [p]
        lib.ser_ligar.argtypes = [p, p, p, p, p, p, p, p, p, p, p, p, p, p, p]
        lib.ser_aprender.argtypes = [p, p, p, ctypes.c_int]
        lib.ser_prever.argtypes = [p, p, ctypes.c_int, p, p]
        lib.ser_episodio.argtypes = [p, ctypes.c_int, ctypes.c_int, p, ctypes.c_int, ctypes.c_int, ctypes.c_int, p, ctypes.c_int, p, p, p, ctypes.c_double, p, p, p]
        lib.ser_episodio.restype = ctypes.c_int
        lib.ser_secao_teste.argtypes = [p, p, ctypes.c_int, p, p, ctypes.c_int, ctypes.c_int, p]
        lib.ser_perturbar.argtypes = [p, ctypes.c_double, ctypes.c_uint64]
        _LIB = lib
    return _LIB

def _i(a):
    return a.ctypes.data

def _mascara_de_nomes(nomes_lidos, tipo):
    nomes = L.ENTRADAS[tipo]
    return int(sum((1 << nomes.index(n) for n in nomes_lidos)))

def descrever_programa(prog):
    ints, cs = ([], [])
    for nome in L.NOMES_DAS_SECOES:
        nos = prog.secoes[nome]
        if nos is None:
            ints += [0, 0, 0]
            continue
        tipo = L.TIPO_DA_SECAO[nome]
        vivos, lidas = L._nos_vivos(nos, tipo)
        ints += [1, len(vivos), _mascara_de_nomes(lidas, tipo)]
        for i in sorted(vivos):
            no = nos[i]
            ints += [i, no.op, no.a, no.b]
            cs.append(L.valor_da_constante(no.c))
    return (np.asarray(ints, np.int32), np.asarray(cs if cs else [0.0], np.float64))

class AprendizSerCpp(LI.AprendizSer):

    def __init__(self, d, c, r, prog, restaurando=False):
        super().__init__(d, c, r, prog, restaurando=restaurando)
        self._ctx = None
        if not restaurando:
            self._adotar(self.r)

    def _adotar(self, gerador=None, rng_estado=None, bx=None, by=None, t=None, diag=None):
        nm, nl, d, c = (self.nm, self.nl, self.d, self.c)
        g_inicial = dict(self.G)
        self.W = [np.ascontiguousarray(w, np.float32) for w in self.W]
        self.conn = [np.ascontiguousarray(x, bool) for x in self.conn]
        self._conn8 = [np.ascontiguousarray(x, np.uint8) for x in self.conn]
        self.mask = [np.ascontiguousarray(m, np.float32) for m in self.mask]
        self.age = [np.ascontiguousarray(a, np.float32) for a in self.age]
        self.S = {k: [np.ascontiguousarray(x, np.float32) for x in v] for k, v in self.S.items()}
        self.U = {k: [np.ascontiguousarray(x, np.float32) for x in v] for k, v in self.U.items()}
        self._G = np.zeros(2, np.float32)
        for k, v in g_inicial.items():
            self._G[k - 1] = float(v)
        self.mu = np.ascontiguousarray(self.mu, np.float32)
        self.var = np.ascontiguousarray(self.var, np.float32)
        self._bx = np.zeros((BUFFER_MAX, d), np.float32)
        self._by = np.zeros((BUFFER_MAX, c), np.float32)
        self._nbuf = np.zeros(1, np.int32)
        bx_ = self.bx if bx is None else bx
        by_ = self.by if by is None else by
        for i, (xx, yy) in enumerate(zip(bx_, by_)):
            self._bx[i], self._by[i] = (xx, self._alvo(yy))
        self._nbuf[0] = len(bx_)
        self.bx, self.by = ([], [])
        t_ = self.t if t is None else t
        dg = self.diag if diag is None else diag
        self._cnt = np.array([t_, dg['passos'], dg['renascidas'], dg['ativadas'], dg['liberadas'], dg['aprendizados']], np.int64)
        if rng_estado is None:
            g = gerador if gerador is not None else np.random.default_rng(0)
            semente = [int(g.integers(1, 2 ** 63 - 1)) for _ in range(4)]
            rng_estado = semente
        self._rng = np.array([int(x) % 2 ** 64 for x in rng_estado], np.uint64)
        if not self._rng.any():
            self._rng[0] = 1
        T = self.T
        act = [L.ATIVACOES.index(T['ativ'][i]) for i in range(3)]
        ih = [d, c, nl, self.B, self.cada, int(T['pol_padrao'])] + [self.rotulos[n] for n in ('POL1', 'POL2', 'POL3')] + act + [int(self.h[i]) if i < nl else 0 for i in range(3)]
        ih += [L.INIT_S.index(T[f'init_S{k}']) for k in (1, 2, 3)] + [L.INIT_U.index(T[f'init_U{k}']) for k in (1, 2)]
        ih += [int(k in self.S_vivas) for k in (1, 2, 3)] + [int(k in self.U_vivas) for k in (1, 2)] + [int(k in self.G_vivas) for k in (1, 2)]
        ih += [int(self.tem_guarda), int(self.usa_xi), _mascara_de_nomes(self.lidas_peso, 'peso')]
        ih = np.asarray(ih, np.int32)
        assert len(ih) == 30, len(ih)
        dh = np.asarray([float(T['escala_init'])], np.float64)
        prog_i, prog_c = descrever_programa(self.prog)
        lib = biblioteca()
        self._ctx = lib.ser_criar(_i(ih), _i(dh), _i(prog_i), _i(prog_c))
        ptr = lambda lst, n: np.array([_i(x) for x in lst] + [0] * (n - len(lst)), np.uint64)
        pW, pconn, page = (ptr(self.W, 4), ptr(self._conn8, 4), ptr(self.age, 4))
        pmask = ptr(self.mask, 3)
        pS = np.zeros(12, np.uint64)
        pU = np.zeros(8, np.uint64)
        for k, v in self.S.items():
            for m, x in enumerate(v):
                pS[(k - 1) * 4 + m] = _i(x)
        for k, v in self.U.items():
            for m, x in enumerate(v):
                pU[(k - 1) * 4 + m] = _i(x)
        lib.ser_ligar(self._ctx, _i(pW), _i(pconn), _i(pmask), _i(page), _i(pS), _i(pU), _i(self._G), _i(self.mu), _i(self.var), _i(self._bx), _i(self._by), _i(self._nbuf), _i(self._cnt), _i(self._rng))
        lib.ser_perturbar(self._ctx, float(LI.PERTURBACAO['eps']), int(LI.PERTURBACAO['semente']))
        self._classes = None

    def __del__(self):
        try:
            if getattr(self, '_ctx', None):
                biblioteca().ser_liberar(self._ctx)
                self._ctx = None
        except Exception:
            pass

    @property
    def t(self):
        return int(self._cnt[0]) if getattr(self, '_cnt', None) is not None else 0

    @t.setter
    def t(self, v):
        if getattr(self, '_cnt', None) is not None:
            self._cnt[0] = v

    @property
    def diag(self):
        c = getattr(self, '_cnt', None)
        if c is None:
            return self.__dict__.get('_diag_inicial', {'passos': 0, 'renascidas': 0, 'ativadas': 0, 'liberadas': 0, 'aprendizados': 0})
        return {'passos': int(c[1]), 'renascidas': int(c[2]), 'ativadas': int(c[3]), 'liberadas': int(c[4]), 'aprendizados': int(c[5])}

    @diag.setter
    def diag(self, v):
        self.__dict__['_diag_inicial'] = dict(v)

    @property
    def G(self):
        g = getattr(self, '_G', None)
        if g is None:
            return self.__dict__.get('_G_inicial', {})
        return {k: np.float32(g[k - 1]) for k in self.G_vivas}

    @G.setter
    def G(self, v):
        self.__dict__['_G_inicial'] = dict(v)

    def aprender(self, x, y):
        x = np.ascontiguousarray(x, np.float32)
        t = np.ascontiguousarray(self._alvo(y)[None, :], np.float32)
        biblioteca().ser_aprender(self._ctx, _i(x), _i(t), 1)

    def aprender_varios(self, X, Y):
        X = np.ascontiguousarray(X, np.float32)
        Y = np.asarray(Y)
        if Y.ndim == 1:
            T = np.zeros((len(Y), self.c), np.float32)
            T[np.arange(len(Y)), Y.astype(np.int64)] = 1.0
        else:
            T = np.ascontiguousarray(Y, np.float32)
        biblioteca().ser_aprender(self._ctx, _i(X), _i(np.ascontiguousarray(T)), len(T))

    def prever(self, X):
        X = np.ascontiguousarray(X, np.float32)
        n = X.shape[0]
        classes = np.zeros(n, np.int64)
        etiquetas = np.zeros(n, np.int8)
        biblioteca().ser_prever(self._ctx, _i(X), n, _i(classes), _i(etiquetas))
        return (classes, etiquetas)

    def episodio(self, lado, inicio, alvos, rot, tmax, ctxv, ruido, explora, sorteio, eps):
        d = lado * lado + 1 + len(ctxv)
        X = np.zeros((tmax, d), np.float32)
        acoes = np.zeros(tmax, np.int32)
        suc = np.zeros(1, np.int32)
        alv = np.ascontiguousarray(alvos, np.int32)
        cv = np.ascontiguousarray(ctxv, np.float64)
        ru = np.ascontiguousarray(ruido, np.float64)
        ex = np.ascontiguousarray(explora, np.float64)
        so = np.ascontiguousarray(sorteio, np.int32)
        n = biblioteca().ser_episodio(self._ctx, int(lado), int(inicio), _i(alv), len(alv), int(rot), int(tmax), _i(cv), len(cv), _i(ru), _i(ex), _i(so), float(eps), _i(X), _i(acoes), _i(suc))
        return (X[:n], acoes[:n], bool(suc[0]))

    def diagnostico(self):
        d = dict(self.diag)
        d['unidades_ativas'] = [int(m.sum()) for m in self.mask]
        d['exemplos_guardados'] = int(self._nbuf[0])
        return d

    def estado(self):
        bits = L.codificar_programa(self.prog)
        n = int(self._nbuf[0])
        return _empacotar({'bits': np.packbits(bits), 'W': self.W, 'conn': [np.packbits(c.astype(np.uint8)) for c in self.conn], 'formas': [list(c.shape) for c in self.conn], 'mask': self.mask, 'age': self.age, 'S': {str(k): v for k, v in self.S.items()}, 'U': {str(k): v for k, v in self.U.items()}, 'G': {str(k): float(v) for k, v in self.G.items()}, 't': self.t, 'mu': self.mu, 'var': self.var, 'bx': self._bx[:n].copy() if n else np.zeros((0, self.d), np.float32), 'by': self._by[:n].copy(), 'diag': self.diag, 'rng': [int(x) for x in self._rng]})

    @staticmethod
    def restaurar(b, d, c):
        o = _desempacotar(b)
        prog = L.decodificar_bits(np.unpackbits(o['bits'])[:L.N_BITS])
        a = AprendizSerCpp(d, c, None, prog, restaurando=True)
        a.W = [np.asarray(w, np.float32) for w in o['W']]
        a.conn = [np.unpackbits(cn)[:int(np.prod(f))].reshape(f).astype(bool) for cn, f in zip(o['conn'], o['formas'])]
        a.mask = [np.asarray(m, np.float32) for m in o['mask']]
        a.age = [np.asarray(x, np.float32) for x in o['age']]
        a.S = {int(k): [np.asarray(x, np.float32) for x in v] for k, v in o['S'].items()}
        a.U = {int(k): [np.asarray(x, np.float32) for x in v] for k, v in o['U'].items()}
        a.G = {int(k): np.float32(v) for k, v in o['G'].items()}
        a.mu, a.var = (np.asarray(o['mu'], np.float32), np.asarray(o['var'], np.float32))
        a._adotar(rng_estado=o['rng'], bx=[x for x in np.asarray(o['bx'], np.float32)], by=[x for x in np.asarray(o['by'], np.float32).reshape(-1, c)], t=int(o['t']), diag=dict(o['diag']))
        return a

def fabricar(bits):
    prog = L.decodificar_bits(bits)
    return (lambda d, c, r: AprendizSerCpp(d, c, r, prog), lambda b, d, c: AprendizSerCpp.restaurar(b, d, c))
CLASSE_DE_FORMA = {'S': 0, 'ROW': 1, 'COL': 2, 'FULL': 4}

def avaliar_secao(prog_secao, tipo, valores, R, C):
    vivos, _ = L._nos_vivos(prog_secao, tipo)
    ints = [len(vivos)]
    cs = []
    for i in sorted(vivos):
        no = prog_secao[i]
        ints += [i, no.op, no.a, no.b]
        cs.append(L.valor_da_constante(no.c))
    ints = np.asarray(ints, np.int32)
    cs = np.asarray(cs if cs else [0.0], np.float64)
    tipo_i = {'retro': 0, 'peso': 1, 'unid': 6, 'glob': 11, 'pol': 13}[tipo]
    cls, arrs = ([], [])
    for v in valores:
        forma = np.shape(v)
        if len(forma) == 0:
            cls.append(0)
        elif forma == (R, C) and R > 1 and (C > 1):
            cls.append(4)
        elif forma == (1, C):
            cls.append(1)
        elif forma == (R, 1):
            cls.append(2)
        else:
            raise ValueError(f'forma {forma} não é escalar, (1, {C}), ({R}, 1) nem ({R}, {C})')
        arrs.append(np.ascontiguousarray(v, np.float32))
    ptrs = np.array([_i(a) for a in arrs], np.uint64)
    dst = np.zeros((R, C), np.float32)
    biblioteca().ser_secao_teste(_i(ints), _i(cs), tipo_i, _i(np.asarray(cls, np.int32)), _i(ptrs), R, C, _i(dst))
    return dst
