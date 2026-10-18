"""codec.py: a linguagem L dos codecs sem perda para a tabela de métricas (itens.csv), e o medidor exato.

A tabela é lida como texto. Cada coluna vira inteiros numa escala fixa (1 ou 2 casas), e o texto de cada célula é refeito pela forma
canônica (a parte inteira, um ponto e as casas sem zeros à direita, ficando ao menos uma). Um dia (1.440 linhas) é um bloco que se lê
sozinho. O candidato escolhe, para cada classe de colunas, a cadeia de transformações; o medidor codifica, decodifica, refaz os bytes do
dia e compara com o original.
"""
import bz2
import lzma
import time
import zlib

import numpy as np

MIN_DIA = 1440

# ------------------------------------------------------------------ os dados

def ler_tabela(caminho):
    linhas = open(caminho, "rb").read().split(b"\n")
    assert linhas[-1] == b""
    cab, corpo = linhas[0], linhas[1:-1]
    cel = [l.split(b",") for l in corpo]
    nc = len(cab.split(b","))
    assert all(len(c) == nc for c in cel)
    escalas, colunas = [], []
    for j in range(nc):
        txt = [c[j] for c in cel]
        if j == 0:
            escalas.append(0)
            colunas.append(np.array([int(t) for t in txt], np.int64))
            continue
        D = max(len(t.split(b".")[1]) for t in txt)
        escalas.append(D)
        v = np.array([int(t.split(b".")[0]) * 10 ** D + int(t.split(b".")[1].ljust(D, b"0")) for t in txt], np.int64)
        colunas.append(v)
    return cab, escalas, np.stack(colunas, axis=1)


def _texto_coluna(v, D):
    if D == 0:
        return [str(int(x)).encode() for x in v]
    p = 10 ** D
    out = []
    for x in v.tolist():
        f = str(x % p).rjust(D, "0").rstrip("0") or "0"
        out.append(f"{x // p}.{f}".encode())
    return out


def texto_do_bloco(escalas, bloco):
    """Os bytes das linhas de um bloco (sem o cabeçalho), pela forma canônica."""
    cols = [_texto_coluna(bloco[:, j], escalas[j]) for j in range(bloco.shape[1])]
    return b"".join(b",".join(c[i] for c in cols) + b"\n" for i in range(bloco.shape[0]))


# ------------------------------------------------------------------ as peças de L

PREDICOES = ("nenhuma", "delta", "delta2", "irma", "irma_delta", "delta", "nenhuma", "delta")      # 3 bits; 5 a 7 repetem, declarado
MAPAS = ("zigue_zague", "deslocamento")
EMPACOTES = ("varint", "bits_fixos", "planos_de_bytes", "int32")
FUNDOS = ("nenhum", "zlib9", "lzma9e", "lzma6")       # L2 (18/10): o bz2 -9, que o seletor da L1 não escolheu em classe nenhuma, deu lugar ao lzma -9e
ARRANJOS = ("coluna_a_coluna", "linha_a_linha")


def _prever(x, modo, irma):
    if modo == "nenhuma":
        return x.copy()
    if modo == "delta":
        r = x.copy(); r[1:] = x[1:] - x[:-1]; return r
    if modo == "delta2":
        r = x.copy()
        if len(x) > 1: r[1] = x[1] - x[0]
        r[2:] = x[2:] - 2 * x[1:-1] + x[:-2]
        return r
    if modo == "irma":
        return x - irma
    if modo == "irma_delta":
        d = x - irma; r = d.copy(); r[1:] = d[1:] - d[:-1]; return r
    raise ValueError(modo)


def _desprever(r, modo, irma):
    if modo == "nenhuma":
        return r.copy()
    if modo == "delta":
        return np.cumsum(r)
    if modo == "delta2":
        x = np.empty_like(r)
        if len(r) == 0: return x
        x[0] = r[0]
        if len(r) > 1: x[1] = r[1] + x[0]
        # as primeiras diferenças são a soma acumulada de r[1:], e x é x[0] mais a soma acumulada delas
        if len(r) > 1:
            x[1:] = r[0] + np.cumsum(np.cumsum(r[1:]))
        return x
    if modo == "irma":
        return r + irma
    if modo == "irma_delta":
        return np.cumsum(r) + irma
    raise ValueError(modo)


def _mapear(r, modo):
    if modo == "zigue_zague":
        return ((r << 1) ^ (r >> 63)).astype(np.uint64), 0
    m = int(r.min()) if len(r) else 0
    return (r - m).astype(np.uint64), m


def _desmapear(u, modo, m):
    if modo == "zigue_zague":
        s = u.astype(np.int64)
        return (s >> 1) ^ -(s & 1)
    return u.astype(np.int64) + m


def _varint(u):
    u = u.astype(np.uint64)
    n = np.ones(len(u), np.int64)
    t = u >> np.uint64(7)
    while t.any():
        n += (t > 0); t >>= np.uint64(7)
    out = np.zeros(int(n.sum()), np.uint8)
    pos = np.concatenate(([0], np.cumsum(n)[:-1]))
    t = u.copy()
    for k in range(int(n.max()) if len(n) else 0):
        sel = n > k
        b = (t[sel] & np.uint64(0x7F)).astype(np.uint8)
        b |= ((n[sel] > k + 1).astype(np.uint8) << 7)
        out[pos[sel] + k] = b
        t[sel] >>= np.uint64(7)
    return out.tobytes()


def _desvarint(buf, cont):
    a = np.frombuffer(buf, np.uint8)
    fins = np.flatnonzero((a & 0x80) == 0)
    assert len(fins) >= cont
    fins = fins[:cont]
    ini = np.concatenate(([0], fins[:-1] + 1))
    u = np.zeros(cont, np.uint64)
    for k in range(10):
        sel = ini + k <= fins
        if not sel.any(): break
        u[sel] |= (a[ini[sel] + k] & np.uint64(0x7F)).astype(np.uint64) << np.uint64(7 * k)
    return u, int(fins[-1]) + 1 if cont else 0


def _empacotar(u, modo):
    if modo == "varint":
        return _varint(u)
    if modo == "bits_fixos":
        w = int(u.max()).bit_length() if len(u) else 0
        if w == 0: return bytes([0])
        bits = ((u[:, None] >> np.arange(w, dtype=np.uint64)[None, :]) & np.uint64(1)).astype(np.uint8)
        return bytes([w]) + np.packbits(bits.ravel()).tobytes()
    if modo == "planos_de_bytes":
        if len(u) and int(u.max()) >= 2 ** 32: return b"\x01" + u.astype("<u8").tobytes()
        return b"\x00" + u.astype("<u4").view(np.uint8).reshape(-1, 4).T.copy().tobytes()
    if modo == "int32":
        if len(u) and int(u.max()) >= 2 ** 32: return b"\x01" + u.astype("<u8").tobytes()
        return b"\x00" + u.astype("<u4").tobytes()
    raise ValueError(modo)


def _desempacotar(buf, modo, cont):
    """Devolve (u, bytes consumidos)."""
    if modo == "varint":
        return _desvarint(buf, cont)
    if modo == "bits_fixos":
        w = buf[0]
        if w == 0: return np.zeros(cont, np.uint64), 1
        nb = (cont * w + 7) // 8
        bits = np.unpackbits(np.frombuffer(buf[1:1 + nb], np.uint8))[:cont * w].reshape(cont, w).astype(np.uint64)
        return (bits << np.arange(w, dtype=np.uint64)[None, :]).sum(axis=1).astype(np.uint64), 1 + nb
    if modo in ("planos_de_bytes", "int32"):
        if buf[0] == 1: return np.frombuffer(buf[1:1 + 8 * cont], "<u8").astype(np.uint64), 1 + 8 * cont
        raw = np.frombuffer(buf[1:1 + 4 * cont], np.uint8)
        if modo == "planos_de_bytes": raw = raw.reshape(4, cont).T.copy().ravel()
        return raw.view("<u4").astype(np.uint64), 1 + 4 * cont
    raise ValueError(modo)


def _rle0(u):
    """Os zeros em corrida viram (0, tamanho - 1); os outros valores sobem 1. Exatamente inversível. (18/10: vetorizada; a versão com
    laço está em codec_v2_laco.py, e as duas dão os mesmos bytes, conferido em testar_rle0.py.)"""
    n = len(u)
    if not n: return u
    z = u == 0
    d = np.diff(np.concatenate(([0], z.astype(np.int8), [0])))
    ini, fim = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    nz = ~z
    # a posição de saída de cada elemento: os de antes, menos os zeros de antes, mais 2 por corrida começada antes
    zeros_antes = np.concatenate(([0], np.cumsum(z)[:-1]))
    corridas_antes = np.concatenate(([0], np.cumsum(d[:-1] == 1)[:-1]))
    pos = np.arange(n) - zeros_antes + 2 * corridas_antes
    out = np.empty(int(nz.sum()) + 2 * len(ini), np.uint64)
    out[pos[nz]] = u[nz] + np.uint64(1)
    out[pos[ini]] = 0
    out[pos[ini] + 1] = (fim - ini - 1).astype(np.uint64)
    return out


def _desrle0(t, cont):
    if not len(t):
        return t
    z = t == 0
    if not z.any():
        assert len(t) == cont
        return t - np.uint64(1)
    d = np.diff(np.concatenate(([0], z.astype(np.int8))))
    run_id = np.cumsum(d == 1)
    ini_run = np.flatnonzero(d == 1)
    deslocamento = np.arange(len(t)) - ini_run[np.maximum(run_id - 1, 0)]
    marca = z & (deslocamento % 2 == 0)
    tam = np.zeros(len(t), np.int64)
    m = np.flatnonzero(marca)
    comprimento = np.zeros(len(t), bool); comprimento[m + 1] = True
    dado = ~marca & ~comprimento
    tam[dado] = 1
    tam[m] = t[m + 1].astype(np.int64) + 1
    pos = np.cumsum(tam) - tam
    u = np.zeros(int(tam.sum()), np.uint64)
    u[pos[dado]] = t[dado] - np.uint64(1)
    assert len(u) == cont
    return u


def _fundo(b, modo):
    if modo == "nenhum": return b
    if modo == "zlib9": return zlib.compress(b, 9)
    if modo == "lzma9e": return lzma.compress(b, format=lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME}])
    if modo == "lzma6": return lzma.compress(b, format=lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA2, "preset": 6}])
    raise ValueError(modo)


def _desfundo(b, modo):
    if modo == "nenhum": return b
    if modo == "zlib9": return zlib.decompress(b)
    if modo == "lzma9e": return lzma.decompress(b, format=lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME}])
    if modo == "lzma6": return lzma.decompress(b, format=lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA2, "preset": 6}])
    raise ValueError(modo)


# ------------------------------------------------------------------ as classes de colunas (regra fixa, declarada, tirada dos dias de desenvolvimento)

CLASSES = ("tempo", "constante", "quase_zero", "contador", "inteiro_pequeno", "inteiro_grande", "com_irma", "outra")


def classificar(escalas, blocos):
    """Uma classe por coluna, pela regra fixa abaixo, olhando só os blocos dados (os de desenvolvimento)."""
    x = np.concatenate(blocos, axis=0)
    out = []
    for j in range(x.shape[1]):
        c = x[:, j]
        if j == 0: out.append(0); continue
        if (c == c[0]).all(): out.append(1); continue
        if (c == 0).mean() > 0.9: out.append(2); continue
        if (np.diff(c) >= 0).all(): out.append(3); continue
        p = 10 ** escalas[j]
        if (c % p == 0).all():
            out.append(4 if c.max() // p < 256 else 5); continue
        if j > 1 and (c == x[:, j - 1]).mean() > 0.5: out.append(6); continue
        out.append(7)
    return out


# ------------------------------------------------------------------ um codec: um gene de 10 bits por classe

def gene_para_cadeia(g):
    """10 bits: predição (3), mapa (1), empacote (2), corrida de zeros (1), fundo (2), arranjo (1)."""
    return {"predicao": PREDICOES[(g >> 7) & 7], "mapa": MAPAS[(g >> 6) & 1], "empacote": EMPACOTES[(g >> 4) & 3], "rle0": bool((g >> 3) & 1),
            "fundo": FUNDOS[(g >> 1) & 3], "arranjo": ARRANJOS[g & 1]}


def _irma(bloco, j, grupos):
    """A irmã da coluna j é a coluna j - 1, se ela estiver decodificada antes: num grupo de número menor, ou no mesmo grupo (que se
    decodifica na ordem das colunas). Sem irmã, a predição usa zeros. A mesma regra vale para codificar e para decodificar."""
    if j > 1 and grupos[j - 1] <= grupos[j]:
        return bloco[:, j - 1]
    return np.zeros(bloco.shape[0], np.int64)


def codificar_bloco(bloco, classes, cadeias, so=None):
    """Os bytes de um bloco: para cada classe, um cabeçalho por coluna (o deslocamento) e o fluxo empacotado e comprimido. Com `so`,
    só aquele grupo (para medir um grupo isolado, com a mesma regra da irmã)."""
    n = bloco.shape[0]
    partes = []
    for k, cad in enumerate(cadeias):
        if so is not None and k != so: continue
        cols = [j for j, c in enumerate(classes) if c == k]
        if not cols: continue
        us, desl = [], []
        for j in cols:
            r = _prever(bloco[:, j], cad["predicao"], _irma(bloco, j, classes))
            u, m = _mapear(r, cad["mapa"])
            us.append(u); desl.append(m)
        if cad["arranjo"] == "linha_a_linha":
            fluxo = np.stack(us, axis=1).ravel()
        else:
            fluxo = np.concatenate(us)
        if cad["rle0"]:
            fluxo = _rle0(fluxo)
        corpo = _fundo(_empacotar(fluxo, cad["empacote"]), cad["fundo"])
        cab = _varint(np.array([len(fluxo)] + [(m << 1) ^ (m >> 63) for m in desl], np.int64).astype(np.uint64))
        partes.append(_varint(np.array([len(cab), len(corpo)], np.uint64)) + cab + corpo)
    return b"".join(partes)


def decodificar_bloco(buf, n, classes, cadeias, so=None, base=None):
    """Com `so`, decodifica só aquele grupo, e as colunas dos outros grupos vêm de `base` (os valores verdadeiros, para a irmã)."""
    out = np.zeros((n, len(classes)), np.int64) if base is None else base.copy()
    pos = 0
    for k, cad in enumerate(cadeias):
        if so is not None and k != so: continue
        cols = [j for j, c in enumerate(classes) if c == k]
        if not cols: continue
        (lc, lb), q = _desvarint(buf[pos:pos + 20], 2); pos += q
        cab, corpo = buf[pos:pos + int(lc)], buf[pos + int(lc):pos + int(lc) + int(lb)]; pos += int(lc) + int(lb)
        h, _ = _desvarint(cab, 1 + len(cols))
        cont = int(h[0]); s = h[1:].astype(np.int64); desl = ((s >> 1) ^ -(s & 1)).tolist()
        fluxo, _ = _desempacotar(_desfundo(corpo, cad["fundo"]), cad["empacote"], cont)
        if cad["rle0"]:
            fluxo = _desrle0(fluxo, n * len(cols))
        us = fluxo.reshape(n, len(cols)).T if cad["arranjo"] == "linha_a_linha" else fluxo.reshape(len(cols), n)
        for i, j in enumerate(cols):          # na ordem das colunas: a irmã (a coluna anterior) já está decodificada quando precisa
            r = _desmapear(us[i], cad["mapa"], desl[i])
            out[:, j] = _desprever(r, cad["predicao"], _irma(out, j, classes))
    return out


def provar_forma_canonica(blocos, textos, escalas):
    """Uma vez, na carga: os bytes de cada bloco são exatamente a forma canônica dos inteiros dele. Com isso, refazer os inteiros
    exatos refaz os bytes exatos, e V pode comparar inteiros."""
    return all(texto_do_bloco(escalas, b) == t for b, t in zip(blocos, textos))


def medir_codec(blocos, textos, escalas, classes, genes):
    """V de um codec sobre os blocos: bytes totais, erro (blocos que não voltam exatos), segundos de codificar e de decodificar.
    A igualdade é a dos inteiros, que equivale à dos bytes pela prova da forma canônica feita na carga."""
    cadeias = [gene_para_cadeia(g) for g in genes]
    total, erros, tc, td = 0, 0, 0.0, 0.0
    for b, txt in zip(blocos, textos):
        t0 = time.process_time()
        try:
            enc = codificar_bloco(b, classes, cadeias)
        except Exception:
            return {"estado": "erro", "bytes": None}
        t1 = time.process_time()
        try:
            dec = decodificar_bloco(enc, b.shape[0], classes, cadeias)
            t2 = time.process_time()
            ok = np.array_equal(dec, b)
        except Exception:
            ok, t2 = False, time.process_time()
        total += len(enc) + 2 + 3; erros += (not ok); tc += t1 - t0; td += t2 - t1      # + o tamanho do bloco e o gene (declarado)
    return {"estado": "ok", "bytes": total, "erros": erros, "s_codificar": tc, "s_decodificar": td}
