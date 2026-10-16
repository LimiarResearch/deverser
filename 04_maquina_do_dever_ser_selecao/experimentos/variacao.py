"""A variação da Máquina do Dever-Ser 4.3.1, sem o aprendiz: a escrita às cegas e o operador da codificação.

As funções e classes abaixo foram copiadas sem mudança de `experimentos/escritor_de_fotos.py` da versão 4.3.1 (tag `v4.3.1`, 01/10/2026). Lá elas
eram os CONTROLES da escrita aprendida (os braços "cega" e "operador", no mesmo orçamento de V); aqui são a única fonte de variação. Ficaram de
fora o modelo, a biblioteca, os motivos, as piscinas e tudo o que aprende. A única peça nova é `Molde`, que guarda do pai só o que a escrita
às cegas lê (a classe `Pai` original calculava também as leituras do modelo).

  a edição às cegas   reescrever um trecho de bits da foto por bits sorteados: um campo inteiro, de 1 a 3 bits dentro de um campo, o bit de
                      presença de um grupo, uma unidade inteira ou duas seguidas, ou uma janela solta de 4 a 16 bits (`MISTURA_CEGA`)
  o operador          `codificacao.mutar`: reescreve de 1 a 3 campos ativos com bits sorteados (a busca de antes)

Só numpy."""
import numpy as np

KMAX = 20                                  # bits do trecho que o registro de edições guarda, antes e depois (o valor da 4.3.1)
TAMANHOS_SOLTOS = (4, 8, 16)
MAX_BITS_DA_EDICAO = 63                    # o registro de edições guarda a sequência em int64
MISTURA_CEGA = {"gene": 0.35, "bits": 0.20, "presenca": 0.10, "unidade": 0.10, "unidades": 0.10, "janela": 0.15}


class Molde:
    """O pai, com o que a escrita às cegas lê dele: a foto, o veredito de V, os bits que fazem diferença, os campos e as unidades ativas e a
    chave. (Os mesmos cálculos de `Pai.__init__` da 4.3.1, sem as leituras do modelo.)"""

    def __init__(self, mapa, bits, ver):
        cod = mapa.cod
        self.bits = np.asarray(bits, np.uint8)
        self.ver = ver
        self.dist = int(ver["distancia"])
        self.nfal = int(ver["nfal"])
        self.ativos = np.asarray(cod.ativos(self.bits), bool)
        self.pos_ativas = np.flatnonzero(self.ativos)
        if len(self.pos_ativas) == 0:                                            # um concorrente sem bit ativo (degenerado): tudo é editável
            self.pos_ativas = np.arange(cod.n_bits)
        self.campos_ativos = np.unique(mapa.campo_de[self.pos_ativas])
        ju = mapa.unidade_de[self.pos_ativas]
        self.unidades_ativas = np.unique(ju[ju >= 0])
        self.chave = cod.chave(self.bits)


class Candidato:
    """Uma edição possível: o trecho reescrito, a foto que sai (canônica) e de onde veio (modelo, biblioteca, às cegas, operador)."""
    __slots__ = ("tipo", "p", "k", "seq", "bits", "origem", "x")

    def __init__(self, tipo, p, k, seq, bits, origem="cega"):
        self.tipo, self.p, self.k, self.seq, self.bits, self.origem, self.x = tipo, int(p), int(k), int(seq), bits, origem, None


def _janela(bits, p, k):
    v = 0
    for x in bits[p: p + k]:
        v = (v << 1) | int(x)
    return v


def _sorteio_de_bits(g, k):
    """Um inteiro de `k` bits sorteado (k pode passar de 62)."""
    v = 0
    while k > 0:
        n = min(k, 30)
        v = (v << n) | int(g.integers(0, 1 << n))
        k -= n
    return v


class Mapa:
    """Os mapas por bit e por campo que a escrita usa: o campo, o grupo e a posição de cada bit, o PAPEL de cada campo (o grupo e o nome dele sem o índice do nó, `RETRO.n3.op` -> `RETRO.op`), os campos
    de presença e a unidade de cada bit. Tudo sai da codificação."""

    def __init__(self, cod):
        self.cod = cod
        mp = cod.mapas()
        self.campo_de, self.grupo_de, self.pos_no_campo, self.inicio = mp["campo_de"], mp["grupo_de"], mp["pos_no_campo"], mp["inicio"]
        self.bits_do_campo = np.array([c["bits"] for c in cod.campos], np.int64)
        papeis, self.papel = {}, np.zeros(cod.n_campos, np.int64)
        for i, c in enumerate(cod.campos):
            sufixo = c["nome"].split(".")[-1]
            self.papel[i] = papeis.setdefault((int(c["grupo"]), sufixo), len(papeis))
        self.nomes_dos_papeis = [f"{cod.nomes_dos_grupos[g]}.{suf}" for (g, suf) in papeis]
        self.presenca = [i for i, c in enumerate(cod.campos) if c.get("tipo") == "presenca"]
        self.unidades = [dict(u) for u in cod.unidades]
        self.unidade_de = np.full(cod.n_bits, -1, np.int64)
        for j, u in enumerate(self.unidades):
            self.unidade_de[u["inicio"]: u["inicio"] + u["bits"]] = j
        cont, self.ordinal = {}, np.zeros(len(self.unidades), np.float32)
        por_grupo = {}
        for j, u in enumerate(self.unidades):
            por_grupo.setdefault(u["grupo"], []).append(j)
        for g, lista in por_grupo.items():
            for r, j in enumerate(lista):
                self.ordinal[j] = r / float(max(len(lista) - 1, 1))
        # unidades que podem ser reescritas em par (as duas seguidas e coladas, cabendo no registro de edições)
        self.pares = [j for j in range(len(self.unidades) - 1) if self.unidades[j]["inicio"] + self.unidades[j]["bits"] == self.unidades[j + 1]["inicio"]
                      and self.unidades[j]["bits"] + self.unidades[j + 1]["bits"] <= MAX_BITS_DA_EDICAO]

    def pos_na_unidade(self, p):
        """Onde o bit `p` cai dentro da unidade em que está (de 0 a 1, 0 se não está em unidade): diz ao modelo qual campo do nó a edição mexe."""
        j = int(self.unidade_de[p])
        if j < 0:
            return 0.0, 0.0
        u = self.unidades[j]
        return (p - u["inicio"] + 1) / float(u["bits"]), float(self.ordinal[j])


def _um_cego(pai, mapa, g, mistura):
    """Uma edição sorteada sem modelo nem biblioteca: (tipo, p, k, seq)."""
    cod = mapa.cod
    tipos = [t for t in mistura if mistura[t] > 0 and (t != "presenca" or mapa.presenca) and (t != "unidade" or len(pai.unidades_ativas)) and (t != "unidades" or (mapa.pares and len(pai.unidades_ativas)))]
    pesos = np.array([mistura[t] for t in tipos], np.float64)
    tipo = tipos[int(g.choice(len(tipos), p=pesos / pesos.sum()))]
    if tipo == "gene":                                                       # um campo inteiro reescrito por bits sorteados
        i = int(pai.campos_ativos[g.integers(len(pai.campos_ativos))])
        k = int(mapa.bits_do_campo[i])
        return "gene", int(mapa.inicio[i]), k, _sorteio_de_bits(g, k)
    if tipo == "bits":                                                       # de 1 a 3 bits dentro de um campo (com código de Gray, o vizinho difere em um bit)
        i = int(pai.campos_ativos[g.integers(len(pai.campos_ativos))])
        nb = int(mapa.bits_do_campo[i])
        k = min(int(g.integers(1, 4)), nb)
        p = int(mapa.inicio[i]) + int(g.integers(0, nb - k + 1))
        return "bits", p, k, _janela(pai.bits, p, k) ^ int(g.integers(1, 1 << k))
    if tipo == "presenca":                                                   # o bit de presença de um grupo: liga ou desliga (às vezes junto com o primeiro campo dele)
        i = int(mapa.presenca[g.integers(len(mapa.presenca))])
        p = int(mapa.inicio[i])
        atual = int(pai.bits[p])
        if g.random() < 0.5 or i + 1 >= cod.n_campos:
            return "presenca", p, 1, 1 - atual
        nb = int(mapa.bits_do_campo[i + 1])
        if 1 + nb > MAX_BITS_DA_EDICAO:
            return "presenca", p, 1, 1 - atual
        return "presenca", p, 1 + nb, ((1 - atual) << nb) | _sorteio_de_bits(g, nb)
    if tipo == "unidade":                                                    # uma unidade inteira (o nó, o comparador) reescrita por bits sorteados
        j = int(pai.unidades_ativas[g.integers(len(pai.unidades_ativas))])
        u = mapa.unidades[j]
        return "unidade", int(u["inicio"]), int(u["bits"]), _sorteio_de_bits(g, int(u["bits"]))
    if tipo == "unidades":                                                   # duas unidades coladas reescritas juntas (é como se constrói uma cadeia: o consumidor e o que ele consome)
        vivas = [j for j in mapa.pares if j in set(pai.unidades_ativas.tolist()) or j + 1 in set(pai.unidades_ativas.tolist())]
        if not vivas:
            return "janela", int(pai.pos_ativas[g.integers(len(pai.pos_ativas))]), 4, int(g.integers(0, 16))
        j = int(vivas[g.integers(len(vivas))])
        u0, u1 = mapa.unidades[j], mapa.unidades[j + 1]
        k = int(u0["bits"]) + int(u1["bits"])
        return "unidades", int(u0["inicio"]), k, _sorteio_de_bits(g, k)
    k = TAMANHOS_SOLTOS[int(g.integers(len(TAMANHOS_SOLTOS)))]               # uma janela solta
    p = min(int(pai.pos_ativas[g.integers(len(pai.pos_ativas))]), cod.n_bits - k)
    return "janela", p, k, int(g.integers(0, 1 << k))


def amostrar_cego(pai, mapa, M_, g, ja=None, mistura=None):
    """Sorteia até `M_` edições SEM modelo nem biblioteca, distintas entre si e do pai, que mudam o concorrente. É o controle sem viés da escrita aprendida."""
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
        out.append(Candidato(tipo, p, k, seq, filho, "cega"))
    return out


def amostrar_operador(pai, mapa, M_, g, forca=1.0):
    """`M_` filhos pelo operador de mutação da codificação (`codificacao.mutar`), o controle da busca de antes. O trecho editado é o menor que cobre os bits que mudaram (o modelo pode aprender dele
    quando cabe em 20 bits)."""
    cod = mapa.cod
    out, ja = [], {pai.chave}
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
        p, fim = int(dif.min()), int(dif.max()) + 1
        k = fim - p
        out.append(Candidato("operador", p, k if k <= KMAX else 0, _janela(filho, p, k) if k <= KMAX else 0, filho, "operador"))
    return out
