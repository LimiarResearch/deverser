# -*- coding: utf-8 -*-
import glob
import os
import shutil
import zipfile
import numpy as np
from experimentos import nivel3b_fotos as F
ORIGENS = ('partida', 'referencia', 'sorteio', 'escrita_aprendida', 'escrita_cega', 'escrita_fria', 'operador', 'cruzada', 'piscina', 'edicao', 'semente_aprendida', 'semente_sorteada', 'semente_a_mao', 'prova_atual', 'prova_candidata', 'testemunha_doadora', 'corpo_do_eixo', 'doadora_da_celula', 'evo')
ESTADOS = ('ok', 'estouro', 'erro', 'oraculo')
MASCARA64 = (1 << 64) - 1
ESPACO_MINIMO = 300 * 1024 * 1024

def _crescer(a, cap, pad):
    b = np.full((cap,) + a.shape[1:], pad, a.dtype)
    b[:len(a)] = a
    return b

def _espaco_livre(pasta):
    try:
        return shutil.disk_usage(pasta).free
    except OSError:
        return ESPACO_MINIMO * 100

def _dividir(v):
    v = int(v)
    return (v & MASCARA64, v >> 64 & MASCARA64)

def _juntar(lo, hi):
    return int(lo) | int(hi) << 64

class ArquivoDeFotos:

    def __init__(self, problema, semente=0, capacidade=4096):
        self.problema = problema
        self.cod = problema.codificacao
        self.NB = (self.cod.n_bits + 7) // 8
        self.NC = problema.n_clausulas
        self.colunas = {'bits': ((self.NB,), np.uint8, 0), 'distancia': ((), np.int32, -1), 'nfal': ((), np.int16, -1), 'estado': ((), np.uint8, 0), 'classe': ((), np.uint8, 0), 'origem': ((), np.uint8, 0), 'pai': ((), np.int64, -1), 'gen': ((), np.int32, 0), 'comp_lo': ((), np.uint64, 0), 'comp_hi': ((), np.uint64, 0), 'valores': ((self.NC,), np.float32, np.nan), 'cpu_ms': ((), np.int32, 0), 'bytes': ((), np.int32, 0)}
        self.g = np.random.default_rng(semente + 919)
        self._cap = max(int(capacidade), 1)
        for nome, (forma, dt, pad) in self.colunas.items():
            setattr(self, nome, np.full((self._cap,) + forma, pad, dt))
        self.N = 0
        self.chaves = {}
        self.vistas = 0
        self.repetidas = 0
        self.recusadas = 0
        self.cheio = False
        self._salvas = 0
        self._pedacos = 0

    def __len__(self):
        return self.N

    def _abrir_linha(self):
        if self.N >= self._cap:
            cap = self._cap * 2
            for nome, (forma, dt, pad) in self.colunas.items():
                setattr(self, nome, _crescer(getattr(self, nome), cap, pad))
            self._cap = cap

    def buscar(self, bits):
        b = self.cod.canonizar(bits)
        return -1 if b is None else self.chaves.get(self.cod.chave(b), -1)

    def adicionar(self, bits, ver, origem='edicao', pai=-1, gen=0):
        if self.cheio:
            self.recusadas += 1
            return (-3, False)
        bits = self.cod.canonizar(bits)
        if bits is None:
            raise ValueError('uma sequência que não é corpus (ilegal) não entra no arquivo: quem chama a descarta antes de medir')
        ch = self.cod.chave(bits)
        self.vistas += 1
        if ch in self.chaves:
            self.repetidas += 1
            return (self.chaves[ch], False)
        self._abrir_linha()
        k = self.N
        self.bits[k] = self.cod.empacotar(bits)
        self.distancia[k], self.nfal[k], self.classe[k] = (int(ver['distancia']), int(ver['nfal']), int(ver['classe']))
        self.estado[k] = ESTADOS.index(ver['estado']) if ver['estado'] in ESTADOS else 2
        self.origem[k] = ORIGENS.index(origem) if isinstance(origem, str) else int(origem)
        self.pai[k], self.gen[k] = (int(pai), int(gen))
        self.comp_lo[k], self.comp_hi[k] = _dividir(ver['comportamento'])
        self.valores[k] = np.asarray(ver['valores'], np.float32)
        self.cpu_ms[k], self.bytes[k] = (int(round(1000 * ver.get('cpu_s', 0.0))), int(ver.get('bytes', 0)))
        self.chaves[ch] = k
        self.N += 1
        return (k, True)

    def reverificar(self, ident, ver):
        k = int(ident)
        self.distancia[k], self.nfal[k], self.classe[k] = (int(ver['distancia']), int(ver['nfal']), int(ver['classe']))
        self.estado[k] = ESTADOS.index(ver['estado']) if ver['estado'] in ESTADOS else 2
        self.comp_lo[k], self.comp_hi[k] = _dividir(ver['comportamento'])
        self.valores[k] = np.asarray(ver['valores'], np.float32)
        self.cpu_ms[k], self.bytes[k] = (int(round(1000 * ver.get('cpu_s', 0.0))), int(ver.get('bytes', 0)))
        if not hasattr(self, '_corrigidas'):
            self._corrigidas = []
        self._corrigidas.append(k)
    _COLUNAS_CORRIGIVEIS = ('distancia', 'nfal', 'classe', 'estado', 'comp_lo', 'comp_hi', 'valores', 'cpu_ms', 'bytes')

    def foto(self, ident):
        return self.cod.desempacotar(self.bits[int(ident)])

    def comportamento(self, ident):
        k = int(ident)
        return _juntar(self.comp_lo[k], self.comp_hi[k])

    def veredito(self, ident):
        k = int(ident)
        viol = self.problema.violacoes([float(x) for x in self.valores[k]]) if self.estado[k] == 0 else [1.0] * self.NC
        return {'estado': ESTADOS[int(self.estado[k])], 'valores': [float(x) for x in self.valores[k]], 'violacoes': viol, 'distancia': int(self.distancia[k]), 'nfal': int(self.nfal[k]), 'classe': int(self.classe[k]), 'comportamento': self.comportamento(k), 'cpu_s': float(self.cpu_ms[k]) / 1000.0, 'bytes': int(self.bytes[k])}

    def distancias(self):
        d = self.distancia[:self.N].astype(np.int64)
        d[self.estado[:self.N] != 0] = -1
        return d

    def melhores(self, k):
        d = self.distancias()
        ok = np.flatnonzero(d >= 0)
        if len(ok) == 0:
            return []
        return [int(i) for i in ok[np.lexsort((self.g.random(len(ok)), d[ok]))][:k]]

    def resumo(self):
        n = self.N
        cls, est, og = (self.classe[:n], self.estado[:n], self.origem[:n])
        ok = est == 0
        d = self.distancias()
        com = d[d >= 0]
        val = self.valores[:n][ok]
        classes = self.problema.classes
        por_clausula = {}
        for i, (cid, medida, op, lim, esc) in enumerate(self.problema.clausulas):
            v = val[:, i] if len(val) else np.zeros(0)
            viol = np.asarray(self.problema.violacoes_de_coluna(i, v)) if len(v) else np.zeros(0)
            por_clausula[cid] = {'cumprem': int((viol <= 1e-09).sum()), 'medidas': int(len(v)), 'melhor_valor': float(v.min() if op in ('<=', '==') else v.max()) if len(v) else None}
        return {'fotos': int(n), 'vistas': int(self.vistas), 'repetidas': int(self.repetidas), 'liberadas': 0, 'recusadas_por_falta_de_espaco': int(self.recusadas), 'cheio': bool(self.cheio), 'por_classe': {classes[k]: int((cls[ok] == k).sum()) for k in range(len(classes) - 1)} | {classes[-1]: int((~ok).sum())}, 'por_estado': {ESTADOS[k]: int((est == k).sum()) for k in range(len(ESTADOS)) if (est == k).any()}, 'por_origem': {ORIGENS[k]: int((og == k).sum()) for k in range(len(ORIGENS)) if (og == k).any()}, 'menor_distancia': int(com.min()) if len(com) else None, 'fotos_na_menor_distancia': int((com == com.min()).sum()) if len(com) else 0, 'por_clausula': por_clausula, 'bytes_de_bits': int(n * self.NB)}

    def salvar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        if _espaco_livre(pasta) < ESPACO_MINIMO:
            self.cheio = True
            return False
        corr = list(dict.fromkeys(getattr(self, '_corrigidas', [])))
        corr = [k for k in corr if k < self._salvas]
        if corr:
            ids = np.asarray(corr, np.int64)
            nc = getattr(self, '_pedacos_corr', 0)
            nome_c = os.path.join(pasta, f'correcoes_{nc:05d}.npz')
            np.savez_compressed(nome_c + '.tmp.npz', ids=ids, **{c: getattr(self, c)[ids] for c in self._COLUNAS_CORRIGIVEIS})
            os.replace(nome_c + '.tmp.npz', nome_c)
            self._pedacos_corr = nc + 1
        self._corrigidas = []
        a, b = (self._salvas, self.N)
        if b == a:
            return True
        nome = os.path.join(pasta, f'fotos_{self._pedacos:05d}.npz')
        tmp = nome + '.tmp.npz'
        np.savez_compressed(tmp, **{c: getattr(self, c)[a:b] for c in self.colunas}, primeira=np.asarray([a]), vistas=np.asarray([self.vistas]), repetidas=np.asarray([self.repetidas]))
        os.replace(tmp, nome)
        self._pedacos += 1
        self._salvas = b
        return True

    @classmethod
    def carregar(cls, pasta, problema, semente=0):
        f = cls(problema, semente=semente)
        if not pasta or not os.path.isdir(pasta):
            return f
        for nome in sorted((x for x in glob.glob(os.path.join(pasta, 'fotos_*.npz')) if not x.endswith('.tmp.npz'))):
            try:
                z = np.load(nome)
                a = int(z['primeira'][0])
                if a != f.N:
                    break
                nn = len(z['bits'])
                while f.N + nn > f._cap:
                    for c, (forma, dt, pad) in f.colunas.items():
                        setattr(f, c, _crescer(getattr(f, c), f._cap * 2, pad))
                    f._cap *= 2
                for c in f.colunas:
                    getattr(f, c)[f.N:f.N + nn] = z[c]
                f.N += nn
                f.vistas, f.repetidas = (int(z['vistas'][0]), int(z['repetidas'][0]))
                f._pedacos += 1
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                break
        for nome in sorted((x for x in glob.glob(os.path.join(pasta, 'correcoes_*.npz')) if not x.endswith('.tmp.npz'))):
            try:
                z = np.load(nome)
                ids = z['ids']
                ok = ids < f.N
                for c in f._COLUNAS_CORRIGIVEIS:
                    getattr(f, c)[ids[ok]] = z[c][ok]
                f._pedacos_corr = getattr(f, '_pedacos_corr', 0) + 1
            except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
                break
        for k in range(f.N):
            f.chaves[f.cod.chave(f.cod.desempacotar(f.bits[k]))] = k
        f._salvas = f.N
        return f
Edicoes = F.Edicoes
