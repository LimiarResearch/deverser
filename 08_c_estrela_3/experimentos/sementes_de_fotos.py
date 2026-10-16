# -*- coding: utf-8 -*-
import numpy as np
from experimentos import escritor_de_fotos as EF
FONTES = ('aprendida', 'a_mao', 'sorteada')
ORIGEM = {'aprendida': 'semente_aprendida', 'a_mao': 'semente_a_mao', 'sorteada': 'semente_sorteada'}
FRACAO_MAXIMA_DA_APRENDIDA = 0.5
Q_MAX = 48
MAX_PREFIXOS = 8

class Semente(EF.Candidato):
    __slots__ = ('fonte', 'passos', 'q')

    def __init__(self, fonte, bits, passos, q, p=0, k=0, seq=0):
        super().__init__('doador', p, k, seq, bits, ORIGEM[fonte])
        self.fonte, self.passos, self.q = (fonte, list(passos), int(q))

class Plano:
    __slots__ = ('fonte', 'candidatas')

    def __init__(self, fonte, candidatas):
        self.fonte, self.candidatas = (fonte, list(candidatas))

def trechos_do_doador(pai_bits, doador_bits, mapa, max_bits=EF.MAX_BITS_DA_EDICAO):
    dif = np.flatnonzero(np.asarray(pai_bits) != np.asarray(doador_bits))
    if len(dif) == 0:
        return []
    campos = np.unique(mapa.campo_de[dif])
    out = {(int(mapa.inicio[i]), int(mapa.bits_do_campo[i])) for i in campos if int(mapa.bits_do_campo[i]) <= max_bits}
    if len(mapa.unidades):
        ju = mapa.unidade_de[dif]
        for j in np.unique(ju[ju >= 0]):
            u = mapa.unidades[int(j)]
            if int(u['bits']) <= max_bits and len({int(mapa.campo_de[p]) for p in dif[ju == j]}) >= 2:
                out.add((int(u['inicio']), int(u['bits'])))
    return [(p, k, EF._janela(doador_bits, p, k)) for p, k in sorted(out)]

class Material:

    def __init__(self, ap, pai, arquivo, doadores, g, max_por_doador=64, n_escritas=64, n_cegas=16):
        self.ap, self.pai = (ap, pai)
        self.ids = [int(i) for i in doadores]
        cod, mapa = (ap.cod, ap.mapa)
        self.partes = []
        for did in self.ids:
            tr = trechos_do_doador(pai.bits, arquivo.foto(did), mapa)
            if len(tr) > max_por_doador:
                tr = sorted([tr[int(i)] for i in g.choice(len(tr), max_por_doador, replace=False)])
            for p, k, seq in tr:
                filho = cod.aplicar(pai.bits, p, k, seq)
                if filho is not None and cod.chave(filho) != pai.chave:
                    self.partes.append((did, p, k, seq))
        novas = ap.escrever(pai, n_escritas, g) if ap.pronto() else []
        novas += EF.amostrar_cego(pai, mapa, n_cegas, g, {pai.chave} | {cod.chave(c.bits) for c in novas}, ap.mistura)
        for c in novas:
            if c.k > 0:
                self.partes.append((-1, c.p, c.k, c.seq))
        self.doador = np.array([p_[0] for p_ in self.partes], np.int64)

    def __len__(self):
        return len(self.partes)

def _aplicar_em_ordem(cod, bits, passos):
    cur, feitos = (np.asarray(bits, np.uint8), [])
    for did, p, k, seq in passos:
        filho = cod.aplicar(cur, p, k, seq)
        if filho is not None:
            cur = filho
            feitos.append((did, p, k, seq))
    return (cur, feitos) if feitos else (None, [])

def _livre(ocupado, p, k):
    return not ocupado[p:p + k].any()

def imaginar(ap, pai, material, g, q_max=Q_MAX, por_passo=128, membros=2, permitidas=None):
    cod = ap.cod
    conj = ap.rede.__class__(ap.rede.membros[:max(1, int(membros))])
    cur = pai.bits.copy()
    nota_cur = np.inf
    ocupado = np.zeros(cod.n_bits, bool)
    livres = list(range(len(material))) if permitidas is None else [int(i) for i in permitidas]
    caminho, notas = ([], [])
    for _ in range(q_max):
        cand = [j for j in livres if _livre(ocupado, material.partes[j][1], material.partes[j][2])]
        if not cand:
            break
        if len(cand) > por_passo:
            cand = [int(j) for j in g.choice(cand, por_passo, replace=False)]
        filhos, validos = ([], [])
        for j in cand:
            _, p, k, seq = material.partes[j]
            f = cod.aplicar(cur, p, k, seq)
            if f is not None:
                filhos.append(f)
                validos.append(j)
        if not filhos:
            break
        nota, _, _ = ap.notas_dos_filhos(pai, np.stack(filhos).astype(np.float32), conjunto=conj)
        i = int(np.argmin(nota))
        if nota[i] >= nota_cur:
            break
        j = validos[i]
        cur, nota_cur = (filhos[i], float(nota[i]))
        _, p, k, _s = material.partes[j]
        ocupado[p:p + k] = True
        livres.remove(j)
        caminho.append(material.partes[j])
        notas.append(nota_cur)
    return (caminho, notas)

def ordem_ao_acaso(material, n_bits, g, permitidas=None, q_max=Q_MAX):
    ocupado = np.zeros(n_bits, bool)
    caminho = []
    idx = list(range(len(material))) if permitidas is None else [int(i) for i in permitidas]
    for j in g.permutation(idx):
        _, p, k, _s = material.partes[int(j)]
        if _livre(ocupado, p, k):
            caminho.append(material.partes[int(j)])
            ocupado[p:p + k] = True
            if len(caminho) >= q_max:
                break
    return caminho

def tamanhos_de_prefixo(n, maximo=MAX_PREFIXOS):
    t, k = ([], 1)
    while k <= n and len(t) < maximo:
        t.append(k)
        k *= 2
    if n > 0 and n not in t and (len(t) < maximo):
        t.append(n)
    return t

def _semente(fonte, bits, feitos, q):
    p, k, seq = (feitos[0][1], feitos[0][2], feitos[0][3]) if len(feitos) == 1 else (feitos[0][1], 0, 0)
    return Semente(fonte, bits, feitos, q, p, k, seq)

def _prefixos(ap, pai, caminho, tamanhos, fonte, ja):
    cod = ap.cod
    out = []
    for t in tamanhos:
        bits, feitos = _aplicar_em_ordem(cod, pai.bits, caminho[:t])
        if bits is None:
            continue
        ch = cod.chave(bits)
        if ch == pai.chave or ch in ja:
            continue
        ja.add(ch)
        out.append(_semente(fonte, bits, feitos, t))
    return out

def plano_aprendido(ap, material, g, ja, q_max=Q_MAX, fracao_de_doadores=0.6):
    if len(material) == 0:
        return (None, [], None)
    ids = np.array(material.ids, np.int64)
    usados = g.choice(ids, max(1, int(round(fracao_de_doadores * len(ids)))), replace=False) if len(ids) > 1 else ids
    permitidas = np.flatnonzero(np.isin(material.doador, np.append(usados, -1)))
    caminho, notas = imaginar(ap, material.pai, material, g, q_max, permitidas=permitidas)
    if not caminho:
        return (None, [], None)
    tam = tamanhos_de_prefixo(len(caminho))
    cs = _prefixos(ap, material.pai, caminho, tam, 'aprendida', ja)
    return (Plano('aprendida', cs), tam, (caminho, notas)) if cs else (None, [], None)

def plano_sorteado(ap, material, tamanhos, g, ja, n=None):
    if len(material) == 0:
        return None
    n = len(tamanhos) if n is None else int(n)
    cs = []
    for _ in range(4):
        caminho = ordem_ao_acaso(material, ap.cod.n_bits, g)
        tam = [t for t in tamanhos if t <= len(caminho)] or tamanhos_de_prefixo(len(caminho))
        cs += _prefixos(ap, material.pai, caminho, tam, 'sorteada', ja)[:max(n - len(cs), 0)]
        if len(cs) >= n:
            break
    return Plano('sorteada', cs) if cs else None

def plano_a_mao(ap, material, arquivo, n, g, ja):
    pai, cod = (material.pai, ap.cod)
    cruzar = getattr(cod, 'semente_a_mao', cod.cruzar)
    cs = []
    if not material.ids:
        return None
    for _ in range(6 * max(n, 1)):
        if len(cs) >= n:
            break
        did = int(material.ids[int(g.integers(len(material.ids)))])
        bits = cruzar(pai.bits, arquivo.foto(did), g)
        ch = cod.chave(bits)
        if ch == pai.chave or ch in ja:
            continue
        dif = np.flatnonzero(np.asarray(bits) != pai.bits)
        if len(dif) == 0:
            continue
        ja.add(ch)
        cs.append(Semente('a_mao', bits, [(did, int(dif.min()), 0, 0)], 1, int(dif.min()), 0, 0))
    return Plano('a_mao', cs) if cs else None

def escrever_planos(ap, pai, arquivo, doadores, n, g, fracao_maxima=FRACAO_MAXIMA_DA_APRENDIDA, q_max=Q_MAX):
    material = Material(ap, pai, arquivo, doadores, g)
    ja = set()
    ap_, so, mao, caminhos = ([], [], [], [])
    for _ in range(3 * n):
        if len(ap_) >= n:
            break
        pl, tam, cam = plano_aprendido(ap, material, g, ja, q_max)
        if pl is None:
            continue
        ap_.append(pl)
        caminhos.append(cam)
        ps = plano_sorteado(ap, material, tam, g, ja, n=len(pl.candidatas))
        if ps is not None:
            so.append(ps)
        pm = plano_a_mao(ap, material, arquivo, len(pl.candidatas), g, ja)
        if pm is not None:
            mao.append(pm)
    limite = int(fracao_maxima / (1.0 - fracao_maxima) * (len(so) + len(mao)) + 1e-09)
    ap_, caminhos = (ap_[:limite], caminhos[:limite])
    return ({'aprendida': ap_, 'sorteada': so, 'a_mao': mao}, caminhos)

class EstadoDaSemente:
    __slots__ = ('fonte', 'bits', 'ver', 'id', 'y_compor', 'y_final', 'pedidas', 'composicoes', 'tamanho_escolhido', 'remendos_aceitos', 'remendos_pedidos', 'doadores')

    def __init__(self, fonte, bits, ver, ident, y_compor, pedidas, composicoes, tamanho, doadores=()):
        self.fonte, self.bits, self.ver, self.id = (fonte, bits, ver, ident)
        self.y_compor, self.y_final = (y_compor, y_compor)
        self.pedidas, self.composicoes, self.tamanho_escolhido = (pedidas, composicoes, tamanho)
        self.remendos_aceitos = self.remendos_pedidos = 0
        self.doadores = tuple(doadores)

def _dist(v):
    return int(v['distancia']) if v['estado'] == 'ok' else 10 ** 12

def conduzir(ap, pai, id_do_pai, planos, medir, guardar, registrar, g, passos=3, edicoes_por_passo=6):
    lista = [(fonte, pl) for fonte, pls in planos.items() for pl in pls]
    flat, donos = ([], [])
    for ip, (fonte, pl) in enumerate(lista):
        for c in pl.candidatas:
            flat.append(c)
            donos.append(ip)
    vers = medir([c.bits for c in flat]) if flat else []
    melhor = {}
    for c, v, ip in zip(flat, vers, donos):
        fonte = lista[ip][0]
        k_id, _ = guardar(c.bits, v, ORIGEM[fonte], id_do_pai)
        registrar(pai, id_do_pai, c, v, ORIGEM[fonte], k_id)
        chave = (_dist(v), c.q)
        if ip not in melhor or chave < melhor[ip][0]:
            melhor[ip] = (chave, c, v, k_id)
    estados = []
    for ip in sorted(melhor):
        _, c, v, k_id = melhor[ip]
        fonte, pl = lista[ip]
        doadores = sorted({int(x[0]) for x in getattr(c, 'passos', None) or [] if int(x[0]) >= 0})
        estados.append(EstadoDaSemente(fonte, c.bits, v, k_id, EF.alvo(pai.dist, v['distancia']) if v['estado'] == 'ok' else EF.CLIP_DO_ALVO, len(pl.candidatas), len(pl.candidatas), c.q, doadores))
    for _ in range(passos):
        props = []
        for est in estados:
            pa = ap.pai(est.bits, est.ver)
            br, cs = ap.propor(pa, 'aprendida' if est.fonte == 'aprendida' else 'cega', edicoes_por_passo, g, n=edicoes_por_passo)
            props.append((est, pa, cs))
        vers = medir([c.bits for _, _, cs in props for c in cs])
        i = 0
        for est, pa, cs in props:
            melhor_filho = None
            est.remendos_pedidos += len(cs)
            est.pedidas += len(cs)
            for c in cs:
                v = vers[i]
                i += 1
                k_id, _ = guardar(c.bits, v, ORIGEM[est.fonte], est.id)
                registrar(pa, est.id, c, v, ORIGEM[est.fonte], k_id)
                if _dist(v) < _dist(est.ver) and (melhor_filho is None or _dist(v) < _dist(melhor_filho[1])):
                    melhor_filho = (c, v, k_id)
            if melhor_filho is not None:
                c, v, k_id = melhor_filho
                est.bits, est.ver, est.id = (c.bits, v, k_id)
                est.remendos_aceitos += 1
    for est in estados:
        est.y_final = EF.alvo(pai.dist, est.ver['distancia']) if est.ver['estado'] == 'ok' else EF.CLIP_DO_ALVO
    return estados
