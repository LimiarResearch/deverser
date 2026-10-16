# -*- coding: utf-8 -*-
import math
import numpy as np
from experimentos import nivel3b_escritor as E
N_ENTRADA = E.N_ENTRADA
PROBES = E.PROBES
KMAX = E.KMAX
LIVRES = N_ENTRADA - PROBES
BRACOS = ('aprendida', 'cega', 'fria', 'operador', 'piscina', 'semente_aprendida', 'semente_sorteada', 'semente_a_mao', 'prova_atual', 'prova_candidata', 'evo')
CODIGO_DE_BRACO = {b: i for i, b in enumerate(BRACOS)}
TIPOS = ('gene', 'bits', 'presenca', 'janela', 'operador', 'biblioteca', 'unidade', 'unidades', 'motivo', 'doador')
ORIGENS_SEM_MODELO = ('cega', 'operador', 'semente_sorteada', 'semente_a_mao', 'evo')
TAMANHOS_SOLTOS = (4, 8, 16)
MAX_BITS_DA_EDICAO = 63
CLIP_DO_ALVO = 3.0
REL = 1000000
MISTURA_CEGA = {'gene': 0.35, 'bits': 0.2, 'presenca': 0.1, 'unidade': 0.1, 'unidades': 0.1, 'janela': 0.15}

def alvo(dist_pai, dist_filho):
    return float(min(max((dist_filho - dist_pai) / 1000.0, -CLIP_DO_ALVO), CLIP_DO_ALVO))

class Layout:
    N_GLOBAL, N_JANELA, N_CAMPO, N_CUSTO = (8, 7, 4, 2)

    def __init__(self, n_grupos, n_resumo):
        ng = int(n_grupos)
        self.n_grupos, self.n_pres, self.n_resumo = (ng, max(ng - 1, 0), int(n_resumo))
        fixas = self.N_GLOBAL + self.N_JANELA + ng + self.N_CAMPO + 2 * self.n_pres + 2 * KMAX + self.N_CUSTO
        self.n_resumo_max = LIVRES - fixas
        if self.n_resumo_max < self.n_resumo or self.n_resumo_max < 1:
            raise ValueError(f'a codificação não cabe no escritor: {ng} grupos deixam {self.n_resumo_max} lugares para o resumo do corpus e ela tem {n_resumo} números')
        partes = [('global', self.N_GLOBAL), ('janela', self.N_JANELA), ('grupo', ng), ('campo', self.N_CAMPO), ('presencas_antes', self.n_pres), ('presencas_depois', self.n_pres), ('bits_antigos', KMAX), ('bits_novos', KMAX), ('resumo_do_pai', self.n_resumo_max), ('custo_do_pai', self.N_CUSTO), ('comportamento_do_pai', PROBES)]
        self.grupos, a = ({}, 0)
        for nome, n in partes:
            self.grupos[nome] = (a, a + n)
            a += n
        assert a == N_ENTRADA, (a, N_ENTRADA)

class Mapa:

    def __init__(self, cod):
        self.cod = cod
        mp = cod.mapas()
        self.campo_de, self.grupo_de, self.pos_no_campo, self.inicio = (mp['campo_de'], mp['grupo_de'], mp['pos_no_campo'], mp['inicio'])
        self.bits_do_campo = np.array([c['bits'] for c in cod.campos], np.int64)
        papeis, self.papel = ({}, np.zeros(cod.n_campos, np.int64))
        for i, c in enumerate(cod.campos):
            sufixo = c['nome'].split('.')[-1]
            self.papel[i] = papeis.setdefault((int(c['grupo']), sufixo), len(papeis))
        self.nomes_dos_papeis = [f'{cod.nomes_dos_grupos[g]}.{suf}' for g, suf in papeis]
        self.presenca = [i for i, c in enumerate(cod.campos) if c.get('tipo') == 'presenca']
        self.unidades = [dict(u) for u in cod.unidades]
        self.unidade_de = np.full(cod.n_bits, -1, np.int64)
        for j, u in enumerate(self.unidades):
            self.unidade_de[u['inicio']:u['inicio'] + u['bits']] = j
        cont, self.ordinal = ({}, np.zeros(len(self.unidades), np.float32))
        por_grupo = {}
        for j, u in enumerate(self.unidades):
            por_grupo.setdefault(u['grupo'], []).append(j)
        for g, lista in por_grupo.items():
            for r, j in enumerate(lista):
                self.ordinal[j] = r / float(max(len(lista) - 1, 1))
        self.pares = [j for j in range(len(self.unidades) - 1) if self.unidades[j]['inicio'] + self.unidades[j]['bits'] == self.unidades[j + 1]['inicio'] and self.unidades[j]['bits'] + self.unidades[j + 1]['bits'] <= MAX_BITS_DA_EDICAO]

    def pos_na_unidade(self, p):
        j = int(self.unidade_de[p])
        if j < 0:
            return (0.0, 0.0)
        u = self.unidades[j]
        return ((p - u['inicio'] + 1) / float(u['bits']), float(self.ordinal[j]))

class Pai:

    def __init__(self, mapa, layout, n_clausulas, bits, ver, passo=0):
        cod = mapa.cod
        self.bits = np.asarray(bits, np.uint8)
        self.ver = ver
        self.comp = int(ver['comportamento'])
        self.dist = int(ver['distancia'])
        self.nfal = int(ver['nfal'])
        self.passo = int(passo)
        self.ativos = np.asarray(cod.ativos(self.bits), bool)
        self.pos_ativas = np.flatnonzero(self.ativos)
        if len(self.pos_ativas) == 0:
            self.pos_ativas = np.arange(cod.n_bits)
        self.campos_ativos = np.unique(mapa.campo_de[self.pos_ativas])
        ju = mapa.unidade_de[self.pos_ativas]
        self.unidades_ativas = np.unique(ju[ju >= 0])
        self.pres = np.asarray(cod.grupos_presentes(self.bits), np.float32)
        self.resumo = np.zeros(layout.n_resumo_max, np.float32)
        r = np.asarray(cod.resumo(self.bits), np.float32)
        self.resumo[:len(r)] = r
        self.phi = np.array([self.comp >> p & 1 for p in range(PROBES)], np.float32)
        self.g_glob = np.array([float(self.pres.mean()) if len(self.pres) else 0.0, float(cod.escalar_do_cabecalho(self.bits)), math.log1p(self.dist / 10.0) / 6.0, min(self.dist / (1000.0 * n_clausulas), 4.0), self.nfal / float(n_clausulas), self.passo / 4.0, 1.0 if self.nfal == 0 else 0.0, float(self.ativos.mean())], np.float32)
        self.custo = np.array([min(ver.get('cpu_s', 0.0) / 30.0, 1.0), min(ver.get('bytes', 0) / 65536.0, 2.0)], np.float32)
        self.chave = cod.chave(self.bits)

class Candidato:
    __slots__ = ('tipo', 'p', 'k', 'seq', 'bits', 'origem', 'x')

    def __init__(self, tipo, p, k, seq, bits, origem='cega'):
        self.tipo, self.p, self.k, self.seq, self.bits, self.origem, self.x = (tipo, int(p), int(k), int(seq), bits, origem, None)

def _janela(bits, p, k):
    v = 0
    for x in bits[p:p + k]:
        v = v << 1 | int(x)
    return v

def _sorteio_de_bits(g, k):
    v = 0
    while k > 0:
        n = min(k, 30)
        v = v << n | int(g.integers(0, 1 << n))
        k -= n
    return v

def _um_cego(pai, mapa, g, mistura):
    cod = mapa.cod
    tipos = [t for t in mistura if mistura[t] > 0 and (t != 'presenca' or mapa.presenca) and (t != 'unidade' or len(pai.unidades_ativas)) and (t != 'unidades' or (mapa.pares and len(pai.unidades_ativas)))]
    pesos = np.array([mistura[t] for t in tipos], np.float64)
    tipo = tipos[int(g.choice(len(tipos), p=pesos / pesos.sum()))]
    if tipo == 'gene':
        i = int(pai.campos_ativos[g.integers(len(pai.campos_ativos))])
        k = int(mapa.bits_do_campo[i])
        return ('gene', int(mapa.inicio[i]), k, _sorteio_de_bits(g, k))
    if tipo == 'bits':
        i = int(pai.campos_ativos[g.integers(len(pai.campos_ativos))])
        nb = int(mapa.bits_do_campo[i])
        k = min(int(g.integers(1, 4)), nb)
        p = int(mapa.inicio[i]) + int(g.integers(0, nb - k + 1))
        return ('bits', p, k, _janela(pai.bits, p, k) ^ int(g.integers(1, 1 << k)))
    if tipo == 'presenca':
        i = int(mapa.presenca[g.integers(len(mapa.presenca))])
        p = int(mapa.inicio[i])
        atual = int(pai.bits[p])
        if g.random() < 0.5 or i + 1 >= cod.n_campos:
            return ('presenca', p, 1, 1 - atual)
        nb = int(mapa.bits_do_campo[i + 1])
        if 1 + nb > MAX_BITS_DA_EDICAO:
            return ('presenca', p, 1, 1 - atual)
        return ('presenca', p, 1 + nb, 1 - atual << nb | _sorteio_de_bits(g, nb))
    if tipo == 'unidade':
        j = int(pai.unidades_ativas[g.integers(len(pai.unidades_ativas))])
        u = mapa.unidades[j]
        return ('unidade', int(u['inicio']), int(u['bits']), _sorteio_de_bits(g, int(u['bits'])))
    if tipo == 'unidades':
        vivas = [j for j in mapa.pares if j in set(pai.unidades_ativas.tolist()) or j + 1 in set(pai.unidades_ativas.tolist())]
        if not vivas:
            return ('janela', int(pai.pos_ativas[g.integers(len(pai.pos_ativas))]), 4, int(g.integers(0, 16)))
        j = int(vivas[g.integers(len(vivas))])
        u0, u1 = (mapa.unidades[j], mapa.unidades[j + 1])
        k = int(u0['bits']) + int(u1['bits'])
        return ('unidades', int(u0['inicio']), k, _sorteio_de_bits(g, k))
    k = TAMANHOS_SOLTOS[int(g.integers(len(TAMANHOS_SOLTOS)))]
    p = min(int(pai.pos_ativas[g.integers(len(pai.pos_ativas))]), cod.n_bits - k)
    return ('janela', p, k, int(g.integers(0, 1 << k)))

def amostrar_cego(pai, mapa, M_, g, ja=None, mistura=None):
    ja = set() if ja is None else ja
    mistura = mistura or MISTURA_CEGA
    cod = mapa.cod
    out = []
    for _ in range(6 * M_):
        if len(out) >= M_:
            break
        tipo, p, k, seq = _um_cego(pai, mapa, g, mistura)
        filho = cod.aplicar(pai.bits, p, k, seq)
        if filho is None:
            continue
        ch = cod.chave(filho)
        if ch == pai.chave or ch in ja:
            continue
        ja.add(ch)
        out.append(Candidato(tipo, p, k, seq, filho, 'cega'))
    return out

def amostrar_operador(pai, mapa, M_, g, forca=1.0):
    cod = mapa.cod
    out, ja = ([], {pai.chave})
    for _ in range(6 * M_):
        if len(out) >= M_:
            break
        filho = cod.mutar(pai.bits, g, forca)
        ch = cod.chave(filho)
        if ch in ja:
            continue
        ja.add(ch)
        dif = np.flatnonzero(filho != pai.bits)
        if len(dif) == 0:
            continue
        p, fim = (int(dif.min()), int(dif.max()) + 1)
        k = fim - p
        out.append(Candidato('operador', p, k if k <= KMAX else 0, _janela(filho, p, k) if k <= KMAX else 0, filho, 'operador'))
    return out

def caracteristicas(pai, cands, mapa, layout):
    cod = mapa.cod
    G = layout.grupos
    X = np.zeros((len(cands), N_ENTRADA), np.float32)
    for r, c in enumerate(cands):
        p, k = (c.p, c.k)
        row = X[r]
        row[G['global'][0]:G['global'][1]] = pai.g_glob
        pres_f = np.asarray(cod.grupos_presentes(c.bits), np.float32)
        if k > 0:
            i0 = int(mapa.campo_de[p])
            campos = np.unique(mapa.campo_de[p:p + k])
            pu, ordinal = mapa.pos_na_unidade(p)
            mexe_presenca = 1.0 if len(pres_f) and bool((pres_f != pai.pres).any()) else 0.0
            a = G['janela'][0]
            row[a:a + layout.N_JANELA] = (k / float(KMAX), mapa.pos_no_campo[p] / 8.0, 1.0 if p == mapa.inicio[i0] else 0.0, len(campos) / 4.0, mexe_presenca, pu, ordinal)
            row[G['grupo'][0] + int(mapa.grupo_de[p])] = 1.0
            antes, depois = (cod.valor_do_campo(pai.bits, i0), cod.valor_do_campo(c.bits, i0))
            a = G['campo'][0]
            row[a:a + layout.N_CAMPO] = (antes, depois, depois - antes, 1.0 if mapa.bits_do_campo[i0] > 1 else 0.0)
            kk = min(k, KMAX)
            a = G['bits_antigos'][0]
            row[a:a + kk] = pai.bits[p:p + kk]
            a = G['bits_novos'][0]
            row[a:a + kk] = [c.seq >> k - 1 - t & 1 for t in range(kk)]
        else:
            dif = np.flatnonzero(c.bits != pai.bits)
            a = G['janela'][0]
            row[a:a + layout.N_JANELA] = (min(len(dif), 40) / 40.0, 0.0, 0.0, len(np.unique(mapa.campo_de[dif])) / 4.0 if len(dif) else 0.0, 0.0, 0.0, 0.0)
        if layout.n_pres:
            row[G['presencas_antes'][0]:G['presencas_antes'][1]] = pai.pres
            row[G['presencas_depois'][0]:G['presencas_depois'][1]] = pres_f
        row[G['resumo_do_pai'][0]:G['resumo_do_pai'][1]] = pai.resumo
        row[G['custo_do_pai'][0]:G['custo_do_pai'][1]] = pai.custo
        row[G['comportamento_do_pai'][0]:G['comportamento_do_pai'][1]] = pai.phi
        c.x = row
    return X

class Motivos:

    def __init__(self, mapa, quantil=0.1, minimo_de_bons=20, max_bons=2000, max_todas=3000, apoio_minimo=0.3, enriquecimento_minimo=1.5, por_posicao=3, max_bits_do_campo=12, min_apoio_absoluto=5):
        self.mapa = mapa
        self.quantil, self.minimo_de_bons, self.max_bons, self.max_todas = (float(quantil), int(minimo_de_bons), int(max_bons), int(max_todas))
        self.apoio_minimo, self.enriquecimento_minimo, self.por_posicao = (float(apoio_minimo), float(enriquecimento_minimo), int(por_posicao))
        self.max_bits_do_campo, self.min_apoio_absoluto = (int(max_bits_do_campo), int(min_apoio_absoluto))
        nc, nu = (len(mapa.bits_do_campo), len(mapa.unidades))
        self.c_valor = np.full((nc, self.por_posicao), -1, np.int64)
        self.c_peso = np.zeros((nc, self.por_posicao))
        self.u_valor = np.full((nu, self.por_posicao), -1, np.int64)
        self.u_peso = np.zeros((nu, self.por_posicao))
        self.info = {}
        self.tem = False
        self.n_bons = 0
        self.corte = None
        self._cache = {}

    def _matriz(self, arquivo, ids):
        cod = self.mapa.cod
        B = np.stack([arquivo.foto(int(i)) for i in ids]) if len(ids) else np.zeros((0, cod.n_bits), np.uint8)
        A = np.zeros(B.shape, bool)
        for r, i in enumerate(ids):
            a = self._cache.get(int(i))
            if a is None:
                a = np.packbits(np.asarray(cod.ativos(B[r]), bool))
                self._cache[int(i)] = a
            A[r] = np.unpackbits(a)[:cod.n_bits].astype(bool)
        return (B, A)

    @staticmethod
    def _valores(M, A, inicio, nb):
        w = (1 << np.arange(nb - 1, -1, -1)).astype(np.int64)
        return (M[:, inicio:inicio + nb].astype(np.int64) @ w, A[:, inicio:inicio + nb].any(1))

    def _escolher(self, vb, ab, vt, at_, nbits):
        n_b, n_t = (int(ab.sum()), int(at_.sum()))
        if n_b < max(self.min_apoio_absoluto, self.minimo_de_bons // 4):
            return []
        vals_b, cont_b = np.unique(vb[ab], return_counts=True)
        if n_t:
            ordem = np.sort(vt[at_])
            cont_t = np.searchsorted(ordem, vals_b, side='right') - np.searchsorted(ordem, vals_b, side='left')
        else:
            cont_t = np.zeros(len(vals_b), np.int64)
        espaco = float(1 << min(nbits, 20))
        out = []
        for v, cb, ct in zip(vals_b, cont_b, cont_t):
            apoio_b = cb / float(n_b)
            apoio_t = (ct + 0.5) / (n_t + 0.5 * espaco)
            enr = apoio_b / apoio_t
            if cb >= self.min_apoio_absoluto and apoio_b >= self.apoio_minimo and (enr >= self.enriquecimento_minimo):
                out.append((int(v), float(apoio_b), float(ct) / max(n_t, 1), float(enr), int(cb), float(apoio_b * np.log(enr))))
        out.sort(key=lambda t: -t[5])
        return out[:self.por_posicao]

    def atualizar(self, arquivo, g=None, excluir=None):
        g = g if g is not None else np.random.default_rng(0)
        d = arquivo.distancias()
        ok = np.flatnonzero(d >= 0)
        if excluir is not None and len(excluir):
            fora = np.zeros(len(d), bool)
            fora[:min(len(excluir), len(d))] = np.asarray(excluir, bool)[:len(d)]
            ok = ok[~fora[ok]]
        self.tem = False
        if len(ok) < 2 * self.minimo_de_bons:
            return False
        self.corte = float(np.quantile(d[ok], self.quantil))
        bons = ok[d[ok] <= self.corte]
        if len(bons) < self.minimo_de_bons:
            bons = ok[np.argsort(d[ok], kind='stable')[:self.minimo_de_bons]]
        if len(bons) > self.max_bons:
            bons = bons[np.argsort(d[bons], kind='stable')[:self.max_bons]]
        outros = ok if len(ok) <= self.max_todas else np.sort(g.choice(ok, self.max_todas, replace=False))
        self.n_bons = len(bons)
        B, AB = self._matriz(arquivo, bons)
        T, AT = self._matriz(arquivo, outros)
        mapa = self.mapa
        self.c_valor[:], self.c_peso[:], self.u_valor[:], self.u_peso[:] = (-1, 0.0, -1, 0.0)
        self.info = {}
        for i in range(len(mapa.bits_do_campo)):
            nb = int(mapa.bits_do_campo[i])
            if nb > self.max_bits_do_campo:
                continue
            vb, ab = self._valores(B, AB, int(mapa.inicio[i]), nb)
            vt, at_ = self._valores(T, AT, int(mapa.inicio[i]), nb)
            for r, (v, apb, apt, enr, cb, peso) in enumerate(self._escolher(vb, ab, vt, at_, nb)):
                self.c_valor[i, r], self.c_peso[i, r] = (v, peso)
                self.info['campo', i, r] = (v, apb, apt, enr, cb)
        for j, u in enumerate(mapa.unidades):
            nb = int(u['bits'])
            vb, ab = self._valores(B, AB, int(u['inicio']), nb) if nb <= 62 else (None, None)
            if vb is None:
                continue
            vt, at_ = self._valores(T, AT, int(u['inicio']), nb)
            for r, (v, apb, apt, enr, cb, peso) in enumerate(self._escolher(vb, ab, vt, at_, nb)):
                self.u_valor[j, r], self.u_peso[j, r] = (v, peso)
                self.info['unidade', j, r] = (v, apb, apt, enr, cb)
        self.tem = bool(self.info)
        return self.tem

    def amostrar(self, pai, M_, g, ja=None):
        ja = set() if ja is None else ja
        out = []
        if not self.tem or M_ <= 0:
            return out
        mapa, cod = (self.mapa, self.mapa.cod)
        opcoes, pesos = ([], [])
        for i in pai.campos_ativos:
            i = int(i)
            nb = int(mapa.bits_do_campo[i])
            if nb > self.max_bits_do_campo or self.c_peso[i].max() <= 0:
                continue
            atual = _janela(pai.bits, int(mapa.inicio[i]), nb)
            for r in range(self.por_posicao):
                if self.c_valor[i, r] >= 0 and self.c_valor[i, r] != atual:
                    opcoes.append(('campo', int(mapa.inicio[i]), nb, int(self.c_valor[i, r])))
                    pesos.append(self.c_peso[i, r])
        for j in pai.unidades_ativas:
            j = int(j)
            u = mapa.unidades[j]
            if u['bits'] > 62 or self.u_peso[j].max() <= 0:
                continue
            atual = _janela(pai.bits, int(u['inicio']), int(u['bits']))
            for r in range(self.por_posicao):
                if self.u_valor[j, r] >= 0 and self.u_valor[j, r] != atual:
                    opcoes.append(('unidade', int(u['inicio']), int(u['bits']), int(self.u_valor[j, r])))
                    pesos.append(self.u_peso[j, r])
        if not opcoes:
            return out
        pesos = np.asarray(pesos, np.float64)
        pesos = pesos / pesos.sum()
        for t in g.choice(len(opcoes), size=min(4 * M_, 4 * len(opcoes)), p=pesos):
            if len(out) >= M_:
                break
            _, p, k, seq = opcoes[int(t)]
            filho = cod.aplicar(pai.bits, p, k, seq)
            if filho is None:
                continue
            ch = cod.chave(filho)
            if ch == pai.chave or ch in ja:
                continue
            ja.add(ch)
            out.append(Candidato('motivo', p, k, seq, filho, 'motivo'))
        return out

    def relatorio(self, biblioteca_d=None, quantos=20):
        mapa, cod = (self.mapa, self.mapa.cod)
        linhas = []
        for (tipo, pos, r), (v, apb, apt, enr, cb) in self.info.items():
            if tipo == 'campo':
                c = cod.campos[pos]
                nb, nome, papel = (int(c['bits']), c['nome'], int(mapa.papel[pos]))
            else:
                u = mapa.unidades[pos]
                nb, nome, papel = (int(u['bits']), f"unidade@{int(u['inicio'])} ({cod.nomes_dos_grupos[u['grupo']]})", None)
            coincide = None
            if tipo == 'campo' and biblioteca_d is not None:
                e = biblioteca_d.get((nb, 0, papel, v))
                coincide = bool(e is not None and e[1] > 0)
            linhas.append({'tipo': tipo, 'onde': nome, 'papel': mapa.nomes_dos_papeis[papel] if papel is not None else None, 'valor': format(v, f'0{nb}b'), 'apoio_nos_bons': round(apb, 3), 'apoio_em_todas': round(apt, 4), 'enriquecimento': round(enr, 2), 'fotos_boas_com_o_campo_ativo': cb, 'coincide_com_edicao_que_melhorou': coincide, '_p': apb * float(np.log(enr))})
        linhas.sort(key=lambda d_: -d_['_p'])
        for d_ in linhas:
            d_.pop('_p')
        return {'fotos_boas': int(self.n_bons), 'corte_de_distancia': self.corte, 'motivos': len(self.info), 'mais_fortes': linhas[:quantos], 'coincidem_com_edicoes_que_melhoraram': int(sum((1 for d_ in linhas if d_['coincide_com_edicao_que_melhorou'])))}

class EscritorDeFotos(E.Escritor):

    def __init__(self, problema, semente=0, pool=384, k_modelo=8, k_cega=2, min_memoria=800, teto_memoria=150000, piscina_m=16, peso_semantico=0.5, mistura=None):
        self.problema = problema
        self.cod = problema.codificacao
        self.mapa = Mapa(self.cod)
        self.layout = Layout(self.cod.n_grupos, self.cod.n_resumo())
        self.mistura = dict(mistura or MISTURA_CEGA)
        super().__init__(0, [], 1, problema.predicados, semente=semente, pool=pool, k_modelo=k_modelo, k_cega=k_cega, passos=1, min_memoria=min_memoria, teto_memoria=teto_memoria, piscina_m=piscina_m, peso_semantico=peso_semantico)
        self.vel = {b: [0, 0, 0] for b in BRACOS[:4]}
        self._vel_anterior = {b: [0, 0, 0] for b in BRACOS[:4]}
        self.contadores.update({'propostas_do_modelo': 0, 'propostas_da_biblioteca': 0, 'propostas_as_cegas': 0, 'propostas_do_operador': 0, 'melhoras_do_modelo': 0, 'melhoras_da_biblioteca': 0, 'melhoras_as_cegas': 0, 'melhoras_do_operador': 0, 'rodadas': 0})
        self._indice = {}
        self._indice_n = 0
        self.motivos = Motivos(self.mapa)
        self.contadores.update({'propostas_do_motivo': 0, 'melhoras_do_motivo': 0})

    def pai(self, bits, ver, passo=0):
        return Pai(self.mapa, self.layout, self.problema.n_clausulas, bits, ver, passo)

    def atualizar_motivos(self, arquivo, g=None):
        return self.motivos.atualizar(arquivo, g if g is not None else self.g)

    def _reindexar(self):
        self._indice = {}
        for k, o, banda, seq in self.biblioteca.d:
            self._indice.setdefault((k, o, banda), []).append(seq)
        self._indice_n = len(self.biblioteca.d)

    def _opcoes(self, k, o, banda, alvo_mask=0):
        if self._indice_n != len(self.biblioteca.d):
            self._reindexar()
        seqs = self._indice.get((k, o, banda))
        if not seqs:
            return (np.zeros(0, np.int64), np.zeros(0))
        P = self.biblioteca.P
        alvo_v = np.array([alvo_mask >> p & 1 for p in range(P)], np.float64) if alvo_mask else None
        pesos = []
        for seq in seqs:
            t, mel, soma, fix, qb = self.biblioteca.d[k, o, banda, seq]
            taxa = (mel + 0.5) / (t + 2.0)
            bonus = float((fix * alvo_v).sum() / (t + 2.0) / alvo_v.sum()) if alvo_v is not None and alvo_v.sum() > 0 else 0.0
            pesos.append(taxa * (1.0 + 4.0 * bonus))
        return (np.asarray(seqs, np.int64), np.asarray(pesos, np.float64))

    def amostrar_da_biblioteca(self, pai, M_, g, alvo_mask=0, ja=None):
        ja = set() if ja is None else ja
        out = []
        if self.biblioteca.tamanho() == 0 or M_ <= 0:
            return out
        mapa, cod = (self.mapa, self.cod)
        for _ in range(6 * M_):
            if len(out) >= M_:
                break
            i = int(pai.campos_ativos[g.integers(len(pai.campos_ativos))])
            papel, nb, p0 = (int(mapa.papel[i]), int(mapa.bits_do_campo[i]), int(mapa.inicio[i]))
            if g.random() < 0.7:
                k, p = (nb, p0)
                seqs, pesos = self._opcoes(k, 0, papel, alvo_mask)
                if len(seqs) == 0:
                    continue
                seq = int(seqs[g.choice(len(seqs), p=pesos / pesos.sum())])
            else:
                k = min(int(g.integers(1, 4)), nb)
                o = int(g.integers(0, nb - k + 1))
                seqs, pesos = self._opcoes(k, o + 1, REL + papel, alvo_mask)
                if len(seqs) == 0:
                    continue
                p = p0 + o
                seq = _janela(pai.bits, p, k) ^ int(seqs[g.choice(len(seqs), p=pesos / pesos.sum())])
            filho = cod.aplicar(pai.bits, p, k, seq)
            if filho is None:
                continue
            ch = cod.chave(filho)
            if ch == pai.chave or ch in ja:
                continue
            ja.add(ch)
            out.append(Candidato('biblioteca', p, k, seq, filho, 'biblioteca'))
        return out

    def propor(self, pai, braco, K, g=None):
        g = g or self.g
        if braco == 'operador':
            cs = amostrar_operador(pai, self.mapa, K, g)
            caracteristicas(pai, cs, self.mapa, self.layout)
            return ('operador', cs)
        if braco == 'aprendida' and self.pronto():
            ja = set()
            n_bib = self.pool // 3 if self.biblioteca.tamanho() >= 30 else 0
            n_mot = self.pool // 4 if self.motivos.tem else 0
            mask_d = self._mascara_das_duras()
            cs = amostrar_cego(pai, self.mapa, self.pool - n_bib - n_mot, g, ja, self.mistura) + self.amostrar_da_biblioteca(pai, n_bib, g, pai.comp & mask_d, ja) + self.motivos.amostrar(pai, n_mot, g, ja)
            if not cs:
                return ('aprendida', [])
            X = caracteristicas(pai, cs, self.mapa, self.layout)
            sc = E.notas(self.rede, X, self.n_duras, self.peso_semantico)
            k1 = min(self.k_modelo, len(cs))
            topo = np.argpartition(sc, k1 - 1)[:k1] if k1 < len(cs) else np.arange(len(cs))
            resto = np.setdiff1d(np.flatnonzero([c.origem == 'cega' for c in cs]), topo)
            k2 = min(self.k_cega, len(resto))
            cegas = g.choice(resto, k2, replace=False) if k2 else np.zeros(0, int)
            out = []
            for i in topo:
                cs[int(i)].origem = 'modelo' if cs[int(i)].origem == 'cega' else cs[int(i)].origem
                out.append(cs[int(i)])
            for i in cegas:
                out.append(cs[int(i)])
            return ('aprendida', out)
        cs = amostrar_cego(pai, self.mapa, K, g, mistura=self.mistura)
        caracteristicas(pai, cs, self.mapa, self.layout)
        return ('cega' if braco == 'cega' else 'fria', cs)

    def propor_piscina(self, pai, M_=None, g=None):
        g = g or self.g
        cs = amostrar_cego(pai, self.mapa, M_ or self.piscina_m, g, mistura=self.mistura)
        caracteristicas(pai, cs, self.mapa, self.layout)
        return cs

    def _registrar_padrao_g(self, pai, c, y, ver_filho):
        if c.tipo in ('operador', 'janela', 'unidade', 'unidades') or c.k == 0:
            return
        mapa = self.mapa
        i = int(mapa.campo_de[c.p])
        nb, p0 = (int(mapa.bits_do_campo[i]), int(mapa.inicio[i]))
        if c.p + c.k > p0 + nb:
            return
        papel = int(mapa.papel[i])
        if c.p == p0 and c.k == nb:
            chave = (c.k, 0, papel, c.seq)
        elif c.tipo == 'bits' or c.k <= 3:
            chave = (c.k, c.p - p0 + 1, REL + papel, _janela(pai.bits, c.p, c.k) ^ c.seq)
        else:
            return
        fix = pai.comp & ~int(ver_filho['comportamento']) & self._mascara_das_duras()
        quebra = ~pai.comp & int(ver_filho['comportamento']) & self._mascara_total()
        novo = chave not in self.biblioteca.d
        self.biblioteca.registrar(chave[0], chave[1], chave[2], chave[3], y, fix, quebra)
        if novo and self._indice_n == len(self.biblioteca.d) - 1:
            self._indice.setdefault(chave[:3], []).append(chave[3])
            self._indice_n += 1

    def registrar(self, pai, pai_foto, c, ver_filho, braco, gen=0, passo=0):
        y = alvo(pai.dist, ver_filho['distancia'])
        mudou = int(ver_filho['comportamento']) != pai.comp
        if c.x is not None:
            self.mem.adicionar(c.x, y, ver_filho['comportamento'], cego=int(c.origem in ('cega', 'operador', 'evo')), rodada=gen, foto=pai_foto, edicao=(TIPOS.index(c.tipo), c.p, c.k, c.seq, 0, passo), informativa=mudou)
        self._registrar_padrao_g(pai, c, y, ver_filho)
        self.contadores['edicoes_avaliadas'] += 1
        self.contadores['edicoes_que_mudaram_o_comportamento'] += int(mudou)
        return y

    def registrar_rodada(self, braco, propostas, ys):
        if braco not in self.vel:
            return
        melhorou = bool(len(ys) and min(ys) < 0)
        self.vel[braco][0] += 1
        self.vel[braco][1] += int(melhorou)
        self.vel[braco][2] += len(ys)
        self.contadores['rodadas'] += 1
        for c, y in zip(propostas, ys):
            nome = {'modelo': 'do_modelo', 'biblioteca': 'da_biblioteca', 'cega': 'as_cegas', 'operador': 'do_operador'}.get(c.origem, 'as_cegas')
            self.contadores['propostas_' + nome] = self.contadores.get('propostas_' + nome, 0) + 1
            if y < 0:
                self.contadores['melhoras_' + nome] = self.contadores.get('melhoras_' + nome, 0) + 1

    def registrar_piscina(self, pai, pai_foto, cands, vers, rodada=0, destino='piscina'):
        if len(cands) < 6:
            return
        X = np.stack([c.x for c in cands]).astype(np.float32)
        ys = np.array([alvo(pai.dist, v['distancia']) for v in vers], np.float32)
        comps = [int(v['comportamento']) for v in vers]
        los = np.zeros(len(cands), np.uint64)
        his = np.zeros(len(cands), np.uint64)
        for i, cc in enumerate(comps):
            los[i], his[i] = E.dividir(cc)
        for c, v, y in zip(cands, vers, ys):
            self._registrar_padrao_g(pai, c, float(y), v)
        self.seq += 1
        if destino == 'piscina':
            self.piscinas.adicionar(X, ys, los, his, 0, self.seq)
        else:
            for c, y, cc in zip(cands, ys, comps):
                self.mem.adicionar(c.x, float(y), cc, cego=1, rodada=rodada, foto=pai_foto, edicao=(TIPOS.index(c.tipo), c.p, c.k, c.seq, 0, 0), informativa=cc != pai.comp)
        self.contadores['piscinas_rotuladas'] += 1
        self.contadores['edicoes_avaliadas'] += len(cands)

    def carregar(self, pasta, semente=0):
        ok = super().carregar(pasta, semente)
        self._indice_n = -1
        return ok

    def _padrao_legivel(self, chave, entrada):
        k, o, banda, seq = chave
        t, mel, soma, fix, qb = entrada
        relativo = banda >= REL
        papel = banda - REL if relativo else banda
        nomes = self.problema.nomes_dos_predicados
        return {'papel': self.mapa.nomes_dos_papeis[papel] if 0 <= papel < len(self.mapa.nomes_dos_papeis) else str(papel), 'tipo': 'mascara_xor' if relativo else 'valor_do_campo', 'k': int(k), 'deslocamento_no_campo': int(o - 1) if relativo else 0, 'sequencia': format(int(seq), f'0{int(k)}b'), 'tentativas': int(t), 'melhoras': int(mel), 'taxa': round(mel / t, 4), 'delta_medio': round(soma / t, 4), 'sondas_que_mais_conserta': [nomes[int(p)] for p in np.argsort(-fix)[:3] if fix[p] > 0 and int(p) < len(nomes)]}

    def padroes(self, piscinas_max=120, quantos=20, minimo=8):
        y = self.mem.y
        linhas = [(k, e) for k, e in self.biblioteca.d.items() if e[0] >= minimo and e[1] > 0]
        linhas.sort(key=lambda ke: (-(ke[1][1] / ke[1][0]), -ke[1][0]))
        out = {'exemplos_proprios': int(len(y)), 'edicoes_que_melhoraram': int((y < 0).sum()), 'padroes_na_biblioteca': self.biblioteca.tamanho(), 'padroes_de_bits_que_mais_melhoraram': [self._padrao_legivel(k, e) for k, e in linhas[:quantos]], 'sondas': self.sondas.descricao()}
        if self.motivos.tem:
            out['motivos_nos_bons_corpus'] = self.motivos.relatorio(self.biblioteca.d, quantos)
        sig = self.significado_por_predicado()
        if sig:
            out['significado_que_o_modelo_sabe_prever'] = sig
        itens = self.piscinas.itens[-piscinas_max:]
        if len(itens) >= 10 and self.pronto():
            base_res, _ = E.ganho_no_top1(E.notas_das_piscinas(self.rede, itens, self.n_duras), itens)
            imp = {}
            g = np.random.default_rng(5)
            for nome, (a, b) in self.layout.grupos.items():
                if b <= a:
                    continue
                emb = []
                for it in itens:
                    Xp = np.asarray(it[0], np.float32).copy()
                    Xp[:, a:b] = Xp[g.permutation(len(Xp))][:, a:b]
                    emb.append(E.notas(self.rede, Xp, self.n_duras, self.peso_semantico))
                r, _ = E.ganho_no_top1(emb, itens)
                imp[nome] = round(r['media'] - base_res['media'], 5)
            out['importancia_dos_grupos'] = imp
            out['ganho_de_decisao_no_top1_contra_o_sorteio'] = {'media': round(base_res['media'], 5), 'erro_padrao': round(base_res['erro_padrao'], 5) if math.isfinite(base_res['erro_padrao']) else None, 'piscinas': base_res['K']}
        return out

    def significado_por_predicado(self, itens=None, max_piscinas=120):
        itens = itens if itens is not None else self.piscinas.itens[-max_piscinas:]
        if len(itens) < 5:
            return None
        P = self.problema.n_definidos
        probs, pais, filhos = ([], [], [])
        for it in itens:
            X = np.asarray(it[0], np.float32)
            probs.append(self.rede.prever_troca(X)[:, :P])
            pais.append(np.tile(X[0, N_ENTRADA - PROBES:N_ENTRADA - PROBES + P], (len(X), 1)))
            filhos.append(E.bits_dos_comportamentos(it[2], it[3], P))
        q, pai, filho = (np.concatenate(probs), np.concatenate(pais), np.concatenate(filhos))
        troca = filho != pai
        out = {}
        for j in range(P):
            t = troca[:, j]
            if 5 <= t.sum() < len(t) - 5:
                ordem = np.argsort(q[:, j], kind='mergesort')
                rk = np.empty(len(q))
                rk[ordem] = np.arange(1, len(q) + 1)
                n1 = int(t.sum())
                out[self.problema.nomes_dos_predicados[j]] = {'mudancas': n1, 'auc': round(float((rk[t].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(q) - n1))), 3)}
        return out
