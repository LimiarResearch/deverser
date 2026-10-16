# -*- coding: utf-8 -*-
import hashlib
import numpy as np

class CodificacaoBase:
    nome = '?'
    versao = 0
    n_bits = 0
    campos = []
    nomes_dos_grupos = []

    def decodificar(self, bits):
        raise NotImplementedError

    def codificar(self, corpus):
        raise NotImplementedError

    def canonizar(self, bits):
        raise NotImplementedError

    def ativos(self, bits):
        raise NotImplementedError

    def sortear(self, rng):
        raise NotImplementedError

    @property
    def n_campos(self):
        return len(self.campos)

    @property
    def n_grupos(self):
        return len(self.nomes_dos_grupos)

    def legal(self, bits):
        return self.decodificar(bits) is not None

    def mapas(self):
        if not hasattr(self, '_mapas'):
            campo_de = np.zeros(self.n_bits, np.int64)
            for i, c in enumerate(self.campos):
                campo_de[c['inicio']:c['inicio'] + c['bits']] = i
            grupo_de_campo = np.array([c['grupo'] for c in self.campos], np.int64)
            inicio = np.array([c['inicio'] for c in self.campos], np.int64)
            self._mapas = {'campo_de': campo_de, 'grupo_de': grupo_de_campo[campo_de], 'pos_no_campo': np.arange(self.n_bits) - inicio[campo_de], 'inicio': inicio}
        return self._mapas

    def chave(self, bits):
        return int.from_bytes(hashlib.blake2b(np.packbits(np.asarray(bits, np.uint8)).tobytes(), digest_size=8).digest(), 'little')

    def empacotar(self, bits):
        return np.packbits(np.asarray(bits, np.uint8))

    def desempacotar(self, pacote):
        return np.unpackbits(np.asarray(pacote, np.uint8))[:self.n_bits].astype(np.uint8)

    def aplicar(self, bits, p, k, seq):
        b = np.array(bits, np.uint8, copy=True)
        b[p:p + k] = [seq >> k - 1 - t & 1 for t in range(k)]
        filho = self.canonizar(b)
        if filho is None or np.array_equal(filho, bits):
            return None
        return filho
    unidades = ()

    def valor_do_campo(self, bits, i):
        c = self.campos[i]
        b = np.asarray(bits, np.uint8)[c['inicio']:c['inicio'] + c['bits']].astype(np.int64)
        return float(int(np.dot(b, 1 << np.arange(c['bits'] - 1, -1, -1))) / float((1 << c['bits']) - 1))

    def valores_dos_campos(self, bits):
        return np.array([self.valor_do_campo(bits, i) for i in range(self.n_campos)], np.float32)

    def grupos_presentes(self, bits):
        return np.ones(max(self.n_grupos - 1, 0), np.uint8)

    def escalar_do_cabecalho(self, bits):
        return 0.0

    def resumo(self, bits):
        mp = self.mapas()
        at = np.asarray(self.ativos(bits), bool)
        v = np.asarray(self.valores_dos_campos(bits), np.float32)
        out = np.zeros(2 * self.n_grupos, np.float32)
        grupo_de_campo = np.array([c['grupo'] for c in self.campos])
        ativo_do_campo = np.array([bool(at[c['inicio']:c['inicio'] + c['bits']].any()) for c in self.campos])
        for g in range(self.n_grupos):
            m = mp['grupo_de'] == g
            if m.any():
                out[2 * g] = float(at[m].mean())
            cm = (grupo_de_campo == g) & ativo_do_campo
            if cm.any():
                out[2 * g + 1] = float(v[cm].mean())
        return out

    def n_resumo(self):
        return 2 * self.n_grupos

    def mutar(self, bits, rng, forca=1.0):
        b0 = self.canonizar(bits)
        if b0 is None:
            return np.asarray(bits, np.uint8).copy()
        at = np.asarray(self.ativos(b0), bool)
        ativos_ = [i for i, c in enumerate(self.campos) if at[c['inicio']:c['inicio'] + c['bits']].any()]
        for _ in range(8):
            b = b0.copy()
            for i in rng.choice(ativos_, min(len(ativos_), 1 + int(2 * forca * rng.random())), replace=False) if ativos_ else []:
                c = self.campos[int(i)]
                b[c['inicio']:c['inicio'] + c['bits']] = rng.integers(0, 2, c['bits'])
            f = self.canonizar(b)
            if f is not None and (not np.array_equal(f, b0)):
                return f
        return b0

    def cruzar(self, a, b, rng):
        mp = self.mapas()
        escolha = rng.random(self.n_grupos) < 0.5
        filho = np.where(escolha[mp['grupo_de']], np.asarray(a, np.uint8), np.asarray(b, np.uint8)).astype(np.uint8)
        f = self.canonizar(filho)
        return np.asarray(a, np.uint8).copy() if f is None else f

    def descricao(self):
        return {'nome': self.nome, 'versao': int(self.versao), 'bits_da_foto': int(self.n_bits), 'campos': int(self.n_campos), 'grupos': list(self.nomes_dos_grupos)}

def _mesmo_corpus(cod, a, b):
    return np.array_equal(cod.canonizar(a), cod.canonizar(b))

def verificar_codificacao(cod, n_sorteios=60, semente=0, medida_do_corpus=None):
    g = np.random.default_rng(semente)
    falhas = []

    def exige(cond, msg):
        if not cond:
            falhas.append(msg)
    cobertura = np.zeros(cod.n_bits, int)
    for c in cod.campos:
        cobertura[c['inicio']:c['inicio'] + c['bits']] += 1
        exige(0 <= c['grupo'] < cod.n_grupos, f"P6 campo {c['nome']} com grupo fora da lista")
    exige(bool((cobertura == 1).all()), 'P6 os campos não cobrem cada bit exatamente uma vez')
    fotos = []
    ilegais = 0
    for _ in range(n_sorteios):
        b = cod.sortear(g)
        exige(isinstance(b, np.ndarray) and b.dtype == np.uint8 and (b.shape == (cod.n_bits,)) and (set(np.unique(b)) <= {0, 1}), 'P1 a foto sorteada não é um vetor de bits do tamanho n_bits')
        fotos.append(b)
    arbitrarias = [g.integers(0, 2, cod.n_bits).astype(np.uint8) for _ in range(n_sorteios)]
    for b in fotos:
        exige(cod.decodificar(b) is not None, 'P2 sortear devolveu uma foto ilegal')
    for b in fotos + arbitrarias:
        corpus = cod.decodificar(b)
        ilegais += corpus is None
        exige(cod.legal(b) == (corpus is not None), 'P2 legal() e decodificar() discordam')
        cn = cod.canonizar(b)
        exige((cn is None) == (corpus is None), 'P2/P3 canonizar devolve None exatamente quando a sequência é ilegal')
        if corpus is None:
            continue
        exige(np.array_equal(cod.canonizar(cn), cn), 'P3 a forma canônica não é idempotente')
        exige(cod.decodificar(cn) is not None, 'P3 a foto canônica não decodifica')
        volta = cod.codificar(corpus)
        exige(np.array_equal(cod.canonizar(volta), cn), 'P4 codificar(decodificar(b)) não dá a foto canônica de b')
        at = np.asarray(cod.ativos(cn), bool)
        exige(at.shape == (cod.n_bits,), 'P5 ativos tem o tamanho errado')
        inativos = np.flatnonzero(~at)
        if len(inativos):
            for pos in g.choice(inativos, min(8, len(inativos)), replace=False):
                b2 = cn.copy()
                b2[pos] ^= 1
                c2 = cod.canonizar(b2)
                exige(c2 is not None and np.array_equal(c2, cn), f'P5 virar o bit inativo {int(pos)} muda o corpus')
        exige(cod.chave(cn) == cod.chave(cn.copy()) and cod.chave(cn) == cod.chave(cod.canonizar(b)), 'P7 a chave da foto canônica não é estável')
        if medida_do_corpus is not None:
            exige(medida_do_corpus(cod.decodificar(b)) == medida_do_corpus(cod.decodificar(cn)), 'P3/P7 a foto e a canônica dão corpus que se medem diferente')
    edicoes_uteis = 0
    for b in fotos[:max(10, n_sorteios // 3)]:
        for _ in range(10):
            k = int(g.integers(1, min(16, cod.n_bits) + 1))
            p = int(g.integers(0, cod.n_bits - k + 1))
            seq = int(g.integers(0, 1 << k))
            filho = cod.aplicar(b, p, k, seq)
            if filho is None:
                continue
            edicoes_uteis += 1
            exige(filho.shape == (cod.n_bits,) and cod.legal(filho), 'P8 a edição devolveu uma foto ilegal')
            exige(np.array_equal(cod.canonizar(filho), filho), 'P8 a foto do filho não é canônica')
            exige(not np.array_equal(filho, cod.canonizar(b)), 'P8 a edição devolveu o mesmo corpus')
    try:
        cob_u = np.zeros(cod.n_bits, int)
        for u in cod.unidades:
            exige(u['bits'] > 0 and 0 <= u['inicio'] and (u['inicio'] + u['bits'] <= cod.n_bits) and (0 <= u['grupo'] < cod.n_grupos), 'P6 unidade fora da foto, vazia ou com grupo fora da lista')
            if u['bits'] > 0 and 0 <= u['inicio'] and (u['inicio'] + u['bits'] <= cod.n_bits):
                cob_u[u['inicio']:u['inicio'] + u['bits']] += 1
        exige(bool((cob_u <= 1).all()), 'P6 unidades se sobrepõem')
    except Exception as e:
        falhas.append(f'P6 unidades levantou {type(e).__name__}')
    legais = [b for b in fotos if cod.decodificar(b) is not None]
    try:
        v = np.asarray(cod.valores_dos_campos(legais[0] if legais else fotos[0]), np.float32)
        exige(v.shape[0] == cod.n_campos and np.isfinite(v).all() and (v >= -1e-06).all() and (v <= 1 + 1e-06).all(), 'P6 valores_dos_campos fora de 0 a 1 ou do tamanho de campos')
    except Exception as e:
        falhas.append(f'P6 valores_dos_campos levantou {type(e).__name__}')
    for b in legais[:max(3, n_sorteios // 10)]:
        try:
            r = np.asarray(cod.resumo(b), np.float32)
            exige(r.shape == (cod.n_resumo(),) and bool(np.isfinite(r).all()), 'P9 resumo com tamanho diferente de n_resumo() ou com valor não finito')
            gp = np.asarray(cod.grupos_presentes(b))
            exige(gp.shape == (max(cod.n_grupos - 1, 0),) and set(np.unique(gp).tolist()) <= {0, 1}, 'P9 grupos_presentes fora de n_grupos - 1 zeros e uns')
            e = float(cod.escalar_do_cabecalho(b))
            exige(0.0 <= e <= 1.0, 'P9 escalar_do_cabecalho fora de 0 a 1')
            v = np.asarray(cod.valores_dos_campos(b), np.float32)
            for i in g.choice(cod.n_campos, min(5, cod.n_campos), replace=False):
                x = float(cod.valor_do_campo(b, int(i)))
                exige(0.0 <= x <= 1.0 and abs(x - float(v[int(i)])) < 1e-05, 'P9 valor_do_campo discorda de valores_dos_campos ou sai de 0 a 1')
            for f in (cod.mutar(b, g), cod.cruzar(b, legais[0], g)):
                exige(f is not None and np.shape(f) == (cod.n_bits,) and cod.legal(f) and np.array_equal(cod.canonizar(f), f), 'P9 mutar ou cruzar devolveu foto ilegal ou não canônica')
        except Exception as e:
            falhas.append(f'P9 levantou {type(e).__name__}')
    return {'ok': not falhas, 'falhas': sorted(set(falhas)), 'resumo': {'nome': cod.nome, 'bits': int(cod.n_bits), 'campos': int(cod.n_campos), 'sequencias_arbitrarias_ilegais': f'{ilegais}/{len(arbitrarias)}', 'edicoes_que_mudam_o_corpus': edicoes_uteis, 'fracao_de_bits_ativos_nas_sorteadas': round(float(np.mean([np.asarray(cod.ativos(cod.canonizar(b))).mean() for b in legais])) if legais else 0.0, 3)}}
